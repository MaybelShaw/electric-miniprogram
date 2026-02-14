from rest_framework import viewsets, permissions, status
from .models import Product, Category, MediaImage, Brand, SearchLog, HomeBanner, SpecialZoneCover, Case
from .serializers import ProductSerializer, CategorySerializer, MediaImageSerializer, BrandSerializer, SearchLogSerializer, HomeBannerSerializer, SpecialZoneCoverSerializer, CaseSerializer
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from django.db.models import Q, Count, Max
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.core.files.base import ContentFile
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.conf import settings
from common.permissions import IsAdminOrReadOnly, IsAdmin
from common.excel import build_excel_response
from common.utils import to_bool, parse_decimal, parse_int
from common.pagination import LargeResultsSetPagination
from common.throttles import CatalogBrowseAnonRateThrottle, CatalogBrowseRateThrottle
from .search import ProductSearchService
from decimal import Decimal
import uuid
import io
from urllib.parse import urlparse
from drf_spectacular.utils import extend_schema, extend_schema_field, OpenApiParameter, OpenApiTypes
from drf_spectacular.types import OpenApiTypes as OT

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None

# Higher limits for read-only browse endpoints (products, categories, brands, home, etc.)
class BrowseThrottleMixin:
    browse_throttle_classes = [CatalogBrowseAnonRateThrottle, CatalogBrowseRateThrottle]

    def get_throttles(self):
        action_name = getattr(self, 'action', None)
        if action_name:
            action_method = getattr(self, action_name, None)
            if action_method is not None and hasattr(action_method, 'throttle_classes'):
                return super().get_throttles()
        if 'throttle_classes' in self.__class__.__dict__:
            return super().get_throttles()
        rest_framework_cfg = getattr(settings, 'REST_FRAMEWORK', {}) or {}
        if not rest_framework_cfg.get('DEFAULT_THROTTLE_CLASSES'):
            return super().get_throttles()
        if self.request and self.request.method in permissions.SAFE_METHODS:
            return [throttle() for throttle in self.browse_throttle_classes]
        return super().get_throttles()

# Create your views here.
@extend_schema(tags=['Products'])
class ProductViewSet(BrowseThrottleMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing products with advanced search and filtering.
    
    Permissions:
    - GET (list/retrieve): AllowAny - public access
    - POST/PUT/PATCH/DELETE: IsAdminOrReadOnly - admin only
    
    Query Parameters for List:
    - search: Keyword search on product name and description
    - category: Filter by category name
    - brand: Filter by brand name
    - min_price: Minimum price filter
    - max_price: Maximum price filter
    - sort_by: Sort strategy (relevance, price_asc, price_desc, sales, created, views)
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20, max: 100)
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """Get base queryset with is_active filter support and optimized queries."""
        qs = super().get_queryset()
        
        # Optimize queries by prefetching related objects
        qs = qs.select_related('category', 'brand')
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            parsed = to_bool(is_active)
            if parsed is not None:
                try:
                    qs = qs.filter(is_active=parsed)
                except Exception:
                    pass

        gift_flag = self.request.query_params.get('show_in_gift_zone')
        if gift_flag is not None:
            parsed = to_bool(gift_flag)
            if parsed is not None:
                try:
                    qs = qs.filter(show_in_gift_zone=parsed)
                except Exception:
                    pass

        designer_flag = self.request.query_params.get('show_in_designer_zone')
        if designer_flag is not None:
            parsed = to_bool(designer_flag)
            if parsed is not None:
                try:
                    qs = qs.filter(show_in_designer_zone=parsed)
                except Exception:
                    pass

        best_seller_flag = self.request.query_params.get('show_in_best_seller_zone')
        if best_seller_flag is not None:
            parsed = to_bool(best_seller_flag)
            if parsed is not None:
                try:
                    qs = qs.filter(show_in_best_seller_zone=parsed)
                except Exception:
                    pass
        return qs

    @extend_schema(
        operation_id='products_destroy',
        description='删除商品：存在关联订单、购物车项、库存日志或折扣规则时，阻止删除并返回提示信息',
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        orders_count = instance.orders.count()
        cart_items_count = instance.cart_items.count()
        inventory_logs_count = instance.inventory_logs.count()
        discount_targets_count = instance.discount_targets.count()
        total_refs = orders_count + cart_items_count + inventory_logs_count + discount_targets_count
        if total_refs > 0:
            return Response(
                {
                    'error': '无法删除商品',
                    'message': (
                        f"该商品存在 {orders_count} 个关联订单、{cart_items_count} 个购物车项、{inventory_logs_count} 条库存日志、{discount_targets_count} 条折扣规则，无法删除"
                    ).strip(),
                    'orders_count': orders_count,
                    'cart_items_count': cart_items_count,
                    'inventory_logs_count': inventory_logs_count,
                    'discount_targets_count': discount_targets_count,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            from django.db.models.deletion import ProtectedError
            if isinstance(e, ProtectedError):
                return Response(
                    {
                        'error': '无法删除商品',
                        'message': '该商品被其他数据引用，无法删除',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise

    @extend_schema(
        operation_id='products_list',
        parameters=[
            OpenApiParameter('search', OT.STR, OpenApiParameter.QUERY, description='Keyword search on product name and description'),
            OpenApiParameter('category', OT.STR, OpenApiParameter.QUERY, description='Filter by category name'),
            OpenApiParameter('brand', OT.STR, OpenApiParameter.QUERY, description='Filter by brand name'),
            OpenApiParameter('min_price', OT.DECIMAL, OpenApiParameter.QUERY, description='Minimum price filter'),
            OpenApiParameter('max_price', OT.DECIMAL, OpenApiParameter.QUERY, description='Maximum price filter'),
            OpenApiParameter('sort_by', OT.STR, OpenApiParameter.QUERY, description='Sort strategy: relevance, price_asc, price_desc, sales, created, views'),
            OpenApiParameter('is_active', OT.BOOL, OpenApiParameter.QUERY, description='是否上架'),
            OpenApiParameter('show_in_gift_zone', OT.BOOL, OpenApiParameter.QUERY, description='是否在礼品专区展示'),
            OpenApiParameter('show_in_designer_zone', OT.BOOL, OpenApiParameter.QUERY, description='是否在设计师专区展示'),
            OpenApiParameter('page', OT.INT, OpenApiParameter.QUERY, description='Page number (default: 1)'),
            OpenApiParameter('page_size', OT.INT, OpenApiParameter.QUERY, description='Results per page (default: 20, max: 100)'),
        ],
        description='List products with advanced search and filtering. Returns paginated results with metadata.',
    )
    def list(self, request, *args, **kwargs):
        """
        List products with advanced search and filtering.
        
        Uses ProductSearchService for comprehensive search capabilities.
        Returns paginated results with metadata.
        """
        # Extract search parameters
        keyword = request.query_params.get('search', '').strip() or None
        category = request.query_params.get('category', '').strip() or None
        brand = request.query_params.get('brand', '').strip() or None
        sort_by = request.query_params.get('sort_by', 'relevance').strip()
        
        # Parse price filters
        min_price = parse_decimal(request.query_params.get('min_price'))
        max_price = parse_decimal(request.query_params.get('max_price'))

        is_active = to_bool(request.query_params.get('is_active'))
        show_in_gift_zone = to_bool(request.query_params.get('show_in_gift_zone'))
        show_in_designer_zone = to_bool(request.query_params.get('show_in_designer_zone'))
        
        # Parse pagination parameters
        page = parse_int(request.query_params.get('page')) or 1
        page_size = parse_int(request.query_params.get('page_size')) or 20
        
        # Get current user for search logging
        user = request.user if request.user.is_authenticated else None
        
        # Perform search
        search_result = ProductSearchService.search(
            keyword=keyword,
            category=category,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            is_active=is_active,
            show_in_gift_zone=show_in_gift_zone,
            show_in_designer_zone=show_in_designer_zone,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
            user=user,
        )
        
        # Serialize results
        serializer = self.get_serializer(search_result['results'], many=True)
        
        # Return paginated response with metadata (matching frontend expectations)
        return Response({
            'results': serializer.data,
            'total': search_result['total'],
            'page': search_result['page'],
            'total_pages': search_result['total_pages'],
            'has_next': search_result['has_next'],
            'has_previous': search_result['has_previous']
        })

    @extend_schema(
        operation_id='products_export',
        parameters=[
            OpenApiParameter('search', OT.STR, OpenApiParameter.QUERY, description='Keyword search on product name and description'),
            OpenApiParameter('category', OT.STR, OpenApiParameter.QUERY, description='Filter by category name'),
            OpenApiParameter('brand', OT.STR, OpenApiParameter.QUERY, description='Filter by brand name'),
            OpenApiParameter('min_price', OT.DECIMAL, OpenApiParameter.QUERY, description='Minimum price filter'),
            OpenApiParameter('max_price', OT.DECIMAL, OpenApiParameter.QUERY, description='Maximum price filter'),
            OpenApiParameter('sort_by', OT.STR, OpenApiParameter.QUERY, description='Sort strategy: relevance, price_asc, price_desc, sales, created, views'),
            OpenApiParameter('is_active', OT.BOOL, OpenApiParameter.QUERY, description='是否上架'),
            OpenApiParameter('show_in_gift_zone', OT.BOOL, OpenApiParameter.QUERY, description='是否在礼品专区展示'),
            OpenApiParameter('show_in_designer_zone', OT.BOOL, OpenApiParameter.QUERY, description='是否在设计师专区展示'),
        ],
        description='Export products with advanced search and filtering.',
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def export(self, request):
        keyword = request.query_params.get('search', '').strip() or None
        category = request.query_params.get('category', '').strip() or None
        brand = request.query_params.get('brand', '').strip() or None
        sort_by = request.query_params.get('sort_by', 'relevance').strip()

        min_price = parse_decimal(request.query_params.get('min_price'))
        max_price = parse_decimal(request.query_params.get('max_price'))

        is_active = to_bool(request.query_params.get('is_active'))
        show_in_gift_zone = to_bool(request.query_params.get('show_in_gift_zone'))
        show_in_designer_zone = to_bool(request.query_params.get('show_in_designer_zone'))

        if sort_by not in ProductSearchService.VALID_SORT_OPTIONS:
            sort_by = 'relevance'

        qs = self.get_queryset()
        if keyword:
            qs = qs.filter(Q(name__icontains=keyword) | Q(description__icontains=keyword))
        if category:
            qs = qs.filter(category__name__iexact=category)
        if brand:
            qs = qs.filter(brand__name__iexact=brand)
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        if is_active is not None:
            qs = qs.filter(is_active=bool(is_active))
        if show_in_gift_zone is not None:
            qs = qs.filter(show_in_gift_zone=bool(show_in_gift_zone))
        if show_in_designer_zone is not None:
            qs = qs.filter(show_in_designer_zone=bool(show_in_designer_zone))

        qs = ProductSearchService._apply_sorting(qs, sort_by, keyword)

        headers = [
            '商品ID',
            '产品名称',
            '品牌',
            '品项',
            '来源',
            '价格',
            '经销价',
            '库存',
            '上架状态',
            '礼品专区',
            '设计师专区',
            '爆品专区',
            '销量',
            '浏览量',
            '创建时间',
        ]
        rows = []
        for product in qs:
            rows.append([
                product.id,
                product.name,
                product.brand.name if product.brand else '',
                product.category.name if product.category else '',
                product.get_source_display(),
                product.price,
                product.dealer_price,
                product.stock,
                '上架' if product.is_active else '下架',
                '是' if product.show_in_gift_zone else '否',
                '是' if product.show_in_designer_zone else '否',
                '是' if product.show_in_best_seller_zone else '否',
                product.sales_count,
                product.view_count,
                product.created_at,
            ])

        filename = f"products_export_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return build_excel_response(filename, headers, rows, title="商品导出")

    @extend_schema(
        operation_id='products_search_suggestions',
        parameters=[
            OpenApiParameter('prefix', OT.STR, OpenApiParameter.QUERY, description='Keyword prefix to match (required)'),
            OpenApiParameter('limit', OT.INT, OpenApiParameter.QUERY, description='Maximum number of suggestions (default: 10)'),
        ],
        description='Get search suggestions based on keyword prefix.',
    )
    @action(detail=False, methods=['get'])
    def search_suggestions(self, request):
        """
        Get search suggestions based on keyword prefix.
        
        Query Parameters:
        - prefix: Keyword prefix to match (required)
        - limit: Maximum number of suggestions (default: 10)
        """
        prefix = request.query_params.get('prefix', '').strip()
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            limit = 10
        
        suggestions = ProductSearchService.get_search_suggestions(prefix, limit)
        return Response({'suggestions': suggestions})

    @extend_schema(
        operation_id='products_hot_keywords',
        parameters=[
            OpenApiParameter('limit', OT.INT, OpenApiParameter.QUERY, description='Maximum number of keywords (default: 10)'),
            OpenApiParameter('days', OT.INT, OpenApiParameter.QUERY, description='Number of days to look back (default: 7)'),
        ],
        description='Get the most popular search keywords.',
    )
    @action(detail=False, methods=['get'])
    def hot_keywords(self, request):
        """
        Get the most popular search keywords.
        
        Query Parameters:
        - limit: Maximum number of keywords (default: 10)
        - days: Number of days to look back (default: 7)
        """
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            limit = 10
        
        try:
            days = int(request.query_params.get('days', 7))
        except (ValueError, TypeError):
            days = 7
        
        hot_keywords = ProductSearchService.get_hot_keywords(limit, days)
        return Response({'hot_keywords': hot_keywords})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def with_discounts(self, request):
        ids = request.query_params.get('product_ids', '')
        try:
            pid_list = [int(x) for x in ids.split(',') if x]
        except Exception:
            pid_list = []
        if not pid_list:
            return Response([])
        qs = self.get_queryset().filter(id__in=pid_list)
        serializer = self.get_serializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get products by category with pagination support.
        
        Query Parameters:
        - category: Category name (required)
        - sort_by: Sort strategy (relevance, sales, price_asc, price_desc)
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20)
        """
        category_name = request.query_params.get('category', None)
        sort_by = request.query_params.get('sort_by', 'relevance').strip()
        
        # Parse pagination parameters
        try:
            page = int(request.query_params.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (ValueError, TypeError):
            page_size = 20
        
        if category_name is not None:
            products = self.get_queryset().filter(category__name=category_name)
        else:
            products = self.get_queryset()
        if not request.user.is_staff:
            products = products.filter(is_active=True)
        
        # Apply sorting
        if sort_by == 'sales':
            products = products.order_by('-sales_count')
        elif sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        elif sort_by == 'created':
            products = products.order_by('-created_at')
        else:  # relevance or default
            products = products.order_by('-sales_count', '-created_at')
        
        # Calculate pagination
        total = products.count()
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        start = (page - 1) * page_size
        end = start + page_size
        
        # Get page results
        results = products[start:end]
        
        serializer = self.get_serializer(results, many=True)
        
        # Return paginated response matching the list() format
        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1
        })

    @action(detail=False, methods=['get'])
    def by_brand(self, request):
        """
        Get products by brand with pagination support.
        
        Query Parameters:
        - brand: Brand name (required)
        - sort_by: Sort strategy (relevance, sales, price_asc, price_desc)
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20)
        """
        brand_name = request.query_params.get('brand', None)
        sort_by = request.query_params.get('sort_by', 'relevance').strip()
        
        # Parse pagination parameters
        try:
            page = int(request.query_params.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (ValueError, TypeError):
            page_size = 20
        
        if brand_name is not None:
            products = self.get_queryset().filter(brand__name=brand_name)
        else:
            products = self.get_queryset()
        if not request.user.is_staff:
            products = products.filter(is_active=True)
        
        # Apply sorting
        if sort_by == 'sales':
            products = products.order_by('-sales_count')
        elif sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        elif sort_by == 'created':
            products = products.order_by('-created_at')
        else:  # relevance or default
            products = products.order_by('-sales_count', '-created_at')
        
        # Calculate pagination
        total = products.count()
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        start = (page - 1) * page_size
        end = start + page_size
        
        # Get page results
        results = products[start:end]
        
        serializer = self.get_serializer(results, many=True)
        
        # Return paginated response matching the list() format
        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1
        })
    
    @extend_schema(
        operation_id='products_recommendations',
        parameters=[
            OpenApiParameter('type', OT.STR, OpenApiParameter.QUERY, description='Recommendation type: popular, category, trending (default: popular)'),
            OpenApiParameter('limit', OT.INT, OpenApiParameter.QUERY, description='Maximum number of recommendations (default: 10, max: 50)'),
            OpenApiParameter('category_id', OT.INT, OpenApiParameter.QUERY, description='Category ID for category-based recommendations (optional)'),
        ],
        description='Get product recommendations based on type.',
    )
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """
        Get product recommendations.
        
        Query Parameters:
        - type: Recommendation type (popular, category, trending) - default: popular
        - limit: Maximum number of recommendations (default: 10, max: 50)
        - category_id: Category ID for category-based recommendations (optional)
        
        Returns:
        - List of recommended products
        """
        rec_type = request.query_params.get('type', 'popular').lower()
        
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(limit, 50)  # Cap at 50
        except (ValueError, TypeError):
            limit = 10
        
        queryset = self.get_queryset().filter(is_active=True)
        
        if rec_type == 'popular':
            # Recommend by sales count
            products = queryset.order_by('-sales_count')[:limit]
        
        elif rec_type == 'trending':
            # Recommend by view count
            products = queryset.order_by('-view_count')[:limit]
        
        elif rec_type == 'category':
            # Recommend by category
            category_id = request.query_params.get('category_id')
            if category_id:
                try:
                    category_id = int(category_id)
                    products = queryset.filter(category_id=category_id).order_by('-sales_count')[:limit]
                except (ValueError, TypeError):
                    products = queryset.order_by('-sales_count')[:limit]
            else:
                products = queryset.order_by('-sales_count')[:limit]
        
        else:
            # Default to popular
            products = queryset.order_by('-sales_count')[:limit]
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single product with optimized queries.
        
        Preloads related category and brand data to avoid N+1 queries.
        """
        # Override queryset to ensure select_related is applied
        self.queryset = self.get_queryset()
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        operation_id='products_related',
        description='Get all products related to a specific product from the same category.',
    )
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """
        Get products related to a specific product.
        
        Returns all active products from the same category, excluding the current product.
        
        Returns:
        - List of related products
        """
        product = self.get_object()

        # Get products from the same category (by ID), excluding current product
        # Use select_related to optimize queries
        related_products = self.get_queryset().filter(
            category_id=product.category_id,
            is_active=True
        ).exclude(id=product.id).order_by('-sales_count')
        
        serializer = self.get_serializer(related_products, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='products_sync_haier_stock',
        description='同步海尔商品库存（仅限海尔产品，管理员权限）',
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def sync_haier_stock(self, request, pk=None):
        """
        同步海尔商品库存
        
        仅对海尔产品有效，需要管理员权限
        """
        product = self.get_object()
        
        # 检查是否为海尔产品
        if not product.product_code:
            return Response(
                {'detail': '该商品不是海尔产品，无需同步'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from integrations.haierapi import HaierAPI
            haier_api = HaierAPI.from_settings()
            
            # 认证
            if not haier_api.authenticate():
                return Response(
                    {'detail': '海尔API认证失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 查询库存
            county_code = request.data.get('county_code', '110101')
            stock_data = haier_api.check_stock(product.product_code, county_code)
            
            if not stock_data:
                return Response(
                    {'detail': '查询库存失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 更新库存
            product.update_stock_from_haier(stock_data)
            
            serializer = self.get_serializer(product)
            return Response({
                'detail': '库存同步成功',
                'product': serializer.data,
                'stock_data': stock_data,
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'同步海尔库存失败: {str(e)}')
            return Response(
                {'detail': f'同步失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        operation_id='products_sync_haier_price',
        description='同步海尔商品价格（仅限海尔产品，管理员权限）',
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def sync_haier_price(self, request, pk=None):
        """
        同步海尔商品价格
        
        仅对海尔产品有效，需要管理员权限
        """
        product = self.get_object()
        
        # 检查是否为海尔产品
        if not product.product_code:
            return Response(
                {'detail': '该商品不是海尔产品，无需同步'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from integrations.haierapi import HaierAPI
            haier_api = HaierAPI.from_settings()
            
            # 认证
            if not haier_api.authenticate():
                return Response(
                    {'detail': '海尔API认证失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 查询价格
            prices = haier_api.get_product_prices([product.product_code])
            
            if not prices:
                return Response(
                    {'detail': '查询价格失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 更新价格
            price_data = prices[0]
            if 'supplyPrice' in price_data:
                product.supply_price = price_data.get('supplyPrice')
                product.price = price_data.get('supplyPrice', product.price)
            if 'invoicePrice' in price_data:
                product.invoice_price = price_data.get('invoicePrice')
            if 'stockRebatePolicy' in price_data:
                product.stock_rebate = price_data.get('stockRebatePolicy')
            if 'rebateMoney' in price_data:
                product.rebate_money = price_data.get('rebateMoney')
            
            product.last_sync_at = timezone.now()
            product.save()
            
            serializer = self.get_serializer(product)
            return Response({
                'detail': '价格同步成功',
                'product': serializer.data,
                'price_data': price_data,
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'同步海尔价格失败: {str(e)}')
            return Response(
                {'detail': f'同步失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['Categories'])
class CategoryViewSet(BrowseThrottleMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing product categories.
    
    Permissions:
    - GET (list/retrieve): AllowAny - public access
    - POST/PUT/PATCH/DELETE: IsAdminOrReadOnly - admin only
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        # 名称模糊搜索
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)

        # 层级过滤：major / minor / item
        level = (self.request.query_params.get('level') or '').strip()
        if level in {Category.LEVEL_MAJOR, Category.LEVEL_MINOR, Category.LEVEL_ITEM}:
            qs = qs.filter(level=level)

        # 父类别过滤（适用于子品类与品项）
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            try:
                pid = int(parent_id)
                qs = qs.filter(parent_id=pid)
            except (ValueError, TypeError):
                pass

        return qs.order_by('order', 'id')

    @extend_schema(
        operation_id='categories_destroy',
        description='删除分类：存在子分类或关联商品时，阻止删除并返回提示信息',
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # 阻止删除存在子分类或商品的分类
        children_count = instance.children.count()
        products_count = instance.products.count()
        if children_count > 0 or products_count > 0:
            return Response(
                {
                    'error': '无法删除分类',
                    'message': (
                        f"该分类存在 {children_count} 个子分类、{products_count} 个关联商品，无法删除"
                    ).strip(),
                    'children_count': children_count,
                    'products_count': products_count,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # 无关联时正常删除，并防御PROTECT错误
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            from django.db.models.deletion import ProtectedError
            if isinstance(e, ProtectedError):
                return Response(
                    {
                        'error': '无法删除分类',
                        'message': '该分类被其他数据引用，无法删除',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise


@extend_schema(tags=['Brands'])
class BrandViewSet(BrowseThrottleMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing product brands.
    
    Provides CRUD operations for brands with admin-only write access.
    
    Permissions:
    - GET (list/retrieve): AllowAny - public access
    - POST/PUT/PATCH/DELETE: IsAdminOrReadOnly - admin only
    
    Features:
    - Search brands by name
    - Prevent deletion of brands with associated products
    - Support for force delete by admins
    
    Query Parameters:
    - search: Filter brands by name (case-insensitive substring match)
    - force_delete: Set to 'true' to force delete brand even with associated products (admin only)
    """
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """
        Get filtered brand queryset.
        
        Supports filtering by:
        - search: Brand name substring search
        """
        qs = super().get_queryset()
        # 名称模糊搜索
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs
    
    @extend_schema(
        operation_id='brands_destroy',
        parameters=[
            OpenApiParameter('force_delete', OT.BOOL, OpenApiParameter.QUERY, description='Force delete brand even with associated products (admin only)'),
        ],
        description='Delete a brand with protection against deleting brands with associated products.',
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete a brand with protection against deleting brands with associated products.
        
        Returns:
        - 204 No Content: Brand successfully deleted
        - 400 Bad Request: Brand has associated products (unless force_delete=true)
        - 403 Forbidden: User lacks permission to force delete
        """
        instance = self.get_object()
        
        # Check if brand has associated products
        associated_products = instance.products.count()
        
        if associated_products > 0:
            force_delete = to_bool(request.query_params.get('force_delete')) or False
            
            if not force_delete:
                # Return warning without deleting
                return Response(
                    {
                        'error': '无法删除品牌',
                        'message': f'该品牌有 {associated_products} 个关联商品，请先删除或转移这些商品',
                        'associated_products_count': associated_products,
                        'suggestion': '如需强制删除，请添加 ?force_delete=true 参数'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                # Only admins can force delete
                if not request.user or not request.user.is_staff:
                    return Response(
                        {
                            'error': '权限不足',
                            'message': '只有管理员可以强制删除有关联商品的品牌'
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        # Proceed with deletion, 捕获PROTECT错误
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            from django.db.models.deletion import ProtectedError
            if isinstance(e, ProtectedError):
                return Response(
                    {
                        'error': '无法删除品牌',
                        'message': '该品牌被商品引用，无法删除',
                        'associated_products_count': associated_products,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise


@extend_schema(tags=['Search'])
class SearchLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing search logs and analytics.
    
    Permissions:
    - GET (list/retrieve): IsAdminOrReadOnly - admin only for list, public for hot keywords
    
    Endpoints:
    - GET /api/search-logs/ - List all search logs (admin only)
    - GET /api/search-logs/hot-keywords/ - Get hot keywords (public)
    """
    queryset = SearchLog.objects.all().order_by('-created_at')
    serializer_class = SearchLogSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """Filter search logs by optional parameters."""
        qs = super().get_queryset()
        
        # Filter by keyword
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(keyword__icontains=keyword)
        
        # Filter by date range
        from django.utils import timezone
        from datetime import timedelta
        
        days = self.request.query_params.get('days')
        if days:
            d = parse_int(days)
            if d is not None:
                try:
                    since = timezone.now() - timedelta(days=d)
                    qs = qs.filter(created_at__gte=since)
                except Exception:
                    pass
        
        return qs
    
    @extend_schema(
        operation_id='search_logs_hot_keywords',
        parameters=[
            OpenApiParameter('limit', OT.INT, OpenApiParameter.QUERY, description='Maximum number of keywords (default: 10)'),
            OpenApiParameter('days', OT.INT, OpenApiParameter.QUERY, description='Number of days to look back (default: 7)'),
        ],
        description='Get the most popular search keywords.',
    )
    @throttle_classes([CatalogBrowseAnonRateThrottle, CatalogBrowseRateThrottle])
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def hot_keywords(self, request):
        """
        Get the most popular search keywords.
        
        Query Parameters:
        - limit: Maximum number of keywords (default: 10)
        - days: Number of days to look back (default: 7)
        """
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            limit = 10
        
        try:
            days = int(request.query_params.get('days', 7))
        except (ValueError, TypeError):
            days = 7
        
        hot_keywords = ProductSearchService.get_hot_keywords(limit, days)
        return Response({'hot_keywords': hot_keywords})

    @extend_schema(
        operation_id='search_logs_my_history',
        parameters=[
            OpenApiParameter('limit', OT.INT, OpenApiParameter.QUERY, description='Maximum number of records to return (default: 20)'),
            OpenApiParameter('distinct', OT.BOOL, OpenApiParameter.QUERY, description='Return distinct keywords sorted by last searched time (default: true)'),
        ],
        description='Get current user search history. Supports distinct keyword mode and limit.',
    )
    @throttle_classes([CatalogBrowseAnonRateThrottle, CatalogBrowseRateThrottle])
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_history(self, request):
        """
        Return search history for the current authenticated user.
        Supports:
        - distinct mode: deduplicated keywords ordered by last searched time with count
        - raw mode: latest search records
        """
        limit = parse_int(request.query_params.get('limit')) or 20
        distinct = request.query_params.get('distinct')
        use_distinct = True if distinct is None else to_bool(distinct)

        base_qs = SearchLog.objects.filter(user=request.user)

        if use_distinct:
            history_qs = (
                base_qs.values('keyword')
                .annotate(last_searched_at=Max('created_at'), count=Count('id'))
                .order_by('-last_searched_at')[:limit]
            )
            data = [
                {
                    'keyword': item['keyword'],
                    'last_searched_at': item['last_searched_at'],
                    'count': item['count'],
                }
                for item in history_qs
            ]
            total = base_qs.values('keyword').distinct().count()
            return Response({'results': data, 'total': total})

        history_qs = base_qs.order_by('-created_at')[:limit]
        serializer = self.get_serializer(history_qs, many=True)
        total = base_qs.count()
        return Response({'results': serializer.data, 'total': total})

    @extend_schema(
        operation_id='search_logs_clear_history',
        description='Clear search history for current user. Optionally provide keyword to delete a single keyword history.',
        request=None,
    )
    @action(detail=False, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def clear_history(self, request):
        """
        Clear search history for the authenticated user.
        If `keyword` is provided (body or query), only delete that keyword (case-insensitive).
        """
        keyword = (
            request.data.get('keyword')
            or request.query_params.get('keyword')
            or ''
        ).strip()

        qs = SearchLog.objects.filter(user=request.user)
        if keyword:
            qs = qs.filter(keyword__iexact=keyword)

        deleted, _ = qs.delete()
        return Response({'cleared': deleted})


@extend_schema(tags=['Media'])
class MediaImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing media images with enhanced security.
    
    Permissions:
    - GET (list/retrieve): AllowAny - public access
    - POST/PUT/PATCH/DELETE: IsAuthenticated - authenticated users only
    
    Features:
    - File validation (extension, size, MIME type)
    - Secure UUID-based filename generation
    - Original filename preservation
    - Optional image compression and format conversion
    
    Upload Parameters:
    - file: Required. The image file to upload
    - format: Optional. Target format (webp, jpeg, png)
    - compress: Optional. Whether to compress the image (1/true/yes/y)
    """
    queryset = MediaImage.objects.all().order_by('-created_at')
    serializer_class = MediaImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def _build_secure_filename(self, ext: str) -> str:
        """
        Generate a secure, unique filename using UUID.
        
        Prevents:
        - File name collisions
        - File overwrites
        - Path traversal attacks
        
        Args:
            ext (str): File extension (without dot)
            
        Returns:
            str: Secure filename path (e.g., 'images/2025/11/15/abc123def456.jpg')
        """
        now = timezone.now()
        dir_path = f"images/{now.year:04}/{now.month:02}/{now.day:02}/"
        # Use UUID hex to ensure uniqueness
        return dir_path + f"{uuid.uuid4().hex}.{ext}"

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """
        Convert MIME type to file extension.
        
        Args:
            mime_type (str): MIME type (e.g., 'image/jpeg')
            
        Returns:
            str: File extension without dot (e.g., 'jpg')
        """
        mime_to_ext = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp',
        }
        return mime_to_ext.get(mime_type, 'jpg')

    def _normalize_media_path(self, url: str) -> str:
        """
        Normalize image URL to a relative MEDIA_URL-based path for storage.
        """
        if not url:
            return ''
        if url.startswith(settings.MEDIA_URL):
            return url
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            path = parsed.path or ''
            if path:
                return path
        if url.startswith('/'):
            return url
        media_prefix = settings.MEDIA_URL.rstrip('/')
        return f"{media_prefix}/{url.lstrip('/')}"

    @extend_schema(
        operation_id='media_images_create',
        parameters=[
            OpenApiParameter('format', OT.STR, OpenApiParameter.QUERY, description='Target format: webp, jpeg, png'),
            OpenApiParameter('compress', OT.BOOL, OpenApiParameter.QUERY, description='Whether to compress the image'),
            OpenApiParameter('product_id', OT.INT, OpenApiParameter.QUERY, description='Product ID to update (optional)'),
            OpenApiParameter('field_name', OT.STR, OpenApiParameter.QUERY, description='Field name: main_images or detail_images (optional)'),
        ],
        description='Create a new media image with secure file handling. Optionally update product images immediately.',
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new media image with secure file handling.
        
        Implements:
        - File validation through serializer
        - Secure UUID-based filename generation
        - Original filename preservation
        - Optional image compression and format conversion
        
        Args:
            request: HTTP request with file in FILES
            
        Returns:
            Response: Serialized MediaImage data
            
        Raises:
            ValidationError: If file validation fails
        """
        file: UploadedFile | None = request.FILES.get('file')
        if not file:
            raise ValidationError('缺少文件: file')
        
        # Optional compression and format conversion parameters
        convert_to = (request.data.get('format') or request.query_params.get('format') or '').lower()
        compress_flag_raw = request.data.get('compress', request.query_params.get('compress'))
        compress_flag = str(compress_flag_raw).lower() in {'1', 'true', 'yes', 'y'}

        # Validate target format
        target_format = convert_to if convert_to in {'webp', 'jpeg', 'png'} else None

        # Get original content type
        content_type = getattr(file, 'content_type', '') or ''
        original_ext = self._get_extension_from_mime(content_type)

        # If Pillow is available and compression/conversion is requested
        if Image is not None and (compress_flag or target_format is not None):
            try:
                image = Image.open(file)
                save_format = (
                    'WEBP' if target_format == 'webp' else
                    'JPEG' if target_format == 'jpeg' else
                    'PNG' if target_format == 'png' else image.format
                )
                buf = io.BytesIO()
                save_kwargs = {}
                if save_format in {'JPEG', 'WEBP'} and compress_flag:
                    save_kwargs['quality'] = 85
                image.save(buf, format=save_format, **save_kwargs)
                buf.seek(0)
                ext = 'webp' if save_format == 'WEBP' else ('jpg' if save_format == 'JPEG' else 'png')
                
                # Generate secure filename
                secure_name = self._build_secure_filename(ext)
                
                media = MediaImage(
                    original_name=getattr(file, 'name', ''),
                    content_type=f"image/{'jpeg' if ext == 'jpg' else ext}",
                )
                media.file.save(secure_name, ContentFile(buf.read()), save=False)
                media.size = media.file.size
                media.save()
                serializer = self.get_serializer(media)
                return Response(serializer.data)
            except Exception as e:
                # Fallback to original file if processing fails
                pass

        # Save original file with secure UUID-based filename
        secure_name = self._build_secure_filename(original_ext)
        media = MediaImage(
            original_name=getattr(file, 'name', ''),
            content_type=content_type,
        )
        media.file.save(secure_name, file, save=False)
        media.size = media.file.size
        media.save()
        relative_url = self._normalize_media_path(media.file.url)
        
        # 如果提供了 product_id 和 field_name，立即更新产品
        product_id = request.data.get('product_id') or request.query_params.get('product_id')
        field_name = request.data.get('field_name') or request.query_params.get('field_name')
        
        # 调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'=== 图片上传 ===')
        logger.info(f'product_id={product_id}, field_name={field_name}')
        logger.info(f'request.data keys: {list(request.data.keys())}')
        logger.info(f'request.query_params: {dict(request.query_params)}')
        logger.info(f'图片URL(相对): {relative_url}')
        logger.info(f'图片URL(绝对): {request.build_absolute_uri(relative_url)}')
        
        if product_id and field_name and field_name in ['main_images', 'detail_images']:
            try:
                # 转换product_id为整数
                product_id = int(product_id)
                product = Product.objects.get(id=product_id)
                
                logger.info(f'找到产品 {product_id}，准备更新 {field_name}')
                
                # 获取当前图片列表并规范化为相对路径
                current_images = getattr(product, field_name) or []
                normalized_images = [
                    self._normalize_media_path(img)
                    for img in current_images
                    if img
                ]
                logger.info(f'当前图片列表(原始): {current_images}')
                logger.info(f'当前图片列表(规范化): {normalized_images}')
                
                # 添加新图片（去重后保存相对路径）
                if relative_url not in normalized_images:
                    normalized_images.append(relative_url)
                    setattr(product, field_name, normalized_images)
                    product.save(update_fields=[field_name])
                    
                    logger.info(f'✅ 产品已更新，新图片列表(规范化): {normalized_images}')
                    
                    # 在响应中添加产品更新信息
                    serializer = self.get_serializer(media)
                    response_data = serializer.data
                    response_data['product_updated'] = True
                    response_data['product_id'] = str(product_id)
                    response_data['field_name'] = field_name
                    logger.info(f'返回响应: {response_data}')
                    return Response(response_data, status=status.HTTP_201_CREATED)
                else:
                    logger.info(f'图片已存在，跳过更新')
            except Product.DoesNotExist:
                logger.warning(f'产品 {product_id} 不存在')
            except ValueError as e:
                logger.error(f'product_id格式错误: {e}')
            except Exception as e:
                # 图片已保存，但产品更新失败，记录错误但不影响图片上传
                logger.error(f'更新产品失败 {product_id}: {e}', exc_info=True)
        
        serializer = self.get_serializer(media)
        logger.info(f'返回普通响应: {serializer.data}')
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Home'])
class HomeBannerViewSet(BrowseThrottleMixin, viewsets.ModelViewSet):
    """
    首页轮播图管理
    
    - GET /api/v1/catalog/home-banners/       获取轮播图列表（公开）
    - POST /api/v1/catalog/home-banners/      创建轮播图（管理员）
    - POST /api/v1/catalog/home-banners/upload/  上传图片并创建轮播图（管理员）
    """
    queryset = HomeBanner.objects.all().order_by('order', '-id')
    serializer_class = HomeBannerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # position filter
        position = self.request.query_params.get('position')
        if position:
            qs = qs.filter(position=position)

        # 公开接口默认只返回启用的轮播图
        if self.request and self.request.method == 'GET' and not self.request.user.is_staff:
            return qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_staff:
            raise PermissionDenied('仅管理员可创建轮播图')
        serializer.save()

    @extend_schema(
        operation_id='home_banners_upload',
        parameters=[
            OpenApiParameter('title', OT.STR, OpenApiParameter.QUERY, description='轮播图标题'),
            OpenApiParameter('product_id', OT.INT, OpenApiParameter.QUERY, description='跳转商品ID'),
            OpenApiParameter('position', OT.STR, OpenApiParameter.QUERY, description='展示位置'),
            OpenApiParameter('order', OT.INT, OpenApiParameter.QUERY, description='排序值'),
            OpenApiParameter('is_active', OT.BOOL, OpenApiParameter.QUERY, description='是否启用'),
        ],
        description='上传图片并创建首页轮播图（管理员）',
    )
    @action(detail=False, methods=['post'])
    def upload(self, request):
        user = getattr(request, 'user', None)
        if not user or not user.is_staff:
            raise PermissionDenied('仅管理员可上传轮播图')

        file: UploadedFile | None = request.FILES.get('file')
        if not file:
            raise ValidationError('缺少文件: file')

        # 使用与 MediaImageViewSet 相同的安全文件处理逻辑
        content_type = getattr(file, 'content_type', '') or ''
        original_ext = self._get_extension_from_mime(content_type)

        try:
            secure_name = self._build_secure_filename(original_ext)
        except Exception:
            secure_name = f"images/{uuid.uuid4().hex}.{original_ext or 'jpg'}"

        media = MediaImage(
            original_name=getattr(file, 'name', ''),
            content_type=content_type,
        )
        media.file.save(secure_name, file, save=False)
        media.size = media.file.size
        media.save()

        title = request.data.get('title') or request.query_params.get('title') or ''
        product_id_raw = request.data.get('product_id')
        if product_id_raw in (None, ''):
            product_id_raw = request.query_params.get('product_id')
        product = None
        if product_id_raw not in (None, ''):
            try:
                product_id = int(product_id_raw)
                product = Product.objects.get(id=product_id)
            except (ValueError, TypeError):
                raise ValidationError('product_id格式错误')
            except Product.DoesNotExist:
                raise ValidationError('product_id对应商品不存在')
        position = request.data.get('position') or request.query_params.get('position') or 'home'
        try:
            order = int(request.data.get('order') or request.query_params.get('order') or 0)
        except (ValueError, TypeError):
            order = 0
        is_active_raw = request.data.get('is_active', request.query_params.get('is_active'))
        is_active = str(is_active_raw).lower() in {'1', 'true', 'yes', 'y'} if is_active_raw is not None else True

        banner = HomeBanner.objects.create(
            image=media,
            title=title,
            product=product,
            position=position,
            order=order,
            is_active=is_active,
        )
        serializer = self.get_serializer(banner)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # 复用 MediaImageViewSet 的工具方法
    def _build_secure_filename(self, ext: str) -> str:
        now = timezone.now()
        dir_path = f"images/{now.year:04}/{now.month:02}/{now.day:02}/"
        return dir_path + f"{uuid.uuid4().hex}.{ext}"

    def _get_extension_from_mime(self, mime_type: str) -> str:
        mime_to_ext = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp',
        }
        return mime_to_ext.get(mime_type, 'jpg')


@extend_schema(tags=['Home'])
class SpecialZoneCoverViewSet(BrowseThrottleMixin, viewsets.ModelViewSet):
    """
    首页专区图片管理

    - GET /api/v1/catalog/special-zone-covers/ 获取首页专区图片列表（公开）
    - POST /api/v1/catalog/special-zone-covers/ 创建首页专区图片（管理员）
    """
    queryset = SpecialZoneCover.objects.all().select_related('image').order_by('type')
    serializer_class = SpecialZoneCoverSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()

        zone_type = self.request.query_params.get('type')
        if zone_type:
            qs = qs.filter(type=zone_type)

        if self.request and self.request.method == 'GET' and not getattr(self.request.user, 'is_staff', False):
            return qs.filter(is_active=True)
        return qs


@extend_schema(tags=['Cases'])
class CaseViewSet(BrowseThrottleMixin, viewsets.ModelViewSet):
    queryset = Case.objects.all().order_by('order', '-id')
    serializer_class = CaseSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('cover_image')
            .prefetch_related('detail_blocks__image')
        )
        if self.request and self.request.method == 'GET' and not getattr(self.request.user, 'is_staff', False):
            return qs.filter(is_active=True)
        return qs
