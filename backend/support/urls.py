from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupportChatViewSet, SupportApiRootView, SupportReplyTemplateViewSet, SupportConversationAutoReplyView

app_name = 'support'

router = DefaultRouter()
router.register('chat', SupportChatViewSet, basename='support-chat')
router.register('reply-templates', SupportReplyTemplateViewSet, basename='support-reply-template')

urlpatterns = [
    path('', SupportApiRootView.as_view(), name='support-root'),
    path('conversations/<int:conversation_id>/auto-reply/', SupportConversationAutoReplyView.as_view(), name='support-auto-reply'),
    path('', include(router.urls)),
]
