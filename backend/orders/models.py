import time
import random
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from stores.models import get_main_store_pk

# Create your models here.
def generate_order_number():
    return f"{int(time.time())}{random.randint(100000, 999999)}"


class CheckoutOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('cancelled', '已取消'),
        ('refunding', '退款中'),
        ('refunded', '已退款'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('init', '待支付'),
        ('processing', '支付中'),
        ('succeeded', '支付成功'),
        ('failed', '支付失败'),
        ('cancelled', '已取消'),
        ('expired', '已过期'),
    ]

    id = models.BigAutoField(primary_key=True)
    checkout_number = models.CharField(max_length=100, unique=True, default=generate_order_number, verbose_name='结算单号')
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='checkout_orders', verbose_name='用户')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='结算状态')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='init', verbose_name='支付状态')
    payment_number = models.CharField(max_length=100, blank=True, default='', verbose_name='支付单号')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总金额')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='实付金额')
    snapshot_contact_name = models.CharField(max_length=50, default='', verbose_name='联系人')
    snapshot_phone = models.CharField(max_length=20, default='', verbose_name='手机号')
    snapshot_address = models.TextField(default='', verbose_name='收货地址')
    snapshot_province = models.CharField(max_length=50, blank=True, default='', verbose_name='省', db_index=True)
    snapshot_city = models.CharField(max_length=50, blank=True, default='', verbose_name='市', db_index=True)
    snapshot_district = models.CharField(max_length=50, blank=True, default='', verbose_name='区', db_index=True)
    snapshot_town = models.CharField(max_length=50, blank=True, default='', verbose_name='县/街道', db_index=True)
    note = models.TextField(blank=True, default='', verbose_name='用户备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '结算单'
        verbose_name_plural = '结算单'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return self.checkout_number


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '待发货'),
        ('shipped', '待收货'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('returning', '退货中'),
        ('refunding', '退款中'),
        ('refunded', '已退款'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='订单状态')

    id = models.BigAutoField(primary_key=True)
    order_number = models.CharField(max_length=100, unique=True,default=generate_order_number,verbose_name='订单号')
    store = models.ForeignKey('stores.Store', on_delete=models.PROTECT, related_name='orders', default=get_main_store_pk, verbose_name='店铺')
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='orders', verbose_name='用户')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, null=True, blank=True, related_name='orders', verbose_name='产品')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总金额')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='实付金额')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    snapshot_contact_name = models.CharField(max_length=50,default='',verbose_name="联系人")
    snapshot_phone = models.CharField(max_length=20,default='',verbose_name="手机号")
    snapshot_address = models.TextField(default='',verbose_name="收货地址")
    snapshot_province = models.CharField(max_length=50, blank=True, default='', verbose_name='省', db_index=True)
    snapshot_city = models.CharField(max_length=50, blank=True, default='', verbose_name='市', db_index=True)
    snapshot_district = models.CharField(max_length=50, blank=True, default='', verbose_name='区', db_index=True)
    snapshot_town = models.CharField(max_length=50, blank=True, default='', verbose_name='县/街道', db_index=True)
    
    # 海尔订单相关字段
    haier_order_no = models.CharField(max_length=100, blank=True, default='', verbose_name='海尔订单号')
    haier_so_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='海尔子订单号')
    haier_status = models.CharField(max_length=20, blank=True, default='', verbose_name='海尔订单状态')
    haier_fail_msg = models.TextField(blank=True, default='', verbose_name='海尔失败信息')
    
    # 配送安装信息
    distribution_time = models.DateTimeField(null=True, blank=True, verbose_name='配送时间')
    install_time = models.DateTimeField(null=True, blank=True, verbose_name='安装时间')
    is_delivery_install = models.BooleanField(default=False, verbose_name='是否送装一体')
    is_government_order = models.BooleanField(default=False, verbose_name='是否国补订单')
    
    # 物流信息
    logistics_no = models.CharField(max_length=100, blank=True, default='', verbose_name='物流单号')
    delivery_record_code = models.CharField(max_length=100, blank=True, default='', verbose_name='发货单号')
    sn_code = models.CharField(max_length=100, blank=True, default='', verbose_name='SN码')
    shipping_info = models.JSONField(default=dict, blank=True, verbose_name='发货信息')
    
    # 配送安装照片
    delivery_images = models.JSONField(default=list, blank=True, verbose_name='配送安装照片')
    
    # New fields
    note = models.TextField(blank=True, default='', verbose_name='用户备注')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 取消信息
    cancel_reason = models.CharField(max_length=200, blank=True, default='', verbose_name='取消原因')
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='取消时间')

    # 父子订单关系（用于海尔 + 本地混合订单拆分）
    ORDER_TYPE_CHOICES = [
        ('main', '主订单'),
        ('haier', '海尔子订单'),
        ('local', '本地子订单'),
    ]
    parent_order = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='child_orders',
        verbose_name='主订单'
    )
    checkout_order = models.ForeignKey(
        'orders.CheckoutOrder',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='结算单'
    )
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='main',
        verbose_name='订单类型'
    )

    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['store', 'status']),
            models.Index(fields=['haier_order_no']),
            models.Index(fields=['haier_so_id']),
            models.Index(fields=['parent_order']),
            models.Index(fields=['checkout_order']),
            models.Index(fields=['order_type']),
        ]

    def __str__(self):
        return self.order_number

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.product_id and self.product.store_id != self.store_id:
            raise ValidationError({'product': '订单商品必须属于同一店铺'})
    
    @property
    def primary_item(self):
        return self.items.first()
    
    @property
    def primary_product(self):
        item = self.primary_item
        return item.product if item else self.product
    
    @property
    def total_quantity(self):
        if hasattr(self, '_prefetched_objects_cache') and 'items' in self._prefetched_objects_cache:
            return sum(item.quantity for item in self.items.all())
        return self.items.aggregate(total=models.Sum('quantity')).get('total') or self.quantity
    
    def prepare_haier_order_data(self, source_system=None, shop_name=None):
        """
        准备推送到海尔的订单数据
        
        Args:
            source_system: 订单来源系统标识（已统一使用 settings.YLH_SOURCE_SYSTEM）
            shop_name: 店铺名称（已统一使用 settings.YLH_SHOP_NAME）
        
        Returns:
            dict: 海尔订单数据格式
        """
        item_list = []
        total_qty = 0
        for item in self.items.select_related('product', 'sku').all():
            product_code = ''
            if item.sku and item.sku.sku_code:
                product_code = item.sku.sku_code
            elif item.product and getattr(item.product, 'product_code', None):
                product_code = item.product.product_code
            item_list.append({
                'productCode': product_code,
                'itemQty': item.quantity,
                'retailPrice': float(item.unit_price),
                'discountAmount': float(item.discount_amount),
                'actualPrice': float(item.actual_amount),
                'isGift': False,
            })
            total_qty += item.quantity

        # 兼容旧数据：没有 order items 时回退到单商品逻辑
        if not item_list and self.product:
            item_list.append({
                'productCode': self.product.product_code,
                'itemQty': self.quantity,
                'retailPrice': float(self.product.market_price or self.product.price),
                'discountAmount': float(self.discount_amount),
                'actualPrice': float(self.actual_amount),
                'isGift': False,
            })
            total_qty = self.quantity

        source_system = settings.YLH_SOURCE_SYSTEM
        shop_name = settings.YLH_SHOP_NAME
        return {
            'sourceSystem': source_system,
            'shopName': shop_name,
            'sellerCode': settings.HAIER_CUSTOMER_CODE,
            'consigneeName': self.snapshot_contact_name,
            'consigneeMobile': self.snapshot_phone,
            'onlineNo': self.order_number,
            'soId': self.order_number,
            'remark': self.note,
            'totalQty': total_qty or self.quantity,
            'totalAmt': float(self.total_amount),
            'createTime': int(self.created_at.timestamp() * 1000),
            'province': self.snapshot_province,
            'city': self.snapshot_city,
            'area': self.snapshot_district,
            'town': self.snapshot_town,
            'detailAddress': self.snapshot_address,
            'distributionTime': int(self.distribution_time.timestamp() * 1000) if self.distribution_time else None,
            'installTime': int(self.install_time.timestamp() * 1000) if self.install_time else None,
            'governmentOrder': self.is_government_order,
            'deliveryInstall': str(self.is_delivery_install).lower(),
            'itemList': item_list
        }
    
    def update_from_haier_callback(self, callback_data: dict):
        """
        从海尔回调更新订单状态
        
        Args:
            callback_data: 海尔回调数据
        """
        from django.utils import timezone
        
        fail_msg = callback_data.get('FailMsg', '')
        if callback_data.get('State') == 1:  # 成功
            self.haier_order_no = callback_data.get('ExtOrderNo', '')
            self.haier_status = 'confirmed'
            self.haier_fail_msg = ''
        else:  # 失败
            self.haier_status = 'failed'
            self.haier_fail_msg = fail_msg
        
        self.updated_at = timezone.now()
        self.save()
    
    def update_logistics_info(self, logistics_data: dict):
        """
        更新物流信息
        
        Args:
            logistics_data: 物流信息数据
        """
        from django.utils import timezone
        
        self.logistics_no = logistics_data.get('logisticsNo', '')
        self.delivery_record_code = logistics_data.get('deliveryRecordCode', '')
        self.sn_code = logistics_data.get('snCode', '')
        self.updated_at = timezone.now()
        self.save()


class OrderItem(models.Model):
    """订单行项目"""
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='订单')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='order_items', verbose_name='产品')
    sku = models.ForeignKey('catalog.ProductSKU', on_delete=models.PROTECT, null=True, blank=True, related_name='order_items', verbose_name='SKU')
    product_name = models.CharField(max_length=200, verbose_name='商品名称')
    sku_specs = models.JSONField(default=dict, blank=True, verbose_name='规格信息')
    sku_code = models.CharField(max_length=100, blank=True, default='', verbose_name='SKU编码')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='单价')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='实付金额')
    snapshot_image = models.URLField(max_length=500, blank=True, default='', verbose_name='商品主图')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    # 海尔 4.2 回调状态字段（签收/退货/拒收数量）
    receive_qty = models.PositiveIntegerField(default=0, verbose_name='签收数量')
    return_qty = models.PositiveIntegerField(default=0, verbose_name='退货数量')
    reject_qty = models.PositiveIntegerField(default=0, verbose_name='拒收数量')

    class Meta:
        verbose_name = '订单商品'
        verbose_name_plural = '订单商品'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f'订单{self.order_id} - {self.product_name} x{self.quantity}'

    @property
    def specs_text(self):
        if not self.sku_specs:
            return ''
        return ' / '.join([f'{k}:{v}' for k, v in self.sku_specs.items()])


class SubOrder(models.Model):
    id = models.BigAutoField(primary_key=True)
    suborder_number = models.CharField(max_length=100, unique=True, default=generate_order_number, verbose_name='子单号')
    checkout_order = models.ForeignKey(CheckoutOrder, on_delete=models.PROTECT, related_name='suborders', verbose_name='结算单')
    legacy_order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='suborder_record', verbose_name='兼容订单')
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='suborders', verbose_name='用户')
    store = models.ForeignKey('stores.Store', on_delete=models.PROTECT, related_name='suborders', verbose_name='店铺')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='suborders', verbose_name='商品SPU')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, default='pending', verbose_name='子单状态')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总金额')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='实付金额')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '子单'
        verbose_name_plural = '子单'
        indexes = [
            models.Index(fields=['checkout_order']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['store', 'status']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return self.suborder_number


class SubOrderItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    suborder = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name='items', verbose_name='子单')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='suborder_items', verbose_name='产品')
    sku = models.ForeignKey('catalog.ProductSKU', on_delete=models.PROTECT, null=True, blank=True, related_name='suborder_items', verbose_name='SKU')
    product_name = models.CharField(max_length=200, verbose_name='商品名称')
    sku_specs = models.JSONField(default=dict, blank=True, verbose_name='规格信息')
    sku_code = models.CharField(max_length=100, blank=True, default='', verbose_name='SKU编码')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='单价')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='实付金额')
    snapshot_image = models.URLField(max_length=500, blank=True, default='', verbose_name='商品主图')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '子单商品'
        verbose_name_plural = '子单商品'
        indexes = [
            models.Index(fields=['suborder']),
            models.Index(fields=['product']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f'子单{self.suborder_id} - {self.product_name} x{self.quantity}'


class Cart(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='cart', verbose_name='用户')

    def __str__(self):
        return f'{self.user.username}的购物车'

    class Meta:
        verbose_name = "购物车"
        verbose_name_plural = "购物车"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.PROTECT, related_name='items', verbose_name='购物车')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='cart_items', verbose_name='产品')
    sku = models.ForeignKey('catalog.ProductSKU', on_delete=models.PROTECT, null=True, blank=True, related_name='cart_items', verbose_name='SKU')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')

    class Meta:
        verbose_name = "购物车项"
        verbose_name_plural = "购物车项"
        unique_together = ('cart', 'product', 'sku')


class Payment(models.Model):
    METHOD_CHOICES = [
        ('wechat', '微信支付'),
        ('alipay', '支付宝'),
        ('bank', '银行卡'),
    ]
    STATUS_CHOICES = [
        ('init', '待支付'),
        ('processing', '支付中'),
        ('succeeded', '支付成功'),
        ('failed', '支付失败'),
        ('cancelled', '已取消'),
        ('expired', '已过期'),
    ]
    PROFIT_SHARING_STATUS_CHOICES = [
        ('not_required', '无需分账'),
        ('pending', '待支付'),
        ('pending_receiver_config', '待配置接收方'),
        ('frozen', '冻结中'),
        ('available', '可分账'),
        ('processing', '分账处理中'),
        ('shared', '分账完成'),
        ('failed', '分账失败'),
        ('manual_settlement_required', '需人工结算'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='payments', verbose_name='订单')
    checkout_order = models.ForeignKey('orders.CheckoutOrder', on_delete=models.PROTECT, null=True, blank=True, related_name='payments', verbose_name='结算单')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='支付金额')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='wechat', verbose_name='支付方式')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='init', verbose_name='支付状态')
    profit_sharing_required = models.BooleanField(default=False, verbose_name='是否微信分账订单')
    profit_sharing_status = models.CharField(
        max_length=40,
        choices=PROFIT_SHARING_STATUS_CHOICES,
        default='not_required',
        verbose_name='分账状态',
    )
    profit_sharing_unfrozen = models.BooleanField(default=False, verbose_name='分账剩余资金已解冻')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    logs = models.JSONField(default=list, blank=True, verbose_name='支付日志')

    class Meta:
        verbose_name = '支付记录'
        verbose_name_plural = '支付记录'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['order']),
            models.Index(fields=['checkout_order']),
            models.Index(fields=['profit_sharing_status']),
        ]

    def __str__(self):
        return f'支付#{self.id} 订单:{self.order_id} 状态:{self.status}'

    @classmethod
    def create_for_order(cls, order, method='wechat', ttl_minutes=None):
        now = timezone.now()
        from django.conf import settings as dj_settings
        ttl = ttl_minutes if ttl_minutes is not None else getattr(dj_settings, 'ORDER_PAYMENT_TIMEOUT_MINUTES', 1440)
        amount = order.actual_amount or order.total_amount
        requires_profit_sharing = cls.requires_profit_sharing(order)
        payment = cls.objects.create(
            order=order,
            checkout_order=getattr(order, 'checkout_order', None),
            amount=amount,
            method=method,
            status='init',
            profit_sharing_required=requires_profit_sharing,
            profit_sharing_status='pending' if requires_profit_sharing else 'not_required',
            expires_at=now + timedelta(minutes=ttl),
            logs=[{'t': now.isoformat(), 'event': 'start', 'detail': f'start payment {method}'}]
        )
        if payment.checkout_order_id:
            payment.checkout_order.payment_status = 'init'
            payment.checkout_order.payment_number = str(payment.id)
            payment.checkout_order.save(update_fields=['payment_status', 'payment_number', 'updated_at'])
        return payment

    @staticmethod
    def requires_profit_sharing(order):
        from stores.models import Store

        checkout_order = getattr(order, 'checkout_order', None)
        if checkout_order_id := getattr(checkout_order, 'id', None):
            return SubOrder.objects.filter(
                checkout_order_id=checkout_order_id,
                store__store_type=Store.TYPE_PARTNER,
            ).exists()
        if getattr(order, 'store', None):
            return order.store.store_type == Store.TYPE_PARTNER
        return False


class StoreProfitSharingEntry(models.Model):
    STATUS_CHOICES = [
        ('platform_retained', '平台留存'),
        ('pending_receiver_config', '待配置接收方'),
        ('frozen', '冻结中'),
        ('available', '可分账'),
        ('available_for_manual_share', '可手动分账'),
        ('processing', '处理中'),
        ('shared', '分账成功'),
        ('failed', '分账失败'),
        ('manual_settled', '人工结算'),
        ('manual_settlement_required', '需人工结算'),
        ('cancelled', '已取消'),
    ]
    RECEIVER_TYPE_MERCHANT_ID = 'MERCHANT_ID'

    id = models.BigAutoField(primary_key=True)
    checkout_order = models.ForeignKey(CheckoutOrder, on_delete=models.PROTECT, related_name='profit_sharing_entries', verbose_name='结算单')
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='profit_sharing_entries', verbose_name='支付记录')
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='profit_sharing_entries', verbose_name='兼容订单')
    suborder = models.OneToOneField(SubOrder, on_delete=models.PROTECT, related_name='profit_sharing_entry', verbose_name='子单')
    store = models.ForeignKey('stores.Store', on_delete=models.PROTECT, related_name='profit_sharing_entries', verbose_name='店铺')
    store_type_snapshot = models.CharField(max_length=32, verbose_name='店铺类型快照')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='子单实付金额')
    commission_rate_snapshot = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), verbose_name='抽佣比例快照')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='抽佣金额')
    sharing_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='分账金额')
    retained_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='平台留存金额')
    receiver_type = models.CharField(max_length=32, blank=True, default='', verbose_name='接收方类型')
    receiver_account = models.CharField(max_length=64, blank=True, default='', verbose_name='接收方账号')
    receiver_name_snapshot = models.CharField(max_length=128, blank=True, default='', verbose_name='接收方名称快照')
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='frozen', verbose_name='分账流水状态')
    available_at = models.DateTimeField(null=True, blank=True, verbose_name='可分账时间')
    shared_at = models.DateTimeField(null=True, blank=True, verbose_name='分账成功时间')
    failure_reason = models.TextField(blank=True, default='', verbose_name='失败原因')
    logs = models.JSONField(default=list, blank=True, verbose_name='日志')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '店铺分账流水'
        verbose_name_plural = '店铺分账流水'
        indexes = [
            models.Index(fields=['checkout_order', 'status']),
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['store', 'status']),
            models.Index(fields=['available_at']),
        ]

    def __str__(self):
        return f'分账流水#{self.id} 子单:{self.suborder_id} 状态:{self.status}'


class WechatProfitSharingOrder(models.Model):
    STATUS_CHOICES = [
        ('processing', '处理中'),
        ('shared', '分账成功'),
        ('failed', '分账失败'),
        ('closed', '已关闭'),
    ]

    id = models.BigAutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='wechat_profit_sharing_orders', verbose_name='支付记录')
    checkout_order = models.ForeignKey(CheckoutOrder, on_delete=models.PROTECT, related_name='wechat_profit_sharing_orders', verbose_name='结算单')
    entries = models.ManyToManyField(StoreProfitSharingEntry, related_name='wechat_profit_sharing_orders', blank=True, verbose_name='分账流水')
    out_order_no = models.CharField(max_length=100, unique=True, default=generate_order_number, verbose_name='商户分账单号')
    transaction_id = models.CharField(max_length=100, blank=True, default='', verbose_name='微信支付交易号')
    receivers = models.JSONField(default=list, blank=True, verbose_name='接收方列表')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='分账总金额')
    unfreeze_unsplit = models.BooleanField(default=False, verbose_name='解冻剩余资金')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing', verbose_name='状态')
    wechat_response = models.JSONField(default=dict, blank=True, verbose_name='微信响应')
    error_message = models.TextField(blank=True, default='', verbose_name='错误信息')
    operator = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='wechat_profit_sharing_orders', verbose_name='操作人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '微信分账请求'
        verbose_name_plural = '微信分账请求'
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['checkout_order', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'微信分账#{self.out_order_no} 状态:{self.status}'


class Refund(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('succeeded', '退款成功'),
        ('failed', '退款失败'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='refunds', verbose_name='订单')
    payment = models.ForeignKey('orders.Payment', on_delete=models.PROTECT, null=True, blank=True, related_name='refunds', verbose_name='关联支付')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='退款金额')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='退款状态')
    reason = models.CharField(max_length=255, blank=True, default='', verbose_name='退款原因')
    evidence_images = models.JSONField(default=list, blank=True, verbose_name='退款凭证')
    transaction_id = models.CharField(max_length=100, blank=True, default='', verbose_name='退款交易号')
    operator = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='handled_refunds', verbose_name='操作人')
    logs = models.JSONField(default=list, blank=True, verbose_name='退款日志')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '退款记录'
        verbose_name_plural = '退款记录'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['order']),
            models.Index(fields=['payment']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'退款#{self.id} 订单:{self.order_id} 状态:{self.status}'

    @property
    def is_finished(self):
        return self.status in {'succeeded', 'failed'}


# 折扣系统
class Discount(models.Model):
    TYPE_AMOUNT = 'amount'
    TYPE_PERCENT = 'percent'
    TYPE_CHOICES = [
        (TYPE_AMOUNT, '减免金额'),
        (TYPE_PERCENT, '折扣率'),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, default='', verbose_name='名称')
    discount_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_AMOUNT,
        verbose_name='折扣类型'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='折扣值')
    effective_time = models.DateTimeField(verbose_name='生效时间')
    expiration_time = models.DateTimeField(verbose_name='过期时间')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 多对多到用户与商品，使用同一个 through 表体现“针对某用户-某商品”的目标
    users = models.ManyToManyField(
        'users.User', through='DiscountTarget', through_fields=('discount', 'user'), related_name='user_discounts', verbose_name='适用用户'
    )
    products = models.ManyToManyField(
        'catalog.Product', through='DiscountTarget', through_fields=('discount', 'product'), related_name='product_discounts', verbose_name='适用商品'
    )

    class Meta:
        verbose_name = '折扣规则'
        verbose_name_plural = '折扣规则'
        indexes = [
            models.Index(fields=['effective_time', 'expiration_time']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"Discount#{self.id} type={self.discount_type} value={self.amount} prio={self.priority}"

    def resolve_discount_amount(self, base_price: Decimal) -> Decimal:
        base = Decimal(base_price or 0)
        if self.discount_type == self.TYPE_PERCENT:
            rate = Decimal(self.amount)
            if rate < 0:
                rate = Decimal('0')
            if rate > 10:
                rate = Decimal('10')
            discounted_price = (base * rate) / Decimal('10')
            amount = base - discounted_price
        else:
            amount = Decimal(self.amount)
        if amount < 0:
            amount = Decimal('0')
        if amount > base:
            amount = base
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return amount

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        return self.effective_time <= now < self.expiration_time


class DiscountTarget(models.Model):
    id = models.BigAutoField(primary_key=True)
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, related_name='targets', verbose_name='折扣')
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='discount_targets', verbose_name='用户')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='discount_targets', verbose_name='商品')

    class Meta:
        verbose_name = '折扣适用范围'
        verbose_name_plural = '折扣适用范围'
        unique_together = ('discount', 'user', 'product')
        indexes = [
            models.Index(fields=['user', 'product']),
            models.Index(fields=['discount']),
        ]

    def __str__(self):
        return f"Target d={self.discount_id} u={self.user_id} p={self.product_id}"


class OrderStatusHistory(models.Model):
    """订单状态变更历史"""
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        Order, 
        on_delete=models.PROTECT, 
        related_name='status_history',
        verbose_name='订单'
    )
    from_status = models.CharField(max_length=20, verbose_name='原状态')
    to_status = models.CharField(max_length=20, verbose_name='新状态')
    operator = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='操作人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    note = models.TextField(blank=True, default='', verbose_name='备注')

    class Meta:
        verbose_name = '订单状态历史'
        verbose_name_plural = '订单状态历史'
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['from_status', 'to_status']),
        ]

    def __str__(self):
        return f'订单#{self.order_id} {self.from_status} -> {self.to_status}'


class OrderShippingAction(models.Model):
    """管理员发货操作审计记录。"""

    ACTION_CHOICES = [
        ('ship', '发货'),
        ('cancel_shipping', '取消发货'),
        ('reship', '重新发货'),
    ]
    STATUS_CHOICES = [
        ('succeeded', '成功'),
        ('failed', '失败'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='shipping_actions',
        verbose_name='订单',
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name='操作')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='结果')
    shipping_snapshot = models.JSONField(default=dict, blank=True, verbose_name='物流快照')
    operator = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipping_actions',
        verbose_name='操作人',
    )
    reason = models.CharField(max_length=200, blank=True, default='', verbose_name='原因')
    wechat_sync_required = models.BooleanField(default=False, verbose_name='需要同步微信')
    wechat_synced = models.BooleanField(default=False, verbose_name='微信同步成功')
    wechat_response = models.JSONField(default=dict, blank=True, verbose_name='微信响应摘要')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '发货操作记录'
        verbose_name_plural = '发货操作记录'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['order', 'created_at'], name='orders_ship_action_order_idx'),
            models.Index(fields=['action', 'status'], name='orders_ship_action_type_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['order'],
                condition=models.Q(action='cancel_shipping', status='succeeded'),
                name='uniq_success_cancel_shipping',
            ),
        ]

    def __str__(self):
        return f'发货操作#{self.id} 订单:{self.order_id} {self.action}/{self.status}'


class OrderShippingSync(models.Model):
    """微信订单管理发货同步记录"""
    STATUS_CHOICES = [
        ('pending', '待同步'),
        ('succeeded', '同步成功'),
        ('failed', '同步失败'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='shipping_syncs',
        verbose_name='订单'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='同步状态')
    payload = models.JSONField(default=dict, blank=True, verbose_name='请求数据')
    response = models.JSONField(default=dict, blank=True, verbose_name='响应数据')
    error = models.TextField(blank=True, default='', verbose_name='错误信息')
    retry_count = models.PositiveIntegerField(default=0, verbose_name='重试次数')
    next_retry_at = models.DateTimeField(null=True, blank=True, verbose_name='下次重试时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '发货同步记录'
        verbose_name_plural = '发货同步记录'
        indexes = [
            models.Index(fields=['order'], name='orders_ship_sync_order_idx'),
            models.Index(fields=['status'], name='orders_ship_sync_status_idx'),
            models.Index(fields=['next_retry_at'], name='orders_ship_sync_retry_idx'),
        ]

    def __str__(self):
        return f'发货同步#{self.id} 订单:{self.order_id} 状态:{self.status}'


class Invoice(models.Model):
    """
    订单发票模型

    用于记录用户对已完成订单的开票申请以及开具结果。
    支持普通发票与专用发票，保存必要的抬头与纳税信息。
    """
    INVOICE_TYPE_CHOICES = [
        ('normal', '普通发票'),
        ('special', '专用发票'),
    ]
    STATUS_CHOICES = [
        ('requested', '已申请'),
        ('issued', '已开具'),
        ('cancelled', '已取消'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='invoice',
        verbose_name='订单'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='用户'
    )

    title = models.CharField(max_length=200, verbose_name='发票抬头')
    taxpayer_id = models.CharField(max_length=50, blank=True, default='', verbose_name='纳税人识别号')
    email = models.EmailField(blank=True, default='', verbose_name='接收邮箱')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='联系电话')
    address = models.CharField(max_length=200, blank=True, default='', verbose_name='公司地址')
    bank_account = models.CharField(max_length=100, blank=True, default='', verbose_name='开户行及账号')

    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES, default='normal', verbose_name='发票类型')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='开票金额')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='税率(%)')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='税额')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested', verbose_name='状态')
    invoice_number = models.CharField(max_length=100, blank=True, default='', verbose_name='发票号码')
    file_url = models.URLField(blank=True, default='', verbose_name='发票文件URL')
    file = models.FileField(upload_to='invoices/', blank=True, null=True, verbose_name='发票文件')

    requested_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    issued_at = models.DateTimeField(null=True, blank=True, verbose_name='开具时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '订单发票'
        verbose_name_plural = '订单发票'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'requested_at']),
        ]

    def __str__(self):
        return f'发票#{self.id} 订单:{self.order_id} 状态:{self.status}'


class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ('requested', '已申请'),
        ('approved', '已同意'),
        ('in_transit', '退货在途'),
        ('received', '已收到退货'),
        ('rejected', '已拒绝'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='return_request',
        verbose_name='订单'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='return_requests',
        verbose_name='用户'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested', verbose_name='状态')
    reason = models.CharField(max_length=200, verbose_name='退货原因')
    tracking_number = models.CharField(max_length=100, blank=True, default='', verbose_name='退货快递单号')
    evidence_images = models.JSONField(default=list, blank=True, verbose_name='退货凭证图片')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_returns',
        verbose_name='处理人'
    )
    processed_note = models.TextField(blank=True, default='', verbose_name='处理备注')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    class Meta:
        verbose_name = '退货申请'
        verbose_name_plural = '退货申请'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'退货#{self.id} 订单:{self.order_id} 状态:{self.status}'
