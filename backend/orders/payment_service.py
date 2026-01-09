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
import json
import base64
import pathlib
import requests
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
    def _debug_enabled() -> bool:
        return getattr(settings, 'WECHAT_PAY_DEBUG', False)

    @staticmethod
    def _log_debug(message: str, extra: Optional[Dict] = None):
        if getattr(settings, 'WECHAT_PAY_DEBUG', False):
            logger.info(f'[WECHAT_PAY_DEBUG] {message} | {extra or {}}')
    
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

        amount_fields = ['amount', 'total_amount', 'total_fee', 'money', 'total']
        val = None
        for field in amount_fields:
            if data.get(field) is not None:
                val = data.get(field)
                break
        if val is None:
            return True, ''  # 没有金额字段时跳过
        if isinstance(val, dict):
            for key in ['total', 'total_fee', 'payer_total']:
                if val.get(key) is not None:
                    try:
                        cents = Decimal(str(val[key]))
                        val = cents / Decimal('100')
                    except (InvalidOperation, TypeError):
                        return False, '回调金额解析失败'
                    break
        try:
            amt = Decimal(str(val))
        except (InvalidOperation, TypeError):
            return False, '回调金额解析失败'
        if amt != payment.amount:
            return False, f'回调金额不匹配: {amt} != {payment.amount}'
        return True, ''

    def _load_private_key():
        key_path = getattr(settings, 'WECHAT_PAY_PRIVATE_KEY_PATH', '')
        if not key_path:
            return None
        path = pathlib.Path(key_path)
        if not path.exists():
            return None
        with path.open('rb') as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    @staticmethod
    def _sign_rsa(message: str) -> str:
        private_key = PaymentService._load_private_key()
        if not private_key:
            raise RuntimeError('微信支付私钥未配置')
        signature = private_key.sign(
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def create_wechat_unified_order(payment, openid: str, client_ip: str = '') -> Optional[Dict]:
        """调用微信JSAPI统一下单，返回 prepay_id 和 wx.requestPayment 参数。"""
        if not openid:
            raise ValueError('缺少 openid，无法发起微信支付')

        appid = getattr(settings, 'WECHAT_APPID', '')
        mchid = getattr(settings, 'WECHAT_PAY_MCHID', '')
        notify_url = getattr(settings, 'WECHAT_PAY_NOTIFY_URL', '')
        serial_no = getattr(settings, 'WECHAT_PAY_SERIAL_NO', '')
        private_key = PaymentService._load_private_key()
        api_v3_key = getattr(settings, 'WECHAT_PAY_API_V3_KEY', '')
        if not (appid and mchid and notify_url and serial_no and private_key and api_v3_key):
            raise RuntimeError('微信支付配置不完整，请检查商户号、appid、notify_url、证书序列号、私钥及APIv3密钥')

        total_cents = int((Decimal(payment.amount) * 100).quantize(Decimal('1')))
        body = {
            "appid": appid,
            "mchid": mchid,
            "description": f"订单{payment.order.order_number}",
            "out_trade_no": payment.order.order_number,
            "notify_url": notify_url,
            "amount": {
                "total": total_cents,
                "currency": "CNY"
            },
            "payer": {"openid": openid},
            "attach": json.dumps({"payment_id": payment.id}),
        }
        if client_ip:
            body["scene_info"] = {"payer_client_ip": client_ip}

        json_body = json.dumps(body, separators=(',', ':'))
        nonce_str = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        canonical_url = '/v3/pay/transactions/jsapi'
        message = f"POST\n{canonical_url}\n{timestamp}\n{nonce_str}\n{json_body}\n"
        signature = PaymentService._sign_rsa(message)

        auth_header = (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{mchid}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{serial_no}"'
        )

        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json',
            'Authorization': auth_header,
        }

        PaymentService._log_debug('jsapi request body', {'body': body, 'client_ip': client_ip})

        resp = requests.post(
            'https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi',
            data=json_body,
            headers=headers,
            timeout=10
        )
        if resp.status_code >= 300:
            raise RuntimeError(f'统一下单失败: {resp.status_code} {resp.text}')
        prepay_id = resp.json().get('prepay_id')
        if not prepay_id:
            raise RuntimeError('统一下单未返回prepay_id')

        pay_package = f'prepay_id={prepay_id}'
        pay_message = f"{appid}\n{timestamp}\n{nonce_str}\n{pay_package}\n"
        pay_sign = PaymentService._sign_rsa(pay_message)

        pay_params = {
            'appId': appid,
            'timeStamp': timestamp,
            'nonceStr': nonce_str,
            'package': pay_package,
            'signType': 'RSA',
            'paySign': pay_sign,
            'prepay_id': prepay_id,
            'mchId': mchid,
            'total': total_cents,
            'total_fee': total_cents,
            'payment_id': payment.id,
            'order_number': payment.order.order_number,
            'amount': str(payment.amount),
        }
        PaymentService._log_debug('jsapi pay params created', {'prepay_id': prepay_id, 'pay_params': pay_params})
        return pay_params

    @staticmethod
    def _load_wechat_public_key() -> tuple:
        """加载微信支付回调验签所需的公钥或平台证书。

        优先使用 WECHAT_PAY_PUBLIC_KEY_PATH（公钥文件），否则回退到 WECHAT_PAY_PLATFORM_CERT_PATH（证书）。
        返回 (public_key, serial)；若从证书读取将附带序列号。
        """
        key_path = getattr(settings, 'WECHAT_PAY_PUBLIC_KEY_PATH', '') or getattr(settings, 'WECHAT_PAY_PLATFORM_CERT_PATH', '')
        if not key_path:
            raise RuntimeError('微信支付公钥未配置')
        path = pathlib.Path(key_path)
        if not path.exists():
            raise RuntimeError(f'微信支付公钥文件不存在: {key_path}')
        data = path.read_bytes()
        # 尝试直接作为公钥加载
        try:
            pub = serialization.load_pem_public_key(data)
            return pub, None
        except Exception:
            try:
                pub = serialization.load_der_public_key(data)
                return pub, None
            except Exception:
                pass
        # 尝试作为证书加载（兼容原有平台证书方式）
        try:
            cert = x509.load_pem_x509_certificate(data)
        except Exception:
            cert = x509.load_der_x509_certificate(data)
        serial = format(cert.serial_number, 'X').upper() if cert else None
        return cert.public_key(), serial

    @staticmethod
    def verify_wechat_http_signature(headers: Dict[str, str], body: str) -> bool:
        """使用平台证书验证微信回调 HTTP 头签名。"""
        try:
            normalized = {str(k).lower(): v for k, v in (headers or {}).items()}
            signature = normalized.get('wechatpay-signature')
            timestamp = normalized.get('wechatpay-timestamp')
            nonce = normalized.get('wechatpay-nonce')
            serial = normalized.get('wechatpay-serial')
            if not all([signature, timestamp, nonce]):
                return False

            pub_key, cert_serial = PaymentService._load_wechat_public_key()
            message = f"{timestamp}\n{nonce}\n{body}\n".encode('utf-8')
            sig_bytes = base64.b64decode(signature)
            pub_key.verify(
                sig_bytes,
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            expected_serial = getattr(settings, 'WECHAT_PAY_PUBLIC_KEY_ID', '') or cert_serial
            if serial and expected_serial and serial.upper() != expected_serial.upper():
                logger.warning('微信平台公钥ID不匹配: header=%s expected=%s', serial, expected_serial)
                return False
            return True
        except Exception as exc:
            logger.error('微信回调验签失败: %s', exc)
            return False

    @staticmethod
    def decrypt_wechat_resource(resource: Dict) -> Dict:
        """解密微信支付回调 resource 数据。"""
        api_key = getattr(settings, 'WECHAT_PAY_API_V3_KEY', '')
        if not api_key:
            raise RuntimeError('微信支付 APIv3 密钥未配置')
        if not resource:
            raise RuntimeError('缺少回调资源数据')
        ciphertext = resource.get('ciphertext')
        nonce = resource.get('nonce')
        assoc = resource.get('associated_data')
        if not (ciphertext and nonce):
            raise RuntimeError('回调资源字段不完整')

        aesgcm = AESGCM(api_key.encode('utf-8'))
        plaintext = aesgcm.decrypt(
            nonce=nonce.encode('utf-8'),
            data=base64.b64decode(ciphertext),
            associated_data=assoc.encode('utf-8') if assoc else None
        )
        return json.loads(plaintext.decode('utf-8'))

    @staticmethod
    def _extract_payment_from_attach(attach) -> Optional[int]:
        """解析回调 attach 中的 payment_id."""
        if attach is None:
            return None
        if isinstance(attach, dict):
            pid = attach.get('payment_id') or attach.get('paymentId')
            if pid:
                try:
                    return int(pid)
                except Exception:
                    return None
        if isinstance(attach, str):
            try:
                parsed = json.loads(attach)
                if isinstance(parsed, dict):
                    return PaymentService._extract_payment_from_attach(parsed)
            except Exception:
                pass
            if attach.isdigit():
                return int(attach)
            if 'payment_id=' in attach:
                try:
                    return int(attach.split('payment_id=')[-1].split('&')[0])
                except Exception:
                    return None
        return None

    @staticmethod
    def parse_wechat_callback(request) -> tuple[Optional[Dict], Optional[str]]:
        """
        解析并验证微信支付回调，返回包含交易数据的字典。

        返回 (result, error)，其中 result 包含:
        {
            'payment': Payment,
            'transaction': dict,
            'trade_state': str,
            'transaction_id': str,
            'amount_decimal': Decimal,
        }
        """
        raw_body = request.body.decode('utf-8') if getattr(request, 'body', None) else ''
        headers = getattr(request, 'headers', {}) or {}
        if not raw_body:
            return None, '回调体为空'
        try:
            payload = json.loads(raw_body)
        except Exception:
            return None, '回调内容不是有效的JSON'

        PaymentService._log_debug('wechat callback raw', {
            'headers': dict(headers),
            'body': raw_body
        })

        if not PaymentService.verify_wechat_http_signature(headers, raw_body):
            return None, '回调签名验证失败'

        resource = payload.get('resource')
        try:
            transaction = PaymentService.decrypt_wechat_resource(resource)
        except Exception as exc:
            return None, f'回调资源解密失败: {exc}'
        PaymentService._log_debug('wechat callback parsed', {'transaction': transaction})

        from .models import Payment, Order
        mchid = getattr(settings, 'WECHAT_PAY_MCHID', '')
        appid = getattr(settings, 'WECHAT_APPID', '')
        if mchid and transaction.get('mchid') and transaction['mchid'] != mchid:
            return None, '商户号不匹配'
        if appid and transaction.get('appid') and transaction['appid'] != appid:
            return None, 'appid 不匹配'

        out_trade_no = transaction.get('out_trade_no')
        attach = transaction.get('attach')
        payment = None
        pid = PaymentService._extract_payment_from_attach(attach)
        if pid:
            payment = Payment.objects.filter(id=pid).first()
        if payment is None and out_trade_no:
            try:
                order = Order.objects.get(order_number=out_trade_no)
                payment = Payment.objects.filter(order=order).order_by('-created_at').first()
            except Order.DoesNotExist:
                payment = None
        if payment is None:
            return None, '未找到对应的支付记录'

        amount_total = None
        try:
            amount_total = transaction.get('amount', {}).get('total')
            amount_decimal = (Decimal(str(amount_total)) / Decimal('100')) if amount_total is not None else None
        except Exception:
            return None, '金额字段解析失败'

        if amount_decimal is not None and amount_decimal != payment.amount:
            return None, '回调金额与支付记录不一致'

        if out_trade_no and payment.order.order_number != out_trade_no:
            return None, '订单号不匹配'

        return {
            'payment': payment,
            'transaction': transaction,
            'trade_state': transaction.get('trade_state'),
            'transaction_id': transaction.get('transaction_id'),
            'amount_decimal': amount_decimal,
            'out_trade_no': out_trade_no,
        }, None

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
            order_amount = order.actual_amount or order.total_amount
            if order_amount > Decimal(str(limit)):
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
            order_amount = order.actual_amount or order.total_amount
            difference = abs(order_amount - payment_amount)
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
                order_amount = order.actual_amount or order.total_amount
                return False, f'支付金额{payment_amount}与订单金额{order_amount}不一致'
        
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
