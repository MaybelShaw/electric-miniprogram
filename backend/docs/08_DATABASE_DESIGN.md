# 数据库设计文档

## 数据库概述

### 数据库类型
- 开发环境：SQLite
- 生产环境：PostgreSQL（推荐）

### 字符集
- UTF-8

### 时区
- UTC

## 数据表结构

### 用户模块 (users)

#### users_user (用户表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| openid | CharField(128) | UNIQUE | 微信OpenID |
| session_key | CharField(128) | NULL | 微信SessionKey |
| nickname | CharField(100) | NULL | 昵称 |
| avatar | URLField | NULL | 头像URL |
| phone | CharField(11) | NULL | 手机号 |
| email | EmailField | NULL | 邮箱 |
| is_active | BooleanField | DEFAULT TRUE | 是否激活 |
| is_staff | BooleanField | DEFAULT FALSE | 是否管理员 |
| date_joined | DateTimeField | AUTO | 注册时间 |
| last_login | DateTimeField | NULL | 最后登录 |

**索引：**
- idx_user_openid: openid
- idx_user_phone: phone
- idx_user_email: email

#### users_address (收货地址表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| user_id | BigIntegerField | FK | 用户ID |
| contact_name | CharField(50) | NOT NULL | 联系人 |
| phone | CharField(11) | NOT NULL | 手机号 |
| province | CharField(50) | NOT NULL | 省份 |
| city | CharField(50) | NOT NULL | 城市 |
| district | CharField(50) | NOT NULL | 区县 |
| detail | CharField(200) | NOT NULL | 详细地址 |
| is_default | BooleanField | DEFAULT FALSE | 是否默认 |
| created_at | DateTimeField | AUTO | 创建时间 |
| updated_at | DateTimeField | AUTO | 更新时间 |

**索引：**
- idx_address_user: user_id
- idx_address_default: user_id, is_default

**外键：**
- user_id → users_user.id (CASCADE)

### 商品目录模块 (catalog)

#### catalog_category (商品分类表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| name | CharField(100) | UNIQUE | 分类名称 |
| description | TextField | NULL | 分类描述 |
| image | ImageField | NULL | 分类图片 |
| parent_id | BigIntegerField | FK, NULL | 父分类ID |
| sort_order | IntegerField | DEFAULT 0 | 排序 |
| is_active | BooleanField | DEFAULT TRUE | 是否启用 |
| created_at | DateTimeField | AUTO | 创建时间 |
| updated_at | DateTimeField | AUTO | 更新时间 |

**索引：**
- idx_category_parent: parent_id
- idx_category_active: is_active
- idx_category_sort: sort_order, name

**外键：**
- parent_id → catalog_category.id (SET_NULL)

#### catalog_brand (品牌表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| name | CharField(100) | UNIQUE | 品牌名称 |
| description | TextField | NULL | 品牌描述 |
| logo | ImageField | NULL | 品牌Logo |
| website | URLField | NULL | 官网地址 |
| sort_order | IntegerField | DEFAULT 0 | 排序 |
| is_active | BooleanField | DEFAULT TRUE | 是否启用 |
| created_at | DateTimeField | AUTO | 创建时间 |
| updated_at | DateTimeField | AUTO | 更新时间 |

**索引：**
- idx_brand_active: is_active
- idx_brand_sort: sort_order, name

#### catalog_product (商品表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| name | CharField(200) | NOT NULL | 商品名称 |
| description | TextField | NULL | 商品描述 |
| category_id | BigIntegerField | FK | 分类ID |
| brand_id | BigIntegerField | FK, NULL | 品牌ID |
| sku | CharField(100) | UNIQUE, NULL | 商品SKU |
| barcode | CharField(50) | NULL | 条形码 |
| price | DecimalField(10,2) | NOT NULL | 价格 |
| cost_price | DecimalField(10,2) | NULL | 成本价 |
| market_price | DecimalField(10,2) | NULL | 市场价 |
| stock | IntegerField | DEFAULT 0 | 库存 |
| min_stock | IntegerField | DEFAULT 0 | 最低库存 |
| weight | DecimalField(10,3) | NULL | 重量(kg) |
| dimensions | CharField(100) | NULL | 尺寸 |
| is_active | BooleanField | DEFAULT TRUE | 是否上架 |
| is_featured | BooleanField | DEFAULT FALSE | 是否推荐 |
| sales_count | IntegerField | DEFAULT 0 | 销量 |
| view_count | IntegerField | DEFAULT 0 | 浏览量 |
| sort_order | IntegerField | DEFAULT 0 | 排序 |
| created_at | DateTimeField | AUTO | 创建时间 |
| updated_at | DateTimeField | AUTO | 更新时间 |

**索引：**
- idx_product_category: category_id
- idx_product_brand: brand_id
- idx_product_sku: sku
- idx_product_price: price
- idx_product_sales: sales_count
- idx_product_active: is_active
- idx_product_featured: is_featured
- idx_product_category_active: category_id, is_active
- idx_product_search: name, sku, is_active

**外键：**
- category_id → catalog_category.id (PROTECT)
- brand_id → catalog_brand.id (SET_NULL)

#### catalog_productimage (商品图片表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| product_id | BigIntegerField | FK | 商品ID |
| image | ImageField | NOT NULL | 图片 |
| alt_text | CharField(200) | NULL | 替代文本 |
| is_main | BooleanField | DEFAULT FALSE | 是否主图 |
| sort_order | IntegerField | DEFAULT 0 | 排序 |
| created_at | DateTimeField | AUTO | 创建时间 |

**索引：**
- idx_productimage_product: product_id
- idx_productimage_main: product_id, is_main

**外键：**
- product_id → catalog_product.id (CASCADE)

#### catalog_favorite (收藏表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| user_id | BigIntegerField | FK | 用户ID |
| product_id | BigIntegerField | FK | 商品ID |
| created_at | DateTimeField | AUTO | 创建时间 |

**索引：**
- idx_favorite_user: user_id
- idx_favorite_product: product_id
- unique_user_product: user_id, product_id (UNIQUE)

**外键：**
- user_id → users_user.id (CASCADE)
- product_id → catalog_product.id (CASCADE)

#### catalog_cart (购物车表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| user_id | BigIntegerField | FK | 用户ID |
| product_id | BigIntegerField | FK | 商品ID |
| quantity | IntegerField | MIN 1 | 数量 |
| created_at | DateTimeField | AUTO | 创建时间 |
| updated_at | DateTimeField | AUTO | 更新时间 |

**索引：**
- idx_cart_user: user_id
- idx_cart_product: product_id
- unique_user_product: user_id, product_id (UNIQUE)

**外键：**
- user_id → users_user.id (CASCADE)
- product_id → catalog_product.id (CASCADE)

### 订单模块 (orders)

#### orders_order (订单表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| order_no | CharField(32) | UNIQUE | 订单号 |
| user_id | BigIntegerField | FK | 用户ID |
| status | CharField(20) | NOT NULL | 订单状态 |
| total_amount | DecimalField(10,2) | NOT NULL | 订单总金额 |
| shipping_fee | DecimalField(10,2) | DEFAULT 0 | 运费 |
| discount_amount | DecimalField(10,2) | DEFAULT 0 | 优惠金额 |
| final_amount | DecimalField(10,2) | NOT NULL | 实付金额 |
| shipping_address | JSONField | NOT NULL | 收货地址 |
| remark | TextField | NULL | 备注 |
| created_at | DateTimeField | AUTO | 创建时间 |
| updated_at | DateTimeField | AUTO | 更新时间 |
| paid_at | DateTimeField | NULL | 支付时间 |
| shipped_at | DateTimeField | NULL | 发货时间 |
| completed_at | DateTimeField | NULL | 完成时间 |
| cancelled_at | DateTimeField | NULL | 取消时间 |
| cancel_reason | CharField(200) | NULL | 取消原因 |

**索引：**
- idx_order_no: order_no
- idx_order_user: user_id
- idx_order_status: status
- idx_order_created: created_at
- idx_order_user_status: user_id, status

**外键：**
- user_id → users_user.id (PROTECT)

#### orders_orderitem (订单明细表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| order_id | BigIntegerField | FK | 订单ID |
| product_id | BigIntegerField | FK | 商品ID |
| product_name | CharField(200) | NOT NULL | 商品名称 |
| product_sku | CharField(100) | NULL | 商品SKU |
| product_image | URLField | NULL | 商品图片 |
| price | DecimalField(10,2) | NOT NULL | 单价 |
| quantity | IntegerField | MIN 1 | 数量 |
| subtotal | DecimalField(10,2) | NOT NULL | 小计 |
| created_at | DateTimeField | AUTO | 创建时间 |

**索引：**
- idx_orderitem_order: order_id
- idx_orderitem_product: product_id

**外键：**
- order_id → orders_order.id (CASCADE)
- product_id → catalog_product.id (PROTECT)

#### orders_payment (支付记录表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| order_id | BigIntegerField | FK | 订单ID |
| payment_no | CharField(64) | UNIQUE | 支付单号 |
| payment_method | CharField(20) | NOT NULL | 支付方式 |
| amount | DecimalField(10,2) | NOT NULL | 支付金额 |
| status | CharField(20) | NOT NULL | 支付状态 |
| transaction_id | CharField(100) | NULL | 第三方交易号 |
| callback_data | JSONField | NULL | 回调数据 |
| created_at | DateTimeField | AUTO | 创建时间 |
| paid_at | DateTimeField | NULL | 支付时间 |
| failed_at | DateTimeField | NULL | 失败时间 |
| failure_reason | CharField(200) | NULL | 失败原因 |

**索引：**
- idx_payment_no: payment_no
- idx_payment_order: order_id
- idx_payment_status: status
- idx_payment_transaction: transaction_id

**外键：**
- order_id → orders_order.id (PROTECT)

### 集成模块 (integrations)

#### integrations_synclog (同步日志表)
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigAutoField | PK | 主键 |
| sync_type | CharField(50) | NOT NULL | 同步类型 |
| status | CharField(20) | NOT NULL | 状态 |
| request_data | JSONField | NULL | 请求数据 |
| response_data | JSONField | NULL | 响应数据 |
| error_message | TextField | NULL | 错误信息 |
| created_at | DateTimeField | AUTO | 创建时间 |
| completed_at | DateTimeField | NULL | 完成时间 |

**索引：**
- idx_synclog_type: sync_type
- idx_synclog_status: status
- idx_synclog_created: created_at

## ER图

```
users_user
    ├── users_address (1:N)
    ├── catalog_favorite (1:N)
    ├── catalog_cart (1:N)
    └── orders_order (1:N)

catalog_category
    ├── catalog_category (1:N, 自关联)
    └── catalog_product (1:N)

catalog_brand
    └── catalog_product (1:N)

catalog_product
    ├── catalog_productimage (1:N)
    ├── catalog_favorite (1:N)
    ├── catalog_cart (1:N)
    └── orders_orderitem (1:N)

orders_order
    ├── orders_orderitem (1:N)
    └── orders_payment (1:N)
```

## 数据库迁移

### 创建迁移
```bash
python manage.py makemigrations
```

### 执行迁移
```bash
python manage.py migrate
```

### 查看迁移状态
```bash
python manage.py showmigrations
```

### 回滚迁移
```bash
python manage.py migrate app_name migration_name
```

## 数据库优化

### 索引优化
- 为外键字段创建索引
- 为常用查询字段创建索引
- 为组合查询创建复合索引

### 查询优化
- 使用select_related减少查询次数
- 使用prefetch_related优化多对多查询
- 使用only/defer减少字段查询
- 使用values/values_list优化数据获取

### 连接池配置
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

## 备份策略

### 自动备份
```bash
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

### 备份脚本
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump dbname > backup_$DATE.sql
```

### 恢复数据
```bash
psql dbname < backup_20250101_020000.sql
```

## 数据字典

完整的数据字典请参考各模块文档。
