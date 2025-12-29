from rest_framework import serializers
from .models import Category, Brand, Product, ProductSKU, MediaImage, SearchLog, HomeBanner, Case, CaseDetailBlock
from orders.models import DiscountTarget
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from common.serializers import (
    SecureCharField,
    ImageFileValidator,
    PriceField,
    StockField,
)


class CategorySerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='parent',
        allow_null=True,
        required=False
    )
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "order", "logo", "level", "parent_id", "children"]
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
                'parent_id': obj.id,
            }
            for c in qs
        ]

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
            qs = Category.objects.filter(level=level, name=name, parent=parent)
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
    
    class Meta:
        model = Brand
        fields = ["id", "name", "logo", "description", "order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def validate_name(self, value):
        """Validate brand name is not empty after stripping."""
        if not value or not value.strip():
            raise serializers.ValidationError("品牌名称不能为空")
        return value


class ProductSKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSKU
        fields = [
            'id',
            'name',
            'sku_code',
            'specs',
            'price',
            'stock',
            'image',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    # 读：显示名称和ID；写：通过 *_id 设置关联
    category = serializers.StringRelatedField(read_only=True)
    brand = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category')
    brand_id = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), source='brand')
    discounted_price = serializers.SerializerMethodField()
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
            'originalPrice',
            'category_id',
            'brand_id',
            'is_haier_product',
            'haier_info',
            'skus',
            'spec_options',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync_at', 'view_count', 'sales_count']

    def validate_main_images(self, value):
        return self._normalize_images(value)
    
    def validate_detail_images(self, value):
        return self._normalize_images(value)
    
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
                return f"{path}{suffix}"
        if url.startswith('/'):
            return url
        media_prefix = settings.MEDIA_URL.rstrip('/')
        return f"{media_prefix}/{url.lstrip('/')}"

    def to_representation(self, instance):
        """自定义序列化输出，将图片URL转换为完整URL"""
        rep = super().to_representation(instance)
        # 合并额外字段
        rep['discounted_price'] = self.get_discounted_price(instance)
        rep['originalPrice'] = self.get_originalPrice(instance)
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
        
        return rep
    
    def validate(self, attrs):
        category = attrs.get('category')
        if category is None and self.instance is not None:
            category = getattr(self.instance, 'category', None)
        if category and getattr(category, 'level', None) not in {Category.LEVEL_MINOR, Category.LEVEL_ITEM}:
            raise serializers.ValidationError({'category_id': '商品必须关联到子品类或品项'})
        return attrs

    def _get_full_image_urls(self, images):
        """将图片URL转换为完整URL"""
        if not images:
            return []
        
        request = self.context.get('request')
        result = []
        
        for img_url in images:
            if not img_url:
                continue
            if img_url.startswith('http://') or img_url.startswith('https://'):
                # 已经是完整URL
                result.append(img_url)
            elif request:
                # 构建完整URL
                result.append(request.build_absolute_uri(img_url))
            else:
                result.append(img_url)
        
        return result
    
    def get_is_haier_product(self, obj: Product):
        """判断是否为海尔产品"""
        # 只根据 source 字段判断
        return getattr(obj, 'source', None) == getattr(obj, 'SOURCE_HAIER', 'haier')
    
    def get_haier_info(self, obj: Product):
        """获取海尔产品信息"""
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

    def get_originalPrice(self, obj: Product):
        """获取原价（市场价或普通价格）"""
        if obj.market_price:
            return obj.market_price
        return obj.price

    def get_discounted_price(self, obj: Product):
        """获取折扣价"""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        
        # 使用display_price作为基础价格
        base_price = obj.display_price if hasattr(obj, 'display_price') else obj.price
        
        if not user or not user.is_authenticated:
            return base_price
        
        # simple cache to reduce DB queries during listing/search
        cache_key = f"discount:{user.id}:{obj.id}"
        amount = cache.get(cache_key)
        if amount is None:
            now = timezone.now()
            dt = (
                DiscountTarget.objects.select_related('discount')
                .filter(
                    user=user,
                    product=obj,
                    discount__effective_time__lte=now,
                    discount__expiration_time__gt=now,
                )
                .order_by('-discount__priority', '-discount__updated_at')
                .first()
            )
            if not dt:
                return base_price
            amount = dt.discount.amount
            if amount < 0:
                amount = 0
            if amount > base_price:
                amount = base_price
            cache.set(cache_key, amount, 60)
        if amount < 0:
            amount = 0
        if amount > base_price:
            amount = base_price
        return base_price - amount

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

    def get_url(self, obj: MediaImage):
        """
        Get the absolute URL for the media image.
        
        Args:
            obj (MediaImage): The MediaImage instance
            
        Returns:
            str: Absolute URL to the image file
        """
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url
    
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


class HomeBannerSerializer(serializers.ModelSerializer):
    image_id = serializers.IntegerField(source='image.id', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = HomeBanner
        fields = [
            'id', 'title', 'link_url', 'position', 'order', 'is_active',
            'image_id', 'image_url', 'created_at', 'updated_at', 'image'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'image_id', 'image_url']

    def get_image_url(self, obj: HomeBanner):
        request = self.context.get('request')
        url = obj.image.file.url if obj.image and obj.image.file else ''
        if not url:
            return ''
        return request.build_absolute_uri(url) if request else url


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

    def get_image_url(self, obj: CaseDetailBlock):
        request = self.context.get('request')
        url = obj.image.file.url if obj.image and obj.image.file else ''
        if not url:
            return ''
        return request.build_absolute_uri(url) if request else url


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

    def get_cover_image_url(self, obj: Case):
        request = self.context.get('request')
        url = obj.cover_image.file.url if obj.cover_image and obj.cover_image.file else ''
        if not url:
            return ''
        return request.build_absolute_uri(url) if request else url

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
