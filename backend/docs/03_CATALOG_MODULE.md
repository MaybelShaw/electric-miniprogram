# 商品目录模块文档 (catalog)

## 模块概述

商品目录模块负责商品信息管理、分类管理、品牌管理、商品搜索等功能。

## 数据模型

### Category (商品分类)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| name | CharField(100) | 分类名称（唯一） |
| order | IntegerField | 排序 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

### Brand (品牌)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| name | CharField(100) | 品牌名称（唯一） |
| logo | URLField | 品牌Logo |
| description | TextField | 品牌描述 |
| order | IntegerField | 排序 |
| is_active | BooleanField | 是否启用 |

### Product (商品)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| name | CharField(200) | 商品名称 |
| description | TextField | 商品描述 |
| category | ForeignKey | 分类 |
| brand | ForeignKey | 品牌 |
| price | DecimalField | 价格 |
| stock | PositiveIntegerField | 库存 |
| main_images | JSONField | 主图列表 |
| detail_images | JSONField | 详情图列表 |
| is_active | BooleanField | 是否上架 |
| view_count | PositiveIntegerField | 浏览次数 |
| sales_count | PositiveIntegerField | 销售数量 |

### MediaImage (媒体图片)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| file | FileField | 文件 |
| original_name | CharField | 原始文件名 |
| content_type | CharField | 内容类型 |
| size | PositiveIntegerField | 文件大小 |

### SearchLog (搜索日志)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| keyword | CharField | 搜索关键词 |
| user | ForeignKey | 用户 |
| created_at | DateTimeField | 搜索时间 |

### InventoryLog (库存日志)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| product | ForeignKey | 商品 |
| change_type | CharField | 变更类型（lock/release/adjust） |
| quantity | IntegerField | 变更数量 |
| reason | CharField | 变更原因 |
| created_by | ForeignKey | 操作人 |

## API端点

### 分类管理
- `GET /api/categories/` - 分类列表
- `GET /api/categories/{id}/` - 分类详情
- `POST /api/categories/` - 创建分类（管理员）
- `PUT /api/categories/{id}/` - 更新分类（管理员）
- `DELETE /api/categories/{id}/` - 删除分类（管理员）

### 品牌管理
- `GET /api/brands/` - 品牌列表
- `GET /api/brands/{id}/` - 品牌详情
- `POST /api/brands/` - 创建品牌（管理员）
- `PUT /api/brands/{id}/` - 更新品牌（管理员）
- `DELETE /api/brands/{id}/` - 删除品牌（管理员）

### 商品管理
- `GET /api/products/` - 商品列表
  - 查询参数：category, brand, search, min_price, max_price, ordering
- `GET /api/products/{id}/` - 商品详情
- `POST /api/products/` - 创建商品（管理员）
- `PUT /api/products/{id}/` - 更新商品（管理员）
- `DELETE /api/products/{id}/` - 删除商品（管理员）
- `GET /api/products/search/` - 搜索商品
- `GET /api/products/hot-searches/` - 热门搜索

### 图片管理
- `POST /api/media/upload/` - 上传图片
- `GET /api/media/{id}/` - 获取图片信息
- `DELETE /api/media/{id}/` - 删除图片（管理员）

## 权限控制
- 查看：所有用户
- 创建/更新/删除：仅管理员

## 索引设计
```sql
-- 商品表索引
CREATE INDEX idx_product_active_sales ON catalog_product(is_active, sales_count DESC);
CREATE INDEX idx_product_active_views ON catalog_product(is_active, view_count DESC);
CREATE INDEX idx_product_category ON catalog_product(category_id, is_active);
CREATE INDEX idx_product_brand ON catalog_product(brand_id, is_active);
CREATE INDEX idx_product_created ON catalog_product(created_at DESC);

-- 品牌表索引
CREATE INDEX idx_brand_active_order ON catalog_brand(is_active, order);

-- 搜索日志索引
CREATE INDEX idx_searchlog_keyword ON catalog_searchlog(keyword, created_at DESC);
```

## 使用示例

### 查询商品列表
```python
GET /api/products/?category=1&brand=2&min_price=100&max_price=1000&ordering=-sales_count
```

### 搜索商品
```python
GET /api/products/search/?q=冰箱
```

### 上传图片
```python
POST /api/media/upload/
Content-Type: multipart/form-data

file: <image_file>
```

### 创建商品
```python
POST /api/products/
Authorization: Bearer <admin_token>

{
    "name": "海尔冰箱",
    "description": "高品质冰箱",
    "category": 1,
    "brand": 1,
    "price": 2999.00,
    "stock": 100,
    "main_images": ["http://..."],
    "detail_images": ["http://..."]
}
```

## 最佳实践

1. **图片管理**
   - 使用MediaImage模型统一管理图片
   - 图片URL存储在Product的JSONField中
   - 定期清理未使用的图片

2. **搜索优化**
   - 记录搜索日志用于分析
   - 使用索引优化搜索性能
   - 实现搜索建议功能

3. **库存管理**
   - 使用InventoryLog记录所有库存变更
   - 实现库存预警机制
   - 防止超卖

4. **性能优化**
   - 使用select_related优化外键查询
   - 使用缓存减少数据库查询
   - 合理使用索引

详细API文档请参考：[API完整参考文档](./07_API_REFERENCE.md)
