from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from django.utils import timezone

from .payment_service import PaymentService
from .state_machine import OrderStateMachine

logger = logging.getLogger(__name__)


def cancel_order_local(
    order,
    operator=None,
    reason: str = '',
    note: str = '',
) -> Dict[str, Any]:
    """Cancel order locally and trigger refunds/notifications.

    This does not sync to YLH; intended for local cancellation after YLH callbacks.
    """
    if order.status in {'cancelled', 'refunding', 'refunded'}:
        return {
            'order': order,
            'refund_started': False,
            'refund_id': None,
            'refund_error': None,
            'refund_channel': None,
            'skipped': True,
        }

    if reason:
        order.cancel_reason = reason
    order.cancelled_at = timezone.now()
    order.save(update_fields=['cancel_reason', 'cancelled_at'])

    refundable_snapshot = PaymentService.calculate_refundable_amount(order)
    pay_snapshot = order.payments.filter(status='succeeded', method='wechat').order_by('-created_at').first()
    should_refund = bool(
        pay_snapshot and refundable_snapshot > 0 and OrderStateMachine.can_transition(order.status, 'refunding')
    )
    refund = None
    refund_err = None
    credit_refund_started = False
    credit_refund_err = None

    # 信用支付：未发货前自动冲减信用，发货后需人工处理
    is_credit = getattr(order, 'payment_method', '') == 'credit'
    if is_credit and order.status in ['pending', 'paid'] and order.status != 'shipped':
        try:
            from users.credit_services import CreditAccountService
            if hasattr(order.user, 'credit_account') and order.user.credit_account:
                CreditAccountService.record_refund(
                    credit_account=order.user.credit_account,
                    amount=getattr(order, 'actual_amount', None) or order.total_amount,
                    order_id=order.id,
                    description=f'订单取消信用退款 #{order.order_number}'
                )
                credit_refund_started = True
            else:
                credit_refund_err = '未找到信用账户，需人工处理'
        except Exception as exc:
            credit_refund_err = str(exc)
        # 信用退款不走微信自动退款
        should_refund = False
    elif is_credit and order.status == 'shipped':
        credit_refund_err = '信用支付订单已发货，需人工审核退款'
        should_refund = False

    # 自动退款（微信支付）
    try:
        refundable = refundable_snapshot
        pay = pay_snapshot
        logger.info('[ORDER_CANCEL] refund check', extra={'order_id': order.id, 'refundable': str(refundable), 'pay_id': pay.id if pay else None, 'pay_status': getattr(pay, "status", None)})
        if should_refund:
            reason_text = order.cancel_reason or note or '订单取消自动退款'
            refund, refund_err = PaymentService.start_order_refund(
                order,
                refundable,
                reason=reason_text,
                operator=operator,
                payment=pay
            )
            if refund_err:
                logger.error(f'取消订单自动退款失败: order_id={order.id}, err={refund_err}', extra={'refund_id': refund.id if refund else None})
                try:
                    from users.services import create_notification
                    create_notification(
                        order.user,
                        title='退款发起失败',
                        content=f'订单 {order.order_number} 退款发起失败，原因：{refund_err}',
                        ntype='refund',
                        metadata={
                            'order_id': order.id,
                            'order_number': order.order_number,
                            'refund_id': refund.id if refund else None,
                            'status': 'failed',
                            'page': f'pages/order-detail/index?id={order.id}',
                        }
                    )
                except Exception:
                    pass
        elif refundable > 0:
            logger.info(f'取消订单未退款：未找到可退款支付记录 order_id={order.id}')
    except Exception as refund_exc:
        refund_err = str(refund_exc)
        logger.exception(f'取消订单触发退款异常: {refund_exc}')
        try:
            from users.services import create_notification
            create_notification(
                order.user,
                title='退款发起失败',
                content=f'订单 {order.order_number} 退款发起失败，原因：{refund_err}',
                ntype='refund',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'refund_id': refund.id if refund else None,
                    'status': 'failed',
                    'page': f'pages/order-detail/index?id={order.id}',
                }
            )
        except Exception:
            pass

    # 状态机更新（根据退款结果）
    if should_refund and not refund_err and OrderStateMachine.can_transition(order.status, 'refunding'):
        order = OrderStateMachine.transition(
            order,
            'refunding',
            operator=operator,
            note=note or '订单取消，退款处理中'
        )
    else:
        order = OrderStateMachine.transition(
            order,
            'cancelled',
            operator=operator,
            note=note
        )

    try:
        from users.services import create_notification
        create_notification(
            order.user,
            title='订单已取消',
            content=f'订单 {order.order_number} 已取消' + (f'，原因：{order.cancel_reason}' if order.cancel_reason else ''),
            ntype='order',
            metadata={
                'order_id': order.id,
                'order_number': order.order_number,
                'status': 'cancelled',
                'page': f'pages/order-detail/index?id={order.id}',
                'subscription_data': {
                    'thing1': {'value': f'订单 {order.order_number}'[:20]},
                    'time2': {'value': timezone.localtime(order.cancelled_at).strftime('%Y-%m-%d %H:%M') if order.cancelled_at else ''},
                    'thing3': {'value': (order.cancel_reason or '订单已取消')[:20]},
                },
            }
        )
    except Exception:
        pass

    return {
        'order': order,
        'refund_started': bool((should_refund and not refund_err and refund) or credit_refund_started),
        'refund_id': refund.id if refund else None,
        'refund_error': refund_err or credit_refund_err,
        'refund_channel': 'wechat' if refund else ('credit' if credit_refund_started else None),
        'skipped': False,
    }
