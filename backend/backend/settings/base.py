from pathlib import Path
from .env_config import EnvironmentConfig

BASE_DIR = Path(__file__).resolve().parents[1]

# Environment-aware configuration
SECRET_KEY = EnvironmentConfig.get_secret_key()
DEBUG = EnvironmentConfig.get_debug()
ALLOWED_HOSTS = EnvironmentConfig.get_allowed_hosts()

INSTALLED_APPS = [
    'simpleui',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_extensions',
    'corsheaders',
    'django_filters',
    'users',
    'catalog',
    'orders',
    'integrations',
    'support',
]

AUTH_USER_MODEL = 'users.User' 

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # 'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ] if EnvironmentConfig.is_production() else [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '100/minute',
        'login': '5/minute',
        'payment': '10/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Versioning disabled for backward compatibility
    # 'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    # 'ALLOWED_VERSIONS': ['v1', 'v2'],
    # 'VERSION_PARAM': 'version',
}

# drf-spectacular configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'E-Commerce API',
    'DESCRIPTION': 'API documentation for the e-commerce system',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': None,
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'CONTACT': {
        'name': 'API Support',
        'email': 'support@example.com',
    },
    'LICENSE': {
        'name': 'MIT',
    },
    'AUTHENTICATION_FLOWS': {
        'JWT': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    },
    'SECURITY': [
        {
            'JWT': []
        }
    ],
    'TAGS': [
        {
            'name': 'Products',
            'description': 'Product management and search',
        },
        {
            'name': 'Categories',
            'description': 'Product category management',
        },
        {
            'name': 'Brands',
            'description': 'Brand management',
        },
        {
            'name': 'Orders',
            'description': 'Order management',
        },
        {
            'name': 'Payments',
            'description': 'Payment processing',
        },
        {
            'name': 'Users',
            'description': 'User authentication and profile',
        },
        {
            'name': 'Addresses',
            'description': 'User address management',
        },
        {
            'name': 'Cart',
            'description': 'Shopping cart management',
        },
        {
            'name': 'Favorites',
            'description': 'Product favorites management',
        },
        {
            'name': 'Search',
            'description': 'Product search and analytics',
        },
        {
            'name': 'Integrations',
            'description': 'Supplier API integrations',
        },
    ],
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

# CORS configuration (environment-specific settings in development.py and production.py)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'common.exceptions.ExceptionLoggingMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default file storage: local filesystem for development;
# override in production to use CDN-backed storage via env or settings.production
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache: local memory for development/test; override in production as needed
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-electric-miniprogram-cache',
        'TIMEOUT': 300,
    }
}

# Logging configuration
from common.logging_config import get_logging_config
LOGGING = get_logging_config()

# WeChat Mini Program Configuration
WECHAT_APPID = EnvironmentConfig.get_env('WECHAT_APPID', '')
WECHAT_SECRET = EnvironmentConfig.get_env('WECHAT_SECRET', '')

# WeChat Pay Configuration (for future use)
WECHAT_PAY_MCHID = EnvironmentConfig.get_env('WECHAT_PAY_MCHID', '')
WECHAT_PAY_SECRET = EnvironmentConfig.get_env('WECHAT_PAY_SECRET', '')

# ============================================================================
# Haier API Configuration (for product sync and pricing)
# ============================================================================
HAIER_CLIENT_ID = EnvironmentConfig.get_env('HAIER_CLIENT_ID', '')
HAIER_CLIENT_SECRET = EnvironmentConfig.get_env('HAIER_CLIENT_SECRET', '')
HAIER_TOKEN_URL = EnvironmentConfig.get_env('HAIER_TOKEN_URL', 'https://openplat-test.haier.net/oauth2/auth')
HAIER_BASE_URL = EnvironmentConfig.get_env('HAIER_BASE_URL', 'https://openplat-test.haier.net')
HAIER_CUSTOMER_CODE = EnvironmentConfig.get_env('HAIER_CUSTOMER_CODE', '')
HAIER_SEND_TO_CODE = EnvironmentConfig.get_env('HAIER_SEND_TO_CODE', '')
HAIER_SUPPLIER_CODE = EnvironmentConfig.get_env('HAIER_SUPPLIER_CODE', '')
HAIER_PASSWORD = EnvironmentConfig.get_env('HAIER_PASSWORD', '')
HAIER_SELLER_PASSWORD = EnvironmentConfig.get_env('HAIER_SELLER_PASSWORD', '')

# ============================================================================
# YLH System API Configuration (for order operations)
# ============================================================================
YLH_AUTH_URL = EnvironmentConfig.get_env('YLH_AUTH_URL', 'http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token')
YLH_BASE_URL = EnvironmentConfig.get_env('YLH_BASE_URL', 'http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev')
YLH_USERNAME = EnvironmentConfig.get_env('YLH_USERNAME', '')
YLH_PASSWORD = EnvironmentConfig.get_env('YLH_PASSWORD', '')
YLH_CLIENT_ID = EnvironmentConfig.get_env('YLH_CLIENT_ID', 'open_api_erp')
YLH_CLIENT_SECRET = EnvironmentConfig.get_env('YLH_CLIENT_SECRET', '12345678')

# YLH Callback Configuration (for receiving Haier platform callbacks)
YLH_CALLBACK_APP_KEY = EnvironmentConfig.get_env('YLH_CALLBACK_APP_KEY', '85f46119-e920-4f01-9624-66326c013217')
YLH_CALLBACK_SECRET = EnvironmentConfig.get_env('YLH_CALLBACK_SECRET', '8e17bb88a087400bac9ab67e67b138ef')

# ============================================================================
# Haier API Mock Data Configuration
# ============================================================================
# 是否使用模拟数据（开发/测试环境建议设置为True，生产环境设置为False）
HAIER_USE_MOCK_DATA = EnvironmentConfig.get_env('HAIER_USE_MOCK_DATA', 'True').lower() in ('true', '1', 'yes')
