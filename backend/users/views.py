from django.shortcuts import render
import requests
import uuid
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from django.conf import settings
from .models import User, Address, CompanyInfo, CreditAccount, AccountStatement, AccountTransaction
from .serializers import (
    UserSerializer, 
    UserProfileSerializer, 
    AddressSerializer, 
    CompanyInfoSerializer,
    CreditAccountSerializer,
    AccountStatementSerializer,
    AccountStatementDetailSerializer,
    AccountTransactionSerializer
)
from django.db.models import Q
from common.permissions import IsOwnerOrAdmin, IsAdmin
from common.throttles import LoginRateThrottle
from common.address_parser import address_parser
from common.utils import to_bool
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes as OT


# Create your views here.
@extend_schema(tags=['Authentication'])
class WeChatLoginView(APIView):
    """
    微信小程序登录接口
    
    功能：
    - 接收微信小程序的code
    - 调用微信API验证code并获取openid
    - 创建或获取用户
    - 返回JWT token
    
    登录模式：
    - 配置了微信凭证：调用真实微信API（开发和生产环境推荐）
    - 未配置微信凭证：使用模拟登录（仅用于本地测试）
    
    特殊功能：
    - code以'admin'开头时自动授予管理员权限（仅开发环境）
    """
    # 登录接口允许匿名访问，并关闭 JWT 认证，避免因携带无效令牌导致 401
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    throttle_classes = [LoginRateThrottle]
    
    @extend_schema(
        operation_id='wechat_login',
        description='WeChat mini program login. Exchange WeChat code for JWT token.',
    )
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        code = request.data.get("code")
        if not code:
            logger.warning('微信登录失败: 缺少code参数')
            return Response(
                {"error": "Code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 获取微信配置
        appid = settings.WECHAT_APPID
        secret = settings.WECHAT_SECRET
        
        # 检查是否配置了微信凭证
        if not appid or not secret:
            # 未配置微信凭证时，使用模拟登录（仅用于本地测试）
            logger.warning('微信凭证未配置，使用模拟登录模式')
            logger.info(f'模拟登录: code={code}')
            openid = code
            session_key = None
        else:
            # 调用微信API（开发和生产环境都使用真实API）
            url = f"https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code"
            
            try:
                logger.info(f'调用微信API: code={code[:10]}...')
                response = requests.get(url, timeout=10)
                data = response.json()
                
                logger.info(f'微信API响应: {data}')
                
                if "errcode" in data:
                    error_code = data.get("errcode")
                    error_msg = data.get("errmsg", "Unknown error")
                    logger.error(f'微信API错误: errcode={error_code}, errmsg={error_msg}')
                    return Response(
                        {
                            "error": "WeChat API error",
                            "errcode": error_code,
                            "errmsg": error_msg
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                openid = data.get("openid")
                session_key = data.get("session_key")
                
                if not openid:
                    logger.error(f'微信API返回数据异常: 缺少openid, data={data}')
                    return Response(
                        {"error": "Invalid WeChat response"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                logger.info(f'微信登录成功: openid={openid[:10]}...')
                
            except requests.RequestException as e:
                logger.error(f'调用微信API失败: {str(e)}')
                return Response(
                    {"error": "Failed to connect to WeChat API"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            except Exception as e:
                logger.error(f'微信登录异常: {str(e)}')
                return Response(
                    {"error": "Internal server error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        from .services import (
            get_or_create_wechat_user,
            grant_admin_on_debug_code,
            update_last_login,
            create_tokens_for_user,
        )

        user, created = get_or_create_wechat_user(openid)
        
        if created:
            logger.info(f'创建新用户: user_id={user.id}, openid={openid[:10]}...')
        else:
            logger.info(f'用户登录: user_id={user.id}, openid={openid[:10]}...')

        # 开发环境支持管理员快捷登录：code 以 'admin' 开头时授予管理员权限
        try:
            granted = grant_admin_on_debug_code(str(code).strip().lower(), user, settings.DEBUG)
            if granted:
                logger.info(f'授予管理员权限: user_id={user.id}')
        except Exception as e:
            logger.error(f'授予管理员权限失败: {str(e)}')

        update_last_login(user)

        refresh, access = create_tokens_for_user(user)

        logger.info(f'登录成功: user_id={user.id}, username={user.username}')

        return Response(
            {
                "access": access,
                "refresh": refresh,
                "user": UserSerializer(user).data,
            }
        )


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@extend_schema(tags=['Authentication'])
@method_decorator(csrf_exempt, name='dispatch')
class PasswordLoginView(APIView):
    """管理员用户名+密码登录。
    - 允许匿名访问
    - 验证用户名与密码
    - 非管理员用户返回 403
    - 开发环境支持快捷创建管理员（若用户名不存在）
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        operation_id='password_login',
        description='Admin password login. Authenticate with username and password to get JWT token.',
    )
    def post(self, request):
        from .services import (
            bootstrap_or_init_admin,
            ensure_user_password,
            update_last_login,
            create_tokens_for_user,
        )
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"error": "用户名与密码必填"}, status=status.HTTP_400_BAD_REQUEST)

        admin_exists = User.objects.filter(is_staff=True).exists()
        user = User.objects.filter(username=username).order_by('-date_joined').first()

        if user is None:
            created_or_initialized = bootstrap_or_init_admin(username, password)
            if created_or_initialized:
                update_last_login(created_or_initialized)
                refresh, access = create_tokens_for_user(created_or_initialized)
                return Response(
                    {
                        "access": access,
                        "refresh": refresh,
                        "user": UserSerializer(created_or_initialized).data,
                    }
                )
            return Response({"error": "用户名或密码错误"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            # 用户存在但无可用密码：允许使用当前提交的密码进行首次初始化（不自动提升为管理员，除非系统无管理员）
            ensure_user_password(user, password)

        # 校验密码
        if not user.check_password(password):
            return Response({"error": "用户名或密码错误"}, status=status.HTTP_401_UNAUTHORIZED)

        # 权限校验：仅在系统无管理员的情况下提升为管理员以完成首次引导
        if not user.is_staff:
            if not admin_exists:
                user.is_staff = True
                user.is_superuser = True
                user.role = 'admin'
                user.save()
            else:
                return Response({"error": "无管理员权限"}, status=status.HTTP_403_FORBIDDEN)
        
        # 确保管理员用户的 role 字段正确
        if user.is_staff and user.role != 'admin':
            user.role = 'admin'
            user.save(update_fields=['role'])

        update_last_login(user)

        refresh, access = create_tokens_for_user(user)

        return Response(
            {
                "access": access,
                "refresh": refresh,
                "user": UserSerializer(user).data,
            }
        )

@api_view(['GET','PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    if request.method == 'GET':
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)
    elif request.method == 'PATCH':
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_statistics(request):
    """
    Get user statistics including orders.
    
    Returns:
    - orders_count: Total number of orders
    - completed_orders_count: Number of completed orders
    - pending_orders_count: Number of pending orders
    - total_spent: Total amount spent on completed orders
    """
    from django.core.cache import cache
    from django.db.models import Sum
    
    user = request.user
    cache_key = f'user_stats_{user.id}'
    
    stats = cache.get(cache_key)
    if stats is None:
        orders_qs = user.orders.all()
        
        stats = {
            'orders_count': orders_qs.count(),
            'completed_orders_count': orders_qs.filter(status='completed').count(),
            'pending_orders_count': orders_qs.filter(status='pending').count(),
            'total_spent': float(
                orders_qs.filter(status='completed').aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            ),
        }
        
        cache.set(cache_key, stats, 300)  # Cache for 5 minutes
    
    return Response(stats)

@extend_schema(tags=['Addresses'])
class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user addresses.
    
    Permissions:
    - IsAuthenticated: Users can only manage their own addresses
    
    Note: list() method returns a simple array instead of paginated response
    """
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # 禁用分页

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-id')

    def list(self, request, *args, **kwargs):
        """返回地址列表（数组格式，不分页）"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        address = self.get_object()
        Address.objects.filter(user=request.user, is_default=True).update(
            is_default=False
        )
        address.is_default = True
        address.save()
        return Response({"status": "默认地址已设置"})
    
    @extend_schema(
        operation_id='parse_address',
        description='Parse a complete address text into province, city, district and detail',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'address': {
                        'type': 'string',
                        'description': '完整的地址文本',
                        'example': '北京市朝阳区建国路88号SOHO现代城A座1001室'
                    }
                },
                'required': ['address']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'province': {'type': 'string', 'nullable': True},
                            'city': {'type': 'string', 'nullable': True},
                            'district': {'type': 'string', 'nullable': True},
                            'detail': {'type': 'string', 'nullable': True}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=["post"], url_path="parse")
    def parse_address(self, request):
        """
        解析完整地址文本
        
        用户输入完整地址后，后端自动识别并拆分成省、市、区、详细地址
        """
        address_text = request.data.get('address', '').strip()
        
        if not address_text:
            return Response({
                'success': False,
                'message': '地址不能为空',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 使用地址解析器解析地址
        result = address_parser.parse_address(address_text)
        
        return Response({
            'success': result['success'],
            'message': result['message'],
            'data': {
                'province': result['province'],
                'city': result['city'],
                'district': result['district'],
                'detail': result['detail']
            }
        })


@extend_schema(tags=['Users'])
class AdminUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for administrator user management.
    
    Permissions:
    - IsAuthenticated: User must be logged in
    - IsAdmin: User must be an administrator
    
    Provides CRUD operations and admin privilege management.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        # 统一搜索：在用户名或 OpenID 上模糊匹配
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(username__icontains=search) | Q(openid__icontains=search))
        # 新增：支持按手机号模糊查询
        phone = self.request.query_params.get('phone')
        if phone:
            qs = qs.filter(phone__icontains=phone)
        # 管理员筛选：支持 true/false/1/0/布尔
        is_staff = self.request.query_params.get('is_staff')
        if is_staff is not None:
            parsed = to_bool(is_staff)
            if parsed is not None:
                try:
                    qs = qs.filter(is_staff=parsed)
                except Exception:
                    pass
        # 角色筛选：支持按role字段筛选
        role = self.request.query_params.get('role')
        if role:
            try:
                qs = qs.filter(role=role)
            except Exception:
                pass
        return qs

    def create(self, request, *args, **kwargs):
        # 允许管理员创建用户：当未提供 openid 时自动生成，若提供密码则安全哈希
        data = request.data.copy()
        if not data.get('openid'):
            data['openid'] = f"manual:{uuid.uuid4().hex[:24]}"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        instance = serializer.save()
        raw_password = self.request.data.get('password')
        if raw_password:
            try:
                instance.set_password(raw_password)
                instance.save()
            except Exception:
                # 若设置密码失败，不阻断创建；密码保持未初始化，由后续流程设置
                pass

    @action(detail=True, methods=['post'])
    def set_admin(self, request, pk=None):
        user = self.get_object()
        user.is_staff = True
        user.is_superuser = True
        user.role = 'admin'
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def unset_admin(self, request, pk=None):
        user = self.get_object()
        user.is_staff = False
        user.is_superuser = False
        # When removing admin privileges, reset to individual unless they are a dealer
        if user.role == 'admin':
            user.role = 'dealer' if hasattr(user, 'company_info') and user.company_info.status == 'approved' else 'individual'
        user.save()
        return Response(UserSerializer(user).data)


@extend_schema(tags=['Company Info'])
class CompanyInfoViewSet(viewsets.ModelViewSet):
    """
    ViewSet for company information management.
    
    User endpoints:
    - POST: Submit company info for dealer certification
    - GET: View own company info
    - PATCH: Update company info (only if pending or rejected)
    
    Admin endpoints:
    - GET list: View all company info submissions
    - approve: Approve company info and upgrade user to dealer
    - reject: Reject company info submission
    """
    queryset = CompanyInfo.objects.all().order_by('-created_at')
    serializer_class = CompanyInfoSerializer
    
    def get_permissions(self):
        """
        Override to allow different permissions for different actions
        """
        if self.action in ['approve', 'reject']:
            # Admin-only actions
            return [IsAuthenticated(), IsAdmin()]
        # Regular authenticated users can create/view/update their own
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return CompanyInfo.objects.none()
        
        if user.is_staff:
            # Admin can see all
            qs = super().get_queryset()
            # Filter by status
            status_filter = self.request.query_params.get('status')
            if status_filter:
                qs = qs.filter(status=status_filter)
            return qs
        else:
            # Regular users can only see their own
            return CompanyInfo.objects.filter(user=user)
    
    def list(self, request, *args, **kwargs):
        """List company info - admin sees all, users see their own"""
        if not request.user.is_staff:
            # For regular users, return their company info or empty
            try:
                company_info = CompanyInfo.objects.get(user=request.user)
                serializer = self.get_serializer(company_info)
                return Response(serializer.data)
            except CompanyInfo.DoesNotExist:
                return Response(None, status=status.HTTP_404_NOT_FOUND)
        
        # Admin gets paginated list
        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Submit company info for certification"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f'创建公司信息请求: user={request.user}, is_authenticated={request.user.is_authenticated}')
        
        # Check if user already has company info
        if hasattr(request.user, 'company_info'):
            logger.warning(f'用户已有公司信息: user_id={request.user.id}')
            return Response(
                {"error": "您已提交公司信息，请勿重复提交"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f'创建公司信息: user_id={request.user.id}, data={request.data}')
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update company info - only allowed if pending or rejected"""
        import logging
        logger = logging.getLogger(__name__)
        
        instance = self.get_object()
        
        # Only owner or admin can update
        if instance.user != request.user and not request.user.is_staff:
            logger.warning(f'无权限修改公司信息: user_id={request.user.id}, company_info_id={instance.id}')
            return Response(
                {"error": "无权限修改"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Users can only update if pending or rejected
        if not request.user.is_staff and instance.status == 'approved':
            logger.warning(f'已审核通过的信息不可修改: user_id={request.user.id}, company_info_id={instance.id}')
            return Response(
                {"error": "已审核通过的信息不可修改"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If user is updating rejected info, reset status to pending
        if not request.user.is_staff and instance.status == 'rejected':
            logger.info(f'用户重新提交被拒绝的公司信息: user_id={request.user.id}, company_info_id={instance.id}')
            instance.status = 'pending'
            instance.approved_at = None
        
        response = super().update(request, *args, **kwargs)
        
        # Save status change if it was modified
        if not request.user.is_staff and instance.status == 'pending':
            instance.save()
        
        return response
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve company info and upgrade user to dealer"""
        from django.utils import timezone
        from decimal import Decimal
        from .credit_services import CreditAccountService
        
        company_info = self.get_object()
        
        if company_info.status == 'approved':
            return Response(
                {"error": "该公司信息已审核通过"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update company info status
        company_info.status = 'approved'
        company_info.approved_at = timezone.now()
        company_info.save()
        
        # Upgrade user to dealer
        user = company_info.user
        user.role = 'dealer'
        user.save()
        try:
            if not hasattr(user, 'credit_account'):
                CreditAccountService.create_credit_account(user, Decimal('0.00'), payment_term_days=30)
        except Exception:
            pass
        credit_account_data = None
        try:
            account = CreditAccount.objects.get(user=user)
            credit_account_data = CreditAccountSerializer(account).data
        except CreditAccount.DoesNotExist:
            credit_account_data = None
        
        return Response({
            "message": "审核通过，用户已升级为经销商",
            "company_info": CompanyInfoSerializer(company_info).data,
            "user": UserSerializer(user).data,
            "credit_account": credit_account_data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject company info submission"""
        company_info = self.get_object()
        
        if company_info.status == 'approved':
            return Response(
                {"error": "已审核通过的信息不可拒绝"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        company_info.status = 'rejected'
        company_info.save()
        
        return Response({
            "message": "已拒绝该公司信息",
            "company_info": CompanyInfoSerializer(company_info).data
        })


@extend_schema(tags=['Credit Account'])
class CreditAccountViewSet(viewsets.ModelViewSet):
    """
    信用账户管理
    
    Admin endpoints:
    - GET list: 查看所有经销商信用账户
    - POST: 为经销商创建信用账户
    - PATCH: 更新信用额度和账期
    - GET detail: 查看信用账户详情
    
    Dealer endpoints:
    - GET my_account: 查看自己的信用账户
    """
    queryset = CreditAccount.objects.all().select_related('user', 'user__company_info').order_by('-created_at')
    serializer_class = CreditAccountSerializer
    
    def get_permissions(self):
        if self.action in ['my_account']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]
    
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return CreditAccount.objects.none()
        
        if user.is_staff:
            # Admin can see all
            qs = super().get_queryset()
            # Filter by active status
            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                parsed = to_bool(is_active)
                if parsed is not None:
                    qs = qs.filter(is_active=parsed)
            return qs
        else:
            # Dealers can only see their own
            return CreditAccount.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_account(self, request):
        """经销商查看自己的信用账户"""
        try:
            account = CreditAccount.objects.get(user=request.user)
            serializer = self.get_serializer(account)
            return Response(serializer.data)
        except CreditAccount.DoesNotExist:
            return Response(
                {"error": "您还没有信用账户"},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(tags=['Account Statement'])
class AccountStatementViewSet(viewsets.ModelViewSet):
    """
    账务对账单管理
    
    Admin endpoints:
    - GET list: 查看所有对账单
    - POST: 创建对账单
    - GET detail: 查看对账单详情（包含交易记录）
    - confirm: 确认对账单
    - settle: 结清对账单
    - export: 导出对账单为Excel
    
    Dealer endpoints:
    - GET my_statements: 查看自己的对账单列表
    - GET detail: 查看对账单详情
    """
    queryset = AccountStatement.objects.all().select_related(
        'credit_account',
        'credit_account__user',
        'credit_account__user__company_info'
    ).order_by('-period_end', '-created_at')
    
    def get_permissions(self):
        if self.action in ['my_statements', 'retrieve', 'confirm']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AccountStatementDetailSerializer
        return AccountStatementSerializer
    
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return AccountStatement.objects.none()
        
        if user.is_staff:
            # Admin can see all
            qs = super().get_queryset()
            
            # Filter by status
            status_filter = self.request.query_params.get('status')
            if status_filter:
                qs = qs.filter(status=status_filter)
            
            # Filter by credit account
            credit_account_id = self.request.query_params.get('credit_account')
            if credit_account_id:
                qs = qs.filter(credit_account_id=credit_account_id)
            
            # Filter by date range
            start_date = self.request.query_params.get('start_date')
            end_date = self.request.query_params.get('end_date')
            if start_date:
                qs = qs.filter(period_start__gte=start_date)
            if end_date:
                qs = qs.filter(period_end__lte=end_date)
            
            return qs
        else:
            # Dealers can only see their own
            try:
                credit_account = CreditAccount.objects.get(user=user)
                return AccountStatement.objects.filter(credit_account=credit_account)
            except CreditAccount.DoesNotExist:
                return AccountStatement.objects.none()

    def create(self, request, *args, **kwargs):
        """管理员创建对账单：根据账期自动汇总交易生成对账单"""
        from .credit_services import AccountStatementService
        from datetime import date
        try:
            credit_account_id = request.data.get('credit_account')
            period_start = request.data.get('period_start')
            period_end = request.data.get('period_end')
            if not credit_account_id or not period_start or not period_end:
                return Response({"error": "credit_account、period_start、period_end 为必填"}, status=status.HTTP_400_BAD_REQUEST)
            # Parse dates
            try:
                ps = date.fromisoformat(str(period_start))
                pe = date.fromisoformat(str(period_end))
            except Exception:
                return Response({"error": "账期日期格式错误，需使用YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
            if ps > pe:
                return Response({"error": "账期开始不能晚于账期结束"}, status=status.HTTP_400_BAD_REQUEST)
            # Load credit account
            try:
                credit_account = CreditAccount.objects.select_related('user').get(id=credit_account_id)
            except CreditAccount.DoesNotExist:
                return Response({"error": "信用账户不存在"}, status=status.HTTP_404_NOT_FOUND)
            # Only allow for dealers
            if credit_account.user.role != 'dealer':
                return Response({"error": "仅支持为经销商创建对账单"}, status=status.HTTP_400_BAD_REQUEST)
            # Prevent duplicate statement for exact period
            existing = AccountStatement.objects.filter(
                credit_account=credit_account,
                period_start=ps,
                period_end=pe,
            ).exists()
            if existing:
                return Response({"error": "该账期的对账单已存在"}, status=status.HTTP_400_BAD_REQUEST)
            # Generate statement via service
            statement = AccountStatementService.generate_statement(credit_account, ps, pe)
            serializer = self.get_serializer(statement)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_statements(self, request):
        """经销商查看自己的对账单列表"""
        try:
            credit_account = CreditAccount.objects.get(user=request.user)
            statements = AccountStatement.objects.filter(
                credit_account=credit_account
            ).order_by('-period_end')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                statements = statements.filter(period_start__gte=start_date)
            if end_date:
                statements = statements.filter(period_end__lte=end_date)
            
            # Apply pagination
            page = self.paginate_queryset(statements)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(statements, many=True)
            return Response(serializer.data)
        except CreditAccount.DoesNotExist:
            return Response(
                {"error": "您还没有信用账户"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """确认对账单"""
        from django.utils import timezone
        
        statement = self.get_object()
        
        if statement.status != 'draft':
            return Response(
                {"error": "只能确认草稿状态的对账单"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        statement.status = 'confirmed'
        statement.confirmed_at = timezone.now()
        statement.save()
        
        return Response({
            "message": "对账单已确认",
            "statement": AccountStatementSerializer(statement).data
        })
    
    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        """结清对账单"""
        from django.utils import timezone
        
        statement = self.get_object()
        
        if statement.status == 'settled':
            return Response(
                {"error": "对账单已结清"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        statement.status = 'settled'
        statement.settled_at = timezone.now()
        statement.save()
        
        # Update credit account outstanding debt
        credit_account = statement.credit_account
        credit_account.outstanding_debt -= statement.period_end_balance
        if credit_account.outstanding_debt < 0:
            credit_account.outstanding_debt = 0
        credit_account.save()
        
        # Create payment transaction
        AccountTransaction.objects.create(
            credit_account=credit_account,
            statement=statement,
            transaction_type='payment',
            amount=statement.period_end_balance,
            balance_after=credit_account.outstanding_debt,
            payment_status='paid',
            paid_date=timezone.now().date(),
            description=f'对账单结算: {statement.period_start} 至 {statement.period_end}'
        )
        
        return Response({
            "message": "对账单已结清",
            "statement": AccountStatementSerializer(statement).data
        })
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """导出对账单为Excel"""
        from django.http import HttpResponse
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        
        statement = self.get_object()
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "对账单"
        
        # Header style
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        # Title
        ws.merge_cells('A1:H1')
        ws['A1'] = f"账务对账单 - {statement.credit_account.user.company_info.company_name}"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Statement info
        ws['A3'] = "账期："
        ws['B3'] = f"{statement.period_start} 至 {statement.period_end}"
        ws['A4'] = "状态："
        ws['B4'] = statement.get_status_display()
        
        # Financial summary
        ws['A6'] = "财务汇总"
        ws['A6'].font = Font(bold=True)
        
        summary_data = [
            ["上期结余", statement.previous_balance],
            ["本期采购", statement.current_purchases],
            ["本期付款", statement.current_payments],
            ["本期退款", statement.current_refunds],
            ["期末未付", statement.period_end_balance],
            ["账期内应付", statement.due_within_term],
            ["账期内已付", statement.paid_within_term],
            ["往来余额（逾期）", statement.overdue_amount],
        ]
        
        for idx, (label, value) in enumerate(summary_data, start=7):
            ws[f'A{idx}'] = label
            ws[f'B{idx}'] = float(value)
        
        # Transaction details
        ws[f'A{len(summary_data) + 9}'] = "交易明细"
        ws[f'A{len(summary_data) + 9}'].font = Font(bold=True)
        
        # Transaction headers
        headers = ["日期", "交易类型", "金额", "余额", "订单ID", "应付日期", "实付日期", "付款状态", "备注"]
        header_row = len(summary_data) + 10
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Transaction data
        transactions = statement.transactions.all().order_by('created_at')
        for row_idx, transaction in enumerate(transactions, start=header_row + 1):
            ws.cell(row=row_idx, column=1, value=transaction.created_at.strftime('%Y-%m-%d'))
            ws.cell(row=row_idx, column=2, value=transaction.get_transaction_type_display())
            ws.cell(row=row_idx, column=3, value=float(transaction.amount))
            ws.cell(row=row_idx, column=4, value=float(transaction.balance_after))
            ws.cell(row=row_idx, column=5, value=transaction.order_id or '')
            ws.cell(row=row_idx, column=6, value=transaction.due_date.strftime('%Y-%m-%d') if transaction.due_date else '')
            ws.cell(row=row_idx, column=7, value=transaction.paid_date.strftime('%Y-%m-%d') if transaction.paid_date else '')
            ws.cell(row=row_idx, column=8, value=transaction.get_payment_status_display())
            ws.cell(row=row_idx, column=9, value=transaction.description)
        
        # Adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        # Save to response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="statement_{statement.id}_{statement.period_start}_{statement.period_end}.xlsx"'
        wb.save(response)
        
        return response


@extend_schema(tags=['Account Transaction'])
class AccountTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    账务交易记录查询
    
    Admin endpoints:
    - GET list: 查看所有交易记录
    - GET detail: 查看交易详情
    
    Dealer endpoints:
    - GET my_transactions: 查看自己的交易记录
    """
    queryset = AccountTransaction.objects.all().select_related(
        'credit_account',
        'credit_account__user',
        'statement'
    ).order_by('-created_at')
    serializer_class = AccountTransactionSerializer
    
    def get_permissions(self):
        if self.action in ['my_transactions']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]
    
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return AccountTransaction.objects.none()
        
        if user.is_staff:
            # Admin can see all
            qs = super().get_queryset()
            
            # Filter by credit account
            credit_account_id = self.request.query_params.get('credit_account')
            if credit_account_id:
                qs = qs.filter(credit_account_id=credit_account_id)
            
            # Filter by transaction type
            transaction_type = self.request.query_params.get('transaction_type')
            if transaction_type:
                qs = qs.filter(transaction_type=transaction_type)
            
            # Filter by payment status
            payment_status = self.request.query_params.get('payment_status')
            if payment_status:
                qs = qs.filter(payment_status=payment_status)
            
            # Filter by date range
            start_date = self.request.query_params.get('start_date')
            end_date = self.request.query_params.get('end_date')
            if start_date:
                qs = qs.filter(created_at__gte=start_date)
            if end_date:
                # Handle end_date inclusive for DateTimeField
                try:
                    from datetime import datetime, timedelta
                    ed = datetime.strptime(end_date, '%Y-%m-%d')
                    ed_end = ed + timedelta(days=1)
                    qs = qs.filter(created_at__lt=ed_end)
                except (ValueError, TypeError):
                    qs = qs.filter(created_at__lte=end_date)
            
            return qs
        else:
            # Dealers can only see their own
            try:
                credit_account = CreditAccount.objects.get(user=user)
                return AccountTransaction.objects.filter(credit_account=credit_account)
            except CreditAccount.DoesNotExist:
                return AccountTransaction.objects.none()
    
    @action(detail=False, methods=['get'])
    def my_transactions(self, request):
        """经销商查看自己的交易记录"""
        try:
            credit_account = CreditAccount.objects.get(user=request.user)
            transactions = AccountTransaction.objects.filter(
                credit_account=credit_account
            ).order_by('-created_at')
            
            transaction_type = request.query_params.get('transaction_type')
            if transaction_type:
                transactions = transactions.filter(transaction_type=transaction_type)
            
            payment_status = request.query_params.get('payment_status')
            if payment_status:
                transactions = transactions.filter(payment_status=payment_status)
            
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                transactions = transactions.filter(created_at__gte=start_date)
            if end_date:
                # Handle end_date inclusive for DateTimeField
                try:
                    from datetime import datetime, timedelta
                    ed = datetime.strptime(end_date, '%Y-%m-%d')
                    ed_end = ed + timedelta(days=1)
                    transactions = transactions.filter(created_at__lt=ed_end)
                except (ValueError, TypeError):
                    transactions = transactions.filter(created_at__lte=end_date)
            
            # Apply pagination
            page = self.paginate_queryset(transactions)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(transactions, many=True)
            return Response(serializer.data)
        except CreditAccount.DoesNotExist:
            return Response(
                {"error": "您还没有信用账户"},
                status=status.HTTP_404_NOT_FOUND
            )
