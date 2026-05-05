from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Store, StoreMember, StorePaymentConfig, StoreSettlementRule
from .permissions import get_accessible_stores, get_default_store, is_platform_admin
from .serializers import (
    StoreMemberSerializer,
    StorePaymentConfigSerializer,
    StoreSerializer,
    StoreSettlementRuleSerializer,
)


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_accessible_stores(self.request.user)

    def perform_create(self, serializer):
        if not is_platform_admin(self.request.user):
            raise PermissionDenied("Only platform admins can create stores.")
        serializer.save()

    def perform_update(self, serializer):
        if not is_platform_admin(self.request.user):
            raise PermissionDenied("Only platform admins can update stores.")
        serializer.save()

    def perform_destroy(self, instance):
        if not is_platform_admin(self.request.user):
            raise PermissionDenied("Only platform admins can delete stores.")
        instance.delete()

    @action(detail=False, methods=["get"])
    def current(self, request):
        stores = list(get_accessible_stores(request.user))
        default_store = get_default_store(request.user)
        memberships = StoreMember.objects.filter(user=request.user, store__in=stores).select_related("store")
        return Response(
            {
                "is_platform_admin": is_platform_admin(request.user),
                "default_store": StoreSerializer(default_store).data if default_store else None,
                "stores": StoreSerializer(stores, many=True).data,
                "memberships": StoreMemberSerializer(memberships, many=True).data,
            }
        )


class StoreMemberViewSet(viewsets.ModelViewSet):
    serializer_class = StoreMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if is_platform_admin(self.request.user):
            return StoreMember.objects.select_related("user", "store").all()
        return StoreMember.objects.select_related("user", "store").filter(user=self.request.user)

    def perform_create(self, serializer):
        if not is_platform_admin(self.request.user):
            raise PermissionDenied("Only platform admins can create store members.")
        serializer.save()

    def perform_update(self, serializer):
        if not is_platform_admin(self.request.user):
            raise PermissionDenied("Only platform admins can update store members.")
        serializer.save()


class StorePaymentConfigViewSet(viewsets.ModelViewSet):
    serializer_class = StorePaymentConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stores = get_accessible_stores(self.request.user)
        return StorePaymentConfig.objects.filter(store__in=stores).select_related("store")


class StoreSettlementRuleViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSettlementRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stores = get_accessible_stores(self.request.user)
        return StoreSettlementRule.objects.filter(store__in=stores).select_related("store")
