"""
海尔API视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
import logging
import os

try:
    from .haierapi import HaierAPI
except Exception:
    class HaierAPI:  # type: ignore
        def __init__(self, config):
            self.config = config
        def authenticate(self):
            return False
        def get_products(self, *args, **kwargs):
            return []
        def get_product_prices(self, *args, **kwargs):
            return []
        def check_stock(self, *args, **kwargs):
            return {}
        def get_account_balance(self, *args, **kwargs):
            return {}
        def get_logistics_info(self, *args, **kwargs):
            return {}
from .ylhapi import YLHSystemAPI
from .models import HaierConfig, HaierSyncLog

logger = logging.getLogger(__name__)


class HaierConfigViewSet(viewsets.ModelViewSet):
    """
    海尔API配置管理ViewSet
    
    权限:
    - 仅管理员可访问
    
    端点:
    - GET /api/haier/config/ - 获取配置列表
    - POST /api/haier/config/ - 创建配置
    - GET /api/haier/config/{id}/ - 获取配置详情
    - PUT /api/haier/config/{id}/ - 更新配置
    - DELETE /api/haier/config/{id}/ - 删除配置
    - POST /api/haier/config/{id}/test/ - 测试连接
    """
    
    queryset = HaierConfig.objects.all()
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        """获取序列化器类"""
        from .serializers import HaierConfigSerializer
        return HaierConfigSerializer
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """
        测试海尔API连接
        
        POST /api/haier/config/{id}/test/
        
        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        config_obj = self.get_object()
        
        try:
            # 创建API实例
            api = HaierAPI(config_obj.config)
            
            # 测试认证
            if api.authenticate():
                return Response({
                    "success": True,
                    "message": "海尔API连接测试成功"
                })
            else:
                return Response(
                    {
                        "success": False,
                        "message": "认证失败"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"海尔API测试失败: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class HaierAPIViewSet(viewsets.ViewSet):
    """
    海尔API操作ViewSet
    
    权限:
    - 仅管理员可访问
    
    端点:
    - GET /api/haier/products/ - 查询商品
    - GET /api/haier/prices/ - 查询价格
    - GET /api/haier/stock/ - 查询库存
    - GET /api/haier/balance/ - 查询余额
    - GET /api/haier/logistics/ - 查询物流
    - GET /api/haier/logs/ - 获取操作日志
    """
    
    permission_classes = [IsAdminUser]
    
    def _get_haier_api(self):
        """获取海尔API实例"""
        try:
            config_obj = HaierConfig.objects.filter(is_active=True).first()
            if not config_obj:
                # 从环境变量加载
                config = {
                    'client_id': os.getenv('HAIER_CLIENT_ID'),
                    'client_secret': os.getenv('HAIER_CLIENT_SECRET'),
                    'token_url': os.getenv('HAIER_TOKEN_URL'),
                    'base_url': os.getenv('HAIER_BASE_URL'),
                    'customer_code': os.getenv('HAIER_CUSTOMER_CODE'),
                    'send_to_code': os.getenv('HAIER_SEND_TO_CODE'),
                    'supplier_code': os.getenv('HAIER_SUPPLIER_CODE', '1001'),
                    'password': os.getenv('HAIER_PASSWORD'),
                    'seller_password': os.getenv('HAIER_SELLER_PASSWORD'),
                }
                if not all([config['client_id'], config['client_secret'], config['token_url'], config['base_url']]):
                    raise Exception("海尔API配置不完整")
            else:
                config = config_obj.config
            
            return HaierAPI(config)
        except Exception as e:
            logger.error(f"获取海尔API实例失败: {str(e)}")
            return None
    
    @action(detail=False, methods=['get'])
    def products(self, request):
        """
        查询可采商品
        
        GET /api/haier/products/?product_codes=GA0SZC00U,EC6001-HT3
        """
        api = self._get_haier_api()
        if not api:
            return Response(
                {"error": "海尔API配置错误"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        product_codes_str = request.query_params.get('product_codes', '')
        product_codes = [code.strip() for code in product_codes_str.split(',') if code.strip()]
        
        try:
            products = api.get_products(product_codes=product_codes if product_codes else None)
            return Response({"success": True, "data": products})
        except Exception as e:
            logger.error(f"查询商品失败: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def prices(self, request):
        """
        查询商品价格
        
        GET /api/haier/prices/?product_codes=GA0SZC00U,EC6001-HT3
        """
        api = self._get_haier_api()
        if not api:
            return Response(
                {"error": "海尔API配置错误"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        product_codes_str = request.query_params.get('product_codes', '')
        product_codes = [code.strip() for code in product_codes_str.split(',') if code.strip()]
        
        if not product_codes:
            return Response(
                {"error": "product_codes参数必填"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            prices = api.get_product_prices(product_codes)
            return Response({"success": True, "data": prices})
        except Exception as e:
            logger.error(f"查询价格失败: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def stock(self, request):
        """
        查询库存
        
        GET /api/haier/stock/?product_code=GA0SZC00U&county_code=110101
        """
        api = self._get_haier_api()
        if not api:
            return Response(
                {"error": "海尔API配置错误"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        product_code = request.query_params.get('product_code')
        county_code = request.query_params.get('county_code', '110101')
        
        if not product_code:
            return Response(
                {"error": "product_code参数必填"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stock = api.check_stock(product_code, county_code)
            return Response({"success": True, "data": stock})
        except Exception as e:
            logger.error(f"查询库存失败: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """
        查询付款方余额
        
        GET /api/haier/balance/
        """
        api = self._get_haier_api()
        if not api:
            return Response(
                {"error": "海尔API配置错误"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            balance = api.get_account_balance()
            return Response({"success": True, "data": balance})
        except Exception as e:
            logger.error(f"查询余额失败: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def logistics(self, request):
        """
        查询物流信息
        
        GET /api/haier/logistics/?order_code=SO.20190106.000003
        """
        api = self._get_haier_api()
        if not api:
            return Response(
                {"error": "海尔API配置错误"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        order_code = request.query_params.get('order_code')
        if not order_code:
            return Response(
                {"error": "order_code参数必填"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            logistics = api.get_logistics_info(order_code)
            return Response({"success": True, "data": logistics})
        except Exception as e:
            logger.error(f"查询物流失败: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def logs(self, request):
        """
        获取操作日志
        
        GET /api/haier/logs/?sync_type=products&status=success&limit=10
        """
        queryset = HaierSyncLog.objects.all()
        
        # 筛选条件
        sync_type = request.query_params.get('sync_type')
        sync_status = request.query_params.get('status')
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        if sync_status:
            queryset = queryset.filter(status=sync_status)
        
        # 限制返回数量
        limit = int(request.query_params.get('limit', 10))
        queryset = queryset[:limit]
        
        # 序列化
        from .serializers import HaierSyncLogSerializer
        serializer = HaierSyncLogSerializer(queryset, many=True)
        
        return Response({
            "count": len(serializer.data),
            "results": serializer.data
        })
