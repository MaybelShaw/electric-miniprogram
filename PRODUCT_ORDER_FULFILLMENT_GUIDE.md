# 产品上架-下单-发货完整流程指南

本文档详细说明非海尔产品和海尔产品的完整业务流程，包括上架、下单、支付、发货和售后的所有环节。

---

## 目录

1. [产品类型说明](#产品类型说明)
2. [非海尔产品流程](#非海尔产品流程)
3. [海尔产品流程](#海尔产品流程)
4. [流程对比](#流程对比)
5. [关键差异](#关键差异)
6. [数据库字段说明](#数据库字段说明)
7. [API接口说明](#api接口说明)

---

## 产品类型说明

### 非海尔产品
- **定义**：`product_code` 字段为空（NULL）的商品
- **特点**：自营商品，库存和发货由平台自行管理
- **示例**：普通家电、配件、自有品牌商品

### 海尔产品
- **定义**：`product_code` 字段有值的商品
- **特点**：海尔供应链商品，需要对接海尔/易理货系统
- **示例**：海尔冰箱、洗衣机、空调等

---

## 非海尔产品流程

### 1. 产品上架

#### 1.1 商户后台操作

**位置**：merchant-admin → 商品管理 → 添加商品

**必填字段**：
- 商品名称
- 商品分类
- 品牌
- 价格
- 库存数量
- 商品图片

**可选字段**：
- 商品描述
- 详情图片
- 市场价
- 是否上架

**注意**：不填写"海尔产品编码"字段

#### 1.2 数据库记录
```sql
INSERT INTO catalog_product (
    name, category_id, brand_id, price, stock,
    product_code,  -- NULL (非海尔产品)
    is_active, created_at
) VALUES (
    '普通冰箱', 1, 1, 2999.00, 100,
    NULL,
    TRUE, NOW()
);
```

#### 1.3 前端展示
- 用户在小程序首页看到商品
- 商品卡片显示：名称、价格、图片
- 点击进入商品详情页

---

### 2. 用户下单

#### 2.1 小程序操作流程


```
1. 浏览商品 → 选择商品
2. 点击"立即购买"或"加入购物车"
3. 选择收货地址
4. 确认订单信息
5. 提交订单
```

#### 2.2 API调用
```http
POST /api/orders/
Content-Type: application/json

{
  "product_id": 1,
  "address_id": 1,
  "quantity": 1,
  "note": "请尽快发货"
}
```

#### 2.3 后端处理
```python
# orders/services.py - create_order()
1. 验证商品存在且有库存
2. 验证地址属于当前用户
3. 计算订单金额（应用折扣）
4. 创建订单记录（状态：pending）
5. 快照收货地址信息
6. 返回订单详情
```

#### 2.4 订单状态
- **初始状态**：`pending`（待支付）
- **订单号**：自动生成（时间戳 + 随机数）
- **is_haier_order**：`False`（序列化器自动判断）

---

### 3. 支付流程

#### 3.1 创建支付


```http
POST /api/orders/{order_id}/pay/
{
  "method": "wechat"
}
```

**后端处理**：
1. 创建支付记录（状态：init）
2. 调用微信支付API
3. 返回支付参数给小程序
4. 设置支付过期时间（默认30分钟）

#### 3.2 支付成功
```http
POST /api/orders/{order_id}/confirm_payment/
```

**后端处理**：
1. 验证支付状态
2. 更新订单状态：`pending` → `paid`
3. 扣减商品库存
4. 记录状态变更历史

---

### 4. 发货流程

#### 4.1 商户后台操作
**位置**：merchant-admin → 订单管理 → 找到已支付订单

**操作**：
1. 点击"发货"按钮
2. 系统自动处理发货

#### 4.2 API调用
```http
PATCH /api/orders/{order_id}/ship/
```

**后端处理**：

```python
1. 验证订单状态为 paid
2. 更新订单状态：paid → shipped
3. 记录发货时间
4. 记录状态变更历史
5. （可选）发送发货通知给用户
```

#### 4.3 订单完成
用户收货后，可以确认收货：
```http
PATCH /api/orders/{order_id}/complete/
```

或者系统自动完成（发货后7天）：
- 订单状态：`shipped` → `completed`

---

## 海尔产品流程

### 1. 产品上架

#### 1.1 方式一：从海尔API同步（推荐）

**命令行操作**：
```bash
cd backend
python manage.py sync_haier_products
```

**同步过程**：
1. 调用海尔API获取产品列表
2. 自动创建/更新商品记录
3. 填充 `product_code`（海尔产品编码）
4. 同步价格、库存、图片等信息

**同步的字段**：

```python
- product_code: 海尔产品编码（必填）
- product_model: 产品型号
- product_group: 产品组
- supply_price: 供价
- invoice_price: 开票价
- market_price: 市场价
- stock_rebate: 直扣
- rebate_money: 台返
- product_image_url: 主图URL
- product_page_urls: 详情图URL列表
- is_sales: 是否可采（1可采/0不可采）
```

#### 1.2 方式二：商户后台手动添加

**位置**：merchant-admin → 商品管理 → 添加商品

**必填字段**：
- 商品名称
- 商品分类
- 品牌
- 价格
- **海尔产品编码**（重要！）

**注意**：必须填写正确的海尔产品编码，否则无法推送订单

---

### 2. 用户下单

#### 2.1 下单流程（与非海尔产品相同）
```
1. 浏览商品 → 选择商品
2. 点击"立即购买"
3. 选择收货地址
4. 确认订单信息
5. 提交订单
```

#### 2.2 订单创建


**API调用**：
```http
POST /api/orders/
{
  "product_id": 2,  // 海尔产品ID
  "address_id": 1,
  "quantity": 1
}
```

**后端处理**：
```python
1. 识别为海尔产品（product_code不为空）
2. 🔍 调用海尔API实时检查库存：
   - 获取收货地址的区域编码
   - 查询该区域的海尔产品库存
   - 验证库存是否充足
3. ✅ 库存充足 → 创建订单（状态：pending）
   ❌ 库存不足 → 返回错误，订单创建失败
4. 订单序列化器返回：
   {
     "is_haier_order": true,
     "haier_order_info": {
       "product_code": "HAIER_AC_001",
       "haier_so_id": null,  // 未推送
       "haier_order_no": null
     }
   }
```

**库存检查（新功能）**：
- ✅ **实时查询**：调用海尔API查询实时库存
- ✅ **区域匹配**：根据收货地址查询对应区域库存
- ✅ **库存拦截**：库存不足时订单创建失败
- ✅ **日志记录**：记录库存查询结果

**库存不足示例**：
```json
HTTP 400 Bad Request
{
  "detail": "海尔产品库存不足，当前库存: 0，需要: 1"
}
```

---

### 3. 支付流程（与非海尔产品相同）

```
1. 创建支付记录
2. 调用微信支付
3. 用户完成支付
4. 订单状态：pending → paid
```

---

### 4. 推送到海尔系统（关键步骤）

#### 4.1 商户后台操作
**位置**：merchant-admin → 订单管理

**识别海尔订单**：
- 订单列表显示"海尔订单: 是"（蓝色标签）
- 显示"未推送"（橙色标签）
- 显示"推送海尔"按钮

**推送操作**：

```
1. 点击"推送海尔"按钮
2. 填写推送信息：
   - 订单来源系统（如：MERCHANT_ADMIN）
   - 店铺名称（如：XX旗舰店）
3. 确认订单信息
4. 点击"确定"推送
```

#### 4.2 API调用
```http
POST /api/orders/{order_id}/push_to_haier/
{
  "source_system": "MERCHANT_ADMIN",
  "shop_name": "XX旗舰店"
}
```

#### 4.3 后端处理流程
```python
# orders/views.py - push_to_haier()

1. 验证订单条件：
   - 必须是海尔产品（product_code不为空）
   - 订单状态必须是 paid
   - 订单未推送过（haier_so_id为空）

2. 初始化易理货API：
   - 使用 YLHSystemAPI
   - 配置认证信息

3. 准备订单数据：
   order_data = {
     "sourceSystem": "MERCHANT_ADMIN",
     "shopName": "XX旗舰店",
     "sellerCode": "8800633175",  // 客户八码
     "consigneeName": "张三",
     "consigneeMobile": "13800138000",
     "onlineNo": "1764050087579528",  // 平台订单号
     "soId": "1764050087579528-2",  // 子订单号
     "province": "北京市",
     "city": "北京市",
     "area": "朝阳区",
     "detailAddress": "xxx街道xxx号",
     "itemList": [{
       "productCode": "HAIER_AC_001",
       "itemQty": 1,
       "retailPrice": 2999.00,
       "actualPrice": 2999.00
     }]
   }

4. 调用易理货API推送订单：
   result = ylh_api.create_order(order_data)

5. 更新订单记录：
   - haier_so_id = "1764050087579528-2"
   - haier_order_no = result['data']['retailOrderNo']  // 巨商汇订单号
   - 保存订单

6. 返回推送结果
```

#### 4.4 推送成功后
- 订单状态变为"已推送"（绿色标签）
- "推送海尔"按钮变为"查询物流"按钮
- 海尔/易理货系统开始处理订单

---

### 5. 查询物流信息

#### 5.1 商户后台操作


**位置**：merchant-admin → 订单管理 → 已推送的海尔订单

**操作**：
1. 点击"查询物流"按钮
2. 查看物流信息

#### 5.2 API调用
```http
GET /api/orders/{order_id}/haier_logistics/
```

#### 5.3 后端处理
```python
# orders/views.py - haier_logistics()

1. 验证订单已推送（haier_so_id不为空）

2. 初始化易理货API

3. 查询物流信息：
   logistics_info = ylh_api.get_logistics_by_order_codes([
     "1764050087579528-2"  // haier_so_id
   ])

4. 返回物流信息：
   {
     "detail": "查询成功",
     "logistics_info": [
       {
         "orderCode": "1764050087579528-2",
         "deliveryRecordCode": "DL20231125001",
         "logisticsList": [
           {
             "logisticsCompany": "顺丰速运",
             "logisticsNo": "SF1234567890",
             "snCode": "SN123456"
           }
         ]
       }
     ]
   }
```

#### 5.4 物流信息展示
merchant-admin显示：
- 统仓云仓物流信息
- 智汇宝物流信息
- 第三方快递信息
- 物流公司、物流单号、SN码

---

### 6. 海尔系统发货

#### 6.1 海尔/易理货系统处理

```
1. 接收订单
2. 仓库拣货
3. 安排物流
4. 发货
5. 回调通知平台
```

#### 6.2 接收海尔回调
```http
POST /api/orders/haier_callback/
{
  "Method": "OrderStatusChange",
  "AppKey": "your-app-key",
  "Sign": "signature",
  "Data": {
    "State": 1,  // 1成功/0失败
    "PlatformOrderNo": "1764050087579528",
    "ExtOrderNo": "HE20231125001",  // 海尔订单号
    "FailMsg": ""
  }
}
```

#### 6.3 后端处理回调
```python
# orders/views.py - haier_callback()

1. 验证签名
2. 解析回调数据
3. 根据 PlatformOrderNo 查找订单
4. 更新订单信息：
   - haier_order_no = "HE20231125001"
   - haier_status = "confirmed" 或 "failed"
5. 记录回调日志
```

---

### 7. 订单完成

#### 7.1 商户后台操作（可选）
如果需要手动完成订单：
```
merchant-admin → 订单管理 → 点击"完成"按钮
```

#### 7.2 自动完成
系统可以配置自动完成规则：
- 发货后N天自动完成
- 用户确认收货后完成

---

## 流程对比

### 完整流程对比表

| 环节 | 非海尔产品 | 海尔产品 |
|------|-----------|---------|
| **上架** | 商户后台手动添加 | 海尔API同步 或 手动添加（需填product_code） |
| **下单** | 用户小程序下单 | 用户小程序下单（相同） |
| **支付** | 微信支付 | 微信支付（相同） |
| **推送** | ❌ 不需要 | ✅ 推送到易理货系统 |
| **发货** | 商户后台点击发货 | 海尔/易理货系统发货 |
| **物流** | 商户自行管理 | 查询易理货系统物流 |
| **完成** | 手动或自动完成 | 手动或自动完成（相同） |

---

## 关键差异

### 1. 产品识别


**判断依据**：`product.product_code` 字段
```python
# 序列化器自动判断
def get_is_haier_order(self, obj: Order) -> bool:
    if not obj.product:
        return False
    return bool(obj.product.product_code and obj.product.product_code.strip())
```

### 2. 订单状态流转

**非海尔产品**：
```
pending → paid → shipped → completed
  ↓
cancelled (任何时候都可取消)
```

**海尔产品**：
```
pending → paid → [推送到海尔] → shipped → completed
  ↓                    ↓
cancelled         haier_status更新
```

### 3. 库存管理

**非海尔产品**：
- 平台自行管理库存
- 支付成功后扣减库存
- 取消订单后恢复库存

**海尔产品**：
- 可以从海尔API同步库存
- 也可以手动管理库存
- 实际库存以海尔系统为准

### 4. 发货方式

**非海尔产品**：
- 商户后台点击"发货"按钮
- 系统更新订单状态
- 可以手动填写物流信息

**海尔产品**：
- 推送订单到易理货系统
- 海尔/易理货系统安排发货
- 通过API查询物流信息
- 接收海尔回调更新状态

---

## 数据库字段说明

### Product 表（商品）

| 字段 | 非海尔产品 | 海尔产品 | 说明 |
|------|-----------|---------|------|
| product_code | NULL | 有值 | 海尔产品编码（关键字段） |
| product_model | - | 有值 | 产品型号 |
| supply_price | - | 有值 | 供价 |
| market_price | 可选 | 有值 | 市场价 |
| is_sales | - | '1'/'0' | 是否可采 |

### Order 表（订单）

| 字段 | 非海尔产品 | 海尔产品 | 说明 |
|------|-----------|---------|------|
| haier_so_id | NULL | 有值 | 子订单号（推送后） |
| haier_order_no | NULL | 有值 | 巨商汇订单号（推送后） |
| haier_status | '' | 有值 | 海尔订单状态 |
| logistics_company | 可选 | 有值 | 物流公司（查询后） |
| logistics_no | 可选 | 有值 | 物流单号（查询后） |

---

## API接口说明

### 通用接口（两种产品都使用）

#### 1. 创建订单
```http
POST /api/orders/
```

#### 2. 支付订单
```http
POST /api/orders/{id}/pay/
```

#### 3. 确认支付
```http
POST /api/orders/{id}/confirm_payment/
```

#### 4. 查询订单
```http
GET /api/orders/{id}/
```

### 海尔产品专用接口

#### 1. 推送订单到海尔
```http
POST /api/orders/{id}/push_to_haier/
{
  "source_system": "MERCHANT_ADMIN",
  "shop_name": "XX旗舰店"
}
```

**权限**：仅管理员
**条件**：
- 订单状态为 paid
- 是海尔产品订单
- 未推送过

#### 2. 查询物流信息
```http
GET /api/orders/{id}/haier_logistics/
```

**权限**：订单所有者或管理员
**条件**：订单已推送（haier_so_id不为空）

#### 3. 接收海尔回调
```http
POST /api/orders/haier_callback/
```

**权限**：公开（需验证签名）
**用途**：接收海尔系统的订单状态更新

### 非海尔产品专用接口

#### 1. 发货
```http
PATCH /api/orders/{id}/ship/
```

**权限**：仅管理员
**条件**：订单状态为 paid

---

## 配置说明

### 环境变量配置

**海尔API配置**（用于产品同步）：
```bash
HAIER_CLIENT_ID=xxx
HAIER_CLIENT_SECRET=xxx
HAIER_TOKEN_URL=https://openplat-test.haier.net/oauth2/auth
HAIER_BASE_URL=https://openplat-test.haier.net
HAIER_CUSTOMER_CODE=8800633175
```

**易理货API配置**（用于订单推送和物流查询）：
```bash
YLH_AUTH_URL=http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token
YLH_BASE_URL=http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev
YLH_USERNAME=erp
YLH_PASSWORD=123qwe
YLH_CLIENT_ID=open_api_erp
YLH_CLIENT_SECRET=12345678
```

---

## 常见问题

### Q1: 如何判断一个订单是否为海尔订单？
**A**: 检查订单关联的商品的 `product_code` 字段是否有值。

### Q2: 海尔订单必须推送吗？
**A**: 是的，海尔产品订单支付后必须推送到易理货系统，否则无法发货。

### Q3: 推送失败怎么办？
**A**: 
1. 检查网络连接
2. 检查易理货API配置
3. 查看后端日志
4. 可以重新推送

### Q4: 非海尔产品可以推送吗？
**A**: 不可以，系统会检查 `product_code`，非海尔产品没有推送按钮。

### Q5: 物流信息多久更新一次？
**A**: 需要手动点击"查询物流"按钮查询，系统不会自动更新。

### Q6: 可以同时销售两种产品吗？
**A**: 可以，系统会自动识别并使用不同的流程处理。

---

## 相关文档

- [海尔订单推送指南](merchant-admin/HAIER_ORDER_PUSH_GUIDE.md)
- [海尔功能快速参考](merchant-admin/HAIER_FEATURES.md)
- [推送订单功能修复](merchant-admin/PUSH_ORDER_FIX.md)
- [物流查询功能修复](merchant-admin/LOGISTICS_QUERY_FIX.md)
- [海尔订单问题排查](merchant-admin/HAIER_ORDER_TROUBLESHOOTING.md)

---

## 更新日志

- **2025-11-25**: 初始版本，完整说明两种产品的流程差异
