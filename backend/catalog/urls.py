from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"products", views.ProductViewSet)
router.register(r"product-skus", views.ProductSKUViewSet, basename="product-skus")
router.register(r"categories", views.CategoryViewSet)
router.register(r"media-images", views.MediaImageViewSet, basename='media-images')
router.register(r"inventory-logs", views.InventoryLogViewSet, basename='inventory-logs')
router.register(r"home-banners", views.HomeBannerViewSet, basename='home-banners')
router.register(r"home-store-cards", views.HomeStoreCardViewSet, basename='home-store-cards')
router.register(r"special-zones", views.SpecialZoneViewSet, basename='special-zones')
router.register(r"special-zone-covers", views.SpecialZoneCoverViewSet, basename='special-zone-covers')
router.register(r"cases", views.CaseViewSet, basename='cases')
router.register(r"brands", views.BrandViewSet)
router.register(r"search-logs", views.SearchLogViewSet, basename='search-logs')

urlpatterns = [
    path("", include(router.urls)),
]
