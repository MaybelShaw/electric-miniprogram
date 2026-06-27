from collections import OrderedDict

from rest_framework import serializers
from django.conf import settings
from urllib.parse import urlparse
from datetime import timedelta
from .models import (
    Order,
    Cart,
    CartItem,
    Payment,
    Refund,
    Discount,
    DiscountTarget,
    Invoice,
    ReturnRequest,
    OrderItem,
    OrderShippingAction,
    StoreProfitSharingEntry,
    WechatProfitSharingOrder,
)
from .shipping_action_service import get_shipping_capabilities, is_haier_order
from catalog.models import Product
from users.models import Address
from catalog.serializers import ProductSerializer, ProductSKUSerializer
from stores.models import Store
from stores.permissions import is_platform_admin, is_support_user
from drf_spectacular.utils import extend_schema_field


def _is_absolute_url(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')


def _resolve_media_url(url: str) -> str:
    if not url or _is_absolute_url(url):
        return url
    media_base = settings.MEDIA_URL or '/media/'
    if not _is_absolute_url(media_base):
        return url
    base = media_base if media_base.endswith('/') else f"{media_base}/"
    base_path = urlparse(base).path or '/'
    trimmed = url
    if base_path != '/' and trimmed.startswith(base_path):
        trimmed = trimmed[len(base_path):]
    trimmed = trimmed.lstrip('/')
    return f"{base}{trimmed}"


def _ensure_https(url: str, request=None) -> str:
    if not url:
        return url
    if request is None or not request.is_secure():
        return url
    if url.startswith('http://'):
        return 'https://' + url[len('http://'):]
    return url


def _build_media_url(url: str, request=None) -> str:
    if not url:
        return url
    if _is_absolute_url(url):
        return _ensure_https(url, request)
    resolved = _resolve_media_url(url)
    if _is_absolute_url(resolved):
        return _ensure_https(resolved, request)
    if request is not None:
        try:
            return _ensure_https(request.build_absolute_uri(url), request)
        except Exception:
            pass
    return _ensure_https(url, request)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    sku = ProductSKUSerializer(read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    sku_id = serializers.IntegerField(source='sku.id', read_only=True, allow_null=True)
    is_haier_item = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_id',
            'product_name',
            'sku',
            'sku_id',
            'sku_specs',
            'sku_code',
            'quantity',
            'unit_price',
            'discount_amount',
            'actual_amount',
            'snapshot_image',
            'created_at',
            'receive_qty',
            'return_qty',
            'reject_qty',
            'is_haier_item',
        ]

    def get_is_haier_item(self, obj: 'OrderItem') -> bool:
        """判断是否为海尔商品"""
        product = getattr(obj, 'product', None)
        if not product:
            return False
        return getattr(product, 'source', None) == getattr(product.__class__, 'SOURCE_HAIER', 'haier')


class OrderShippingActionSerializer(serializers.ModelSerializer):
    operator_username = serializers.CharField(
        source='operator.username',
        read_only=True,
        allow_null=True,
    )
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderShippingAction
        fields = [
            'id',
            'action',
            'action_label',
            'status',
            'status_label',
            'shipping_snapshot',
            'operator',
            'operator_username',
            'reason',
            'wechat_sync_required',
            'wechat_synced',
            'wechat_response',
            'created_at',
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_label = serializers.SerializerMethodField()
    is_haier_order = serializers.SerializerMethodField()
    haier_order_info = serializers.SerializerMethodField()
    logistics_info = serializers.SerializerMethodField()
    invoice_info = serializers.SerializerMethodField()
    return_info = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    quantity = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    refunded_amount = serializers.SerializerMethodField()
    refundable_amount = serializers.SerializerMethodField()
    refund_pending = serializers.SerializerMethodField()
    refund_action_required = serializers.SerializerMethodField()
    refund_locked = serializers.SerializerMethodField()
    child_orders = serializers.SerializerMethodField()
    can_cancel_shipping = serializers.SerializerMethodField()
    is_reshipment_pending = serializers.SerializerMethodField()
    reship_requires_wechat_sync = serializers.SerializerMethodField()
    shipping_cancel_count = serializers.SerializerMethodField()
    order_type = serializers.CharField(read_only=True)
    parent_order = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "user",
            "user_username",
            "product",
            "quantity",
            "total_amount",
            "discount_amount",
            "actual_amount",
            "refunded_amount",
            "refundable_amount",
            "refund_pending",
            "refund_action_required",
            "refund_locked",
            "status",
            "status_label",
            "payment_method",
            "created_at",
            "updated_at",
            "expires_at",
            "snapshot_contact_name",
            "snapshot_phone",
            "snapshot_address",
            "snapshot_province",
            "snapshot_city",
            "snapshot_district",
            "snapshot_town",
            "note",
            "is_haier_order",
            "haier_order_info",
            "logistics_info",
            "invoice_info",
            "return_info",
            "distribution_time",
            "install_time",
            "is_delivery_install",
            "is_government_order",
            "cancel_reason",
            "cancelled_at",
            "items",
            "order_type",
            "parent_order",
            "child_orders",
            "can_cancel_shipping",
            "is_reshipment_pending",
            "reship_requires_wechat_sync",
            "shipping_cancel_count",
        ]

    def get_quantity(self, obj: Order) -> int:
        return obj.total_quantity

    def get_status_label(self, obj: Order) -> str:
        mapping = {
            'pending': '待支付',
            'paid': '待发货',
            'shipped': '待收货',
            'completed': '已完成',
            'cancelled': '已取消',
            'returning': '退货中',
            'refunding': '退款中',
            'refunded': '已退款',
        }
        return mapping.get(obj.status, obj.status)

    def get_payment_method(self, obj: Order) -> str:
        # 优先检查关联的支付记录
        payment = obj.payments.first()
        if payment:
            return payment.method
            
        # 检查是否为信用支付
        # 这里为了避免循环引用，在方法内部导入
        from users.models import AccountTransaction
        # 检查是否存在关联的采购交易
        if AccountTransaction.objects.filter(order_id=obj.id, transaction_type='purchase').exists():
            return 'credit'
            
        return 'unknown'

    def get_refunded_amount(self, obj: Order) -> str:
        from django.db.models import Sum
        from decimal import Decimal
        total = obj.refunds.filter(status='succeeded').aggregate(total=Sum('amount')).get('total') or Decimal('0')
        return str(total)

    def get_refundable_amount(self, obj: Order) -> str:
        from .payment_service import PaymentService
        return str(PaymentService.calculate_refundable_amount(obj))

    def get_refund_pending(self, obj: Order) -> bool:
        return obj.refunds.filter(status__in=['pending', 'processing']).exists()

    def get_refund_action_required(self, obj: Order) -> bool:
        return obj.refunds.filter(status__in=['pending', 'failed']).exists()

    def get_refund_locked(self, obj: Order) -> bool:
        return obj.refunds.exists()
    
    def get_is_haier_order(self, obj: Order) -> bool:
        """判断是否为海尔订单"""
        return is_haier_order(obj)

    def _shipping_capabilities(self, obj: Order) -> dict:
        return get_shipping_capabilities(obj)

    def get_can_cancel_shipping(self, obj: Order) -> bool:
        return self._shipping_capabilities(obj)['can_cancel_shipping']

    def get_is_reshipment_pending(self, obj: Order) -> bool:
        return self._shipping_capabilities(obj)['is_reshipment_pending']

    def get_reship_requires_wechat_sync(self, obj: Order) -> bool:
        return self._shipping_capabilities(obj)['reship_requires_wechat_sync']

    def get_shipping_cancel_count(self, obj: Order) -> int:
        return self._shipping_capabilities(obj)['shipping_cancel_count']
    
    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_haier_order_info(self, obj: Order):
        """获取海尔订单信息"""
        primary_product = obj.primary_product
        if not self.get_is_haier_order(obj):
            return None
        
        return {
            'haier_order_no': obj.haier_order_no,
            'haier_so_id': obj.haier_so_id,
            'haier_status': obj.haier_status,
            'haier_fail_msg': obj.haier_fail_msg,
            'product_code': primary_product.product_code if primary_product else '',
        }
    
    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_logistics_info(self, obj: Order):
        """获取物流信息"""
        # 只要有任意一项物流相关信息，就返回字典，确保前端能展示已有信息
        if not any([
            obj.logistics_no,
            obj.delivery_record_code,
            obj.sn_code,
            obj.delivery_images,
            obj.shipping_info,
        ]):
            return None
        
        request = self.context.get('request')
        return {
            'logistics_no': obj.logistics_no,
            'delivery_record_code': obj.delivery_record_code,
            'sn_code': obj.sn_code,
            'delivery_images': [_build_media_url(url, request) for url in (obj.delivery_images or [])],
            'shipping_info': obj.shipping_info or None,
        }

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_invoice_info(self, obj: Order):
        """获取发票信息"""
        if hasattr(obj, 'invoice'):
            return {
                'id': obj.invoice.id,
                'status': obj.invoice.status,
                'status_display': obj.invoice.get_status_display(),
                'invoice_number': obj.invoice.invoice_number,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_return_info(self, obj: Order):
        rr = getattr(obj, 'return_request', None)
        if not rr:
            return None
        mapping = {
            'requested': '已申请',
            'approved': '已同意',
            'in_transit': '退货在途',
            'received': '已收到退货',
            'rejected': '已拒绝',
        }
        return {
            'id': rr.id,
            'status': rr.status,
            'status_display': mapping.get(rr.status, rr.status),
            'reason': rr.reason,
            'tracking_number': rr.tracking_number,
            'evidence_images': rr.evidence_images,
            'created_at': rr.created_at,
            'updated_at': rr.updated_at,
            'processed_note': rr.processed_note,
            'processed_at': rr.processed_at,
        }

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_expires_at(self, obj: Order):
        if obj.status == 'pending':
            timeout = getattr(settings, 'ORDER_PAYMENT_TIMEOUT_MINUTES', 1440)
            return obj.created_at + timedelta(minutes=timeout)
        return None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_child_orders(self, obj: Order):
        """获取子订单列表（仅当为主订单时返回）"""
        if obj.order_type != 'main':
            return []

        # 使用预加载的 child_orders（如果可用）
        # Django 的 prefetch_related 将结果存储在 _prefetched_objects_cache 字典中
        child_orders = getattr(obj, '_prefetched_objects_cache', {}).get('child_orders', None)
        if child_orders is None:
            child_orders = obj.child_orders.all().order_by('created_at')

        result = []
        for child in child_orders:
            # 使用预加载的 items（如果可用）
            # prefetch_related('child_orders__items') 会将 items 存储在 _prefetched_objects_cache['items'] 中
            items = getattr(child, '_prefetched_objects_cache', {}).get('items', None)
            if items is None:
                product_count = child.items.count()
            else:
                product_count = len(items)  # items 已是列表，直接使用 len()

            result.append({
                'id': child.id,
                'order_number': child.order_number,
                'order_type': child.order_type,
                'status': child.status,
                'status_label': self.get_status_label(child),
                'total_amount': str(child.total_amount),
                'discount_amount': str(child.discount_amount),
                'actual_amount': str(child.actual_amount),
                'product_count': product_count,
                'quantity': child.total_quantity,
            })
        return result


class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    sku_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)

    def validate(self, attrs):
        product_id = attrs.get('product_id')
        sku_id = attrs.get('sku_id')
        try:
            Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError("商品不存在")
        if sku_id:
            from catalog.models import ProductSKU
            try:
                ProductSKU.objects.get(id=sku_id, product_id=product_id)
            except ProductSKU.DoesNotExist:
                raise serializers.ValidationError("SKU不存在或不属于该商品")
        return attrs


class OrderCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    address_id = serializers.IntegerField(write_only=True)
    quantity = serializers.IntegerField(write_only=True, required=False, min_value=1, default=1)
    sku_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    note = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=500, default='')
    payment_method = serializers.ChoiceField(
        choices=['online', 'credit'],
        write_only=True,
        required=False,
        default='online',
        help_text='支付方式: online-在线支付, credit-信用支付'
    )
    items = OrderCreateItemSerializer(many=True, required=False, write_only=True)

    def validate_product_id(self, value):
        if value is None:
            return value
        try:
            Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("商品不存在")
        return value

    def validate_address_id(self, value):
        try:
            Address.objects.get(id=value, user=self.context["request"].user)
        except Address.DoesNotExist:
            raise serializers.ValidationError("地址无效或不属于当前用户")
        return value

    def validate_quantity(self, value):
        if value is None:
            return 1
        if value <= 0:
            raise serializers.ValidationError("数量必须为正整数")
        return value

    def validate_payment_method(self, value):
        if value == 'credit':
            user = self.context["request"].user
            if user.role != 'dealer':
                raise serializers.ValidationError("只有经销商可以使用信用支付")
            if not hasattr(user, 'credit_account'):
                raise serializers.ValidationError("您还没有信用账户")
            if not user.credit_account.is_active:
                raise serializers.ValidationError("您的信用账户已停用")
        return value

    def validate(self, attrs):
        items = attrs.get('items') or []
        product_id = attrs.get('product_id')
        sku_id = attrs.get('sku_id')
        if not items and not product_id:
            raise serializers.ValidationError("请至少选择一种商品或SKU")
        if sku_id and not product_id and not items:
            raise serializers.ValidationError("sku_id 需要配合 product_id 使用")
        if sku_id and product_id:
            from catalog.models import ProductSKU
            if not ProductSKU.objects.filter(id=sku_id, product_id=product_id).exists():
                raise serializers.ValidationError("SKU不存在或不属于该商品")
        return attrs

    class Meta:
        model = Order
        fields = [
            "product_id",
            "sku_id",
            "address_id",
            "quantity",
            "note",
            "payment_method",
            "items",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField()  # Remove write_only to include in response
    sku = ProductSKUSerializer(read_only=True)
    sku_id = serializers.IntegerField(required=False, allow_null=True)
    sku_specs = serializers.SerializerMethodField()
    store_id = serializers.IntegerField(source="product.store_id", read_only=True)
    store_name = serializers.CharField(source="product.store.name", read_only=True)
    store_logo = serializers.SerializerMethodField()
    store_type = serializers.CharField(source="product.store.store_type", read_only=True)
    store_is_main = serializers.BooleanField(source="product.store.is_main", read_only=True)
    is_available = serializers.SerializerMethodField()
    unavailable_reason = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_id",
            "sku",
            "sku_id",
            "sku_specs",
            "quantity",
            "store_id",
            "store_name",
            "store_logo",
            "store_type",
            "store_is_main",
            "is_available",
            "unavailable_reason",
        ]

    @extend_schema_field(serializers.DictField())
    def get_sku_specs(self, obj: CartItem):
        if obj.sku_id and obj.sku and obj.sku.specs:
            return obj.sku.specs
        return {}

    @extend_schema_field(serializers.CharField())
    def get_store_logo(self, obj: CartItem):
        request = self.context.get("request")
        store = getattr(obj.product, "store", None)
        return _build_media_url(getattr(store, "logo", ""), request)

    def _availability_reason(self, obj: CartItem) -> str:
        product = obj.product
        if not product.is_active:
            return "商品已下架"
        if product.store.store_type == Store.TYPE_PARTNER:
            return "合作店铺商品仅展示，暂不支持购买"
        if obj.sku_id:
            if not obj.sku or not obj.sku.is_active:
                return "规格已下架"
            if obj.quantity > obj.sku.stock:
                return "库存不足"
            return ""
        if obj.quantity > product.stock:
            return "库存不足"
        return ""

    @extend_schema_field(serializers.BooleanField())
    def get_is_available(self, obj: CartItem):
        return self._availability_reason(obj) == ""

    @extend_schema_field(serializers.CharField())
    def get_unavailable_reason(self, obj: CartItem):
        return self._availability_reason(obj)

class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    store_groups = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "items",
            "store_groups",
        ]

    @extend_schema_field(CartItemSerializer(many=True))
    def get_items(self, obj: Cart):
        items = sorted(obj.items.all(), key=lambda cart_item: cart_item.id)
        return CartItemSerializer(items, many=True, context=self.context).data

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_store_groups(self, obj: Cart):
        item_serializer = CartItemSerializer(context=self.context)
        groups = OrderedDict()

        for item in sorted(obj.items.all(), key=lambda cart_item: cart_item.id):
            product = item.product
            store = product.store
            group = groups.setdefault(
                store.id,
                {
                    "store_id": store.id,
                    "store_name": store.name,
                    "store_logo": _build_media_url(store.logo, self.context.get("request")),
                    "store_type": store.store_type,
                    "store_is_main": store.is_main,
                    "item_count": 0,
                    "total_quantity": 0,
                    "items": [],
                },
            )
            group["item_count"] += 1
            group["total_quantity"] += item.quantity
            group["items"].append(item_serializer.to_representation(item))

        return list(groups.values())


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'method', 'status',
            'profit_sharing_required', 'profit_sharing_status', 'profit_sharing_unfrozen',
            'created_at', 'updated_at', 'expires_at', 'logs'
        ]


class StoreProfitSharingEntrySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    checkout_number = serializers.CharField(source='checkout_order.checkout_number', read_only=True)
    suborder_number = serializers.CharField(source='suborder.suborder_number', read_only=True)

    class Meta:
        model = StoreProfitSharingEntry
        fields = [
            'id', 'checkout_order', 'checkout_number', 'payment', 'order', 'suborder',
            'suborder_number', 'store', 'store_name', 'store_type_snapshot',
            'gross_amount', 'commission_rate_snapshot', 'commission_amount',
            'sharing_amount', 'retained_amount', 'receiver_type', 'receiver_account',
            'receiver_name_snapshot', 'status', 'available_at', 'shared_at',
            'failure_reason', 'logs', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class WechatProfitSharingOrderSerializer(serializers.ModelSerializer):
    entry_ids = serializers.PrimaryKeyRelatedField(source='entries', many=True, read_only=True)

    class Meta:
        model = WechatProfitSharingOrder
        fields = [
            'id', 'payment', 'checkout_order', 'entry_ids', 'out_order_no',
            'transaction_id', 'receivers', 'amount', 'unfreeze_unsplit',
            'status', 'wechat_response', 'error_message', 'operator',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class RefundSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(source='payment.method', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = Refund
        fields = [
            'id', 'order', 'order_number', 'payment', 'payment_method',
            'amount', 'status', 'reason', 'evidence_images', 'transaction_id',
            'operator', 'logs', 'created_at', 'updated_at'
        ]


class RefundCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ['order', 'payment', 'amount', 'reason', 'evidence_images']

    def validate(self, attrs):
        order = attrs.get('order')
        payment = attrs.get('payment')
        amount = attrs.get('amount')
        request = self.context.get('request')

        if not order:
            raise serializers.ValidationError('缺少订单信息')

        if payment and payment.order_id != order.id:
            raise serializers.ValidationError('支付记录不属于该订单')

        if order.status in ['cancelled', 'refunded']:
            raise serializers.ValidationError('当前订单状态不支持退款')

        if Refund.objects.filter(order=order).exists():
            raise serializers.ValidationError('该订单已存在退款记录，请联系商家处理')

        from .payment_service import PaymentService
        refundable = PaymentService.calculate_refundable_amount(order)
        if amount is None or amount <= 0:
            raise serializers.ValidationError('退款金额必须大于0')
        if amount > refundable:
            raise serializers.ValidationError(f'退款金额超出可退金额，可退 {refundable}')

        evidence_images = attrs.get('evidence_images') or []
        if evidence_images:
            if not isinstance(evidence_images, list):
                raise serializers.ValidationError('退款凭证格式不正确')
            if len(evidence_images) > 3:
                raise serializers.ValidationError('退款凭证最多上传3张')
            if not all(isinstance(item, str) and item for item in evidence_images):
                raise serializers.ValidationError('退款凭证格式不正确')

        if order.status != 'completed':
            raise serializers.ValidationError('仅支持已收货订单申请退款')

        # 普通用户只能操作自己的订单
        if request and not (is_platform_admin(request.user) or is_support_user(request.user)):
            if order.user_id != request.user.id:
                raise serializers.ValidationError('没有权限为该订单退款')

        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    product_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'order', 'order_number', 'product_name', 'user', 'username', 'title', 'taxpayer_id', 'email', 'phone',
            'address', 'bank_account', 'invoice_type', 'amount', 'tax_rate', 'tax_amount', 'status',
            'status_label', 'invoice_number', 'requested_at', 'issued_at', 'updated_at'
        ]

    def get_status_label(self, obj: Invoice) -> str:
        mapping = {
            'requested': '已申请',
            'issued': '已开具',
            'cancelled': '已取消',
        }
        return mapping.get(obj.status, obj.status)

    def get_product_name(self, obj: Invoice) -> str:
        order = obj.order
        if hasattr(order, 'primary_item') and order.primary_item:
            return order.primary_item.product_name
        return order.product.name if order.product else ''


class InvoiceCreateSerializer(serializers.ModelSerializer):
    invoice_type = serializers.ChoiceField(choices=['normal', 'special'], required=False, default='normal')
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)

    class Meta:
        model = Invoice
        fields = [
            'title', 'taxpayer_id', 'email', 'phone', 'address', 'bank_account', 'invoice_type', 'tax_rate'
        ]

    def validate(self, attrs):
        order: Order = self.context.get('order')
        request = self.context.get('request')
        if not order or not request:
            raise serializers.ValidationError('缺少订单或请求上下文')
        if order.status != 'completed':
            raise serializers.ValidationError('仅已完成的订单可以申请发票')
        if hasattr(order, 'invoice') and order.invoice and order.invoice.status != 'cancelled':
            raise serializers.ValidationError('该订单已申请或已开具发票')
        return attrs

    def create(self, validated_data):
        order: Order = self.context['order']
        user = self.context['request'].user
        amount = order.actual_amount
        tax_rate = validated_data.pop('tax_rate', 0) or 0
        tax_amount = (amount * tax_rate) / 100 if tax_rate else 0
        inv = Invoice.objects.create(
            order=order,
            user=user,
            amount=amount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            status='requested',
            **validated_data
        )
        return inv


class ReturnRequestSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'order', 'user', 'status', 'status_label', 'reason',
            'tracking_number', 'evidence_images',
            'created_at', 'updated_at', 'processed_note', 'processed_at'
        ]

    def get_status_label(self, obj: ReturnRequest) -> str:
        mapping = {
            'requested': '已申请',
            'approved': '已同意',
            'in_transit': '退货在途',
            'received': '已收到退货',
            'rejected': '已拒绝',
        }
        return mapping.get(obj.status, obj.status)


class ReturnRequestCreateSerializer(serializers.ModelSerializer):
    evidence_images = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = ReturnRequest
        fields = ['reason', 'evidence_images']

    def validate(self, attrs):
        order: Order = self.context.get('order')
        request = self.context.get('request')
        if not order or not request:
            raise serializers.ValidationError('缺少订单或请求上下文')
        if hasattr(order, 'return_request') and order.return_request:
            raise serializers.ValidationError('该订单已存在退货申请')
        if order.status not in {'paid', 'shipped', 'completed'}:
            raise serializers.ValidationError('仅待发货/待收货/已完成订单可申请退货')
        reason = attrs.get('reason')
        if not reason or not str(reason).strip():
            raise serializers.ValidationError('退货原因不能为空')
        return attrs

    def create(self, validated_data):
        order: Order = self.context['order']
        user = self.context['request'].user
        rr = ReturnRequest.objects.create(
            order=order,
            user=user,
            reason=validated_data.get('reason'),
            evidence_images=validated_data.get('evidence_images') or []
        )
        return rr


class DiscountTargetSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    retail_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    dealer_price = serializers.DecimalField(source='product.dealer_price', max_digits=10, decimal_places=2, read_only=True)
    discounted_retail_price = serializers.SerializerMethodField()
    discounted_dealer_price = serializers.SerializerMethodField()

    class Meta:
        model = DiscountTarget
        fields = [
            'id', 'discount', 'user', 'product', 
            'product_name', 'retail_price', 'dealer_price', 
            'discounted_retail_price', 'discounted_dealer_price'
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True))
    def get_discounted_retail_price(self, obj):
        if not obj.product or obj.product.price is None:
            return None
        discount_amount = obj.discount.resolve_discount_amount(obj.product.price)
        return obj.product.price - discount_amount

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True))
    def get_discounted_dealer_price(self, obj):
        if not obj.product or obj.product.dealer_price is None:
            return None
        discount_amount = obj.discount.resolve_discount_amount(obj.product.dealer_price)
        return obj.product.dealer_price - discount_amount


class DiscountSerializer(serializers.ModelSerializer):
    targets = DiscountTargetSerializer(many=True, read_only=True)
    # 批量设置适用范围（写入时使用）：用户与商品ID列表
    user_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    product_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Discount
        fields = [
            'id', 'name', 'discount_type', 'amount', 'effective_time', 'expiration_time', 'priority', 'created_at', 'updated_at', 'targets',
            'user_ids', 'product_ids'
        ]

    def validate(self, attrs):
        discount_type = attrs.get('discount_type') or getattr(self.instance, 'discount_type', Discount.TYPE_AMOUNT)
        amount = attrs.get('amount', getattr(self.instance, 'amount', None))
        if discount_type == Discount.TYPE_PERCENT:
            if amount is None:
                raise serializers.ValidationError({'amount': '请输入折扣率'})
            if amount <= 0 or amount > 10:
                raise serializers.ValidationError({'amount': '折扣率需在 0 到 10 之间'})
        return attrs

    def create(self, validated_data):
        user_ids = list(set(validated_data.pop('user_ids', []) or []))
        product_ids = list(set(validated_data.pop('product_ids', []) or []))
        discount = super().create(validated_data)
        # 若同时提供用户与商品，则批量建立适用范围
        if user_ids and product_ids:
            targets = [
                DiscountTarget(discount=discount, user_id=uid, product_id=pid)
                for uid in user_ids for pid in product_ids
            ]
            # 忽略唯一约束冲突（理论上不会因新建而冲突）
            DiscountTarget.objects.bulk_create(targets, ignore_conflicts=True)
        return discount

    def update(self, instance, validated_data):
        # 支持通过传入 user_ids / product_ids 重置适用范围：
        # - 若两者都提供：使用两者的笛卡尔积覆盖原有范围
        # - 若只提供其一：与当前另一维的集合做笛卡尔积覆盖
        user_ids_raw = validated_data.pop('user_ids', None)
        product_ids_raw = validated_data.pop('product_ids', None)
        discount = super().update(instance, validated_data)

        if user_ids_raw is not None or product_ids_raw is not None:
            # 当前已有的集合
            current_users = list(
                DiscountTarget.objects.filter(discount=discount).values_list('user_id', flat=True).distinct()
            )
            current_products = list(
                DiscountTarget.objects.filter(discount=discount).values_list('product_id', flat=True).distinct()
            )

            user_ids = list(set((user_ids_raw or current_users) or []))
            product_ids = list(set((product_ids_raw or current_products) or []))

            # 覆盖原有范围
            DiscountTarget.objects.filter(discount=discount).delete()
            if user_ids and product_ids:
                targets = [
                    DiscountTarget(discount=discount, user_id=uid, product_id=pid)
                    for uid in user_ids for pid in product_ids
                ]
                DiscountTarget.objects.bulk_create(targets, ignore_conflicts=True)
        return discount
