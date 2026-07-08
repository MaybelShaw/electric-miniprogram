from django.contrib import admin

from .models import FeedbackTicket, FeedbackTicketReply, SupportConversation, SupportMessage, SupportReplyTemplate


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    fields = ("sender", "role", "content_type", "content", "order", "product", "created_at")
    readonly_fields = ("created_at",)


@admin.register(SupportConversation)
class SupportConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "user", "updated_at", "last_user_message_at", "last_support_message_at")
    list_filter = ("store", "updated_at", "last_user_message_at", "last_support_message_at")
    search_fields = ("user__username", "user__phone", "user__openid")
    readonly_fields = (
        "created_at",
        "updated_at",
        "first_contacted_at",
        "last_user_message_at",
        "last_user_entered_at",
        "last_support_message_at",
        "last_auto_reply_at",
    )
    inlines = [SupportMessageInline]


@admin.register(SupportReplyTemplate)
class SupportReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "title", "template_type", "content_type", "enabled", "is_pinned", "sort_order", "updated_at")
    list_filter = ("store", "template_type", "content_type", "enabled", "is_pinned", "trigger_event")
    search_fields = ("title", "content", "group_name")
    readonly_fields = ("usage_count", "last_used_at", "created_at", "updated_at")


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "role", "content_type", "order", "product", "created_at")
    list_filter = ("role", "content_type", "attachment_type", "created_at")
    search_fields = ("sender__username", "content", "order__order_number", "product__name")
    readonly_fields = ("created_at",)


class FeedbackTicketReplyInline(admin.TabularInline):
    model = FeedbackTicketReply
    extra = 0
    fields = ("sender", "record_type", "content", "created_at")
    readonly_fields = ("created_at",)


@admin.register(FeedbackTicket)
class FeedbackTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "title", "ticket_type", "store", "user", "status", "created_at", "last_replied_at")
    list_filter = ("ticket_type", "status", "store", "created_at")
    search_fields = ("ticket_number", "title", "content", "user__username", "user__phone", "contact_phone")
    readonly_fields = ("ticket_number", "created_at", "updated_at", "last_replied_at")
    inlines = [FeedbackTicketReplyInline]


@admin.register(FeedbackTicketReply)
class FeedbackTicketReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "sender", "record_type", "created_at")
    list_filter = ("record_type", "created_at")
    search_fields = ("ticket__ticket_number", "sender__username", "content")
    readonly_fields = ("created_at",)
