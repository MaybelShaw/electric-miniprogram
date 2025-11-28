"""
海尔API视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import logging
import os
import json

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


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def ylh_callback_view(request):
    """
    易理货系统回调接口
    
    POST /api/integrations/ylh/callback/
    
    接收海尔平台的回调通知：
    - 确认订单回调 (hmm.scm_heorder.confirm)
    - 取消订单回调 (hmm.scm_heorder.cancel)
    - 订单缺货回调 (hmm.scm_heorder.oostock)
    
    请求格式: application/x-www-form-urlencoded
    参数:
    - AppKey: 应用ID
    - TimeStamp: 时间戳
    - Sign: 签名
    - Method: 回调方法
    - Data: 业务数据(JSON字符串)
    """
    from .ylhapi import YLHCallbackHandler
    
    try:
        # 解析表单数据
        form_data = {}
        if request.content_type == 'application/x-www-form-urlencoded':
            form_data = request.POST.dict()
        elif request.content_type == 'application/json':
            # 兼容JSON格式
            form_data = json.loads(request.body.decode('utf-8'))
        else:
            form_data = request.POST.dict()
        
        logger.info(f"YLH Callback received: Method={form_data.get('Method')}, AppKey={form_data.get('AppKey')}")
        
        # 创建回调处理器
        handler = YLHCallbackHandler.from_settings()
        
        # 路由并处理回调
        response_data = handler.route_callback(form_data)
        
        # 记录响应
        logger.info(f"YLH Callback response: {response_data}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"YLH Callback error: {str(e)}", exc_info=True)
        return JsonResponse({
            "success": False,
            "code": "error",
            "description": f"系统错误: {str(e)}",
            "timeStamp": timezone.now().strftime("%Y%m%d%H%M%S"),
            "data": {}
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def ylh_create_order_view(request):
    """
    创建易理货订单
    
    POST /api/integrations/ylh/orders/create/
    
    请求体:
    {
        "sourceSystem": "TEST_SYSTEM",
        "shopName": "测试店铺",
        "sellerCode": "8800539012",
        "consigneeName": "张三",
        "consigneeMobile": "13900139000",
        "onlineNo": "HMM202300001",
        "soId": "SUB202300001",
        "totalQty": 1,
        "totalAmt": 1999.98,
        "createTime": 1748931496000,
        "province": "江苏省",
        "city": "南京市",
        "area": "鼓楼区",
        "detailAddress": "中山北路100号",
        "deliveryInstall": true,
        "itemList": [...]
    }
    """
    try:
        order_data = request.data
        
        # 创建API实例
        api = YLHSystemAPI.from_settings()
        
        # 创建订单
        result = api.create_order(order_data)
        
        if result:
            return Response({
                "success": True,
                "message": "订单创建成功",
                "data": result
            })
        else:
            return Response({
                "success": False,
                "message": "订单创建失败"
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Create YLH order error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def ylh_cancel_order_view(request):
    """
    取消易理货订单
    
    POST /api/integrations/ylh/orders/cancel/
    
    请求体:
    {
        "soId": "SUB202300001",
        "cancelReason": "客户要求取消",
        "sourceSystem": "TEST_SYSTEM",
        "cancelTime": 1748931496000  // 可选
    }
    """
    try:
        so_id = request.data.get('soId')
        cancel_reason = request.data.get('cancelReason')
        source_system = request.data.get('sourceSystem')
        cancel_time = request.data.get('cancelTime')
        
        if not all([so_id, cancel_reason, source_system]):
            return Response({
                "success": False,
                "message": "soId, cancelReason, sourceSystem为必填参数"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建API实例
        api = YLHSystemAPI.from_settings()
        
        # 取消订单
        result = api.cancel_order(so_id, cancel_reason, source_system, cancel_time)
        
        if result:
            return Response({
                "success": True,
                "message": "订单取消成功",
                "data": result
            })
        else:
            return Response({
                "success": False,
                "message": "订单取消失败"
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Cancel YLH order error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def ylh_update_distribution_time_view(request):
    """
    更新订单配送安装时间
    
    POST /api/integrations/ylh/orders/update-time/
    
    请求体:
    {
        "retailOrderNo": "SO.20250430.000001",
        "distributionTime": 1748931496000,  // 可选
        "installTime": 1748931496000  // 可选
    }
    """
    try:
        retail_order_no = request.data.get('retailOrderNo')
        distribution_time = request.data.get('distributionTime')
        install_time = request.data.get('installTime')
        
        if not retail_order_no:
            return Response({
                "success": False,
                "message": "retailOrderNo为必填参数"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建API实例
        api = YLHSystemAPI.from_settings()
        
        # 更新时间
        result = api.update_distribution_time(retail_order_no, distribution_time, install_time)
        
        if result:
            return Response({
                "success": True,
                "message": "时间更新成功",
                "data": result
            })
        else:
            return Response({
                "success": False,
                "message": "时间更新失败"
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Update YLH distribution time error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def ylh_get_delivery_images_view(request):
    """
    获取配送安装照片
    
    GET /api/integrations/ylh/orders/delivery-images/?order_no=SO.20250430.000001
    """
    try:
        order_no = request.query_params.get('order_no')
        
        if not order_no:
            return Response({
                "success": False,
                "message": "order_no参数必填"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建API实例
        api = YLHSystemAPI.from_settings()
        
        # 获取照片
        result = api.get_delivery_images(order_no)
        
        if result is not None:
            return Response({
                "success": True,
                "message": "获取成功",
                "data": result
            })
        else:
            return Response({
                "success": False,
                "message": "获取失败"
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Get YLH delivery images error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def ylh_get_logistics_view(request):
    """
    查询物流信息
    
    POST /api/integrations/ylh/orders/logistics/
    
    请求体:
    {
        "orderCodes": ["SO.20250514.014572", "SO.20250514.014573"]
    }
    """
    try:
        order_codes = request.data.get('orderCodes', [])
        
        if not order_codes or not isinstance(order_codes, list):
            return Response({
                "success": False,
                "message": "orderCodes必须是非空数组"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建API实例
        api = YLHSystemAPI.from_settings()
        
        # 查询物流
        result = api.get_logistics_by_order_codes(order_codes)
        
        if result is not None:
            return Response({
                "success": True,
                "message": "查询成功",
                "data": result
            })
        else:
            return Response({
                "success": False,
                "message": "查询失败"
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Get YLH logistics error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
