from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupportTicketViewSet, SupportMessageViewSet, SupportChatViewSet, SupportApiRootView
from backend.settings.env_config import EnvironmentConfig

app_name = 'support'

router = DefaultRouter()
if EnvironmentConfig.is_development():
    router.register('chat', SupportChatViewSet, basename='support-chat')
    router.register('tickets', SupportTicketViewSet, basename='support-ticket')
    router.register('messages', SupportMessageViewSet, basename='support-message')
else:
    router.register('chat', SupportChatViewSet, basename='support-chat')
    router.register('tickets', SupportTicketViewSet, basename='support-ticket')
    router.register('messages', SupportMessageViewSet, basename='support-message')


urlpatterns = [
    path('', SupportApiRootView.as_view(), name='support-root'),
    path('', include(router.urls)),
]
