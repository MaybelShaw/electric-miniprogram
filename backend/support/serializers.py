from rest_framework import serializers
from .models import SupportConversation, SupportMessage


def _ensure_https(url: str, request=None) -> str:
    if not url:
        return url
    if request is None or not request.is_secure():
        return url
    if url.startswith('http://'):
        return 'https://' + url[len('http://'):]
    return url


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    attachment_url = serializers.SerializerMethodField()
    order_info = serializers.SerializerMethodField()
    product_info = serializers.SerializerMethodField()
    conversation = serializers.IntegerField(source='conversation_id', read_only=True)
    ticket = serializers.IntegerField(source='conversation_id', read_only=True)

    class Meta:
        model = SupportMessage
        fields = [
            'id',
            'conversation',
            'ticket',
            'sender',
            'sender_username',
            'role',
            'content',
            'attachment_type',
            'attachment_url',
            'order_info',
            'product_info',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'conversation',
            'ticket',
            'sender',
            'sender_username',
            'role',
            'attachment_type',
            'attachment_url',
            'order_info',
            'product_info',
            'created_at',
        ]

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get('request')
        url = obj.attachment.url
        if request is not None:
            return _ensure_https(request.build_absolute_uri(url), request)
        return _ensure_https(url, request)

    def get_order_info(self, obj):
        request = self.context.get('request')
        o = getattr(obj, 'order', None)
        if not o:
            return None
        p = getattr(o, 'product', None)
        image = ''
        if p and getattr(p, 'product_image_url', ''):
            image = _ensure_https(p.product_image_url, request)
        elif p and getattr(p, 'main_images', None):
            try:
                image = _ensure_https((p.main_images or [None])[0] or '', request)
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
        request = self.context.get('request')
        p = getattr(obj, 'product', None)
        if not p:
            return None
        image = ''
        if getattr(p, 'product_image_url', ''):
            image = _ensure_https(p.product_image_url, request)
        elif getattr(p, 'main_images', None):
            try:
                image = _ensure_https((p.main_images or [None])[0] or '', request)
            except Exception:
                image = ''
        return {
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
            'image': image,
        }


class SupportConversationSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    last_message = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()

    class Meta:
        model = SupportConversation
        fields = [
            'id',
            'user',
            'user_username',
            'created_at',
            'updated_at',
            'last_message',
            'last_message_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'user_username',
            'created_at',
            'updated_at',
            'last_message',
            'last_message_at',
        ]

    def _get_last_message(self, obj):
        cached = getattr(obj, 'last_message_list', None)
        if cached:
            return cached[0]
        return obj.messages.order_by('-created_at').first()

    def get_last_message(self, obj):
        msg = self._get_last_message(obj)
        if not msg:
            return None
        return SupportMessageSerializer(msg, context=self.context).data

    def get_last_message_at(self, obj):
        msg = self._get_last_message(obj)
        return getattr(msg, 'created_at', None)
