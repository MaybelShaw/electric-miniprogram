"""
Custom throttle classes for API rate limiting.

This module provides specialized throttle classes for sensitive operations
like login and payment, with stricter rate limits than general API endpoints.
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginRateThrottle(UserRateThrottle):
    """
    Throttle class for login endpoints.
    
    Enforces stricter rate limiting on login attempts to prevent brute force attacks.
    - Authenticated users: 5 requests per minute
    - Anonymous users: 5 requests per minute
    
    Typical usage:
        @api_view(['POST'])
        @throttle_classes([LoginRateThrottle])
        def login(request):
            ...
    
    Or in ViewSet:
        class LoginViewSet(viewsets.ViewSet):
            throttle_classes = [LoginRateThrottle]
    """
    scope = 'login'


class PaymentRateThrottle(UserRateThrottle):
    """
    Throttle class for payment-related endpoints.
    
    Enforces stricter rate limiting on payment operations to prevent abuse
    and protect against accidental duplicate payments.
    - Authenticated users: 10 requests per minute
    - Anonymous users: Not allowed (payment requires authentication)
    
    Typical usage:
        @api_view(['POST'])
        @throttle_classes([PaymentRateThrottle])
        def create_payment(request):
            ...
    
    Or in ViewSet:
        class PaymentViewSet(viewsets.ModelViewSet):
            throttle_classes = [PaymentRateThrottle]
    """
    scope = 'payment'


class AnonLoginRateThrottle(AnonRateThrottle):
    """
    Throttle class for anonymous login attempts.
    
    Applies to unauthenticated users attempting to log in.
    - Anonymous users: 5 requests per minute
    
    This is stricter than the default anonymous throttle to prevent
    brute force attacks on login endpoints.
    """
    scope = 'login'


class AnonPaymentRateThrottle(AnonRateThrottle):
    """
    Throttle class for anonymous payment attempts.
    
    Applies to unauthenticated users attempting payment operations.
    - Anonymous users: 10 requests per minute
    
    Note: In practice, payment endpoints should require authentication,
    so this throttle may not be used frequently.
    """
    scope = 'payment'


class CatalogBrowseRateThrottle(UserRateThrottle):
    """
    Throttle class for product browsing endpoints (authenticated users).

    Provides higher limits for product list/detail/search/recommendations to
    avoid throttling normal browsing behavior.
    """
    scope = 'catalog_browse_user'


class CatalogBrowseAnonRateThrottle(AnonRateThrottle):
    """
    Throttle class for product browsing endpoints (anonymous users).

    Provides higher limits for public product browsing endpoints.
    """
    scope = 'catalog_browse_anon'
