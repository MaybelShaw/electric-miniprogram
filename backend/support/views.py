from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import SupportTicket, SupportMessage
from orders.models import Order
from catalog.models import Product
from .serializers import SupportTicketSerializer, SupportMessageSerializer
from common.serializers import AttachmentFileValidator


class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all().order_by('-updated_at')
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') == 'support':
            return self.queryset
        return self.queryset.filter(user_id=user.id)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_message(self, request, pk=None):
        ticket = self.get_object()
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support' or ticket.user_id == request.user.id):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        content = request.data.get('content', '')
        attachment = request.FILES.get('attachment')
        attachment_type = request.data.get('attachment_type')
        order_id = request.data.get('order_id')
        product_id = request.data.get('product_id')
        if not content and not attachment and not order_id and not product_id:
            return Response({'detail': 'content or attachment required'}, status=status.HTTP_400_BAD_REQUEST)
        if attachment:
            try:
                AttachmentFileValidator()(attachment)
            except serializers.ValidationError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
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
        role = 'support' if (request.user.is_staff or getattr(request.user, 'role', '') == 'support') else 'user'
        order_obj = None
        product_obj = None
        if order_id:
            try:
                oid = int(order_id)
                order_obj = Order.objects.get(id=oid, user_id=ticket.user_id)
            except Exception:
                return Response({'detail': 'order not found'}, status=status.HTTP_404_NOT_FOUND)
        if product_id:
            try:
                pid = int(product_id)
                product_obj = Product.objects.get(id=pid)
            except Exception:
                return Response({'detail': 'product not found'}, status=status.HTTP_404_NOT_FOUND)
        msg = SupportMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            role=role,
            content=content or '',
            attachment=attachment,
            attachment_type=attachment_type,
            order=order_obj,
            product=product_obj,
        )
        if role == 'support':
            if ticket.status == 'open':
                ticket.status = 'pending'
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['status', 'updated_at'])
            else:
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['updated_at'])
        else:
            if ticket.status != 'open':
                ticket.status = 'open'
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['status', 'updated_at'])
            else:
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['updated_at'])
        return Response(SupportMessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_status(self, request, pk=None):
        ticket = self.get_object()
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        status_value = request.data.get('status')
        valid_status = [c[0] for c in SupportTicket._meta.get_field('status').choices]
        if status_value not in valid_status:
            return Response({'detail': 'invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = status_value
        ticket.save(update_fields=['status'])
        return Response(SupportTicketSerializer(ticket).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        assigned_to = request.data.get('user_id')
        from users.models import User
        try:
            u = User.objects.get(id=assigned_to)
        except User.DoesNotExist:
            return Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
        ticket.assigned_to = u
        ticket.save(update_fields=['assigned_to'])
        return Response(SupportTicketSerializer(ticket).data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def messages(self, request, pk=None):
        ticket = self.get_object()
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support' or ticket.user_id == request.user.id):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        qs = ticket.messages.all().order_by('created_at')
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


class SupportMessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupportMessage.objects.select_related('ticket', 'order', 'product').all().order_by('created_at')
    serializer_class = SupportMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') == 'support':
            base_qs = self.queryset
        else:
            base_qs = self.queryset.filter(Q(sender_id=user.id) | Q(ticket__user_id=user.id))

        params = self.request.query_params
        ticket_id = params.get('ticket')
        after = params.get('after')
        limit = params.get('limit')

        if ticket_id:
            try:
                tid = int(ticket_id)
                base_qs = base_qs.filter(ticket_id=tid)
            except ValueError:
                pass
        if after:
            dt = parse_datetime(after)
            if dt is not None and timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            if dt is not None:
                base_qs = base_qs.filter(created_at__gt=dt)
        if limit:
            try:
                l = int(limit)
                if l > 0:
                    base_qs = base_qs[:l]
            except ValueError:
                pass

        return base_qs


class SupportChatViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportMessageSerializer

    def _ensure_user_chat_ticket(self, user):
        ticket = SupportTicket.objects.filter(user_id=user.id, status__in=['open', 'pending', 'resolved']).order_by('-updated_at').first()
        if not ticket:
            ticket = SupportTicket.objects.create(user=user, subject='会话', status='open', priority='normal')
        return ticket

    @action(detail=False, methods=['get'])
    def conversations(self, request):
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        qs = SupportTicket.objects.all().order_by('-updated_at')
        
        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        else:
            qs = qs.filter(status__in=['open', 'pending', 'resolved'])

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SupportTicketSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SupportTicketSerializer(qs, many=True)
        return Response(serializer.data)

    def list(self, request):
        user_id = request.query_params.get('user_id')
        if user_id:
            if not (request.user.is_staff or getattr(request.user, 'role', '') == 'support'):
                return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
            try:
                uid = int(user_id)
            except ValueError:
                return Response({'detail': 'invalid user_id'}, status=status.HTTP_400_BAD_REQUEST)
            from users.models import User
            try:
                target_user = User.objects.get(id=uid)
            except User.DoesNotExist:
                return Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
            ticket = self._ensure_user_chat_ticket(target_user)
        else:
            ticket = self._ensure_user_chat_ticket(request.user)

        qs = ticket.messages.all().order_by('created_at')
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
        if not content and not attachment and not order_id and not product_id:
            return Response({'detail': 'content or attachment required'}, status=status.HTTP_400_BAD_REQUEST)
        if attachment:
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

        user_id = request.data.get('user_id')
        is_support = request.user.is_staff or getattr(request.user, 'role', '') == 'support'

        if user_id and is_support:
            try:
                uid = int(user_id)
            except ValueError:
                return Response({'detail': 'invalid user_id'}, status=status.HTTP_400_BAD_REQUEST)
            from users.models import User
            try:
                target_user = User.objects.get(id=uid)
            except User.DoesNotExist:
                return Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
            ticket = self._ensure_user_chat_ticket(target_user)
            role = 'support'
            sender = request.user
        else:
            ticket = self._ensure_user_chat_ticket(request.user)
            role = 'user'
            sender = request.user

        order_obj = None
        product_obj = None
        if order_id:
            try:
                oid = int(order_id)
                order_obj = Order.objects.get(id=oid, user_id=ticket.user_id)
            except Exception:
                return Response({'detail': 'order not found'}, status=status.HTTP_404_NOT_FOUND)
        if product_id:
            try:
                pid = int(product_id)
                product_obj = Product.objects.get(id=pid)
            except Exception:
                return Response({'detail': 'product not found'}, status=status.HTTP_404_NOT_FOUND)

        msg = SupportMessage.objects.create(
            ticket=ticket,
            sender=sender,
            role=role,
            content=content or '',
            attachment=attachment,
            attachment_type=attachment_type,
            order=order_obj,
            product=product_obj,
        )
        if role == 'support':
            if ticket.status == 'open':
                ticket.status = 'pending'
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['status', 'updated_at'])
            else:
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['updated_at'])
        else:
            if ticket.status != 'open':
                ticket.status = 'open'
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['status', 'updated_at'])
            else:
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['updated_at'])
        return Response(SupportMessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)


class SupportApiRootView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = request.build_absolute_uri('.')
        return Response({
            'chat': base + 'chat/',
            'tickets': base + 'tickets/',
            'messages': base + 'messages/',
        })
