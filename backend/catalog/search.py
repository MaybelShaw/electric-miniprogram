"""
Product search service with support for keyword search, filtering, and sorting.

Features:
- Keyword-based fuzzy search on product name and description
- Multi-condition filtering (category, brand, price range)
- Multiple sorting options (relevance, price, sales, creation date)
- Pagination support
- Search logging for analytics
"""

from django.db.models import Q, Count, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal
from typing import Dict, List, Optional, Any
from .models import Product, SearchLog


class ProductSearchService:
    """
    Service for searching and filtering products with advanced capabilities.
    
    Supports:
    - Keyword search on name and description
    - Filtering by category, brand, and price range
    - Multiple sorting strategies
    - Pagination with metadata
    """
    
    # Default page size for pagination
    DEFAULT_PAGE_SIZE = 20
    
    # Maximum page size to prevent abuse
    MAX_PAGE_SIZE = 100
    
    # Valid sort options
    VALID_SORT_OPTIONS = {
        'relevance',      # Keyword relevance (if keyword provided)
        'price_asc',      # Price ascending
        'price_desc',     # Price descending
        'sales',          # Sales count descending
        'created',        # Creation date descending (newest first)
        'views',          # View count descending
    }
    
    @classmethod
    def search(
        cls,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        sort_by: str = 'relevance',
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        user=None,
    ) -> Dict[str, Any]:
        """
        Search for products with multiple filter and sort options.
        
        Args:
            keyword: Search keyword for product name/description
            category: Filter by category name
            brand: Filter by brand name
            min_price: Minimum price filter
            max_price: Maximum price filter
            sort_by: Sort strategy (relevance, price_asc, price_desc, sales, created, views)
            page: Page number (1-indexed)
            page_size: Number of results per page
            user: User object for logging search (optional)
            
        Returns:
            Dict containing:
            - results: List of Product objects
            - total: Total number of matching products
            - page: Current page number
            - page_size: Results per page
            - total_pages: Total number of pages
            - has_next: Whether there's a next page
            - has_previous: Whether there's a previous page
            
        Raises:
            ValueError: If invalid sort_by option provided
        """
        # Validate sort option
        if sort_by not in cls.VALID_SORT_OPTIONS:
            sort_by = 'relevance'
        
        # Validate and constrain page size
        try:
            page_size = int(page_size)
            page_size = min(max(page_size, 1), cls.MAX_PAGE_SIZE)
        except (ValueError, TypeError):
            page_size = cls.DEFAULT_PAGE_SIZE
        
        # Admin can see all products; regular users see only active ones
        if user and getattr(user, 'is_staff', False):
            queryset = Product.objects.all()
        else:
            queryset = Product.objects.filter(is_active=True)
        
        # Apply keyword search
        if keyword and keyword.strip():
            keyword = keyword.strip()
            queryset = queryset.filter(
                Q(name__icontains=keyword) | 
                Q(description__icontains=keyword)
            )
            
            # Log search keyword
            cls._log_search(keyword, user)
        
        # Apply category filter
        if category and category.strip():
            queryset = queryset.filter(category__name__iexact=category.strip())
        
        # Apply brand filter
        if brand and brand.strip():
            queryset = queryset.filter(brand__name__iexact=brand.strip())
        
        # Apply price range filters
        if min_price is not None:
            try:
                min_price = Decimal(str(min_price))
                queryset = queryset.filter(price__gte=min_price)
            except (ValueError, TypeError):
                pass
        
        if max_price is not None:
            try:
                max_price = Decimal(str(max_price))
                queryset = queryset.filter(price__lte=max_price)
            except (ValueError, TypeError):
                pass
        
        # Apply sorting
        queryset = cls._apply_sorting(queryset, sort_by, keyword)
        
        # Apply pagination
        paginator = Paginator(queryset, page_size)
        
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_obj = paginator.page(page)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)
        
        return {
            'results': list(page_obj.object_list),
            'total': paginator.count,
            'page': page_obj.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    
    @classmethod
    def _apply_sorting(
        cls,
        queryset,
        sort_by: str,
        keyword: Optional[str] = None
    ):
        """
        Apply sorting to the queryset based on sort_by option.
        
        Args:
            queryset: Django queryset to sort
            sort_by: Sort strategy
            keyword: Search keyword (for relevance sorting)
            
        Returns:
            Sorted queryset
        """
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'sales':
            queryset = queryset.order_by('-sales_count', '-created_at')
        elif sort_by == 'views':
            queryset = queryset.order_by('-view_count', '-created_at')
        elif sort_by == 'created':
            queryset = queryset.order_by('-created_at')
        else:  # relevance or default
            # For relevance, prioritize name matches over description matches
            # and sort by sales/views as secondary criteria
            if keyword:
                queryset = queryset.annotate(
                    name_match=Case(
                        When(name__icontains=keyword, then=Value(2)),
                        default=Value(1),
                        output_field=IntegerField()
                    )
                ).order_by('-name_match', '-sales_count', '-created_at')
            else:
                queryset = queryset.order_by('-created_at')
        
        return queryset
    
    @classmethod
    def _log_search(cls, keyword: str, user=None) -> None:
        """
        Log a search query for analytics.
        
        Args:
            keyword: Search keyword
            user: User object (optional)
        """
        try:
            SearchLog.objects.create(
                keyword=keyword,
                user=user
            )
        except Exception:
            # Silently fail if logging fails to not interrupt search
            pass
    
    @classmethod
    def get_hot_keywords(cls, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get the most popular search keywords from recent searches.
        
        Args:
            limit: Maximum number of keywords to return
            days: Number of days to look back
            
        Returns:
            List of dicts with 'keyword' and 'count' keys, sorted by count descending
        """
        from django.utils import timezone
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        
        hot_keywords = SearchLog.objects.filter(
            created_at__gte=since
        ).values('keyword').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        return list(hot_keywords)
    
    @classmethod
    def get_search_suggestions(
        cls,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get search suggestions based on keyword prefix.
        
        Args:
            prefix: Keyword prefix to match
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested keywords
        """
        if not prefix or not prefix.strip():
            return []
        
        prefix = prefix.strip()
        
        # Get suggestions from product names and descriptions
        product_suggestions = Product.objects.filter(
            is_active=True,
            name__istartswith=prefix
        ).values_list('name', flat=True).distinct()[:limit]
        
        # Get suggestions from search history
        history_suggestions = SearchLog.objects.filter(
            keyword__istartswith=prefix
        ).values_list('keyword', flat=True).distinct()[:limit]
        
        # Combine and deduplicate
        all_suggestions = set(product_suggestions) | set(history_suggestions)
        
        return sorted(list(all_suggestions))[:limit]


# Import Case and When for relevance sorting
from django.db.models import Case, When, Value, IntegerField
