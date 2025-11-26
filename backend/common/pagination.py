"""
Custom pagination classes for DRF with enhanced metadata.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class with configurable page size.
    
    Returns pagination metadata including:
    - results: List of items
    - total: Total number of items
    - page: Current page number
    - total_pages: Total number of pages
    - has_next: Whether there is a next page
    - has_previous: Whether there is a previous page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    page_size_query_description = 'Number of results to return per page.'
    max_page_size = 100
    page_query_param = 'page'
    page_query_description = 'A page number within the paginated result set.'

    def get_paginated_response(self, data):
        """
        Return paginated response compatible with frontend expectations.
        """
        return Response({
            'results': data,
            'total': self.page.paginator.count,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            # Legacy fields for backward compatibility
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
        })


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class for large result sets with larger page size.
    
    Used for endpoints that return many items.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        """
        Return paginated response compatible with frontend expectations.
        """
        return Response({
            'results': data,
            'total': self.page.paginator.count,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            # Legacy fields for backward compatibility
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
        })


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination class for small result sets with smaller page size.
    
    Used for endpoints that return few items or for mobile clients.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        """
        Return paginated response compatible with frontend expectations.
        """
        return Response({
            'results': data,
            'total': self.page.paginator.count,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            # Legacy fields for backward compatibility
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
        })
