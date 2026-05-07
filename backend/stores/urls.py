from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PublicPartnerStoreListAPIView,
    PublicStoreDetailAPIView,
    StoreMemberViewSet,
    StorePaymentConfigViewSet,
    StoreSettlementRuleViewSet,
    StoreViewSet,
)

router = DefaultRouter()
router.register(r"members", StoreMemberViewSet, basename="store-members")
router.register(r"payment-configs", StorePaymentConfigViewSet, basename="store-payment-configs")
router.register(r"settlement-rules", StoreSettlementRuleViewSet, basename="store-settlement-rules")
router.register(r"", StoreViewSet, basename="stores")

urlpatterns = [
    path("public/partners/", PublicPartnerStoreListAPIView.as_view(), name="public-partner-stores"),
    path("public/<int:pk>/detail/", PublicStoreDetailAPIView.as_view(), name="public-store-detail"),
    path("", include(router.urls)),
]
