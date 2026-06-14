from __future__ import annotations

import base64
import json
import time
import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from stores.models import Store, StorePaymentConfig

from .models import Payment, StoreProfitSharingEntry, SubOrder, WechatProfitSharingOrder
from .payment_service import PaymentService


def amount_to_cents(amount: Decimal) -> int:
    return int((Decimal(amount) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_amount(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))


class ProfitSharingService:
    @staticmethod
    def checkout_requires_profit_sharing(checkout_order) -> bool:
        return SubOrder.objects.filter(
            checkout_order=checkout_order,
            store__store_type=Store.TYPE_PARTNER,
        ).exists()

    @staticmethod
    def create_entries_for_payment(payment: Payment) -> list[StoreProfitSharingEntry]:
        if not payment.checkout_order_id:
            return []

        entries: list[StoreProfitSharingEntry] = []
        suborders = (
            SubOrder.objects
            .select_related("store", "legacy_order", "checkout_order")
            .filter(checkout_order_id=payment.checkout_order_id)
            .order_by("id")
        )
        with transaction.atomic():
            for suborder in suborders:
                entry, created = ProfitSharingService._create_entry(payment, suborder)
                if created:
                    entries.append(entry)
            ProfitSharingService.update_payment_status(payment)
        return entries

    @staticmethod
    def _create_entry(payment: Payment, suborder: SubOrder):
        store = suborder.store
        rule = getattr(store, "settlement_rule", None)
        commission_rate = getattr(rule, "commission_rate", Decimal("0.00")) if rule else Decimal("0.00")
        cycle_days = getattr(rule, "settlement_cycle_days", 7) if rule else 7
        gross_amount = suborder.actual_amount or Decimal("0.00")
        commission_amount = (gross_amount * commission_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sharing_amount = gross_amount - commission_amount

        payment_config = getattr(store, "payment_config", None)
        receiver_ready = bool(payment_config and payment_config.is_profit_sharing_ready)
        if store.store_type == Store.TYPE_PARTNER:
            status = "frozen" if receiver_ready else "pending_receiver_config"
            retained_amount = commission_amount
            receiver_type = StorePaymentConfig.RECEIVER_TYPE_MERCHANT_ID
            receiver_account = payment_config.wechat_mch_id if payment_config else ""
            receiver_name = payment_config.profit_sharing_receiver_name if payment_config else ""
        else:
            status = "platform_retained"
            sharing_amount = Decimal("0.00")
            retained_amount = gross_amount
            receiver_type = ""
            receiver_account = ""
            receiver_name = ""

        available_at = timezone.now() + timedelta(days=cycle_days) if status == "frozen" else None
        return StoreProfitSharingEntry.objects.get_or_create(
            suborder=suborder,
            defaults={
                "checkout_order": suborder.checkout_order,
                "payment": payment,
                "order": suborder.legacy_order,
                "store": store,
                "store_type_snapshot": store.store_type,
                "gross_amount": gross_amount,
                "commission_rate_snapshot": commission_rate,
                "commission_amount": commission_amount,
                "sharing_amount": sharing_amount,
                "retained_amount": retained_amount,
                "receiver_type": receiver_type,
                "receiver_account": receiver_account,
                "receiver_name_snapshot": receiver_name,
                "status": status,
                "available_at": available_at,
                "logs": [{"t": timezone.now().isoformat(), "event": "created"}],
            },
        )

    @staticmethod
    def refresh_entries_for_store(store) -> int:
        config = getattr(store, "payment_config", None)
        if not config or not config.is_profit_sharing_ready:
            return 0

        updated = 0
        now = timezone.now()
        entries = StoreProfitSharingEntry.objects.filter(store=store, status="pending_receiver_config")
        for entry in entries:
            entry.receiver_type = config.profit_sharing_receiver_type or StorePaymentConfig.RECEIVER_TYPE_MERCHANT_ID
            entry.receiver_account = config.wechat_mch_id
            entry.receiver_name_snapshot = config.profit_sharing_receiver_name
            if entry.available_at and entry.available_at <= now:
                entry.status = "available_for_manual_share"
            else:
                entry.status = "frozen"
                if not entry.available_at:
                    rule = getattr(store, "settlement_rule", None)
                    cycle_days = getattr(rule, "settlement_cycle_days", 7) if rule else 7
                    entry.available_at = now + timedelta(days=cycle_days)
            entry.logs.append({"t": now.isoformat(), "event": "receiver_config_refreshed"})
            entry.save(update_fields=[
                "receiver_type",
                "receiver_account",
                "receiver_name_snapshot",
                "status",
                "available_at",
                "logs",
                "updated_at",
            ])
            updated += 1
        return updated

    @staticmethod
    def mark_available(now=None) -> int:
        now = now or timezone.now()
        return StoreProfitSharingEntry.objects.filter(
            status="frozen",
            available_at__lte=now,
        ).update(status="available", updated_at=now)

    @staticmethod
    def update_payment_status(payment: Payment):
        if not payment.profit_sharing_required:
            return
        statuses = set(payment.profit_sharing_entries.values_list("status", flat=True))
        if not statuses:
            payment.profit_sharing_status = "pending"
        elif any(status == "pending_receiver_config" for status in statuses):
            payment.profit_sharing_status = "pending_receiver_config"
        elif any(status in {"frozen", "available", "available_for_manual_share"} for status in statuses):
            payment.profit_sharing_status = "available" if any(status in {"available", "available_for_manual_share"} for status in statuses) else "frozen"
        elif any(status == "processing" for status in statuses):
            payment.profit_sharing_status = "processing"
        elif any(status == "failed" for status in statuses):
            payment.profit_sharing_status = "failed"
        elif all(status in {"shared", "platform_retained", "cancelled", "manual_settled"} for status in statuses):
            payment.profit_sharing_status = "shared"
        payment.save(update_fields=["profit_sharing_status", "updated_at"])

    @staticmethod
    def start_manual_share(payment: Payment, entries: Iterable[StoreProfitSharingEntry], operator=None, unfreeze_unsplit: bool = False):
        entries = list(entries)
        if not payment.profit_sharing_required:
            raise ValueError("该支付不是微信分账订单")
        if payment.status != "succeeded":
            raise ValueError("支付未成功，不能分账")
        if payment.profit_sharing_unfrozen:
            raise ValueError("该支付剩余资金已解冻，不能继续微信分账")

        shareable_statuses = {"available", "available_for_manual_share", "failed"}
        invalid = [entry.id for entry in entries if entry.status not in shareable_statuses]
        if invalid:
            raise ValueError(f"存在不可分账流水: {invalid}")
        for entry in entries:
            if not entry.receiver_account or entry.sharing_amount <= 0:
                raise ValueError(f"分账流水#{entry.id}缺少接收方或金额")

        receivers = [
            {
                "type": entry.receiver_type or StorePaymentConfig.RECEIVER_TYPE_MERCHANT_ID,
                "account": entry.receiver_account,
                "name": entry.receiver_name_snapshot,
                "amount": amount_to_cents(entry.sharing_amount),
                "description": f"订单分账 {entry.suborder.suborder_number}",
            }
            for entry in entries
        ]
        amount = sum((entry.sharing_amount for entry in entries), Decimal("0.00"))

        with transaction.atomic():
            share_order = WechatProfitSharingOrder.objects.create(
                payment=payment,
                checkout_order=payment.checkout_order,
                transaction_id=ProfitSharingService.resolve_transaction_id(payment),
                receivers=receivers,
                amount=amount,
                unfreeze_unsplit=unfreeze_unsplit,
                operator=operator,
            )
            share_order.entries.set(entries)
            for entry in entries:
                entry.status = "processing"
                entry.logs.append({"t": timezone.now().isoformat(), "event": "manual_share_started", "out_order_no": share_order.out_order_no})
                entry.save(update_fields=["status", "logs", "updated_at"])
            ProfitSharingService.update_payment_status(payment)

        try:
            response = ProfitSharingService.request_wechat_share(share_order)
        except Exception as exc:
            ProfitSharingService.mark_share_failed(share_order, str(exc))
            raise
        share_order.wechat_response = response
        share_order.status = "processing"
        share_order.save(update_fields=["wechat_response", "status", "updated_at"])
        return share_order

    @staticmethod
    def resolve_transaction_id(payment: Payment) -> str:
        for entry in reversed(payment.logs or []):
            if isinstance(entry, dict) and entry.get("transaction_id"):
                return entry["transaction_id"]
        return ""

    @staticmethod
    def request_wechat_share(share_order: WechatProfitSharingOrder) -> dict:
        mchid = getattr(settings, "WECHAT_PAY_MCHID", "")
        if not mchid:
            raise RuntimeError("微信支付商户号未配置")
        if not share_order.transaction_id:
            raise RuntimeError("缺少微信支付交易号")

        body = {
            "appid": getattr(settings, "WECHAT_APPID", ""),
            "transaction_id": share_order.transaction_id,
            "out_order_no": share_order.out_order_no,
            "receivers": share_order.receivers,
            "unfreeze_unsplit": share_order.unfreeze_unsplit,
        }
        path = "/v3/profitsharing/orders"
        response = ProfitSharingService._wechat_post(path, body)
        return response

    @staticmethod
    def _wechat_post(path: str, body: dict) -> dict:
        mchid = getattr(settings, "WECHAT_PAY_MCHID", "")
        serial_no = getattr(settings, "WECHAT_PAY_SERIAL_NO", "")
        if not (mchid and serial_no and PaymentService._load_private_key()):
            raise RuntimeError("微信支付配置不完整")
        json_body = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        nonce_str = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        message = f"POST\n{path}\n{timestamp}\n{nonce_str}\n{json_body}\n"
        signature = PaymentService._sign_rsa(message)
        auth_header = (
            "WECHATPAY2-SHA256-RSA2048 "
            f'mchid="{mchid}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{serial_no}"'
        )
        resp = requests.post(
            f"https://api.mch.weixin.qq.com{path}",
            data=json_body.encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json",
                "Authorization": auth_header,
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"微信分账请求失败: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}

    @staticmethod
    def mark_share_succeeded(share_order: WechatProfitSharingOrder, response: dict | None = None):
        now = timezone.now()
        with transaction.atomic():
            share_order.status = "shared"
            if response is not None:
                share_order.wechat_response = response
            share_order.save(update_fields=["status", "wechat_response", "updated_at"])
            for entry in share_order.entries.select_for_update().all():
                entry.status = "shared"
                entry.shared_at = now
                entry.logs.append({"t": now.isoformat(), "event": "shared", "out_order_no": share_order.out_order_no})
                entry.save(update_fields=["status", "shared_at", "logs", "updated_at"])
            if share_order.unfreeze_unsplit:
                payment = share_order.payment
                payment.profit_sharing_unfrozen = True
                payment.save(update_fields=["profit_sharing_unfrozen", "updated_at"])
            ProfitSharingService.update_payment_status(share_order.payment)

    @staticmethod
    def mark_share_failed(share_order: WechatProfitSharingOrder, error_message: str):
        with transaction.atomic():
            share_order.status = "failed"
            share_order.error_message = error_message
            share_order.save(update_fields=["status", "error_message", "updated_at"])
            for entry in share_order.entries.select_for_update().all():
                entry.status = "failed"
                entry.failure_reason = error_message
                entry.logs.append({"t": timezone.now().isoformat(), "event": "share_failed", "error": error_message})
                entry.save(update_fields=["status", "failure_reason", "logs", "updated_at"])
            ProfitSharingService.update_payment_status(share_order.payment)
