"""
易理货系统API实现
用于处理订单创建、取消、改约等操作
"""
import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import base64
import time

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
            {"productCode": "BS01U000N", "qty": 1, "price": 1999.98}
        ]
    }
    print("create_order:", api.create_order(order_data))
    print("cancel_order:", api.cancel_order(so_id, "测试取消", "TEST_SYSTEM", int(_t.time()*1000)))
    dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    ts = int(dt.timestamp()*1000)
    print("update_distribution_time:", api.update_distribution_time("SO.TEST.000001", distribution_time=ts, install_time=ts))
    print("get_delivery_images:", api.get_delivery_images("SO.TEST.000001"))
    print("get_logistics_by_order_codes:", api.get_logistics_by_order_codes(["SO.TEST.000001", "SO.TEST.000002"]))
