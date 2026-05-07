from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Store, StoreMember


def is_platform_admin(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return StoreMember.objects.filter(
        user=user,
        role=StoreMember.ROLE_PLATFORM_ADMIN,
        status=StoreMember.STATUS_ACTIVE,
        store__is_main=True,
        store__status=Store.STATUS_ACTIVE,
    ).exists()


def is_support_user(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False) and getattr(user, "role", "") == "support")


def get_active_memberships(user):
    if not user or not getattr(user, "is_authenticated", False):
        return StoreMember.objects.none()
    return StoreMember.objects.filter(
        user=user,
        status=StoreMember.STATUS_ACTIVE,
        store__status=Store.STATUS_ACTIVE,
    ).select_related("store")


def get_accessible_stores(user):
    if is_platform_admin(user) or is_support_user(user):
        return Store.objects.filter(status=Store.STATUS_ACTIVE).order_by("-is_main", "id")
    memberships = get_active_memberships(user)
    return Store.objects.filter(id__in=memberships.values("store_id")).order_by("-is_main", "id")


def get_default_store(user=None):
    if is_platform_admin(user):
        return Store.objects.filter(is_main=True).first() or Store.objects.order_by("id").first()
    return get_accessible_stores(user).first()


def can_access_store(user, store) -> bool:
    if store is None:
        return False
    if is_platform_admin(user) or is_support_user(user):
        return True
    return get_active_memberships(user).filter(store=store).exists()


def can_manage_store(user, store) -> bool:
    if is_platform_admin(user):
        return True
    return get_active_memberships(user).filter(
        store=store,
        role__in=[StoreMember.ROLE_STORE_ADMIN, StoreMember.ROLE_STORE_STAFF],
    ).exists()


def has_store_role(user, store, roles) -> bool:
    if store is None:
        return False
    if isinstance(roles, str):
        roles = [roles]
    return get_active_memberships(user).filter(store=store, role__in=roles).exists()


def can_view_store_dashboard(user, store) -> bool:
    return can_access_store(user, store)


def can_manage_store_catalog(user, store) -> bool:
    return is_platform_admin(user) or has_store_role(
        user,
        store,
        [StoreMember.ROLE_STORE_ADMIN, StoreMember.ROLE_STORE_STAFF],
    )


def can_manage_store_operations(user, store) -> bool:
    return is_platform_admin(user) or has_store_role(
        user,
        store,
        [StoreMember.ROLE_STORE_ADMIN, StoreMember.ROLE_STORE_STAFF],
    )


def get_requested_store(request, *, required=False, allow_public=False):
    user = getattr(request, "user", None)
    store_id = request.query_params.get("store") or request.query_params.get("store_id")
    if store_id in (None, "") and hasattr(request, "data"):
        store_id = request.data.get("store") or request.data.get("store_id")
    if store_id not in (None, ""):
        try:
            store = Store.objects.get(id=int(store_id), status=Store.STATUS_ACTIVE)
        except (Store.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"store": "Invalid store."})
        if not can_access_store(user, store):
            has_store_membership = bool(user and getattr(user, "is_authenticated", False) and get_active_memberships(user).exists())
            if allow_public and not has_store_membership:
                return store
            raise PermissionDenied("You cannot access this store.")
        return store
    if required:
        store = get_default_store(user)
        if not store:
            raise PermissionDenied("No accessible store.")
        return store
    return None


def filter_queryset_by_store(queryset, request, field="store"):
    user = getattr(request, "user", None)
    requested_store = get_requested_store(
        request,
        allow_public=getattr(request, "method", "GET") in ("GET", "HEAD", "OPTIONS"),
    )
    filter_key = f"{field}_id"

    if requested_store is not None:
        return queryset.filter(**{filter_key: requested_store.id})

    if user and getattr(user, "is_authenticated", False):
        if is_platform_admin(user):
            return queryset
        store_ids = list(get_accessible_stores(user).values_list("id", flat=True))
        if not store_ids:
            return queryset.none()
        return queryset.filter(**{f"{field}_id__in": store_ids})

    main_store = Store.objects.filter(is_main=True).first()
    if main_store:
        return queryset.filter(**{filter_key: main_store.id})
    return queryset


def validate_store_scope(instance_store, related_store, field_name):
    if instance_store and related_store and instance_store_id(instance_store) != instance_store_id(related_store):
        raise DjangoValidationError({field_name: "Related object must belong to the same store."})


def instance_store_id(store):
    return getattr(store, "id", store)
