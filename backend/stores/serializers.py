from rest_framework import serializers

from .models import Store, StoreMember, StorePaymentConfig, StoreSettlementRule


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "code",
            "status",
            "is_main",
            "allow_haier",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StoreMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = StoreMember
        fields = [
            "id",
            "user",
            "username",
            "store",
            "store_name",
            "role",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "username", "store_name", "created_at", "updated_at"]


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
