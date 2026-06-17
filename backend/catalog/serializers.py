from rest_framework import serializers
from decimal import Decimal
from .models import Category, Brand, Product, ProductSKU, MediaImage, SearchLog, InventoryLog, HomeBanner, SpecialZone, SpecialZoneProduct, SpecialZoneCover, HomeStoreCard, HomeStoreCardProduct, HomeStoreCardCategory, Case, CaseDetailBlock
from orders.services import get_best_active_discount, resolve_base_price
from django.conf import settings
from urllib.parse import urlparse
from common.serializers import (
    SecureCharField,
    ImageFileValidator,
    PriceField,
    StockField,
)
from stores.models import Store
from stores.permissions import get_active_memberships, is_platform_admin, is_support_user
from django.db.models import Q
from drf_spectacular.utils import extend_schema_field


def _is_absolute_url(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')


LEGACY_MEDIA_BASE_URL = 'https://img.qxelectric.cn/media/'
LEGACY_MEDIA_PATH_PREFIXES = ('images/images/',)


def _legacy_media_url(url: str) -> str:
    if not url:
        return ''
    parsed = urlparse(str(url).strip())
    media_path = (parsed.path or '').lstrip('/')
    media_prefix = (urlparse(settings.MEDIA_URL or '/media/').path or '/media/').strip('/')
    if media_prefix and media_path.startswith(f'{media_prefix}/'):
        media_path = media_path[len(media_prefix) + 1:]
    if not any(media_path.startswith(prefix) for prefix in LEGACY_MEDIA_PATH_PREFIXES):
        return ''
    suffix = ''
    if parsed.query:
        suffix = f'{suffix}?{parsed.query}'
    if parsed.fragment:
        suffix = f'{suffix}#{parsed.fragment}' if suffix else f'#{parsed.fragment}'
    return f'{LEGACY_MEDIA_BASE_URL}{media_path}{suffix}'


def _resolve_media_url(url: str) -> str:
    """Build an absolute media URL when MEDIA_URL is absolute."""
    if not url:
        return url
    legacy_url = _legacy_media_url(url)
    if legacy_url:
        return legacy_url
    if _is_absolute_url(url):
        return url
    media_base = settings.MEDIA_URL or '/media/'
    if not _is_absolute_url(media_base):
        return url
    base = media_base if media_base.endswith('/') else f"{media_base}/"
    base_path = urlparse(base).path or '/'
    trimmed = url
    if base_path != '/' and trimmed.startswith(base_path):
        trimmed = trimmed[len(base_path):]
    trimmed = trimmed.lstrip('/')
    return f"{base}{trimmed}"


def _build_media_url(url: str, request=None) -> str:
    if not url:
        return ''
    resolved_url = _resolve_media_url(url)
    if _is_absolute_url(resolved_url):
        return _ensure_https(resolved_url, request)
    if request:
        return _ensure_https(request.build_absolute_uri(resolved_url), request)
    return _ensure_https(resolved_url, request)


def _build_media_file_url(file_field, request=None) -> str:
    if not file_field:
        return ''
    file_name = getattr(file_field, 'name', '') or ''
    if file_name:
        resolved_name = _resolve_media_url(file_name)
        if _is_absolute_url(resolved_name):
            return _ensure_https(resolved_name, request)
    try:
        return _build_media_url(file_field.url, request)
    except (AttributeError, ValueError):
        return ''


def _ensure_https(url: str, request=None) -> str:
    """Upgrade to HTTPS only when the request is HTTPS."""
    if not url:
        return url
    if request is None or not request.is_secure():
        return url
    if url.startswith('http://'):
        return 'https://' + url[len('http://'):]
    return url


class CategorySerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        source='store',
        required=False,
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='parent',
        allow_null=True,
        required=False
    )
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "store", "store_id", "name", "order", "logo", "level", "parent_id", "children"]
        read_only_fields = ["store"]
        # Disable default validators to allow custom duplicate check in validate()
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 动态限制父类别可选范围
        level = None
        if hasattr(self, 'initial_data') and isinstance(self.initial_data, dict):
            level = self.initial_data.get('level')
        elif self.instance:
            level = getattr(self.instance, 'level', None)

        if level == Category.LEVEL_MINOR:
            self.fields['parent_id'].queryset = Category.objects.filter(level=Category.LEVEL_MAJOR)
        elif level == Category.LEVEL_ITEM:
            self.fields['parent_id'].queryset = Category.objects.filter(level=Category.LEVEL_MINOR)
        else:
            self.fields['parent_id'].queryset = Category.objects.filter(id__isnull=False)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj: Category):
        # 返回直接子节点（避免无限嵌套）
        if obj.level not in {Category.LEVEL_MAJOR, Category.LEVEL_MINOR}:
            return []
        qs = obj.children.all().order_by('order', 'id')
        return [
            {
                'id': c.id,
                'name': c.name,
                'order': c.order,
                'logo': c.logo,
                'level': c.level,
                'store': c.store_id,
                'parent_id': obj.id,
            }
            for c in qs
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        rep['logo'] = _build_media_url(rep.get('logo'), request)
        rep['children'] = [
            {**child, 'logo': _build_media_url(child.get('logo'), request)}
            for child in rep.get('children', [])
        ]
        return rep

    def validate(self, attrs):
        name = attrs.get('name')
        parent = attrs.get('parent')
        level = attrs.get('level')
        
        # If updating, use existing values if not provided
        if self.instance:
            if 'name' not in attrs:
                name = self.instance.name
            if 'parent' not in attrs:
                parent = self.instance.parent
            if 'level' not in attrs:
                level = self.instance.level
        
        # Check for duplicates
        if level and name:
            store = attrs.get('store') or getattr(self.instance, 'store', None)
            qs = Category.objects.filter(store=store, level=level, name=name, parent=parent)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                if parent:
                    raise serializers.ValidationError({'name': '同父分类下名称已存在'})
                else:
                    raise serializers.ValidationError({'name': '同层级根分类名称已存在'})
        
        return attrs


class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer for Brand model.
    
    Includes all brand fields with validation:
    - name: Required, unique brand name
    - logo: Optional URL to brand logo
    - description: Optional brand description
    - order: Display order for sorting
    - is_active: Whether brand is active/visible
    - created_at: Timestamp when brand was created
    - updated_at: Timestamp when brand was last updated
    """
    name = SecureCharField(max_length=100)
    description = SecureCharField(required=False, allow_blank=True)
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        source='store',
        required=False,
    )
    
    class Meta:
        model = Brand
        fields = ["id", "store", "store_id", "name", "logo", "description", "order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "store", "created_at", "updated_at"]
        validators = []
    
    def validate_name(self, value):
        """Validate brand name is not empty after stripping."""
        if not value or not value.strip():
            raise serializers.ValidationError("品牌名称不能为空")
        return value

    def validate_logo(self, value: str) -> str:
        """Normalize logo path to avoid storing host-specific URLs."""
        return self._normalize_logo_path(value)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['logo'] = self._build_full_logo_url(rep.get('logo'))
        return rep

    def _normalize_logo_path(self, logo: str) -> str:
        """Strip host info and normalize to media-relative path, mirroring product images."""
        if not logo:
            return ''
        if logo.startswith(settings.MEDIA_URL):
            return logo
        parsed = urlparse(logo)
        if parsed.scheme or parsed.netloc:
            path = parsed.path or ''
            suffix = ''
            if parsed.query:
                suffix = f"{suffix}?{parsed.query}"
            if parsed.fragment:
                suffix = f"{suffix}#{parsed.fragment}" if suffix else f"#{parsed.fragment}"
            # Only strip host for our media paths or same-host URLs; keep external URLs unchanged
            request = self.context.get('request')
            request_host = request.get_host() if request else None
            if path and (path.startswith(settings.MEDIA_URL) or parsed.netloc == request_host):
                return f"{path}{suffix}"
            return logo
        if logo.startswith('/'):
            return logo
        media_prefix = settings.MEDIA_URL.rstrip('/')
        return f"{media_prefix}/{logo.lstrip('/')}"

    def _build_full_logo_url(self, logo: str) -> str:
        """Build absolute URL like product images do."""
        if not logo:
            return ''
        normalized_logo = self._normalize_logo_path(logo)
        if not normalized_logo:
            return ''
        request = self.context.get('request')
        if _is_absolute_url(normalized_logo):
            return _ensure_https(normalized_logo, request)
        resolved_logo = _resolve_media_url(normalized_logo)
        if _is_absolute_url(resolved_logo):
            return _ensure_https(resolved_logo, request)
        if request:
            try:
                return _ensure_https(request.build_absolute_uri(normalized_logo), request)
            except Exception:
                pass
        return normalized_logo


class ProductSKUSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True,
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    display_price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductSKU
        fields = [
            'id',
            'product',
            'product_id',
            'product_name',
            'name',
            'sku_code',
            'specs',
            'price',
            'display_price',
            'discounted_price',
            'stock',
            'image',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'product', 'product_name', 'created_at', 'updated_at', 'display_price', 'discounted_price']

    def validate_specs(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('规格参数必须是键值对象')
        return value

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_display_price(self, obj: ProductSKU):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return resolve_base_price(user, obj.product, sku=obj)

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_discounted_price(self, obj: ProductSKU):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        base_price = self.get_display_price(obj)
        amount = get_best_active_discount(user, obj.product, base_price=base_price)
        return base_price - amount


class ProductSerializer(serializers.ModelSerializer):
    # 读：显示名称和ID；写：通过 *_id 设置关联
    category = serializers.StringRelatedField(read_only=True)
    brand = serializers.StringRelatedField(read_only=True)
    store_id = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), source='store', required=False)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category')
    brand_id = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), source='brand')
    discounted_price = serializers.SerializerMethodField()
    display_price = serializers.SerializerMethodField()
    originalPrice = serializers.SerializerMethodField()
    skus = serializers.SerializerMethodField()
    spec_options = serializers.SerializerMethodField()
    
    # 海尔相关字段（只读）
    is_haier_product = serializers.SerializerMethodField()
    haier_info = serializers.SerializerMethodField()
    
    # Use secure fields for text input
    name = SecureCharField(max_length=200)
    description = SecureCharField(required=False, allow_blank=True)
    product_model = SecureCharField(max_length=100, required=False, allow_blank=True)
    product_group = SecureCharField(max_length=100, required=False, allow_blank=True)
    warehouse_code = SecureCharField(max_length=50, required=False, allow_blank=True)
    no_sales_reason = SecureCharField(max_length=200, required=False, allow_blank=True)
    
    # Use specialized fields for numeric input
    price = PriceField(max_digits=10, decimal_places=2)
    stock = StockField()
    supply_price = PriceField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    invoice_price = PriceField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    market_price = PriceField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    stock_rebate = PriceField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    rebate_money = PriceField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = Product
        fields = "__all__"
        extra_fields = [
            'discounted_price',
            'display_price',
            'originalPrice',
            'category_id',
            'brand_id',
            'is_haier_product',
            'haier_info',
            'skus',
            'spec_options',
        ]
        read_only_fields = ['id', 'store', 'created_at', 'updated_at', 'last_sync_at', 'view_count', 'sales_count']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        store = attrs.get('store') or getattr(self.instance, 'store', None)
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        brand = attrs.get('brand') or getattr(self.instance, 'brand', None)

        if store and category and category.store_id != store.id:
            raise serializers.ValidationError({'category_id': '商品分类必须属于同一店铺'})
        if store and brand and brand.store_id != store.id:
            raise serializers.ValidationError({'brand_id': '商品品牌必须属于同一店铺'})
        return attrs

    def validate_main_images(self, value):
        return self._normalize_images(value)
    
    def validate_detail_images(self, value):
        normalized = self._normalize_images(value)
        if len(normalized) > 50:
            raise serializers.ValidationError("详情图最多上传50张")
        return normalized

    def validate_specifications(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("商品参数必须是键值对象")
        return value
    
    def _normalize_images(self, images):
        if not images:
            return []
        normalized = []
        for url in images:
            normalized_url = self._normalize_image_url(url)
            if normalized_url:
                normalized.append(normalized_url)
        return normalized
    
    def _normalize_image_url(self, url: str) -> str:
        if not url:
            return ''
        if url.startswith(settings.MEDIA_URL):
            return url
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            path = parsed.path or ''
            if path:
                suffix = ''
                if parsed.query:
                    suffix = f"?{parsed.query}"
                if parsed.fragment:
                    suffix = f"{suffix}#{parsed.fragment}" if suffix else f"#{parsed.fragment}"
                request = self.context.get('request')
                request_host = request.get_host() if request else None
                if path.startswith(settings.MEDIA_URL) or (request_host and parsed.netloc == request_host):
                    return f"{path}{suffix}"
                return url
        if url.startswith('/'):
            return url
        media_prefix = settings.MEDIA_URL.rstrip('/')
        return f"{media_prefix}/{url.lstrip('/')}"

    def _viewer_flags(self):
        cached = self.context.get('_product_viewer_flags')
        if cached is not None:
            return cached
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_authenticated = bool(user and user.is_authenticated)
        is_backend_user = bool(
            is_authenticated and (
                is_platform_admin(user)
                or is_support_user(user)
                or get_active_memberships(user).exists()
            )
        )
        flags = {
            'dealer_price': bool(is_authenticated and (getattr(user, 'role', '') == 'dealer' or is_backend_user)),
            'internal_fields': is_backend_user,
        }
        self.context['_product_viewer_flags'] = flags
        return flags

    def to_representation(self, instance):
        """自定义序列化输出，将图片URL转换为完整URL"""
        rep = super().to_representation(instance)
        viewer_flags = self._viewer_flags()
        if not viewer_flags['dealer_price']:
            rep.pop('dealer_price', None)
        if not viewer_flags['internal_fields']:
            for field in (
                'product_code',
                'supply_price',
                'invoice_price',
                'stock_rebate',
                'rebate_money',
                'is_sales',
                'no_sales_reason',
                'warehouse_code',
                'warehouse_grade',
                'last_sync_at',
            ):
                rep.pop(field, None)
        # 合并额外字段
        rep['discounted_price'] = self.get_discounted_price(instance)
        rep['display_price'] = self.get_display_price(instance)
        rep['originalPrice'] = self.get_originalPrice(instance)
        rep.update(self.get_customer_group_context(instance))
        rep['is_haier_product'] = self.get_is_haier_product(instance)
        rep['haier_info'] = self.get_haier_info(instance)
        
        # 处理主图：优先使用本地上传的图片，其次使用海尔图片
        local_main = self._get_full_image_urls(instance.main_images)
        if local_main:
            rep['main_images'] = local_main
        elif instance.product_image_url:
            rep['main_images'] = [instance.product_image_url]
        else:
            rep['main_images'] = []

        # 处理详情图：优先使用海尔拉页，其次使用本地上传的详情图
        detail_images = []
        if instance.product_page_urls and len(instance.product_page_urls) > 0:
            # 海尔拉页URL已经是完整URL，直接使用
            detail_images = [url for url in instance.product_page_urls if url]
        
        if not detail_images:
            # 如果没有海尔拉页，使用本地详情图
            detail_images = self._get_full_image_urls(instance.detail_images)
        
        rep['detail_images'] = detail_images
        
        # 价格字段：保留 price 作为商户对外售价，供价通过 supply_price 返回
        # 如果前端需要“显示价”为供价，可使用 rep['supply_price'] 或自行选择显示策略
        # SKU 列表
        rep['skus'] = self.get_skus(instance)
        rep['spec_options'] = self.get_spec_options(instance)
        # 如果存在SKU，用SKU聚合库存与价格
        if rep['skus']:
            try:
                rep['stock'] = sum([int(s.get('stock') or 0) for s in rep['skus'] if s.get('is_active', True)])
            except Exception:
                pass
            try:
                prices = [float(s.get('price')) for s in rep['skus'] if s.get('is_active', True) and s.get('price') is not None]
                if prices:
                    rep['price'] = min(prices)
            except Exception:
                pass
            try:
                display_prices = []
                for sku in rep['skus']:
                    display = sku.get('display_price')
                    if display is not None:
                        display_prices.append(Decimal(str(display)))
                if display_prices:
                    rep['display_price'] = min(display_prices)
            except Exception:
                pass
            try:
                discounted_prices = []
                for sku in rep['skus']:
                    discounted = sku.get('discounted_price')
                    if discounted is not None:
                        discounted_prices.append(Decimal(str(discounted)))
                if discounted_prices:
                    rep['discounted_price'] = min(discounted_prices)
            except Exception:
                pass
        
        return rep
    
    def validate(self, attrs):
        category = attrs.get('category')
        if category is None and self.instance is not None:
            category = getattr(self.instance, 'category', None)
        if category and getattr(category, 'level', None) not in {Category.LEVEL_MINOR, Category.LEVEL_ITEM}:
            raise serializers.ValidationError({'category_id': '商品必须关联到子品类或品项'})
        return attrs

    def validate_product_code(self, value):
        source = None
        try:
            source = (self.initial_data or {}).get('source')
        except AttributeError:
            source = None
        if not source and self.instance is not None:
            source = getattr(self.instance, 'source', None)

        if isinstance(value, str):
            value = value.strip()

        if source == Product.SOURCE_HAIER:
            if not value:
                raise serializers.ValidationError('海尔商品必须设置产品编码')
        else:
            if not value:
                return None

        qs = Product.objects.filter(product_code=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('海尔产品编码已存在，请使用唯一编码')
        return value

    def _get_full_image_urls(self, images):
        """将图片URL转换为完整URL"""
        if not images:
            return []
        
        request = self.context.get('request')
        result = []
        
        for img_url in images:
            if not img_url:
                continue
            if _is_absolute_url(img_url):
                # 已经是完整URL
                result.append(_ensure_https(img_url, request))
                continue
            resolved_url = _resolve_media_url(img_url)
            if _is_absolute_url(resolved_url):
                result.append(_ensure_https(resolved_url, request))
                continue
            if request:
                # 构建完整URL
                result.append(_ensure_https(request.build_absolute_uri(img_url), request))
            else:
                result.append(img_url)
        
        return result
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_haier_product(self, obj: Product):
        """判断是否为海尔产品"""
        # 只根据 source 字段判断
        return getattr(obj, 'source', None) == getattr(obj, 'SOURCE_HAIER', 'haier')
    
    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_haier_info(self, obj: Product):
        """获取海尔产品信息"""
        if not self._viewer_flags()['internal_fields']:
            return None
        # 只有标记为海尔商品并且有 product_code 才返回详细信息
        if not self.get_is_haier_product(obj) or not obj.product_code:
            return None
        
        return {
            'product_code': obj.product_code,
            'product_model': obj.product_model,
            'product_group': obj.product_group,
            'supply_price': obj.supply_price,
            'invoice_price': obj.invoice_price,
            'market_price': obj.market_price,
            'is_sales': obj.is_sales,
            'no_sales_reason': obj.no_sales_reason,
            'warehouse_code': obj.warehouse_code,
            'warehouse_grade': obj.warehouse_grade,
            'last_sync_at': obj.last_sync_at,
        }

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_originalPrice(self, obj: Product):
        """获取原价（市场价或普通价格）"""
        if obj.market_price:
            return obj.market_price
        return obj.price

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_discounted_price(self, obj: Product):
        """获取折扣价"""
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        base_price = resolve_base_price(user, obj)
        if not user or not user.is_authenticated:
            return base_price

        amount = get_best_active_discount(user, obj, base_price=base_price)
        return base_price - amount

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_display_price(self, obj: Product):
        """获取展示价（经销商优先经销价，空/0回退零售价）"""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return resolve_base_price(user, obj)

    def get_customer_group_context(self, obj: Product):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        try:
            from stores.pricing import get_customer_group_price_context

            return get_customer_group_price_context(user, obj)
        except Exception:
            return {
                'customer_group_id': None,
                'customer_group_name': '',
                'show_customer_group_name': False,
            }

    @extend_schema_field(ProductSKUSerializer(many=True))
    def get_skus(self, obj: Product):
        skus = getattr(obj, 'skus', None)
        if skus is None:
            return []
        serializer = ProductSKUSerializer(
            skus.filter(is_active=True),
            many=True,
            context=self.context
        )
        return serializer.data

    @extend_schema_field(serializers.DictField(child=serializers.ListField(child=serializers.CharField())))
    def get_spec_options(self, obj: Product):
        options = {}
        for sku in obj.skus.all() if hasattr(obj, 'skus') else []:
            if not sku.is_active or not sku.specs:
                continue
            for k, v in sku.specs.items():
                if not k:
                    continue
                options.setdefault(k, set()).add(str(v))
        # 转换为列表
        return {k: sorted(list(v_set)) for k, v_set in options.items()}
    



class MediaImageSerializer(serializers.ModelSerializer):
    """
    Serializer for MediaImage model with enhanced file upload security.
    
    Features:
    - File validation (extension, size, MIME type)
    - Secure file naming with UUID
    - Original filename preservation
    - Content type detection
    
    The serializer validates uploaded files and stores them with:
    - UUID-based filename to prevent collisions and overwrites
    - Original filename preserved in database for reference
    - Detected content type for verification
    """
    url = serializers.SerializerMethodField()
    
    # Add file validation with ImageFileValidator
    file = serializers.FileField(validators=[ImageFileValidator()])

    class Meta:
        model = MediaImage
        fields = ['id', 'file', 'url', 'original_name', 'content_type', 'size', 'created_at']
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(serializers.CharField())
    def get_url(self, obj: MediaImage):
        """
        Get the absolute URL for the media image.
        
        Args:
            obj (MediaImage): The MediaImage instance
            
        Returns:
            str: Absolute URL to the image file
        """
        return _build_media_file_url(obj.file, self.context.get('request'))

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        url = self.get_url(instance)
        rep['file'] = url
        rep['url'] = url
        return rep
    
    def create(self, validated_data):
        """
        Create a MediaImage instance with secure file handling.
        
        Implements:
        - UUID-based filename generation to prevent collisions
        - Original filename preservation for reference
        - Content type detection and storage
        - File size recording
        
        Args:
            validated_data (dict): Validated data from the serializer
            
        Returns:
            MediaImage: Created MediaImage instance
        """
        file = validated_data.get('file')
        
        if file:
            # Store original filename for reference
            validated_data['original_name'] = file.name
            
            # Detect and store content type
            if hasattr(file, 'content_type') and file.content_type:
                validated_data['content_type'] = file.content_type
            else:
                import mimetypes
                content_type, _ = mimetypes.guess_type(file.name)
                validated_data['content_type'] = content_type or 'application/octet-stream'
            
            # Store file size
            validated_data['size'] = file.size
        
        return super().create(validated_data)



class SearchLogSerializer(serializers.ModelSerializer):
    """
    Serializer for SearchLog model.
    
    Provides read-only access to search logs for analytics.
    
    Fields:
    - id: Unique identifier
    - keyword: Search keyword
    - user: User who performed the search (null for anonymous)
    - created_at: Timestamp of the search
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True, allow_null=True)
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = SearchLog
        fields = ['id', 'keyword', 'user_id', 'username', 'created_at']
        read_only_fields = ['id', 'keyword', 'user_id', 'username', 'created_at']


class SpecialZoneSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        source='store',
        required=False,
    )

    class Meta:
        model = SpecialZone
        fields = [
            'id',
            'store',
            'store_id',
            'title',
            'slug',
            'kind',
            'subtitle',
            'cover_image',
            'is_active',
            'show_on_home',
            'home_order',
            'start_at',
            'end_at',
            'description',
            'rules',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'store', 'created_at', 'updated_at']
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        store = attrs.get('store') or getattr(self.instance, 'store', None)
        slug = attrs.get('slug') or getattr(self.instance, 'slug', None)
        if store and slug:
            qs = SpecialZone.objects.filter(store=store, slug=slug)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'slug': '同一店铺下专区标识已存在'})
        return attrs


class SpecialZoneProductSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
    )
    product = ProductSerializer(read_only=True)

    class Meta:
        model = SpecialZoneProduct
        fields = [
            'id',
            'zone',
            'product',
            'product_id',
            'is_active',
            'order',
            'created_at',
        ]
        read_only_fields = ['id', 'zone', 'product', 'created_at']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        zone = self.context.get('zone') or attrs.get('zone') or getattr(self.instance, 'zone', None)
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        if (
            zone
            and product
            and zone.kind != SpecialZone.KIND_PLATFORM_ACTIVITY
            and zone.store_id != product.store_id
        ):
            raise serializers.ValidationError({'product_id': '专区商品必须属于同一店铺'})
        return attrs


class ActivitySummarySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = SpecialZone
        fields = ['id', 'store', 'store_name', 'title', 'kind', 'is_active']


class ProductActivitiesSerializer(serializers.Serializer):
    available = ActivitySummarySerializer(many=True, read_only=True)
    selected = ActivitySummarySerializer(many=True, read_only=True)
    can_edit = serializers.BooleanField(read_only=True)


class HomeStoreCardSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), source='store')
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_type = serializers.CharField(source='store.store_type', read_only=True)
    store_is_main = serializers.BooleanField(source='store.is_main', read_only=True)
    main_product_id = serializers.IntegerField(write_only=True)
    secondary_product_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    category_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    main_product = serializers.SerializerMethodField()
    secondary_products = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    has_inactive_products = serializers.SerializerMethodField()
    inactive_product_names = serializers.SerializerMethodField()

    class Meta:
        model = HomeStoreCard
        fields = [
            'id', 'store', 'store_id', 'store_name', 'store_type', 'store_is_main', 'title', 'subtitle', 'order', 'is_active',
            'main_product_id', 'secondary_product_ids', 'category_ids',
            'main_product', 'secondary_products', 'categories',
            'has_inactive_products', 'inactive_product_names', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'store', 'created_at', 'updated_at']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        store = attrs.get('store') or getattr(self.instance, 'store', None)
        main_product_id = attrs.get('main_product_id')
        secondary_product_ids = attrs.get('secondary_product_ids')
        category_ids = attrs.get('category_ids')
        if self.instance:
            if main_product_id is None:
                main = self.instance.card_products.filter(role=HomeStoreCardProduct.ROLE_MAIN).first()
                main_product_id = main.product_id if main else None
            if secondary_product_ids is None:
                secondary_product_ids = list(self.instance.card_products.filter(role=HomeStoreCardProduct.ROLE_SECONDARY).values_list('product_id', flat=True))
            if category_ids is None:
                category_ids = list(self.instance.card_categories.values_list('category_id', flat=True))
        if not store:
            raise serializers.ValidationError({'store_id': '请选择店铺'})
        if not main_product_id:
            raise serializers.ValidationError({'main_product_id': '请选择 1 个主推商品'})
        if len(secondary_product_ids or []) != 4:
            raise serializers.ValidationError({'secondary_product_ids': '必须选择 4 个副推商品'})
        if len(category_ids or []) < 3:
            raise serializers.ValidationError({'category_ids': '至少选择 3 个一级分类'})
        product_ids = [main_product_id, *(secondary_product_ids or [])]
        if len(set(product_ids)) != 5:
            raise serializers.ValidationError({'secondary_product_ids': '主推和副推商品不能重复'})
        products = Product.objects.filter(id__in=product_ids)
        if products.count() != 5:
            raise serializers.ValidationError({'secondary_product_ids': '商品不存在或不完整'})
        if products.exclude(store=store).exists():
            raise serializers.ValidationError({'secondary_product_ids': '卡片商品必须属于绑定店铺'})
        categories = Category.objects.filter(id__in=category_ids or [])
        if categories.count() != len(set(category_ids or [])):
            raise serializers.ValidationError({'category_ids': '分类不存在或不完整'})
        if categories.exclude(store=store).exists():
            raise serializers.ValidationError({'category_ids': '卡片分类必须属于绑定店铺'})
        if categories.exclude(level=Category.LEVEL_MAJOR).exists():
            raise serializers.ValidationError({'category_ids': '卡片分类必须是一级分类'})
        invalid_category_ids = [
            category.id
            for category in categories
            if not Product.objects.filter(store=store, is_active=True).filter(
                Q(category=category) | Q(category__parent=category) | Q(category__parent__parent=category)
            ).exists()
        ]
        if invalid_category_ids:
            raise serializers.ValidationError({'category_ids': '所选一级分类下必须存在上架商品'})
        return attrs

    def create(self, validated_data):
        main_product_id = validated_data.pop('main_product_id')
        secondary_product_ids = validated_data.pop('secondary_product_ids')
        category_ids = validated_data.pop('category_ids')
        card = HomeStoreCard.objects.create(**validated_data)
        self._replace_children(card, main_product_id, secondary_product_ids, category_ids)
        return card

    def update(self, instance, validated_data):
        main_product_id = validated_data.pop('main_product_id', None)
        secondary_product_ids = validated_data.pop('secondary_product_ids', None)
        category_ids = validated_data.pop('category_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if main_product_id is not None or secondary_product_ids is not None or category_ids is not None:
            main_product_id = main_product_id or instance.card_products.get(role=HomeStoreCardProduct.ROLE_MAIN).product_id
            if secondary_product_ids is None:
                secondary_product_ids = list(instance.card_products.filter(role=HomeStoreCardProduct.ROLE_SECONDARY).values_list('product_id', flat=True))
            if category_ids is None:
                category_ids = list(instance.card_categories.values_list('category_id', flat=True))
            self._replace_children(instance, main_product_id, secondary_product_ids, category_ids)
        return instance

    def _replace_children(self, card, main_product_id, secondary_product_ids, category_ids):
        card.card_products.all().delete()
        card.card_categories.all().delete()
        HomeStoreCardProduct.objects.create(card=card, product_id=main_product_id, role=HomeStoreCardProduct.ROLE_MAIN, order=0)
        for index, product_id in enumerate(secondary_product_ids, start=1):
            HomeStoreCardProduct.objects.create(card=card, product_id=product_id, role=HomeStoreCardProduct.ROLE_SECONDARY, order=index)
        for index, category_id in enumerate(category_ids):
            HomeStoreCardCategory.objects.create(card=card, category_id=category_id, order=index)

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_main_product(self, obj):
        link = obj.card_products.filter(role=HomeStoreCardProduct.ROLE_MAIN).select_related('product').first()
        return ProductSerializer(link.product, context=self.context).data if link else None

    @extend_schema_field(ProductSerializer(many=True))
    def get_secondary_products(self, obj):
        products = [link.product for link in obj.card_products.filter(role=HomeStoreCardProduct.ROLE_SECONDARY).select_related('product').order_by('order', 'id')]
        return ProductSerializer(products, many=True, context=self.context).data

    @extend_schema_field(CategorySerializer(many=True))
    def get_categories(self, obj):
        categories = [link.category for link in obj.card_categories.select_related('category').order_by('order', 'id')]
        return CategorySerializer(categories, many=True, context=self.context).data

    def _card_products(self, obj):
        return [link.product for link in obj.card_products.select_related('product')]

    @extend_schema_field(serializers.BooleanField())
    def get_has_inactive_products(self, obj):
        return any(not product.is_active for product in self._card_products(obj))

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_inactive_product_names(self, obj):
        return [product.name for product in self._card_products(obj) if not product.is_active]


class HomeBannerSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        source='store',
        required=False,
    )
    image_id = serializers.IntegerField(source='image.id', read_only=True)
    image_url = serializers.SerializerMethodField()
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        allow_null=True,
        required=False
    )
    product_name = serializers.CharField(source='product.name', read_only=True, default='')
    special_zone_id = serializers.PrimaryKeyRelatedField(
        queryset=SpecialZone.objects.all(),
        source='special_zone',
        allow_null=True,
        required=False,
    )

    class Meta:
        model = HomeBanner
        fields = [
            'id', 'title', 'position', 'order', 'is_active',
            'store', 'store_id',
            'special_zone', 'special_zone_id',
            'product_id', 'product_name',
            'image_id', 'image_url', 'created_at', 'updated_at', 'image'
        ]
        read_only_fields = ['id', 'store', 'special_zone', 'created_at', 'updated_at', 'image_id', 'image_url', 'product_name']

    @extend_schema_field(serializers.CharField())
    def get_image_url(self, obj: HomeBanner):
        return _build_media_file_url(obj.image.file if obj.image else None, self.context.get('request'))

    def validate(self, attrs):
        attrs = super().validate(attrs)
        store = attrs.get('store') or getattr(self.instance, 'store', None)
        special_zone = attrs.get('special_zone') or getattr(self.instance, 'special_zone', None)
        if store and special_zone and special_zone.store_id != store.id:
            raise serializers.ValidationError({'special_zone_id': '专区轮播图必须属于同一店铺'})
        return attrs


class SpecialZoneCoverSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        source='store',
        required=False,
    )
    image_id = serializers.IntegerField(source='image.id', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = SpecialZoneCover
        fields = [
            'id', 'store', 'store_id', 'type', 'is_active', 'image_id', 'image_url', 'created_at', 'updated_at', 'image'
        ]
        read_only_fields = ['id', 'store', 'created_at', 'updated_at', 'image_id', 'image_url']
        validators = []

    @extend_schema_field(serializers.CharField())
    def get_image_url(self, obj: SpecialZoneCover):
        return _build_media_file_url(obj.image.file if obj.image else None, self.context.get('request'))


class CaseDetailBlockSerializer(serializers.ModelSerializer):
    image_id = serializers.PrimaryKeyRelatedField(
        queryset=MediaImage.objects.all(),
        source='image',
        allow_null=True,
        required=False
    )
    image_url = serializers.SerializerMethodField()
    id = serializers.IntegerField(required=False)

    class Meta:
        model = CaseDetailBlock
        fields = [
            'id',
            'block_type',
            'text',
            'order',
            'image_id',
            'image_url',
        ]
        read_only_fields = ['image_url']

    @extend_schema_field(serializers.CharField())
    def get_image_url(self, obj: CaseDetailBlock):
        return _build_media_file_url(obj.image.file if obj.image else None, self.context.get('request'))


class CaseSerializer(serializers.ModelSerializer):
    cover_image_id = serializers.PrimaryKeyRelatedField(
        queryset=MediaImage.objects.all(),
        source='cover_image'
    )
    cover_image_url = serializers.SerializerMethodField()
    detail_blocks = CaseDetailBlockSerializer(many=True, required=False)

    class Meta:
        model = Case
        fields = [
            'id',
            'title',
            'order',
            'is_active',
            'cover_image_id',
            'cover_image_url',
            'detail_blocks',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'cover_image_url']

    @extend_schema_field(serializers.CharField())
    def get_cover_image_url(self, obj: Case):
        return _build_media_file_url(obj.cover_image.file if obj.cover_image else None, self.context.get('request'))

    def create(self, validated_data):
        blocks_data = validated_data.pop('detail_blocks', [])
        case = Case.objects.create(**validated_data)
        
        for block_data in blocks_data:
            CaseDetailBlock.objects.create(case=case, **block_data)
        
        return case

    def update(self, instance, validated_data):
        blocks_data = validated_data.pop('detail_blocks', None)
        
        # Update Case fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update Blocks
        if blocks_data is not None:
            # 简单策略：全量删除重建
            # 如果需要保留ID，逻辑会复杂很多，考虑到CaseBlock结构简单，重建是可接受的
            instance.detail_blocks.all().delete()
            for block_data in blocks_data:
                # 移除可能存在的 id 字段（如果是从前端传回来的）
                if 'id' in block_data:
                    del block_data['id']
                CaseDetailBlock.objects.create(case=instance, **block_data)
                
        return instance


class InventoryLogSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    sku_name = serializers.CharField(source='sku.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    change_type_display = serializers.CharField(source='get_change_type_display', read_only=True)

    class Meta:
        model = InventoryLog
        fields = [
            'id',
            'product',
            'product_name',
            'sku',
            'sku_name',
            'change_type',
            'change_type_display',
            'quantity',
            'reason',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = fields
