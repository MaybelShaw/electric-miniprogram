# 海尔API集成 - 模型适配说明

## 概述

本文档说明了为适配海尔API而对数据模型进行的修改。

## 修改的模型

### 1. Product (商品模型) - catalog/models.py

#### 新增字段

**海尔API相关字段：**
- `product_code` (CharField, 50, unique): 海尔产品编码，如 "GA0SZC00U"
- `product_model` (CharField, 100): 海尔产品型号，如 "EC6001-HT3"
- `product_group` (CharField, 100): 海尔产品组，如 "电热水器"

**价格相关字段（海尔API）：**
- `supply_price` (DecimalField): 普通供价
- `invoice_price` (DecimalField): 开票价
- `market_price` (DecimalField): 市场价
- `stock_rebate` (DecimalField): 直扣
- `rebate_money` (DecimalField): 台返

**图片字段（海尔API）：**
- `product_image_url` (URLField, 500): 海尔主图URL
- `product_page_urls` (JSONField): 海尔拉页URL列表

**状态字段（海尔API）：**
- `is_sales` (CharField, 1): 海尔是否可采（1可采，0不可采）
- `no_sales_reason` (CharField, 200): 不可采原因

**库存信息（海尔API）：**
- `warehouse_code` (CharField, 50): 库位编码
- `warehouse_grade` (CharField, 1): 仓库等级（0本级仓/1上级仓）

**同步时间：**
- `last_sync_at` (DateTimeField): 最后同步时间

#### 新增方法

```python
@classmethod
def sync_from_haier(cls, haier_data: dict, category=None, brand=None):
    """从海尔API数据同步商品"""
    
def update_stock_from_haier(self, stock_data: dict):
    """从海尔API更新库存信息"""
    
@property
def display_price(self):
    """显示价格（优先使用供价）"""
    
@property
def is_available_from_haier(self):
    """是否从海尔可采"""
```

#### 新增索引

```python
models.Index(fields=['product_code']),
models.Index(fields=['is_sales']),
```

### 2. Order (订单模型) - orders/models.py

#### 新增字段

**金额字段：**
- `discount_amount` (DecimalField, default=0): 折扣金额
- `actual_amount` (DecimalField, default=0): 实付金额

**地址详细字段：**
- `snapshot_province` (CharField, 50): 省
- `snapshot_city` (CharField, 50): 市
- `snapshot_district` (CharField, 50): 区
- `snapshot_town` (CharField, 50): 县/街道

**海尔订单相关字段：**
- `haier_order_no` (CharField, 100): 海尔订单号（ExtOrderNo）
- `haier_so_id` (CharField, 100, unique): 海尔子订单号（soId）
- `haier_status` (CharField, 20): 海尔订单状态

**配送安装信息：**
- `distribution_time` (DateTimeField): 配送时间
- `install_time` (DateTimeField): 安装时间
- `is_delivery_install` (BooleanField): 是否送装一体
- `is_government_order` (BooleanField): 是否国补订单

**物流信息：**
- `logistics_company` (CharField, 100): 物流公司
- `logistics_no` (CharField, 100): 物流单号
- `delivery_record_code` (CharField, 100): 发货单号
- `sn_code` (CharField, 100): SN码

**配送照片：**
- `delivery_images` (JSONField): 配送安装照片URL列表

**取消信息：**
- `cancel_reason` (CharField, 200): 取消原因
- `cancelled_at` (DateTimeField): 取消时间

#### 新增方法

```python
def prepare_haier_order_data(self, source_system='YOUR_SYSTEM', shop_name='默认店铺'):
    """准备推送到海尔的订单数据"""
    
def update_from_haier_callback(self, callback_data: dict):
    """从海尔回调更新订单状态"""
    
def update_logistics_info(self, logistics_data: dict):
    """更新物流信息"""
```

#### 新增索引

```python
models.Index(fields=['haier_order_no']),
models.Index(fields=['haier_so_id']),
```

## 数据映射关系

### 商品数据映射

| 海尔API字段 | 本地模型字段 | 说明 |
|------------|-------------|------|
| productCode | product_code | 产品编码 |
| productModel | product_model | 型号 |
| productGroupNamd | product_group | 产品组 |
| productBrandName | brand.name | 品牌名称 |
| productImageUrl | product_image_url | 主图URL |
| productLageUrls | product_page_urls | 拉页URL列表 |
| isSales | is_sales | 是否可采 |
| noSalesReason | no_sales_reason | 不可采原因 |
| supplyPrice | supply_price | 普通供价 |
| invoicePrice | invoice_price | 开票价 |
| stockRebatePolicy | stock_rebate | 直扣 |
| rebateMoney | rebate_money | 台返 |

### 订单数据映射

| 海尔API字段 | 本地模型字段 | 说明 |
|------------|-------------|------|
| sourceSystem | - | 订单来源（配置） |
| shopName | - | 店铺名称（配置） |
| sellerCode | - | 客户八码（配置） |
| consigneeName | snapshot_contact_name | 收货人姓名 |
| consigneeMobile | snapshot_phone | 收货人手机号 |
| onlineNo | order_number | 平台订单号 |
| soId | haier_so_id | 子订单号 |
| remark | note | 备注 |
| totalQty | quantity | 订单总数量 |
| totalAmt | total_amount | 订单总金额 |
| createTime | created_at | 订单创建时间 |
| province | snapshot_province | 省 |
| city | snapshot_city | 市 |
| area | snapshot_district | 区 |
| town | snapshot_town | 县 |
| detailAddress | snapshot_address | 详细地址 |
| distributionTime | distribution_time | 配送时间 |
| installTime | install_time | 安装时间 |
| governmentOrder | is_government_order | 是否国补订单 |
| deliveryInstall | is_delivery_install | 是否送装一体 |
| itemList[].productCode | product.product_code | 商品编码 |
| itemList[].itemQty | quantity | 商品数量 |
| itemList[].retailPrice | product.market_price | 零售价 |
| itemList[].discountAmount | discount_amount | 折扣金额 |
| itemList[].actualPrice | actual_amount | 实际成交价 |

### 订单回调数据映射

| 海尔回调字段 | 本地模型字段 | 说明 |
|-------------|-------------|------|
| ExtOrderNo | haier_order_no | 海尔订单号 |
| PlatformOrderNo | order_number | 客户平台订单号 |
| State | haier_status | 状态（1成功，0失败） |
| FailMsg | note | 失败原因 |

### 物流数据映射

| 海尔API字段 | 本地模型字段 | 说明 |
|------------|-------------|------|
| orderCode | order_number | 订单编码 |
| deliveryRecordCode | delivery_record_code | 发货单号 |
| logisticsCompany | logistics_company | 物流公司 |
| logisticsNo | logistics_no | 物流单号 |
| snCode | sn_code | SN码 |

## 使用示例

### 1. 从海尔API同步商品

```python
from catalog.models import Product, Category, Brand
from integrations.haierapi import HaierAPI

# 初始化海尔API
haier_api = HaierAPI(config)

# 查询商品
products_data = haier_api.get_products(product_codes=['GA0SZC00U'])

# 同步到本地
for product_data in products_data:
    # 获取价格信息
    prices = haier_api.get_product_prices([product_data['productCode']])
    if prices:
        product_data.update(prices[0])
    
    # 同步商品
    category = Category.objects.get(name='电热水器')
    brand = Brand.objects.get(name='海尔')
    product = Product.sync_from_haier(product_data, category, brand)
    print(f"同步商品: {product.name}")
```

### 2. 更新商品库存

```python
from catalog.models import Product
from integrations.haierapi import HaierAPI

# 初始化海尔API
haier_api = HaierAPI(config)

# 查询库存
product = Product.objects.get(product_code='GA0SZC00U')
stock_data = haier_api.check_stock(product.product_code, county_code='110101')

if stock_data:
    product.update_stock_from_haier(stock_data)
    print(f"更新库存: {product.name} - {product.stock}件")
```

### 3. 创建订单并推送到海尔

```python
from orders.models import Order
from integrations.ylhapi import YLHApi

# 创建本地订单
order = Order.objects.create(
    user=user,
    product=product,
    quantity=1,
    total_amount=product.price,
    actual_amount=product.price,
    snapshot_contact_name='张三',
    snapshot_phone='13800138000',
    snapshot_province='北京市',
    snapshot_city='北京市',
    snapshot_district='朝阳区',
    snapshot_address='建国路88号',
)

# 准备海尔订单数据
haier_order_data = order.prepare_haier_order_data(
    source_system='YOUR_SYSTEM',
    shop_name='XX旗舰店'
)

# 推送到海尔（需要使用易理货系统API）
ylh_api = YLHApi(config)
result = ylh_api.create_order(haier_order_data)

if result:
    print(f"订单推送成功: {order.order_number}")
```

### 4. 处理海尔订单回调

```python
from orders.models import Order

# 接收海尔回调数据
callback_data = {
    'ExtOrderNo': 'SO.20250101.000001',
    'PlatformOrderNo': 'ORDER123456',
    'State': 1,
    'FailMsg': ''
}

# 更新订单状态
order = Order.objects.get(order_number=callback_data['PlatformOrderNo'])
order.update_from_haier_callback(callback_data)

print(f"订单状态更新: {order.haier_status}")
```

### 5. 查询并更新物流信息

```python
from orders.models import Order
from integrations.haierapi import HaierAPI

# 初始化海尔API
haier_api = HaierAPI(config)

# 查询物流信息
order = Order.objects.get(haier_order_no='SO.20250101.000001')
logistics_info = haier_api.get_logistics_info(order.haier_order_no)

if logistics_info:
    # 更新物流信息
    order.update_logistics_info({
        'logisticsCompany': '顺丰速运',
        'logisticsNo': 'SF1234567890',
        'deliveryRecordCode': 'SO.20250101.000001.F1',
        'snCode': 'SN123456789'
    })
    print(f"物流信息更新: {order.logistics_company} - {order.logistics_no}")
```

## 数据库迁移

执行以下命令创建并应用迁移：

```bash
# 创建迁移文件
python manage.py makemigrations catalog orders --name add_haier_fields

# 应用迁移
python manage.py migrate
```

## 配置要求

在 `settings.py` 或环境变量中添加以下配置：

```python
# 海尔API配置
HAIER_CLIENT_ID = 'your_client_id'
HAIER_CLIENT_SECRET = 'your_client_secret'
HAIER_TOKEN_URL = 'https://openplat-test.haier.net/oauth2/auth'
HAIER_BASE_URL = 'https://openplat-test.haier.net'
HAIER_CUSTOMER_CODE = '8800633175'  # 售达方编码
HAIER_SEND_TO_CODE = '8800633175'   # 送达方编码
HAIER_SUPPLIER_CODE = '1001'         # 供货方编码
HAIER_PASSWORD = 'your_password'     # 约定密码
HAIER_SELLER_PASSWORD = 'your_password'  # 客户密码

# 易理货系统配置（用于订单推送）
YLH_USERNAME = 'your_username'
YLH_PASSWORD = 'your_password'
YLH_BASE_URL = 'http://dev.ylhtest.com'
```

## 注意事项

1. **product_code唯一性**：海尔产品编码必须唯一，用于关联海尔商品
2. **haier_so_id唯一性**：海尔子订单号必须唯一，用于防止重复推送
3. **价格优先级**：显示价格时优先使用supply_price（供价），其次使用price
4. **库存同步**：建议定期同步海尔库存信息，确保数据准确
5. **订单推送**：订单推送到海尔需要使用易理货系统的token，不是OAuth2.0的token
6. **时间格式**：海尔API使用毫秒时间戳，需要进行转换
7. **地址信息**：订单推送时需要完整的省市区县地址信息
8. **送装一体**：如果配送时间和安装时间相同，需要设置is_delivery_install为True

## 相关文档

- [海尔API文档](../haier_api.md)
- [集成模块文档](05_INTEGRATIONS_MODULE.md)
- [订单模块文档](04_ORDERS_MODULE.md)
- [商品目录模块文档](03_CATALOG_MODULE.md)

## 更新记录

- 2025-01-01: 初始版本，添加海尔API适配字段和方法
