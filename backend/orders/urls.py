from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet,
    CartViewSet,
    PaymentViewSet,
    RefundViewSet,
    DiscountViewSet,
    PaymentCallbackView,
    RefundCallbackView,
    AnalyticsViewSet,
    InvoiceViewSet,
    StoreProfitSharingEntryViewSet,
    WechatProfitSharingOrderViewSet,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'refunds', RefundViewSet, basename='refunds')
router.register(r'discounts', DiscountViewSet, basename='discounts')
router.register(r'invoices', InvoiceViewSet, basename='invoices')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'profit-sharing-entries', StoreProfitSharingEntryViewSet, basename='profit-sharing-entries')
router.register(r'wechat-profit-sharing-orders', WechatProfitSharingOrderViewSet, basename='wechat-profit-sharing-orders')
urlpatterns = [
    path("", include(router.urls)),
    # 微信支付、退款回调
    path("payments/callback/<str:provider>/", PaymentCallbackView.as_view(), name="payment-callback"),
    path("payments/refund-callback/<str:provider>/", RefundCallbackView.as_view(), name="refund-callback"),
]
