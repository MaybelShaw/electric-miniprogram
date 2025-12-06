from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from catalog.models import Category, Brand, Product
from orders.models import Order


class Command(BaseCommand):
    help = "Seed basic test data: user, category, brand, product, and a sample pending order."

    def handle(self, *args, **options):
        user = self._get_or_create_user()
        category = self._get_or_create_category()
        brand = self._get_or_create_brand()
        product = self._get_or_create_product(category, brand)
        order = self._get_or_create_order(user, product)

        self.stdout.write(self.style.SUCCESS("Seed data created/ensured:"))
        self.stdout.write(f"- User: {user.username}")
        self.stdout.write(f"- Category: {category.name}")
        self.stdout.write(f"- Brand: {brand.name}")
        self.stdout.write(f"- Product: {product.name}")
        self.stdout.write(f"- Order: {order.order_number} (status: {order.status})")

    def _get_or_create_user(self):
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@example.com",
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if not user.has_usable_password():
            user.set_password("demo1234")
            user.save(update_fields=["password"])
        return user

    def _get_or_create_category(self):
        category, _ = Category.objects.get_or_create(
            name="家电",
            defaults={"level": Category.LEVEL_MAJOR, "order": 1},
        )
        return category

    def _get_or_create_brand(self):
        brand, _ = Brand.objects.get_or_create(name="示例品牌", defaults={"order": 1})
        return brand

    def _get_or_create_product(self, category, brand):
        product, _ = Product.objects.get_or_create(
            name="示例商品",
            defaults={
                "category": category,
                "brand": brand,
                "price": Decimal("1999.00"),
                "stock": 100,
                "description": "示例商品描述",
            },
        )
        return product

    def _get_or_create_order(self, user, product):
        order = (
            Order.objects.filter(user=user, product=product)
            .order_by("-created_at")
            .first()
        )
        if order:
            return order
        return Order.objects.create(
            user=user,
            product=product,
            quantity=1,
            total_amount=product.price,
            actual_amount=product.price,
            status="pending",
            snapshot_contact_name="张三",
            snapshot_phone="13800000000",
            snapshot_address="示例地址",
        )
