"""
同步海尔商品数据的管理命令
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Product, Category, Brand
from integrations.haierapi import HaierAPI
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '从海尔API同步商品数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-codes',
            nargs='+',
            type=str,
            help='指定要同步的产品编码列表'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='指定商品分类名称'
        )
        parser.add_argument(
            '--brand',
            type=str,
            help='指定品牌名称'
        )
        parser.add_argument(
            '--sync-prices',
            action='store_true',
            help='同步价格信息'
        )
        parser.add_argument(
            '--sync-stock',
            action='store_true',
            help='同步库存信息'
        )
        parser.add_argument(
            '--county-code',
            type=str,
            default='110101',
            help='区域编码（用于库存查询，默认北京东城区）'
        )

    def handle(self, *args, **options):
        # 初始化海尔API
        config = {
            'client_id': settings.HAIER_CLIENT_ID,
            'client_secret': settings.HAIER_CLIENT_SECRET,
            'token_url': settings.HAIER_TOKEN_URL,
            'base_url': settings.HAIER_BASE_URL,
            'customer_code': settings.HAIER_CUSTOMER_CODE,
            'send_to_code': settings.HAIER_SEND_TO_CODE,
            'supplier_code': settings.HAIER_SUPPLIER_CODE,
            'password': settings.HAIER_PASSWORD,
            'seller_password': settings.HAIER_SELLER_PASSWORD,
        }
        
        haier_api = HaierAPI(config)
        
        # 认证
        self.stdout.write('正在认证...')
        if not haier_api.authenticate():
            self.stdout.write(self.style.ERROR('认证失败'))
            return
        
        self.stdout.write(self.style.SUCCESS('认证成功'))
        
        # 获取分类和品牌
        category = None
        if options['category']:
            try:
                category = Category.objects.get(name=options['category'])
                self.stdout.write(f"使用分类: {category.name}")
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"分类不存在: {options['category']}"))
        
        brand = None
        if options['brand']:
            try:
                brand = Brand.objects.get(name=options['brand'])
                self.stdout.write(f"使用品牌: {brand.name}")
            except Brand.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"品牌不存在: {options['brand']}"))
        
        # 查询商品
        product_codes = options.get('product_codes')
        self.stdout.write(f"正在查询商品... {product_codes or '全部'}")
        
        products_data = haier_api.get_products(product_codes=product_codes)
        
        if not products_data:
            self.stdout.write(self.style.WARNING('未查询到商品'))
            return
        
        self.stdout.write(f"查询到 {len(products_data)} 个商品")
        
        # 同步商品
        synced_count = 0
        for product_data in products_data:
            try:
                product_code = product_data.get('productCode')
                
                # 同步价格信息
                if options['sync_prices']:
                    self.stdout.write(f"正在查询价格: {product_code}")
                    prices = haier_api.get_product_prices([product_code])
                    if prices:
                        product_data.update(prices[0])
                
                # 同步商品
                product = Product.sync_from_haier(product_data, category, brand)
                
                if product:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ 同步成功: {product.name} ({product_code})")
                    )
                    
                    # 同步库存信息
                    if options['sync_stock']:
                        self.stdout.write(f"  正在查询库存...")
                        stock_data = haier_api.check_stock(
                            product_code,
                            options['county_code']
                        )
                        if stock_data:
                            product.update_stock_from_haier(stock_data)
                            self.stdout.write(
                                self.style.SUCCESS(f"  ✓ 库存更新: {product.stock}件")
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"  ! 库存查询失败")
                            )
                    
                    synced_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f"✗ 同步失败: {product_code}")
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ 错误: {product_code} - {str(e)}")
                )
                logger.exception(f"同步商品失败: {product_code}")
        
        # 总结
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f"同步完成: {synced_count}/{len(products_data)} 个商品"))
