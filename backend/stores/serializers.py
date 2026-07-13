from rest_framework import serializers

from .models import (
    PartnerEntryConfig,
    Store,
    StoreCustomerGroup,
    StoreCustomerGroupMember,
    StoreCustomerGroupPrice,
    StoreMember,
    StorePaymentConfig,
    StoreSettlementRule,
)
from .permissions import get_membership_permissions
from drf_spectacular.utils import extend_schema_field


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "code",
            "status",
            "is_main",
            "store_type",
            "logo",
            "cover_image",
            "description",
            "is_visible",
            "show_on_home",
            "home_order",
            "contact_phone",
            "address",
            "allow_haier",
            "show_customer_group_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PublicStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "code",
            "is_main",
            "store_type",
            "logo",
            "cover_image",
            "description",
            "is_visible",
            "contact_phone",
            "address",
            "home_order",
        ]


class PartnerEntryConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerEntryConfig
        fields = ["entry_title", "entry_subtitle", "section_title"]


class StoreMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    store_is_main = serializers.BooleanField(source="store.is_main", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = StoreMember
        fields = [
            "id",
            "user",
            "username",
            "store",
            "store_name",
            "store_is_main",
            "role",
            "permissions",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "username", "store_name", "store_is_main", "permissions", "created_at", "updated_at"]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        return get_membership_permissions(obj)

    def validate(self, attrs):
        user = attrs.get("user", getattr(self.instance, "user", None))
        role = attrs.get("role", getattr(self.instance, "role", StoreMember.ROLE_STORE_ADMIN))
        status = attrs.get("status", getattr(self.instance, "status", StoreMember.STATUS_ACTIVE))
        if user and status == StoreMember.STATUS_ACTIVE and role != StoreMember.ROLE_PLATFORM_ADMIN:
            exists = (
                StoreMember.objects.filter(user=user, status=StoreMember.STATUS_ACTIVE)
                .exclude(role=StoreMember.ROLE_PLATFORM_ADMIN)
                .exclude(pk=getattr(self.instance, "pk", None))
                .exists()
            )
            if exists:
                raise serializers.ValidationError({"user": "后台账号只能绑定一个店铺。"})
        return attrs


class StoreCustomerGroupSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    member_count = serializers.IntegerField(read_only=True, default=0)
    active_member_count = serializers.IntegerField(read_only=True, default=0)
    price_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = StoreCustomerGroup
        fields = [
            "id",
            "store",
            "store_name",
            "name",
            "description",
            "status",
            "member_count",
            "active_member_count",
            "price_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "store_name",
            "member_count",
            "active_member_count",
            "price_count",
            "created_at",
            "updated_at",
        ]


class StoreCustomerGroupMemberSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = StoreCustomerGroupMember
        fields = [
            "id",
            "store",
            "store_name",
            "group",
            "group_name",
            "user",
            "username",
            "phone",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "store_name", "group_name", "username", "created_at", "updated_at"]

    def validate(self, attrs):
        store = attrs.get("store", getattr(self.instance, "store", None))
        group = attrs.get("group", getattr(self.instance, "group", None))
        phone = (attrs.get("phone", getattr(self.instance, "phone", "")) or "").strip()
        user = attrs.get("user", getattr(self.instance, "user", None))

        if group and store and group.store_id != store.id:
            raise serializers.ValidationError({"group": "客户分组必须属于同一店铺。"})

        if not user and phone:
            try:
                from users.models import User

                user = User.objects.filter(phone=phone).order_by("id").first()
            except Exception:
                user = None
            if user:
                attrs["user"] = user

        if not user and not phone:
            raise serializers.ValidationError({"phone": "手机号或用户必须至少填写一个。"})
        attrs["phone"] = phone or getattr(user, "phone", "") or ""
        return attrs


class StoreCustomerGroupPriceSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_source = serializers.CharField(source="product.source", read_only=True)
    product_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    sku_name = serializers.CharField(source="sku.name", read_only=True)
    sku_code = serializers.CharField(source="sku.sku_code", read_only=True)
    sku_price = serializers.DecimalField(source="sku.price", max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    store = serializers.IntegerField(source="group.store_id", read_only=True)

    class Meta:
        model = StoreCustomerGroupPrice
        fields = [
            "id",
            "store",
            "group",
            "group_name",
            "product",
            "product_name",
            "product_source",
            "product_price",
            "sku",
            "sku_name",
            "sku_code",
            "sku_price",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "store",
            "group_name",
            "product_name",
            "product_source",
            "product_price",
            "sku_name",
            "sku_code",
            "sku_price",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        group = attrs.get("group", getattr(self.instance, "group", None))
        product = attrs.get("product", getattr(self.instance, "product", None))
        sku = attrs.get("sku", getattr(self.instance, "sku", None))
        if group and product and group.store_id != product.store_id:
            raise serializers.ValidationError({"product": "商品必须属于客户分组所在店铺。"})
        if sku and product and sku.product_id != product.id:
            raise serializers.ValidationError({"sku": "SKU 必须属于当前商品。"})
        return attrs


class StorePaymentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorePaymentConfig
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class StoreSettlementRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettlementRule
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
