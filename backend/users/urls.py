from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import WeChatLoginView, PasswordLoginView, AddressViewSet, user_profile, user_statistics, AdminUserViewSet

router = SimpleRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'users', AdminUserViewSet, basename='users')

urlpatterns = [
    path('login/', WeChatLoginView.as_view(), name='wechat-login'),
    path('password_login/', PasswordLoginView.as_view(), name='password-login'),
    path('admin/login/', PasswordLoginView.as_view(), name='admin-login'),  # 管理员登录别名
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('user/profile/', user_profile, name='user-profile'),
    path('user/statistics/', user_statistics, name='user-statistics'),
    path('', include(router.urls)),
]