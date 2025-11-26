"""
订单状态机模块

定义订单的所有可能状态和合法的状态转换规则。
使用状态机模式确保订单状态流转的合法性。
"""

from enum import Enum
from typing import Set, Optional
from django.db import transaction
from django.utils import timezone


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = 'pending'          # 待支付
    PAID = 'paid'                # 待发货
    SHIPPED = 'shipped'          # 待收货
    COMPLETED = 'completed'      # 已完成
    CANCELLED = 'cancelled'      # 已取消
    REFUNDING = 'refunding'      # 退款中
    REFUNDED = 'refunded'        # 已退款


class OrderStateMachine:
    """订单状态机
    
    管理订单状态的转换规则和业务逻辑。
    确保订单状态只能按照定义的规则进行转换。
    """
    
    # 定义允许的状态转换规则
    # 键为当前状态，值为允许转换到的状态集合
    TRANSITIONS = {
        OrderStatus.PENDING: {
            OrderStatus.PAID,        # 支付成功
            OrderStatus.CANCELLED,   # 取消订单
        },
        OrderStatus.PAID: {
            OrderStatus.SHIPPED,     # 发货
            OrderStatus.REFUNDING,   # 申请退款
            OrderStatus.CANCELLED,   # 取消订单（支付后仍可取消）
        },
        OrderStatus.SHIPPED: {
            OrderStatus.COMPLETED,   # 订单完成
            OrderStatus.REFUNDING,   # 申请退款
        },
        OrderStatus.COMPLETED: {
            OrderStatus.REFUNDING,   # 售后退款
        },
        OrderStatus.REFUNDING: {
            OrderStatus.REFUNDED,    # 退款完成
            OrderStatus.PAID,        # 退款取消，恢复已支付状态
        },
        OrderStatus.CANCELLED: set(),      # 已取消，不允许转换
        OrderStatus.REFUNDED: set(),       # 已退款，不允许转换
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """检查状态转换是否合法
        
        Args:
            from_status: 当前状态（字符串）
            to_status: 目标状态（字符串）
            
        Returns:
            bool: 如果转换合法返回True，否则返回False
        """
        try:
            from_enum = OrderStatus(from_status)
            to_enum = OrderStatus(to_status)
            return to_enum in cls.TRANSITIONS.get(from_enum, set())
        except ValueError:
            # 无效的状态值
            return False
    
    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> Set[str]:
        """获取当前状态允许转换到的所有状态
        
        Args:
            current_status: 当前状态（字符串）
            
        Returns:
            Set[str]: 允许转换到的状态集合
        """
        try:
            current_enum = OrderStatus(current_status)
            allowed_enums = cls.TRANSITIONS.get(current_enum, set())
            return {status.value for status in allowed_enums}
        except ValueError:
            return set()
    
    @classmethod
    @transaction.atomic
    def transition(
        cls,
        order,
        new_status: str,
        operator=None,
        note: str = ''
    ):
        """执行状态转换
        
        Args:
            order: Order对象
            new_status: 目标状态（字符串）
            operator: 操作人（User对象，可选）
            note: 转换备注（可选）
            
        Raises:
            ValueError: 如果状态转换不合法
            
        Returns:
            Order: 更新后的订单对象
        """
        # 检查转换是否合法
        if not cls.can_transition(order.status, new_status):
            allowed = cls.get_allowed_transitions(order.status)
            raise ValueError(
                f'不允许从状态 "{order.status}" 转换到 "{new_status}"。'
                f'允许的转换: {allowed}'
            )
        
        old_status = order.status
        
        # 执行状态转换前的业务逻辑
        cls._handle_pre_transition(order, old_status, new_status, operator)
        
        # 更新订单状态
        order.status = new_status
        order.updated_at = timezone.now()
        order.save(update_fields=['status', 'updated_at'])
        
        # 记录状态变更历史
        from .models import OrderStatusHistory
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            operator=operator,
            note=note
        )
        
        # 执行状态转换后的业务逻辑
        cls._handle_post_transition(order, old_status, new_status, operator)
        try:
            from .analytics import OrderAnalytics
            OrderAnalytics.on_order_status_changed(order.id)
        except Exception:
            pass
        
        return order
    
    @classmethod
    def _handle_pre_transition(
        cls,
        order,
        old_status: str,
        new_status: str,
        operator=None
    ):
        """处理状态转换前的业务逻辑
        
        在状态转换前执行必要的验证和准备工作。
        
        Args:
            order: Order对象
            old_status: 原状态
            new_status: 新状态
            operator: 操作人
        """
        # 可在此添加转换前的验证逻辑
        pass
    
    @classmethod
    def _handle_post_transition(
        cls,
        order,
        old_status: str,
        new_status: str,
        operator=None
    ):
        """处理状态转换后的业务逻辑
        
        在状态转换后执行相关的业务操作，如释放库存、发送通知等。
        
        Args:
            order: Order对象
            old_status: 原状态
            new_status: 新状态
            operator: 操作人
        """
        # 订单被取消时，释放库存
        if new_status == OrderStatus.CANCELLED.value:
            cls._handle_order_cancelled(order, operator)
        
        # 订单完成时，更新商品销量
        elif new_status == OrderStatus.COMPLETED.value:
            cls._handle_order_completed(order)
        
        # 退款完成时，释放库存
        elif new_status == OrderStatus.REFUNDED.value:
            cls._handle_order_refunded(order, operator)
        
        # 订单支付成功时，更新商品浏览次数
        elif new_status == OrderStatus.PAID.value:
            cls._handle_order_paid(order)
    
    @classmethod
    def _handle_order_cancelled(cls, order, operator=None):
        """处理订单取消
        
        释放锁定的库存。
        
        Args:
            order: Order对象
            operator: 操作人
        """
        from .services import InventoryService
        
        try:
            InventoryService.release_stock(
                product_id=order.product_id,
                quantity=order.quantity,
                reason='order_cancelled',
                operator=operator
            )
        except Exception as e:
            # 记录错误但不中断流程
            print(f'释放库存失败: {str(e)}')
    
    @classmethod
    def _handle_order_completed(cls, order):
        """处理订单完成
        
        更新商品销量统计。
        
        Args:
            order: Order对象
        """
        from catalog.models import Product
        from django.db.models import F
        
        try:
            Product.objects.filter(id=order.product_id).update(
                sales_count=F('sales_count') + order.quantity
            )
        except Exception as e:
            # 记录错误但不中断流程
            print(f'更新销量失败: {str(e)}')
    
    @classmethod
    def _handle_order_refunded(cls, order, operator=None):
        """处理订单退款完成
        
        释放锁定的库存。
        
        Args:
            order: Order对象
            operator: 操作人
        """
        from .services import InventoryService
        
        try:
            InventoryService.release_stock(
                product_id=order.product_id,
                quantity=order.quantity,
                reason='order_refunded',
                operator=operator
            )
        except Exception as e:
            # 记录错误但不中断流程
            print(f'释放库存失败: {str(e)}')
    
    @classmethod
    def _handle_order_paid(cls, order):
        """处理订单支付成功
        
        可在此添加支付成功后的业务逻辑，如发送通知等。
        
        Args:
            order: Order对象
        """
        # 预留接口，可在此添加支付成功后的业务逻辑
        # 例如：发送支付成功通知、更新用户积分等
        pass
