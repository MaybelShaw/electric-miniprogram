from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, Q

from .models import (
    Store,
    StoreCustomerGroup,
    StoreCustomerGroupMember,
    StoreCustomerGroupPrice,
    StoreMember,
    StorePaymentConfig,
    StoreSettlementRule,
)
from .permissions import (
    PERMISSION_CUSTOMER_GROUPS_MANAGE,
    PERMISSION_STORE_MEMBERS_MANAGE,
    get_accessible_stores,
    get_default_store,
    has_store_permission,
    is_platform_admin,
)
from .serializers import (
    PublicStoreSerializer,
    StoreCustomerGroupMemberSerializer,
    StoreCustomerGroupPriceSerializer,
    StoreCustomerGroupSerializer,
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
        qs = Store.objects.filter(
            status=Store.STATUS_ACTIVE,
            store_type=Store.TYPE_PARTNER,
            is_visible=True,
            show_on_home=True,
        )
        return qs.order_by("home_order", "id")


class PublicStoreDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PublicStoreSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Store.objects.filter(status=Store.STATUS_ACTIVE).exclude(
            store_type=Store.TYPE_PARTNER,
            is_visible=False,
        )

    def retrieve(self, request, *args, **kwargs):
        store = self.get_object()
        from catalog.models import Brand, Category, HomeBanner, Product, SpecialZone
        from catalog.serializers import BrandSerializer, CategorySerializer, HomeBannerSerializer, ProductSerializer, SpecialZoneSerializer

        context = self.get_serializer_context()
        category_id = request.query_params.get("category_id")
        products = Product.objects.filter(store=store, is_active=True).select_related("category", "brand").order_by("id")
        if category_id:
            products = products.filter(
                Q(category_id=category_id)
                | Q(category__parent_id=category_id)
                | Q(category__parent__parent_id=category_id)
            )
        brand_ids = products.values_list("brand_id", flat=True).distinct()
        brands = Brand.objects.filter(store=store, is_active=True, id__in=brand_ids).order_by("order", "id")
        new_arrivals = Product.objects.filter(store=store, is_active=True).select_related("category", "brand").order_by("-created_at", "-id")[:8]

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
                "brands": BrandSerializer(brands, many=True, context=context).data,
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
                "new_arrivals": ProductSerializer(new_arrivals, many=True, context=context).data,
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
            editable_fields = set(serializer.validated_data.keys())
            can_update_group_display = (
                editable_fields <= {"show_customer_group_name"}
                and has_store_permission(
                    self.request.user,
                    serializer.instance,
                    PERMISSION_CUSTOMER_GROUPS_MANAGE,
                )
            )
            if not can_update_group_display:
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
        qs = StoreMember.objects.select_related("user", "store").order_by("id")
        if is_platform_admin(self.request.user):
            return qs
        stores = [
            store
            for store in get_accessible_stores(self.request.user)
            if has_store_permission(self.request.user, store, PERMISSION_STORE_MEMBERS_MANAGE)
        ]
        if not stores:
            return qs.none()
        return qs.filter(store__in=stores).exclude(role=StoreMember.ROLE_PLATFORM_ADMIN)

    def _ensure_can_manage_member(self, store, role):
        if is_platform_admin(self.request.user):
            return
        if not has_store_permission(self.request.user, store, PERMISSION_STORE_MEMBERS_MANAGE):
            raise PermissionDenied("You cannot manage members of this store.")
        if role == StoreMember.ROLE_PLATFORM_ADMIN:
            raise PermissionDenied("Store admins cannot assign platform admin roles.")

    def perform_create(self, serializer):
        store = serializer.validated_data.get("store")
        role = serializer.validated_data.get("role")
        self._ensure_can_manage_member(store, role)
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        store = serializer.validated_data.get("store", instance.store)
        role = serializer.validated_data.get("role", instance.role)
        if not is_platform_admin(self.request.user) and instance.role == StoreMember.ROLE_PLATFORM_ADMIN:
            raise PermissionDenied("Store admins cannot update platform admins.")
        self._ensure_can_manage_member(store, role)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_can_manage_member(instance.store, instance.role)
        instance.delete()

    @action(detail=False, methods=["post"])
    def create_user_member(self, request):
        data = request.data
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        phone = (data.get("phone") or "").strip()
        email = (data.get("email") or "").strip()
        status_value = data.get("status") or StoreMember.STATUS_ACTIVE
        store_id = data.get("store")
        role = data.get("role") or StoreMember.ROLE_STORE_ADMIN

        if role != StoreMember.ROLE_STORE_ADMIN:
            raise ValidationError({"role": "只能创建店铺管理员。"})
        if status_value not in dict(StoreMember.STATUS_CHOICES):
            raise ValidationError({"status": "成员状态无效。"})
        if not username:
            raise ValidationError({"username": "请输入用户名。"})
        if not password:
            raise ValidationError({"password": "请输入密码。"})
        if not store_id:
            raise ValidationError({"store": "请选择店铺。"})

        try:
            store = Store.objects.get(pk=store_id)
        except (Store.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"store": "店铺不存在。"})

        self._ensure_can_manage_member(store, StoreMember.ROLE_STORE_ADMIN)

        from users.models import User

        if User.objects.filter(username=username).exists():
            raise ValidationError({"username": "用户名已存在。"})

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                phone=phone or None,
                email=email or None,
                role="admin",
                is_staff=True,
                is_superuser=False,
            )
            serializer = self.get_serializer(
                data={
                    "user": user.id,
                    "store": store.id,
                    "role": StoreMember.ROLE_STORE_ADMIN,
                    "status": status_value,
                }
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def available_users(self, request):
        if not is_platform_admin(request.user):
            manageable = any(
                has_store_permission(request.user, store, PERMISSION_STORE_MEMBERS_MANAGE)
                for store in get_accessible_stores(request.user)
            )
            if not manageable:
                raise PermissionDenied("You cannot manage store members.")
        from users.models import User
        from users.serializers import UserSerializer

        qs = User.objects.all().order_by("-date_joined")
        qs = qs.exclude(
            store_memberships__status=StoreMember.STATUS_ACTIVE,
            store_memberships__role__in=[
                StoreMember.ROLE_STORE_ADMIN,
                StoreMember.ROLE_STORE_SUB_ADMIN,
                StoreMember.ROLE_STORE_STAFF,
            ],
        )
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(username__icontains=search) | Q(phone__icontains=search) | Q(openid__icontains=search))
        return Response(UserSerializer(qs[:100], many=True).data)


def _stores_with_customer_group_permission(user):
    if is_platform_admin(user):
        return Store.objects.filter(status=Store.STATUS_ACTIVE).order_by("-is_main", "id")
    store_ids = [
        store.id
        for store in get_accessible_stores(user)
        if has_store_permission(user, store, PERMISSION_CUSTOMER_GROUPS_MANAGE)
    ]
    return Store.objects.filter(id__in=store_ids).order_by("-is_main", "id")


def _ensure_can_manage_customer_group_store(user, store):
    if is_platform_admin(user):
        return
    if not has_store_permission(user, store, PERMISSION_CUSTOMER_GROUPS_MANAGE):
        raise PermissionDenied("You cannot manage customer groups of this store.")


class StoreCustomerGroupViewSet(viewsets.ModelViewSet):
    serializer_class = StoreCustomerGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stores = _stores_with_customer_group_permission(self.request.user)
        qs = (
            StoreCustomerGroup.objects.select_related("store")
            .filter(store__in=stores)
            .annotate(
                member_count=Count("members", distinct=True),
                active_member_count=Count(
                    "members",
                    filter=Q(members__status=StoreCustomerGroupMember.STATUS_ACTIVE),
                    distinct=True,
                ),
                price_count=Count("prices", distinct=True),
            )
            .order_by("store_id", "id")
        )
        store_id = self.request.query_params.get("store") or self.request.query_params.get("store_id")
        if store_id not in (None, ""):
            qs = qs.filter(store_id=store_id)
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    def perform_create(self, serializer):
        store = serializer.validated_data.get("store")
        _ensure_can_manage_customer_group_store(self.request.user, store)
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        store = serializer.validated_data.get("store", instance.store)
        _ensure_can_manage_customer_group_store(self.request.user, instance.store)
        if store != instance.store:
            _ensure_can_manage_customer_group_store(self.request.user, store)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_can_manage_customer_group_store(self.request.user, instance.store)
        instance.delete()


class StoreCustomerGroupMemberViewSet(viewsets.ModelViewSet):
    serializer_class = StoreCustomerGroupMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stores = _stores_with_customer_group_permission(self.request.user)
        qs = (
            StoreCustomerGroupMember.objects.select_related("store", "group", "user")
            .filter(store__in=stores)
            .order_by("store_id", "id")
        )
        store_id = self.request.query_params.get("store") or self.request.query_params.get("store_id")
        if store_id not in (None, ""):
            qs = qs.filter(store_id=store_id)
        group_id = self.request.query_params.get("group") or self.request.query_params.get("group_id")
        if group_id not in (None, ""):
            qs = qs.filter(group_id=group_id)
        phone = self.request.query_params.get("phone")
        if phone:
            qs = qs.filter(phone__icontains=phone)
        return qs

    def perform_create(self, serializer):
        store = serializer.validated_data.get("store")
        _ensure_can_manage_customer_group_store(self.request.user, store)
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        store = serializer.validated_data.get("store", instance.store)
        _ensure_can_manage_customer_group_store(self.request.user, instance.store)
        if store != instance.store:
            _ensure_can_manage_customer_group_store(self.request.user, store)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_can_manage_customer_group_store(self.request.user, instance.store)
        instance.delete()


class StoreCustomerGroupPriceViewSet(viewsets.ModelViewSet):
    serializer_class = StoreCustomerGroupPriceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stores = _stores_with_customer_group_permission(self.request.user)
        qs = (
            StoreCustomerGroupPrice.objects.select_related("group", "group__store", "product", "sku")
            .filter(group__store__in=stores)
            .order_by("group_id", "product_id", "sku_id")
        )
        store_id = self.request.query_params.get("store") or self.request.query_params.get("store_id")
        if store_id not in (None, ""):
            qs = qs.filter(group__store_id=store_id)
        group_id = self.request.query_params.get("group") or self.request.query_params.get("group_id")
        if group_id not in (None, ""):
            qs = qs.filter(group_id=group_id)
        product_id = self.request.query_params.get("product") or self.request.query_params.get("product_id")
        if product_id not in (None, ""):
            qs = qs.filter(product_id=product_id)
        return qs

    def perform_create(self, serializer):
        group = serializer.validated_data.get("group")
        _ensure_can_manage_customer_group_store(self.request.user, group.store)
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        group = serializer.validated_data.get("group", instance.group)
        _ensure_can_manage_customer_group_store(self.request.user, instance.group.store)
        if group != instance.group:
            _ensure_can_manage_customer_group_store(self.request.user, group.store)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_can_manage_customer_group_store(self.request.user, instance.group.store)
        instance.delete()


class StorePaymentConfigViewSet(viewsets.ModelViewSet):
    serializer_class = StorePaymentConfigSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        stores = get_accessible_stores(self.request.user)
        return StorePaymentConfig.objects.filter(store__in=stores).select_related("store")

    def perform_create(self, serializer):
        instance = serializer.save()
        self._refresh_profit_sharing_entries(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._refresh_profit_sharing_entries(instance)

    @staticmethod
    def _refresh_profit_sharing_entries(instance):
        try:
            from orders.profit_sharing import ProfitSharingService
            ProfitSharingService.refresh_entries_for_store(instance.store)
        except Exception:
            pass


class StoreSettlementRuleViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSettlementRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get_queryset(self):
        stores = get_accessible_stores(self.request.user)
        return StoreSettlementRule.objects.filter(store__in=stores).select_related("store")
