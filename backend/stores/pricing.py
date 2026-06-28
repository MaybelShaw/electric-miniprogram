from decimal import Decimal

from .models import Store, StoreCustomerGroupMember, StoreCustomerGroupPrice


EMPTY_CUSTOMER_GROUP_CONTEXT = {
    "customer_group_id": None,
    "customer_group_name": "",
    "show_customer_group_name": False,
}


def _normalized_phone(user) -> str:
    return (getattr(user, "phone", "") or "").strip()


def get_customer_group_membership(user, store: Store):
    if not user or not getattr(user, "is_authenticated", False) or store is None:
        return None

    membership = (
        StoreCustomerGroupMember.objects.select_related("group", "store")
        .filter(
            store=store,
            user=user,
            status=StoreCustomerGroupMember.STATUS_ACTIVE,
            group__status="active",
            group__store__status=Store.STATUS_ACTIVE,
        )
        .first()
    )
    if membership:
        return membership

    phone = _normalized_phone(user)
    if not phone:
        return None

    pending = (
        StoreCustomerGroupMember.objects.select_related("group", "store")
        .filter(
            store=store,
            user__isnull=True,
            phone=phone,
            status=StoreCustomerGroupMember.STATUS_ACTIVE,
            group__status="active",
            group__store__status=Store.STATUS_ACTIVE,
        )
        .first()
    )
    if not pending:
        return None

    if not StoreCustomerGroupMember.objects.filter(store=store, user=user).exists():
        pending.user = user
        pending.save(update_fields=["user", "updated_at"])
    return pending


def resolve_customer_group_price(user, product, sku=None):
    if not product:
        return None

    membership = get_customer_group_membership(user, getattr(product, "store", None))
    if not membership:
        return None

    price_qs = StoreCustomerGroupPrice.objects.filter(group=membership.group, product=product)
    if sku is not None:
        price = price_qs.filter(sku=sku).values_list("price", flat=True).first()
        if price is None:
            price = price_qs.filter(sku__isnull=True).values_list("price", flat=True).first()
    else:
        price = price_qs.filter(sku__isnull=True).values_list("price", flat=True).first()

    if price is None:
        return None
    return Decimal(price)


def get_customer_group_price_context(user, product):
    if not product:
        return EMPTY_CUSTOMER_GROUP_CONTEXT.copy()
    membership = get_customer_group_membership(user, getattr(product, "store", None))
    if not membership:
        return EMPTY_CUSTOMER_GROUP_CONTEXT.copy()
    return {
        "customer_group_id": membership.group_id,
        "customer_group_name": membership.group.name,
        "show_customer_group_name": bool(membership.store.show_customer_group_name),
    }
