"""
Unified API response formatting for consistent response structure across all endpoints.

This module provides:
- StandardResponse: Wrapper for successful responses
- ErrorResponse: Wrapper for error responses
- Custom exception handlers for DRF
"""

from rest_framework.response import Response
from rest_framework import status
from typing import Any, Dict, Optional


class StandardResponse:
    """
    Wrapper for successful API responses with consistent format.
    
    Response format:
    {
        "success": true,
        "code": 200,
        "message": "Operation successful",
        "data": {...},
        "pagination": {...}  # Optional
    }
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = status.HTTP_200_OK,
        pagination: Optional[Dict] = None
    ) -> Response:
        """
        Create a successful response.
        
        Args:
            data: The response data
            message: Success message
            status_code: HTTP status code
            pagination: Optional pagination metadata
            
        Returns:
            Response: DRF Response object
        """
        response_data = {
            'success': True,
            'code': status_code,
            'message': message,
            'data': data,
        }
        
        if pagination:
            response_data['pagination'] = pagination
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "Resource created successfully"
    ) -> Response:
        """
        Create a 201 Created response.
        
        Args:
            data: The created resource data
            message: Success message
            
        Returns:
            Response: DRF Response object
        """
        return StandardResponse.success(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def no_content(message: str = "Operation successful") -> Response:
        """
        Create a 204 No Content response.
        
        Args:
            message: Success message
            
        Returns:
            Response: DRF Response object
        """
        return Response(
            {
                'success': True,
                'code': status.HTTP_204_NO_CONTENT,
                'message': message,
            },
            status=status.HTTP_204_NO_CONTENT
        )


class ErrorResponse:
    """
    Wrapper for error API responses with consistent format.
    
    Response format:
    {
        "success": false,
        "code": 400,
        "message": "Error message",
        "errors": {...}  # Optional
    }
    """
    
    @staticmethod
    def error(
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Optional[Dict] = None,
        error_code: Optional[str] = None
    ) -> Response:
        """
        Create an error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            errors: Optional detailed error information
            error_code: Optional error code for client handling
            
        Returns:
            Response: DRF Response object
        """
        response_data = {
            'success': False,
            'code': status_code,
            'message': message,
        }
        
        if error_code:
            response_data['error_code'] = error_code
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def bad_request(
        message: str = "Bad request",
        errors: Optional[Dict] = None
    ) -> Response:
        """
        Create a 400 Bad Request response.
        
        Args:
            message: Error message
            errors: Optional detailed error information
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            errors=errors
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Response:
        """
        Create a 401 Unauthorized response.
        
        Args:
            message: Error message
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(message: str = "Permission denied") -> Response:
        """
        Create a 403 Forbidden response.
        
        Args:
            message: Error message
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> Response:
        """
        Create a 404 Not Found response.
        
        Args:
            message: Error message
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def conflict(
        message: str = "Resource conflict",
        errors: Optional[Dict] = None
    ) -> Response:
        """
        Create a 409 Conflict response.
        
        Args:
            message: Error message
            errors: Optional detailed error information
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            errors=errors
        )
    
    @staticmethod
    def unprocessable_entity(
        message: str = "Unprocessable entity",
        errors: Optional[Dict] = None
    ) -> Response:
        """
        Create a 422 Unprocessable Entity response.
        
        Args:
            message: Error message
            errors: Optional detailed error information
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=errors
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error") -> Response:
        """
        Create a 500 Internal Server Error response.
        
        Args:
            message: Error message
            
        Returns:
            Response: DRF Response object
        """
        return ErrorResponse.error(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that formats all errors consistently.
    
    Args:
        exc: The exception that was raised
        context: Additional context about the request
        
    Returns:
        Response: Formatted error response
    """
    from rest_framework.views import exception_handler
    
    # Get the standard DRF exception response
    response = exception_handler(exc, context)
    
    if response is not None:
        # Format the error response
        error_detail = response.data
        
        # Extract error message
        if isinstance(error_detail, dict):
            # Handle validation errors
            if 'detail' in error_detail:
                message = str(error_detail['detail'])
            else:
                # Multiple field errors
                message = 'Validation error'
                errors = error_detail
        else:
            message = str(error_detail)
            errors = None
        
        # Create formatted response
        formatted_response = {
            'success': False,
            'code': response.status_code,
            'message': message,
        }
        
        if errors and isinstance(error_detail, dict):
            formatted_response['errors'] = error_detail
        
        response.data = formatted_response
    
    return response
