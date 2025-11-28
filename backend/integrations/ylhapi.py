"""
易理货系统API实现
用于处理订单创建、取消、改约等操作
"""
import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import parse_qs
import logging
import base64
import time
import hashlib

logger = logging.getLogger(__name__)


class YLHSystemAPI:
    """
    易理货系统API实现
    
    用于处理订单相关操作，使用独立的认证系统
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化易理货系统API
        
        Args:
            config: 配置字典，包含以下字段：
                - auth_url: 鉴权URL
                - base_url: API基础URL
                - username: 用户名
                - password: 密码
                - client_id: 客户端ID（用于Basic认证）
                - client_secret: 客户端密钥（用于Basic认证）
        """
        self.auth_url = config.get('auth_url')
        self.base_url = config.get('base_url')
        self.username = config.get('username')
        self.password = config.get('password')
        self.client_id = config.get('client_id', 'open_api_erp')
        self.client_secret = config.get('client_secret', '12345678')
        
        self.access_token = None
        self.token_type = None
        self.token_expiry = None

    @classmethod
    def from_settings(cls):
        from django.conf import settings
        config = {
            'auth_url': getattr(settings, 'YLH_AUTH_URL', 'http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token'),
            'base_url': getattr(settings, 'YLH_BASE_URL', 'http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev'),
            'username': getattr(settings, 'YLH_USERNAME', ''),
            'password': getattr(settings, 'YLH_PASSWORD', ''),
            'client_id': getattr(settings, 'YLH_CLIENT_ID', 'open_api_erp'),
            'client_secret': getattr(settings, 'YLH_CLIENT_SECRET', '12345678'),
        }
        return cls(config)
    
    def _get_basic_auth(self) -> str:
        """
        生成Basic认证头
        
        Returns:
            str: Basic认证字符串
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def authenticate(self) -> bool:
        """
        获取访问令牌
        
        Returns:
            bool: 认证成功返回True
        """
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "system-name": "ylh-open-api",
                "Authorization": self._get_basic_auth()
            }
            
            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password
            }
            
            response = self._post_form(
                self.auth_url,
                data,
                headers,
                timeout=10,
                retries=1,
            )
            
            if response and response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                self.token_type = result.get("token_type", "Bearer")
                expires_in = result.get("expires_in", 3600)
                # 提前10分钟刷新token
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 600)
                logger.info("YLH System authentication successful")
                return True
            else:
                code = response.status_code if response else 'N/A'
                text = response.text if response else 'No Response'
                logger.error(f"YLH System authentication failed: {code} - {text}")
                return False
        except Exception as e:
            logger.error(f"YLH System authentication error: {str(e)}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        确保已认证
        
        Returns:
            bool: 已认证返回True
        """
        if not self.access_token or not self.token_expiry:
            return self.authenticate()
        
        if datetime.now() >= self.token_expiry:
            logger.info("Token expired, re-authenticating...")
            return self.authenticate()
        
        return True
    
    def _get_auth_header(self) -> str:
        """
        获取认证头
        
        Returns:
            str: 认证头字符串
        """
        return f"{self.token_type} {self.access_token}"

    def _post_form(self, url, data, headers, timeout=10, retries=1):
        for attempt in range(retries + 1):
            try:
                response = requests.post(url, headers=headers, data=data, timeout=timeout)
                if response.status_code == 200:
                    return response
                if attempt < retries:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    return response
            except Exception:
                if attempt < retries:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    return None

    def _post_json(self, url, body, headers, timeout=30, retries=1):
        for attempt in range(retries + 1):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
                if response.status_code == 200:
                    return response
                if attempt < retries:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    return response
            except Exception:
                if attempt < retries:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    return None
    
    def create_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        创建订单（接收水联网订单）
        
        Args:
            order_data: 订单数据，包含以下字段：
                - sourceSystem: 订单来源
                - shopName: 店铺名称
                - sellerCode: 客户八码
                - consigneeName: 收货人姓名
                - consigneeMobile: 收货人手机号
                - onlineNo: 平台订单号
                - soId: 子订单号（唯一）
                - remark: 备注
                - totalQty: 订单总数量
                - totalAmt: 订单总金额
                - createTime: 订单创建时间戳（毫秒）
                - province: 省
                - city: 市
                - area: 区
                - town: 县
                - detailAddress: 详细地址
                - distributionTime: 配送时间（时间戳）
                - installTime: 安装时间（时间戳）
                - governmentOrder: 是否国补订单
                - deliveryInstall: 是否送装一体
                - itemList: 订单明细列表
        
        Returns:
            Dict: 订单创建结果
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            response = self._post_json(
                f"{self.base_url}/api/page/hmm/retailorder/receive-hmm-retail-order",
                order_data,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json"
                },
                timeout=30,
                retries=1,
            )
            
            if response and response.status_code == 200:
                data = response.json()
                return data
            else:
                code = response.status_code if response else 'N/A'
                text = response.text if response else 'No Response'
                logger.error(f"Failed to create order: {code} - {text}")
                return None
        except Exception as e:
            logger.error(f"Create order error: {str(e)}")
            return None
    
    def cancel_order(self, so_id: str, cancel_reason: str, source_system: str, 
                    cancel_time: int = None) -> Optional[Dict[str, Any]]:
        """
        取消订单
        
        Args:
            so_id: 子订单号
            cancel_reason: 取消原因
            source_system: 订单来源系统
            cancel_time: 取消时间（毫秒时间戳，可选）
        
        Returns:
            Dict: 取消结果
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            body = {
                "soId": so_id,
                "cancelTime": str(cancel_time or int(datetime.now().timestamp() * 1000)),
                "cancelReason": cancel_reason,
                "sourceSystem": source_system
            }
            
            response = self._post_json(
                f"{self.base_url}/api/page/hmm/retailorder/cancel-hmm-retail-order",
                body,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json"
                },
                timeout=30,
                retries=1,
            )
            
            if response and response.status_code == 200:
                data = response.json()
                return data
            else:
                code = response.status_code if response else 'N/A'
                text = response.text if response else 'No Response'
                logger.error(f"Failed to cancel order: {code} - {text}")
                return None
        except Exception as e:
            logger.error(f"Cancel order error: {str(e)}")
            return None
    
    def update_distribution_time(self, retail_order_no: str, 
                                distribution_time: int = None, 
                                install_time: int = None) -> Optional[Dict[str, Any]]:
        """
        订单改约（更新配送安装时间）
        
        Args:
            retail_order_no: 巨商汇订单号
            distribution_time: 配送时间（时间戳，时分秒必须为23:59:59）
            install_time: 安装时间（时间戳，时分秒必须为23:59:59）
        
        Returns:
            Dict: 更新结果
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            body = {
                "retailOrderNo": retail_order_no
            }
            
            if distribution_time:
                body["distributionTime"] = distribution_time
            if install_time:
                body["installTime"] = install_time
            
            response = self._post_json(
                f"{self.base_url}/api/page/retailorder/hmm/update-distribution-time",
                body,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json"
                },
                timeout=30,
                retries=1,
            )
            
            if response and response.status_code == 200:
                data = response.json()
                return data
            else:
                code = response.status_code if response else 'N/A'
                text = response.text if response else 'No Response'
                logger.error(f"Failed to update distribution time: {code} - {text}")
                return None
        except Exception as e:
            logger.error(f"Update distribution time error: {str(e)}")
            return None
    
    def get_delivery_images(self, order_no: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取配送安装照片
        
        Args:
            order_no: 订单中台订单号
        
        Returns:
            List[Dict]: 照片信息列表
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            body = {
                "orderNo": order_no
            }
            
            response = self._post_json(
                f"{self.base_url}/api/page/retailorder/search/get-retail-order-delivery-img",
                body,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json"
                },
                timeout=30,
                retries=1,
            )
            
            if response and response.status_code == 200:
                data = response.json()
                return data.get('data', []) if isinstance(data, dict) else data
            else:
                code = response.status_code if response else 'N/A'
                text = response.text if response else 'No Response'
                logger.error(f"Failed to get delivery images: {code} - {text}")
                return None
        except Exception as e:
            logger.error(f"Get delivery images error: {str(e)}")
            return None
    
    def get_logistics_by_order_codes(self, order_codes: List[str]) -> Optional[List[Dict[str, Any]]]:
        """
        通过SO单号查询物流单号、物流公司、SN码
        
        Args:
            order_codes: SO单号列表（最多100个）
        
        Returns:
            List[Dict]: 物流信息列表
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            response = self._post_json(
                f"{self.base_url}/api/composite/stock/logistics/get-store-logistics-by-order-code",
                order_codes,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json"
                },
                timeout=30,
                retries=1,
            )
            
            if response and response.status_code == 200:
                data = response.json()
                return data.get('data', []) if isinstance(data, dict) else data
            else:
                code = response.status_code if response else 'N/A'
                text = response.text if response else 'No Response'
                logger.error(f"Failed to get logistics: {code} - {text}")
                return None
        except Exception as e:
            logger.error(f"Get logistics error: {str(e)}")
            return None


class YLHCallbackHandler:
    """
    易理货系统回调处理器
    
    用于处理海尔平台的回调通知（确认订单、取消订单、订单缺货）
    """
    
    def __init__(self, app_key: str, secret: str):
        """
        初始化回调处理器
        
        Args:
            app_key: 应用ID
            secret: 密钥
        """
        self.app_key = app_key
        self.secret = secret
    
    @classmethod
    def from_settings(cls):
        """从Django配置创建实例"""
        from django.conf import settings
        app_key = getattr(settings, 'YLH_CALLBACK_APP_KEY', '')
        secret = getattr(settings, 'YLH_CALLBACK_SECRET', '')
        return cls(app_key, secret)
    
    def generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成签名
        
        签名算法：
        1. 将除sign外的所有"参数+参数值"进行字典排序生成字符串
        2. 将secret加到该字符串的首尾并转小写
        3. 进行MD5加密，加密后再转大写
        
        Args:
            params: 参数字典
        
        Returns:
            str: 签名字符串
        """
        # 过滤空值和sign参数
        filtered_params = {
            k: v for k, v in params.items() 
            if v is not None and str(v).strip() != '' and k.lower() != 'sign'
        }
        
        # 字典排序
        sorted_keys = sorted(filtered_params.keys())
        
        # 拼接字符串
        sign_str = self.secret
        for key in sorted_keys:
            sign_str += f"{key}{filtered_params[key]}"
        sign_str += self.secret
        
        # MD5加密并转大写
        sign = hashlib.md5(sign_str.lower().encode('utf-8')).hexdigest().upper()
        return sign
    
    def verify_sign(self, params: Dict[str, Any]) -> bool:
        """
        验证签名
        
        Args:
            params: 包含sign的参数字典
        
        Returns:
            bool: 签名验证通过返回True
        """
        received_sign = params.get('Sign') or params.get('sign')
        if not received_sign:
            logger.warning("No signature found in callback params")
            return False
        
        calculated_sign = self.generate_sign(params)
        is_valid = calculated_sign == received_sign
        
        if not is_valid:
            logger.warning(f"Signature verification failed. Expected: {calculated_sign}, Got: {received_sign}")
        
        return is_valid
    
    def parse_callback_data(self, form_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析回调数据
        
        Args:
            form_data: 表单数据（application/x-www-form-urlencoded）
        
        Returns:
            Dict: 解析后的数据，包含AppKey, TimeStamp, Sign, Method, Data
        """
        try:
            # 验证签名
            if not self.verify_sign(form_data):
                logger.error("Callback signature verification failed")
                return None
            
            # 解析Data字段
            data_str = form_data.get('Data', '{}')
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
            
            return {
                'AppKey': form_data.get('AppKey'),
                'TimeStamp': form_data.get('TimeStamp'),
                'Sign': form_data.get('Sign'),
                'Method': form_data.get('Method'),
                'Data': data
            }
        except Exception as e:
            logger.error(f"Failed to parse callback data: {str(e)}")
            return None
    
    def handle_order_confirm_callback(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理确认订单回调
        
        Method: hmm.scm_heorder.confirm
        
        Args:
            form_data: 回调表单数据
        
        Returns:
            Dict: 响应数据
        """
        parsed = self.parse_callback_data(form_data)
        if not parsed:
            return self._error_response("签名验证失败")
        
        data = parsed['Data']
        ext_order_no = data.get('ExtOrderNo')  # 海尔订单号
        platform_order_no = data.get('PlatformOrderNo')  # 客户平台订单号
        state = data.get('State')  # 1成功，0失败
        fail_msg = data.get('FailMsg', '')
        
        logger.info(f"Order confirm callback: platform={platform_order_no}, ext={ext_order_no}, state={state}")
        
        # 这里应该调用业务逻辑处理订单确认
        # 例如：更新订单状态、记录海尔订单号等
        # print(data)
        
        return self._success_response({
            "statusCode": "200",
            "message": "成功",
            "platformOrderNo": platform_order_no
        })
    
    def handle_order_cancel_callback(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理取消订单回调
        
        Method: hmm.scm_heorder.cancel
        
        Args:
            form_data: 回调表单数据
        
        Returns:
            Dict: 响应数据
        """
        parsed = self.parse_callback_data(form_data)
        if not parsed:
            return self._error_response("签名验证失败")
        
        data = parsed['Data']
        ext_order_no = data.get('ExtOrderNo')  # 海尔订单号
        platform_order_no = data.get('PlatformOrderNo')  # 客户平台订单号
        state = data.get('State')  # 1成功，0失败
        fail_msg = data.get('FailMsg', '')
        
        logger.info(f"Order cancel callback: platform={platform_order_no}, ext={ext_order_no}, state={state}")
        
        # 这里应该调用业务逻辑处理订单取消
        # 例如：更新订单状态为已取消等
        
        return self._success_response({
            "statusCode": "200",
            "message": "成功",
            "platformOrderNo": platform_order_no
        })
    
    def handle_order_outofstock_callback(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理订单缺货回调
        
        Method: hmm.scm_heorder.oostock
        
        Args:
            form_data: 回调表单数据
        
        Returns:
            Dict: 响应数据
        """
        parsed = self.parse_callback_data(form_data)
        if not parsed:
            return self._error_response("签名验证失败")
        
        data = parsed['Data']
        ext_order_no = data.get('ExtOrderNo')  # 海尔订单号
        platform_order_no = data.get('PlatformOrderNo')  # 客户平台订单号
        state = data.get('State')  # 1成功，0失败
        fail_msg = data.get('FailMsg', '')
        
        logger.info(f"Order out of stock callback: platform={platform_order_no}, ext={ext_order_no}, state={state}")
        
        # 这里应该调用业务逻辑处理订单缺货
        # 例如：通知用户、更新订单状态等
        
        return self._success_response({
            "statusCode": "200",
            "message": "成功",
            "platformOrderNo": platform_order_no
        })
    
    def route_callback(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据Method路由到对应的回调处理方法
        
        Args:
            form_data: 回调表单数据
        
        Returns:
            Dict: 响应数据
        """
        method = form_data.get('Method', '')
        
        if method == 'hmm.scm_heorder.confirm':
            return self.handle_order_confirm_callback(form_data)
        elif method == 'hmm.scm_heorder.cancel':
            return self.handle_order_cancel_callback(form_data)
        elif method == 'hmm.scm_heorder.oostock':
            return self.handle_order_outofstock_callback(form_data)
        else:
            logger.error(f"Unknown callback method: {method}")
            return self._error_response(f"未知的回调方法: {method}")
    
    def _success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成成功响应
        
        Args:
            data: 业务数据
        
        Returns:
            Dict: 响应数据
        """
        return {
            "success": True,
            "code": "success",
            "description": "成功",
            "timeStamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            "data": data
        }
    
    def _error_response(self, message: str, code: str = "error") -> Dict[str, Any]:
        """
        生成错误响应
        
        Args:
            message: 错误消息
            code: 错误码
        
        Returns:
            Dict: 响应数据
        """
        return {
            "success": False,
            "code": code,
            "description": message,
            "timeStamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            "data": {}
        }


if __name__ == "__main__":
    # 测试代码
    config = {
        'auth_url': "http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token",
        'base_url': "http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev",
        'username': "erp",
        'password': "123qwe",
        'client_id': "open_api_erp",
        'client_secret': "12345678",
    }
    
    api = YLHSystemAPI(config)
    
    # 测试认证
    print("=== 测试认证 ===")
    print(f"认证结果: {api.authenticate()}")
    print(f"Access Token: {api.access_token[:50]}..." if api.access_token else "None")
    print(f"Token类型: {api.token_type}")
    print(f"Token过期时间: {api.token_expiry}")
    import time as _t
    import random as _r
    so_id = f"SUB{int(_t.time()*1000)}"
    order_data = {
        "sourceSystem": "TEST_SYSTEM",
        "shopName": "测试店铺",
        "sellerCode": "8800539012",
        "consigneeName": "李四",
        "consigneeMobile": "13900139000",
        "onlineNo": f"HMM{int(_t.time())}",
        "soId": so_id,
        "remark": "测试",
        "totalQty": 1,
        "totalAmt": 1999.98,
        "createTime": int(_t.time()*1000),
        "province": "江苏省",
        "city": "南京市",
        "area": "鼓楼区",
        "detailAddress": "中山北路100号",
        "deliveryInstall": True,
        "itemList": [
            {
                "productCode": "BS01U000N", 
                "itemQty": 1,
                "retailPrice": 1999.98,
               "discountAmount":0,
               "actualPrice":1999.98}
        ]
# | productCode | string | 必须 |  | 商品编码，例如"BS01U000N" |  |
# | itemQty | integer | 必须 |  | 商品数量，例如1，一单一台 |  |
# | retailPrice | number | 必须 |  | 零售价，例如1299.99 |  |
# | discountAmount | number | 必须 |  | 单件商品折扣金额（如果没有就传0），例如100.00 |  |
# | actualPrice | number | 必须 |  | 实际成交价，例如1199.99 |  |
# | isGift | boolean | 非必须 |  | 是否赠品，例如 false |  |
    }
    print("create_order:", api.create_order(order_data))
    print("cancel_order:", api.cancel_order(so_id, "测试取消", "TEST_SYSTEM", int(_t.time()*1000)))
    dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    ts = int(dt.timestamp()*1000)
    print("update_distribution_time:", api.update_distribution_time("SO.TEST.000001", distribution_time=ts, install_time=ts))
    print("get_delivery_images:", api.get_delivery_images("SO.TEST.000001"))
    print("get_logistics_by_order_codes:", api.get_logistics_by_order_codes(["SO.20250514.014572", "SO.TEST.000002"]))
    
    # 测试回调处理器
    print("\n=== 测试回调处理器 ===")
    callback_handler = YLHCallbackHandler(
        app_key="85f46119-e920-4f01-9624-66326c013217",
        secret="8e17bb88a087400bac9ab67e67b138ef"
    )
    
    # 测试签名生成
    print("\n--- 测试签名生成 ---")
    test_params = {
        "AppKey": "85f46119-e920-4f01-9624-66326c013217",
        "TimeStamp": "20230912113528",
        "Method": "hmm.scm_heorder.confirm",
        "Data": '{"ExtOrderNo":"SO.20230912.000001","PlatformOrderNo":"PO20230912001","State":1}'
    }
    generated_sign = callback_handler.generate_sign(test_params)
    print(f"生成的签名: {generated_sign}")
    
    # 测试签名验证
    print("\n--- 测试签名验证 ---")
    test_params_with_sign = test_params.copy()
    test_params_with_sign["Sign"] = generated_sign
    print(f"签名验证结果: {callback_handler.verify_sign(test_params_with_sign)}")
    
    # 测试错误签名
    test_params_with_wrong_sign = test_params.copy()
    test_params_with_wrong_sign["Sign"] = "WRONG_SIGN_12345"
    print(f"错误签名验证结果: {callback_handler.verify_sign(test_params_with_wrong_sign)}")
    
    # 测试确认订单回调
    print("\n--- 测试确认订单回调 ---")
    confirm_callback_data = {
        "AppKey": "85f46119-e920-4f01-9624-66326c013217",
        "TimeStamp": "20230912113528",
        "Method": "hmm.scm_heorder.confirm",
        "Data": json.dumps({
            "ExtOrderNo": "SO.20230912.000001",
            "PlatformOrderNo": "PO20230912001",
            "State": 1
        }),
        "Sign": callback_handler.generate_sign({
            "AppKey": "85f46119-e920-4f01-9624-66326c013217",
            "TimeStamp": "20230912113528",
            "Method": "hmm.scm_heorder.confirm",
            "Data": json.dumps({
                "ExtOrderNo": "SO.20230912.000001",
                "PlatformOrderNo": "PO20230912001",
                "State": 1
            })
        })
    }
    confirm_response = callback_handler.route_callback(confirm_callback_data)
    print(f"确认订单回调响应: {json.dumps(confirm_response, ensure_ascii=False, indent=2)}")
    
    # 测试取消订单回调
    print("\n--- 测试取消订单回调 ---")
    cancel_callback_data = {
        "AppKey": "85f46119-e920-4f01-9624-66326c013217",
        "TimeStamp": "20230912113530",
        "Method": "hmm.scm_heorder.cancel",
        "Data": json.dumps({
            "ExtOrderNo": "SO.20230912.000001",
            "PlatformOrderNo": "PO20230912001",
            "State": 1
        }),
        "Sign": callback_handler.generate_sign({
            "AppKey": "85f46119-e920-4f01-9624-66326c013217",
            "TimeStamp": "20230912113530",
            "Method": "hmm.scm_heorder.cancel",
            "Data": json.dumps({
                "ExtOrderNo": "SO.20230912.000001",
                "PlatformOrderNo": "PO20230912001",
                "State": 1
            })
        })
    }
    cancel_response = callback_handler.route_callback(cancel_callback_data)
    print(f"取消订单回调响应: {json.dumps(cancel_response, ensure_ascii=False, indent=2)}")
    
    # 测试订单缺货回调
    print("\n--- 测试订单缺货回调 ---")
    oostock_callback_data = {
        "AppKey": "85f46119-e920-4f01-9624-66326c013217",
        "TimeStamp": "20230912113532",
        "Method": "hmm.scm_heorder.oostock",
        "Data": json.dumps({
            "ExtOrderNo": "SO.20230912.000001",
            "PlatformOrderNo": "PO20230912001",
            "State": 1,
            "FailMsg": "商品缺货"
        }),
        "Sign": callback_handler.generate_sign({
            "AppKey": "85f46119-e920-4f01-9624-66326c013217",
            "TimeStamp": "20230912113532",
            "Method": "hmm.scm_heorder.oostock",
            "Data": json.dumps({
                "ExtOrderNo": "SO.20230912.000001",
                "PlatformOrderNo": "PO20230912001",
                "State": 1,
                "FailMsg": "商品缺货"
            })
        })
    }
    oostock_response = callback_handler.route_callback(oostock_callback_data)
    print(f"订单缺货回调响应: {json.dumps(oostock_response, ensure_ascii=False, indent=2)}")
    
    # 测试未知方法
    print("\n--- 测试未知回调方法 ---")
    unknown_callback_data = {
        "AppKey": "85f46119-e920-4f01-9624-66326c013217",
        "TimeStamp": "20230912113534",
        "Method": "hmm.scm_heorder.unknown",
        "Data": "{}",
        "Sign": callback_handler.generate_sign({
            "AppKey": "85f46119-e920-4f01-9624-66326c013217",
            "TimeStamp": "20230912113534",
            "Method": "hmm.scm_heorder.unknown",
            "Data": "{}"
        })
    }
    unknown_response = callback_handler.route_callback(unknown_callback_data)
    print(f"未知方法回调响应: {json.dumps(unknown_response, ensure_ascii=False, indent=2)}")
