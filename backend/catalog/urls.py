from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"products", views.ProductViewSet)
router.register(r"categories", views.CategoryViewSet)
router.register(r"media-images", views.MediaImageViewSet, basename='media-images')
router.register(r"brands", views.BrandViewSet)
router.register(r"search-logs", views.SearchLogViewSet, basename='search-logs')

urlpatterns = [
    path("", include(router.urls)),
]
