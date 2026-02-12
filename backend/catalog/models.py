from django.db import models
from django.core.validators import MinValueValidator

# Create your models here.
class Category(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='类别名称', default='默认分类')
    order = models.IntegerField(default=0, verbose_name='排序')
    logo = models.URLField(max_length=500, blank=True, default='', verbose_name='分类Logo')

    LEVEL_MAJOR = 'major'
    LEVEL_MINOR = 'minor'
    LEVEL_ITEM = 'item'
    LEVEL_CHOICES = [
        (LEVEL_MAJOR, '品类'),
        (LEVEL_MINOR, '子品类'),
        (LEVEL_ITEM, '品项'),
    ]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_MAJOR, verbose_name='层级')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children', verbose_name='父类别')

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '商品类别'
        verbose_name_plural = '商品类别'
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'parent', 'name'],
                name='unique_category_level_parent_name',
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.name is not None:
            self.name = str(self.name).strip()
        from django.core.exceptions import ValidationError

        if self.level and self.name:
            if self.parent_id is None:
                exists = Category.objects.filter(
                    level=self.level,
                    parent__isnull=True,
                    name=self.name,
                ).exclude(pk=self.pk).exists()
                if exists:
                    raise ValidationError({'name': '同层级根分类名称已存在'})
            else:
                exists = Category.objects.filter(
                    level=self.level,
                    parent_id=self.parent_id,
                    name=self.name,
                ).exclude(pk=self.pk).exists()
                if exists:
                    raise ValidationError({'name': '同父分类下名称已存在'})
        # 品类（大类）不能有父类别
        if self.level == self.LEVEL_MAJOR and self.parent is not None:
            raise ValidationError({'parent': '品类不允许设置父类别'})
        # 子品类（小类）必须有父类别，且父类别必须是品类（大类）
        if self.level == self.LEVEL_MINOR:
            if self.parent is None:
                raise ValidationError({'parent': '子品类必须设置父类别'})
            if getattr(self.parent, 'level', None) != self.LEVEL_MAJOR:
                raise ValidationError({'parent': '子品类的父类别必须是品类'})
        # 品项必须有父类别，且父类别必须是子品类
        if self.level == self.LEVEL_ITEM:
            if self.parent is None:
                raise ValidationError({'parent': '品项必须设置父类别'})
            if getattr(self.parent, 'level', None) != self.LEVEL_MINOR:
                raise ValidationError({'parent': '品项的父类别必须是子品类'})

    def save(self, *args, **kwargs):
        # 确保模型校验执行
        self.full_clean()
        super().save(*args, **kwargs)


class Brand(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, verbose_name='品牌名称')
    logo = models.URLField(max_length=500, blank=True, default='', verbose_name='品牌Logo')
    description = models.TextField(blank=True, default='', verbose_name='品牌描述')
    order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '品牌'
        verbose_name_plural = '品牌'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['is_active', 'order']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name='产品名称')
    description = models.TextField(blank=True, default='', verbose_name='产品描述')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name='类别')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products', verbose_name='品牌')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='价格')
    dealer_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True, verbose_name='经销价')
    
    # 商品来源（用于区分本地商品 / 海尔商品等）
    SOURCE_LOCAL = 'local'
    SOURCE_HAIER = 'haier'
    SOURCE_CHOICES = [
        (SOURCE_LOCAL, '本地商品'),
        (SOURCE_HAIER, '海尔商品'),
    ]
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_LOCAL,
        verbose_name='商品来源',
        help_text='local=本地维护商品; haier=来自海尔API的商品',
    )

    # 商品标签
    TAG_BRAND_DIRECT = 'brand_direct'
    TAG_SOURCE_FACTORY = 'source_factory'
    TAG_CHOICES = [
        ('', '无标签'),
        (TAG_BRAND_DIRECT, '品牌直发'),
        (TAG_SOURCE_FACTORY, '源头厂家'),
    ]
    tag = models.CharField(
        max_length=20,
        choices=TAG_CHOICES,
        default='',
        blank=True,
        verbose_name='商品标签'
    )

    stock = models.PositiveIntegerField(default=0, verbose_name='库存数量')
    
    # 海尔API相关字段
    product_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name='海尔产品编码')
    product_model = models.CharField(max_length=100, blank=True, default='', verbose_name='海尔产品型号')
    product_group = models.CharField(max_length=100, blank=True, default='', verbose_name='海尔产品组')
    
    # 价格相关字段（海尔API）
    supply_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='普通供价')
    invoice_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='开票价')
    market_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='市场价')
    stock_rebate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='直扣')
    rebate_money = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='台返')
    
    # 图片字段 - 存储图片URL列表
    main_images = models.JSONField(default=list, blank=True, verbose_name='主图列表')
    detail_images = models.JSONField(default=list, blank=True, verbose_name='详情图列表')
    product_image_url = models.URLField(max_length=500, blank=True, default='', verbose_name='海尔主图URL')
    product_page_urls = models.JSONField(default=list, blank=True, verbose_name='海尔拉页URL列表')
    
    # 状态和统计字段
    is_active = models.BooleanField(default=True, verbose_name='是否上架')
    show_in_gift_zone = models.BooleanField(default=False, verbose_name='礼品专区展示')
    show_in_designer_zone = models.BooleanField(default=False, verbose_name='设计师专区展示')
    is_sales = models.CharField(max_length=1, default='1', verbose_name='海尔是否可采(1可采,0不可采)')
    no_sales_reason = models.CharField(max_length=200, blank=True, default='', verbose_name='不可采原因')
    view_count = models.PositiveIntegerField(default=0, verbose_name='浏览次数')
    sales_count = models.PositiveIntegerField(default=0, verbose_name='销售数量')
    
    # 库存信息（海尔API）
    warehouse_code = models.CharField(max_length=50, blank=True, default='', verbose_name='库位编码')
    warehouse_grade = models.CharField(max_length=1, blank=True, default='', verbose_name='仓库等级(0本级仓/1上级仓)')
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='更新时间')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='最后同步时间')

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-sales_count']),
            models.Index(fields=['is_active', '-view_count']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['product_code']),
            models.Index(fields=['is_sales']),
            models.Index(fields=['show_in_gift_zone', 'is_active']),
            models.Index(fields=['show_in_designer_zone', 'is_active']),
        ]

    def __str__(self):
        return self.name
    
    def clean(self):
        # 兼容旧数据：允许关联到小类或品项；新数据推荐关联到品项
        from django.core.exceptions import ValidationError
        if self.category and getattr(self.category, 'level', None) not in {Category.LEVEL_MINOR, Category.LEVEL_ITEM}:
            raise ValidationError({'category': '商品必须关联到子品类或品项'})

    @classmethod
    def sync_from_haier(cls, haier_data: dict, category=None, brand=None):
        """
        从海尔API数据同步商品
        
        Args:
            haier_data: 海尔API返回的商品数据
            category: 商品分类对象
            brand: 品牌对象
        
        Returns:
            Product: 商品对象
        """
        from django.utils import timezone
        
        product_code = haier_data.get('productCode')
        if not product_code:
            return None
        
        # 获取或创建商品
        product, created = cls.objects.get_or_create(
            product_code=product_code,
            defaults={
                'name': haier_data.get('productModel', product_code),
                'category': category or Category.objects.first(),
                'brand': brand or Brand.objects.first(),
                'price': 0,
                'source': cls.SOURCE_HAIER,
            }
        )
        
        # 更新商品信息
        product.product_model = haier_data.get('productModel', '')
        product.product_group = haier_data.get('productGroupNamd', '')
        product.product_image_url = haier_data.get('productImageUrl', '')
        product.product_page_urls = haier_data.get('productLageUrls', [])
        product.is_sales = haier_data.get('isSales', '1')
        product.no_sales_reason = haier_data.get('noSalesReason', '')
        
        # 更新价格信息（如果有）
        if 'supplyPrice' in haier_data:
            product.supply_price = haier_data.get('supplyPrice')
        # 海尔返回的市场价（用于商户对外售价的参考）
        if 'marketPrice' in haier_data:
            product.market_price = haier_data.get('marketPrice')
        if 'invoicePrice' in haier_data:
            product.invoice_price = haier_data.get('invoicePrice')
        if 'stockRebatePolicy' in haier_data:
            product.stock_rebate = haier_data.get('stockRebatePolicy')
        if 'rebateMoney' in haier_data:
            product.rebate_money = haier_data.get('rebateMoney')

        # 商户对外售价：优先使用市场价；否则初始为供价（后续可由商户调整）
        try:
            if product.price in (None, 0):
                base_sale_price = product.market_price or product.supply_price or 0
                product.price = base_sale_price
        except Exception:
            # 兼容旧数据类型
            base_sale_price = product.market_price or product.supply_price or 0
            product.price = base_sale_price
        
        # 更新品牌（如果海尔数据中有）
        if haier_data.get('productBrandName') and not brand:
            brand_name = haier_data.get('productBrandName')
            brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
            product.brand = brand_obj
        
        # 确保来源标记为海尔商品（兼容旧数据）
        product.source = cls.SOURCE_HAIER
        product.last_sync_at = timezone.now()
        product.save()
        
        return product
    
    def update_stock_from_haier(self, stock_data: dict):
        """
        从海尔API更新库存信息
        
        Args:
            stock_data: 海尔库存API返回的数据
        """
        from django.utils import timezone
        
        self.stock = int(stock_data.get('stock', 0))
        self.warehouse_code = stock_data.get('secCode', '')
        self.warehouse_grade = stock_data.get('warehouseGrade', '')
        self.last_sync_at = timezone.now()
        self.save()
    
    @property
    def display_price(self):
        """基础售价（不包含用户态折扣/经销逻辑）"""
        return self.price
    
    @property
    def is_available_from_haier(self):
        """是否从海尔可采"""
        return self.is_sales == '1'


class ProductSKU(models.Model):
    """商品SKU，用于管理规格、价格与库存"""
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='skus', verbose_name='商品')
    name = models.CharField(max_length=200, blank=True, default='', verbose_name='SKU名称')
    sku_code = models.CharField(max_length=100, blank=True, default='', verbose_name='SKU编码')
    specs = models.JSONField(default=dict, blank=True, verbose_name='规格参数')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='售价')
    stock = models.PositiveIntegerField(default=0, verbose_name='库存')
    image = models.URLField(max_length=500, blank=True, default='', verbose_name='SKU主图')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '商品SKU'
        verbose_name_plural = '商品SKU'
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku_code']),
        ]
        unique_together = [('product', 'sku_code')]

    def __str__(self):
        return self.name or self.sku_code or f'SKU#{self.id}'

    @property
    def specs_text(self):
        if not self.specs:
            return ''
        return ' / '.join([f'{k}:{v}' for k, v in self.specs.items()])


class MediaImage(models.Model):
    """
    媒体图片模型
    
    用于存储上传的图片文件，支持安全的文件管理。
    """
    id = models.BigAutoField(primary_key=True)
    file = models.FileField(upload_to='images/', verbose_name='文件')
    original_name = models.CharField(max_length=255, blank=True, default='', verbose_name='原始文件名')
    content_type = models.CharField(max_length=100, blank=True, default='', verbose_name='内容类型')
    size = models.PositiveIntegerField(default=0, verbose_name='文件大小(字节)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '媒体图片'
        verbose_name_plural = '媒体图片'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'{self.original_name} ({self.id})'


class HomeBanner(models.Model):
    """
    首页轮播图
    
    通过关联已上传的媒体图片来管理首页展示的轮播图。
    """
    POSITION_HOME = 'home'
    POSITION_GIFT = 'gift'
    POSITION_DESIGNER = 'designer'
    POSITION_CHOICES = [
        (POSITION_HOME, '首页'),
        (POSITION_GIFT, '礼品专区'),
        (POSITION_DESIGNER, '设计师专区'),
    ]

    id = models.BigAutoField(primary_key=True)
    image = models.ForeignKey(
        'catalog.MediaImage',
        on_delete=models.PROTECT,
        related_name='banners',
        verbose_name='图片'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.SET_NULL,
        related_name='home_banners',
        null=True,
        blank=True,
        verbose_name='跳转商品'
    )
    title = models.CharField(max_length=100, blank=True, default='', verbose_name='标题')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default=POSITION_HOME, verbose_name='展示位置')
    order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '首页轮播图'
        verbose_name_plural = '首页轮播图'
        ordering = ['order', '-id']
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['position', 'is_active', 'order']),
        ]

    def __str__(self):
        return self.title or f'Banner {self.id}'


class SpecialZoneCover(models.Model):
    TYPE_GIFT = 'gift'
    TYPE_DESIGNER = 'designer'
    TYPE_CHOICES = [
        (TYPE_GIFT, '礼品专区'),
        (TYPE_DESIGNER, '设计师专区'),
    ]

    id = models.BigAutoField(primary_key=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_GIFT, unique=True, verbose_name='专区类型')
    image = models.ForeignKey(
        'catalog.MediaImage',
        on_delete=models.PROTECT,
        related_name='special_zone_covers',
        verbose_name='图片'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '首页专区图片'
        verbose_name_plural = '首页专区图片'
        ordering = ['type']
        indexes = [
            models.Index(fields=['type', 'is_active']),
        ]

    def __str__(self):
        return self.get_type_display() or f'ZoneCover {self.id}'


class Case(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200, verbose_name='标题')
    cover_image = models.ForeignKey(
        'catalog.MediaImage',
        on_delete=models.PROTECT,
        related_name='cases_as_cover',
        verbose_name='展示图',
    )
    order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '案例'
        verbose_name_plural = '案例'
        ordering = ['order', '-id']
        indexes = [
            models.Index(fields=['is_active', 'order']),
        ]

    def __str__(self):
        return self.title


class CaseDetailBlock(models.Model):
    TYPE_TEXT = 'text'
    TYPE_IMAGE = 'image'
    TYPE_CHOICES = [
        (TYPE_TEXT, '文本'),
        (TYPE_IMAGE, '图片'),
    ]

    id = models.BigAutoField(primary_key=True)
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='detail_blocks',
        verbose_name='案例',
    )
    block_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXT, verbose_name='类型')
    text = models.TextField(blank=True, default='', verbose_name='文本内容')
    image = models.ForeignKey(
        'catalog.MediaImage',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='case_detail_blocks',
        verbose_name='图片',
    )
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '案例详情块'
        verbose_name_plural = '案例详情块'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['case', 'order', 'id']),
        ]

    def __str__(self):
        return f'{self.case_id}#{self.id}:{self.block_type}'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.block_type == self.TYPE_TEXT:
            if not (self.text or '').strip():
                raise ValidationError({'text': '文本块必须填写文本内容'})
            if self.image_id:
                raise ValidationError({'image': '文本块不允许设置图片'})
        if self.block_type == self.TYPE_IMAGE:
            if not self.image_id:
                raise ValidationError({'image': '图片块必须选择图片'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SearchLog(models.Model):
    """
    搜索日志模型
    
    记录用户的搜索行为，用于分析热门关键词和搜索趋势。
    """
    id = models.BigAutoField(primary_key=True)
    keyword = models.CharField(max_length=200, verbose_name='搜索关键词')
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_logs',
        verbose_name='用户'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='搜索时间')

    class Meta:
        verbose_name = '搜索日志'
        verbose_name_plural = '搜索日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['keyword', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'{self.keyword} - {self.created_at}'





class InventoryLog(models.Model):
    """
    库存日志模型
    
    记录商品库存的所有变更操作，用于审计和追踪。
    """
    CHANGE_TYPE_CHOICES = [
        ('lock', '锁定'),
        ('release', '释放'),
        ('adjust', '调整'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='inventory_logs',
        verbose_name='商品'
    )
    sku = models.ForeignKey(
        'catalog.ProductSKU',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventory_logs',
        verbose_name='SKU'
    )
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        verbose_name='变更类型'
    )
    quantity = models.IntegerField(verbose_name='变更数量')
    reason = models.CharField(max_length=100, verbose_name='变更原因')
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='操作人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '库存日志'
        verbose_name_plural = '库存日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['sku', 'created_at']),
            models.Index(fields=['change_type']),
        ]

    def __str__(self):
        base = self.product.name
        if self.sku_id:
            base = f'{base} ({self.sku})'
        return f'{base} - {self.get_change_type_display()} - {self.quantity}'
