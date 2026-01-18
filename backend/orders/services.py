from .models import Order, Cart, CartItem, OrderItem, Discount
from catalog.models import Product, InventoryLog
from django.utils import timezone
from .models import DiscountTarget
from users.models import Address
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from decimal import Decimal, ROUND_HALF_UP


def _get_best_discount_rule(user, product):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    cache_key = f"discount_rule:{user.id}:{product.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

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
    if not dt:
        cache.set(cache_key, False, 60)
        return None
    rule = {
        'type': dt.discount.discount_type,
        'value': str(dt.discount.amount),
        'discount_id': dt.discount_id,
    }
    cache.set(cache_key, rule, 60)
    return rule


def get_best_active_discount(user, product, base_price=None):
    """Select the best active discount amount for a given user and product.
    Result is cached briefly to reduce DB hits during browsing.
    """
    rule = _get_best_discount_rule(user, product)
    if not rule:
        return Decimal('0')

    base = Decimal(base_price if base_price is not None else product.price)
    if rule['type'] == Discount.TYPE_PERCENT:
        rate = Decimal(rule['value'])
        if rate < 0:
            rate = Decimal('0')
        if rate > 10:
            rate = Decimal('10')
        discounted_price = (base * rate) / Decimal('10')
        amount = base - discounted_price
    else:
        amount = Decimal(rule['value'])
    if amount < 0:
        amount = Decimal('0')
    if amount > base:
        amount = base
    amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
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
    
    # 使用真实海尔API
    from integrations.haierapi import HaierAPI
    
    logger.info(f'查询海尔库存: product_code={product.product_code}')
    
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


def create_order(
    user,
    product_id=None,
    address_id=None,
    quantity=1,
    note='',
    payment_method='online',
    items=None
):
    """创建订单并锁定库存（支持多商品、多SKU）
    
    Args:
        user: 用户对象
        product_id: 商品ID（兼容旧接口）
        address_id: 地址ID
        quantity: 订单数量（仅旧接口使用）
        note: 订单备注
        payment_method: 支付方式 ('online' 或 'credit')
        items: 新的下单商品列表 [{product_id, sku_id, quantity}]
    """
    if not address_id:
        raise ValueError('缺少 address_id')

    address = Address.objects.get(id=address_id, user=user)

    # 兼容旧接口：未传 items 时使用 product_id/quantity
    if not items:
        if not product_id:
            raise ValueError('商品信息不能为空')
        items = [{
            'product_id': product_id,
            'quantity': quantity or 1,
            'sku_id': None,
        }]

    if not isinstance(items, list) or len(items) == 0:
        raise ValueError('商品列表不能为空')

    full_address = (
        f"{address.province} {address.city} {address.district} {address.detail}"
    )

    normalized_items = []
    total_amount = Decimal('0')
    total_discount = Decimal('0')
    is_credit = payment_method == 'credit'

    # 下单前校验与准备
    for item in items:
        product_id = item.get('product_id')
        sku_id = item.get('sku_id')
        qty = int(item.get('quantity') or 1)

        if not product_id or qty <= 0:
            raise ValueError('商品或数量无效')

        product = Product.objects.get(id=product_id)
        sku = None
        if sku_id not in (None, '', False):
            sku_id = int(sku_id)
            from catalog.models import ProductSKU
            sku = ProductSKU.objects.get(id=sku_id, product_id=product_id)

        # 价格与折扣
        base_price = Decimal(sku.price if sku else product.price)
        discount_amount = get_best_active_discount(user, product, base_price=base_price)
        if discount_amount < 0:
            discount_amount = Decimal('0')
        if discount_amount > base_price:
            discount_amount = base_price

        unit_price = Decimal(base_price)
        actual_unit_price = unit_price - discount_amount
        line_total = actual_unit_price * qty
        total_amount += unit_price * qty
        total_discount += discount_amount * qty

        normalized_items.append({
            'product': product,
            'sku': sku,
            'quantity': qty,
            'unit_price': unit_price,
            'discount_amount': discount_amount * qty,
            'actual_amount': line_total,
            'sku_specs': sku.specs if sku else {},
            'sku_code': getattr(sku, 'sku_code', '') or getattr(product, 'product_code', '') or '',
            'product_name': product.name,
            'snapshot_image': (sku.image or (product.main_images[0] if product.main_images else product.product_image_url or '')) if sku else (product.main_images[0] if product.main_images else product.product_image_url or ''),
            'is_haier': getattr(product, 'source', None) == getattr(Product, 'SOURCE_HAIER', 'haier'),
        })

    actual_amount = total_amount - total_discount

    # 如果使用信用支付，检查信用额度
    if is_credit:
        if user.role != 'dealer':
            raise ValueError('只有经销商可以使用信用支付')
        if not hasattr(user, 'credit_account'):
            raise ValueError('您还没有信用账户')
        credit_account = user.credit_account
        if not credit_account.can_place_order(actual_amount):
            raise ValueError(f'信用额度不足，可用额度: ¥{credit_account.available_credit}')

    # 在事务中创建订单并锁定库存
    with transaction.atomic():
        # 逐项锁定库存/校验海尔库存
        for item in normalized_items:
            if item['is_haier']:
                check_haier_stock(item['product'], address, item['quantity'])
            else:
                InventoryService.lock_stock(
                    product_id=item['product'].id,
                    sku_id=item['sku'].id if item['sku'] else None,
                    quantity=item['quantity'],
                    reason='order_created',
                    operator=user
                )

        order = Order.objects.create(
            user=user,
            product=normalized_items[0]['product'] if normalized_items else None,
            quantity=sum(i['quantity'] for i in normalized_items),
            total_amount=total_amount,
            discount_amount=total_discount,
            actual_amount=actual_amount,
            snapshot_contact_name=address.contact_name,
            snapshot_phone=address.phone,
            snapshot_address=full_address,
            snapshot_province=address.province,
            snapshot_city=address.city,
            snapshot_district=address.district,
            note=note,
        )

        # 创建订单行
        order_items = []
        for item in normalized_items:
            order_items.append(
                OrderItem(
                    order=order,
                    product=item['product'],
                    sku=item['sku'],
                    product_name=item['product_name'],
                    sku_specs=item['sku_specs'],
                    sku_code=item['sku_code'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    discount_amount=item['discount_amount'],
                    actual_amount=item['actual_amount'],
                    snapshot_image=item['snapshot_image'],
                )
            )
        OrderItem.objects.bulk_create(order_items)

        # 信用支付直接记账并标记为已支付
        if is_credit:
            from users.credit_services import CreditAccountService
            CreditAccountService.record_purchase(
                credit_account=user.credit_account,
                amount=actual_amount,
                order_id=order.id,
                description=f'订单 #{order.order_number}'
            )
            order.status = 'paid'
            order.save(update_fields=['status', 'updated_at'])
        
        try:
            from .analytics import OrderAnalytics
            OrderAnalytics.on_order_created(order.id)
        except Exception:
            pass

    return order


def get_or_create_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def add_to_cart(user, product_id, quantity=1, sku_id=None):
    cart = get_or_create_cart(user)
    product = Product.objects.get(id=product_id)
    sku = None
    if sku_id:
        from catalog.models import ProductSKU
        sku = ProductSKU.objects.get(id=sku_id, product=product)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, sku=sku, defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return cart_item


def remove_from_cart(user, product_id, sku_id=None):
    cart = get_or_create_cart(user)
    qs = CartItem.objects.filter(cart=cart, product_id=product_id)
    if sku_id:
        qs = qs.filter(sku_id=sku_id)
    qs.delete()


class InventoryService:
    """库存管理服务
    
    负责处理库存的锁定、释放和变更记录。
    使用数据库行锁确保并发安全。
    """

    @staticmethod
    @transaction.atomic
    def lock_stock(product_id: int, quantity: int, reason: str = 'order_created', operator=None, sku_id: int = None) -> bool:
        """锁定库存（使用数据库行锁）
        
        Args:
            product_id: 商品ID
            quantity: 锁定数量
            reason: 锁定原因
            operator: 操作人（可选）
            sku_id: SKU ID（可选）
            
        Returns:
            bool: 锁定成功返回True
            
        Raises:
            ValueError: 库存不足时抛出异常
            Product.DoesNotExist: 商品不存在时抛出异常
        """
        # 使用select_for_update锁定行，防止并发问题
        if sku_id:
            from catalog.models import ProductSKU
            sku = ProductSKU.objects.select_for_update().get(id=sku_id, product_id=product_id)
            if sku.stock < quantity:
                raise ValueError(f'库存不足，当前库存: {sku.stock}，需要: {quantity}')
            sku.stock = F('stock') - quantity
            sku.save(update_fields=['stock'])
            sku.refresh_from_db()
            product = sku.product
        else:
            product = Product.objects.select_for_update().get(id=product_id)
            if product.stock < quantity:
                raise ValueError(f'库存不足，当前库存: {product.stock}，需要: {quantity}')
            product.stock = F('stock') - quantity
            product.save(update_fields=['stock'])
            product.refresh_from_db()
        
        # 记录库存变更
        InventoryLog.objects.create(
            product=product,
            sku_id=sku_id,
            change_type='lock',
            quantity=-quantity,
            reason=reason,
            created_by=operator
        )
        
        return True

    @staticmethod
    @transaction.atomic
    def release_stock(product_id: int, quantity: int, reason: str = 'order_cancelled', operator=None, sku_id: int = None) -> bool:
        """释放库存
        
        Args:
            product_id: 商品ID
            quantity: 释放数量
            reason: 释放原因
            operator: 操作人（可选）
            sku_id: SKU ID（可选）
            
        Returns:
            bool: 释放成功返回True
            
        Raises:
            Product.DoesNotExist: 商品不存在时抛出异常
        """
        if sku_id:
            from catalog.models import ProductSKU
            sku = ProductSKU.objects.select_for_update().get(id=sku_id, product_id=product_id)
            sku.stock = F('stock') + quantity
            sku.save(update_fields=['stock'])
            sku.refresh_from_db()
            product = sku.product
        else:
            product = Product.objects.select_for_update().get(id=product_id)
            product.stock = F('stock') + quantity
            product.save(update_fields=['stock'])
            product.refresh_from_db()
        
        # 记录库存变更
        InventoryLog.objects.create(
            product=product,
            sku_id=sku_id,
            change_type='release',
            quantity=quantity,
            reason=reason,
            created_by=operator
        )
        
        return True

    @staticmethod
    @transaction.atomic
    def adjust_stock(product_id: int, quantity: int, reason: str = 'manual_adjust', operator=None, sku_id: int = None) -> bool:
        """调整库存（增加或减少）
        
        Args:
            product_id: 商品ID
            quantity: 调整数量（正数增加，负数减少）
            reason: 调整原因
            operator: 操作人（可选）
            sku_id: SKU ID（可选）
            
        Returns:
            bool: 调整成功返回True
            
        Raises:
            ValueError: 调整后库存为负数时抛出异常
            Product.DoesNotExist: 商品不存在时抛出异常
        """
        if sku_id:
            from catalog.models import ProductSKU
            sku = ProductSKU.objects.select_for_update().get(id=sku_id, product_id=product_id)
            new_stock = sku.stock + quantity
            if new_stock < 0:
                raise ValueError(f'调整后库存不能为负数，当前库存: {sku.stock}，调整: {quantity}')
            sku.stock = F('stock') + quantity
            sku.save(update_fields=['stock'])
            sku.refresh_from_db()
            product = sku.product
        else:
            product = Product.objects.select_for_update().get(id=product_id)
            new_stock = product.stock + quantity
            if new_stock < 0:
                raise ValueError(f'调整后库存不能为负数，当前库存: {product.stock}，调整: {quantity}')
            product.stock = F('stock') + quantity
            product.save(update_fields=['stock'])
            product.refresh_from_db()
        
        # 记录库存变更
        InventoryLog.objects.create(
            product=product,
            sku_id=sku_id,
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
        released = False
        for item in order.items.select_related('product', 'sku').all():
            released = True
            if getattr(item.product, 'source', None) == getattr(Product, 'SOURCE_HAIER', 'haier'):
                # 海尔库存不需要释放
                continue
            InventoryService.release_stock(
                product_id=item.product_id,
                sku_id=item.sku_id,
                quantity=item.quantity,
                reason='order_cancelled',
                operator=order.user
            )
        if not released and order.product_id:
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
