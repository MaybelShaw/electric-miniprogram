"""
海尔API路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HaierConfigViewSet, HaierAPIViewSet

router = DefaultRouter()
router.register(r'config', HaierConfigViewSet, basename='haier-config')
router.register(r'api', HaierAPIViewSet, basename='haier-api')

urlpatterns = [
    path('', include(router.urls)),
]
