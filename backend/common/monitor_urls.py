"""
API监控URL配置
"""
from django.urls import path
from .api_monitor import (
    api_monitor_records,
    api_monitor_statistics,
    api_monitor_clear,
    api_monitor_dashboard,
)

urlpatterns = [
    path('dashboard/', api_monitor_dashboard, name='api_monitor_dashboard'),
    path('records/', api_monitor_records, name='api_monitor_records'),
    path('statistics/', api_monitor_statistics, name='api_monitor_statistics'),
    path('clear/', api_monitor_clear, name='api_monitor_clear'),
]
