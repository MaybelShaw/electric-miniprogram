from rest_framework import viewsets, permissions, status, serializers
from rest_framework.views import APIView
from .models import Order,Cart,CartItem, Payment, Refund, Discount, DiscountTarget, Invoice, ReturnRequest
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    CartItemSerializer,
    CartSerializer,
    PaymentSerializer,
    RefundSerializer,
    RefundCreateSerializer,
    DiscountSerializer,
    DiscountTargetSerializer,
    InvoiceSerializer,
    InvoiceCreateSerializer,
    ReturnRequestSerializer,
    ReturnRequestCreateSerializer,
)
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import create_order, get_or_create_cart, add_to_cart, remove_from_cart, resolve_base_price
from .analytics import OrderAnalytics
from catalog.models import Product
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from typing import Dict, Optional
from common.permissions import IsOwnerOrAdmin, IsAdmin
from common.excel import build_excel_response
from common.utils import parse_int, parse_datetime
from common.throttles import PaymentRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes as OT
from django.http import FileResponse
from common.serializers import PDFOrImageFileValidator
from common.logging import log_security
import logging
import json
from decimal import Decimal, ROUND_HALF_UP
from .payment_service import PaymentService


def _wechat_shipping_error_message(err: str | None, resp: Dict | None) -> str:
    errcode = None
    errmsg = None
    if isinstance(resp, dict):
        errcode = resp.get('errcode')
        errmsg = resp.get('errmsg')

    errcode_map = {
        -1: '系统繁忙，请稍后再试',
        10060001: '支付单不存在，请核对订单号或交易号',
        10060002: '支付单已完成发货，无法继续发货',
        10060003: '该支付单已使用重新发货机会',
        10060004: '支付单处于不可发货状态',
        10060005: '物流类型有误',
        10060006: '非快递发货不允许分拆发货',
        10060007: '分拆发货必须填写 is_all_delivered',
        10060008: '商品描述不能为空',
        10060009: '商品描述过长',
        10060012: '系统繁忙，请稍后再试',
        10060014: '参数错误，请检查请求参数',
        10060019: '系统繁忙，请稍后再试',
        10060020: '未填写商品描述，无法完成发货',
        10060023: '发货信息未更新',
        10060024: '物流信息列表过长（最多 15 条）',
        10060025: '物流公司编码过长',
        10060026: '物流单号过长',
        10060031: '订单不属于该用户 openid',
        268485216: '上传时间格式非法，请使用 RFC3339',
        268485224: '发货模式非法',
        268485195: 'transaction_id 不能为空',
        268485196: 'mchid 不能为空',
        268485197: 'out_trade_no 不能为空',
        268485194: '订单单号类型非法',
        268485228: '统一发货模式下物流信息列表长度必须为 1',
        268485226: '物流单号不能为空',
        268485227: '物流公司编码不能为空',
    }
    internal_map = {
        'missing_access_token': '微信 access_token 获取失败',
        'missing_order_key': '订单号信息缺失，无法同步微信发货',
        'missing_openid': 'openid 缺失，无法同步微信发货',
        'missing_tracking_no': '物流单号缺失',
        'missing_express_company': '物流公司编码缺失',
        'missing_is_all_delivered': '分拆发货必须提供 is_all_delivered',
        'missing_item_desc': '商品描述缺失',
        'sync_disabled_or_not_wechat_paid': '该订单未开启或无需微信发货同步',
        'invalid_shipping_list': '包裹列表格式不正确',
        'shipping_list_empty': '包裹列表不能为空',
        'shipping_list_too_long': '包裹数量不能超过 15 个',
        'delivery_mode_mismatch': '发货模式与包裹数量不匹配',
    }

    if errcode in errcode_map:
        return errcode_map[errcode]
    if err in internal_map:
        return internal_map[err]
    if isinstance(err, str) and err.startswith('http_status_'):
        return f"微信接口请求失败（HTTP {err.split('_')[-1]}），结果可能未同步，请先在微信后台确认后再重试"
    if errmsg:
        lowered = str(errmsg).lower()
        if 'not utf8' in lowered or 'data format error' in lowered:
            rid = None
            if 'rid' in lowered:
                try:
                    rid = str(errmsg).split('rid:')[-1].strip()
                except Exception:
                    rid = None
            suffix = f"（rid: {rid}）" if rid else ''
            return f"发货数据格式错误（请检查物流单号/商品描述/联系方式是否包含非 UTF-8 字符）{suffix}"
        return f"微信返回错误：{errmsg}"
    if err:
        return f"微信接口异常（{err}），结果可能未同步，请先在微信后台确认后再重试"
    return '微信发货同步失败'


class _WechatShippingSyncException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def _mask_tracking_no(value: str) -> str:
    if not value:
        return ''
    if len(value) <= 6:
        return '*' * len(value)
    return f"{value[:3]}****{value[-3:]}"

def _log_ship_debug(logger, message: str, extra: dict | None = None):
    """Ensure shipping debug info is emitted even when DEBUG logs are disabled."""
    payload = extra or {}
    logger.warning(f"[SHIP_DEBUG] {message} | {json.dumps(payload, ensure_ascii=False)}")


def _contains_chinese(value: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in (value or ''))

# Create your views here.
@extend_schema(tags=['Orders'])
class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders.
    
    Permissions:
    - IsOwnerOrAdmin: Users can only access their own orders, admins can access all
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.all() if (user.is_staff or getattr(user, 'role', '') == 'support') else Order.objects.filter(user=user)
        
        # Optimize queries by prefetching related objects
        qs = qs.select_related('user', 'product', 'return_request').prefetch_related(
            'payments',
            'status_history',
            'items',
            'items__product',
            'items__sku',
            'refunds',
        )

        # 订单状态筛选
        status_filter = self.request.query_params.get('status')
        if status_filter:
            if ',' in status_filter:
                status_list = status_filter.split(',')
                rr_active = {'requested', 'approved', 'in_transit', 'received'}
                if 'returning' in status_list:
                    qs = qs.filter(
                        Q(status__in=status_list) |
                        Q(return_request__status__in=rr_active)
                    )
                else:
                    qs = qs.filter(status__in=status_list)
            else:
                if status_filter == 'returning':
                    rr_active = {'requested', 'approved', 'in_transit', 'received'}
                    qs = qs.filter(Q(status='returning') | Q(return_request__status__in=rr_active))
                elif status_filter == 'completed':
                    rr_active = {'requested', 'approved', 'in_transit', 'received'}
                    qs = qs.filter(status='completed').exclude(return_request__status__in=rr_active)
                else:
                    qs = qs.filter(status=status_filter)

        # 订单号搜索（模糊）
        order_number = self.request.query_params.get('order_number')
        if order_number:
            qs = qs.filter(order_number__icontains=order_number)

        # 商品名称搜索（模糊）
        product_name = self.request.query_params.get('product_name')
        if product_name:
            try:
                qs = qs.filter(Q(product__name__icontains=product_name) | Q(items__product__name__icontains=product_name))
            except Exception:
                pass

        # 用户名搜索（管理员可用）：模糊匹配 user.username
        username = self.request.query_params.get('username')
        if (self.request.user.is_staff or getattr(self.request.user, 'role', '') == 'support') and username:
            try:
                qs = qs.filter(user__username__icontains=username)
            except Exception:
                pass

        # 按用户ID筛选（仅管理员有效）
        user_id = self.request.query_params.get('user_id')
        if (user.is_staff or getattr(user, 'role', '') == 'support') and user_id:
            uid = parse_int(user_id)
            if uid is not None:
                try:
                    qs = qs.filter(user_id=uid)
                except Exception:
                    pass

        # 创建时间范围筛选：created_after / created_before（ISO8601 或可解析时间字符串）
        created_after = self.request.query_params.get('created_after')
        created_before = self.request.query_params.get('created_before')
        if created_after:
            dt = parse_datetime(created_after)
            if dt:
                try:
                    qs = qs.filter(created_at__gte=dt)
                except Exception:
                    pass
        if created_before:
            dt = parse_datetime(created_before)
            if dt:
                try:
                    qs = qs.filter(created_at__lte=dt)
                except Exception:
                    pass

        return qs.distinct().order_by('-created_at')

    @action(detail=False, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        headers = [
            '订单号',
            '用户名',
            '状态',
            '商品',
            '数量',
            '总金额',
            '折扣金额',
            '实付金额',
            '下单时间',
        ]
        rows = []
        for order in qs:
            items = list(order.items.all())
            if items:
                names = []
                for item in items:
                    name = getattr(item, 'product_name', '') or (item.product.name if item.product else '')
                    if name:
                        names.append(name)
                product_names = ", ".join(names)
            else:
                product_names = order.product.name if order.product else ''
            rows.append([
                order.order_number,
                getattr(order.user, 'username', ''),
                order.get_status_display(),
                product_names,
                order.total_quantity,
                order.total_amount,
                order.discount_amount,
                order.actual_amount,
                order.created_at,
            ])
        filename = f"orders_export_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="订单导出")

    @action(detail=True, methods=['patch'], permission_classes=[IsOwnerOrAdmin])
    def status(self, request, pk=None):
        """更新订单状态：管理员或订单所有者可操作。输入 {status} 为枚举值。
        用于满足 PRD 中 PATCH /api/orders/{id}/status/ 端点。
        """
        order = self.get_object()
        new_status = str(request.data.get('status', '')).lower()
        allowed = {s for s, _ in Order.STATUS_CHOICES}
        if new_status not in allowed:
            return Response({'detail': 'invalid status'}, status=400)
        # 权限已由 IsAdminOrOwner 保证；若为终态间切换，允许覆盖
        order.status = new_status
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def adjust_amount(self, request, pk=None):
        import logging as pylogging
        logger = pylogging.getLogger(__name__)
        order = self.get_object()
        if order.status != 'pending':
            logger.info(
                '[ORDER_ADJUST] blocked: status_not_pending',
                extra={'order_id': order.id, 'order_status': order.status}
            )
            return Response({'detail': 'Only pending orders can be adjusted'}, status=status.HTTP_400_BAD_REQUEST)

        from common.utils import parse_decimal
        new_amount = parse_decimal(request.data.get('actual_amount'))
        if new_amount is None:
            return Response({'detail': 'actual_amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        if new_amount <= 0:
            return Response({'detail': 'actual_amount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)

        new_amount = new_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_amount = order.total_amount or Decimal('0')
        current_amount = order.actual_amount if order.actual_amount is not None else total_amount
        if new_amount > current_amount:
            return Response({'detail': 'actual_amount cannot exceed current payable amount'}, status=status.HTTP_400_BAD_REQUEST)

        if order.payments.filter(status='succeeded').exists():
            logger.info(
                '[ORDER_ADJUST] blocked: payment_succeeded',
                extra={'order_id': order.id, 'order_status': order.status}
            )
            return Response({'detail': 'Order has succeeded payment, cannot adjust amount'}, status=status.HTTP_400_BAD_REQUEST)

        processing_payment = order.payments.filter(status='processing').first()
        if processing_payment:
            logger.info(
                '[ORDER_ADJUST] blocked: payment_processing',
                extra={
                    'order_id': order.id,
                    'order_status': order.status,
                    'payment_id': processing_payment.id
                }
            )
            return Response({'detail': 'Payment is processing, cannot adjust amount'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # 取消未开始的支付记录，确保后续支付使用新金额
            init_payments = order.payments.filter(status='init')
            for payment in init_payments:
                payment.status = 'cancelled'
                payment.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'cancelled_by_admin_adjust',
                    'detail': 'cancelled due to admin amount adjustment',
                })
                payment.save(update_fields=['status', 'logs', 'updated_at'])

            items = list(order.items.select_for_update())
            if items and current_amount > 0:
                allocations = []
                for item in items:
                    unit_total = (item.unit_price or Decimal('0')) * item.quantity
                    base_amount = item.actual_amount if item.actual_amount is not None else unit_total
                    raw_amount = (base_amount * new_amount) / current_amount
                    rounded_amount = raw_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    allocations.append({
                        'item': item,
                        'unit_total': unit_total,
                        'base_amount': base_amount,
                        'raw_amount': raw_amount,
                        'rounded_amount': rounded_amount,
                        'fraction': raw_amount - rounded_amount,
                    })

                sum_rounded = sum(entry['rounded_amount'] for entry in allocations)
                diff_cents = int((new_amount - sum_rounded) * 100)
                step = Decimal('0.01')

                if diff_cents > 0:
                    candidates = sorted(
                        [e for e in allocations if e['fraction'] > 0],
                        key=lambda e: e['fraction'],
                        reverse=True,
                    )
                    while diff_cents > 0:
                        adjusted = False
                        for entry in candidates:
                            if entry['rounded_amount'] + step <= entry['base_amount']:
                                entry['rounded_amount'] += step
                                diff_cents -= 1
                                adjusted = True
                                if diff_cents == 0:
                                    break
                        if not adjusted:
                            break
                elif diff_cents < 0:
                    candidates = sorted(
                        [e for e in allocations if e['fraction'] < 0],
                        key=lambda e: e['fraction'],
                    )
                    while diff_cents < 0:
                        adjusted = False
                        for entry in candidates:
                            if entry['rounded_amount'] - step >= 0:
                                entry['rounded_amount'] -= step
                                diff_cents += 1
                                adjusted = True
                                if diff_cents == 0:
                                    break
                        if not adjusted:
                            break

                if diff_cents != 0:
                    for entry in allocations:
                        if diff_cents > 0:
                            if entry['rounded_amount'] + step <= entry['base_amount']:
                                entry['rounded_amount'] += step
                                diff_cents -= 1
                        elif diff_cents < 0:
                            if entry['rounded_amount'] - step >= 0:
                                entry['rounded_amount'] -= step
                                diff_cents += 1
                        if diff_cents == 0:
                            break

                for entry in allocations:
                    item = entry['item']
                    new_item_amount = entry['rounded_amount'].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    item.actual_amount = new_item_amount
                    item.discount_amount = (entry['unit_total'] - new_item_amount).quantize(
                        Decimal('0.01'),
                        rounding=ROUND_HALF_UP,
                    )
                    item.save(update_fields=['actual_amount', 'discount_amount'])

            order.actual_amount = new_amount
            order.discount_amount = (total_amount - new_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            order.save(update_fields=['actual_amount', 'discount_amount', 'updated_at'])

        return Response(OrderSerializer(order).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_orders(self, request):
        """
        获取当前用户的订单列表（分页）
        
        Query Parameters:
            status: 订单状态筛选（可选）
            page: 页码（默认1）
            page_size: 每页数量（默认20）
        
        Returns:
            分页格式的订单列表
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def create_order(self, request):
        """创建订单
        
        Request Body:
            {
                "product_id": 商品ID (必填),
                "address_id": 地址ID (必填),
                "quantity": 数量 (可选，默认1),
                "method": 支付方式 (可选，默认wechat)
            }
        
        Returns:
            {
                "order": 订单信息,
                "payment": 支付信息
            }
        """
        import logging
        logger = logging.getLogger(__name__)

        serializer = OrderCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        target_user = request.user
        user_id_raw = request.data.get('user_id')
        if user_id_raw and (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            try:
                from users.models import User
                target_user = User.objects.get(id=int(user_id_raw))
                logger.info(f'管理员为用户{target_user.id}创建订单')
            except Exception as e:
                logger.error(f'无效的user_id: {user_id_raw}, error: {str(e)}')
                return Response({'detail': 'invalid user_id'}, status=400)

        try:
            with transaction.atomic():
                payment_method = serializer.validated_data.get("payment_method", "online")
                items_payload = serializer.validated_data.get("items")
                if not items_payload and serializer.validated_data.get("product_id"):
                    items_payload = [{
                        'product_id': serializer.validated_data.get("product_id"),
                        'quantity': serializer.validated_data.get("quantity", 1),
                        'sku_id': serializer.validated_data.get("sku_id"),
                    }]

                order = create_order(
                    user=target_user,
                    product_id=serializer.validated_data.get("product_id"),
                    address_id=serializer.validated_data["address_id"],
                    quantity=serializer.validated_data.get("quantity", 1),
                    note=serializer.validated_data.get("note", ""),
                    payment_method=payment_method,
                    items=items_payload,
                )

                logger.info(f'订单创建成功: order_id={order.id}, user_id={target_user.id}, payment_method={payment_method}')

                payment = None
                if payment_method == 'online':
                    payment_method_type = request.data.get('method', 'wechat')
                    payment = Payment.create_for_order(
                        order,
                        method=payment_method_type,
                        ttl_minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES
                    )
                    logger.info(f'支付记录创建成功: payment_id={payment.id}, order_id={order.id}')
                else:
                    logger.info(f'信用支付订单，无需创建支付记录: order_id={order.id}')
        except ValueError as e:
            logger.warning(f'创建订单失败: {str(e)}')
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'创建订单异常: {str(e)}')
            return Response(
                {'detail': f'创建订单失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        order_serializer = OrderSerializer(order)
        pay_serializer = PaymentSerializer(payment) if payment else None

        return Response({
            'order': order_serializer.data, 
            'payment': pay_serializer.data if pay_serializer else None
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def create_batch_orders(self, request):
        """批量创建订单（购物车结算）
        
        Request Body:
            {
                "items": [
                    {"product_id": 1, "quantity": 2},
                    {"product_id": 2, "quantity": 1}
                ],
                "address_id": 地址ID (必填),
                "note": 备注 (可选),
                "payment_method": "online|credit" (可选，默认 online)，用于区分是否走信用支付；
                "method": "wechat|alipay|bank" (可选，默认 wechat)，当 payment_method 为 online 时指定具体在线支付渠道
            }
        
        Returns:
            {
                "orders": [订单信息列表],
                "payments": [支付信息列表]
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        
        items = request.data.get('items', [])
        address_id = request.data.get('address_id')
        note = request.data.get('note', '')
        payment_method = request.data.get('payment_method', 'online')
        online_method = request.data.get('method', 'wechat')
        
        if not items:
            return Response({'detail': '商品列表不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not address_id:
            return Response({'detail': '地址ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        normalized_items = []
        for item in items:
            try:
                pid = int(item.get('product_id'))
                qty = int(item.get('quantity', 1))
                if qty <= 0:
                    return Response({'detail': '商品数量必须大于0'}, status=status.HTTP_400_BAD_REQUEST)
                normalized_items.append({
                    'product_id': pid,
                    'quantity': qty,
                    'sku_id': item.get('sku_id')
                })
            except Exception:
                return Response({'detail': '商品参数无效'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment = None
        
        try:
            with transaction.atomic():
                order = create_order(
                    user=request.user,
                    address_id=address_id,
                    note=note,
                    payment_method=payment_method,
                    items=normalized_items,
                )
                
                # 只有在线支付才创建支付记录
                if payment_method == 'online':
                    payment = Payment.create_for_order(
                        order,
                        method=online_method,
                        ttl_minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES
                    )
                
                logger.info(f'批量订单创建: order_id={order.id}, item_count={len(normalized_items)}')
                
        except ValueError as e:
            logger.warning(f'批量创建订单失败: {str(e)}')
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'批量创建订单异常: {str(e)}')
            return Response(
                {'detail': f'批量创建订单失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        order_data = OrderSerializer(order).data
        payment_data = PaymentSerializer(payment).data if payment else None
        
        return Response({
            'order': order_data,
            'payment': payment_data,
            # 兼容旧结构
            'orders': [order_data],
            'payments': [payment_data] if payment_data else []
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """取消订单：本人或管理员可取消，使用状态机进行状态转换"""
        import logging as pylogging
        logger = pylogging.getLogger(__name__)
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support' or order.user_id == user.id):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from .state_machine import OrderStateMachine
            note = request.data.get('note', '')
            reason = request.data.get('reason', '')
            logger.info('[ORDER_CANCEL] start', extra={'order_id': order.id, 'user_id': user.id, 'reason': reason, 'note': note})
            # YLH 订单取消：先提交请求，等待回调后再做本地状态/退款
            if order.haier_so_id:
                if order.haier_status in ['cancel_pending', 'cancelled']:
                    return Response({"detail": "取消已提交或已完成"}, status=status.HTTP_400_BAD_REQUEST)
                allow_retry_when_cancelled = order.haier_status == 'cancel_failed' and order.status == 'cancelled'
                if not allow_retry_when_cancelled and not (
                    OrderStateMachine.can_transition(order.status, 'cancelled')
                    or OrderStateMachine.can_transition(order.status, 'refunding')
                ):
                    return Response({"detail": "当前状态不允许取消"}, status=status.HTTP_400_BAD_REQUEST)

                if reason:
                    order.cancel_reason = reason
                    order.save(update_fields=['cancel_reason'])

                from integrations.ylhapi import YLHSystemAPI
                ylh_api = YLHSystemAPI.from_settings()
                if not ylh_api.authenticate():
                    return Response({'detail': '易理货系统认证失败，取消不同步'}, status=status.HTTP_502_BAD_GATEWAY)

                result = ylh_api.cancel_order(order.haier_so_id, order.cancel_reason or '', settings.YLH_SOURCE_SYSTEM)
                if not result:
                    return Response({'detail': '推送易理货取消失败'}, status=status.HTTP_502_BAD_GATEWAY)

                order.haier_status = 'cancel_pending'
                order.haier_fail_msg = ''
                order.save(update_fields=['haier_status', 'haier_fail_msg'])
                serializer = self.get_serializer(order)
                resp = serializer.data
                resp.update({'detail': '取消已提交，等待回调'})
                return Response(resp, status=status.HTTP_202_ACCEPTED)

            # 非海尔订单：本地直接取消
            from .cancel_service import cancel_order_local
            result = cancel_order_local(order, operator=user, reason=reason, note=note)
            serializer = self.get_serializer(result['order'])
            resp = serializer.data
            resp.update({
                'refund_started': result['refund_started'],
                'refund_id': result['refund_id'],
                'refund_error': result['refund_error'],
                'refund_channel': result['refund_channel'],
            })
            return Response(resp, status=200)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f'取消订单失败: order_id={order.id}')
            return Response({"detail": f"取消订单失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def ship(self, request, pk=None):
        """发货：仅管理员可操作，状态从 paid 转换到 shipped"""
        logger = logging.getLogger(__name__)
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support'):
            return Response({"detail": "Only admins can ship orders"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from .state_machine import OrderStateMachine
            note = request.data.get('note', '')
            express_company = request.data.get('express_company') or request.data.get('logistics_company_code') or ''
            shipping_list = request.data.get('shipping_list')
            tracking_number = request.data.get('tracking_number') or request.data.get('logistics_no')
            logistics_type = request.data.get('logistics_type')
            delivery_mode = request.data.get('delivery_mode')
            is_all_delivered = request.data.get('is_all_delivered')
            item_desc = request.data.get('item_desc')
            _log_ship_debug(
                logger,
                "ship request received",
                extra={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "delivery_mode": delivery_mode,
                    "logistics_type": logistics_type,
                    "express_company": express_company,
                    "tracking_no": _mask_tracking_no(tracking_number or ''),
                    "shipping_list_len": len(shipping_list) if isinstance(shipping_list, list) else None,
                    "is_all_delivered": is_all_delivered,
                    "has_item_desc": bool(item_desc),
                },
            )
            resolved_logistics_type = int(logistics_type or getattr(settings, 'WECHAT_SHIPPING_LOGISTICS_TYPE', 1) or 1)
            if resolved_logistics_type != 1:
                return Response({"detail": "当前仅支持快递发货（logistics_type=1）"}, status=status.HTTP_400_BAD_REQUEST)
            resolved_delivery_mode = int(delivery_mode or getattr(settings, 'WECHAT_SHIPPING_DELIVERY_MODE', 1) or 1)
            normalized_shipping_list = None
            if shipping_list is not None:
                if not isinstance(shipping_list, list):
                    return Response({"detail": "shipping_list 必须为数组"}, status=status.HTTP_400_BAD_REQUEST)
                if len(shipping_list) == 0:
                    return Response({"detail": "包裹列表不能为空"}, status=status.HTTP_400_BAD_REQUEST)
                if len(shipping_list) > 15:
                    return Response({"detail": "包裹数量不能超过 15 个"}, status=status.HTTP_400_BAD_REQUEST)
                if delivery_mode in (None, ''):
                    resolved_delivery_mode = 2 if len(shipping_list) > 1 else 1
                if resolved_delivery_mode == 1 and len(shipping_list) != 1:
                    return Response({"detail": "统一发货模式仅允许 1 个包裹"}, status=status.HTTP_400_BAD_REQUEST)
                if resolved_delivery_mode == 2 and len(shipping_list) < 2:
                    return Response({"detail": "分拆发货至少需要 2 个包裹"}, status=status.HTTP_400_BAD_REQUEST)

                normalized_shipping_list = []
                for idx, item in enumerate(shipping_list):
                    if not isinstance(item, dict):
                        return Response({"detail": f"包裹 {idx + 1} 格式不正确"}, status=status.HTTP_400_BAD_REQUEST)
                    tracking = item.get('tracking_no') or item.get('logistics_no') or item.get('tracking_number')
                    company = item.get('express_company') or item.get('logistics_company_code') or express_company
                    if not tracking:
                        return Response({"detail": f"包裹 {idx + 1} 缺少物流单号"}, status=status.HTTP_400_BAD_REQUEST)
                    if not company:
                        return Response({"detail": f"包裹 {idx + 1} 缺少物流公司"}, status=status.HTTP_400_BAD_REQUEST)
                    if _contains_chinese(company):
                        return Response({"detail": f"包裹 {idx + 1} 物流公司编码不支持，请使用微信物流公司编码"}, status=status.HTTP_400_BAD_REQUEST)
                    if str(company).upper().startswith('SF') and not (item.get('contact') or getattr(order, 'snapshot_phone', '')):
                        return Response({"detail": "顺丰发货需提供收件人联系方式"}, status=status.HTTP_400_BAD_REQUEST)
                    normalized_item = {
                        'tracking_no': tracking,
                        'express_company': company,
                    }
                    if item.get('item_desc'):
                        normalized_item['item_desc'] = item.get('item_desc')
                    if item.get('contact'):
                        normalized_item['contact'] = item.get('contact')
                    normalized_shipping_list.append(normalized_item)
                if not tracking_number:
                    tracking_number = normalized_shipping_list[0].get('tracking_no')
                if not express_company:
                    express_company = normalized_shipping_list[0].get('express_company')
            else:
                if resolved_delivery_mode == 2:
                    return Response({"detail": "分拆发货必须提供包裹列表"}, status=status.HTTP_400_BAD_REQUEST)
                if not express_company:
                    return Response({"detail": "express_company 为必填"}, status=status.HTTP_400_BAD_REQUEST)
                if _contains_chinese(express_company):
                    return Response({"detail": "物流公司编码不支持，请使用微信物流公司编码"}, status=status.HTTP_400_BAD_REQUEST)
                if str(express_company).upper().startswith('SF') and not getattr(order, 'snapshot_phone', ''):
                    return Response({"detail": "顺丰发货需提供收件人联系方式"}, status=status.HTTP_400_BAD_REQUEST)
                if not tracking_number:
                    return Response({"detail": "tracking_number 或 logistics_no 为必填"}, status=status.HTTP_400_BAD_REQUEST)
            if resolved_delivery_mode == 2 and is_all_delivered is None:
                return Response({"detail": "分拆发货必须提供 is_all_delivered"}, status=status.HTTP_400_BAD_REQUEST)
            wechat_synced = False
            with transaction.atomic():
                order = (
                    Order.objects.select_for_update()
                    .select_related('user')
                    .get(pk=order.id)
                )
                if not OrderStateMachine.can_transition(order.status, 'shipped'):
                    allowed = OrderStateMachine.get_allowed_transitions(order.status)
                    raise ValueError(f'当前状态不允许发货。允许的转换: {allowed}')

                should_sync = (
                    getattr(settings, 'WECHAT_SHIPPING_SYNC_ENABLED', False)
                    and order.payments.filter(status='succeeded', method='wechat').exists()
                )
                _log_ship_debug(
                    logger,
                    "ship sync decision",
                    extra={
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "should_sync": should_sync,
                        "delivery_mode": resolved_delivery_mode,
                        "logistics_type": resolved_logistics_type,
                        "shipping_list_len": len(normalized_shipping_list) if normalized_shipping_list else 1,
                    },
                )
                if should_sync and not getattr(order.user, 'openid', ''):
                    raise _WechatShippingSyncException("openid 缺失，无法同步微信发货信息")

                shipping_info = {
                    'logistics_type': resolved_logistics_type,
                    'delivery_mode': resolved_delivery_mode,
                    'is_all_delivered': bool(is_all_delivered) if resolved_delivery_mode == 2 else None,
                    'shipping_list': normalized_shipping_list or [{
                        'tracking_no': tracking_number,
                        'express_company': express_company,
                        **({'item_desc': item_desc} if item_desc else {}),
                    }],
                }
                order.logistics_no = tracking_number
                order.shipping_info = shipping_info
                order.save(update_fields=['logistics_no', 'shipping_info'])
                order = OrderStateMachine.transition(
                    order,
                    'shipped',
                    operator=user,
                    note=note
                )
                _log_ship_debug(
                    logger,
                    "ship state transition done",
                    extra={
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "status": order.status,
                    },
                )
                if should_sync:
                    try:
                        from .wechat_shipping_service import upload_shipping_info
                        ok, resp, err = upload_shipping_info(
                            order,
                            tracking_no=tracking_number,
                            express_company=express_company,
                            logistics_type=resolved_logistics_type,
                            delivery_mode=resolved_delivery_mode,
                            is_all_delivered=is_all_delivered,
                            item_desc=item_desc,
                            retry_times=2,
                            shipping_list=normalized_shipping_list,
                        )
                        if not ok:
                            logger.warning('wechat shipping sync failed', extra={'order_id': order.id, 'error': err, 'resp': resp})
                            raise _WechatShippingSyncException(_wechat_shipping_error_message(err, resp))
                        wechat_synced = True
                        _log_ship_debug(
                            logger,
                            "wechat shipping sync succeeded",
                            extra={
                                "order_id": order.id,
                                "order_number": order.order_number,
                                "delivery_mode": resolved_delivery_mode,
                                "logistics_type": resolved_logistics_type,
                            },
                        )
                    except _WechatShippingSyncException:
                        raise
                    except Exception:
                        logger.exception('wechat shipping sync failed', extra={'order_id': order.id})
                        raise _WechatShippingSyncException("微信发货同步异常，请稍后重试", status.HTTP_502_BAD_GATEWAY)

                def _send_ship_notification():
                    try:
                        from users.services import create_notification
                        create_notification(
                            order.user,
                            title='订单已发货',
                            content=f'订单 {order.order_number} 已发货，物流单号 {tracking_number}',
                            ntype='order',
                            metadata={
                                'order_id': order.id,
                                'order_number': order.order_number,
                                'logistics_no': tracking_number,
                                'status': 'shipped',
                                'page': f'pages/order-detail/index?id={order.id}',
                                'subscription_data': {
                                    'thing1': {'value': f'订单 {order.order_number}'[:20]},
                                    'time2': {'value': timezone.localtime(order.updated_at).strftime('%Y-%m-%d %H:%M') if order.updated_at else ''},
                                    'thing3': {'value': f'物流单号 {tracking_number}'[:20]},
                                },
                            }
                        )
                    except Exception:
                        pass

                transaction.on_commit(_send_ship_notification)
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=200)
        except _WechatShippingSyncException as e:
            return Response({"detail": e.message}, status=e.status_code)
        except ValueError as e:
            detail = str(e)
            if 'wechat_synced' in locals() and wechat_synced:
                detail = f"{detail}（微信已同步成功，请在微信后台核对订单）"
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            detail = f"发货失败: {str(e)}"
            if 'wechat_synced' in locals() and wechat_synced:
                detail = "发货失败且微信已同步成功，请联系技术处理"
            return Response({"detail": detail}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """完成订单：仅管理员可操作，状态从 shipped 转换到 completed"""
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support'):
            return Response({"detail": "Only admins can complete orders"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from .state_machine import OrderStateMachine
            note = request.data.get('note', '')
            order = OrderStateMachine.transition(
                order,
                'completed',
                operator=user,
                note=note
            )
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=200)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"完成订单失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def confirm_receipt(self, request, pk=None):
        """确认收货：订单所有者或管理员可操作，状态从 shipped 转换到 completed"""
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support' or order.user_id == user.id):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from .state_machine import OrderStateMachine
            note = request.data.get('note', '')
            order = OrderStateMachine.transition(
                order,
                'completed',
                operator=user,
                note=note or '用户确认收货'
            )
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=200)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"确认收货失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def request_invoice(self, request, pk=None):
        """
        申请订单发票（仅订单所有者且订单状态为 completed）。

        请求体：
        {
          "title": 发票抬头,
          "taxpayer_id": 纳税人识别号(可选),
          "email": 接收邮箱(可选),
          "phone": 联系电话(可选),
          "address": 公司地址(可选),
          "bank_account": 开户行及账号(可选),
          "invoice_type": "normal|special"(可选,默认normal),
          "tax_rate": 税率(百分比, 可选, 默认0)
        }

        返回：创建的发票记录
        """
        order = self.get_object()
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support' or order.user_id == request.user.id):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvoiceCreateSerializer(data=request.data, context={'request': request, 'order': order})
        serializer.is_valid(raise_exception=True)
        inv = serializer.save()

        try:
            from common.audit_logger import payment_audit_logger
            payment_audit_logger.info(
                f'Invoice requested: order_id={order.id}, invoice_id={inv.id}, user_id={request.user.id}',
                extra={'event': 'invoice_requested', 'order_id': order.id, 'invoice_id': inv.id, 'user_id': request.user.id}
            )
        except Exception:
            pass

        return Response(InvoiceSerializer(inv).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def request_return(self, request, pk=None):
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support' or order.user_id == user.id):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReturnRequestCreateSerializer(data=request.data, context={'request': request, 'order': order})
        serializer.is_valid(raise_exception=True)
        rr = serializer.save()
        try:
            from users.services import create_notification
            create_notification(
                order.user,
                title='退货申请已提交',
                content=f'订单 {order.order_number} 的退货申请已提交，待客服审核',
                ntype='return',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'return_request_id': rr.id,
                    'status': rr.status,
                    'page': f'pages/order-detail/index?id={order.id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(rr.created_at).strftime('%Y-%m-%d %H:%M') if rr.created_at else ''},
                        'thing3': {'value': '退货申请已提交'},
                    },
                }
            )
        except Exception:
            pass
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def add_return_tracking(self, request, pk=None):
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support' or order.user_id == user.id):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        rr = getattr(order, 'return_request', None)
        if not rr:
            return Response({"detail": "尚未申请退货"}, status=status.HTTP_400_BAD_REQUEST)
        if rr.status != 'approved':
            return Response({"detail": "退货申请尚未审核通过，无法填写物流"}, status=status.HTTP_400_BAD_REQUEST)
        tracking_number = request.data.get('tracking_number') or request.data.get('logistics_no')
        evidence_images = request.data.get('evidence_images') or []
        if not tracking_number:
            return Response({"detail": "tracking_number 或 logistics_no 为必填"}, status=status.HTTP_400_BAD_REQUEST)
        rr.tracking_number = str(tracking_number)
        if isinstance(evidence_images, list) and evidence_images:
            rr.evidence_images = list(set((rr.evidence_images or []) + [str(x) for x in evidence_images if x]))
        rr.status = 'in_transit'
        rr.save()
        try:
            from .state_machine import OrderStateMachine
            if OrderStateMachine.can_transition(order.status, 'returning'):
                OrderStateMachine.transition(order, 'returning', operator=user, note='用户填写退货快递单号')
        except Exception:
            pass
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def approve_return(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        rr = getattr(order, 'return_request', None)
        if not rr:
            return Response({"detail": "尚未申请退货"}, status=status.HTTP_400_BAD_REQUEST)
        if rr.status not in {'requested'}:
            return Response({"detail": "当前状态不可审批"}, status=status.HTTP_400_BAD_REQUEST)
        rr.status = 'approved'
        rr.processed_by = request.user
        rr.processed_note = str(request.data.get('note', '') or '')
        from django.utils import timezone
        rr.processed_at = timezone.now()
        rr.save()
        try:
            from users.services import create_notification
            create_notification(
                order.user,
                title='退货申请已同意',
                content=f'订单 {order.order_number} 的退货申请已同意，请尽快寄回商品',
                ntype='return',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'return_request_id': rr.id,
                    'status': rr.status,
                    'page': f'pages/order-detail/index?id={order.id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(rr.processed_at).strftime('%Y-%m-%d %H:%M') if rr.processed_at else ''},
                        'thing3': {'value': '退货申请已同意'},
                    },
                }
            )
        except Exception:
            pass
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def reject_return(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        rr = getattr(order, 'return_request', None)
        if not rr:
            return Response({"detail": "尚未申请退货"}, status=status.HTTP_400_BAD_REQUEST)
        if rr.status not in {'requested', 'approved'}:
            return Response({"detail": "当前状态不可拒绝"}, status=status.HTTP_400_BAD_REQUEST)
        rr.status = 'rejected'
        rr.processed_by = request.user
        rr.processed_note = str(request.data.get('note', '') or '')
        from django.utils import timezone
        rr.processed_at = timezone.now()
        rr.save()
        try:
            from users.services import create_notification
            create_notification(
                order.user,
                title='退货申请被拒绝',
                content=f'订单 {order.order_number} 的退货申请被拒绝' + (f'，原因：{rr.processed_note}' if rr.processed_note else ''),
                ntype='return',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'return_request_id': rr.id,
                    'status': rr.status,
                    'page': f'pages/order-detail/index?id={order.id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(rr.processed_at).strftime('%Y-%m-%d %H:%M') if rr.processed_at else ''},
                        'thing3': {'value': (rr.processed_note or '退货申请被拒绝')[:20]},
                    },
                }
            )
        except Exception:
            pass
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def receive_return(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        rr = getattr(order, 'return_request', None)
        if not rr:
            return Response({"detail": "尚未申请退货"}, status=status.HTTP_400_BAD_REQUEST)
        rr.status = 'received'
        rr.processed_by = request.user
        rr.processed_note = str(request.data.get('note', '') or '')
        from django.utils import timezone
        rr.processed_at = timezone.now()
        rr.save()
        try:
            from users.services import create_notification
            create_notification(
                order.user,
                title='退货包裹已签收',
                content=f'订单 {order.order_number} 的退货包裹已签收，正在处理退款',
                ntype='return',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'return_request_id': rr.id,
                    'status': rr.status,
                    'page': f'pages/order-detail/index?id={order.id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(rr.processed_at).strftime('%Y-%m-%d %H:%M') if rr.processed_at else ''},
                        'thing3': {'value': '退货包裹已签收'},
                    },
                }
            )
        except Exception:
            pass
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def complete_refund(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        rr = getattr(order, 'return_request', None)
        if not rr:
            return Response({"detail": "尚未申请退货"}, status=status.HTTP_400_BAD_REQUEST)
        from .state_machine import OrderStateMachine

        # 计算可退金额
        refundable = PaymentService.calculate_refundable_amount(order)
        if refundable <= 0:
            return Response({"detail": "暂无可退金额"}, status=status.HTTP_400_BAD_REQUEST)

        refund = None
        refund_err = None
        pay = order.payments.filter(status='succeeded', method='wechat').order_by('-created_at').first()

        if pay:
            reason_text = str(request.data.get('note', '') or request.data.get('reason', '') or '退货退款')
            refund, refund_err = PaymentService.start_order_refund(
                order,
                refundable,
                reason=reason_text,
                operator=request.user,
                payment=pay
            )
            if refund_err:
                return Response({"detail": f"微信退款发起失败: {refund_err}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                if OrderStateMachine.can_transition(order.status, 'refunding'):
                    OrderStateMachine.transition(order, 'refunding', operator=request.user, note='退货退款处理中')
            except Exception:
                pass
            try:
                from users.services import create_notification
                create_notification(
                    order.user,
                    title='退款处理中',
                    content=f'订单 {order.order_number} 退款已提交微信处理，金额 ¥{refundable}',
                    ntype='refund',
                    metadata={
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'refund_id': refund.id if refund else None,
                        'status': 'refunding',
                        'amount': str(refundable),
                        'page': f'pages/order-detail/index?id={order.id}',
                        'subscription_data': {
                            'thing1': {'value': f'订单 {order.order_number}'[:20]},
                            'time2': {'value': timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M')},
                            'thing3': {'value': f'退款金额 ¥{refundable}'[:20]},
                        },
                    }
                )
            except Exception:
                pass
        else:
            if order.payments.filter(status='succeeded').exists():
                return Response({"detail": "当前支付方式暂不支持自动退款，请线下处理"}, status=status.HTTP_400_BAD_REQUEST)
            # 信用账户/线下退款直接完结
            try:
                OrderStateMachine.transition(order, 'refunded', operator=request.user, note=str(request.data.get('note', '') or ''))
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"detail": f"退款完成失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                if not order.payments.exists():
                    from users.credit_services import CreditAccountService
                    if hasattr(order.user, 'credit_account') and order.user.credit_account:
                        CreditAccountService.record_refund(
                            credit_account=order.user.credit_account,
                            amount=getattr(order, 'actual_amount', None) or order.total_amount,
                            order_id=order.id,
                            description=f'退货退款 #{order.order_number}'
                        )
            except Exception:
                pass
            try:
                from users.services import create_notification
                create_notification(
                    order.user,
                    title='退款已完成',
                    content=f'订单 {order.order_number} 退款已完成，金额 ¥{order.actual_amount}',
                    ntype='refund',
                    metadata={
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'status': 'refunded',
                        'amount': str(order.actual_amount),
                        'page': f'pages/order-detail/index?id={order.id}',
                        'subscription_data': {
                            'thing1': {'value': f'订单 {order.order_number}'[:20]},
                            'time2': {'value': timezone.localtime(order.updated_at).strftime('%Y-%m-%d %H:%M') if order.updated_at else ''},
                            'thing3': {'value': f'退款金额 ¥{order.actual_amount}'[:20]},
                        },
                    }
                )
            except Exception:
                pass

        data = {'order': OrderSerializer(order).data}
        if refund:
            data['refund'] = RefundSerializer(refund).data
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def push_to_haier(self, request, pk=None):
        """
        推送订单到海尔系统
        
        仅对海尔产品订单有效，需要管理员权限
        """
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        
        # 检查是否为海尔订单：只根据 product.source 判断
        items = list(order.items.select_related('product').all())
        product = order.product or (items[0].product if items else None)
        from catalog.models import Product as CatalogProduct
        haier_items = [it for it in items if getattr(it.product, 'source', None) == getattr(CatalogProduct, 'SOURCE_HAIER', 'haier')]
        if not haier_items and product:
            if getattr(product, 'source', None) == getattr(CatalogProduct, 'SOURCE_HAIER', 'haier'):
                haier_items = items or [None]
        if not haier_items:
            return Response(
                {'detail': '该订单不是海尔产品订单，无需推送'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if items and len(haier_items) != len(items):
            return Response(
                {'detail': '订单含非海尔商品，暂不支持混合推送'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已推送/处理中
        if order.haier_status in ['push_pending', 'confirmed', 'cancel_pending', 'cancelled'] or (not order.haier_status and order.haier_so_id):
            return Response(
                {'detail': '该订单已推送到海尔系统'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.conf import settings
            import logging
            
            logger = logging.getLogger(__name__)
            
            # 准备订单数据
            source_system = settings.YLH_SOURCE_SYSTEM
            shop_name = settings.YLH_SHOP_NAME
            order_data = order.prepare_haier_order_data(source_system, shop_name)
            
            # 始终使用真实易理货API
            from integrations.ylhapi import YLHSystemAPI
            
            logger.info(f'调用易理货API推送订单: order_id={order.id}')
            
            ylh_api = YLHSystemAPI.from_settings()
            
            # 认证
            if not ylh_api.authenticate():
                logger.error('易理货系统认证失败')
                order.haier_status = 'failed'
                order.haier_fail_msg = '易理货系统认证失败'
                order.save(update_fields=['haier_status', 'haier_fail_msg'])
                return Response(
                    {'detail': '易理货系统认证失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 推送订单
            result = ylh_api.create_order(order_data)
            
            if not result:
                logger.error(f'推送订单失败: order_id={order.id}')
                order.haier_status = 'failed'
                order.haier_fail_msg = '推送订单失败'
                order.save(update_fields=['haier_status', 'haier_fail_msg'])
                return Response(
                    {'detail': '推送订单失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info(f'推送已提交: order_id={order.id}')
            
            order.haier_so_id = order_data['soId']
            order.haier_status = 'push_pending'
            order.haier_fail_msg = ''
            haier_order_no = ''
            if isinstance(result, dict):
                data_section = result.get('data') if isinstance(result.get('data', None), dict) else result
                if isinstance(data_section, dict):
                    haier_order_no = data_section.get('retailOrderNo', '') or data_section.get('retail_order_no', '')
            order.haier_order_no = haier_order_no
            order.save(update_fields=['haier_so_id', 'haier_status', 'haier_fail_msg', 'haier_order_no'])

            # 自动变更为已发货
            try:
                from .state_machine import OrderStateMachine
                if OrderStateMachine.can_transition(order.status, 'shipped'):
                    OrderStateMachine.transition(
                        order, 
                        'shipped', 
                        operator=request.user, 
                        note=f'海尔订单推送成功，自动发货。海尔单号: {haier_order_no or order.haier_so_id}'
                    )
            except Exception as e:
                logger.warning(f'海尔订单自动发货失败: {str(e)}')
            
            serializer = self.get_serializer(order)
            return Response({
                'detail': '订单已提交，等待回调确认',
                'order': serializer.data,
                'haier_response': result,
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'推送海尔订单失败: {str(e)}')
            try:
                order.haier_status = 'failed'
                order.haier_fail_msg = f'推送失败: {str(e)}'
                order.save(update_fields=['haier_status', 'haier_fail_msg'])
            except Exception:
                logger.exception('更新海尔推送失败状态异常')
            return Response(
                {'detail': f'推送失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def haier_logistics(self, request, pk=None):
        """
        查询海尔订单物流信息
        
        仅对已推送的海尔订单有效
        """
        order = self.get_object()
        
        # 检查权限
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support') and order.user != request.user:
            return Response(
                {'detail': '无权查看该订单'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 检查是否为海尔订单（已推送）
        if not order.haier_so_id:
            return Response(
                {'detail': '该订单未推送到海尔系统'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from integrations.ylhapi import YLHSystemAPI
            from django.conf import settings
            
            ylh_api = YLHSystemAPI.from_settings()
            
            # 认证
            if not ylh_api.authenticate():
                return Response(
                    {'detail': '易理货系统认证失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            code = order.haier_order_no or order.haier_so_id
            logistics_info = ylh_api.get_logistics_by_order_codes([code])
            
            if not logistics_info:
                return Response({'detail': '查询物流失败'}, status=status.HTTP_502_BAD_GATEWAY)
            
            return Response({
                'detail': '查询成功',
                'logistics_info': logistics_info,
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'查询海尔物流失败: {str(e)}')
            return Response(
                {'detail': f'查询失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False,methods=['get'])
    def my_cart(self,request):
        cart = get_or_create_cart(request.user)
        # Optimize cart query by prefetching related products
        from .models import CartItem
        cart.items.all().select_related('product', 'product__category', 'product__brand', 'sku')
        # 传入请求上下文以便 ProductSerializer 计算 discounted_price
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False,methods=['post'])
    def add_item(self,request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        sku_id = request.data.get('sku_id')
        
        if not product_id:
            return Response({"detail": "product_id is required"}, status=400)
        try:
            sku_id = int(sku_id) if sku_id not in (None, '', False) else None
        except (TypeError, ValueError):
            return Response({"detail": "sku_id is invalid"}, status=400)
        
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"detail": "quantity must be integer"}, status=400)
        
        if quantity <= 0:
            return Response({"detail": "quantity must be positive"}, status=400)
        
        try:
            add_to_cart(request.user, product_id, quantity, sku_id=sku_id)
            cart = get_or_create_cart(request.user)
            serializer = CartSerializer(cart, context={'request': request})
            return Response(serializer.data, status=201)
        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=404)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """移除购物车商品"""
        product_id = request.data.get('product_id')
        sku_id = request.data.get('sku_id')
        
        if not product_id:
            return Response({"detail": "product_id is required"}, status=400)
        try:
            sku_id = int(sku_id) if sku_id not in (None, '', False) else None
        except (TypeError, ValueError):
            return Response({"detail": "sku_id is invalid"}, status=400)
        
        try:
            remove_from_cart(request.user, product_id, sku_id=sku_id)
            cart = get_or_create_cart(request.user)
            serializer = CartSerializer(cart, context={'request': request})
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """设置某商品的精确数量（不存在则创建）"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[购物车更新] Content-Type: {request.content_type}")
        logger.info(f"[购物车更新] request.data: {request.data}")
        
        product_id = request.data.get('product_id')
        quantity_raw = request.data.get('quantity', 1)
        sku_id = request.data.get('sku_id')
        try:
            sku_id = int(sku_id) if sku_id not in (None, '', False) else None
        except (TypeError, ValueError):
            return Response({"detail": "sku_id is invalid"}, status=400)
        
        if not product_id:
            logger.error(f"[购物车更新] 缺少 product_id, request.data={request.data}")
            return Response({"detail": "product_id is required"}, status=400)
        
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError) as e:
            logger.error(f"[购物车更新] 数量转换失败: quantity_raw={quantity_raw}, error={e}")
            return Response({"detail": f"quantity must be integer, got: {quantity_raw}"}, status=400)
        
        if quantity <= 0:
            remove_from_cart(request.user, product_id, sku_id=sku_id)
            return Response({"detail": "Item removed"}, status=200)

        try:
            cart = get_or_create_cart(request.user)
            from .models import CartItem
            product = Product.objects.get(id=product_id)
            sku = None
            stock_to_check = product.stock
            if sku_id:
                from catalog.models import ProductSKU
                sku = ProductSKU.objects.get(id=sku_id, product=product)
                stock_to_check = sku.stock
            
            if quantity > stock_to_check:
                logger.warning(f"[购物车更新] 库存不足: quantity={quantity}, stock={stock_to_check}")
                return Response({
                    "detail": f"库存不足，当前库存: {stock_to_check}"
                }, status=400)
            
            item, created = CartItem.objects.get_or_create(cart=cart, product=product, sku=sku)
            item.quantity = quantity
            item.save()
            logger.info(f"[购物车更新] 更新成功: item_id={item.id}, quantity={quantity}, created={created}")
            
            serializer = CartSerializer(cart, context={'request': request})
            return Response(serializer.data, status=200)
        except Product.DoesNotExist:
            logger.error(f"[购物车更新] 商品不存在: product_id={product_id}")
            return Response({"detail": "商品不存在"}, status=404)
        except Exception as e:
            logger.error(f"[购物车更新] 更新失败: {str(e)}", exc_info=True)
            return Response({"detail": str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """清空购物车"""
        try:
            cart = get_or_create_cart(request.user)
            from .models import CartItem
            CartItem.objects.filter(cart=cart).delete()
            serializer = CartSerializer(cart, context={'request': request})
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


@extend_schema(tags=['Payments'])
class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.
    
    Permissions:
    - IsOwnerOrAdmin: Users can only access payments for their own orders, admins can access all
    
    Throttling:
    - PaymentRateThrottle: Stricter rate limiting (10 requests/minute) to prevent abuse
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsOwnerOrAdmin]
    throttle_classes = [PaymentRateThrottle]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.filter(order__user=user) if not user.is_staff else Payment.objects.all()
        
        # Optimize queries by prefetching related order data
        qs = qs.select_related('order', 'order__user', 'order__product').prefetch_related('order__items__product', 'order__items__sku')
        
        from common.utils import parse_int
        order_id = self.request.query_params.get('order_id')
        if order_id:
            oid = parse_int(order_id)
            if oid is not None:
                qs = qs.filter(order_id=oid)
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """为指定订单创建新的支付记录
        
        验证订单状态和金额一致性，添加支付金额验证，提供明确的错误信息。
        
        Request body:
        {
            "order_id": 123,
            "method": "wechat",  # 可选，默认为wechat
            "amount": "100.00"   # 可选，如果提供则验证与订单金额一致
        }
        
        Returns:
            201: 支付记录创建成功
            400: 参数验证失败
            404: 订单不存在
            409: 订单状态不允许支付
        """
        from .payment_service import PaymentService
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 验证order_id参数
        from common.utils import parse_int, parse_decimal
        order_id = parse_int(request.data.get('order_id'))
        if order_id is None:
            logger.warning(f'无效的order_id: {request.data.get("order_id")}')
            return Response(
                {'detail': 'order_id is required and must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取支付方式
        method = request.data.get('method', 'wechat')
        if method not in ['wechat', 'alipay', 'bank']:
            logger.warning(f'不支持的支付方式: {method}')
            return Response(
                {'detail': f'Unsupported payment method: {method}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 查找订单
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            logger.warning(f'订单不存在: order_id={order_id}, user_id={request.user.id}')
            return Response(
                {'detail': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        payable_amount = order.actual_amount or order.total_amount
        
        # 验证支付金额（如果提供）
        payment_amount = request.data.get('amount')
        if payment_amount is not None:
            parsed_amount = parse_decimal(payment_amount)
            if parsed_amount is None:
                logger.error('金额验证异常: invalid decimal')
                return Response(
                    {'detail': 'Invalid payment amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not PaymentService.check_payment_amount(order, parsed_amount):
                logger.warning(
                    f'支付金额不匹配: order_id={order_id}, '
                    f'order_amount={payable_amount}, '
                    f'payment_amount={parsed_amount}'
                )
                return Response(
                    {
                        'detail': f'Payment amount {parsed_amount} does not match order amount {payable_amount}',
                        'order_amount': str(payable_amount),
                        'payment_amount': str(parsed_amount)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 验证订单状态和金额一致性
        is_valid, error_msg = PaymentService.validate_payment_creation(order, payment_amount)
        if not is_valid:
            logger.warning(f'订单验证失败: order_id={order_id}, error={error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_409_CONFLICT
            )
        
        # 检查是否已存在未过期的支付记录
        existing_payment = Payment.objects.filter(
            order=order,
            status__in=['init', 'processing']
        ).order_by('-created_at').first()
        
        if existing_payment and timezone.now() < existing_payment.expires_at:
            logger.info(f'已存在未过期的支付记录: payment_id={existing_payment.id}')
            serializer = self.get_serializer(existing_payment)
            return Response(
                {
                    'detail': 'An active payment record already exists for this order',
                    'payment': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        # 创建支付记录
        try:
            payment = Payment.create_for_order(order, method=method, ttl_minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES)
            
            # 记录支付创建事件
            PaymentService.log_payment_event(
                payment.id,
                'payment_created',
                details={
                    'method': method,
                    'amount': str(payable_amount),
                    'user_id': request.user.id
                }
            )
            
            logger.info(f'支付记录已创建: payment_id={payment.id}, order_id={order_id}')
            serializer = self.get_serializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f'创建支付记录失败: {str(e)}')
            return Response(
                {'detail': f'Failed to create payment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        payment = self.get_object()
        from .payment_service import PaymentService
        from .models import Order
        import logging
        logger = logging.getLogger(__name__)

        ok, reason = PaymentService.ensure_payment_startable(payment)
        if not ok:
            # 如果因过期导致不可用，更新状态
            if '过期' in reason:
                payment.status = 'expired'
                payment.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'expired_before_start'
                })
                payment.save(update_fields=['status', 'logs', 'updated_at'])
            return Response({'detail': reason}, status=status.HTTP_400_BAD_REQUEST)

        provider = request.data.get('provider') or payment.method

        ok_freq, msg_freq = PaymentService.check_user_payment_frequency(request.user)
        if not ok_freq:
            log_security('pay_freq_user', msg_freq, {'user_id': request.user.id if request.user else None})
            return Response({'detail': msg_freq}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # 设备/IP 限频
        client_ip = PaymentService.extract_client_ip(request)
        device_id = request.META.get('HTTP_X_DEVICE_ID', '')
        ok_cli, msg_cli = PaymentService.check_client_frequency(request.user, client_ip=client_ip, device_id=device_id)
        if not ok_cli:
            log_security('pay_freq_client', msg_cli, {'user_id': request.user.id if request.user else None, 'ip': client_ip, 'device_id': device_id})
            return Response({'detail': msg_cli}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # 仅待支付订单可启动支付
        if payment.order.status not in ['pending', 'paid']:
            return Response({'detail': '订单状态不支持支付'}, status=status.HTTP_409_CONFLICT)
        if not request.user.is_staff and payment.order.user_id != request.user.id:
            return Response({'detail': '无权支付该订单'}, status=status.HTTP_403_FORBIDDEN)

        # 金额阈值校验
        ok_amount, msg_amount = PaymentService.check_amount_threshold(payment.order)
        if not ok_amount:
            log_security('pay_amount_exceeded', msg_amount, {'user_id': request.user.id if request.user else None, 'order_id': payment.order_id})
            return Response({'detail': msg_amount}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = 'processing'
        payment.logs.append({
            't': timezone.now().isoformat(),
            'event': 'start',
            'detail': f'user starts {provider} payment'
        })
        payment.save(update_fields=['status', 'logs', 'updated_at'])

        pay_params = None
        if provider == 'wechat':
            openid = getattr(request.user, 'openid', '') or request.data.get('openid') or ''
            if not openid:
                payment.status = 'init'
                payment.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'detail': 'missing_openid'
                })
                payment.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': '缺少 openid，无法发起微信支付'}, status=status.HTTP_400_BAD_REQUEST)
            client_ip = PaymentService.extract_client_ip(request)
            try:
                pay_params = PaymentService.create_wechat_unified_order(payment, openid=openid, client_ip=client_ip)
            except Exception as exc:
                logger.exception('微信统一下单失败', extra={'payment_id': payment.id, 'order_id': payment.order_id})
                payment.status = 'init'
                payment.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'detail': f'wechat_order_error: {exc}'
                })
                payment.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': f'微信支付下单失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if not pay_params:
                payment.status = 'init'
                payment.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'detail': 'wechat_pay_params_empty'
                })
                payment.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': '微信支付未正确配置或下单失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # 确保前端可以拿到金额字段（微信JSAPI报 total_fee 缺失时兜底用）
            try:
                cents = int((Decimal(payment.amount) * 100).quantize(Decimal('1')))
                pay_params.setdefault('total_fee', cents)
                pay_params.setdefault('total', cents)
                pay_params.setdefault('amount', str(payment.amount))
                pay_params.setdefault('payment_id', payment.id)
                pay_params.setdefault('order_number', payment.order.order_number)
            except Exception:
                pass

        serializer_data = self.get_serializer(payment).data
        return Response({
            'payment': serializer_data,
            'pay_params': pay_params
        })

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """主动查询微信支付结果并同步支付/订单状态。"""
        payment = self.get_object()
        if not request.user.is_staff and payment.order.user_id != request.user.id:
            return Response({'detail': '无权查询该支付'}, status=status.HTTP_403_FORBIDDEN)

        try:
            result = PaymentService.query_wechat_transaction(payment)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        trade_state = result.get('trade_state')
        transaction_id = result.get('transaction_id')
        amount_total = result.get('amount', {}).get('total')
        try:
            amount_decimal = (Decimal(str(amount_total)) / Decimal('100')) if amount_total is not None else None
        except Exception:
            amount_decimal = None
        if amount_decimal is not None and amount_decimal != payment.amount:
            return Response({'detail': '查单金额与支付记录不一致'}, status=status.HTTP_400_BAD_REQUEST)

        if trade_state == 'SUCCESS' and payment.status != 'succeeded':
            PaymentService.process_payment_success(payment.id, transaction_id=transaction_id, operator=request.user)
        elif trade_state in {'CLOSED', 'REVOKED'} and payment.status not in ['succeeded', 'cancelled']:
            payment.status = 'cancelled'
            payment.save(update_fields=['status', 'updated_at'])

        return Response({
            'payment': self.get_serializer(payment).data,
            'trade_state': trade_state,
            'transaction': result
        })

@extend_schema(tags=['Payments'])
class RefundCallbackView(APIView):
    """微信退款回调处理视图。"""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PaymentRateThrottle]

    def post(self, request, provider: str = 'wechat'):
        provider = (provider or 'wechat').lower()
        if provider != 'wechat':
            return Response({'detail': 'unsupported provider'}, status=400)

        parsed, err = PaymentService.parse_wechat_refund_callback(request)
        if err:
            logger = logging.getLogger(__name__)
            logger.error(f'微信退款回调解析失败: {err}')
            return Response({'code': 'FAIL', 'message': err}, status=status.HTTP_400_BAD_REQUEST)

        refund = parsed['refund']
        if refund.status == 'succeeded':
            return Response({'code': 'SUCCESS', 'message': 'OK'})
        refund_status = str(parsed.get('refund_status') or '').upper()
        transaction_id = parsed.get('transaction_id')

        if refund_status == 'SUCCESS':
            try:
                PaymentService.process_refund_success(refund.id, transaction_id=transaction_id)
            except Exception as exc:
                return Response({'code': 'FAIL', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif refund_status in {'CLOSED', 'ABNORMAL'}:
            refund.status = 'failed'
            refund.logs.append({
                't': timezone.now().isoformat(),
                'event': 'refund_failed',
                'reason': refund_status
            })
            refund.save(update_fields=['status', 'logs', 'updated_at'])

        return Response({'code': 'SUCCESS', 'message': '成功'})

@extend_schema(tags=['Discounts'])
class DiscountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing discounts.
    
    Permissions:
    - IsAdmin: Only administrators can manage discounts
    """
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            with transaction.atomic():
                instance.targets.all().delete()
                instance.delete()
        except ProtectedError:
            return Response(
                {
                    'error': '无法删除折扣',
                    'message': '该折扣被其他数据引用，无法删除',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        # 折扣管理仅管理员可见；普通用户仅能查看与自己相关的折扣（用于调试），实际前端不暴露列表
        user = self.request.user
        if user.is_staff:
            qs = Discount.objects.prefetch_related('targets', 'targets__product').all()
            # 名称模糊搜索
            name = self.request.query_params.get('name')
            if name:
                qs = qs.filter(name__icontains=name)
            # 优先级筛选（精确匹配）
            priority = self.request.query_params.get('priority')
            if priority is not None:
                p = parse_int(priority)
                if p is not None:
                    try:
                        qs = qs.filter(priority=p)
                    except Exception:
                        pass
            # 时间范围过滤：effective_before/after, expiration_before/after
            eff_after = self.request.query_params.get('effective_after')
            eff_before = self.request.query_params.get('effective_before')
            exp_after = self.request.query_params.get('expiration_after')
            exp_before = self.request.query_params.get('expiration_before')
            if eff_after:
                dt = parse_datetime(eff_after)
                if dt:
                    try:
                        qs = qs.filter(effective_time__gte=dt)
                    except Exception:
                        pass
            if eff_before:
                dt = parse_datetime(eff_before)
                if dt:
                    try:
                        qs = qs.filter(effective_time__lte=dt)
                    except Exception:
                        pass
            if exp_after:
                dt = parse_datetime(exp_after)
                if dt:
                    try:
                        qs = qs.filter(expiration_time__gte=dt)
                    except Exception:
                        pass
            if exp_before:
                dt = parse_datetime(exp_before)
                if dt:
                    try:
                        qs = qs.filter(expiration_time__lte=dt)
                    except Exception:
                        pass
            return qs.order_by('-priority', '-updated_at')
        # 非管理员：只返回与该用户相关的折扣
        return Discount.objects.filter(targets__user=user).distinct().order_by('-priority')

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset()).prefetch_related('targets')
        headers = [
            '名称',
            '折扣类型',
            '折扣值',
            '生效时间',
            '过期时间',
            '优先级',
            '用户数',
            '商品数',
            '状态',
        ]
        rows = []
        now = timezone.now()
        for discount in qs:
            targets = list(discount.targets.all())
            user_ids = {t.user_id for t in targets if t.user_id}
            product_ids = {t.product_id for t in targets if t.product_id}
            is_active = discount.effective_time <= now < discount.expiration_time
            rows.append([
                discount.name,
                discount.get_discount_type_display(),
                discount.amount,
                discount.effective_time,
                discount.expiration_time,
                discount.priority,
                len(user_ids),
                len(product_ids),
                '生效中' if is_active else '已失效',
            ])
        filename = f"discounts_export_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="折扣导出")

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def batch_set(self, request):
        """批量为指定用户设置一组商品的统一折扣金额与时间窗。
        输入: { user_id, product_ids:[], amount, discount_type, effective_time, expiration_time, priority }
        返回: 创建/更新的目标数量
        """
        try:
            user_id = int(request.data.get('user_id'))
            product_ids = request.data.get('product_ids') or []
            amount = request.data.get('amount')
            discount_type = request.data.get('discount_type', Discount.TYPE_AMOUNT)
            effective_time = request.data.get('effective_time')
            expiration_time = request.data.get('expiration_time')
            priority = int(request.data.get('priority', 0))
        except Exception:
            return Response({'detail': '参数不合法'}, status=400)
        if not product_ids or amount is None or not effective_time or not expiration_time:
            return Response({'detail': '缺少必要参数'}, status=400)
        if discount_type not in {Discount.TYPE_AMOUNT, Discount.TYPE_PERCENT}:
            return Response({'detail': '折扣类型不合法'}, status=400)
        if discount_type == Discount.TYPE_PERCENT:
            try:
                amount_val = float(amount)
            except Exception:
                return Response({'detail': '折扣率不合法'}, status=400)
            if amount_val <= 0 or amount_val > 10:
                return Response({'detail': '折扣率需在 0 到 10 之间'}, status=400)

        # 创建折扣规则
        disc = Discount.objects.create(
            name=request.data.get('name', ''),
            amount=amount,
            discount_type=discount_type,
            effective_time=effective_time,
            expiration_time=expiration_time,
            priority=priority,
        )
        # 建立目标关系
        created = 0
        for pid in product_ids:
            try:
                DiscountTarget.objects.create(discount=disc, user_id=user_id, product_id=int(pid))
                created += 1
            except Exception:
                # unique 冲突忽略
                pass
        return Response({'discount_id': disc.id, 'created_targets': created}, status=201)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def query_user_products(self, request):
        """批量查询当前用户在一组商品上的有效折扣，返回字典 {product_id: {amount, discount_id, discount_type, discount_value}}。
        性能：限制商品ID数量，并做索引查询；后续将配合缓存。
        """
        from common.utils import parse_csv_ints
        prod_ids = request.query_params.get('product_ids', '')
        ids = parse_csv_ints(prod_ids)
        if not ids:
            return Response({})

        now = timezone.now()
        # 优先级排序选择一个最优折扣（最高优先级）；若同优先级按更新时间
        qs = DiscountTarget.objects.select_related('discount', 'product').filter(
            user=request.user,
            product_id__in=ids,
            discount__effective_time__lte=now,
            discount__expiration_time__gt=now,
        ).order_by('-discount__priority', '-discount__updated_at')

        result: dict[int, dict] = {}
        for dt in qs:
            pid = dt.product_id
            if pid in result:
                continue
            base_price = resolve_base_price(request.user, dt.product)
            amount = dt.discount.resolve_discount_amount(base_price)
            result[pid] = {
                'amount': float(amount),
                'discount_id': dt.discount_id,
                'discount_type': dt.discount.discount_type,
                'discount_value': float(dt.discount.amount),
            }
        return Response(result)


@extend_schema(tags=['Invoices'])
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        is_admin = user.is_staff or getattr(user, 'role', '') == 'support'
        qs = Invoice.objects.all() if is_admin else Invoice.objects.filter(user=user)
        qs = qs.select_related('order', 'user', 'order__product').order_by('-requested_at')

        order_number = self.request.query_params.get('order_number')
        if order_number:
            qs = qs.filter(order__order_number__icontains=order_number)

        title = self.request.query_params.get('title')
        if title:
            qs = qs.filter(title__icontains=title)

        invoice_type = self.request.query_params.get('invoice_type')
        if invoice_type:
            qs = qs.filter(invoice_type=invoice_type)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        if is_admin:
            username = self.request.query_params.get('username')
            if username:
                qs = qs.filter(user__username__icontains=username)
        return qs

    @action(detail=False, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        headers = [
            'ID',
            '订单号',
            '用户名',
            '发票抬头',
            '类型',
            '金额',
            '状态',
            '发票号码',
            '申请时间',
            '开具时间',
        ]
        rows = []
        for inv in qs:
            rows.append([
                inv.id,
                inv.order.order_number if inv.order else '',
                getattr(inv.user, 'username', ''),
                inv.title,
                inv.get_invoice_type_display(),
                inv.amount,
                inv.get_status_display(),
                inv.invoice_number,
                inv.requested_at,
                inv.issued_at,
            ])
        filename = f"invoices_export_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="发票导出")

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def issue(self, request, pk=None):
        # Support staff should be able to issue invoices
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
             return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        inv = self.get_object()
        if inv.status == 'issued':
            return Response({'detail': '发票已开具'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice_number = str(request.data.get('invoice_number', '')).strip()
        
        if not invoice_number:
            return Response({'detail': 'invoice_number 必填'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle optional file upload directly in issue
        file = request.FILES.get('file')
        if file:
            try:
                PDFOrImageFileValidator()(file)
            except serializers.ValidationError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            inv.file = file
        
        inv.invoice_number = invoice_number
        inv.status = 'issued'
        inv.issued_at = timezone.now()
        inv.save()

        return Response(self.get_serializer(inv).data)

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def cancel(self, request, pk=None):
        # Support staff should be able to cancel invoices
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
             return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        inv = self.get_object()
        if inv.status == 'issued':
            return Response({'detail': '已开具发票不可取消'}, status=status.HTTP_400_BAD_REQUEST)
        inv.status = 'cancelled'
        inv.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(inv).data)

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def upload_file(self, request, pk=None):
        """上传发票文件（PDF/图片），管理员或客服。"""
        # Support staff should be able to upload invoice files
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
             return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        inv = self.get_object()
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '缺少文件参数 file'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            PDFOrImageFileValidator()(file)
        except serializers.ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        inv.file = file
        inv.save()
        return Response(self.get_serializer(inv).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def download(self, request, pk=None):
        """下载发票文件，订单所有者或管理员或客服可访问。"""
        # Support staff should be able to download invoice files
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support' or self.get_object().user_id == request.user.id):
             return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        inv = self.get_object()
        # 优先使用 FileField
        if getattr(inv, 'file', None):
            f = inv.file
            try:
                # Determine filename
                name = getattr(f, 'name', 'invoice')
                filename = name.split('/')[-1] or 'invoice'
                resp = FileResponse(f.open('rb'))
                resp['Content-Disposition'] = f'attachment; filename="{filename}"'
                return resp
            except Exception as e:
                return Response({'detail': f'文件读取失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': '未找到发票文件'}, status=status.HTTP_404_NOT_FOUND)



@extend_schema(tags=['Payments'])
class PaymentCallbackView(APIView):
    """支付回调处理视图（微信支付）。"""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PaymentRateThrottle]

    def post(self, request, provider: str = 'wechat'):
        """处理支付回调
        
        Args:
            request: HTTP请求对象
            provider: 支付提供商（目前仅微信）
            
        Returns:
            Response: 支付记录序列化数据或错误信息
        """
        from .payment_service import PaymentService
        import logging
        
        logger = logging.getLogger(__name__)
        provider = (provider or 'wechat').lower()
        if provider != 'wechat':
            return Response({'detail': 'unsupported provider'}, status=400)

        raw_body = ''
        try:
            raw_body = request.body.decode('utf-8')
        except Exception:
            raw_body = ''
        logger.info(f'收到支付回调: provider={provider}, body={raw_body or request.data}')

        payment = None
        status_param = None
        transaction_id = None
        callback_amount = None
        validation_data = None
        data = request.data or {}

        parsed, err = PaymentService.parse_wechat_callback(request)
        if err:
            logger.error(f'微信回调解析失败: {err}')
            return Response({'code': 'FAIL', 'message': err}, status=status.HTTP_400_BAD_REQUEST)
        payment = parsed['payment']
        status_param = parsed.get('trade_state')
        transaction_id = parsed.get('transaction_id')
        callback_amount = parsed.get('amount_decimal')
        validation_data = {'amount': parsed.get('amount_decimal')}
        data = parsed.get('transaction') or {}
        PaymentService.log_payment_event(
            payment.id,
            'signature_verified',
            details={'provider': provider, 'channel': 'wechat_v3'}
        )

        # 防止重复处理已成功的支付
        if payment.status == 'succeeded':
            logger.warning(f'支付记录已处理过: payment_id={payment.id}')
            PaymentService.log_payment_event(
                payment.id,
                'duplicate_callback_ignored',
                details={'provider': provider}
            )
            return Response({'code': 'SUCCESS', 'message': 'OK', 'payment_id': payment.id})
        if payment.status in ['cancelled', 'expired', 'failed']:
            logger.warning(f'回调被拒绝，支付状态不允许更新: payment_id={payment.id}, status={payment.status}')
            PaymentService.log_payment_event(
                payment.id,
                'callback_rejected_by_status',
                details={'provider': provider, 'status': payment.status}
            )
            return Response({'code': 'SUCCESS', 'message': '支付状态不可更新', 'payment_id': payment.id})

        # 验证回调金额与支付单一致
        ok_amount, reason_amount = PaymentService.validate_callback_amount(payment, validation_data)
        if not ok_amount:
            logger.error(f'回调金额校验失败: payment_id={payment.id}, reason={reason_amount}')
            PaymentService.log_payment_event(
                payment.id,
                'callback_amount_mismatch',
                details={'provider': provider},
                error=reason_amount
            )
            return Response({'detail': reason_amount}, status=400)

        # 提取回调数据
        status_param = status_param or data.get('status') or data.get('result_code') or data.get('trade_state')
        transaction_id = transaction_id or data.get('transaction_id') or data.get('wx_transaction_id') or data.get('trans_id')
        callback_amount = callback_amount or data.get('total_fee') or data.get('amount') or data.get('total')

        # 映射支付状态
        new_status = self._map_payment_status(provider, status_param)

        # 使用事务处理支付状态更新
        try:
            with transaction.atomic():
                # 锁定支付记录，避免并发回调穿透
                from .models import Payment
                payment = Payment.objects.select_for_update().get(id=payment.id)

                # 处理支付成功
                if new_status == 'succeeded' and payment.status in ['init', 'processing']:
                    # 再次金额阈值/一致性校验
                    ok_amount, reason_amt = PaymentService.check_amount_threshold(payment.order)
                    if not ok_amount:
                        raise ValueError(reason_amt)
                    if callback_amount:
                        try:
                            cb_amount = Decimal(str(callback_amount))
                        except Exception:
                            cb_amount = None
                        if cb_amount is not None and cb_amount != payment.amount:
                            log_security('callback_amount_mismatch', '回调金额不一致', {'payment_id': payment.id, 'order_id': payment.order_id})
                            raise ValueError('回调金额与支付单不一致')

                    PaymentService.process_payment_success(
                        payment.id,
                        transaction_id=transaction_id,
                        operator=None
                    )
                    # refresh local status to avoid后续误覆盖
                    payment.status = 'succeeded'
                    logger.info(f'支付成功处理: payment_id={payment.id}, transaction_id={transaction_id}')

                # 处理支付失败
                elif new_status == 'failed' and payment.status not in ['cancelled', 'expired']:
                    payment.status = 'failed'
                    PaymentService.log_payment_event(
                        payment.id,
                        'payment_failed',
                        details={'provider': provider, 'reason': status_param}
                    )
                    payment.save()
                    logger.warning(f'支付失败: payment_id={payment.id}')

                # 处理支付取消
                elif new_status == 'cancelled' and payment.status not in ['cancelled', 'expired']:
                    payment.status = 'cancelled'
                    PaymentService.log_payment_event(
                        payment.id,
                        'payment_cancelled',
                        details={'provider': provider}
                    )
                    payment.save()
                    logger.info(f'支付已取消: payment_id={payment.id}')

                # 处理支付过期
                elif new_status == 'expired' and payment.status != 'expired':
                    payment.status = 'expired'
                    # 使用状态机更新订单状态
                    try:
                        from .state_machine import OrderStateMachine
                        OrderStateMachine.transition(
                            payment.order,
                            'cancelled',
                            operator=None,
                            note='Payment expired'
                        )
                    except ValueError as e:
                        logger.error(f'订单状态转换失败: {str(e)}')
                        payment.order.status = 'cancelled'
                        payment.order.save()

                    try:
                        from users.services import create_notification
                        create_notification(
                            payment.order.user,
                            title='支付已过期',
                            content=f'订单 {payment.order.order_number} 支付已过期，请重新下单或再次支付',
                            ntype='payment',
                            metadata={
                                'order_id': payment.order_id,
                                'payment_id': payment.id,
                                'order_number': payment.order.order_number,
                                'page': f'pages/order-detail/index?id={payment.order_id}',
                                'subscription_data': {
                                    'thing1': {'value': f'订单 {payment.order.order_number}'[:20]},
                                    'time2': {'value': timezone.localtime(payment.expires_at).strftime('%Y-%m-%d %H:%M') if payment.expires_at else ''},
                                    'thing3': {'value': '支付已过期'},
                                },
                            }
                        )
                    except Exception:
                        pass
                    
                    PaymentService.log_payment_event(
                        payment.id,
                        'payment_expired',
                        details={'provider': provider}
                    )
                    payment.save()
                    logger.info(f'支付已过期: payment_id={payment.id}')
                
                # 处理支付处理中
                else:
                    payment.status = 'processing'
                    PaymentService.log_payment_event(
                        payment.id,
                        'payment_processing',
                        details={'provider': provider}
                    )
                    payment.save()
                    logger.info(f'支付处理中: payment_id={payment.id}')
        
        except Exception as e:
            logger.error(f'处理支付回调异常: {str(e)}')
            PaymentService.log_payment_event(
                payment.id,
                'callback_processing_error',
                details={'provider': provider},
                error=str(e)
            )
            return Response({'detail': 'callback processing failed'}, status=500)

        return Response({'code': 'SUCCESS', 'message': '成功', 'payment_id': payment.id})

    @staticmethod
    def _map_payment_status(provider: str, status_param: str) -> str:
        """映射支付状态"""
        if provider == 'wechat':
            val = str(status_param).upper() if status_param else ''
            if val == 'SUCCESS':
                return 'succeeded'
            if val in {'CLOSED', 'REVOKED'}:
                return 'cancelled'
            if val in {'USERPAYING', 'NOTPAY', 'ACCEPT'}:
                return 'processing'
            return 'failed'
        if provider == 'alipay':
            val = str(status_param).lower() if status_param else ''
            if val == 'trade_success':
                return 'succeeded'
            if val == 'trade_closed':
                return 'cancelled'
            return 'failed'
        return 'processing'


@extend_schema(tags=['Refunds'])
class RefundViewSet(viewsets.ModelViewSet):
    """
    退款管理
    - 创建退款（支持部分退款）
    - 更新退款状态（start/succeed/fail）
    """
    queryset = Refund.objects.all().select_related('order', 'payment', 'operator')
    serializer_class = RefundSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if not user.is_staff:
            qs = qs.filter(order__user=user)
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return RefundCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        refund = serializer.save(status='pending')

        refund.logs.append({
            't': timezone.now().isoformat(),
            'event': 'refund_created',
            'amount': str(refund.amount),
            'reason': refund.reason,
            'order_status': refund.order.status
        })
        refund.save(update_fields=['logs'])

        # 管理员创建的退款可直接进入退款中状态，用户申请保持审核中
        try:
            from .state_machine import OrderStateMachine
            if request.user.is_staff or getattr(request.user, 'role', '') == 'support':
                if refund.order.status not in ['refunded', 'refunding']:
                    OrderStateMachine.transition(refund.order, 'refunding', operator=request.user, note='申请退款')
        except Exception:
            pass

        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        from .state_machine import OrderStateMachine
        refund = self.get_object()
        if refund.order.status in ['pending', 'cancelled']:
            return Response({'detail': '当前订单状态不支持退款'}, status=status.HTTP_400_BAD_REQUEST)
        if refund.status not in ['pending', 'failed']:
            return Response({'detail': '当前状态不可开始处理'}, status=400)
        refund.status = 'processing'
        refund.logs.append({'t': timezone.now().isoformat(), 'event': 'start'})
        refund.operator = request.user
        refund.save(update_fields=['status', 'logs', 'operator', 'updated_at'])

        provider = (request.data.get('provider') or (refund.payment.method if refund.payment else 'wechat')).lower()
        if provider == 'credit':
            refundable = PaymentService.calculate_refundable_amount(refund.order)
            if refund.amount > refundable:
                refund.status = 'failed'
                refund.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'reason': f'退款金额超出可退金额，可退 {refundable}'
                })
                refund.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': f'退款金额超出可退金额，可退 {refundable}'}, status=status.HTTP_400_BAD_REQUEST)

            from users.credit_services import CreditAccountService
            credit_account = getattr(refund.order.user, 'credit_account', None)
            if not credit_account:
                refund.status = 'failed'
                refund.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'reason': '未找到信用账户'
                })
                refund.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': '未找到信用账户'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                with transaction.atomic():
                    CreditAccountService.record_refund(
                        credit_account=credit_account,
                        amount=refund.amount,
                        order_id=refund.order_id,
                        description=f'信用退款 #{refund.order.order_number}'
                    )
                    refund.logs.append({
                        't': timezone.now().isoformat(),
                        'event': 'credit_refund_recorded',
                        'amount': str(refund.amount),
                    })
                    refund.save(update_fields=['logs'])
                    PaymentService.process_refund_success(refund.id, operator=request.user)
                    refund.refresh_from_db()
                    refund.operator = request.user
                    refund.save(update_fields=['operator', 'updated_at'])
            except Exception as exc:
                refund.status = 'failed'
                refund.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'reason': str(exc)
                })
                refund.operator = request.user
                refund.save(update_fields=['status', 'logs', 'operator', 'updated_at'])
                return Response({'detail': f'退款完成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(RefundSerializer(refund).data, status=status.HTTP_200_OK)
        if provider == 'wechat':
            refundable = PaymentService.calculate_refundable_amount(refund.order)
            if refund.amount > refundable:
                refund.status = 'failed'
                refund.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'reason': f'退款金额超出可退金额，可退 {refundable}'
                })
                refund.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': f'退款金额超出可退金额，可退 {refundable}'}, status=status.HTTP_400_BAD_REQUEST)

            pay = refund.payment or refund.order.payments.filter(status='succeeded', method='wechat').order_by('-created_at').first()
            if not pay:
                refund.status = 'failed'
                refund.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'reason': '未找到可退款的微信支付记录'
                })
                refund.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': '未找到可退款的微信支付记录'}, status=status.HTTP_400_BAD_REQUEST)
            if pay.status != 'succeeded':
                # 尝试主动查单同步支付状态
                try:
                    result = PaymentService.query_wechat_transaction(pay)
                    trade_state = result.get('trade_state')
                    transaction_id = result.get('transaction_id')
                    if trade_state == 'SUCCESS':
                        PaymentService.process_payment_success(pay.id, transaction_id=transaction_id, operator=request.user)
                        pay.refresh_from_db()
                    else:
                        refund.status = 'failed'
                        refund.logs.append({
                            't': timezone.now().isoformat(),
                            'event': 'start_failed',
                            'reason': f'支付状态非已成功: {trade_state or pay.status}'
                        })
                        refund.save(update_fields=['status', 'logs', 'updated_at'])
                        return Response({'detail': f'支付状态非已成功: {trade_state or pay.status}'}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as sync_exc:
                    refund.status = 'failed'
                    refund.logs.append({
                        't': timezone.now().isoformat(),
                        'event': 'start_failed',
                        'reason': f'支付状态校验失败: {sync_exc}'
                    })
                    refund.save(update_fields=['status', 'logs', 'updated_at'])
                    return Response({'detail': f'支付状态校验失败: {sync_exc}'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                logging.getLogger(__name__).info(
                    '[REFUND_START] calling wechat refund',
                    extra={
                        'refund_id': refund.id,
                        'order_id': refund.order_id,
                        'payment_id': refund.payment_id,
                        'amount': str(refund.amount)
                    }
                )
                data = PaymentService.create_wechat_refund(refund, operator=request.user)
            except Exception as exc:
                refund.status = 'failed'
                refund.logs.append({
                    't': timezone.now().isoformat(),
                    'event': 'start_failed',
                    'reason': str(exc)
                })
                refund.save(update_fields=['status', 'logs', 'updated_at'])
                return Response({'detail': f'微信退款发起失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                if OrderStateMachine.can_transition(refund.order.status, 'refunding'):
                    OrderStateMachine.transition(refund.order, 'refunding', operator=request.user, note='退款处理中')
            except Exception:
                pass
            serializer = RefundSerializer(refund)
            return Response({'refund': serializer.data, 'wechat': data}, status=status.HTTP_200_OK)

        return Response(RefundSerializer(refund).data)

    @action(detail=True, methods=['post'])
    def succeed(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        refund = self.get_object()
        if refund.status != 'processing':
            return Response({'detail': '当前状态不可标记成功'}, status=400)

        # 防止超额退款
        refundable = PaymentService.calculate_refundable_amount(refund.order)
        if refund.amount > refundable:
            return Response({'detail': '退款金额超出可退金额'}, status=400)

        refund.status = 'succeeded'
        refund.transaction_id = request.data.get('transaction_id') or refund.transaction_id
        refund.logs.append({
            't': timezone.now().isoformat(),
            'event': 'succeeded',
            'transaction_id': refund.transaction_id
        })
        refund.operator = request.user
        refund.save(update_fields=['status', 'transaction_id', 'logs', 'operator', 'updated_at'])

        # 退款成功即视为订单退款完成
        try:
            from .state_machine import OrderStateMachine
            if OrderStateMachine.can_transition(refund.order.status, 'refunded'):
                OrderStateMachine.transition(refund.order, 'refunded', operator=request.user, note='退款完成')
            elif OrderStateMachine.can_transition(refund.order.status, 'refunding'):
                OrderStateMachine.transition(refund.order, 'refunding', operator=request.user, note='退款完成')
                OrderStateMachine.transition(refund.order, 'refunded', operator=request.user, note='退款完成')
        except Exception:
            pass

        try:
            from users.services import create_notification
            create_notification(
                refund.order.user,
                title='退款成功',
                content=f'订单 {refund.order.order_number} 退款成功，金额 ¥{refund.amount}',
                ntype='refund',
                metadata={
                    'order_id': refund.order.id,
                    'order_number': refund.order.order_number,
                    'refund_id': refund.id,
                    'payment_id': refund.payment_id,
                    'status': refund.status,
                    'amount': str(refund.amount),
                    'page': f'pages/order-detail/index?id={refund.order.id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {refund.order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(refund.updated_at).strftime('%Y-%m-%d %H:%M') if refund.updated_at else ''},
                        'thing3': {'value': f'退款金额 ¥{refund.amount}'[:20]},
                    },
                }
            )
        except Exception:
            pass

        return Response(RefundSerializer(refund).data)

    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        refund = self.get_object()
        if refund.status not in ['pending', 'processing']:
            return Response({'detail': '当前状态不可标记失败'}, status=400)
        refund.status = 'failed'
        refund.logs.append({
            't': timezone.now().isoformat(),
            'event': 'failed',
            'reason': request.data.get('reason', '')
        })
        refund.operator = request.user
        refund.save(update_fields=['status', 'logs', 'operator', 'updated_at'])
        try:
            order = refund.order
            if order.status == 'refunding':
                previous_status = None
                for entry in reversed(refund.logs or []):
                    if isinstance(entry, dict):
                        candidate = entry.get('order_status') or entry.get('order_status_snapshot')
                        if candidate:
                            previous_status = candidate
                            break
                if not previous_status:
                    previous_status = order.status_history.filter(
                        to_status='refunding'
                    ).order_by('-created_at').values_list('from_status', flat=True).first()
                target_status = previous_status or 'paid'
                if target_status != order.status:
                    from .models import OrderStatusHistory
                    old_status = order.status
                    order.status = target_status
                    order.updated_at = timezone.now()
                    order.save(update_fields=['status', 'updated_at'])
                    OrderStatusHistory.objects.create(
                        order=order,
                        from_status=old_status,
                        to_status=target_status,
                        operator=request.user,
                        note='退款失败回退'
                    )
                    try:
                        from .analytics import OrderAnalytics
                        OrderAnalytics.on_order_status_changed(order.id)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            from users.services import create_notification
            reason_text = str(request.data.get('reason') or '')
            create_notification(
                refund.order.user,
                title='退款失败',
                content=f'订单 {refund.order.order_number} 退款失败' + (f'，原因：{reason_text}' if reason_text else ''),
                ntype='refund',
                metadata={
                    'order_id': refund.order.id,
                    'order_number': refund.order.order_number,
                    'refund_id': refund.id,
                    'payment_id': refund.payment_id,
                    'status': refund.status,
                    'page': f'pages/order-detail/index?id={refund.order.id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {refund.order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(refund.updated_at).strftime('%Y-%m-%d %H:%M') if refund.updated_at else ''},
                        'thing3': {'value': (reason_text or '退款失败')[:20]},
                    },
                }
            )
        except Exception:
            pass
        return Response(RefundSerializer(refund).data)


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics and statistics.
    
    Permissions:
    - IsAdmin: Only administrators can access analytics
    
    Provides endpoints for:
    - Sales summary statistics
    - Top products ranking
    - Daily sales data
    - User growth statistics
    - Order status distribution
    """
    permission_classes = [IsAdmin]
    
    @action(detail=False, methods=['get'])
    def sales_summary(self, request):
        """
        获取销售汇总统计
        
        Query Parameters:
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
        
        Returns:
            {
                "total_orders": 订单总数,
                "total_amount": 销售总额,
                "avg_amount": 平均订单金额
            }
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        result = OrderAnalytics.get_sales_summary(
            start_date=start_date,
            end_date=end_date
        )
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """
        获取热销商品排行
        
        Query Parameters:
            limit: 返回的商品数量 (默认10)
            days: 统计周期天数 (默认30)
        
        Returns:
            [
                {
                    "product__id": 商品ID,
                    "product__name": 商品名称,
                    "total_quantity": 销售数量,
                    "total_amount": 销售额
                },
                ...
            ]
        """
        try:
            limit = int(request.query_params.get('limit', 10))
            days = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            return Response(
                {'detail': 'limit and days must be integers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证参数范围
        if limit < 1 or limit > 100:
            return Response(
                {'detail': 'limit must be between 1 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if days < 1 or days > 365:
            return Response(
                {'detail': 'days must be between 1 and 365'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = OrderAnalytics.get_top_products(limit=limit, days=days)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def daily_sales(self, request):
        """
        获取每日销售统计
        
        Query Parameters:
            days: 统计周期天数 (默认30)
        
        Returns:
            [
                {
                    "date": 日期,
                    "orders": 订单数,
                    "amount": 销售额
                },
                ...
            ]
        """
        try:
            days = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            return Response(
                {'detail': 'days must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证参数范围
        if days < 1 or days > 365:
            return Response(
                {'detail': 'days must be between 1 and 365'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = OrderAnalytics.get_daily_sales(days=days)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def user_growth(self, request):
        """
        获取用户增长统计
        
        Query Parameters:
            days: 统计周期天数 (默认30)
        
        Returns:
            [
                {
                    "date": 日期,
                    "new_users": 新增用户数
                },
                ...
            ]
        """
        try:
            days = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            return Response(
                {'detail': 'days must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证参数范围
        if days < 1 or days > 365:
            return Response(
                {'detail': 'days must be between 1 and 365'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = OrderAnalytics.get_user_growth(days=days)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def order_status_distribution(self, request):
        """
        获取订单状态分布统计
        
        Query Parameters:
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
        
        Returns:
            {
                "pending": {"label": "待支付", "count": 数量},
                "paid": {"label": "已支付", "count": 数量},
                ...
            }
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        result = OrderAnalytics.get_order_status_distribution(
            start_date=start_date,
            end_date=end_date
        )
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def regional_sales(self, request):
        """
        获取按地区聚合的销售统计
        
        Query Parameters:
            level: 地区维度（province/city/district/town），默认 province
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            product_id: 商品ID（可选）
            order_by: 排序字段（orders/total_quantity/amount），默认 amount
            limit: 返回条目上限（可选）
        
        Returns:
            [ { region: 地区名称, orders: 订单数, total_quantity: 销量, amount: 销售额 }, ... ]
        """
        level = request.query_params.get('level', 'province')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        product_id = request.query_params.get('product_id')
        order_by = request.query_params.get('order_by', 'amount')
        limit = request.query_params.get('limit')
        
        try:
            product_id = int(product_id) if product_id is not None else None
        except (ValueError, TypeError):
            return Response({'detail': 'product_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            limit = int(limit) if limit is not None else None
        except (ValueError, TypeError):
            return Response({'detail': 'limit must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_levels = {'province', 'city', 'district', 'town'}
        if str(level).lower() not in valid_levels:
            return Response({'detail': 'Invalid level, choose province/city/district/town'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_order = {'orders', 'total_quantity', 'amount'}
        if str(order_by).lower() not in valid_order:
            return Response({'detail': 'Invalid order_by, choose orders/total_quantity/amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = OrderAnalytics.get_sales_by_region(
            level=str(level).lower(),
            start_date=start_date,
            end_date=end_date,
            product_id=product_id,
            order_by=str(order_by).lower(),
            limit=limit,
        )
        return Response(result)

    @action(detail=False, methods=['get'])
    def export_regional_sales(self, request):
        level = request.query_params.get('level', 'province')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        product_id = request.query_params.get('product_id')
        order_by = request.query_params.get('order_by', 'amount')
        limit = request.query_params.get('limit')

        try:
            product_id = int(product_id) if product_id is not None else None
        except (ValueError, TypeError):
            return Response({'detail': 'product_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = int(limit) if limit is not None else None
        except (ValueError, TypeError):
            return Response({'detail': 'limit must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        valid_levels = {'province', 'city', 'district', 'town'}
        if str(level).lower() not in valid_levels:
            return Response({'detail': 'Invalid level, choose province/city/district/town'}, status=status.HTTP_400_BAD_REQUEST)

        valid_order = {'orders', 'total_quantity', 'amount'}
        if str(order_by).lower() not in valid_order:
            return Response({'detail': 'Invalid order_by, choose orders/total_quantity/amount'}, status=status.HTTP_400_BAD_REQUEST)

        result = OrderAnalytics.get_sales_by_region(
            level=str(level).lower(),
            start_date=start_date,
            end_date=end_date,
            product_id=product_id,
            order_by=str(order_by).lower(),
            limit=limit,
        )
        headers = ['地区', '订单数', '销售数量', '销售金额']
        rows = [
            [
                item.get('region_name'),
                item.get('orders'),
                item.get('total_quantity'),
                item.get('amount'),
            ]
            for item in result
        ]
        filename = f"sales_regional_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="销售统计-地区")

    @action(detail=False, methods=['get'])
    def product_region_distribution(self, request):
        """
        获取某商品在各地区的销售分布
        
        Query Parameters:
            product_id: 商品ID（必填）
            level: 地区维度（province/city/district/town），默认 province
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            order_by: 排序字段（orders/total_quantity/amount），默认 total_quantity
        
        Returns:
            [ { region: 地区名称, orders: 订单数, total_quantity: 销量, amount: 销售额 }, ... ]
        """
        product_id = request.query_params.get('product_id')
        level = request.query_params.get('level', 'province')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        order_by = request.query_params.get('order_by', 'total_quantity')
        
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return Response({'detail': 'product_id is required and must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_levels = {'province', 'city', 'district', 'town'}
        if str(level).lower() not in valid_levels:
            return Response({'detail': 'Invalid level, choose province/city/district/town'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_order = {'orders', 'total_quantity', 'amount'}
        if str(order_by).lower() not in valid_order:
            return Response({'detail': 'Invalid order_by, choose orders/total_quantity/amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = OrderAnalytics.get_product_region_distribution(
            product_id=product_id,
            level=str(level).lower(),
            start_date=start_date,
            end_date=end_date,
            order_by=str(order_by).lower(),
        )
        return Response(result)

    @action(detail=False, methods=['get'])
    def export_product_region_distribution(self, request):
        product_id = request.query_params.get('product_id')
        level = request.query_params.get('level', 'province')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        order_by = request.query_params.get('order_by', 'total_quantity')

        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return Response({'detail': 'product_id is required and must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        valid_levels = {'province', 'city', 'district', 'town'}
        if str(level).lower() not in valid_levels:
            return Response({'detail': 'Invalid level, choose province/city/district/town'}, status=status.HTTP_400_BAD_REQUEST)

        valid_order = {'orders', 'total_quantity', 'amount'}
        if str(order_by).lower() not in valid_order:
            return Response({'detail': 'Invalid order_by, choose orders/total_quantity/amount'}, status=status.HTTP_400_BAD_REQUEST)

        result = OrderAnalytics.get_product_region_distribution(
            product_id=product_id,
            level=str(level).lower(),
            start_date=start_date,
            end_date=end_date,
            order_by=str(order_by).lower(),
        )
        headers = ['地区', '订单数', '销售数量', '销售金额']
        rows = [
            [
                item.get('region_name'),
                item.get('orders'),
                item.get('total_quantity'),
                item.get('amount'),
            ]
            for item in result
        ]
        filename = f"sales_product_region_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="销售统计-商品地区分布")

    @action(detail=False, methods=['get'])
    def region_product_stats(self, request):
        """
        获取某地区的热销商品统计
        
        Query Parameters:
            region_name: 地区名称（必填）
            level: 地区维度（province/city/district/town），默认 province
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            order_by: 排序字段（orders/total_quantity/amount），默认 total_quantity
            limit: 返回条目上限（可选）
        
        Returns:
            [ { product__id, product__name, orders, total_quantity, amount }, ... ]
        """
        region_name = request.query_params.get('region_name')
        level = request.query_params.get('level', 'province')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        order_by = request.query_params.get('order_by', 'total_quantity')
        limit = request.query_params.get('limit')
        
        if not region_name:
            return Response({'detail': 'region_name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            limit = int(limit) if limit is not None else None
        except (ValueError, TypeError):
            return Response({'detail': 'limit must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_levels = {'province', 'city', 'district', 'town'}
        if str(level).lower() not in valid_levels:
            return Response({'detail': 'Invalid level, choose province/city/district/town'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_order = {'orders', 'total_quantity', 'amount'}
        if str(order_by).lower() not in valid_order:
            return Response({'detail': 'Invalid order_by, choose orders/total_quantity/amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = OrderAnalytics.get_region_product_stats(
            region_name=region_name,
            level=str(level).lower(),
            start_date=start_date,
            end_date=end_date,
            order_by=str(order_by).lower(),
            limit=limit,
        )
        return Response(result)

    @action(detail=False, methods=['get'])
    def export_region_product_stats(self, request):
        region_name = request.query_params.get('region_name')
        level = request.query_params.get('level', 'province')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        order_by = request.query_params.get('order_by', 'total_quantity')
        limit = request.query_params.get('limit')

        if not region_name:
            return Response({'detail': 'region_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = int(limit) if limit is not None else None
        except (ValueError, TypeError):
            return Response({'detail': 'limit must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        valid_levels = {'province', 'city', 'district', 'town'}
        if str(level).lower() not in valid_levels:
            return Response({'detail': 'Invalid level, choose province/city/district/town'}, status=status.HTTP_400_BAD_REQUEST)

        valid_order = {'orders', 'total_quantity', 'amount'}
        if str(order_by).lower() not in valid_order:
            return Response({'detail': 'Invalid order_by, choose orders/total_quantity/amount'}, status=status.HTTP_400_BAD_REQUEST)

        result = OrderAnalytics.get_region_product_stats(
            region_name=region_name,
            level=str(level).lower(),
            start_date=start_date,
            end_date=end_date,
            order_by=str(order_by).lower(),
            limit=limit,
        )
        headers = ['商品', '订单数', '销售数量', '销售金额']
        rows = [
            [
                item.get('product__name'),
                item.get('orders'),
                item.get('total_quantity'),
                item.get('amount'),
            ]
            for item in result
        ]
        filename = f"sales_region_products_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="销售统计-地区商品")

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def invalidate_cache(self, request):
        """
        清除统计缓存
        
        Request Body (optional):
            {
                "cache_keys": ["sales_summary_*", "top_products_*"]
            }
        
        Returns:
            {"detail": "Cache invalidated"}
        """
        cache_keys = request.data.get('cache_keys')
        
        OrderAnalytics.invalidate_cache(cache_keys=cache_keys)
        
        return Response({'detail': 'Cache invalidated'})
