from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from stores.models import Store


class ProductSpecificationsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        major = Category.objects.create(
            name="Appliance",
            level=Category.LEVEL_MAJOR,
            store=self.store,
        )
        self.category = Category.objects.create(
            name="Refrigerator",
            level=Category.LEVEL_MINOR,
            parent=major,
            store=self.store,
        )
        self.brand = Brand.objects.create(name="Premium Brand", store=self.store)
        self.admin = get_user_model().objects.create_superuser(
            username="catalog-admin",
            password="password",
        )
        self.customer = get_user_model().objects.create_user(
            username="browse-customer",
            password="password",
        )

    def product_payload(self, **overrides):
        payload = {
            "store_id": self.store.id,
            "name": "French door refrigerator",
            "category_id": self.category.id,
            "brand_id": self.brand.id,
            "price": "6999.00",
            "dealer_price": "6299.00",
            "stock": 10,
            "is_active": True,
            "specifications": {
                "capacity": "520L",
                "energy_grade": "level 1",
                "cooling": "no frost",
            },
        }
        payload.update(overrides)
        return payload

    def test_admin_can_create_update_and_public_retrieve_product_specifications(self):
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            "/api/catalog/products/",
            self.product_payload(),
            format="json",
        )

        self.assertEqual(create_response.status_code, 201, create_response.content)
        self.assertEqual(
            create_response.data["specifications"],
            {
                "capacity": "520L",
                "energy_grade": "level 1",
                "cooling": "no frost",
            },
        )

        product_id = create_response.data["id"]
        update_response = self.client.patch(
            f"/api/catalog/products/{product_id}/",
            {"specifications": {"power": "380W", "noise": "36dB"}},
            format="json",
        )

        self.assertEqual(update_response.status_code, 200, update_response.content)
        self.assertEqual(update_response.data["specifications"], {"power": "380W", "noise": "36dB"})

        self.client.force_authenticate(user=None)
        retrieve_response = self.client.get(f"/api/catalog/products/{product_id}/")

        self.assertEqual(retrieve_response.status_code, 200, retrieve_response.content)
        self.assertEqual(retrieve_response.data["specifications"], {"power": "380W", "noise": "36dB"})

    def test_product_specifications_rejects_non_object_payload(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/catalog/products/",
            self.product_payload(specifications=["520L", "level 1"]),
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("specifications", response.data["errors"])

    def test_non_dealer_receives_specifications_without_dealer_price(self):
        product = Product.objects.create(
            store=self.store,
            name="Public appliance",
            category=self.category,
            brand=self.brand,
            price=Decimal("4999.00"),
            dealer_price=Decimal("4299.00"),
            stock=5,
            is_active=True,
            specifications={"capacity": "360L"},
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get(f"/api/catalog/products/{product.id}/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["specifications"], {"capacity": "360L"})
        self.assertNotIn("dealer_price", response.data)
