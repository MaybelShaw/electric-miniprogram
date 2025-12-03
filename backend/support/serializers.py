from rest_framework import serializers
from .models import SupportTicket, SupportMessage


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    attachment_url = serializers.SerializerMethodField()
    order_info = serializers.SerializerMethodField()
    product_info = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ['id', 'ticket', 'sender', 'sender_username', 'role', 'content', 'attachment_type', 'attachment_url', 'order_info', 'product_info', 'created_at']
        read_only_fields = ['id', 'sender', 'sender_username', 'role', 'attachment_type', 'attachment_url', 'order_info', 'product_info', 'created_at']

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get('request')
        url = obj.attachment.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_order_info(self, obj):
        o = getattr(obj, 'order', None)
        if not o:
            return None
        p = getattr(o, 'product', None)
        image = ''
        if p and getattr(p, 'product_image_url', ''):
            image = p.product_image_url
        elif p and getattr(p, 'main_images', None):
            try:
                image = (p.main_images or [None])[0] or ''
            except Exception:
                image = ''
        return {
            'id': o.id,
            'order_number': o.order_number,
            'status': o.status,
            'quantity': o.quantity,
            'total_amount': str(o.total_amount),
            'product_id': getattr(o, 'product_id', None),
            'product_name': getattr(p, 'name', '') if p else '',
            'image': image,
        }

    def get_product_info(self, obj):
        p = getattr(obj, 'product', None)
        if not p:
            return None
        image = ''
        if getattr(p, 'product_image_url', ''):
            image = p.product_image_url
        elif getattr(p, 'main_images', None):
            try:
                image = (p.main_images or [None])[0] or ''
            except Exception:
                image = ''
        return {
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
            'image': image,
        }


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'user_username', 'order', 'order_number', 'subject', 'status', 'priority',
            'assigned_to', 'assigned_to_username', 'created_at', 'updated_at', 'messages'
        ]
        read_only_fields = ['id', 'user', 'user_username', 'order_number', 'assigned_to_username', 'created_at', 'updated_at']
