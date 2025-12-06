from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet,
    CartViewSet,
    PaymentViewSet,
    RefundViewSet,
    DiscountViewSet,
    PaymentCallbackView,
    AnalyticsViewSet,
    InvoiceViewSet,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'refunds', RefundViewSet, basename='refunds')
router.register(r'discounts', DiscountViewSet, basename='discounts')
router.register(r'invoices', InvoiceViewSet, basename='invoices')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
urlpatterns = [
    path("", include(router.urls)),
    # 第三方支付回调模拟：/api/payments/callback/<provider>/
    path("payments/callback/<str:provider>/", PaymentCallbackView.as_view(), name="payment-callback"),
]
