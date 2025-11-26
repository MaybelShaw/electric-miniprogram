from rest_framework import serializers
from .models import User, Address
from django.core.cache import cache


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with statistics.
    
    Includes computed fields for user statistics:
    - orders_count: Total number of orders
    - completed_orders_count: Number of completed orders
    """
    orders_count = serializers.SerializerMethodField()
    completed_orders_count = serializers.SerializerMethodField()
    
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

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "avatar_url",
            "phone",
            "email",
        ]

    def validate(self, data):
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
