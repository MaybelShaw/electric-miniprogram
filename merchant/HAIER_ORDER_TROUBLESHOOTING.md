# 海尔订单显示问题排查指南

## 问题：订单列表显示"海尔订单: 否"

### 原因
订单是否为海尔订单的判断依据是：**商品是否有 `product_code`（海尔产品编码）**

如果商品的 `product_code` 字段为空（NULL 或空字符串），则不会被识别为海尔订单。

### 解决方案

#### 方案1：从海尔API同步产品（推荐）
```bash
cd backend
python manage.py sync_haier_products
```

这会从海尔API获取产品信息，自动填充 `product_code` 字段。

#### 方案2：手动添加产品编码

在商户后台的"商品管理"页面：
1. 编辑商品
2. 填写"海尔产品编码"字段
3. 保存

#### 方案3：通过Django Admin添加

1. 访问 Django Admin: http://localhost:8000/admin/
2. 进入"商品"管理
3. 编辑商品，填写"product_code"字段
4. 保存

### 验证

修改后，刷新merchant-admin订单列表页面，应该能看到：
- **海尔订单: 是**（蓝色标签）
- **未推送**（橙色标签）- 如果订单已支付但未推送
- **推送海尔**按钮 - 可以推送订单到海尔

### 技术细节

判断逻辑在 `backend/orders/serializers.py` 的 `OrderSerializer`:

```python
def get_is_haier_order(self, obj: Order) -> bool:
    """判断是否为海尔订单"""
    if not obj.product:
        return False
    # 检查 product_code 是否存在且不为空字符串
    return bool(obj.product.product_code and obj.product.product_code.strip())
```

### 常见问题

**Q: 我的商品名称包含"海尔"，为什么不显示为海尔订单？**
A: 判断依据不是商品名称，而是 `product_code` 字段。必须填写海尔产品编码。

**Q: 如何批量设置产品编码？**
A: 使用 `sync_haier_products` 命令从海尔API批量同步，或者通过Django Admin批量编辑。

**Q: 已经设置了 product_code，但还是显示"否"？**
A: 检查以下几点：
1. 确认 product_code 不是空字符串
2. 刷新浏览器缓存
3. 检查后端日志是否有错误
4. 重启后端服务

### 测试数据

如果需要测试，可以手动给产品添加测试编码：

```python
# Django shell
from catalog.models import Product
product = Product.objects.get(name__contains='海尔')
product.product_code = 'HAIER_TEST_001'
product.save()
```

或者使用SQL：

```sql
UPDATE catalog_product 
SET product_code = 'HAIER_TEST_001' 
WHERE name LIKE '%海尔%';
```
