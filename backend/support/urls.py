from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupportChatViewSet, SupportApiRootView

app_name = 'support'

router = DefaultRouter()
router.register('chat', SupportChatViewSet, basename='support-chat')

urlpatterns = [
    path('', SupportApiRootView.as_view(), name='support-root'),
    path('', include(router.urls)),
]
