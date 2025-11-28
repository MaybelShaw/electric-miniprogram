from .models import Order, Cart, CartItem
from catalog.models import Product, InventoryLog
from django.utils import timezone
from .models import DiscountTarget
from users.models import Address
from django.core.cache import cache
from django.db import transaction
from django.db.models import F


def get_best_active_discount(user, product):
    """Select the best active discount amount for a given user and product.
    Result is cached briefly to reduce DB hits during browsing.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return 0
    cache_key = f"discount:{user.id}:{product.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    now = timezone.now()
    dt = (
        DiscountTarget.objects.select_related('discount')
        .filter(
            user=user,
            product=product,
            discount__effective_time__lte=now,
            discount__expiration_time__gt=now,
        )
        .order_by('-discount__priority', '-discount__updated_at')
        .first()
    )
    amount = dt.discount.amount if dt else 0
    if amount < 0:
        amount = 0
    if amount > product.price:
        amount = product.price
    # cache for 60 seconds; short-lived to reflect admin updates quickly
    cache.set(cache_key, amount, 60)
    return amount


def get_county_code(province, city, district):
    """获取区域编码（6位国标码）
    
    使用 jionlp 库自动获取行政区划代码
    
    Args:
        province: 省份
        city: 城市
        district: 区县
        
    Returns:
        str: 6位区域编码
    """
    import jionlp as jio
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # 加载中国行政区划数据
        location_data = jio.china_location_loader()
        
        # 方法1: 直接查询
        county_data = location_data.get(province, {}).get(city, {}).get(district, {})
        
        if county_data and '_admin_code' in county_data:
            admin_code = county_data['_admin_code']
            logger.info(f'成功获取区域编码: {province} {city} {district} → {admin_code}')
            return admin_code
        
        # 方法2: 如果区县字段不完整（如"北京"而不是"朝阳区"），尝试使用市级编码
        if district and (district == city.replace('市', '') or district == province.replace('市', '').replace('省', '')):
            # 区县字段只是城市名称，使用市级编码
            city_data = location_data.get(province, {}).get(city, {})
            if city_data and '_admin_code' in city_data:
                admin_code = city_data['_admin_code']
                logger.info(f'使用市级编码: {province} {city} → {admin_code}')
                return admin_code
        
        # 方法3: 使用 jionlp 的地址解析
        full_address = f"{province}{city}{district}"
        parsed = jio.parse_location(full_address)
        
        if parsed:
            p = parsed.get('province', province)
            c = parsed.get('city', city)
            d = parsed.get('county', district)
            
            # 尝试使用解析后的区县
            if d and d != district:
                county_data = location_data.get(p, {}).get(c, {}).get(d, {})
                if county_data and '_admin_code' in county_data:
                    admin_code = county_data['_admin_code']
                    logger.info(f'通过地址解析获取区域编码: {p} {c} {d} → {admin_code}')
                    return admin_code
            
            # 如果解析后还是没有区县，使用市级编码
            city_data = location_data.get(p, {}).get(c, {})
            if city_data and '_admin_code' in city_data:
                admin_code = city_data['_admin_code']
                logger.info(f'使用解析后的市级编码: {p} {c} → {admin_code}')
                return admin_code
        
        # 方法4: 如果以上都失败，尝试直接使用市级编码
        city_data = location_data.get(province, {}).get(city, {})
        if city_data and '_admin_code' in city_data:
            admin_code = city_data['_admin_code']
            logger.warning(f'未找到区县编码，使用市级编码: {province} {city} → {admin_code}')
            return admin_code
        
        # 最后的默认值
        logger.warning(f'未找到区域编码: {province} {city} {district}，使用默认值 110101')
        return '110101'  # 默认北京东城区
        
    except Exception as e:
        logger.error(f'获取区域编码失败: {str(e)}，使用默认值 110101')
        return '110101'


def check_haier_stock(product, address, quantity):
    """检查海尔产品库存
    
    Args:
        product: 商品对象
        address: 地址对象
        quantity: 订单数量
        
    Returns:
        dict: 库存信息，包含 available（是否有货）和 stock（库存数量）
        
    Raises:
        ValueError: API调用失败或库存不足时抛出异常
    """
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 获取区域编码
    county_code = get_county_code(address.province, address.city, address.district)
    logger.info(f'使用区域编码: {county_code} ({address.province} {address.city} {address.district})')
    
    # 检查是否启用模拟数据模式
    use_mock_data = getattr(settings, 'HAIER_USE_MOCK_DATA', True)
    
    if use_mock_data:
        # 使用模拟数据（开发/测试环境）
        logger.info(f'使用模拟库存数据: product_code={product.product_code}')
        
        # 模拟库存数据（根据API文档格式）
        mock_stock_info = {
            'secCode': 'WH001',  # 库位编码
            'stock': 100,  # 模拟库存数量
            'warehouseGrade': '0',  # 0:本级仓/1:上级仓
            'timelinessData': {
                'cutTime': '18:00',  # 截单时间
                'achieveUserOrderCut': '2025-11-26 18:00',  # 预计送达用户时间
                'hour': '24',  # 配送用户时效
                'isTranfer': '0'  # 是否转运：0否 1是
            }
        }
        
        available_stock = mock_stock_info['stock']
        
        logger.info(f'模拟库存查询成功: product_code={product.product_code}, stock={available_stock}, required={quantity}')
        
        # 检查库存是否充足
        if available_stock < quantity:
            raise ValueError(f'海尔产品库存不足，当前库存: {available_stock}，需要: {quantity}')
        
        return {
            'available': True,
            'stock': available_stock,
            'warehouse_code': mock_stock_info.get('secCode', ''),
            'warehouse_grade': mock_stock_info.get('warehouseGrade', ''),
            'timeliness_data': mock_stock_info.get('timelinessData', {})
        }
    
    else:
        # 使用真实海尔API（生产环境）
        from integrations.haierapi import HaierAPI
        
        logger.info(f'使用真实海尔API查询库存: product_code={product.product_code}')
        
        haier_api = HaierAPI.from_settings()
        
        # 认证
        if not haier_api.authenticate():
            logger.error('海尔API认证失败')
            raise ValueError('海尔库存查询失败：认证失败')
        
        # 查询库存
        stock_info = haier_api.check_stock(product.product_code, county_code)
        
        if not stock_info:
            logger.error(f'海尔库存查询失败: product_code={product.product_code}')
            raise ValueError('海尔库存查询失败：无法获取库存信息')
        
        # 检查库存是否充足
        available_stock = stock_info.get('stock', 0)
        
        logger.info(f'海尔库存查询成功: product_code={product.product_code}, stock={available_stock}, required={quantity}')
        
        if available_stock < quantity:
            raise ValueError(f'海尔产品库存不足，当前库存: {available_stock}，需要: {quantity}')
        
        return {
            'available': True,
            'stock': available_stock,
            'warehouse_code': stock_info.get('secCode', ''),
            'warehouse_grade': stock_info.get('warehouseGrade', ''),
            'timeliness_data': stock_info.get('timelinessData', {})
        }


def create_order(user, product_id, address_id, quantity, note=''):
    """创建订单并锁定库存
    
    Args:
        user: 用户对象
        product_id: 商品ID
        address_id: 地址ID
        quantity: 订单数量
        note: 订单备注（可选）
        
    Returns:
        Order: 创建的订单对象
        
    Raises:
        ValueError: 库存不足时抛出异常
        Product.DoesNotExist: 商品不存在时抛出异常
        Address.DoesNotExist: 地址不存在时抛出异常
    """
    product = Product.objects.get(id=product_id)
    address = Address.objects.get(id=address_id, user=user)

    # 检查是否为海尔产品：只根据 source 字段判断
    is_haier_product = getattr(product, 'source', None) == getattr(Product, 'SOURCE_HAIER', 'haier')
    
    # 如果是海尔产品，先检查海尔库存
    if is_haier_product:
        try:
            haier_stock_info = check_haier_stock(product, address, quantity)
            # 可以将海尔库存信息保存到订单备注或其他字段
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'海尔库存检查通过: {haier_stock_info}')
        except ValueError as e:
            # 海尔库存不足，直接抛出异常，不创建订单
            raise e

    full_address = (
        f"{address.province} {address.city} {address.district} {address.detail}"
    )
    # 折扣计算：选择一个有效折扣（最高优先级），硬性规则：折扣不得超过商品原价
    discount_amount = get_best_active_discount(user, product)

    unit_price = product.price - discount_amount
    total_amount = unit_price * quantity

    # 在事务中创建订单并锁定库存
    with transaction.atomic():
        # 对于非海尔产品，锁定本地库存
        # 对于海尔产品，不锁定本地库存（因为库存在海尔系统）
        if not is_haier_product:
            # 先锁定库存，如果失败则抛出异常，订单不会被创建
            InventoryService.lock_stock(
                product_id=product_id,
                quantity=quantity,
                reason='order_created',
                operator=user
            )
        
        # 库存检查通过，创建订单
        order = Order.objects.create(
            user=user,
            product=product,
            quantity=quantity,
            total_amount=total_amount,
            snapshot_contact_name=address.contact_name,
            snapshot_phone=address.phone,
            snapshot_address=full_address,
            snapshot_province=address.province,
            snapshot_city=address.city,
            snapshot_district=address.district,
            note=note,
        )
        try:
            from .analytics import OrderAnalytics
            OrderAnalytics.on_order_created(order.id)
        except Exception:
            pass

    return order


def get_or_create_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def add_to_cart(user, product_id, quantity=1):
    cart = get_or_create_cart(user)
    product = Product.objects.get(id=product_id)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return cart_item


def remove_from_cart(user, product_id):
    cart = get_or_create_cart(user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()


class InventoryService:
    """库存管理服务
    
    负责处理库存的锁定、释放和变更记录。
    使用数据库行锁确保并发安全。
    """

    @staticmethod
    @transaction.atomic
    def lock_stock(product_id: int, quantity: int, reason: str = 'order_created', operator=None) -> bool:
        """锁定库存（使用数据库行锁）
        
        Args:
            product_id: 商品ID
            quantity: 锁定数量
            reason: 锁定原因
            operator: 操作人（可选）
            
        Returns:
            bool: 锁定成功返回True
            
        Raises:
            ValueError: 库存不足时抛出异常
            Product.DoesNotExist: 商品不存在时抛出异常
        """
        # 使用select_for_update锁定行，防止并发问题
        product = Product.objects.select_for_update().get(id=product_id)
        
        if product.stock < quantity:
            raise ValueError(f'库存不足，当前库存: {product.stock}，需要: {quantity}')
        
        # 扣减库存
        product.stock = F('stock') - quantity
        product.save(update_fields=['stock'])
        
        # 刷新对象以获取最新的stock值
        product.refresh_from_db()
        
        # 记录库存变更
        InventoryLog.objects.create(
            product=product,
            change_type='lock',
            quantity=-quantity,
            reason=reason,
            created_by=operator
        )
        
        return True

    @staticmethod
    @transaction.atomic
    def release_stock(product_id: int, quantity: int, reason: str = 'order_cancelled', operator=None) -> bool:
        """释放库存
        
        Args:
            product_id: 商品ID
            quantity: 释放数量
            reason: 释放原因
            operator: 操作人（可选）
            
        Returns:
            bool: 释放成功返回True
            
        Raises:
            Product.DoesNotExist: 商品不存在时抛出异常
        """
        product = Product.objects.select_for_update().get(id=product_id)
        
        # 增加库存
        product.stock = F('stock') + quantity
        product.save(update_fields=['stock'])
        
        # 刷新对象以获取最新的stock值
        product.refresh_from_db()
        
        # 记录库存变更
        InventoryLog.objects.create(
            product=product,
            change_type='release',
            quantity=quantity,
            reason=reason,
            created_by=operator
        )
        
        return True

    @staticmethod
    @transaction.atomic
    def adjust_stock(product_id: int, quantity: int, reason: str = 'manual_adjust', operator=None) -> bool:
        """调整库存（增加或减少）
        
        Args:
            product_id: 商品ID
            quantity: 调整数量（正数增加，负数减少）
            reason: 调整原因
            operator: 操作人（可选）
            
        Returns:
            bool: 调整成功返回True
            
        Raises:
            ValueError: 调整后库存为负数时抛出异常
            Product.DoesNotExist: 商品不存在时抛出异常
        """
        product = Product.objects.select_for_update().get(id=product_id)
        
        new_stock = product.stock + quantity
        if new_stock < 0:
            raise ValueError(f'调整后库存不能为负数，当前库存: {product.stock}，调整: {quantity}')
        
        # 更新库存
        product.stock = F('stock') + quantity
        product.save(update_fields=['stock'])
        
        # 刷新对象以获取最新的stock值
        product.refresh_from_db()
        
        # 记录库存变更
        InventoryLog.objects.create(
            product=product,
            change_type='adjust',
            quantity=quantity,
            reason=reason,
            created_by=operator
        )
        
        return True

    @staticmethod
    def get_inventory_logs(product_id: int, limit: int = 100):
        """获取商品的库存变更日志
        
        Args:
            product_id: 商品ID
            limit: 返回记录数限制
            
        Returns:
            QuerySet: 库存日志查询集
        """
        return InventoryLog.objects.filter(
            product_id=product_id
        ).order_by('-created_at')[:limit]



def cancel_order(order):
    """取消订单并释放库存
    
    Args:
        order: 订单对象
        
    Returns:
        Order: 更新后的订单对象
        
    Raises:
        ValueError: 订单状态不允许取消时抛出异常
    """
    # 检查订单状态是否允许取消
    if order.status in ['completed', 'cancelled', 'refunded']:
        raise ValueError(f'订单状态为 {order.status}，不允许取消')
    
    with transaction.atomic():
        # 释放库存
        InventoryService.release_stock(
            product_id=order.product_id,
            quantity=order.quantity,
            reason='order_cancelled',
            operator=order.user
        )
        
        # 更新订单状态
        order.status = 'cancelled'
        order.save(update_fields=['status', 'updated_at'])
    
    return order
