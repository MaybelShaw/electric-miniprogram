from rest_framework import viewsets, permissions, status, serializers
from rest_framework.views import APIView
from .models import Order,Cart,CartItem, Payment, Discount, DiscountTarget, Invoice, ReturnRequest
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    CartItemSerializer,
    CartSerializer,
    PaymentSerializer,
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
from .services import create_order,get_or_create_cart,add_to_cart,remove_from_cart
from .analytics import OrderAnalytics
from catalog.models import Product
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from typing import Dict, Optional
from common.permissions import IsOwnerOrAdmin, IsAdmin
from common.utils import parse_int, parse_datetime
from common.throttles import PaymentRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes as OT
from django.http import FileResponse
from common.serializers import PDFOrImageFileValidator


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
        qs = qs.select_related('user', 'product', 'return_request').prefetch_related('payments', 'status_history')

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
                qs = qs.filter(product__name__icontains=product_name)
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

        return qs.order_by('-created_at')

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
        
        # 验证请求数据
        serializer = OrderCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # 获取目标用户（支持管理员为其他用户创建订单）
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

        # 创建订单
        try:
            with transaction.atomic():
                payment_method = serializer.validated_data.get("payment_method", "online")
                
                order = create_order(
                    user=target_user,
                    product_id=serializer.validated_data["product_id"],
                    address_id=serializer.validated_data["address_id"],
                    quantity=serializer.validated_data.get("quantity", 1),
                    note=serializer.validated_data.get("note", ""),
                    payment_method=payment_method,
                )
                
                logger.info(f'订单创建成功: order_id={order.id}, user_id={target_user.id}, payment_method={payment_method}')
                
                # 只有在线支付才创建支付记录
                payment = None
                if payment_method == 'online':
                    payment_method_type = request.data.get('method', 'wechat')
                    payment = Payment.create_for_order(
                        order, 
                        method=payment_method_type, 
                        ttl_minutes=30
                    )
                    logger.info(f'支付记录创建成功: payment_id={payment.id}, order_id={order.id}')
                else:
                    logger.info(f'信用支付订单，无需创建支付记录: order_id={order.id}')
                
        except ValueError as e:
            # 业务逻辑错误（如库存不足）
            logger.warning(f'创建订单失败: {str(e)}')
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # 系统错误
            logger.error(f'创建订单异常: {str(e)}')
            return Response(
                {'detail': f'创建订单失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 返回订单和支付信息
        order_serializer = OrderSerializer(order)
        pay_serializer = PaymentSerializer(payment)
        
        return Response({
            'order': order_serializer.data, 
            'payment': pay_serializer.data
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
        
        # 合并同一商品的数量
        product_quantities = {}
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            if product_id:
                product_quantities[product_id] = product_quantities.get(product_id, 0) + quantity
        
        orders = []
        payments = []
        
        try:
            with transaction.atomic():
                # 为每个不同的商品创建订单
                for product_id, quantity in product_quantities.items():
                    order = create_order(
                        user=request.user,
                        product_id=product_id,
                        address_id=address_id,
                        quantity=quantity,
                        note=note,
                        payment_method=payment_method,
                    )
                    orders.append(order)
                    
                    # 只有在线支付才创建支付记录
                    if payment_method == 'online':
                        payment = Payment.create_for_order(
                            order,
                            method=online_method,
                            ttl_minutes=30
                        )
                        payments.append(payment)
                    
                    logger.info(f'批量订单创建: order_id={order.id}, product_id={product_id}, quantity={quantity}')
                
        except ValueError as e:
            logger.warning(f'批量创建订单失败: {str(e)}')
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'批量创建订单异常: {str(e)}')
            return Response(
                {'detail': f'批量创建订单失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 返回订单和支付信息
        order_serializers = [OrderSerializer(order).data for order in orders]
        payment_serializers = [PaymentSerializer(payment).data for payment in payments]
        
        return Response({
            'orders': order_serializers, 
            'payments': payment_serializers
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """取消订单：本人或管理员可取消，使用状态机进行状态转换"""
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support' or order.user_id == user.id):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from django.utils import timezone
            from .state_machine import OrderStateMachine
            note = request.data.get('note', '')
            reason = request.data.get('reason', '')
            if reason:
                order.cancel_reason = reason
            order.cancelled_at = timezone.now()
            order.save(update_fields=['cancel_reason', 'cancelled_at'])
            order = OrderStateMachine.transition(
                order,
                'cancelled',
                operator=user,
                note=note
            )
            try:
                from catalog.models import Product as CatalogProduct
                is_haier_product = bool(
                    order.product and getattr(order.product, 'source', None) == getattr(CatalogProduct, 'SOURCE_HAIER', 'haier')
                )
                if is_haier_product and order.haier_so_id:
                    from integrations.ylhapi import YLHSystemAPI
                    import logging
                    logger = logging.getLogger(__name__)
                    ylh_api = YLHSystemAPI.from_settings()
                    if ylh_api.authenticate():
                        src = str(request.data.get('source_system', 'MERCHANT_ADMIN'))
                        ylh_api.cancel_order(order.haier_so_id, order.cancel_reason or '', src)
                        logger.info(f'已同步易理货取消: order_id={order.id}, soId={order.haier_so_id}')
                    else:
                        logger.error('易理货系统认证失败，取消不同步')
            except Exception as sync_err:
                import logging
                logging.getLogger(__name__).error(f'同步易理货取消失败: {str(sync_err)}')
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=200)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"取消订单失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def ship(self, request, pk=None):
        """发货：仅管理员可操作，状态从 paid 转换到 shipped"""
        order = self.get_object()
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'support'):
            return Response({"detail": "Only admins can ship orders"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from .state_machine import OrderStateMachine
            note = request.data.get('note', '')
            tracking_number = request.data.get('tracking_number') or request.data.get('logistics_no')
            if not tracking_number:
                return Response({"detail": "tracking_number 或 logistics_no 为必填"}, status=status.HTTP_400_BAD_REQUEST)
            order.logistics_no = tracking_number
            order.save()
            order = OrderStateMachine.transition(
                order,
                'shipped',
                operator=user,
                note=note
            )
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=200)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"发货失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
        return Response(ReturnRequestSerializer(rr).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def complete_refund(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        rr = getattr(order, 'return_request', None)
        if not rr:
            return Response({"detail": "尚未申请退货"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from .state_machine import OrderStateMachine
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
                        amount=order.total_amount,
                        order_id=order.id,
                        description=f'退货退款 #{order.order_number}'
                    )
        except Exception:
            pass
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
    
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
        product = order.product
        from catalog.models import Product as CatalogProduct
        is_haier_product = bool(
            product and getattr(product, 'source', None) == getattr(CatalogProduct, 'SOURCE_HAIER', 'haier')
        )
        if not is_haier_product:
            return Response(
                {'detail': '该订单不是海尔产品订单，无需推送'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已推送
        if order.haier_so_id:
            return Response(
                {'detail': '该订单已推送到海尔系统'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.conf import settings
            import logging
            
            logger = logging.getLogger(__name__)
            
            # 准备订单数据
            source_system = request.data.get('source_system', 'YOUR_SYSTEM')
            shop_name = request.data.get('shop_name', '默认店铺')
            order_data = order.prepare_haier_order_data(source_system, shop_name)
            
            # 始终使用真实易理货API
            from integrations.ylhapi import YLHSystemAPI
            
            logger.info(f'调用易理货API推送订单: order_id={order.id}')
            
            ylh_api = YLHSystemAPI.from_settings()
            
            # 认证
            if not ylh_api.authenticate():
                logger.error('易理货系统认证失败')
                return Response(
                    {'detail': '易理货系统认证失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 推送订单
            result = ylh_api.create_order(order_data)
            
            if not result:
                logger.error(f'推送订单失败: order_id={order.id}')
                return Response(
                    {'detail': '推送订单失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info(f'推送成功: order_id={order.id}')
            
            order.haier_so_id = order_data['soId']
            haier_order_no = ''
            if isinstance(result, dict):
                data_section = result.get('data') if isinstance(result.get('data', None), dict) else result
                if isinstance(data_section, dict):
                    haier_order_no = data_section.get('retailOrderNo', '') or data_section.get('retail_order_no', '')
            order.haier_order_no = haier_order_no
            order.save()
            
            serializer = self.get_serializer(order)
            return Response({
                'detail': '订单推送成功',
                'order': serializer.data,
                'haier_response': result,
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'推送海尔订单失败: {str(e)}')
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
        cart.items.all().select_related('product', 'product__category', 'product__brand')
        # 传入请求上下文以便 ProductSerializer 计算 discounted_price
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False,methods=['post'])
    def add_item(self,request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        if not product_id:
            return Response({"detail": "product_id is required"}, status=400)
        
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"detail": "quantity must be integer"}, status=400)
        
        if quantity <= 0:
            return Response({"detail": "quantity must be positive"}, status=400)
        
        try:
            add_to_cart(request.user, product_id, quantity)
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
        
        if not product_id:
            return Response({"detail": "product_id is required"}, status=400)
        
        try:
            remove_from_cart(request.user, product_id)
            cart = get_or_create_cart(request.user)
            serializer = CartSerializer(cart, context={'request': request})
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """设置某商品的精确数量（不存在则创建）"""
        # 添加调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[购物车更新] Content-Type: {request.content_type}")
        logger.info(f"[购物车更新] request.data: {request.data}")
        logger.info(f"[购物车更新] request.data type: {type(request.data)}")
        logger.info(f"[购物车更新] request.data keys: {list(request.data.keys()) if hasattr(request.data, 'keys') else 'N/A'}")
        
        product_id = request.data.get('product_id')
        quantity_raw = request.data.get('quantity', 1)
        
        logger.info(f"[购物车更新] product_id={product_id} (type: {type(product_id)})")
        logger.info(f"[购物车更新] quantity_raw={quantity_raw} (type: {type(quantity_raw)})")
        
        # 验证 product_id
        if not product_id:
            logger.error(f"[购物车更新] 缺少 product_id, request.data={request.data}")
            return Response({"detail": "product_id is required"}, status=400)
        
        # 验证 quantity
        try:
            quantity = int(quantity_raw)
            logger.info(f"[购物车更新] 数量转换成功: {quantity}")
        except (TypeError, ValueError) as e:
            logger.error(f"[购物车更新] 数量转换失败: quantity_raw={quantity_raw}, error={e}")
            return Response({"detail": f"quantity must be integer, got: {quantity_raw}"}, status=400)
        
        # 如果数量 <= 0，移除商品
        if quantity <= 0:
            remove_from_cart(request.user, product_id)
            return Response({"detail": "Item removed"}, status=200)

        try:
            logger.info(f"[购物车更新] 开始更新购物车")
            cart = get_or_create_cart(request.user)
            logger.info(f"[购物车更新] 获取购物车成功: cart_id={cart.id}")
            
            from .models import CartItem
            product = Product.objects.get(id=product_id)
            logger.info(f"[购物车更新] 获取商品成功: product_id={product.id}, stock={product.stock}")
            
            # 检查库存
            if quantity > product.stock:
                logger.warning(f"[购物车更新] 库存不足: quantity={quantity}, stock={product.stock}")
                return Response({
                    "detail": f"库存不足，当前库存: {product.stock}"
                }, status=400)
            
            item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            item.quantity = quantity
            item.save()
            logger.info(f"[购物车更新] 更新成功: item_id={item.id}, quantity={quantity}, created={created}")
            
            # 返回更新后的购物车
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
        qs = qs.select_related('order', 'order__user', 'order__product')
        
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
                    f'order_amount={order.total_amount}, '
                    f'payment_amount={parsed_amount}'
                )
                return Response(
                    {
                        'detail': f'Payment amount {parsed_amount} does not match order amount {order.total_amount}',
                        'order_amount': str(order.total_amount),
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
            payment = Payment.create_for_order(order, method=method, ttl_minutes=30)
            
            # 记录支付创建事件
            PaymentService.log_payment_event(
                payment.id,
                'payment_created',
                details={
                    'method': method,
                    'amount': str(order.total_amount),
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
        if payment.status in ['succeeded', 'cancelled', 'expired']:
            return Response({'detail': 'Payment not startable'}, status=400)
        payment.status = 'processing'
        payment.logs.append({'t': str(payment.updated_at), 'event': 'start', 'detail': 'user starts payment'})
        payment.save()
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=['post'])
    def succeed(self, request, pk=None):
        payment = self.get_object()
        payment.status = 'succeeded'
        payment.logs.append({'t': str(payment.updated_at), 'event': 'succeeded'})
        payment.save()
        
        # 使用状态机更新订单状态
        try:
            from .state_machine import OrderStateMachine
            OrderStateMachine.transition(
                payment.order,
                'paid',
                operator=request.user,
                note='Payment succeeded'
            )
        except ValueError:
            # 如果状态转换失败，仍然返回支付成功的响应
            pass
        
        return Response(self.get_serializer(payment).data)


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

    def get_queryset(self):
        # 折扣管理仅管理员可见；普通用户仅能查看与自己相关的折扣（用于调试），实际前端不暴露列表
        user = self.request.user
        if user.is_staff:
            qs = Discount.objects.all()
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

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def batch_set(self, request):
        """批量为指定用户设置一组商品的统一折扣金额与时间窗。
        输入: { user_id, product_ids:[], amount, effective_time, expiration_time, priority }
        返回: 创建/更新的目标数量
        """
        try:
            user_id = int(request.data.get('user_id'))
            product_ids = request.data.get('product_ids') or []
            amount = request.data.get('amount')
            effective_time = request.data.get('effective_time')
            expiration_time = request.data.get('expiration_time')
            priority = int(request.data.get('priority', 0))
        except Exception:
            return Response({'detail': '参数不合法'}, status=400)
        if not product_ids or amount is None or not effective_time or not expiration_time:
            return Response({'detail': '缺少必要参数'}, status=400)

        # 创建折扣规则
        disc = Discount.objects.create(
            name=request.data.get('name', ''),
            amount=amount,
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
        """批量查询当前用户在一组商品上的有效折扣，返回字典 {product_id: {amount, discount_id}}。
        性能：限制商品ID数量，并做索引查询；后续将配合缓存。
        """
        from common.utils import parse_csv_ints
        prod_ids = request.query_params.get('product_ids', '')
        ids = parse_csv_ints(prod_ids)
        if not ids:
            return Response({})

        now = timezone.now()
        # 优先级排序选择一个最优折扣（最高优先级）；若同优先级按更新时间
        qs = DiscountTarget.objects.select_related('discount').filter(
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
            result[pid] = {'amount': float(dt.discount.amount), 'discount_id': dt.discount_id}


@extend_schema(tags=['Invoices'])
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = Invoice.objects.all() if (user.is_staff or getattr(user, 'role', '') == 'support') else Invoice.objects.filter(user=user)
        return qs.select_related('order', 'user', 'order__product').order_by('-requested_at')

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
    """支付回调处理视图
    
    处理来自第三方支付服务商的支付回调。
    支持多个支付提供商（mock、wechat等）。
    
    功能：
    - 验证回调签名真实性
    - 防止重复处理已成功的支付
    - 记录完整的支付日志
    - 使用事务处理支付状态更新
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PaymentRateThrottle]

    def post(self, request, provider: str = 'mock'):
        """处理支付回调
        
        Args:
            request: HTTP请求对象
            provider: 支付提供商（mock、wechat等）
            
        Returns:
            Response: 支付记录序列化数据或错误信息
        """
        from .payment_service import PaymentService
        import logging
        
        logger = logging.getLogger(__name__)
        provider = (provider or 'mock').lower()
        data = request.data or {}

        # 仅在开发环境允许简化回调（mock/wechat）
        if not settings.DEBUG and provider in ('mock', 'wechat'):
            logger.warning(f'非开发环境不允许{provider}回调')
            return Response({'detail': f'{provider} callback only enabled in development'}, status=403)

        # 记录回调接收事件
        logger.info(f'收到支付回调: provider={provider}, data={data}')

        # 查找支付记录
        payment = self._find_payment(data)
        if payment is None:
            logger.error(f'支付记录不存在: {data}')
            return Response({'detail': 'payment not found'}, status=404)

        # 验证回调签名（如果提供了签名）
        signature = data.get('signature') or data.get('sign')
        if signature:
            if not self._verify_signature(provider, data, signature):
                logger.error(f'签名验证失败: payment_id={payment.id}, provider={provider}')
                PaymentService.log_payment_event(
                    payment.id,
                    'signature_verification_failed',
                    details={'provider': provider},
                    error='Signature verification failed'
                )
                return Response({'detail': 'signature verification failed'}, status=403)
            
            PaymentService.log_payment_event(
                payment.id,
                'signature_verified',
                details={'provider': provider}
            )

        # 防止重复处理已成功的支付
        if payment.status == 'succeeded':
            logger.warning(f'支付记录已处理过: payment_id={payment.id}')
            PaymentService.log_payment_event(
                payment.id,
                'duplicate_callback_ignored',
                details={'provider': provider}
            )
            return Response(PaymentSerializer(payment).data)

        # 提取回调数据
        status_param = data.get('status') or data.get('result_code') or data.get('trade_state')
        transaction_id = data.get('transaction_id') or data.get('wx_transaction_id') or data.get('trans_id')

        # 映射支付状态
        new_status = self._map_payment_status(provider, status_param)

        # 使用事务处理支付状态更新
        try:
            with transaction.atomic():
                # 处理支付成功
                if new_status == 'succeeded' and payment.status != 'succeeded':
                    PaymentService.process_payment_success(
                        payment.id,
                        transaction_id=transaction_id,
                        operator=None
                    )
                    logger.info(f'支付成功处理: payment_id={payment.id}, transaction_id={transaction_id}')
                
                # 处理支付失败
                elif new_status == 'failed':
                    payment.status = 'failed'
                    PaymentService.log_payment_event(
                        payment.id,
                        'payment_failed',
                        details={'provider': provider, 'reason': status_param}
                    )
                    payment.save()
                    logger.warning(f'支付失败: payment_id={payment.id}')
                
                # 处理支付取消
                elif new_status == 'cancelled':
                    payment.status = 'cancelled'
                    PaymentService.log_payment_event(
                        payment.id,
                        'payment_cancelled',
                        details={'provider': provider}
                    )
                    payment.save()
                    logger.info(f'支付已取消: payment_id={payment.id}')
                
                # 处理支付过期
                elif new_status == 'expired':
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

        return Response(PaymentSerializer(payment).data)

    def _find_payment(self, data: Dict) -> Optional[Payment]:
        """查找支付记录
        
        优先通过payment_id查找，其次通过order_number查找。
        
        Args:
            data: 回调数据字典
            
        Returns:
            Payment: 支付记录对象，如果不存在返回None
        """
        from common.utils import parse_int
        payment_id = data.get('payment_id')
        order_number = data.get('order_number') or data.get('out_trade_no')

        if payment_id:
            pid = parse_int(payment_id)
            if pid is not None:
                try:
                    return Payment.objects.get(id=pid)
                except Payment.DoesNotExist:
                    pass

        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
                return (
                    Payment.objects.filter(order=order)
                    .order_by('-created_at')
                    .first()
                )
            except Order.DoesNotExist:
                pass

        return None

    def _verify_signature(self, provider: str, data: Dict, signature: str) -> bool:
        """验证回调签名
        
        根据支付提供商调用相应的签名验证方法。
        
        Args:
            provider: 支付提供商
            data: 回调数据字典
            signature: 签名值
            
        Returns:
            bool: 签名验证成功返回True，否则返回False
        """
        from .payment_service import PaymentService
        
        if provider == 'wechat':
            # 微信支付签名验证
            secret = settings.WECHAT_PAY_SECRET if hasattr(settings, 'WECHAT_PAY_SECRET') else None
            if not secret:
                return False
            return PaymentService.verify_callback_signature(data, signature, secret)
        
        elif provider == 'alipay':
            # 支付宝签名验证
            secret = settings.ALIPAY_SECRET if hasattr(settings, 'ALIPAY_SECRET') else None
            if not secret:
                return False
            return PaymentService.verify_callback_signature(data, signature, secret)
        
        elif provider == 'mock':
            # 开发环境mock支付，跳过签名验证
            return True
        
        return False

    def _map_payment_status(self, provider: str, status_param: str) -> str:
        """映射支付状态
        
        将不同支付提供商的状态值映射到统一的支付状态。
        
        Args:
            provider: 支付提供商
            status_param: 支付提供商返回的状态值
            
        Returns:
            str: 统一的支付状态
        """
        if provider == 'mock':
            mapping = {
                'succeeded': 'succeeded',
                'success': 'succeeded',
                'failed': 'failed',
                'fail': 'failed',
                'cancelled': 'cancelled',
                'expired': 'expired',
                'processing': 'processing',
            }
            return mapping.get(str(status_param).lower(), 'succeeded')
        
        elif provider == 'wechat':
            # 微信支付状态映射
            val = str(status_param).upper() if status_param else ''
            return 'succeeded' if val == 'SUCCESS' else 'failed'
        
        elif provider == 'alipay':
            # 支付宝状态映射
            val = str(status_param).lower() if status_param else ''
            if val == 'trade_success':
                return 'succeeded'
            elif val == 'trade_closed':
                return 'cancelled'
            else:
                return 'failed'
        
        return 'processing'


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
