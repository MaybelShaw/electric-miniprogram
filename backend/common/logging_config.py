"""
Logging configuration for the Django application.

This module provides:
- Centralized logging configuration
- File rotation for log files
- Separate audit logging for payment operations
- Environment-aware logging levels
- Windows-compatible file handlers
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from backend.settings.env_config import EnvironmentConfig

# Check if running on Windows
IS_WINDOWS = sys.platform.startswith('win')

# Get the base directory for log files
BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / 'backend' / 'logs'

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_logging_config():
    """
    Get the logging configuration dictionary for Django.
    
    This function returns a LOGGING configuration that can be used in Django settings:
    
    Example in settings.py:
        from common.logging_config import get_logging_config
        LOGGING = get_logging_config()
    
    Returns:
        dict: Logging configuration for Django
    """
    def _resolve_level(env_key: str, default: str) -> str:
        val = EnvironmentConfig.get_env(env_key, '').strip().upper()
        if val:
            return val
        return default

    is_prod = EnvironmentConfig.is_production()
    default_level = _resolve_level('LOG_LEVEL', 'INFO' if not is_prod else 'INFO')
    django_level = _resolve_level('DJANGO_LOG_LEVEL', default_level)
    db_level = _resolve_level('DB_LOG_LEVEL', 'INFO')
    integrations_debug_enabled = EnvironmentConfig.get_env('INTEGRATIONS_API_DEBUG', 'False').lower() in ('1', 'true', 'yes', 'on')

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        # Define formatters
        'formatters': {
            'verbose': {
                'format': '[{levelname}] {asctime} {name} {funcName}:{lineno} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'simple': {
                'format': '[{levelname}] {asctime} {name} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'audit': {
                'format': '[AUDIT] {asctime} {name} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        # Define handlers
        'handlers': {},
        'loggers': {},
    }

    handlers = config['handlers']

    handlers['console'] = {
        'level': default_level,
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    }

    if integrations_debug_enabled:
        handlers['integrations_console_debug'] = {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }

    # General application log file
    if IS_WINDOWS:
        handlers['file'] = {
            'level': default_level,
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOGS_DIR / 'app.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }
    else:
        handlers['file'] = {
            'level': default_level,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'app.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }

    # Error log file
    if IS_WINDOWS:
        handlers['error_file'] = {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOGS_DIR / 'error.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }
    else:
        handlers['error_file'] = {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'error.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }

    # Payment audit log file
    if IS_WINDOWS:
        handlers['payment_audit'] = {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOGS_DIR / 'payment_audit.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 90,
            'formatter': 'audit',
            'encoding': 'utf-8',
        }
    else:
        handlers['payment_audit'] = {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'payment_audit.log'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 20,
            'formatter': 'audit',
            'encoding': 'utf-8',
        }

    # Database query log file (development only)
    if IS_WINDOWS:
        handlers['db_queries'] = {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOGS_DIR / 'db_queries.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 7,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }
    else:
        handlers['db_queries'] = {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'db_queries.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }

    # API request/response log file
    if IS_WINDOWS:
        handlers['api'] = {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOGS_DIR / 'api.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }
    else:
        handlers['api'] = {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'api.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        }

    config['loggers'] = {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': django_level,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            # Enable query logging only when DB_LOG_LEVEL=DEBUG
            'handlers': ['db_queries'] if db_level == 'DEBUG' else [],
            'level': db_level,
            'propagate': False,
        },
        'backend': {
            'handlers': ['console', 'file', 'error_file'],
            'level': default_level,
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'api', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'payment_audit': {
            'handlers': ['console', 'payment_audit', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'file', 'error_file'],
            'level': default_level,
            'propagate': False,
        },
        'catalog': {
            'handlers': ['console', 'file', 'error_file'],
            'level': default_level,
            'propagate': False,
        },
        'users': {
            'handlers': ['console', 'file', 'error_file'],
            'level': default_level,
            'propagate': False,
        },
        'integrations': {
            'handlers': ['console', 'file', 'error_file'] + (['integrations_console_debug'] if integrations_debug_enabled else []),
            'level': 'DEBUG' if integrations_debug_enabled else default_level,
            'propagate': False,
        },
        'common': {
            'handlers': ['console', 'file', 'error_file'],
            'level': default_level,
            'propagate': False,
        },
        'support': {
            'handlers': ['console', 'file', 'error_file'],
            'level': default_level,
            'propagate': False,
        },
    }

    return config


# ============================================================================
# Logging Utilities
# ============================================================================

def get_logger(name):
    """
    Get a logger instance with the given name.
    
    Args:
        name (str): Logger name (typically __name__)
        
    Returns:
        logging.Logger: Logger instance
        
    Example:
        from common.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info('Application started')
    """
    return logging.getLogger(name)


def get_payment_audit_logger():
    """
    Get the payment audit logger for logging payment operations.
    
    Returns:
        logging.Logger: Payment audit logger
        
    Example:
        from common.logging_config import get_payment_audit_logger
        audit_logger = get_payment_audit_logger()
        audit_logger.info(f'Payment created: {payment_id}')
    """
    return logging.getLogger('payment_audit')


def get_api_logger():
    """
    Get the API logger for logging API operations.
    
    Returns:
        logging.Logger: API logger
        
    Example:
        from common.logging_config import get_api_logger
        api_logger = get_api_logger()
        api_logger.info(f'API request: {method} {path}')
    """
    return logging.getLogger('api')


# ============================================================================
# Logging Decorators
# ============================================================================

def log_payment_operation(operation_type):
    """
    Decorator for logging payment operations.
    
    Args:
        operation_type (str): Type of payment operation (e.g., 'create', 'verify', 'process')
        
    Example:
        @log_payment_operation('create')
        def create_payment(order_id, amount):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            audit_logger = get_payment_audit_logger()
            
            try:
                result = func(*args, **kwargs)
                audit_logger.info(
                    f'{operation_type.upper()} - Success: {func.__name__}',
                    extra={
                        'operation': operation_type,
                        'function': func.__name__,
                        'args': str(args)[:100],  # Limit length
                        'kwargs': str(kwargs)[:100],
                    }
                )
                return result
            except Exception as e:
                audit_logger.error(
                    f'{operation_type.upper()} - Failed: {func.__name__} - {str(e)}',
                    exc_info=True,
                    extra={
                        'operation': operation_type,
                        'function': func.__name__,
                        'error': str(e),
                    }
                )
                raise
        
        return wrapper
    return decorator


def log_api_operation(operation_type):
    """
    Decorator for logging API operations.
    
    Args:
        operation_type (str): Type of API operation (e.g., 'list', 'create', 'update')
        
    Example:
        @log_api_operation('create')
        def create_product(request):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            api_logger = get_api_logger()
            
            try:
                result = func(*args, **kwargs)
                api_logger.info(
                    f'{operation_type.upper()} - {func.__name__}',
                    extra={
                        'operation': operation_type,
                        'function': func.__name__,
                    }
                )
                return result
            except Exception as e:
                api_logger.error(
                    f'{operation_type.upper()} - {func.__name__} - {str(e)}',
                    exc_info=True,
                    extra={
                        'operation': operation_type,
                        'function': func.__name__,
                        'error': str(e),
                    }
                )
                raise
        
        return wrapper
    return decorator
