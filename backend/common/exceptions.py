"""
Custom exception classes and unified exception handler for the API.

This module provides:
- Custom business logic exceptions (InsufficientStockError, InvalidOrderStatusError, etc.)
- Unified exception handler that formats all errors consistently
- Environment-aware error response formatting (hides sensitive info in production)
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
import logging
import traceback

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Business Logic Exceptions
# ============================================================================

class BusinessException(APIException):
    """
    Base class for all business logic exceptions.
    
    Provides a consistent way to handle domain-specific errors with
    appropriate HTTP status codes and error messages.
    """
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A business logic error occurred.'
    default_code = 'business_error'
    error_code = 'BUSINESS_ERROR'
    
    def __init__(self, detail=None, code=None, error_code=None):
        """
        Initialize the exception.
        
        Args:
            detail (str, optional): Error message. Uses default_detail if not provided.
            code (str, optional): Error code for DRF. Uses default_code if not provided.
            error_code (str, optional): Custom error code for client. Uses class error_code if not provided.
        """
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if error_code is None:
            error_code = self.error_code
        
        super().__init__(detail=detail, code=code)
        self.error_code = error_code


class InsufficientStockError(BusinessException):
    """
    Raised when attempting to purchase more items than available in stock.
    
    HTTP Status: 409 Conflict
    
    Example:
        if product.stock < quantity:
            raise InsufficientStockError(
                detail=f'库存不足，当前库存: {product.stock}'
            )
    """
    
    status_code = status.HTTP_409_CONFLICT
    default_detail = '库存不足'
    default_code = 'insufficient_stock'
    error_code = 'INSUFFICIENT_STOCK'


class InvalidOrderStatusError(BusinessException):
    """
    Raised when attempting an invalid order status transition.
    
    HTTP Status: 400 Bad Request
    
    Example:
        if order.status == 'cancelled':
            raise InvalidOrderStatusError(
                detail='已取消的订单不能发货'
            )
    """
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '订单状态转换不合法'
    default_code = 'invalid_order_status'
    error_code = 'INVALID_ORDER_STATUS'


class PaymentVerificationError(BusinessException):
    """
    Raised when payment verification fails (signature, amount, etc.).
    
    HTTP Status: 400 Bad Request
    
    Example:
        if not verify_signature(data, signature):
            raise PaymentVerificationError(
                detail='支付签名验证失败'
            )
    """
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '支付验证失败'
    default_code = 'payment_verification_failed'
    error_code = 'PAYMENT_VERIFICATION_FAILED'


class DuplicatePaymentError(BusinessException):
    """
    Raised when attempting to process a payment that has already been processed.
    
    HTTP Status: 409 Conflict
    
    Example:
        if payment.status == 'succeeded':
            raise DuplicatePaymentError(
                detail='该支付已处理'
            )
    """
    
    status_code = status.HTTP_409_CONFLICT
    default_detail = '重复支付'
    default_code = 'duplicate_payment'
    error_code = 'DUPLICATE_PAYMENT'


class InvalidPaymentAmountError(BusinessException):
    """
    Raised when payment amount doesn't match order total.
    
    HTTP Status: 400 Bad Request
    
    Example:
        if order.total_amount != payment_amount:
            raise InvalidPaymentAmountError(
                detail=f'支付金额不匹配，应支付: {order.total_amount}'
            )
    """
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '支付金额不匹配'
    default_code = 'invalid_payment_amount'
    error_code = 'INVALID_PAYMENT_AMOUNT'


class SupplierAPIError(BusinessException):
    """
    Raised when supplier API call fails.
    
    HTTP Status: 502 Bad Gateway
    
    Example:
        try:
            supplier.get_products()
        except requests.RequestException as e:
            raise SupplierAPIError(
                detail=f'供应商API调用失败: {str(e)}'
            )
    """
    
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = '供应商API调用失败'
    default_code = 'supplier_api_error'
    error_code = 'SUPPLIER_API_ERROR'


class SupplierAuthenticationError(BusinessException):
    """
    Raised when supplier authentication fails.
    
    HTTP Status: 401 Unauthorized
    
    Example:
        if not supplier.authenticate():
            raise SupplierAuthenticationError(
                detail='供应商认证失败'
            )
    """
    
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = '供应商认证失败'
    default_code = 'supplier_auth_failed'
    error_code = 'SUPPLIER_AUTH_FAILED'


class ResourceConflictError(BusinessException):
    """
    Raised when attempting to delete a resource that has dependencies.
    
    HTTP Status: 409 Conflict
    
    Example:
        if brand.products.exists():
            raise ResourceConflictError(
                detail='该品牌有关联商品，无法删除'
            )
    """
    
    status_code = status.HTTP_409_CONFLICT
    default_detail = '资源冲突'
    default_code = 'resource_conflict'
    error_code = 'RESOURCE_CONFLICT'


class InvalidFileError(BusinessException):
    """
    Raised when file validation fails.
    
    HTTP Status: 400 Bad Request
    
    Example:
        if not is_valid_image(file):
            raise InvalidFileError(
                detail='文件格式不支持'
            )
    """
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '文件验证失败'
    default_code = 'invalid_file'
    error_code = 'INVALID_FILE'


class RateLimitExceededError(BusinessException):
    """
    Raised when rate limit is exceeded.
    
    HTTP Status: 429 Too Many Requests
    
    Note: Usually handled by DRF throttling, but can be raised manually if needed.
    """
    
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = '请求过于频繁，请稍后再试'
    default_code = 'rate_limit_exceeded'
    error_code = 'RATE_LIMIT_EXCEEDED'


# ============================================================================
# Unified Exception Handler
# ============================================================================

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that formats all errors consistently.
    
    Features:
    - Unified response format for all errors
    - Environment-aware error details (hides stack traces in production)
    - Proper HTTP status codes
    - Error codes for client-side handling
    - Comprehensive logging
    
    Args:
        exc: The exception that was raised
        context: Additional context about the request (view, request, etc.)
        
    Returns:
        Response: Formatted error response, or None if exception is not handled
    """
    from backend.settings.env_config import EnvironmentConfig
    
    request = context.get('request')
    view = context.get('view')
    
    # Get the standard DRF exception response
    response = drf_exception_handler(exc, context)
    
    # Log the exception
    _log_exception(exc, context, response)
    
    if response is not None:
        # Format the error response
        error_data = response.data
        status_code = response.status_code
        
        # Extract error information
        message, errors, error_code = _extract_error_info(error_data, exc)
        
        # Build formatted response
        formatted_response = {
            'success': False,
            'code': status_code,
            'message': message,
        }
        
        if error_code:
            formatted_response['error_code'] = error_code
        
        # Include detailed errors only in development
        if errors and not EnvironmentConfig.is_production():
            formatted_response['errors'] = errors
        
        # Hide sensitive information in production
        if EnvironmentConfig.is_production():
            # Don't expose internal error details
            if status_code >= 500:
                formatted_response['message'] = '服务器内部错误，请稍后重试'
        
        response.data = formatted_response
    else:
        # Handle exceptions not caught by DRF
        response = _handle_unhandled_exception(exc, context)
    
    return response


def _extract_error_info(error_data, exc):
    """
    Extract error message, detailed errors, and error code from error data.
    
    Args:
        error_data: The error data from DRF response
        exc: The original exception
        
    Returns:
        tuple: (message, errors, error_code)
    """
    message = 'An error occurred'
    errors = None
    error_code = None
    
    # Get error code from custom exception
    if isinstance(exc, BusinessException):
        error_code = exc.error_code
    
    # Extract message
    if isinstance(error_data, dict):
        if 'detail' in error_data:
            message = str(error_data['detail'])
        elif 'message' in error_data:
            message = str(error_data['message'])
        else:
            # Multiple field errors
            message = 'Validation error'
            errors = error_data
    elif isinstance(error_data, list):
        message = str(error_data[0]) if error_data else message
    else:
        message = str(error_data)
    
    return message, errors, error_code


def _handle_unhandled_exception(exc, context):
    """
    Handle exceptions that are not caught by DRF.
    
    Args:
        exc: The exception
        context: Request context
        
    Returns:
        Response: Formatted error response
    """
    from backend.settings.env_config import EnvironmentConfig
    
    # Log the unhandled exception
    logger.error(
        f'Unhandled exception: {type(exc).__name__}',
        exc_info=exc,
        extra={
            'request_path': context.get('request').path if context.get('request') else None,
            'request_method': context.get('request').method if context.get('request') else None,
        }
    )
    
    # Determine status code
    if isinstance(exc, DjangoValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
        message = 'Validation error'
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = 'Internal server error'
    
    # Hide details in production
    if EnvironmentConfig.is_production():
        message = 'An error occurred, please try again later'
    else:
        message = f'{type(exc).__name__}: {str(exc)}'
    
    response_data = {
        'success': False,
        'code': status_code,
        'message': message,
    }
    
    return Response(response_data, status=status_code)


def _log_exception(exc, context, response):
    """
    Log exception details for debugging and monitoring.
    
    Args:
        exc: The exception
        context: Request context
        response: The response object (if available)
    """
    request = context.get('request')
    view = context.get('view')
    
    # Determine log level based on status code
    if response and response.status_code >= 500:
        log_level = logging.ERROR
    elif response and response.status_code >= 400:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # Build log message
    log_message = f'{type(exc).__name__}'
    if str(exc):
        log_message += f': {str(exc)}'
    
    # Build request metadata only for support chat 401 to reduce noise
    client_meta = {}
    if (
        request
        and response
        and response.status_code == status.HTTP_401_UNAUTHORIZED
        and request.path.startswith('/api/support/chat/')
    ):
        client_meta = {
            'client_ip': request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
        }

    # Log with context
    logger.log(
        log_level,
        log_message,
        exc_info=exc if log_level == logging.ERROR else None,
        extra={
            'request_path': request.path if request else None,
            'request_method': request.method if request else None,
            'view_name': view.__class__.__name__ if view else None,
            'status_code': response.status_code if response else None,
            **client_meta,
        }
    )


# ============================================================================
# Middleware for catching unhandled exceptions
# ============================================================================

class ExceptionLoggingMiddleware:
    """
    Middleware that catches and logs unhandled exceptions.
    
    This middleware should be added to MIDDLEWARE in settings.py:
    
    MIDDLEWARE = [
        ...
        'common.exceptions.ExceptionLoggingMiddleware',
        ...
    ]
    """
    
    def __init__(self, get_response):
        """
        Initialize the middleware.
        
        Args:
            get_response: The next middleware or view
        """
        self.get_response = get_response
    
    def __call__(self, request):
        """
        Process the request and catch any unhandled exceptions.
        
        Args:
            request: The HTTP request
            
        Returns:
            Response: The response from the next middleware/view
        """
        try:
            response = self.get_response(request)
        except Exception as exc:
            # Log the exception
            logger.error(
                f'Unhandled exception in middleware: {type(exc).__name__}',
                exc_info=exc,
                extra={
                    'request_path': request.path,
                    'request_method': request.method,
                }
            )
            
            # Return error response
            from backend.settings.env_config import EnvironmentConfig
            
            if EnvironmentConfig.is_production():
                message = 'Internal server error'
            else:
                message = f'{type(exc).__name__}: {str(exc)}'
            
            response_data = {
                'success': False,
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': message,
            }
            
            return JsonResponse(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return response
