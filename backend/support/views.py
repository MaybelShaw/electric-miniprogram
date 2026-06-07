import json
import logging
import uuid
from datetime import timedelta, datetime, time
from zoneinfo import ZoneInfo
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Prefetch, Subquery, OuterRef, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from common.serializers import AttachmentFileValidator, ImageFileValidator
from orders.models import Order
from .models import FeedbackTicket, FeedbackTicketReply, SupportConversation, SupportMessage, SupportReplyTemplate
from .serializers import (
    FeedbackTicketSerializer,
    SupportConversationSerializer,
    SupportMessageSerializer,
    SupportReplyTemplateSerializer,
)
from stores.models import Store, StoreMember
from stores.permissions import can_manage_store, get_accessible_stores, has_store_role, is_platform_admin, is_support_user
from users.models import User

logger = logging.getLogger(__name__)
FEEDBACK_MAX_IMAGES = 9


def _is_support_backend_user(user):
    return is_platform_admin(user) or is_support_user(user)


def _can_reply_feedback_ticket(user, ticket):
    return _is_support_backend_user(user) or can_manage_store(user, ticket.store)


def _can_close_feedback_ticket(user, ticket):
    return is_platform_admin(user) or has_store_role(user, ticket.store, StoreMember.ROLE_STORE_ADMIN)


def _collect_feedback_images(request):
    files = []
    for key in ('images', 'image', 'attachments', 'attachment'):
        files.extend(request.FILES.getlist(key))
    if not files and request.FILES:
        files = list(request.FILES.values())

    existing = request.data.get('attachments') or request.data.get('images')
    existing_paths = []
    if existing and not hasattr(existing, 'read'):
        if isinstance(existing, str):
            try:
                parsed = json.loads(existing)
            except (TypeError, ValueError):
                parsed = [existing]
        else:
            parsed = existing
        if isinstance(parsed, list):
            existing_paths = [str(item).strip() for item in parsed if str(item).strip()]

    if len(files) + len(existing_paths) > FEEDBACK_MAX_IMAGES:
        raise serializers.ValidationError(f'每次最多上传 {FEEDBACK_MAX_IMAGES} 张图片')

    validator = ImageFileValidator()
    saved_paths = []
    for image in files:
        validator(image)
        name = getattr(image, 'name', '') or 'image'
        ext = name.rsplit('.', 1)[-1].lower() if '.' in name else 'jpg'
        today = timezone.localdate()
        path = f"support/feedback/{today:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"
        saved_paths.append(default_storage.save(path, image))
    return existing_paths + saved_paths


def _require_not_closed(ticket):
    if ticket.status == FeedbackTicket.STATUS_CLOSED:
        return Response({'detail': '工单已关闭，不能继续操作'}, status=status.HTTP_400_BAD_REQUEST)
    return None


def _is_store_backend_user(user):
    return bool(
        user
        and getattr(user, 'is_authenticated', False)
        and get_accessible_stores(user).exists()
        and not _is_support_backend_user(user)
    )


def _get_support_sender():
    sender = User.objects.filter(role='support').order_by('id').first()
    if sender:
        return sender
    for user in User.objects.order_by('id'):
        if is_platform_admin(user):
            return user
    return None


def _resolve_template_content(template, content_override=None):
    if content_override is not None and content_override != '':
        return content_override
    content = template.content or ''
    if not content and template.title:
        content = template.title
    return content


def _is_auto_reply_rate_limited(conversation, template, now):
    if template.daily_limit and template.daily_limit > 0:
        tz = ZoneInfo('Asia/Shanghai')
        now_local = timezone.localtime(now, tz)
        if template.daily_limit == 1:
            if conversation.last_auto_reply_at:
                last_local = timezone.localtime(conversation.last_auto_reply_at, tz)
                if last_local.date() == now_local.date():
                    return True
        else:
            today = now_local.date()
            day_start_local = datetime.combine(today, time.min, tzinfo=tz)
            day_end_local = day_start_local + timedelta(days=1)
            day_start_utc = day_start_local.astimezone(timezone.get_fixed_timezone(0))
            day_end_utc = day_end_local.astimezone(timezone.get_fixed_timezone(0))
            count = SupportMessage.objects.filter(
                conversation=conversation,
                template__template_type=SupportReplyTemplate.TYPE_AUTO,
                created_at__gte=day_start_utc,
                created_at__lt=day_end_utc
            ).count()
            if count >= template.daily_limit:
                return True

    if template.user_cooldown_days and template.user_cooldown_days > 0:
        cutoff = now - timedelta(days=template.user_cooldown_days)
        latest = (
            SupportConversation.objects.filter(
                user_id=conversation.user_id,
                last_auto_reply_at__isnull=False
            )
            .order_by('-last_auto_reply_at')
            .values_list('last_auto_reply_at', flat=True)
            .first()
        )
        if latest and latest >= cutoff:
            return True
    return False


def _send_template_message(conversation, sender, template, now, content_override=None):
    message = SupportMessage.objects.create(
        conversation=conversation,
        sender=sender,
        role='support',
        content=_resolve_template_content(template, content_override),
        content_type=template.content_type,
        content_payload=template.content_payload,
        template=template,
        created_at=now,
    )
    SupportReplyTemplate.objects.filter(id=template.id).update(
        usage_count=models.F('usage_count') + 1,
        last_used_at=now,
    )
    SupportConversation.objects.filter(id=conversation.id).update(
        updated_at=now,
        last_support_message_at=now,
        last_auto_reply_at=now,
    )
    return message


def _normalize_auto_reply_time(reference_time, now=None):
    resolved_now = now or timezone.now()
    if not reference_time:
        return resolved_now
    if resolved_now <= reference_time:
        return reference_time + timedelta(seconds=1)
    return resolved_now


def _maybe_send_auto_reply_with_debug(conversation, had_user_messages, last_user_entered_at, now_override=None):
    templates = SupportReplyTemplate.objects.filter(
        enabled=True,
        template_type=SupportReplyTemplate.TYPE_AUTO,
    ).order_by('sort_order', 'id')
    now = now_override or timezone.now()
    debug = {
        'now': now.isoformat(),
        'had_user_messages': had_user_messages,
        'last_user_entered_at': last_user_entered_at.isoformat() if last_user_entered_at else None,
        'last_auto_reply_at': conversation.last_auto_reply_at.isoformat() if conversation.last_auto_reply_at else None,
        'templates_count': templates.count(),
        'templates': [],
    }
    if not templates.exists():
        debug['result'] = 'no_templates'
        return None, debug

    sender = _get_support_sender()
    if not sender:
        debug['result'] = 'no_sender'
        return None, debug
    debug['sender_id'] = sender.id

    for template in templates:
        template_debug = {
            'id': template.id,
            'trigger_event': template.trigger_event,
            'idle_minutes': template.idle_minutes,
            'daily_limit': template.daily_limit,
            'user_cooldown_days': template.user_cooldown_days,
        }
        if template.trigger_event == SupportReplyTemplate.TRIGGER_FIRST:
            if not had_user_messages:
                if _is_auto_reply_rate_limited(conversation, template, now):
                    template_debug['result'] = 'rate_limited'
                    debug['templates'].append(template_debug)
                    debug['result'] = 'rate_limited'
                    return None, debug
                msg = _send_template_message(conversation, sender, template, now)
                template_debug['result'] = 'sent'
                debug['templates'].append(template_debug)
                debug['result'] = 'sent'
                return msg, debug
            template_debug['result'] = 'skipped_had_user_messages'
            debug['templates'].append(template_debug)
            continue
        if template.trigger_event == SupportReplyTemplate.TRIGGER_IDLE:
            if not last_user_entered_at or not template.idle_minutes:
                template_debug['result'] = 'skipped_missing_idle_conditions'
                debug['templates'].append(template_debug)
                continue
            if now - last_user_entered_at < timedelta(minutes=template.idle_minutes):
                template_debug['result'] = 'skipped_idle_not_reached'
                debug['templates'].append(template_debug)
                continue
            if conversation.last_auto_reply_at and now - conversation.last_auto_reply_at < timedelta(minutes=template.idle_minutes):
                template_debug['result'] = 'skipped_auto_reply_recent'
                debug['templates'].append(template_debug)
                continue
            if _is_auto_reply_rate_limited(conversation, template, now):
                template_debug['result'] = 'rate_limited'
                debug['templates'].append(template_debug)
                debug['result'] = 'rate_limited'
                return None, debug
            msg = _send_template_message(conversation, sender, template, now)
            template_debug['result'] = 'sent'
            debug['templates'].append(template_debug)
            debug['result'] = 'sent'
            return msg, debug
        if template.trigger_event == SupportReplyTemplate.TRIGGER_BOTH:
            if not had_user_messages:
                if _is_auto_reply_rate_limited(conversation, template, now):
                    template_debug['result'] = 'rate_limited'
                    debug['templates'].append(template_debug)
                    debug['result'] = 'rate_limited'
                    return None, debug
                msg = _send_template_message(conversation, sender, template, now)
                template_debug['result'] = 'sent'
                debug['templates'].append(template_debug)
                debug['result'] = 'sent'
                return msg, debug
            if not last_user_entered_at or not template.idle_minutes:
                template_debug['result'] = 'skipped_missing_idle_conditions'
                debug['templates'].append(template_debug)
                continue
            if now - last_user_entered_at < timedelta(minutes=template.idle_minutes):
                template_debug['result'] = 'skipped_idle_not_reached'
                debug['templates'].append(template_debug)
                continue
            if conversation.last_auto_reply_at and now - conversation.last_auto_reply_at < timedelta(minutes=template.idle_minutes):
                template_debug['result'] = 'skipped_auto_reply_recent'
                debug['templates'].append(template_debug)
                continue
            if _is_auto_reply_rate_limited(conversation, template, now):
                template_debug['result'] = 'rate_limited'
                debug['templates'].append(template_debug)
                debug['result'] = 'rate_limited'
                return None, debug
            msg = _send_template_message(conversation, sender, template, now)
            template_debug['result'] = 'sent'
            debug['templates'].append(template_debug)
            debug['result'] = 'sent'
            return msg, debug
        template_debug['result'] = 'skipped_unknown_trigger'
        debug['templates'].append(template_debug)
    debug['result'] = 'no_match'
    return None, debug


def _maybe_send_auto_reply(conversation, had_user_messages, last_user_entered_at, now_override=None):
    msg, _ = _maybe_send_auto_reply_with_debug(conversation, had_user_messages, last_user_entered_at, now_override)
    return msg


def _log_auto_reply_debug(context, conversation, request_user, triggered, debug_info):
    logger.info(
        '[SUPPORT_AUTO_REPLY_DEBUG] %s',
        json.dumps(
            {
                'context': context,
                'conversation_id': conversation.id,
                'user_id': conversation.user_id,
                'request_user_id': getattr(request_user, 'id', None),
                'triggered': triggered,
                'debug': debug_info,
            },
            ensure_ascii=False,
            default=str,
        ),
    )


class SupportChatViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportMessageSerializer

    def _ensure_conversation(self, user):
        conversation = (
            SupportConversation.objects.filter(user=user).order_by('-updated_at', '-id').first()
        )
        if conversation:
            return conversation
        return SupportConversation.objects.create(user=user)

    def _resolve_conversation(self, request):
        conversation_id = request.query_params.get('conversation_id') or request.query_params.get('ticket_id')
        user_id_raw = request.query_params.get('user_id')
        is_support = _is_support_backend_user(request.user)

        if conversation_id:
            try:
                cid = int(conversation_id)
            except ValueError:
                return None, Response({'detail': 'invalid conversation_id'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                conv = SupportConversation.objects.select_related('user').get(id=cid)
            except SupportConversation.DoesNotExist:
                return None, Response({'detail': 'conversation not found'}, status=status.HTTP_404_NOT_FOUND)
            if not is_support and conv.user_id != request.user.id:
                return None, Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
            return conv, None

        if user_id_raw:
            if not is_support:
                return None, Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
            try:
                uid = int(user_id_raw)
            except ValueError:
                return None, Response({'detail': 'invalid user_id'}, status=status.HTTP_400_BAD_REQUEST)
            from users.models import User
            try:
                target_user = User.objects.get(id=uid)
            except User.DoesNotExist:
                return None, Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
            return self._ensure_conversation(target_user), None

        return self._ensure_conversation(request.user), None

    @action(detail=False, methods=['get'])
    def conversations(self, request):
        if not _is_support_backend_user(request.user):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

        last_message_prefetch = Prefetch(
            'messages',
            queryset=SupportMessage.objects.select_related('sender').order_by('-created_at')[:1],
            to_attr='last_message_list',
        )

        qs = (
            SupportConversation.objects.select_related('user')
            .prefetch_related(last_message_prefetch)
            .order_by('-updated_at', '-id')
        )

        user_id_raw = request.query_params.get('user_id')
        if user_id_raw:
            try:
                uid = int(user_id_raw)
                qs = qs.filter(user_id=uid)
            except ValueError:
                return Response({'detail': 'invalid user_id'}, status=status.HTTP_400_BAD_REQUEST)

        status_param = request.query_params.get('status')
        if status_param == 'open':
            last_msg_role = SupportMessage.objects.filter(
                conversation=OuterRef('pk')
            ).order_by('-created_at').values('role')[:1]
            qs = qs.annotate(last_msg_role=Subquery(last_msg_role)).filter(last_msg_role='user')

        page = self.paginate_queryset(qs)
        serializer = SupportConversationSerializer(page or qs, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='auto-reply')
    def auto_reply(self, request):
        conversation, error = self._resolve_conversation(request)
        if error:
            return error
        previous_last_user_entered_at = conversation.last_user_entered_at
        base_entered_at = previous_last_user_entered_at or conversation.last_user_message_at or conversation.updated_at or conversation.created_at
        now = timezone.now()
        SupportConversation.objects.filter(id=conversation.id).update(
            last_user_entered_at=now,
            updated_at=now,
        )
        had_user_messages = SupportMessage.objects.filter(conversation=conversation, role='user').exists()
        msg, debug_info = _maybe_send_auto_reply_with_debug(conversation, had_user_messages, base_entered_at, now)
        if msg:
            _log_auto_reply_debug('user_auto_reply', conversation, request.user, True, debug_info)
            payload = {'triggered': True, 'message': SupportMessageSerializer(msg, context={'request': request}).data}
            payload['debug'] = debug_info
            return Response(payload, status=status.HTTP_201_CREATED)
        _log_auto_reply_debug('user_auto_reply', conversation, request.user, False, debug_info)
        payload = {'triggered': False}
        payload['debug'] = debug_info
        return Response(payload, status=status.HTTP_200_OK)

    def list(self, request):
        conversation, error = self._resolve_conversation(request)
        if error:
            return error

        qs = conversation.messages.select_related('order', 'product', 'sender').order_by('created_at')
        after = request.query_params.get('after')
        limit = request.query_params.get('limit')

        if after:
            dt = parse_datetime(after)
            if dt is not None and timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            if dt is not None:
                qs = qs.filter(created_at__gt=dt)
        if limit:
            try:
                l = int(limit)
                if l > 0:
                    qs = qs[:l]
            except ValueError:
                pass

        return Response(SupportMessageSerializer(qs, many=True, context={'request': request}).data)

    def create(self, request):
        content = request.data.get('content', '')
        attachment = request.FILES.get('attachment')
        attachment_type = request.data.get('attachment_type')
        order_id = request.data.get('order_id')
        product_id = request.data.get('product_id')
        template_id = request.data.get('template_id')
        explicit_conversation_id = request.data.get('conversation_id') or request.data.get('ticket_id')

        if not content and not attachment and not order_id and not product_id and not template_id:
            return Response({'detail': 'content or attachment required'}, status=status.HTTP_400_BAD_REQUEST)

        if attachment:
            try:
                AttachmentFileValidator()(attachment)
            except serializers.ValidationError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if not attachment_type:
                ct = getattr(attachment, 'content_type', '') or ''
                if ct.startswith('image/'):
                    attachment_type = 'image'
                elif ct.startswith('video/'):
                    attachment_type = 'video'
            if attachment_type not in ('image', 'video'):
                return Response({'detail': 'unsupported attachment type'}, status=status.HTTP_400_BAD_REQUEST)

        if order_id and product_id:
            return Response({'detail': 'only one of order_id or product_id allowed'}, status=status.HTTP_400_BAD_REQUEST)

        is_support = _is_support_backend_user(request.user)
        sender = request.user
        role = 'support' if is_support else 'user'

        conversation, error = self._resolve_conversation_from_body(request, explicit_conversation_id)
        if error:
            return error

        previous_last_user_entered_at = conversation.last_user_entered_at
        base_entered_at = previous_last_user_entered_at or conversation.last_user_message_at or conversation.updated_at or conversation.created_at
        had_user_messages = SupportMessage.objects.filter(conversation=conversation, role='user').exists()

        order_obj = None
        product_obj = None

        if order_id:
            try:
                oid = int(order_id)
            except ValueError:
                return Response({'detail': 'invalid order_id'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                order_obj = Order.objects.get(id=oid, user_id=conversation.user_id)
            except Order.DoesNotExist:
                return Response({'detail': 'order not found'}, status=status.HTTP_404_NOT_FOUND)

        if product_id:
            try:
                pid = int(product_id)
            except ValueError:
                return Response({'detail': 'invalid product_id'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                product_obj = Product.objects.get(id=pid)
            except Product.DoesNotExist:
                return Response({'detail': 'product not found'}, status=status.HTTP_404_NOT_FOUND)

        template = None
        if template_id:
            if not is_support:
                return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
            try:
                tid = int(template_id)
            except ValueError:
                return Response({'detail': 'invalid template_id'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                template = SupportReplyTemplate.objects.get(id=tid, enabled=True)
            except SupportReplyTemplate.DoesNotExist:
                return Response({'detail': 'template not found'}, status=status.HTTP_404_NOT_FOUND)

        resolved_content = content
        content_type = SupportReplyTemplate.CONTENT_TEXT
        content_payload = {}
        if template:
            resolved_content = _resolve_template_content(template, content_override=content)
            content_type = template.content_type
            content_payload = template.content_payload

        msg = SupportMessage.objects.create(
            conversation=conversation,
            sender=sender,
            role=role,
            content=resolved_content or '',
            content_type=content_type,
            content_payload=content_payload,
            attachment=attachment,
            attachment_type=attachment_type,
            order=order_obj,
            product=product_obj,
            template=template,
        )
        if template:
            SupportReplyTemplate.objects.filter(id=template.id).update(
                usage_count=models.F('usage_count') + 1,
                last_used_at=timezone.now(),
            )
        now = timezone.now()
        update_fields = {'updated_at': now}
        if role == 'user':
            update_fields['last_user_message_at'] = now
            update_fields['last_user_entered_at'] = now
            if not conversation.first_contacted_at:
                update_fields['first_contacted_at'] = now
        else:
            update_fields['last_support_message_at'] = now
        SupportConversation.objects.filter(id=conversation.id).update(**update_fields)

        if role == 'user':
            auto_reply_now = _normalize_auto_reply_time(msg.created_at)
            _maybe_send_auto_reply(conversation, had_user_messages, base_entered_at, auto_reply_now)

        return Response(SupportMessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def _resolve_conversation_from_body(self, request, explicit_conversation_id=None):
        is_support = _is_support_backend_user(request.user)
        user_id_raw = request.data.get('user_id')

        if explicit_conversation_id:
            try:
                cid = int(explicit_conversation_id)
            except ValueError:
                return None, Response({'detail': 'invalid conversation_id'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                conv = SupportConversation.objects.select_related('user').get(id=cid)
            except SupportConversation.DoesNotExist:
                return None, Response({'detail': 'conversation not found'}, status=status.HTTP_404_NOT_FOUND)
            if not is_support and conv.user_id != request.user.id:
                return None, Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
            return conv, None

        if user_id_raw and is_support:
            try:
                uid = int(user_id_raw)
            except ValueError:
                return None, Response({'detail': 'invalid user_id'}, status=status.HTTP_400_BAD_REQUEST)
            from users.models import User
            try:
                target_user = User.objects.get(id=uid)
            except User.DoesNotExist:
                return None, Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
            return self._ensure_conversation(target_user), None

        return self._ensure_conversation(request.user), None


class SupportConversationAutoReplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        user = request.user
        if not _is_support_backend_user(user):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            conversation = SupportConversation.objects.select_related('user').get(id=conversation_id)
        except SupportConversation.DoesNotExist:
            return Response({'detail': 'conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        had_user_messages = SupportMessage.objects.filter(conversation=conversation, role='user').exists()
        base_entered_at = conversation.last_user_entered_at or conversation.last_user_message_at or conversation.updated_at or conversation.created_at
        msg, debug_info = _maybe_send_auto_reply_with_debug(conversation, had_user_messages, base_entered_at)
        if msg:
            _log_auto_reply_debug('staff_auto_reply', conversation, request.user, True, debug_info)
            payload = {'triggered': True, 'message': SupportMessageSerializer(msg, context={'request': request}).data}
            payload['debug'] = debug_info
            return Response(payload, status=status.HTTP_201_CREATED)
        _log_auto_reply_debug('staff_auto_reply', conversation, request.user, False, debug_info)
        payload = {'triggered': False}
        payload['debug'] = debug_info
        return Response(payload, status=status.HTTP_200_OK)


class SupportApiRootView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = request.build_absolute_uri('.')
        return Response({
            'chat': base + 'chat/',
            'conversations': base + 'chat/conversations/',
            'reply_templates': base + 'reply-templates/',
            'feedback_tickets': base + 'feedback-tickets/',
            'conversation_auto_reply': base + 'conversations/{id}/auto-reply/',
        })


class FeedbackTicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedbackTicketSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = (
            FeedbackTicket.objects.select_related('store', 'user')
            .prefetch_related(
                Prefetch(
                    'replies',
                    queryset=FeedbackTicketReply.objects.select_related('sender').order_by('created_at', 'id'),
                    to_attr='prefetched_replies',
                )
            )
            .order_by('-created_at', '-id')
        )

        if is_platform_admin(user) or is_support_user(user):
            pass
        elif _is_store_backend_user(user):
            store_ids = list(get_accessible_stores(user).values_list('id', flat=True))
            qs = qs.filter(store_id__in=store_ids)
        else:
            qs = qs.filter(user=user)

        ticket_type = self.request.query_params.get('ticket_type') or self.request.query_params.get('type')
        if ticket_type:
            types = [item.strip() for item in str(ticket_type).split(',') if item.strip()]
            qs = qs.filter(ticket_type__in=types)

        status_value = self.request.query_params.get('status')
        if status_value:
            statuses = [item.strip() for item in str(status_value).split(',') if item.strip()]
            qs = qs.filter(status__in=statuses)

        store_id = self.request.query_params.get('store') or self.request.query_params.get('store_id')
        if store_id not in (None, ''):
            qs = qs.filter(store_id=store_id)

        date_from = self.request.query_params.get('date_from') or self.request.query_params.get('created_from')
        date_to = self.request.query_params.get('date_to') or self.request.query_params.get('created_to')
        if date_from:
            dt = parse_datetime(date_from)
            if dt is None:
                try:
                    dt = datetime.fromisoformat(f"{date_from}T00:00:00")
                except ValueError:
                    dt = None
            if dt is not None:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                qs = qs.filter(created_at__gte=dt)
        if date_to:
            dt = parse_datetime(date_to)
            if dt is None:
                try:
                    dt = datetime.fromisoformat(f"{date_to}T23:59:59")
                except ValueError:
                    dt = None
            if dt is not None:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                qs = qs.filter(created_at__lte=dt)

        keyword = self.request.query_params.get('search') or self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(ticket_number__icontains=keyword)
                | Q(title__icontains=keyword)
                | Q(content__icontains=keyword)
                | Q(user__username__icontains=keyword)
                | Q(user__phone__icontains=keyword)
                | Q(contact_phone__icontains=keyword)
            )

        return qs

    def create(self, request, *args, **kwargs):
        if _is_store_backend_user(request.user) or _is_support_backend_user(request.user):
            return Response({'detail': '后台账号不能创建用户工单'}, status=status.HTTP_403_FORBIDDEN)

        store_id = request.data.get('store') or request.data.get('store_id')
        if not store_id:
            return Response({'detail': '请选择店铺'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            store = Store.objects.get(id=int(store_id), status=Store.STATUS_ACTIVE)
        except (Store.DoesNotExist, ValueError, TypeError):
            return Response({'detail': '店铺不存在或不可用'}, status=status.HTTP_400_BAD_REQUEST)

        ticket_type = request.data.get('ticket_type') or request.data.get('type') or FeedbackTicket.TYPE_QUESTION
        if ticket_type not in {FeedbackTicket.TYPE_QUESTION, FeedbackTicket.TYPE_REQUIREMENT}:
            return Response({'detail': '工单类型不正确'}, status=status.HTTP_400_BAD_REQUEST)

        title = (request.data.get('title') or '').strip()
        content = (request.data.get('content') or '').strip()
        if not 5 <= len(title) <= 60:
            return Response({'detail': '标题需为 5-60 字'}, status=status.HTTP_400_BAD_REQUEST)
        if not 10 <= len(content) <= 1000:
            return Response({'detail': '内容需为 10-1000 字'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attachments = _collect_feedback_images(request)
        except serializers.ValidationError as exc:
            return Response({'detail': exc.detail if hasattr(exc, 'detail') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        ticket = FeedbackTicket.objects.create(
            store=store,
            user=request.user,
            ticket_type=ticket_type,
            title=title,
            content=content,
            contact_phone=(request.data.get('contact_phone') or '').strip(),
            attachments=attachments,
        )
        serializer = self.get_serializer(ticket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='stores')
    def stores(self, request):
        qs = Store.objects.filter(status=Store.STATUS_ACTIVE).order_by('-show_on_home', 'home_order', '-is_main', 'id')
        return Response([
            {
                'id': store.id,
                'name': store.name,
                'code': store.code,
                'logo': store.logo,
                'cover_image': store.cover_image,
                'description': store.description,
                'contact_phone': store.contact_phone,
                'address': store.address,
                'show_on_home': store.show_on_home,
                'home_order': store.home_order,
            }
            for store in qs
        ])

    @action(detail=False, methods=['post'], url_path='upload-image')
    def upload_image(self, request):
        image = request.FILES.get('image') or request.FILES.get('file') or request.FILES.get('attachment')
        if not image:
            return Response({'detail': '请选择图片'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ImageFileValidator()(image)
        except serializers.ValidationError as exc:
            return Response({'detail': exc.detail if hasattr(exc, 'detail') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        name = getattr(image, 'name', '') or 'image'
        ext = name.rsplit('.', 1)[-1].lower() if '.' in name else 'jpg'
        today = timezone.localdate()
        path = default_storage.save(f"support/feedback/{today:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}", image)
        return Response({'path': path, 'url': default_storage.url(path)}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        pending_count = self.get_queryset().filter(status=FeedbackTicket.STATUS_PENDING).count()
        return Response({'pending_count': pending_count})

    @action(detail=True, methods=['post'], url_path='supplement')
    def supplement(self, request, pk=None):
        ticket = self.get_object()
        if ticket.user_id != request.user.id:
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        closed_error = _require_not_closed(ticket)
        if closed_error:
            return closed_error

        content = (request.data.get('content') or '').strip()
        try:
            attachments = _collect_feedback_images(request)
        except serializers.ValidationError as exc:
            return Response({'detail': exc.detail if hasattr(exc, 'detail') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not content and not attachments:
            return Response({'detail': '请填写补充内容或上传图片'}, status=status.HTTP_400_BAD_REQUEST)
        if content and len(content) > 1000:
            return Response({'detail': '补充内容不能超过 1000 字'}, status=status.HTTP_400_BAD_REQUEST)

        FeedbackTicketReply.objects.create(
            ticket=ticket,
            sender=request.user,
            record_type=FeedbackTicketReply.TYPE_USER_SUPPLEMENT,
            content=content,
            attachments=attachments,
        )
        FeedbackTicket.objects.filter(id=ticket.id).update(status=FeedbackTicket.STATUS_PENDING, updated_at=timezone.now())
        ticket.refresh_from_db()
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=['post'], url_path='reply')
    def reply(self, request, pk=None):
        ticket = self.get_object()
        if not _can_reply_feedback_ticket(request.user, ticket):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        closed_error = _require_not_closed(ticket)
        if closed_error:
            return closed_error

        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'detail': '请填写回复内容'}, status=status.HTTP_400_BAD_REQUEST)
        if len(content) > 1000:
            return Response({'detail': '回复内容不能超过 1000 字'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            attachments = _collect_feedback_images(request)
        except serializers.ValidationError as exc:
            return Response({'detail': exc.detail if hasattr(exc, 'detail') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        FeedbackTicketReply.objects.create(
            ticket=ticket,
            sender=request.user,
            record_type=FeedbackTicketReply.TYPE_MERCHANT_REPLY,
            content=content,
            attachments=attachments,
        )
        FeedbackTicket.objects.filter(id=ticket.id).update(
            status=FeedbackTicket.STATUS_REPLIED,
            last_replied_at=now,
            updated_at=now,
        )
        ticket.refresh_from_db()
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        ticket = self.get_object()
        if not _can_close_feedback_ticket(request.user, ticket):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        closed_error = _require_not_closed(ticket)
        if closed_error:
            return closed_error

        content = (request.data.get('content') or request.data.get('close_note') or '').strip()
        if len(content) > 1000:
            return Response({'detail': '关闭说明不能超过 1000 字'}, status=status.HTTP_400_BAD_REQUEST)
        FeedbackTicketReply.objects.create(
            ticket=ticket,
            sender=request.user,
            record_type=FeedbackTicketReply.TYPE_CLOSE,
            content=content,
            attachments=[],
        )
        FeedbackTicket.objects.filter(id=ticket.id).update(status=FeedbackTicket.STATUS_CLOSED, updated_at=timezone.now())
        ticket.refresh_from_db()
        return Response(self.get_serializer(ticket).data)


class SupportReplyTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportReplyTemplateSerializer
    queryset = SupportReplyTemplate.objects.all()

    def get_queryset(self):
        user = self.request.user
        is_support = _is_support_backend_user(user)
        if not is_support:
            return SupportReplyTemplate.objects.none()

        qs = super().get_queryset()
        template_type = self.request.query_params.get('type')
        enabled = self.request.query_params.get('enabled')
        group_name = self.request.query_params.get('group')
        keyword = self.request.query_params.get('search')

        if template_type in {'A', 'a'}:
            template_type = SupportReplyTemplate.TYPE_AUTO
        elif template_type in {'B', 'b'}:
            template_type = SupportReplyTemplate.TYPE_QUICK

        if template_type in {SupportReplyTemplate.TYPE_AUTO, SupportReplyTemplate.TYPE_QUICK}:
            qs = qs.filter(template_type=template_type)
        if enabled is not None:
            if str(enabled).lower() in {'true', '1', 'yes'}:
                qs = qs.filter(enabled=True)
            elif str(enabled).lower() in {'false', '0', 'no'}:
                qs = qs.filter(enabled=False)
        if group_name:
            qs = qs.filter(group_name=group_name)
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))

        return qs.order_by('-is_pinned', 'sort_order', 'id')

    def list(self, request, *args, **kwargs):
        user = request.user
        if not _is_support_backend_user(user):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        user = request.user
        if not _is_support_backend_user(user):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        if not _is_support_backend_user(user):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if not _is_support_backend_user(user):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
