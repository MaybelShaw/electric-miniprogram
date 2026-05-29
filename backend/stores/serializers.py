from rest_framework import serializers

from .models import Store, StoreMember, StorePaymentConfig, StoreSettlementRule
from .permissions import get_membership_permissions


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
            "platform_store",
            "logo",
            "cover_image",
            "description",
            "show_on_home",
            "home_order",
            "contact_phone",
            "address",
            "allow_haier",
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
            "store_type",
            "platform_store",
            "logo",
            "cover_image",
            "description",
            "contact_phone",
            "address",
            "home_order",
        ]


class StoreMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = StoreMember
        fields = [
            "id",
            "user",
            "username",
            "store",
            "store_name",
            "role",
            "permissions",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "username", "store_name", "permissions", "created_at", "updated_at"]

    def get_permissions(self, obj):
        return get_membership_permissions(obj)


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
