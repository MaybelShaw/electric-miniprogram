from rest_framework import serializers
from .models import Order, Cart, CartItem, Payment, Discount, DiscountTarget
from catalog.models import Product
from users.models import Address
from catalog.serializers import ProductSerializer


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_label = serializers.SerializerMethodField()
    is_haier_order = serializers.SerializerMethodField()
    haier_order_info = serializers.SerializerMethodField()
    logistics_info = serializers.SerializerMethodField()

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
            "status",
            "status_label",
            "created_at",
            "updated_at",
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
            "distribution_time",
            "install_time",
            "is_delivery_install",
            "is_government_order",
            "cancel_reason",
            "cancelled_at",
        ]

    def get_status_label(self, obj: Order) -> str:
        mapping = {
            'pending': '待支付',
            'paid': '待发货',
            'shipped': '待收货',
            'completed': '已完成',
            'cancelled': '已取消',
            'refunding': '退款中',
            'refunded': '已退款',
        }
        return mapping.get(obj.status, obj.status)
    
    def get_is_haier_order(self, obj: Order) -> bool:
        """判断是否为海尔订单"""
        if not obj.product:
            return False
        # 只根据商品来源(source)判断
        return getattr(obj.product, 'source', None) == getattr(Product, 'SOURCE_HAIER', 'haier')
    
    def get_haier_order_info(self, obj: Order):
        """获取海尔订单信息"""
        if not obj.product:
            return None
        # 只有海尔订单且存在 product_code 时才返回
        if not self.get_is_haier_order(obj) or not obj.product.product_code:
            return None
        
        return {
            'haier_order_no': obj.haier_order_no,
            'haier_so_id': obj.haier_so_id,
            'haier_status': obj.haier_status,
            'product_code': obj.product.product_code,
        }
    
    def get_logistics_info(self, obj: Order):
        """获取物流信息"""
        if not obj.logistics_company and not obj.logistics_no:
            return None
        
        return {
            'logistics_company': obj.logistics_company,
            'logistics_no': obj.logistics_no,
            'delivery_record_code': obj.delivery_record_code,
            'sn_code': obj.sn_code,
            'delivery_images': obj.delivery_images,
        }


class OrderCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)
    address_id = serializers.IntegerField(write_only=True)
    quantity = serializers.IntegerField(write_only=True, required=False, min_value=1, default=1)
    note = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=500, default='')

    def validate_product_id(self, value):
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

    class Meta:
        model = Order
        fields = [
            "product_id",
            "address_id",
            "quantity",
            "note",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField()  # Remove write_only to include in response

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_id",
            "quantity",
        ]

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "items",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'method', 'status', 'created_at', 'updated_at', 'expires_at', 'logs'
        ]


class DiscountTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountTarget
        fields = ['id', 'discount', 'user', 'product']


class DiscountSerializer(serializers.ModelSerializer):
    targets = DiscountTargetSerializer(many=True, read_only=True)
    # 批量设置适用范围（写入时使用）：用户与商品ID列表
    user_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    product_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Discount
        fields = [
            'id', 'name', 'amount', 'effective_time', 'expiration_time', 'priority', 'created_at', 'updated_at', 'targets',
            'user_ids', 'product_ids'
        ]

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