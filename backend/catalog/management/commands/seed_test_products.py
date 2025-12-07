"""
快速插入测试商品/SKU数据，用于本地联调与端到端演示。

Usage:
    python manage.py seed_test_products
    python manage.py seed_test_products --products 8 --skus 3
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from catalog.models import Category, Brand, Product, ProductSKU


class Command(BaseCommand):
    help = 'Seed demo products with multiple SKUs for local testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            type=int,
            default=5,
            help='How many products to create (default: 5)',
        )
        parser.add_argument(
            '--skus',
            type=int,
            default=2,
            help='How many SKUs per product (default: 2)',
        )

    def handle(self, *args, **options):
        product_count = max(1, options['products'])
        sku_count = max(1, options['skus'])

        # 基础分类与品牌
        major_cat, _ = Category.objects.get_or_create(
            name='测试家电',
            defaults={'level': Category.LEVEL_MAJOR},
        )
        minor_cat, _ = Category.objects.get_or_create(
            name='测试品类',
            defaults={'level': Category.LEVEL_MINOR, 'parent': major_cat},
        )
        brand, _ = Brand.objects.get_or_create(name='测试品牌')

        created_products = 0
        created_skus = 0

        for idx in range(1, product_count + 1):
            name = f'测试商品{idx:02d}'
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'{name} 的描述信息',
                    'category': minor_cat,
                    'brand': brand,
                    'price': Decimal('1999.00') + Decimal(idx * 10),
                    'stock': 0,
                    'is_active': True,
                    'main_images': [f'https://dummyimage.com/600x600/000/fff&text={name}'],
                    'detail_images': [],
                },
            )
            created_products += 1

            # 创建 SKUs
            colors = ['红', '蓝', '黑', '白', '银', '灰']
            capacities = ['256G', '512G', '1T', '2T']
            for sk in range(sku_count):
                color = colors[(idx + sk) % len(colors)]
                capacity = capacities[(idx + sk) % len(capacities)]
                sku_name = f'{name}-{color}-{capacity}'
                sku_code = f'SKU-{idx:02d}-{sk+1:02d}'
                sku, created = ProductSKU.objects.get_or_create(
                    product=product,
                    sku_code=sku_code,
                    defaults={
                        'name': sku_name,
                        'specs': {'颜色': color, '容量': capacity},
                        'price': product.price + Decimal(sk * 50),
                        'stock': 20 + sk * 5,
                        'image': f'https://dummyimage.com/600x600/{(idx*37)%999:03}/{(sk*91)%999:03}&text={sku_name}',
                        'is_active': True,
                    },
                )
                if created:
                    created_skus += 1
                    # 累加商品可用库存
                    product.stock = (product.stock or 0) + sku.stock
            product.save(update_fields=['stock'])

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created_products} products with {created_skus} SKUs in total'
        ))
