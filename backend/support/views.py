from django.db.models import Prefetch, Subquery, OuterRef
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
from .models import SupportConversation, SupportMessage
from .serializers import SupportConversationSerializer, SupportMessageSerializer


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
        explicit_conversation_id = request.data.get('conversation_id') or request.data.get('ticket_id')

        if not content and not attachment and not order_id and not product_id:
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

        msg = SupportMessage.objects.create(
            conversation=conversation,
            sender=sender,
            role=role,
            content=content or '',
            attachment=attachment,
            attachment_type=attachment_type,
            order=order_obj,
            product=product_obj,
        )
        SupportConversation.objects.filter(id=conversation.id).update(updated_at=timezone.now())

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


class SupportApiRootView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = request.build_absolute_uri('.')
        return Response({
            'chat': base + 'chat/',
            'conversations': base + 'chat/conversations/',
        })
