# 开发指南

## 开发环境搭建

### 1. 系统要求
- Python 3.10+
- Git
- 代码编辑器（推荐VS Code / PyCharm）

### 2. 克隆项目
```bash
git clone https://github.com/yourrepo/electric-miniprogram.git
cd electric-miniprogram/backend
```

### 3. 创建虚拟环境
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 4. 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. 配置环境变量
```bash
cp .env.example .env
```

编辑`.env`文件，填写开发环境配置。

### 6. 数据库迁移
```bash
python manage.py migrate
```

### 7. 创建超级用户
```bash
python manage.py createsuperuser
```

### 8. 运行开发服务器
```bash
python manage.py runserver
```

访问：http://localhost:8000

## 代码规范

### Python代码规范（PEP 8）

#### 命名规范
```python
# 类名：大驼峰
class ProductViewSet:
    pass

# 函数名：小写+下划线
def get_product_list():
    pass

# 变量名：小写+下划线
product_count = 10

# 常量：大写+下划线
MAX_PAGE_SIZE = 100

# 私有方法：前缀下划线
def _internal_method():
    pass
```

#### 导入顺序
```python
# 1. 标准库
import os
import sys
from datetime import datetime

# 2. 第三方库
from django.db import models
from rest_framework import viewsets

# 3. 本地应用
from catalog.models import Product
from common.permissions import IsOwnerOrAdmin
```

#### 文档字符串
```python
def create_order(user, items, address):
    """
    创建订单
    
    Args:
        user: 用户对象
        items: 订单项列表
        address: 收货地址
    
    Returns:
        Order: 创建的订单对象
    
    Raises:
        InsufficientStockError: 库存不足
        InvalidAddressError: 地址无效
    """
    pass
```

### Django最佳实践

#### 模型设计
```python
class Product(models.Model):
    """商品模型"""
    
    name = models.CharField('商品名称', max_length=200)
    price = models.DecimalField('价格', max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'catalog_product'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # 保存前的逻辑
        super().save(*args, **kwargs)
        # 保存后的逻辑
```

#### 视图集设计
```python
class ProductViewSet(viewsets.ModelViewSet):
    """商品视图集"""
    
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku']
    ordering_fields = ['price', 'created_at']
    
    def get_queryset(self):
        """优化查询"""
        queryset = super().get_queryset()
        return queryset.select_related('category', 'brand')
    
    def perform_create(self, serializer):
        """创建时的额外逻辑"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        """自定义动作"""
        product = self.get_object()
        # 处理逻辑
        return Response({'status': 'success'})
```

#### 序列化器设计
```python
class ProductSerializer(serializers.ModelSerializer):
    """商品序列化器"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'category_name', 'main_image_url']
        read_only_fields = ['id', 'created_at']
    
    def get_main_image_url(self, obj):
        """获取主图URL"""
        if obj.main_image:
            return obj.main_image.image.url
        return None
    
    def validate_price(self, value):
        """验证价格"""
        if value <= 0:
            raise serializers.ValidationError("价格必须大于0")
        return value
    
    def create(self, validated_data):
        """创建逻辑"""
        return Product.objects.create(**validated_data)
```

## 测试指南

### 单元测试

#### 测试模型
```python
from django.test import TestCase
from catalog.models import Product

class ProductModelTest(TestCase):
    
    def setUp(self):
        """测试前准备"""
        self.product = Product.objects.create(
            name='测试商品',
            price=99.99,
            stock=10
        )
    
    def test_product_creation(self):
        """测试商品创建"""
        self.assertEqual(self.product.name, '测试商品')
        self.assertEqual(self.product.price, 99.99)
    
    def test_product_str(self):
        """测试字符串表示"""
        self.assertEqual(str(self.product), '测试商品')
    
    def test_decrease_stock(self):
        """测试库存扣减"""
        result = self.product.decrease_stock(5)
        self.assertTrue(result)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
```

#### 测试API
```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class ProductAPITest(APITestCase):
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_products(self):
        """测试商品列表"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_product(self):
        """测试创建商品"""
        data = {
            'name': '新商品',
            'price': 199.99,
            'stock': 20
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], '新商品')
```

### 运行测试
```bash
# 运行所有测试
python manage.py test

# 运行特定应用的测试
python manage.py test catalog

# 运行特定测试类
python manage.py test catalog.tests.ProductModelTest

# 运行特定测试方法
python manage.py test catalog.tests.ProductModelTest.test_product_creation

# 显示详细输出
python manage.py test --verbosity=2

# 保留测试数据库
python manage.py test --keepdb

# 并行测试
python manage.py test --parallel
```

### 测试覆盖率
```bash
# 安装coverage
pip install coverage

# 运行测试并生成覆盖率报告
coverage run --source='.' manage.py test
coverage report
coverage html

# 查看HTML报告
open htmlcov/index.html
```

## 调试技巧

### Django Debug Toolbar

#### 安装
```bash
pip install django-debug-toolbar
```

#### 配置
```python
# settings.py
INSTALLED_APPS = [
    ...
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    ...
]

INTERNAL_IPS = [
    '127.0.0.1',
]
```

```python
# urls.py
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

### 使用pdb调试
```python
import pdb

def some_function():
    x = 10
    pdb.set_trace()  # 设置断点
    y = x * 2
    return y
```

### 日志调试
```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.debug('调试信息')
    logger.info('一般信息')
    logger.warning('警告信息')
    logger.error('错误信息')
```

### Django Shell
```bash
# 进入Django Shell
python manage.py shell

# 使用IPython（推荐）
pip install ipython
python manage.py shell
```

```python
# 在Shell中测试
from catalog.models import Product

# 查询所有商品
products = Product.objects.all()

# 创建商品
product = Product.objects.create(name='测试', price=99.99)

# 更新商品
product.price = 199.99
product.save()

# 删除商品
product.delete()
```

## Git工作流

### 分支策略

```
main (生产环境)
  ↑
develop (开发环境)
  ↑
feature/xxx (功能分支)
hotfix/xxx (紧急修复)
```

### 常用命令

#### 创建功能分支
```bash
git checkout develop
git pull origin develop
git checkout -b feature/add-product-filter
```

#### 提交代码
```bash
git add .
git commit -m "feat: 添加商品筛选功能"
```

#### 推送分支
```bash
git push origin feature/add-product-filter
```

#### 合并到develop
```bash
git checkout develop
git merge feature/add-product-filter
git push origin develop
```

#### 发布到生产
```bash
git checkout main
git merge develop
git tag v1.0.0
git push origin main --tags
```

### 提交信息规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具相关

示例：
feat: 添加商品搜索功能
fix: 修复订单金额计算错误
docs: 更新API文档
```

## 常见问题

### 1. 数据库迁移冲突
```bash
# 查看迁移状态
python manage.py showmigrations

# 回滚迁移
python manage.py migrate app_name migration_name

# 重新生成迁移
python manage.py makemigrations

# 合并迁移
python manage.py makemigrations --merge
```

### 2. 静态文件不更新
```bash
# 清除缓存
python manage.py collectstatic --clear --noinput

# 重新收集
python manage.py collectstatic --noinput
```

### 3. 端口被占用
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :8000
kill -9 <pid>
```

### 4. 依赖包冲突
```bash
# 重新创建虚拟环境
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 开发工具推荐

### VS Code插件
- Python
- Django
- GitLens
- REST Client
- SQLite Viewer

### PyCharm配置
- 启用Django支持
- 配置代码格式化
- 设置测试运行器
- 配置数据库工具

### 其他工具
- Postman：API测试
- DBeaver：数据库管理
- Redis Desktop Manager：Redis管理
- Docker Desktop：容器管理

## 性能优化建议

### 数据库查询优化
```python
# 使用select_related
products = Product.objects.select_related('category', 'brand').all()

# 使用prefetch_related
products = Product.objects.prefetch_related('images').all()

# 使用only
products = Product.objects.only('id', 'name', 'price').all()

# 使用values
products = Product.objects.values('id', 'name').all()

# 批量创建
Product.objects.bulk_create([
    Product(name='商品1', price=99.99),
    Product(name='商品2', price=199.99),
])

# 批量更新
Product.objects.filter(category_id=1).update(is_active=True)
```

### 缓存使用
```python
from django.core.cache import cache

# 设置缓存
cache.set('key', 'value', 300)  # 5分钟

# 获取缓存
value = cache.get('key')

# 删除缓存
cache.delete('key')

# 使用装饰器
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15分钟
def my_view(request):
    pass
```

### 异步任务
```python
# 使用Celery
from celery import shared_task

@shared_task
def send_email_task(user_id):
    # 发送邮件逻辑
    pass

# 调用任务
send_email_task.delay(user_id)
```

## 代码审查清单

### 功能性
- [ ] 功能是否按需求实现
- [ ] 边界条件是否处理
- [ ] 错误处理是否完善
- [ ] 测试是否通过

### 代码质量
- [ ] 代码是否符合规范
- [ ] 命名是否清晰
- [ ] 注释是否充分
- [ ] 是否有重复代码

### 性能
- [ ] 数据库查询是否优化
- [ ] 是否使用缓存
- [ ] 是否有N+1查询
- [ ] 是否有性能瓶颈

### 安全
- [ ] 输入是否验证
- [ ] 权限是否检查
- [ ] SQL注入是否防范
- [ ] XSS是否防范

## 学习资源

### 官方文档
- Django: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Python: https://docs.python.org/

### 推荐书籍
- 《Django企业开发实战》
- 《Two Scoops of Django》
- 《Python Web开发实战》

### 在线课程
- Django官方教程
- Real Python
- Udemy Django课程

## 联系方式

- 技术讨论：tech@example.com
- Bug反馈：GitHub Issues
- 文档贡献：提交PR
