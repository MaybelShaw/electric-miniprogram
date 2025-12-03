from rest_framework import serializers
from .models import SupportTicket, SupportMessage


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = SupportMessage
        fields = ['id', 'ticket', 'sender', 'sender_username', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'sender', 'sender_username', 'role', 'created_at']


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
