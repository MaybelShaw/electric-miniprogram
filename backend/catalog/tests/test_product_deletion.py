from decimal import Decimal

from django.test import TestCase

from catalog.models import Brand, Category, Product, ProductSKU, SpecialZone, SpecialZoneProduct


class ProductDeletionTests(TestCase):
    def setUp(self):
        major = Category.objects.create(name="瓷砖", level=Category.LEVEL_MAJOR)
        self.category = Category.objects.create(
            name="花砖",
            level=Category.LEVEL_MINOR,
            parent=major,
        )
        self.brand = Brand.objects.create(name="马可波罗")

    def create_product(self, name="马可波罗艺术花砖"):
        return Product.objects.create(
            name=name,
            category=self.category,
            brand=self.brand,
            price=Decimal("99.00"),
            stock=10,
        )

    def test_deleting_product_cascades_skus_and_special_zone_links(self):
        product = self.create_product()
        ProductSKU.objects.create(
            product=product,
            name="标准款",
            sku_code="standard",
            price=Decimal("99.00"),
            stock=10,
        )
        ProductSKU.objects.create(
            product=product,
            name="升级款",
            sku_code="premium",
            price=Decimal("129.00"),
            stock=5,
        )
        zone = SpecialZone.objects.create(title="动态专区", slug="dynamic-zone")
        SpecialZoneProduct.objects.create(zone=zone, product=product)

        product.delete()

        self.assertFalse(Product.objects.filter(id=product.id).exists())
        self.assertFalse(ProductSKU.objects.filter(product_id=product.id).exists())
        self.assertFalse(SpecialZoneProduct.objects.filter(product_id=product.id).exists())
