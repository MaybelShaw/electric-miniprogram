from django.db import models
from django.db.models import Prefetch, Subquery, OuterRef, Q
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from common.serializers import AttachmentFileValidator
from orders.models import Order
from .models import SupportConversation, SupportMessage, SupportReplyTemplate
from .serializers import SupportConversationSerializer, SupportMessageSerializer, SupportReplyTemplateSerializer
from users.models import User


def _get_support_sender():
    return User.objects.filter(Q(is_staff=True) | Q(role='support')).order_by('id').first()


def _resolve_template_content(template, content_override=None):
    if content_override is not None and content_override != '':
        return content_override
    content = template.content or ''
    if not content and template.title:
        content = template.title
    return content


def _is_auto_reply_rate_limited(conversation, template, now):
    if template.daily_limit and template.daily_limit > 0:
        if template.daily_limit == 1:
            if conversation.last_auto_reply_at and timezone.localdate(conversation.last_auto_reply_at) == timezone.localdate(now):
                return True
        else:
            today = timezone.localdate(now)
            count = SupportMessage.objects.filter(
                conversation=conversation,
                template__template_type=SupportReplyTemplate.TYPE_AUTO,
                created_at__date=today
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


def _maybe_send_auto_reply(conversation, had_user_messages, last_user_message_at):
    templates = SupportReplyTemplate.objects.filter(
        enabled=True,
        template_type=SupportReplyTemplate.TYPE_AUTO,
    ).order_by('sort_order', 'id')
    if not templates.exists():
        return None

    sender = _get_support_sender()
    if not sender:
        return None

    now = timezone.now()
    for template in templates:
        if template.trigger_event == SupportReplyTemplate.TRIGGER_FIRST:
            if not had_user_messages:
                if _is_auto_reply_rate_limited(conversation, template, now):
                    return None
                return _send_template_message(conversation, sender, template, now)
            continue
        if template.trigger_event == SupportReplyTemplate.TRIGGER_IDLE:
            if not last_user_message_at or not template.idle_minutes:
                continue
            if now - last_user_message_at < timedelta(minutes=template.idle_minutes):
                continue
            if conversation.last_auto_reply_at and now - conversation.last_auto_reply_at < timedelta(minutes=template.idle_minutes):
                continue
            if _is_auto_reply_rate_limited(conversation, template, now):
                return None
            return _send_template_message(conversation, sender, template, now)
        if template.trigger_event == SupportReplyTemplate.TRIGGER_BOTH:
            if not had_user_messages:
                if _is_auto_reply_rate_limited(conversation, template, now):
                    return None
                return _send_template_message(conversation, sender, template, now)
            if not last_user_message_at or not template.idle_minutes:
                continue
            if now - last_user_message_at < timedelta(minutes=template.idle_minutes):
                continue
            if conversation.last_auto_reply_at and now - conversation.last_auto_reply_at < timedelta(minutes=template.idle_minutes):
                continue
            if _is_auto_reply_rate_limited(conversation, template, now):
                return None
            return _send_template_message(conversation, sender, template, now)
    return None


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
        is_support = request.user.is_staff or getattr(request.user, 'role', '') == 'support'

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
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
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

        is_support = request.user.is_staff or getattr(request.user, 'role', '') == 'support'
        sender = request.user
        role = 'support' if is_support else 'user'

        conversation, error = self._resolve_conversation_from_body(request, explicit_conversation_id)
        if error:
            return error

        previous_last_user_message_at = conversation.last_user_message_at
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
            if not conversation.first_contacted_at:
                update_fields['first_contacted_at'] = now
        else:
            update_fields['last_support_message_at'] = now
        SupportConversation.objects.filter(id=conversation.id).update(**update_fields)

        if role == 'user':
            _maybe_send_auto_reply(conversation, had_user_messages, previous_last_user_message_at)

        return Response(SupportMessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def _resolve_conversation_from_body(self, request, explicit_conversation_id=None):
        is_support = request.user.is_staff or getattr(request.user, 'role', '') == 'support'
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
        if not (user and (user.is_staff or getattr(user, 'role', '') == 'support')):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            conversation = SupportConversation.objects.select_related('user').get(id=conversation_id)
        except SupportConversation.DoesNotExist:
            return Response({'detail': 'conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        had_user_messages = SupportMessage.objects.filter(conversation=conversation, role='user').exists()
        msg = _maybe_send_auto_reply(conversation, had_user_messages, conversation.last_user_message_at)
        if msg:
            return Response(
                {'triggered': True, 'message': SupportMessageSerializer(msg, context={'request': request}).data},
                status=status.HTTP_201_CREATED
            )
        return Response({'triggered': False}, status=status.HTTP_200_OK)


class SupportApiRootView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = request.build_absolute_uri('.')
        return Response({
            'chat': base + 'chat/',
            'conversations': base + 'chat/conversations/',
            'reply_templates': base + 'reply-templates/',
            'conversation_auto_reply': base + 'conversations/{id}/auto-reply/',
        })


class SupportReplyTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportReplyTemplateSerializer
    queryset = SupportReplyTemplate.objects.all()

    def get_queryset(self):
        user = self.request.user
        is_support = user and (user.is_staff or getattr(user, 'role', '') == 'support')
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
        if not (user and (user.is_staff or getattr(user, 'role', '') == 'support')):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        user = request.user
        if not (user and (user.is_staff or getattr(user, 'role', '') == 'support')):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        if not (user and (user.is_staff or getattr(user, 'role', '') == 'support')):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if not (user and (user.is_staff or getattr(user, 'role', '') == 'support')):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
