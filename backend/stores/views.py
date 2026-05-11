from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.db.models import Q

from .models import Store, StoreMember, StorePaymentConfig, StoreSettlementRule
from .permissions import get_accessible_stores, get_default_store, is_platform_admin
from .serializers import (
    PublicStoreSerializer,
    StoreMemberSerializer,
    StorePaymentConfigSerializer,
    StoreSerializer,
    StoreSettlementRuleSerializer,
)


class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_platform_admin(getattr(request, "user", None))


class PublicPartnerStoreListAPIView(generics.ListAPIView):
    serializer_class = PublicStoreSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        platform_id = self.request.query_params.get("platform") or self.request.query_params.get("platform_store")
        platform = None
        if platform_id not in (None, ""):
            try:
                platform = Store.objects.get(id=int(platform_id), status=Store.STATUS_ACTIVE)
            except (Store.DoesNotExist, ValueError, TypeError):
                return Store.objects.none()
        else:
            platform = Store.objects.filter(is_main=True, status=Store.STATUS_ACTIVE).first()

        qs = Store.objects.filter(
            status=Store.STATUS_ACTIVE,
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
        )
        if platform is not None:
            qs = qs.filter(platform_store=platform)
        return qs.order_by("home_order", "id")


class PublicStoreDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PublicStoreSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Store.objects.filter(status=Store.STATUS_ACTIVE)

    def retrieve(self, request, *args, **kwargs):
        store = self.get_object()
        from catalog.models import Category, HomeBanner, Product, SpecialZone
        from catalog.serializers import CategorySerializer, HomeBannerSerializer, ProductSerializer, SpecialZoneSerializer

        context = self.get_serializer_context()
        category_id = request.query_params.get("category_id")
        products = Product.objects.filter(store=store, is_active=True).select_related("category", "brand").order_by("id")
        if category_id:
            products = products.filter(
                Q(category_id=category_id)
                | Q(category__parent_id=category_id)
                | Q(category__parent__parent_id=category_id)
            )

        return Response(
            {
                "store": PublicStoreSerializer(store, context=context).data,
                "banners": HomeBannerSerializer(
                    HomeBanner.objects.filter(store=store, is_active=True).order_by("order", "-id"),
                    many=True,
                    context=context,
                ).data,
                "categories": CategorySerializer(
                    Category.objects.filter(store=store, level=Category.LEVEL_MAJOR).order_by("order", "id"),
                    many=True,
                    context=context,
                ).data,
                "special_zones": SpecialZoneSerializer(
                    SpecialZone.objects.filter(
                        store=store,
                        kind__in=[SpecialZone.KIND_STORE_ACTIVITY, SpecialZone.KIND_ACTIVITY],
                        is_active=True,
                    ).order_by("home_order", "id"),
                    many=True,
                    context=context,
                ).data,
                "products": ProductSerializer(products[:20], many=True, context=context).data,
            }
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
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        return StoreMember.objects.select_related("user", "store").all()

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
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        stores = get_accessible_stores(self.request.user)
        return StorePaymentConfig.objects.filter(store__in=stores).select_related("store")


class StoreSettlementRuleViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSettlementRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        stores = get_accessible_stores(self.request.user)
        return StoreSettlementRule.objects.filter(store__in=stores).select_related("store")
