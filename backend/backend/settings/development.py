from .base import *  # noqa
from corsheaders.defaults import default_headers
from .env_config import EnvironmentConfig

# Development environment settings
DEBUG = True

DATABASES = {
    'default': EnvironmentConfig.get_database_config()
}

# CORS for local development: allow all origins to avoid port mismatch
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    'authorization',
]
CORS_ALLOW_CREDENTIALS = True

# Allow all for dev if needed
ALLOWED_HOSTS = ['*']