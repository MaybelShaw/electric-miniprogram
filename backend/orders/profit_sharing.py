from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from stores.models import Store, StorePaymentConfig

from .models import Payment, StoreProfitSharingEntry, SubOrder


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
        commission_amount = (gross_amount * commission_rate / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        sharing_amount = gross_amount - commission_amount

        payment_config = getattr(store, "payment_config", None)
        if store.store_type == Store.TYPE_PARTNER:
            status = "frozen"
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
        if not config or not config.wechat_mch_id:
            return 0

        updated = 0
        now = timezone.now()
        entries = StoreProfitSharingEntry.objects.filter(store=store, status="pending_receiver_config")
        for entry in entries:
            entry.receiver_type = config.profit_sharing_receiver_type or StorePaymentConfig.RECEIVER_TYPE_MERCHANT_ID
            entry.receiver_account = config.wechat_mch_id
            entry.receiver_name_snapshot = config.profit_sharing_receiver_name
            if entry.available_at and entry.available_at <= now:
                entry.status = "available"
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
            payment.profit_sharing_status = (
                "available"
                if any(status in {"available", "available_for_manual_share"} for status in statuses)
                else "frozen"
            )
        elif any(status == "processing" for status in statuses):
            payment.profit_sharing_status = "processing"
        elif any(status == "failed" for status in statuses):
            payment.profit_sharing_status = "failed"
        elif all(status in {"shared", "platform_retained", "cancelled", "manual_settled"} for status in statuses):
            payment.profit_sharing_status = "shared"
        payment.save(update_fields=["profit_sharing_status", "updated_at"])

    @staticmethod
    def resolve_transaction_id(payment: Payment) -> str:
        for entry in reversed(payment.logs or []):
            if isinstance(entry, dict) and entry.get("transaction_id"):
                return entry["transaction_id"]
        return ""
