"""
支付服务模块

负责处理支付流程、回调验证和防止重复支付。
提供支付金额验证、签名验证等安全功能。
"""

import hashlib
import hmac
import time
import uuid
from decimal import Decimal
from typing import Dict, Optional
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import logging
import re

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
            # 按字典序排序参数（排除签名字段）
            sorted_params = sorted(
                (k, v) for k, v in data.items() if k not in {'sign', 'signature'}
            )
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
    def verify_wechat_callback(data: Dict) -> bool:
        """基于项目配置的简化版微信回调验签。

        说明：正式的微信支付V3回调应使用平台证书与sha256+RSA验签并解密资源。
        这里在未集成官方SDK时使用共享密钥的HMAC校验以便开发测试。
        """
        secret = getattr(settings, 'WECHAT_PAY_SECRET', '')
        signature = data.get('signature') or data.get('sign')
        if not (secret and signature):
            return False
        return PaymentService.verify_callback_signature(data, signature, secret)

    @staticmethod
    def validate_callback_amount(payment, data: Dict) -> tuple[bool, str]:
        """验证回调金额与支付单金额一致。"""
        from decimal import Decimal, InvalidOperation

        amount_fields = ['amount', 'total_amount', 'total_fee', 'money']
        val = None
        for field in amount_fields:
            if data.get(field) is not None:
                val = data.get(field)
                break
        if val is None:
            return True, ''  # 没有金额字段时跳过
        try:
            amt = Decimal(str(val))
        except (InvalidOperation, TypeError):
            return False, '回调金额解析失败'
        if amt != payment.amount:
            return False, f'回调金额不匹配: {amt} != {payment.amount}'
        return True, ''

    @staticmethod
    def generate_wechat_jsapi_params(payment) -> Dict:
        """生成微信JSAPI支付参数（开发/测试用）

        生成符合 wx.requestPayment 所需的参数结构，同时记录基本信息用于日志/对账。
        在缺少真实微信商户配置时，使用占位的 appid/mchid/密钥生成签名，便于前后端联调。
        """
        app_id = getattr(settings, 'WECHAT_APPID', '') or 'mock-appid'
        mch_id = getattr(settings, 'WECHAT_PAY_MCHID', '') or 'mock-mchid'
        sign_key = getattr(settings, 'WECHAT_PAY_SECRET', '') or settings.SECRET_KEY

        # 生成基础字段
        nonce_str = uuid.uuid4().hex
        time_stamp = str(int(time.time()))
        prepay_id = uuid.uuid4().hex  # 占位的prepay_id，真实环境应由微信返回
        package = f'prepay_id={prepay_id}'
        sign_type = 'HMAC-SHA256'

        # 按微信签名规范拼接字符串并生成签名
        sign_payload = '&'.join([
            f'appId={app_id}',
            f'timeStamp={time_stamp}',
            f'nonceStr={nonce_str}',
            f'package={package}',
            f'signType={sign_type}',
        ])
        pay_sign = hmac.new(
            sign_key.encode('utf-8'),
            sign_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return {
            'appId': app_id,
            'mch_id': mch_id,
            'timeStamp': time_stamp,
            'nonceStr': nonce_str,
            'package': package,
            'signType': sign_type,
            'paySign': pay_sign,
            'prepay_id': prepay_id,
            'signPayload': sign_payload,
            'payment_id': payment.id,
            'order_number': getattr(payment.order, 'order_number', ''),
            'amount': str(payment.amount),
            'mchId': mch_id,
        }

    @staticmethod
    def ensure_payment_startable(payment) -> tuple[bool, str]:
        """检查支付是否可开始/继续。

        仅允许 init/processing 状态继续，其他状态返回原因。
        """
        if payment.status in ['cancelled', 'expired', 'failed']:
            return False, f'支付已处于不可继续状态: {payment.status}'
        if timezone.now() > payment.expires_at:
            return False, '支付已过期'
        return True, ''

    @staticmethod
    def ensure_payment_succeed_allowed(payment) -> tuple[bool, str]:
        """检查支付是否可以被标记为成功。"""
        if payment.status == 'succeeded':
            return False, '支付已成功'
        if payment.status in ['cancelled', 'expired', 'failed']:
            return False, f'当前状态不允许标记成功: {payment.status}'
        if timezone.now() > payment.expires_at:
            return False, '支付已过期'
        return True, ''

    @staticmethod
    def calculate_refundable_amount(order) -> Decimal:
        """计算订单当前可退款金额（基于已成功支付减去已成功退款）。"""
        from .models import Refund
        from decimal import Decimal

        paid_amount = sum([p.amount for p in order.payments.filter(status='succeeded')])
        refunded_amount = sum([r.amount for r in Refund.objects.filter(order=order, status='succeeded')])
        available = Decimal(str(paid_amount)) - Decimal(str(refunded_amount))
        return available if available > 0 else Decimal('0')

    @staticmethod
    def check_user_payment_frequency(user, window_seconds: int = 5) -> tuple[bool, str]:
        """简单的支付防抖控制：同一用户在短时间内重复拉起支付会被拒绝。"""
        if not user or not getattr(user, 'id', None):
            return True, ''
        cache_key = f'pay_rate_limit_user_{user.id}'
        last_ts = cache.get(cache_key)
        now_ts = time.time()
        if last_ts and (now_ts - last_ts) < window_seconds:
            return False, f'支付操作过于频繁，请稍后再试'
        cache.set(cache_key, now_ts, timeout=window_seconds)
        return True, ''

    @staticmethod
    def check_amount_threshold(order, max_amount: Decimal | None = None) -> tuple[bool, str]:
        """校验订单支付金额是否超过阈值。

        max_amount 默认读取 settings.PAYMENT_MAX_AMOUNT；用于阻止异常大额支付。
        """
        limit = max_amount or getattr(settings, 'PAYMENT_MAX_AMOUNT', None)
        if limit is None:
            return True, ''
        try:
            if order.total_amount > Decimal(str(limit)):
                return False, f'单笔金额超出限制（上限 {limit}）'
        except Exception:
            pass
        return True, ''

    @staticmethod
    def check_client_frequency(user, client_ip: str = '', device_id: str = '', window_seconds: int = 10, limit: int = 3) -> tuple[bool, str]:
        """基于设备/IP 的短时间限频。

        在 window_seconds 内，同一 device_id 或 IP 超过 limit 次则拒绝。
        device_id 可由前端通过 Header 传递（如 X-Device-Id）。
        """
        keys = []
        if device_id:
            keys.append(f'pay_freq_dev_{device_id}')
        if client_ip:
            keys.append(f'pay_freq_ip_{client_ip}')
        if not keys:
            return True, ''

        for key in keys:
            count = cache.get(key, 0)
            if count >= limit:
                return False, '支付请求过于频繁，请稍后再试'
        # increment
        for key in keys:
            count = cache.get(key, 0)
            cache.set(key, count + 1, timeout=window_seconds)
        return True, ''

    @staticmethod
    def extract_client_ip(request) -> str:
        ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') or ''
        # 取第一个 IP
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        # 简单校验 IPv4/IPv6 格式
        if ip and not re.match(r'^[0-9a-fA-F:\.]+$', ip):
            return ''
        return ip
    
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
        from users.services import create_notification
        
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

        # 创建通知（订阅消息/站内）
        try:
            create_notification(
                payment.order.user,
                title='支付成功',
                content=f'订单 {payment.order.order_number} 支付成功，金额 ¥{payment.amount}',
                ntype='payment',
                metadata={
                    'order_id': payment.order_id,
                    'payment_id': payment.id,
                    'order_number': payment.order.order_number,
                    'status': payment.status,
                    'amount': str(payment.amount),
                    'page': f'pages/order-detail/index?id={payment.order_id}',
                    'subscription_data': {
                        'thing1': {'value': f'订单 {payment.order.order_number}'[:20]},
                        'time2': {'value': timezone.localtime(payment.updated_at).strftime('%Y-%m-%d %H:%M') if payment.updated_at else ''},
                        'thing3': {'value': f'支付成功，金额¥{payment.amount}'[:20]},
                    },
                }
            )
        except Exception:
            pass

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
