# 海尔API集成模块文档 (integrations)

## 模块概述

集成模块负责与海尔供应商API和易理货系统API的对接，实现商品查询、价格查询、库存查询、订单创建、物流查询等功能。

## 架构设计

### 双API系统

系统集成了两套独立的API：

1. **海尔OAuth2.0 API** - 用于商品信息查询
   - 商品查询
   - 价格查询
   - 库存查询
   - 物流查询
   - 余额查询

2. **易理货系统API** - 用于订单操作
   - 订单创建
   - 订单取消
   - 订单改约
   - 配送照片查询
   - 物流单号查询

### 认证机制

#### 海尔OAuth2.0认证
```python
# 认证流程
POST /oauth2/auth
Content-Type: application/json

{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "grant_type": "client_credentials"
}

# 响应
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

#### 易理货系统认证
```python
# 认证流程
POST /oauth/token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=xxx&password=xxx

# 响应
{
  "access_token": "xxx",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## HaierAPI类

### 初始化配置

```python
from integrations.haierapi import HaierAPI

config = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'token_url': 'https://openplat.haier.net/oauth2/auth',
    'base_url': 'https://openplat.haier.net',
    'customer_code': '8800633175',
    'send_to_code': '8800633175',
    'supplier_code': '1001',
    'password': 'your_password',
    'seller_password': 'your_password'
}

api = HaierAPI(config)
```

### 核心方法

#### 1. authenticate()
OAuth2.0认证并获取访问令牌

**返回值：**
- `bool`: 认证成功返回True

**特性：**
- 自动管理token过期时间
- 提前10分钟刷新token
- 失败时记录详细日志


#### 2. get_products(product_codes, **filters)
批量查询可采商品

**参数：**
- `product_codes`: 产品编码列表（最多20个）
- `search_type`: 查询类型（默认PTJSH）

**返回值：**
```python
[
    {
        "productCode": "GA0SZC00U",
        "productModel": "BCD-215STPH",
        "productGroupName": "冰箱",
        "productBrandName": "海尔",
        "productImageUrl": "http://...",
        "productLageUrls": ["http://..."],
        "isSales": 1,
        "noSalesReason": ""
    }
]
```

**使用示例：**
```python
# 查询单个商品
products = api.get_products(product_codes=["GA0SZC00U"])

# 查询多个商品
products = api.get_products(
    product_codes=["GA0SZC00U", "GA0SZC00V"],
    search_type="PTJSH"
)
```

#### 3. get_product_prices(product_codes)
查询商品价格

**参数：**
- `product_codes`: 产品编码列表（最多20个）

**返回值：**
```python
[
    {
        "productCode": "GA0SZC00U",
        "supplyPrice": 2999.00,
        "invoicePrice": 3299.00,
        "stockRebatePolicy": 100.00,
        "rebateMoney": 50.00,
        "reason": "",
        "isSales": 1
    }
]
```

**价格说明：**
- `supplyPrice`: 普通供价（采购价）
- `invoicePrice`: 开票价（含税价）
- `stockRebatePolicy`: 直扣（直接扣减金额）
- `rebateMoney`: 台返（按台返还金额）

#### 4. get_product_detail(product_code)
获取商品详情（包含价格信息）

**参数：**
- `product_code`: 商品代码

**返回值：**
```python
{
    "productCode": "GA0SZC00U",
    "productModel": "BCD-215STPH",
    "productGroupName": "冰箱",
    "productBrandName": "海尔",
    "productImageUrl": "http://...",
    "supplyPrice": 2999.00,
    "invoicePrice": 3299.00,
    "isSales": 1
}
```

**实现逻辑：**
1. 调用get_products获取商品基本信息
2. 调用get_product_prices获取价格信息
3. 合并返回完整数据

#### 5. check_stock(product_code, county_code)
RX库存三方直连库存查询

**参数：**
- `product_code`: 商品编码
- `county_code`: 区域编码（6位国标码，默认110101北京东城区）

**返回值：**
```python
{
    "secCode": "WH001",
    "stock": 50,
    "warehouseGrade": 0,
    "timelinessData": {
        "cutTime": "18:00",
        "achieveUserOrderCut": "2025-01-02 12:00:00",
        "hour": 18,
        "isTranfer": false
    }
}
```

**字段说明：**
- `secCode`: 库位编码
- `stock`: 库存数量
- `warehouseGrade`: 0本级仓/1上级仓
- `timelinessData`: 时效信息
  - `cutTime`: 截单时间
  - `achieveUserOrderCut`: 预计送达用户时间
  - `hour`: 配送用户时效（小时）
  - `isTranfer`: 是否转运

#### 6. get_account_balance()
查询付款方余额

**返回值：**
```python
{
    "saleGroupCode": "SG001",
    "saleGroupName": "华北销售组织",
    "payerAccountCode": "8800633175",
    "payerAccountName": "测试客户",
    "payerAccountBalance": 1000000.00
}
```

#### 7. get_logistics_info(order_code, delivery_record_code, member_id)
查询物流信息

**参数：**
- `order_code`: 订单编码（必填）
- `delivery_record_code`: 发货单号（可选）
- `member_id`: 会员ID（可选）

**返回值：**
```python
{
    "getAllLogisticsInfoByOrderCode": [
        {
            "logisticsCompany": "顺丰速运",
            "logisticsNo": "SF1234567890",
            "status": "已签收",
            "traces": [
                {
                    "time": "2025-01-01 10:00:00",
                    "status": "已发货"
                }
            ]
        }
    ],
    "getStockDeliveryLogisticsRecord": [],
    "getStockDeliveryLogisticsRecordThirdparty": []
}
```

### 自动重试机制

所有API请求都支持自动重试：

```python
def _retry_request(self, func, *args, **kwargs):
    """
    带重试机制的请求执行
    
    - 最大重试次数：3次
    - 重试延迟：1秒
    - 失败时记录日志
    """
    last_error = None
    
    for attempt in range(self.max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
    
    logger.error(f"All retry attempts failed: {str(last_error)}")
    return None
```

### Token自动管理

```python
def _ensure_authenticated(self):
    """
    确保已认证，如果令牌过期则自动刷新
    
    - 检查token是否存在
    - 检查token是否过期
    - 自动刷新过期token
    """
    if not self.access_token or self._is_token_expired():
        return self.authenticate()
    return True
```

## YLHSystemAPI类

### 初始化配置

```python
from integrations.ylhapi import YLHSystemAPI

config = {
    'auth_url': 'http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token',
    'base_url': 'http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev',
    'username': 'erp',
    'password': '123qwe',
    'client_id': 'open_api_erp',
    'client_secret': '12345678'
}

api = YLHSystemAPI(config)
```

### 核心方法

#### 1. authenticate()
获取访问令牌

**认证方式：**
- Basic认证（client_id:client_secret）
- 用户名密码登录

**返回值：**
- `bool`: 认证成功返回True

#### 2. create_order(order_data)
创建订单（接收水联网订单）

**请求参数：**
```python
order_data = {
    "sourceSystem": "MINIPROGRAM",
    "shopName": "测试店铺",
    "sellerCode": "8800633175",
    "consigneeName": "张三",
    "consigneeMobile": "13800138000",
    "onlineNo": "MP202501011230001",
    "soId": "SO202501011230001",
    "remark": "请尽快发货",
    "totalQty": 2,
    "totalAmt": 5998.00,
    "createTime": 1640995200000,
    "province": "北京市",
    "city": "北京市",
    "area": "朝阳区",
    "town": "",
    "detailAddress": "建国路88号",
    "distributionTime": 1641081600000,
    "installTime": 1641168000000,
    "governmentOrder": 0,
    "deliveryInstall": 1,
    "itemList": [
        {
            "productCode": "GA0SZC00U",
            "productName": "海尔冰箱BCD-215STPH",
            "qty": 1,
            "price": 2999.00,
            "totalAmt": 2999.00
        }
    ]
}

result = api.create_order(order_data)
```

**返回值：**
```python
{
    "success": true,
    "code": 200,
    "message": "订单创建成功",
    "data": {
        "retailOrderNo": "RO202501011230001",
        "soId": "SO202501011230001"
    }
}
```

**注意事项：**
- `soId`必须唯一
- 时间戳使用毫秒
- 配送/安装时间的时分秒必须为23:59:59

#### 3. cancel_order(so_id, cancel_reason, source_system)
取消订单

**参数：**
- `so_id`: 子订单号
- `cancel_reason`: 取消原因
- `source_system`: 订单来源系统

**使用示例：**
```python
result = api.cancel_order(
    so_id="SO202501011230001",
    cancel_reason="用户取消",
    source_system="MINIPROGRAM"
)
```

#### 4. update_distribution_time(retail_order_no, distribution_time, install_time)
订单改约（更新配送安装时间）

**参数：**
- `retail_order_no`: 巨商汇订单号
- `distribution_time`: 配送时间（时间戳，时分秒必须为23:59:59）
- `install_time`: 安装时间（时间戳，时分秒必须为23:59:59）

**使用示例：**
```python
result = api.update_distribution_time(
    retail_order_no="RO202501011230001",
    distribution_time=1641168000000,
    install_time=1641254400000
)
```

#### 5. get_delivery_images(order_no)
获取配送安装照片

**参数：**
- `order_no`: 订单中台订单号

**返回值：**
```python
[
    {
        "imageType": "配送照片",
        "imageUrl": "http://...",
        "uploadTime": "2025-01-01 12:00:00"
    },
    {
        "imageType": "安装照片",
        "imageUrl": "http://...",
        "uploadTime": "2025-01-01 14:00:00"
    }
]
```

#### 6. get_logistics_by_order_codes(order_codes)
通过SO单号查询物流单号、物流公司、SN码

**参数：**
- `order_codes`: SO单号列表（最多100个）

**返回值：**
```python
[
    {
        "orderCode": "SO202501011230001",
        "deliveryRecordCode": "DR202501011230001",
        "logisticsList": [
            {
                "logisticsCompany": "顺丰速运",
                "logisticsNo": "SF1234567890",
                "snCode": "SN123456"
            }
        ]
    }
]
```

## Django集成

### 视图集成

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from integrations.haierapi import HaierAPI
from integrations.ylhapi import YLHSystemAPI
from django.conf import settings

class ProductViewSet(viewsets.ModelViewSet):
    
    @action(detail=False, methods=['post'])
    def sync_from_haier(self, request):
        """从海尔同步商品"""
        # 初始化API
        api = HaierAPI(settings.HAIER_API_CONFIG)
        
        # 获取商品列表
        product_codes = request.data.get('product_codes', [])
        products = api.get_products(product_codes)
        
        # 同步到数据库
        for product_data in products:
            Product.objects.update_or_create(
                sku=product_data['productCode'],
                defaults={
                    'name': product_data['productModel'],
                    'brand': product_data['productBrandName'],
                    # ...
                }
            )
        
        return Response({'message': f'同步了{len(products)}个商品'})
```

### 订单创建集成

```python
class OrderViewSet(viewsets.ModelViewSet):
    
    def perform_create(self, serializer):
        """创建订单并推送到易理货系统"""
        # 保存订单
        order = serializer.save()
        
        # 准备订单数据
        order_data = {
            "sourceSystem": "MINIPROGRAM",
            "sellerCode": settings.HAIER_API_CONFIG['customer_code'],
            "consigneeName": order.shipping_address['contact_name'],
            "consigneeMobile": order.shipping_address['phone'],
            "onlineNo": order.order_no,
            "soId": order.order_no,
            "totalQty": sum(item.quantity for item in order.items.all()),
            "totalAmt": float(order.final_amount),
            "createTime": int(order.created_at.timestamp() * 1000),
            # ...
        }
        
        # 推送到易理货系统
        api = YLHSystemAPI(settings.YLH_API_CONFIG)
        result = api.create_order(order_data)
        
        if result and result.get('success'):
            # 保存巨商汇订单号
            order.external_order_no = result['data']['retailOrderNo']
            order.save()
```

## 配置管理

### 环境变量配置

```python
# .env
HAIER_CLIENT_ID=your_client_id
HAIER_CLIENT_SECRET=your_client_secret
HAIER_TOKEN_URL=https://openplat.haier.net/oauth2/auth
HAIER_BASE_URL=https://openplat.haier.net
HAIER_CUSTOMER_CODE=8800633175
HAIER_PASSWORD=your_password

YLH_AUTH_URL=http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token
YLH_BASE_URL=http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev
YLH_USERNAME=erp
YLH_PASSWORD=123qwe
```

### Settings配置

```python
# settings.py
HAIER_API_CONFIG = {
    'client_id': env('HAIER_CLIENT_ID'),
    'client_secret': env('HAIER_CLIENT_SECRET'),
    'token_url': env('HAIER_TOKEN_URL'),
    'base_url': env('HAIER_BASE_URL'),
    'customer_code': env('HAIER_CUSTOMER_CODE'),
    'send_to_code': env('HAIER_CUSTOMER_CODE'),
    'supplier_code': '1001',
    'password': env('HAIER_PASSWORD'),
    'seller_password': env('HAIER_PASSWORD'),
}

YLH_API_CONFIG = {
    'auth_url': env('YLH_AUTH_URL'),
    'base_url': env('YLH_BASE_URL'),
    'username': env('YLH_USERNAME'),
    'password': env('YLH_PASSWORD'),
}
```

## 同步日志

### 日志记录

```python
import logging

logger = logging.getLogger('integrations')

# 记录API调用
logger.info(f"Calling Haier API: get_products({product_codes})")

# 记录成功
logger.info(f"Successfully fetched {len(products)} products")

# 记录错误
logger.error(f"Failed to authenticate: {str(e)}", exc_info=True)
```

### 日志配置

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'integrations_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/integrations.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'integrations': {
            'handlers': ['integrations_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

## 错误处理

### 自定义异常

```python
from common.exceptions import SupplierAPIError, SupplierAuthenticationError

# 认证失败
if not api.authenticate():
    raise SupplierAuthenticationError(detail='海尔API认证失败')

# API调用失败
products = api.get_products(product_codes)
if products is None:
    raise SupplierAPIError(detail='获取商品信息失败')
```

### 错误重试

```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def sync_product_with_retry(product_code):
    """带重试的商品同步"""
    api = HaierAPI(settings.HAIER_API_CONFIG)
    product = api.get_product_detail(product_code)
    
    if not product:
        raise Exception("Failed to fetch product")
    
    return product
```

## 性能优化

### 批量查询

```python
# 不推荐：逐个查询
for code in product_codes:
    product = api.get_product_detail(code)

# 推荐：批量查询
products = api.get_products(product_codes)
prices = api.get_product_prices(product_codes)
```

### 缓存策略

```python
from django.core.cache import cache

def get_product_with_cache(product_code):
    """带缓存的商品查询"""
    cache_key = f'haier_product_{product_code}'
    
    # 尝试从缓存获取
    product = cache.get(cache_key)
    if product:
        return product
    
    # 从API获取
    api = HaierAPI(settings.HAIER_API_CONFIG)
    product = api.get_product_detail(product_code)
    
    # 缓存15分钟
    if product:
        cache.set(cache_key, product, 900)
    
    return product
```

## 测试

### 单元测试

```python
from django.test import TestCase
from unittest.mock import Mock, patch

class HaierAPITestCase(TestCase):
    
    def setUp(self):
        self.config = {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            # ...
        }
        self.api = HaierAPI(self.config)
    
    @patch('requests.post')
    def test_authenticate_success(self, mock_post):
        """测试认证成功"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'token': 'test_token',
            'expires_in': 3600
        }
        
        result = self.api.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(self.api.access_token, 'test_token')
    
    @patch('requests.post')
    def test_get_products(self, mock_post):
        """测试获取商品"""
        self.api.access_token = 'test_token'
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'data': [{'productCode': 'GA0SZC00U'}]
        }
        
        products = self.api.get_products(['GA0SZC00U'])
        
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['productCode'], 'GA0SZC00U')
```

## 最佳实践

### 1. Token管理
- 使用自动刷新机制
- 提前10分钟刷新token
- 失败时记录详细日志

### 2. 错误处理
- 使用自定义异常
- 实现自动重试
- 记录完整错误信息

### 3. 性能优化
- 批量查询代替单个查询
- 使用缓存减少API调用
- 异步处理耗时操作

### 4. 安全性
- 敏感信息使用环境变量
- 不在日志中记录密码
- 使用HTTPS通信

### 5. 监控告警
- 记录API调用次数
- 监控响应时间
- 设置失败率告警
