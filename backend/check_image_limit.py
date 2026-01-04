
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.development')
django.setup()

from rest_framework.exceptions import ValidationError
from catalog.serializers import ProductSerializer

def test_detail_images_limit():
    serializer = ProductSerializer()
    
    # Test with 50 images (should pass)
    images_50 = [f'http://example.com/image_{i}.jpg' for i in range(50)]
    try:
        serializer.validate_detail_images(images_50)
        print("SUCCESS: 50 images validation passed.")
    except ValidationError as e:
        print(f"FAILURE: 50 images validation failed: {e}")

    # Test with 51 images (should fail)
    images_51 = [f'http://example.com/image_{i}.jpg' for i in range(51)]
    try:
        serializer.validate_detail_images(images_51)
        print("FAILURE: 51 images validation passed (should fail).")
    except ValidationError as e:
        print(f"SUCCESS: 51 images validation failed as expected: {e}")

if __name__ == '__main__':
    test_detail_images_limit()
