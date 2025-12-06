from rest_framework import serializers
from .models import User, Address, CompanyInfo, CreditAccount, AccountStatement, AccountTransaction, Notification
from django.core.cache import cache


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with statistics.
    
    Includes computed fields for user statistics:
    - orders_count: Total number of orders
    - completed_orders_count: Number of completed orders
    - company_info: Company information for dealers
    """
    orders_count = serializers.SerializerMethodField()
    completed_orders_count = serializers.SerializerMethodField()
    company_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = "__all__"
    
    def get_orders_count(self, obj):
        """Get total number of orders for the user."""
        cache_key = f'user_orders_count_{obj.id}'
        count = cache.get(cache_key)
        
        if count is None:
            count = obj.orders.count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        
        return count
    
    def get_completed_orders_count(self, obj):
        """Get number of completed orders for the user."""
        cache_key = f'user_completed_orders_count_{obj.id}'
        count = cache.get(cache_key)
        
        if count is None:
            count = obj.orders.filter(status='completed').count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        
        return count
    
    def get_company_info(self, obj):
        """Get company info for dealers."""
        if hasattr(obj, 'company_info'):
            return {
                'company_name': obj.company_info.company_name,
                'status': obj.company_info.status,
            }
        return None

class UserProfileSerializer(serializers.ModelSerializer):
    has_company_info = serializers.SerializerMethodField()
    company_status = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            "username",
            "avatar_url",
            "phone",
            "email",
            "role",
            "has_company_info",
            "company_status",
            "company_name",
        ]
    
    def get_has_company_info(self, obj):
        """Check if user has company info"""
        return hasattr(obj, 'company_info')
    
    def get_company_status(self, obj):
        """Get company info approval status"""
        if hasattr(obj, 'company_info'):
            return obj.company_info.status
        return None
    
    def get_company_name(self, obj):
        """Get company name if approved"""
        if hasattr(obj, 'company_info') and obj.company_info.status == 'approved':
            return obj.company_info.company_name
        return None

    def validate(self, data):
        return data


class CompanyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInfo
        fields = [
            "id",
            "company_name",
            "business_license",
            "legal_representative",
            "contact_person",
            "contact_phone",
            "contact_email",
            "province",
            "city",
            "district",
            "detail_address",
            "business_scope",
            "status",
            "created_at",
            "updated_at",
            "approved_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at", "approved_at"]
    
    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)
    
    def validate(self, data):
        # Check if user already has company info
        user = self.context["request"].user
        if not self.instance and hasattr(user, 'company_info'):
            raise serializers.ValidationError("用户已提交公司信息")
        return data

class AddressSerializer(serializers.ModelSerializer):
    # full_address = serializers.CharField(source="get_full_address", read_only=True)

    class Meta:
        model = Address
        fields = [
            "id",
            "contact_name",
            "phone",
            "province",
            "city",
            "district",
            "detail",
            "is_default",
        ]

    def get_full_address(self, obj):
        return f"{obj.province} {obj.city} {obj.district} {obj.detail}"

    def validate(self, data):
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        is_default = validated_data.get("is_default", False)
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        validated_data["user"] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default", False) and not instance.is_default:
            Address.objects.filter(user=instance.user, is_default=True).update(
                is_default=False
            )
        return super().update(instance, validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器，用于站内信/订阅消息中心。"""
    is_read = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'content',
            'type',
            'type_display',
            'status',
            'status_display',
            'metadata',
            'created_at',
            'sent_at',
            'read_at',
            'is_read',
        ]
        read_only_fields = fields

    def get_is_read(self, obj):
        return bool(getattr(obj, 'read_at', None))


class CreditAccountSerializer(serializers.ModelSerializer):
    """信用账户序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    company_name = serializers.CharField(source='user.company_info.company_name', read_only=True)
    available_credit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CreditAccount
        fields = [
            'id',
            'user',
            'user_name',
            'company_name',
            'credit_limit',
            'payment_term_days',
            'outstanding_debt',
            'available_credit',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'outstanding_debt', 'created_at', 'updated_at']


class AccountStatementSerializer(serializers.ModelSerializer):
    """账务对账单序列化器"""
    user_name = serializers.CharField(source='credit_account.user.username', read_only=True)
    company_name = serializers.CharField(source='credit_account.user.company_info.company_name', read_only=True)
    
    class Meta:
        model = AccountStatement
        fields = [
            'id',
            'credit_account',
            'user_name',
            'company_name',
            'period_start',
            'period_end',
            'previous_balance',
            'current_purchases',
            'current_payments',
            'current_refunds',
            'period_end_balance',
            'due_within_term',
            'paid_within_term',
            'overdue_amount',
            'status',
            'created_at',
            'updated_at',
            'confirmed_at',
            'settled_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AccountTransactionSerializer(serializers.ModelSerializer):
    """账务交易记录序列化器"""
    user_name = serializers.CharField(source='credit_account.user.username', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    order_info = serializers.SerializerMethodField()
    
    class Meta:
        model = AccountTransaction
        fields = [
            'id',
            'credit_account',
            'user_name',
            'statement',
            'transaction_type',
            'transaction_type_display',
            'amount',
            'balance_after',
            'order_id',
            'order_info',
            'due_date',
            'paid_date',
            'payment_status',
            'payment_status_display',
            'description',
            'created_at',
        ]
        read_only_fields = ['id', 'balance_after', 'created_at']
    
    def get_order_info(self, obj):
        """获取订单详细信息"""
        if not obj.order_id:
            return None
        
        try:
            from orders.models import Order
            order = Order.objects.select_related('product').get(id=obj.order_id)
            return {
                'order_number': order.order_number,
                'product_name': order.product.name if order.product else None,
                'quantity': order.quantity,
                'status': order.status,
                'status_display': order.get_status_display(),
            }
        except:
            return None


class AccountStatementDetailSerializer(AccountStatementSerializer):
    """账务对账单详情序列化器（包含交易记录）"""
    transactions = AccountTransactionSerializer(many=True, read_only=True)
    
    class Meta(AccountStatementSerializer.Meta):
        fields = AccountStatementSerializer.Meta.fields + ['transactions']
