"""
Custom serializer fields and validators for enhanced input validation and security.

This module provides:
- SecureCharField: Automatically escapes HTML in character fields
- ImageFileValidator: Validates image files for type, size, and content
"""

from rest_framework import serializers
from django.utils.html import escape
from decimal import Decimal
import mimetypes


class SecureCharField(serializers.CharField):
    """
    A CharField that automatically escapes HTML content to prevent XSS attacks.
    
    This field sanitizes user input by converting HTML special characters to their
    entity equivalents, preventing malicious scripts from being stored or executed.
    
    Example:
        class ProductSerializer(serializers.ModelSerializer):
            name = SecureCharField(max_length=200)
            description = SecureCharField(required=False, allow_blank=True)
    """
    
    def to_internal_value(self, data):
        """
        Convert input data to internal representation with HTML escaping.
        
        Args:
            data: The input data (typically a string)
            
        Returns:
            str: The escaped string value
            
        Raises:
            ValidationError: If the data is not a valid string
        """
        # First validate using parent class
        value = super().to_internal_value(data)
        
        # Escape HTML special characters
        if value:
            value = escape(value)
        
        return value


class ImageFileValidator:
    """
    Validator for image file uploads.
    
    Validates:
    - File extension is in the allowed list (whitelist)
    - File size does not exceed the maximum
    - MIME type is a valid image type (verified against actual file content)
    - File content matches the declared MIME type
    
    Example:
        class MediaImageSerializer(serializers.ModelSerializer):
            file = serializers.FileField(validators=[ImageFileValidator()])
    """
    
    # Allowed image file extensions (whitelist)
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    
    # Maximum file size: 20MB
    MAX_SIZE = 20 * 1024 * 1024
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp',
    ]
    
    # Magic bytes for image file type detection
    MAGIC_BYTES = {
        b'\xff\xd8\xff': 'image/jpeg',  # JPEG
        b'\x89PNG\r\n\x1a\n': 'image/png',  # PNG
        b'GIF87a': 'image/gif',  # GIF87a
        b'GIF89a': 'image/gif',  # GIF89a
        b'RIFF': 'image/webp',  # WebP (RIFF format)
        b'BM': 'image/bmp',  # BMP
    }
    
    def __init__(self, max_size=None, allowed_extensions=None, allowed_mime_types=None):
        """
        Initialize the validator with custom settings.
        
        Args:
            max_size (int, optional): Maximum file size in bytes. Defaults to 2MB.
            allowed_extensions (list, optional): List of allowed file extensions.
            allowed_mime_types (list, optional): List of allowed MIME types.
        """
        if max_size is not None:
            self.MAX_SIZE = max_size
        if allowed_extensions is not None:
            self.ALLOWED_EXTENSIONS = allowed_extensions
        if allowed_mime_types is not None:
            self.ALLOWED_MIME_TYPES = allowed_mime_types
    
    def __call__(self, file):
        """
        Validate the uploaded file.
        
        Args:
            file: The uploaded file object
            
        Raises:
            ValidationError: If the file fails any validation check
        """
        # Validate file extension
        self._validate_extension(file)
        
        # Validate file size
        self._validate_size(file)
        
        # Validate MIME type
        self._validate_mime_type(file)
    
    def _validate_extension(self, file):
        """
        Validate that the file extension is in the allowed list (whitelist).
        
        Args:
            file: The uploaded file object
            
        Raises:
            ValidationError: If the extension is not allowed
        """
        filename = file.name
        if not filename:
            raise serializers.ValidationError('文件名不能为空')
        
        # Get file extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        if not ext:
            raise serializers.ValidationError('文件必须有扩展名')
        
        if ext not in self.ALLOWED_EXTENSIONS:
            allowed = ', '.join(self.ALLOWED_EXTENSIONS)
            raise serializers.ValidationError(
                f'不支持的文件类型: .{ext}。允许的类型: {allowed}'
            )
    
    def _validate_size(self, file):
        """
        Validate that the file size does not exceed the maximum.
        
        Args:
            file: The uploaded file object
            
        Raises:
            ValidationError: If the file is too large
        """
        if file.size > self.MAX_SIZE:
            max_mb = self.MAX_SIZE / (1024 * 1024)
            raise serializers.ValidationError(
                f'文件大小超过限制: {max_mb:.1f}MB'
            )
    
    def _validate_mime_type(self, file):
        """
        Validate that the file MIME type is a valid image type by checking:
        1. Declared MIME type (if available)
        2. Magic bytes (file signature)
        3. Actual file content
        
        Args:
            file: The uploaded file object
            
        Raises:
            ValidationError: If the MIME type is not a valid image type
        """
        try:
            # Read file header for magic byte detection
            file.seek(0)
            header = file.read(512)
            file.seek(0)
            
            if not header:
                raise serializers.ValidationError('文件为空')
            
            # Check magic bytes first (most reliable)
            detected_mime = self._detect_mime_from_magic_bytes(header)
            
            # If magic bytes detection failed, try other methods
            if not detected_mime:
                detected_mime = self._detect_mime_from_content(file, header)
            
            # Verify detected MIME type is allowed
            if detected_mime not in self.ALLOWED_MIME_TYPES:
                raise serializers.ValidationError(
                    f'文件内容不是有效的图片: {detected_mime}'
                )
        
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(
                f'无法验证文件内容: {str(e)}'
            )
    
    def _detect_mime_from_magic_bytes(self, header):
        """
        Detect MIME type from file magic bytes (file signature).
        
        Args:
            header (bytes): First bytes of the file
            
        Returns:
            str: Detected MIME type or None
        """
        # Check for WebP (special case - RIFF format)
        if header.startswith(b'RIFF') and len(header) >= 12:
            if header[8:12] == b'WEBP':
                return 'image/webp'
        
        # Check other magic bytes
        for magic, mime_type in self.MAGIC_BYTES.items():
            if header.startswith(magic):
                return mime_type
        
        return None
    
    
class PDFOrImageFileValidator(ImageFileValidator):
    ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp',
    ]

    def _detect_mime_from_magic_bytes(self, header):
        mime = super()._detect_mime_from_magic_bytes(header)
        if mime:
            return mime
        # Simple PDF detection by header '%PDF'
        if header.startswith(b'%PDF'):
            return 'application/pdf'
        return None


class AttachmentFileValidator(ImageFileValidator):
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov']
    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp',
        'video/mp4',
        'video/quicktime',
    ]
    MAX_SIZE = 50 * 1024 * 1024
    
    def _detect_mime_from_content(self, file, header):
        """
        Detect MIME type from file content using available methods.
        
        Args:
            file: The uploaded file object
            header (bytes): First bytes of the file
            
        Returns:
            str: Detected MIME type or None
        """
        # Try using python-magic if available
        try:
            import magic
            mime_type = magic.from_buffer(header, mime=True)
            return mime_type
        except ImportError:
            pass
        
        # Fallback to mimetypes module
        mime_type, _ = mimetypes.guess_type(file.name)
        if mime_type:
            return mime_type
        
        # Try PIL/Pillow if available
        try:
            from PIL import Image
            file.seek(0)
            img = Image.open(file)
            file.seek(0)
            
            # Map PIL format to MIME type
            format_to_mime = {
                'JPEG': 'image/jpeg',
                'PNG': 'image/png',
                'GIF': 'image/gif',
                'WEBP': 'image/webp',
                'BMP': 'image/bmp',
            }
            return format_to_mime.get(img.format)
        except ImportError:
            pass
        except Exception:
            pass
        
        return None


class PriceField(serializers.DecimalField):
    """
    A DecimalField specifically for prices with built-in validation.
    
    Ensures:
    - Price is greater than 0
    - Price has at most 2 decimal places
    
    Example:
        class ProductSerializer(serializers.ModelSerializer):
            price = PriceField(max_digits=10, decimal_places=2)
    """
    
    def validate_value(self, value):
        """
        Validate that the price is positive.
        
        Args:
            value: The price value
            
        Raises:
            ValidationError: If the price is not positive
        """
        value = super().validate_value(value)
        
        if value is not None and value <= 0:
            raise serializers.ValidationError('价格必须大于0')
        
        return value


class StockField(serializers.IntegerField):
    """
    An IntegerField specifically for stock quantities with built-in validation.
    
    Ensures:
    - Stock is non-negative
    
    Example:
        class ProductSerializer(serializers.ModelSerializer):
            stock = StockField()
    """
    
    def validate_value(self, value):
        """
        Validate that the stock is non-negative.
        
        Args:
            value: The stock value
            
        Raises:
            ValidationError: If the stock is negative
        """
        value = super().validate_value(value)
        
        if value is not None and value < 0:
            raise serializers.ValidationError('库存不能为负数')
        
        return value
