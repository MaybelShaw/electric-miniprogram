import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from stores.models import Store


class ProductAttachmentTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir, MEDIA_URL='/media/')
        self.settings_override.enable()

        self.client = APIClient()
        self.store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        major = Category.objects.create(name='Appliance', level=Category.LEVEL_MAJOR, store=self.store)
        self.category = Category.objects.create(
            name='Refrigerator',
            level=Category.LEVEL_MINOR,
            parent=major,
            store=self.store,
        )
        self.brand = Brand.objects.create(name='Premium Brand', store=self.store)
        self.admin = get_user_model().objects.create_superuser(
            username='attachment-admin',
            password='password',
        )

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_dir, ignore_errors=True)

    def create_product(self, **overrides):
        data = {
            'store': self.store,
            'name': 'Refrigerator',
            'category': self.category,
            'brand': self.brand,
            'price': Decimal('6999.00'),
            'stock': 10,
            'is_active': True,
        }
        data.update(overrides)
        return Product.objects.create(**data)

    def test_upload_attachment_accepts_pdf_only(self):
        self.client.force_authenticate(self.admin)

        pdf_response = self.client.post(
            '/api/catalog/products/upload-attachment/',
            {'file': ContentFile(b'%PDF-1.4\nbody', name='manual.pdf')},
            format='multipart',
        )

        self.assertEqual(pdf_response.status_code, 201, pdf_response.content)
        self.assertEqual(pdf_response.data['name'], 'manual.pdf')
        self.assertEqual(pdf_response.data['file_type'], 'pdf')
        self.assertTrue(pdf_response.data['url'].startswith('/media/product_attachments/'))

        txt_response = self.client.post(
            '/api/catalog/products/upload-attachment/',
            {'file': ContentFile(b'not pdf', name='manual.txt')},
            format='multipart',
        )

        self.assertEqual(txt_response.status_code, 400, txt_response.content)

    def test_product_update_removes_unreferenced_attachment_file(self):
        self.client.force_authenticate(self.admin)
        storage_name = default_storage.save(
            'product_attachments/manual.pdf',
            ContentFile(b'%PDF-1.4\nbody'),
        )
        url = f'/media/{storage_name}'
        product = self.create_product(product_attachments=[{'name': 'manual.pdf', 'url': url, 'file_type': 'pdf'}])

        response = self.client.patch(
            f'/api/catalog/products/{product.id}/',
            {'product_attachments': []},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(default_storage.exists(storage_name))
