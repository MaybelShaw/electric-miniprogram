"""
订单和销售数据统计服务

提供销售汇总、热销商品排行、每日销售统计等功能
支持缓存优化以提升查询性能
"""

from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional


class OrderAnalytics:
    """订单和销售数据统计服务"""
    
    # 缓存超时时间（秒）
    CACHE_TIMEOUT = 300  # 5分钟
    
    @classmethod
    def get_sales_summary(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取销售汇总统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
        
        Returns:
            包含订单数、总金额、平均金额的字典
        """
        from orders.models import Order
        
        # 生成缓存键
        cache_key = f'sales_summary_{start_date}_{end_date}'
        result = cache.get(cache_key)
        
        if result is not None:
            return result
        
        # 查询已完成的订单
        queryset = Order.objects.filter(status='completed')
        
        # 按日期范围筛选
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # 聚合统计
        result = queryset.aggregate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount'),
            avg_amount=Avg('total_amount')
        )
        
        # 处理None值
        result['total_orders'] = result['total_orders'] or 0
        result['total_amount'] = result['total_amount'] or Decimal('0.00')
        result['avg_amount'] = result['avg_amount'] or Decimal('0.00')
        
        # 缓存结果
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        
        return result
    
    @classmethod
    def get_top_products(
        cls,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict]:
        """
        获取热销商品排行
        
        Args:
            limit: 返回的商品数量
            days: 统计周期（天数）
        
        Returns:
            热销商品列表，包含商品ID、名称、销量、销售额
        """
        from orders.models import Order
        
        # 生成缓存键
        cache_key = f'top_products_{limit}_{days}'
        result = cache.get(cache_key)
        
        if result is not None:
            return result
        
        # 计算起始日期
        since = timezone.now() - timedelta(days=days)
        
        # 查询热销商品
        result = list(
            Order.objects.filter(
                status='completed',
                created_at__gte=since
            )
            .values('product__id', 'product__name')
            .annotate(
                total_quantity=Sum('quantity'),
                total_amount=Sum('total_amount')
            )
            .order_by('-total_quantity')[:limit]
        )
        
        # 缓存结果
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        
        return result
    
    @classmethod
    def get_daily_sales(
        cls,
        days: int = 30
    ) -> List[Dict]:
        """
        获取每日销售统计
        
        Args:
            days: 统计周期（天数）
        
        Returns:
            每日销售数据列表，包含日期、订单数、销售额
        """
        from orders.models import Order
        
        # 生成缓存键
        cache_key = f'daily_sales_{days}'
        result = cache.get(cache_key)
        
        if result is not None:
            return result
        
        # 计算起始日期
        since = timezone.now() - timedelta(days=days)
        
        # 查询每日销售数据
        result = list(
            Order.objects.filter(
                status='completed',
                created_at__gte=since
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                orders=Count('id'),
                amount=Sum('total_amount')
            )
            .order_by('date')
        )
        
        # 缓存结果
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        
        return result
    
    @classmethod
    def get_user_growth(
        cls,
        days: int = 30
    ) -> List[Dict]:
        """
        获取用户增长统计
        
        Args:
            days: 统计周期（天数）
        
        Returns:
            每日新增用户数据列表
        """
        from users.models import User
        
        # 生成缓存键
        cache_key = f'user_growth_{days}'
        result = cache.get(cache_key)
        
        if result is not None:
            return result
        
        # 计算起始日期
        since = timezone.now() - timedelta(days=days)
        
        # 查询每日新增用户
        result = list(
            User.objects.filter(
                date_joined__gte=since
            )
            .annotate(date=TruncDate('date_joined'))
            .values('date')
            .annotate(new_users=Count('id'))
            .order_by('date')
        )
        
        # 缓存结果
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        
        return result
    
    @classmethod
    def get_order_status_distribution(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取订单状态分布统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
        
        Returns:
            各状态订单数量的字典
        """
        from orders.models import Order
        
        # 生成缓存键
        cache_key = f'order_status_dist_{start_date}_{end_date}'
        result = cache.get(cache_key)
        
        if result is not None:
            return result
        
        # 查询订单
        queryset = Order.objects.all()
        
        # 按日期范围筛选
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # 按状态分组统计
        result = {}
        for status, label in Order.STATUS_CHOICES:
            count = queryset.filter(status=status).count()
            result[status] = {
                'label': label,
                'count': count
            }
        
        # 缓存结果
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        
        return result
    
    @classmethod
    def invalidate_cache(cls, cache_keys: Optional[List[str]] = None):
        """
        清除缓存
        
        Args:
            cache_keys: 要清除的缓存键列表，如果为None则清除所有统计缓存
        """
        if cache_keys is None:
            # 清除所有统计相关的缓存
            # 由于Django缓存不支持通配符删除，我们需要手动清除已知的缓存键
            # 这里使用一个简单的策略：清除所有可能的缓存键组合
            
            # 清除销售汇总缓存
            for start_date in [None, '2024-01-01', '2024-06-01', '2024-11-01']:
                for end_date in [None, '2024-12-31']:
                    cache_key = f'sales_summary_{start_date}_{end_date}'
                    cache.delete(cache_key)
            
            # 清除热销商品缓存
            for limit in [5, 10, 20, 50]:
                for days in [7, 14, 30, 60, 90]:
                    cache_key = f'top_products_{limit}_{days}'
                    cache.delete(cache_key)
            
            # 清除每日销售缓存
            for days in [7, 14, 30, 60, 90]:
                cache_key = f'daily_sales_{days}'
                cache.delete(cache_key)
            
            # 清除用户增长缓存
            for days in [7, 14, 30, 60, 90]:
                cache_key = f'user_growth_{days}'
                cache.delete(cache_key)
            
            # 清除订单状态分布缓存
            for start_date in [None, '2024-01-01', '2024-06-01', '2024-11-01']:
                for end_date in [None, '2024-12-31']:
                    cache_key = f'order_status_dist_{start_date}_{end_date}'
                    cache.delete(cache_key)
        else:
            # 清除指定的缓存键
            cache.delete_many(cache_keys)
    
    @classmethod
    def on_order_status_changed(cls, order_id: int):
        """
        订单状态变更时调用，用于清除相关缓存
        
        Args:
            order_id: 订单ID
        """
        # 清除所有统计缓存，因为订单状态变更可能影响多个统计指标
        cls.invalidate_cache()
    
    @classmethod
    def on_order_created(cls, order_id: int):
        """
        订单创建时调用，用于清除相关缓存
        
        Args:
            order_id: 订单ID
        """
        # 清除所有统计缓存
        cls.invalidate_cache()
