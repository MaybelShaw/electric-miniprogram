from django.db import models
from django.conf import settings
from orders.models import Order
from catalog.models import Product


class SupportConversation(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['user'], name='support_conv_user_idx'),
            models.Index(fields=['updated_at'], name='support_conv_updated_idx'),
        ]


class SupportMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(SupportConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_messages')
    role = models.CharField(max_length=20, default='', db_index=True)
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='support/attachments/%Y/%m/%d/', null=True, blank=True)
    attachment_type = models.CharField(max_length=10, choices=[('image', 'image'), ('video', 'video')], null=True, blank=True, db_index=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_messages')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_messages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='support_msg_conv_created_idx'),
            models.Index(fields=['attachment_type'], name='support_sup_attachm_54bc2a_idx'),
            models.Index(fields=['order'], name='support_sup_order_i_c35c9c_idx'),
            models.Index(fields=['product'], name='support_sup_product_cd2223_idx'),
        ]
