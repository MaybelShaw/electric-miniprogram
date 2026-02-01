"""
海尔API路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HaierConfigViewSet, 
    HaierAPIViewSet,
    ylh_callback_view,
    ylh_create_order_view,
    ylh_cancel_order_view,
    ylh_update_distribution_time_view,
    ylh_get_delivery_images_view,
    ylh_get_logistics_view,
    wechat_delivery_company_list_view,
)

router = DefaultRouter()
router.register(r'config', HaierConfigViewSet, basename='haier-config')
router.register(r'api', HaierAPIViewSet, basename='haier-api')

urlpatterns = [
    path('', include(router.urls)),
    
    # YLH回调接口
    path('ylh/callback/', ylh_callback_view, name='ylh-callback'),
    
    # YLH订单操作接口
    path('ylh/orders/create/', ylh_create_order_view, name='ylh-create-order'),
    path('ylh/orders/cancel/', ylh_cancel_order_view, name='ylh-cancel-order'),
    path('ylh/orders/update-time/', ylh_update_distribution_time_view, name='ylh-update-time'),
    path('ylh/orders/delivery-images/', ylh_get_delivery_images_view, name='ylh-delivery-images'),
    path('ylh/orders/logistics/', ylh_get_logistics_view, name='ylh-logistics'),
    path('wechat/delivery-companies/', wechat_delivery_company_list_view, name='wechat-delivery-companies'),
]
