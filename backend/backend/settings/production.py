from .base import *  # noqa
import os
from .env_config import EnvironmentConfig

# Production environment settings
DEBUG = False

# Validate production configuration on startup
EnvironmentConfig.validate_production_config()

ALLOWED_HOSTS = EnvironmentConfig.get_allowed_hosts()

DATABASES = {
    'default': EnvironmentConfig.get_database_config()
}

# Security settings for production
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() in ('true', '1', 'yes')
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() in ('true', '1', 'yes')

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = EnvironmentConfig.get_cors_allowed_origins()
CORS_ALLOW_CREDENTIALS = True

# Media/CDN settings for production
MEDIA_URL = os.getenv('MEDIA_URL', os.getenv('CDN_MEDIA_URL', '/media/'))
# In production, you may set a cloud storage backend via env, e.g.,
# 'storages.backends.s3boto3.S3Boto3Storage' (requires django-storages and boto3)
DEFAULT_FILE_STORAGE = os.getenv(
    'DEFAULT_FILE_STORAGE',
    'django.core.files.storage.FileSystemStorage'
)