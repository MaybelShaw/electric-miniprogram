# 公共工具模块文档 (common)

## 模块概述

公共工具模块提供了整个系统通用的功能组件，包括异常处理、权限控制、分页器、地址解析、日志配置等。

## 异常处理 (exceptions.py)

### 自定义业务异常

#### BusinessException
所有业务逻辑异常的基类

```python
from common.exceptions import BusinessException

class CustomError(BusinessException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '自定义错误'
    default_code = 'custom_error'
    error_code = 'CUSTOM_ERROR'
```

#### InsufficientStockError
库存不足异常

```python
from common.exceptions import InsufficientStockError

if product.stock < quantity:
    raise InsufficientStockError(
        detail=f'库存不足，当前库存: {product.stock}'
    )
```

**HTTP状态码：** 409 Conflict

#### InvalidOrderStatusError
订单状态转换不合法异常

```python
from common.exceptions import InvalidOrderStatusError

if order.status == 'cancelled':
    raise InvalidOrderStatusError(
        detail='已取消的订单不能发货'
    )
```

**HTTP状态码：** 400 Bad Request

#### PaymentVerificationError
支付验证失败异常

```python
from common.exceptions import PaymentVerificationError

if not verify_signature(data, signature):
    raise PaymentVerificationError(
        detail='支付签名验证失败'
    )
```

**HTTP状态码：** 400 Bad Request

#### DuplicatePaymentError
重复支付异常

```python
from common.exceptions import DuplicatePaymentError

if payment.status == 'succeeded':
    raise DuplicatePaymentError(
        detail='该支付已处理'
    )
```

**HTTP状态码：** 409 Conflict

#### InvalidPaymentAmountError
支付金额不匹配异常

```python
from common.exceptions import InvalidPaymentAmountError

if order.total_amount != payment_amount:
    raise InvalidPaymentAmountError(
        detail=f'支付金额不匹配，应支付: {order.total_amount}'
    )
```

**HTTP状态码：** 400 Bad Request

#### SupplierAPIError
供应商API调用失败异常

```python
from common.exceptions import SupplierAPIError

try:
    supplier.get_products()
except requests.RequestException as e:
    raise SupplierAPIError(
        detail=f'供应商API调用失败: {str(e)}'
    )
```

**HTTP状态码：** 502 Bad Gateway

#### SupplierAuthenticationError
供应商认证失败异常

```python
from common.exceptions import SupplierAuthenticationError

if not supplier.authenticate():
    raise SupplierAuthenticationError(
        detail='供应商认证失败'
    )
```

**HTTP状态码：** 401 Unauthorized

#### ResourceConflictError
资源冲突异常

```python
from common.exceptions import ResourceConflictError

if brand.products.exists():
    raise ResourceConflictError(
        detail='该品牌有关联商品，无法删除'
    )
```

**HTTP状态码：** 409 Conflict

#### InvalidFileError
文件验证失败异常

```python
from common.exceptions import InvalidFileError

if not is_valid_image(file):
    raise InvalidFileError(
        detail='文件格式不支持'
    )
```

**HTTP状态码：** 400 Bad Request

#### RateLimitExceededError
请求频率超限异常

```python
from common.exceptions import RateLimitExceededError

raise RateLimitExceededError(
    detail='请求过于频繁，请稍后再试'
)
```

**HTTP状态码：** 429 Too Many Requests

### 统一异常处理器

```python
def custom_exception_handler(exc, context):
    """
    统一异常处理器
    
    特性：
    - 统一响应格式
    - 环境感知（生产环境隐藏敏感信息）
    - 完整日志记录
    - 自动HTTP状态码
    """
```

**响应格式：**
```json
{
    "success": false,
    "code": 400,
    "message": "错误信息",
    "error_code": "BUSINESS_ERROR",
    "errors": {
        "field": ["错误详情"]
    }
}
```

**配置方式：**
```python
# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
}
```

### 异常日志中间件

```python
class ExceptionLoggingMiddleware:
    """
    捕获并记录未处理的异常
    
    配置方式：
    MIDDLEWARE = [
        ...
        'common.exceptions.ExceptionLoggingMiddleware',
        ...
    ]
    """
```

## 权限控制 (permissions.py)

### IsOwnerOrAdmin
资源所有者或管理员权限

```python
from common.permissions import IsOwnerOrAdmin

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrAdmin]
```

**规则：**
- 管理员（is_staff=True）可访问所有对象
- 普通用户只能访问自己的对象
- 对象必须有user属性

### IsAdminOrReadOnly
管理员可写，所有人可读

```python
from common.permissions import IsAdminOrReadOnly

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
```

**规则：**
- GET、HEAD、OPTIONS：所有用户
- POST、PUT、PATCH、DELETE：仅管理员

### IsAdmin
仅管理员权限

```python
from common.permissions import IsAdmin

class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
```

**规则：**
- 仅is_staff=True的用户可访问

### EnvironmentAwarePermission
环境感知权限

```python
from common.permissions import EnvironmentAwarePermission

class SensitiveViewSet(viewsets.ModelViewSet):
    permission_classes = [EnvironmentAwarePermission]
```

**规则：**
- 开发环境：所有认证用户
- 生产环境：需要明确权限检查

### IsAuthenticatedOrReadOnly
认证用户可写，所有人可读

```python
from common.permissions import IsAuthenticatedOrReadOnly

class CommentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
```

**规则：**
- GET、HEAD、OPTIONS：所有用户（包括未认证）
- POST、PUT、PATCH、DELETE：需要认证

## 分页器 (pagination.py)

### StandardResultsSetPagination
标准分页器

```python
from common.pagination import StandardResultsSetPagination

class ProductViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
```

**配置：**
- 默认每页：20条
- 最大每页：100条
- 页码参数：page
- 页大小参数：page_size

**响应格式：**
```json
{
    "count": 100,
    "next": "http://api.example.com/products/?page=2",
    "previous": null,
    "results": [...]
}
```

### LargeResultsSetPagination
大数据集分页器

```python
from common.pagination import LargeResultsSetPagination

class OrderViewSet(viewsets.ModelViewSet):
    pagination_class = LargeResultsSetPagination
```

**配置：**
- 默认每页：50条
- 最大每页：200条

## 地址解析 (address_parser.py)

### AddressParser类

基于JioNLP实现的智能地址解析器

#### parse_address(address_text)
解析地址文本

```python
from common.address_parser import address_parser

result = address_parser.parse_address(
    "北京市朝阳区建国路88号SOHO现代城"
)

# 返回值
{
    'province': '北京市',
    'city': '北京市',
    'district': '朝阳区',
    'detail': '建国路88号SOHO现代城',
    'success': True,
    'message': '地址识别成功'
}
```

**支持格式：**
- 完整地址：北京市朝阳区建国路88号
- 简写地址：北京朝阳建国路88号
- 带邮编：100000北京市朝阳区建国路88号
- 多种分隔符：北京市-朝阳区-建国路88号

#### validate_address(province, city, district)
验证省市区是否有效

```python
is_valid = address_parser.validate_address(
    province='北京市',
    city='北京市',
    district='朝阳区'
)
```

#### extract_phone(text)
从文本中提取手机号

```python
phone = address_parser.extract_phone(
    "联系人：张三，电话：13800138000"
)
# 返回: '13800138000'
```

#### extract_id_card(text)
从文本中提取身份证号

```python
id_card = address_parser.extract_id_card(
    "身份证：110101199001011234"
)
# 返回: '110101199001011234'
```

### 在视图中使用

```python
from rest_framework.decorators import action
from common.address_parser import address_parser

class AddressViewSet(viewsets.ModelViewSet):
    
    @action(detail=False, methods=['post'])
    def parse(self, request):
        """解析地址"""
        address_text = request.data.get('address')
        result = address_parser.parse_address(address_text)
        return Response(result)
```

## 日志配置 (logging_config.py)

### 日志级别

- DEBUG: 详细调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

### 日志处理器

#### console
控制台输出

```python
logger.info("这是一条信息")
```

#### file
文件输出（logs/django.log）

- 最大文件大小：10MB
- 备份文件数：5个
- 自动轮转

#### error_file
错误日志（logs/error.log）

- 仅记录ERROR及以上级别
- 最大文件大小：10MB
- 备份文件数：5个

### 日志格式

```
[2025-01-01 12:00:00] [INFO] [module.view] Message
```

### 使用示例

```python
import logging

logger = logging.getLogger(__name__)

# 记录信息
logger.info("用户登录成功", extra={'user_id': user.id})

# 记录警告
logger.warning("库存不足", extra={'product_id': product.id})

# 记录错误
logger.error("支付失败", exc_info=True, extra={'order_id': order.id})
```

### 特定模块日志

```python
# 用户模块
logger = logging.getLogger('users')

# 订单模块
logger = logging.getLogger('orders')

# 集成模块
logger = logging.getLogger('integrations')
```

## 审计日志

### AuditLog模型

记录重要操作的审计日志

```python
from common.models import AuditLog

AuditLog.objects.create(
    user=request.user,
    action='CREATE_ORDER',
    resource_type='Order',
    resource_id=order.id,
    ip_address=request.META.get('REMOTE_ADDR'),
    user_agent=request.META.get('HTTP_USER_AGENT'),
    details={'order_no': order.order_no}
)
```

**字段说明：**
- user: 操作用户
- action: 操作类型
- resource_type: 资源类型
- resource_id: 资源ID
- ip_address: IP地址
- user_agent: 用户代理
- details: 详细信息（JSON）
- created_at: 创建时间

## 响应格式

### 成功响应

```json
{
    "success": true,
    "code": 200,
    "message": "操作成功",
    "data": {...}
}
```

### 错误响应

```json
{
    "success": false,
    "code": 400,
    "message": "错误信息",
    "error_code": "BUSINESS_ERROR",
    "errors": {...}
}
```

### 分页响应

```json
{
    "count": 100,
    "next": "http://...",
    "previous": null,
    "results": [...]
}
```

## 健康检查

### 端点

```
GET /healthz
```

### 响应

```json
{
    "status": "healthy",
    "timestamp": "2025-01-01T12:00:00Z",
    "services": {
        "database": "ok",
        "cache": "ok",
        "storage": "ok"
    }
}
```

### 检查项

- 数据库连接
- 缓存服务
- 文件存储
- 第三方API

## 工具函数

### 生成唯一编号

```python
from common.utils import generate_unique_code

order_no = generate_unique_code('ORDER')
# 返回: ORDER202501011230001234
```

### 格式化金额

```python
from common.utils import format_amount

formatted = format_amount(1234.56)
# 返回: '1,234.56'
```

### 验证手机号

```python
from common.utils import validate_phone

is_valid = validate_phone('13800138000')
# 返回: True
```

### 验证身份证号

```python
from common.utils import validate_id_card

is_valid = validate_id_card('110101199001011234')
# 返回: True
```

## 最佳实践

### 1. 异常处理
- 使用自定义业务异常
- 提供清晰的错误信息
- 记录完整的错误日志

### 2. 权限控制
- 选择合适的权限类
- 对象级权限检查
- 环境感知权限

### 3. 日志记录
- 使用合适的日志级别
- 记录关键操作
- 包含上下文信息

### 4. 地址解析
- 验证解析结果
- 处理解析失败
- 提供手动修正

### 5. 分页
- 选择合适的分页器
- 限制最大页大小
- 优化查询性能
