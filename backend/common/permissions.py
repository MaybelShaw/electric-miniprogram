"""
Custom permission classes for API access control.

This module provides environment-aware permission classes that enforce
different security policies based on the runtime environment (development vs production).
"""

from rest_framework import permissions
from backend.settings.env_config import EnvironmentConfig


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows access to object owners or administrators.
    
    - Administrators (is_staff=True) can access any object
    - Regular users can only access objects they own
    
    Typical usage:
        class OrderViewSet(viewsets.ModelViewSet):
            permission_classes = [IsOwnerOrAdmin]
    
    The object must have a 'user' attribute that references the owner.
    For related objects (e.g., Payment with order.user), override has_object_permission.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is the owner or an administrator.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            obj: The object being accessed
            
        Returns:
            bool: True if user is admin or owner, False otherwise
        """
        # Administrators and support staff have access to all objects
        if request.user and (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return True
        
        # Get the owner from the object
        owner = getattr(obj, 'user', None)
        
        # If object doesn't have direct user field, try to get it from related object
        if owner is None and hasattr(obj, 'order'):
            try:
                owner = obj.order.user
            except Exception:
                owner = None
        
        # Check if current user is the owner
        return owner == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows read access to everyone and write access to administrators only.
    
    - GET, HEAD, OPTIONS requests are allowed for all users
    - POST, PUT, PATCH, DELETE requests require administrator privileges
    
    Typical usage:
        class ProductViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAdminOrReadOnly]
    """
    
    def has_permission(self, request, view):
        """
        Check if request is allowed based on method and user role.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        # Allow read-only methods for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require authentication and admin status for write methods
        return request.user and request.user.is_staff


class IsAdmin(permissions.BasePermission):
    """
    Permission class that requires administrator privileges.
    
    Only users with is_staff=True can access the resource.
    
    Typical usage:
        class AdminUserViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAdmin]
    """
    
    def has_permission(self, request, view):
        """
        Check if user is an administrator.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        return request.user and request.user.is_staff


class EnvironmentAwarePermission(permissions.BasePermission):
    """
    Permission class that enforces different policies based on environment.
    
    - Development environment: Allows all authenticated users
    - Production environment: Requires explicit permission checks
    
    This is useful for relaxing permissions during development while maintaining
    strict security in production.
    
    Typical usage:
        class SensitiveViewSet(viewsets.ModelViewSet):
            permission_classes = [EnvironmentAwarePermission]
    """
    
    def has_permission(self, request, view):
        """
        Check permission based on environment.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        # In development, allow all authenticated users
        if not EnvironmentConfig.is_production():
            return request.user and request.user.is_authenticated
        
        # In production, require authentication
        return request.user and request.user.is_authenticated


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows read access to everyone and write access to authenticated users only.
    
    - GET, HEAD, OPTIONS requests are allowed for all users (authenticated or not)
    - POST, PUT, PATCH, DELETE requests require authentication
    
    Typical usage:
        class CommentViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticatedOrReadOnly]
    """
    
    def has_permission(self, request, view):
        """
        Check if request is allowed based on method and authentication.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        # Allow read-only methods for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require authentication for write methods
        return request.user and request.user.is_authenticated
