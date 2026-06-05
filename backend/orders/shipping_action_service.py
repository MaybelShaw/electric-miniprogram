from copy import deepcopy

from django.db import IntegrityError, transaction

from catalog.models import Product

from .models import Order, OrderShippingAction
from .state_machine import OrderStateMachine


class ShippingActionError(ValueError):
    """发货操作业务错误。"""


def is_haier_order(order: Order) -> bool:
    if order.order_type == 'haier':
        return True
    if order.haier_so_id or order.haier_order_no or order.haier_status:
        return True

    items = list(order.items.all())
    if any(
        item.product_id
        and getattr(item.product, 'source', None) == Product.SOURCE_HAIER
        for item in items
    ):
        return True

    return bool(
        not items
        and order.product_id
        and getattr(order.product, 'source', None) == Product.SOURCE_HAIER
    )


def build_shipping_snapshot(order: Order) -> dict:
    return {
        'logistics_no': order.logistics_no or '',
        'shipping_info': deepcopy(order.shipping_info or {}),
        'delivery_record_code': order.delivery_record_code or '',
        'sn_code': order.sn_code or '',
        'delivery_images': deepcopy(order.delivery_images or []),
    }


def get_shipping_capabilities(order: Order) -> dict:
    cached = getattr(order, '_shipping_capabilities_cache', None)
    if cached is not None:
        return cached

    actions = list(order.shipping_actions.all())
    successful_cancel = next(
        (
            action for action in actions
            if action.action == 'cancel_shipping' and action.status == 'succeeded'
        ),
        None,
    )
    successful_reship = any(
        action.action == 'reship' and action.status == 'succeeded'
        for action in actions
    )
    pending = successful_cancel is not None and not successful_reship
    capabilities = {
        'can_cancel_shipping': (
            order.status == 'shipped'
            and not is_haier_order(order)
            and successful_cancel is None
        ),
        'is_reshipment_pending': order.status == 'paid' and pending,
        'reship_requires_wechat_sync': (
            order.status == 'paid'
            and pending
            and bool(successful_cancel.wechat_sync_required)
        ),
        'shipping_cancel_count': 1 if successful_cancel else 0,
    }
    order._shipping_capabilities_cache = capabilities
    return capabilities


def get_shipping_context(order: Order) -> dict:
    capabilities = get_shipping_capabilities(order)
    return {
        'action': 'reship' if capabilities['is_reshipment_pending'] else 'ship',
        'is_reship': capabilities['is_reshipment_pending'],
        'wechat_sync_required': (
            capabilities['reship_requires_wechat_sync']
            if capabilities['is_reshipment_pending']
            else False
        ),
    }


def sanitize_wechat_response(response: dict | None, error: str = '') -> dict:
    response = response if isinstance(response, dict) else {}
    result = {
        key: response[key]
        for key in ('errcode', 'errmsg')
        if key in response
    }
    if error:
        result['error'] = str(error)[:500]
    return result


def create_successful_shipping_action(
    *,
    order: Order,
    action: str,
    operator,
    snapshot: dict,
    wechat_sync_required: bool,
    wechat_synced: bool,
    wechat_response: dict | None,
) -> OrderShippingAction:
    return OrderShippingAction.objects.create(
        order=order,
        action=action,
        status='succeeded',
        shipping_snapshot=deepcopy(snapshot),
        operator=operator,
        wechat_sync_required=wechat_sync_required,
        wechat_synced=wechat_synced,
        wechat_response=sanitize_wechat_response(wechat_response),
    )


def create_failed_reship_action(
    *,
    order_id: int,
    operator,
    snapshot: dict,
    response: dict | None,
    error: str,
) -> OrderShippingAction:
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        return OrderShippingAction.objects.create(
            order=order,
            action='reship',
            status='failed',
            shipping_snapshot=deepcopy(snapshot),
            operator=operator,
            reason='微信重新发货同步失败',
            wechat_sync_required=True,
            wechat_synced=False,
            wechat_response=sanitize_wechat_response(response, error),
        )


@transaction.atomic
def cancel_shipping(order_id: int, operator, reason: str) -> OrderShippingAction:
    normalized_reason = (reason or '').strip()
    if not normalized_reason:
        raise ShippingActionError('取消原因不能为空')
    if len(normalized_reason) > 200:
        raise ShippingActionError('取消原因不能超过200个字符')

    order = (
        Order.objects.select_for_update()
        .select_related('product', 'user')
        .prefetch_related('items__product', 'shipping_actions', 'shipping_syncs')
        .get(pk=order_id)
    )
    if any(
        action.action == 'cancel_shipping' and action.status == 'succeeded'
        for action in order.shipping_actions.all()
    ):
        raise ShippingActionError('该订单已使用取消发货机会')
    if order.status != 'shipped':
        raise ShippingActionError('仅已发货订单可以取消发货')
    if is_haier_order(order):
        raise ShippingActionError('海尔订单不支持取消发货')

    snapshot = build_shipping_snapshot(order)
    prior_wechat_sync = any(
        sync.status == 'succeeded'
        for sync in order.shipping_syncs.all()
    )
    try:
        with transaction.atomic():
            action = OrderShippingAction.objects.create(
                order=order,
                action='cancel_shipping',
                status='succeeded',
                shipping_snapshot=snapshot,
                operator=operator,
                reason=normalized_reason,
                wechat_sync_required=prior_wechat_sync,
                wechat_synced=False,
            )
    except IntegrityError as exc:
        raise ShippingActionError('该订单已使用取消发货机会') from exc

    order.logistics_no = ''
    order.shipping_info = {}
    order.delivery_record_code = ''
    order.sn_code = ''
    order.delivery_images = []
    order.save(update_fields=[
        'logistics_no',
        'shipping_info',
        'delivery_record_code',
        'sn_code',
        'delivery_images',
    ])
    OrderStateMachine.reverse_shipping(
        order,
        operator=operator,
        note=f'取消发货：{normalized_reason}',
    )
    return action
