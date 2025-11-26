"""
Audit logging utilities for tracking critical operations.

This module provides specialized logging for:
- Payment operations (create, verify, process, refund)
- Order operations (create, cancel, status changes)
- User authentication (login, logout)
- Admin operations (create, update, delete)
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from django.contrib.auth.models import AnonymousUser

# Get the payment audit logger
payment_audit_logger = logging.getLogger('payment_audit')
api_logger = logging.getLogger('api')


class AuditLogger:
    """
    Centralized audit logging for critical operations.
    
    Provides methods for logging different types of operations with
    consistent formatting and context information.
    """
    
    @staticmethod
    def log_payment_created(payment_id: int, order_id: int, amount: float, user_id: Optional[int] = None):
        """
        Log payment creation.
        
        Args:
            payment_id: Payment ID
            order_id: Associated order ID
            amount: Payment amount
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Payment created: payment_id={payment_id}, order_id={order_id}, amount={amount}',
            extra={
                'event': 'payment_created',
                'payment_id': payment_id,
                'order_id': order_id,
                'amount': amount,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_payment_verified(payment_id: int, transaction_id: str, user_id: Optional[int] = None):
        """
        Log payment verification.
        
        Args:
            payment_id: Payment ID
            transaction_id: External transaction ID
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Payment verified: payment_id={payment_id}, transaction_id={transaction_id}',
            extra={
                'event': 'payment_verified',
                'payment_id': payment_id,
                'transaction_id': transaction_id,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_payment_succeeded(payment_id: int, order_id: int, amount: float, user_id: Optional[int] = None):
        """
        Log successful payment processing.
        
        Args:
            payment_id: Payment ID
            order_id: Associated order ID
            amount: Payment amount
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Payment succeeded: payment_id={payment_id}, order_id={order_id}, amount={amount}',
            extra={
                'event': 'payment_succeeded',
                'payment_id': payment_id,
                'order_id': order_id,
                'amount': amount,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_payment_failed(payment_id: int, reason: str, user_id: Optional[int] = None):
        """
        Log payment failure.
        
        Args:
            payment_id: Payment ID
            reason: Failure reason
            user_id: User ID (optional)
        """
        payment_audit_logger.warning(
            f'Payment failed: payment_id={payment_id}, reason={reason}',
            extra={
                'event': 'payment_failed',
                'payment_id': payment_id,
                'reason': reason,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_payment_refunded(payment_id: int, order_id: int, amount: float, reason: str, user_id: Optional[int] = None):
        """
        Log payment refund.
        
        Args:
            payment_id: Payment ID
            order_id: Associated order ID
            amount: Refund amount
            reason: Refund reason
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Payment refunded: payment_id={payment_id}, order_id={order_id}, amount={amount}, reason={reason}',
            extra={
                'event': 'payment_refunded',
                'payment_id': payment_id,
                'order_id': order_id,
                'amount': amount,
                'reason': reason,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_order_created(order_id: int, user_id: int, total_amount: float, items_count: int):
        """
        Log order creation.
        
        Args:
            order_id: Order ID
            user_id: User ID
            total_amount: Order total amount
            items_count: Number of items in order
        """
        payment_audit_logger.info(
            f'Order created: order_id={order_id}, user_id={user_id}, total_amount={total_amount}, items={items_count}',
            extra={
                'event': 'order_created',
                'order_id': order_id,
                'user_id': user_id,
                'total_amount': total_amount,
                'items_count': items_count,
            }
        )
    
    @staticmethod
    def log_order_cancelled(order_id: int, reason: str, user_id: Optional[int] = None):
        """
        Log order cancellation.
        
        Args:
            order_id: Order ID
            reason: Cancellation reason
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Order cancelled: order_id={order_id}, reason={reason}',
            extra={
                'event': 'order_cancelled',
                'order_id': order_id,
                'reason': reason,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_order_status_changed(order_id: int, from_status: str, to_status: str, user_id: Optional[int] = None):
        """
        Log order status change.
        
        Args:
            order_id: Order ID
            from_status: Previous status
            to_status: New status
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Order status changed: order_id={order_id}, {from_status} -> {to_status}',
            extra={
                'event': 'order_status_changed',
                'order_id': order_id,
                'from_status': from_status,
                'to_status': to_status,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_user_login(user_id: int, login_type: str, ip_address: Optional[str] = None):
        """
        Log user login.
        
        Args:
            user_id: User ID
            login_type: Type of login (wechat, admin, etc.)
            ip_address: User IP address (optional)
        """
        payment_audit_logger.info(
            f'User login: user_id={user_id}, type={login_type}',
            extra={
                'event': 'user_login',
                'user_id': user_id,
                'login_type': login_type,
                'ip_address': ip_address,
            }
        )
    
    @staticmethod
    def log_admin_action(action: str, resource_type: str, resource_id: int, admin_id: int, details: Optional[Dict] = None):
        """
        Log admin action.
        
        Args:
            action: Action type (create, update, delete, etc.)
            resource_type: Type of resource (product, order, user, etc.)
            resource_id: Resource ID
            admin_id: Admin user ID
            details: Additional details (optional)
        """
        details_str = json.dumps(details) if details else ''
        payment_audit_logger.info(
            f'Admin action: {action} {resource_type} {resource_id} by admin {admin_id}',
            extra={
                'event': 'admin_action',
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'admin_id': admin_id,
                'details': details_str,
            }
        )
    
    @staticmethod
    def log_api_error(endpoint: str, method: str, status_code: int, error_message: str, user_id: Optional[int] = None):
        """
        Log API error.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            error_message: Error message
            user_id: User ID (optional)
        """
        api_logger.error(
            f'API error: {method} {endpoint} - {status_code} - {error_message}',
            extra={
                'event': 'api_error',
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'error_message': error_message,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_inventory_change(product_id: int, change_type: str, quantity: int, reason: str, user_id: Optional[int] = None):
        """
        Log inventory change.
        
        Args:
            product_id: Product ID
            change_type: Type of change (lock, release, adjust)
            quantity: Quantity changed
            reason: Reason for change
            user_id: User ID (optional)
        """
        payment_audit_logger.info(
            f'Inventory changed: product_id={product_id}, type={change_type}, qty={quantity}, reason={reason}',
            extra={
                'event': 'inventory_changed',
                'product_id': product_id,
                'change_type': change_type,
                'quantity': quantity,
                'reason': reason,
                'user_id': user_id,
            }
        )
    
    @staticmethod
    def log_supplier_sync(supplier_name: str, sync_type: str, status: str, message: str = ''):
        """
        Log supplier data sync.
        
        Args:
            supplier_name: Supplier name
            sync_type: Type of sync (products, inventory, etc.)
            status: Sync status (success, failed, etc.)
            message: Additional message (optional)
        """
        payment_audit_logger.info(
            f'Supplier sync: {supplier_name} - {sync_type} - {status}',
            extra={
                'event': 'supplier_sync',
                'supplier_name': supplier_name,
                'sync_type': sync_type,
                'status': status,
                'message': message,
            }
        )


# Convenience functions for common logging operations

def log_payment_created(payment_id: int, order_id: int, amount: float, user_id: Optional[int] = None):
    """Log payment creation."""
    AuditLogger.log_payment_created(payment_id, order_id, amount, user_id)


def log_payment_succeeded(payment_id: int, order_id: int, amount: float, user_id: Optional[int] = None):
    """Log successful payment."""
    AuditLogger.log_payment_succeeded(payment_id, order_id, amount, user_id)


def log_payment_failed(payment_id: int, reason: str, user_id: Optional[int] = None):
    """Log payment failure."""
    AuditLogger.log_payment_failed(payment_id, reason, user_id)


def log_order_created(order_id: int, user_id: int, total_amount: float, items_count: int):
    """Log order creation."""
    AuditLogger.log_order_created(order_id, user_id, total_amount, items_count)


def log_order_cancelled(order_id: int, reason: str, user_id: Optional[int] = None):
    """Log order cancellation."""
    AuditLogger.log_order_cancelled(order_id, reason, user_id)


def log_user_login(user_id: int, login_type: str, ip_address: Optional[str] = None):
    """Log user login."""
    AuditLogger.log_user_login(user_id, login_type, ip_address)
