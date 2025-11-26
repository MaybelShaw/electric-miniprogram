"""
支付服务模块

负责处理支付流程、回调验证和防止重复支付。
提供支付金额验证、签名验证等安全功能。
"""

import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Optional
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """支付服务类
    
    负责处理支付相关的业务逻辑，包括：
    - 支付回调签名验证
    - 支付成功处理
    - 支付金额验证
    - 防止重复支付
    """
    
    @staticmethod
    def verify_callback_signature(data: Dict, signature: str, secret: str) -> bool:
        """验证支付回调签名
        
        使用HMAC-SHA256算法验证回调数据的真实性。
        按字典序排序参数，然后计算签名进行比对。
        
        Args:
            data: 回调数据字典
            signature: 回调中提供的签名
            secret: 签名密钥
            
        Returns:
            bool: 签名验证成功返回True，否则返回False
            
        Example:
            >>> data = {'order_id': '123', 'amount': '100.00'}
            >>> signature = 'abc123...'
            >>> secret = 'my_secret_key'
            >>> PaymentService.verify_callback_signature(data, signature, secret)
            True
        """
        try:
            # 按字典序排序参数
            sorted_params = sorted(data.items())
            sign_str = '&'.join([f'{k}={v}' for k, v in sorted_params])
            
            # 计算签名
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                sign_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 使用恒定时间比较防止时序攻击
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f'签名验证异常: {str(e)}')
            return False
    
    @staticmethod
    def check_payment_amount(order, payment_amount: Decimal) -> bool:
        """验证支付金额
        
        检查支付金额是否与订单金额一致。
        允许0.01元的误差以处理浮点数精度问题。
        
        Args:
            order: Order对象
            payment_amount: 支付金额
            
        Returns:
            bool: 金额验证成功返回True，否则返回False
            
        Raises:
            ValueError: 如果payment_amount不是Decimal类型
            
        Example:
            >>> from decimal import Decimal
            >>> order = Order.objects.get(id=1)
            >>> PaymentService.check_payment_amount(order, Decimal('100.00'))
            True
        """
        try:
            # 确保payment_amount是Decimal类型
            if not isinstance(payment_amount, Decimal):
                payment_amount = Decimal(str(payment_amount))
            
            # 允许0.01元的误差
            difference = abs(order.total_amount - payment_amount)
            return difference < Decimal('0.01')
        except Exception as e:
            logger.error(f'金额验证异常: {str(e)}')
            return False
    
    @staticmethod
    @transaction.atomic
    def process_payment_success(
        payment_id: int,
        transaction_id: str = None,
        operator=None
    ):
        """处理支付成功
        
        处理支付成功的业务逻辑，包括：
        1. 防止重复处理已成功的支付
        2. 更新支付状态
        3. 记录交易ID
        4. 使用状态机更新订单状态
        5. 记录完整的操作日志
        
        Args:
            payment_id: 支付记录ID
            transaction_id: 第三方支付系统的交易ID（可选）
            operator: 操作人（可选）
            
        Returns:
            Payment: 更新后的支付对象
            
        Raises:
            Payment.DoesNotExist: 支付记录不存在
            ValueError: 订单状态转换失败
            
        Example:
            >>> payment = PaymentService.process_payment_success(
            ...     payment_id=1,
            ...     transaction_id='wx_trans_123',
            ...     operator=user
            ... )
        """
        from .models import Payment
        from .state_machine import OrderStateMachine
        
        # 使用select_for_update锁定支付记录，防止并发处理
        payment = Payment.objects.select_for_update().get(id=payment_id)
        
        # 防止重复处理已成功的支付
        if payment.status == 'succeeded':
            logger.warning(f'支付记录#{payment_id}已处理过，忽略重复处理')
            return payment
        
        # 检查支付是否已过期
        if timezone.now() > payment.expires_at:
            logger.warning(f'支付记录#{payment_id}已过期')
            payment.status = 'expired'
            payment.logs.append({
                't': timezone.now().isoformat(),
                'event': 'expired',
                'detail': 'Payment expired before processing'
            })
            payment.save()
            return payment
        
        # 更新支付状态
        payment.status = 'succeeded'
        
        # 记录交易ID
        if transaction_id:
            payment.logs.append({
                't': timezone.now().isoformat(),
                'event': 'transaction_id_recorded',
                'transaction_id': transaction_id
            })
        
        # 记录支付成功事件
        payment.logs.append({
            't': timezone.now().isoformat(),
            'event': 'payment_succeeded',
            'operator': operator.username if operator else 'system',
            'detail': 'Payment processed successfully'
        })
        
        payment.save()
        
        # 使用状态机更新订单状态
        try:
            OrderStateMachine.transition(
                payment.order,
                'paid',
                operator=operator,
                note=f'Payment succeeded with transaction_id: {transaction_id}' if transaction_id else 'Payment succeeded'
            )
            logger.info(f'订单#{payment.order_id}状态已更新为paid')
        except ValueError as e:
            logger.error(f'订单状态转换失败: {str(e)}')
            # 记录状态转换失败的日志，但不中断支付处理
            payment.logs.append({
                't': timezone.now().isoformat(),
                'event': 'order_transition_failed',
                'error': str(e)
            })
            payment.save()
            raise
        
        return payment
    
    @staticmethod
    def validate_payment_creation(order, payment_amount: Decimal = None) -> tuple[bool, str]:
        """验证支付创建的前置条件
        
        在创建支付记录前进行验证，确保：
        1. 订单状态允许支付
        2. 支付金额与订单金额一致
        3. 订单未过期
        
        Args:
            order: Order对象
            payment_amount: 支付金额（可选，如果不提供则使用订单总额）
            
        Returns:
            tuple: (是否验证通过, 错误信息)
            
        Example:
            >>> order = Order.objects.get(id=1)
            >>> is_valid, error_msg = PaymentService.validate_payment_creation(order)
            >>> if is_valid:
            ...     payment = Payment.create_for_order(order)
        """
        # 检查订单状态
        if order.status not in ['pending', 'paid']:
            return False, f'订单状态为{order.status}，不允许支付'
        
        # 检查支付金额
        if payment_amount is not None:
            if not PaymentService.check_payment_amount(order, payment_amount):
                return False, f'支付金额{payment_amount}与订单金额{order.total_amount}不一致'
        
        # 检查订单是否过期（订单创建超过24小时）
        from datetime import timedelta
        if timezone.now() - order.created_at > timedelta(hours=24):
            return False, '订单已过期，请重新创建'
        
        return True, ''
    
    @staticmethod
    def log_payment_event(
        payment_id: int,
        event: str,
        details: Dict = None,
        error: str = None
    ):
        """记录支付事件
        
        为支付记录添加事件日志，用于审计和调试。
        
        Args:
            payment_id: 支付记录ID
            event: 事件类型（如'callback_received', 'signature_verified'等）
            details: 事件详情字典（可选）
            error: 错误信息（可选）
            
        Example:
            >>> PaymentService.log_payment_event(
            ...     payment_id=1,
            ...     event='callback_received',
            ...     details={'provider': 'wechat', 'status': 'SUCCESS'}
            ... )
        """
        from .models import Payment
        
        try:
            payment = Payment.objects.get(id=payment_id)
            
            log_entry = {
                't': timezone.now().isoformat(),
                'event': event,
            }
            
            if details:
                log_entry['details'] = details
            
            if error:
                log_entry['error'] = error
            
            payment.logs.append(log_entry)
            payment.save(update_fields=['logs'])
            
            logger.info(f'支付事件已记录: payment_id={payment_id}, event={event}')
        except Payment.DoesNotExist:
            logger.error(f'支付记录不存在: payment_id={payment_id}')
        except Exception as e:
            logger.error(f'记录支付事件失败: {str(e)}')
