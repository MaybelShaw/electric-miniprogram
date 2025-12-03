from django.db import models
from django.conf import settings
from orders.models import Order
from catalog.models import Product


class SupportTicket(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[('open', 'open'), ('pending', 'pending'), ('resolved', 'resolved'), ('closed', 'closed')], default='open', db_index=True)
    priority = models.CharField(max_length=20, choices=[('low', 'low'), ('normal', 'normal'), ('high', 'high')], default='normal', db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['user', 'created_at']),
        ]


class SupportMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
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
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['attachment_type']),
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]
