import logging
import json
from datetime import timedelta, datetime
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from integrations.wechat import WeChatMiniProgramClient
from .models import OrderShippingSync

logger = logging.getLogger(__name__)


def _mask_contact(value: str) -> str:
    if not value:
        return ''
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    if len(digits) < 4:
        return value
    if len(digits) >= 7:
        return f"{digits[:3]}****{digits[-4:]}"
    return f"****{digits[-4:]}"


def _build_item_desc(order) -> str:
    parts = []
    items = list(order.items.all()) if hasattr(order, 'items') else []
    if items:
        for item in items:
            name = item.product_name or getattr(item.product, 'name', '') or '商品'
            qty = item.quantity or 1
            parts.append(f"{name}*{qty}")
    else:
        name = getattr(order.product, 'name', '') if order.product else '商品'
        qty = order.quantity or 1
        parts.append(f"{name}*{qty}")

    desc = '，'.join(parts)
    return desc[:120]


def _build_order_key(order) -> Optional[Dict[str, str]]:
    order_number_type = int(getattr(settings, 'WECHAT_SHIPPING_ORDER_NUMBER_TYPE', 1) or 1)
    if order_number_type == 1:
        mchid = getattr(settings, 'WECHAT_PAY_MCHID', '')
        if not mchid:
            logger.warning('wechat shipping missing mchid, skip order_id=%s', order.id)
            return None
        return {
            'order_number_type': 1,
            'mchid': mchid,
            'out_trade_no': order.order_number,
        }
    # order_number_type == 2
    pay = order.payments.filter(status='succeeded', method='wechat').order_by('-created_at').first()
    transaction_id = None
    if pay:
        for log in reversed(pay.logs or []):
            if isinstance(log, dict) and log.get('transaction_id'):
                transaction_id = log.get('transaction_id')
                break
    if not transaction_id:
        logger.warning('wechat shipping missing transaction_id, skip order_id=%s', order.id)
        return None
    return {
        'order_number_type': 2,
        'transaction_id': transaction_id,
    }


def _should_sync(order) -> bool:
    if not getattr(settings, 'WECHAT_SHIPPING_SYNC_ENABLED', False):
        return False
    # only sync wechat-paid orders
    return order.payments.filter(status='succeeded', method='wechat').exists()


def _next_retry_time() -> Optional[datetime]:
    minutes = int(getattr(settings, 'WECHAT_SHIPPING_RETRY_INTERVAL_MINUTES', 10) or 10)
    return timezone.now() + timedelta(minutes=minutes)


def upload_shipping_info(
    order,
    tracking_no: Optional[str] = None,
    express_company: Optional[str] = None,
    logistics_type: Optional[int] = None,
    delivery_mode: Optional[int] = None,
    is_all_delivered: Optional[bool] = None,
    item_desc: Optional[str] = None,
    retry_times: int = 1,
    shipping_list: Optional[list] = None,
) -> Tuple[bool, Dict, str]:
    if not _should_sync(order):
        return False, {}, 'sync_disabled_or_not_wechat_paid'

    order_key = _build_order_key(order)
    if not order_key:
        return False, {}, 'missing_order_key'

    openid = getattr(order.user, 'openid', '')
    if not openid:
        return False, {}, 'missing_openid'

    logistics_type = int(logistics_type or getattr(settings, 'WECHAT_SHIPPING_LOGISTICS_TYPE', 1) or 1)
    delivery_mode = int(delivery_mode or getattr(settings, 'WECHAT_SHIPPING_DELIVERY_MODE', 1) or 1)

    if logistics_type == 1 and not shipping_list:
        if not tracking_no:
            return False, {}, 'missing_tracking_no'
        if not express_company:
            return False, {}, 'missing_express_company'

    if delivery_mode == 2 and is_all_delivered is None:
        return False, {}, 'missing_is_all_delivered'

    shipping_items: list[Dict[str, object]] = []
    if shipping_list:
        if not isinstance(shipping_list, list):
            return False, {}, 'invalid_shipping_list'
        if len(shipping_list) == 0:
            return False, {}, 'shipping_list_empty'
        if len(shipping_list) > 15:
            return False, {}, 'shipping_list_too_long'
        for item in shipping_list:
            if not isinstance(item, dict):
                return False, {}, 'invalid_shipping_list'
            tracking = item.get('tracking_no')
            company = item.get('express_company')
            if logistics_type == 1:
                if not tracking:
                    return False, {}, 'missing_tracking_no'
                if not company:
                    return False, {}, 'missing_express_company'
            desc = (item.get('item_desc') or item_desc or _build_item_desc(order) or '').strip()[:120]
            if not desc:
                return False, {}, 'missing_item_desc'
            shipping_item: Dict[str, object] = {
                'item_desc': desc,
            }
            if tracking:
                shipping_item['tracking_no'] = tracking
            if company:
                shipping_item['express_company'] = company
            if item.get('contact'):
                shipping_item['contact'] = item.get('contact')
            elif company and str(company).upper().startswith('SF'):
                contact = _mask_contact(getattr(order, 'snapshot_phone', '') or '')
                if contact:
                    shipping_item['contact'] = {'receiver_contact': contact}
            shipping_items.append(shipping_item)
    else:
        desc = (item_desc or _build_item_desc(order) or '').strip()[:120]
        if not desc:
            return False, {}, 'missing_item_desc'
        shipping_item: Dict[str, object] = {
            'item_desc': desc,
        }
        if tracking_no:
            shipping_item['tracking_no'] = tracking_no
        if express_company:
            shipping_item['express_company'] = express_company
        if express_company and str(express_company).upper().startswith('SF'):
            contact = _mask_contact(getattr(order, 'snapshot_phone', '') or '')
            if contact:
                shipping_item['contact'] = {'receiver_contact': contact}
        shipping_items = [shipping_item]

    if delivery_mode == 1 and len(shipping_items) != 1:
        return False, {}, 'delivery_mode_mismatch'
    if delivery_mode == 2 and len(shipping_items) < 2:
        return False, {}, 'delivery_mode_mismatch'

    payload: Dict[str, object] = {
        'order_key': order_key,
        'logistics_type': logistics_type,
        'delivery_mode': delivery_mode,
        'shipping_list': shipping_items,
        'upload_time': timezone.now().isoformat(),
        'payer': {'openid': openid},
    }
    if delivery_mode == 2:
        payload['is_all_delivered'] = bool(is_all_delivered)

    def _should_retry(last_err: str, last_resp: Dict) -> bool:
        if isinstance(last_err, str) and last_err.startswith('http_status_'):
            return True
        if last_err in {'missing_access_token'}:
            return True
        if isinstance(last_resp, dict) and last_resp.get('errcode') in (-1, 10060012, 10060019):
            return True
        return False

    max_attempts = max(1, int(retry_times or 1))
    client = WeChatMiniProgramClient()
    last_resp: Dict = {}
    last_err = ''
    for attempt in range(max_attempts):
        logger.warning(
            '[SHIP_DEBUG] wechat upload shipping info attempt | %s',
            json.dumps(
                {
                    'order_id': getattr(order, 'id', None),
                    'delivery_mode': delivery_mode,
                    'logistics_type': logistics_type,
                    'shipping_list_len': len(shipping_items),
                    'attempt': attempt + 1,
                    'max_attempts': max_attempts,
                },
                ensure_ascii=False,
            ),
        )
        ok, resp, err = client.upload_shipping_info(payload)
        last_resp = resp or {}
        last_err = err or ''
        if ok:
            OrderShippingSync.objects.create(
                order=order,
                status='succeeded',
                payload=payload,
                response=last_resp,
                error='',
            )
            return True, last_resp, ''

        # treat "未更新" as idempotent success
        if isinstance(last_resp, dict) and last_resp.get('errcode') == 10060023:
            OrderShippingSync.objects.create(
                order=order,
                status='succeeded',
                payload=payload,
                response=last_resp,
                error='',
            )
            return True, last_resp, ''

        if attempt >= max_attempts - 1 or not _should_retry(last_err, last_resp):
            break

    error_message = last_err or (last_resp.get('errmsg') if isinstance(last_resp, dict) else 'wechat_error')
    return False, last_resp, error_message
