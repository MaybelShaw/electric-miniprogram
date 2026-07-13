from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PartnerEntryConfigAPIView,
    PublicPartnerStoreListAPIView,
    PublicPartnerEntryConfigAPIView,
    PublicStoreDetailAPIView,
    StoreCustomerGroupMemberViewSet,
    StoreCustomerGroupPriceViewSet,
    StoreCustomerGroupViewSet,
    StoreMemberViewSet,
    StorePaymentConfigViewSet,
    StoreSettlementRuleViewSet,
    StoreViewSet,
)

router = DefaultRouter()
router.register(r"customer-groups", StoreCustomerGroupViewSet, basename="store-customer-groups")
router.register(r"customer-group-members", StoreCustomerGroupMemberViewSet, basename="store-customer-group-members")
router.register(r"customer-group-prices", StoreCustomerGroupPriceViewSet, basename="store-customer-group-prices")
router.register(r"members", StoreMemberViewSet, basename="store-members")
router.register(r"payment-configs", StorePaymentConfigViewSet, basename="store-payment-configs")
router.register(r"settlement-rules", StoreSettlementRuleViewSet, basename="store-settlement-rules")
router.register(r"", StoreViewSet, basename="stores")

urlpatterns = [
    path("partner-entry-config/", PartnerEntryConfigAPIView.as_view(), name="partner-entry-config"),
    path("public/partner-entry-config/", PublicPartnerEntryConfigAPIView.as_view(), name="public-partner-entry-config"),
    path("public/partners/", PublicPartnerStoreListAPIView.as_view(), name="public-partner-stores"),
    path("public/<int:pk>/detail/", PublicStoreDetailAPIView.as_view(), name="public-store-detail"),
    path("", include(router.urls)),
]
