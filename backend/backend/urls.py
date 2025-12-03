"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from common.health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('healthz', health_check, name='health-check'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API v1 endpoints (versioned)
    path('api/v1/catalog/', include('catalog.urls')),
    path('api/v1/', include('catalog.urls')),
    path('api/v1/', include('orders.urls')),
    path('api/v1/', include('users.urls')),
    path('api/v1/haier/', include('integrations.urls')),
    path('api/v1/support/', include('support.urls')),
    
    # Backward compatible endpoints (without version prefix)
    path('api/catalog/', include('catalog.urls')),
    path('api/', include('catalog.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('users.urls')),
    path('api/haier/', include('integrations.urls')),
    path('api/support/', include('support.urls')),
    
    # YLH callback endpoint (direct path for external callback)
    path('api/', include('integrations.urls')),
    path('api/', include('support.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
