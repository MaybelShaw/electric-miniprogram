"""
Health check endpoint for monitoring system status.

This module provides:
- Database connectivity check
- Redis/Cache connectivity check
- Overall system health status
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint that verifies system status.
    
    Returns:
    {
        "success": true,
        "code": 200,
        "message": "System is healthy",
        "data": {
            "status": "healthy",
            "timestamp": "2025-11-15T10:30:00Z",
            "services": {
                "database": {
                    "status": "healthy",
                    "response_time_ms": 5.2
                },
                "cache": {
                    "status": "healthy",
                    "response_time_ms": 2.1
                }
            }
        }
    }
    
    Status codes:
    - 200: All services are healthy
    - 503: One or more services are unhealthy
    """
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'services': {}
    }
    
    overall_status_code = status.HTTP_200_OK
    
    # Check database connectivity
    db_health = _check_database()
    health_status['services']['database'] = db_health
    if db_health['status'] != 'healthy':
        overall_status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    # Check cache connectivity
    cache_health = _check_cache()
    health_status['services']['cache'] = cache_health
    if cache_health['status'] != 'healthy':
        overall_status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    # Update overall status
    if overall_status_code != status.HTTP_200_OK:
        health_status['status'] = 'unhealthy'
    
    # Log health check (debug to reduce noise in normal logs)
    logger.debug(
        'Health check performed',
        extra={
            'health_status': health_status['status'],
            'database_status': db_health['status'],
            'cache_status': cache_health['status'],
        }
    )
    
    response_data = {
        'success': overall_status_code == status.HTTP_200_OK,
        'code': overall_status_code,
        'message': 'System is healthy' if overall_status_code == status.HTTP_200_OK else 'System is unhealthy',
        'data': health_status
    }
    
    return Response(response_data, status=overall_status_code)


def _check_database():
    """
    Check database connectivity and response time.
    
    Returns:
        dict: Health status with response time in milliseconds
    """
    import time
    
    try:
        start_time = time.time()
        
        # Execute a simple query to verify connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        
        response_time_ms = (time.time() - start_time) * 1000
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time_ms, 2)
        }
    except Exception as e:
        logger.error(
            'Database health check failed',
            exc_info=e,
            extra={'error': str(e)}
        )
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_cache():
    """
    Check cache connectivity and response time.
    
    Returns:
        dict: Health status with response time in milliseconds
    """
    import time
    
    try:
        # Test cache with a simple set/get operation
        test_key = '__health_check__'
        test_value = 'healthy'
        
        start_time = time.time()
        
        # Set a test value
        cache.set(test_key, test_value, timeout=10)
        
        # Get the test value
        cached_value = cache.get(test_key)
        
        response_time_ms = (time.time() - start_time) * 1000
        
        # Verify the value was cached correctly
        if cached_value == test_value:
            # Clean up
            cache.delete(test_key)
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time_ms, 2)
            }
        return {
            'status': 'unhealthy',
            'error': 'Cache value mismatch'
        }
    except Exception as e:
        logger.error(
            'Cache health check failed',
            exc_info=e,
            extra={'error': str(e)}
        )
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_wechatpay_config(strict: bool = False):
    """Validate required WeChat Pay config to fail fast in logs."""
    from django.conf import settings
    required = {
        'WECHAT_APPID': getattr(settings, 'WECHAT_APPID', ''),
        'WECHAT_PAY_MCHID': getattr(settings, 'WECHAT_PAY_MCHID', ''),
        'WECHAT_PAY_SERIAL_NO': getattr(settings, 'WECHAT_PAY_SERIAL_NO', ''),
        'WECHAT_PAY_PRIVATE_KEY_PATH': getattr(settings, 'WECHAT_PAY_PRIVATE_KEY_PATH', ''),
        'WECHAT_PAY_API_V3_KEY': getattr(settings, 'WECHAT_PAY_API_V3_KEY', ''),
        'WECHAT_PAY_REFUND_NOTIFY_URL': getattr(settings, 'WECHAT_PAY_REFUND_NOTIFY_URL', ''),
        'WECHAT_PAY_NOTIFY_URL': getattr(settings, 'WECHAT_PAY_NOTIFY_URL', ''),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        msg = f'wechat pay config missing: {", ".join(missing)}'
        if strict:
            raise RuntimeError(msg)
        logging.getLogger(__name__).warning(msg)
    return True
