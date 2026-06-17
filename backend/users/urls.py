from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    WeChatLoginView, 
    WeChatExplicitLoginView,
    AdminPasswordLoginView,
    PasswordLoginView, 
    AddressViewSet, 
    user_profile, 
    user_statistics, 
    AdminUserViewSet, 
    CompanyInfoViewSet,
    CreditAccountViewSet,
    AccountStatementViewSet,
    AccountTransactionViewSet,
    NotificationViewSet
)

router = SimpleRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'users', AdminUserViewSet, basename='users')
router.register(r'company-info', CompanyInfoViewSet, basename='company-info')
router.register(r'credit-accounts', CreditAccountViewSet, basename='credit-account')
router.register(r'account-statements', AccountStatementViewSet, basename='account-statement')
router.register(r'account-transactions', AccountTransactionViewSet, basename='account-transaction')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat-login'),
    path('wechat/explicit-login/', WeChatExplicitLoginView.as_view(), name='wechat-explicit-login'),
    path('password_login/', PasswordLoginView.as_view(), name='password-login'),
    path('admin/login/', AdminPasswordLoginView.as_view(), name='admin-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('user/profile/', user_profile, name='user-profile'),
    path('user/statistics/', user_statistics, name='user-statistics'),
    path('', include(router.urls)),
]
