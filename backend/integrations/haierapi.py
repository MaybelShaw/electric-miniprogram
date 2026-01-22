import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)


class HaierAPI:
    def __init__(self, config: Dict[str, Any]):
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.token_url = config.get('token_url')
        self.base_url = (config.get('base_url') or '').rstrip('/')
        self.customer_code = config.get('customer_code')
        self.send_to_code = config.get('send_to_code')
        self.supplier_code = config.get('supplier_code', '1001')
        self.password = config.get('password')
        self.seller_password = config.get('seller_password')
        self.customer_password = config.get('customer_password', self.password)
        self.debug = bool(config.get('debug', False))
        self.access_token: Optional[str] = None
        self.token_type: str = 'Bearer'
        self.token_expiry: Optional[datetime] = None

    @classmethod
    def from_settings(cls):
        from django.conf import settings
        return cls({
            'client_id': getattr(settings, 'HAIER_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'HAIER_CLIENT_SECRET', ''),
            'token_url': getattr(settings, 'HAIER_TOKEN_URL', ''),
            'base_url': getattr(settings, 'HAIER_BASE_URL', ''),
            'customer_code': getattr(settings, 'HAIER_CUSTOMER_CODE', ''),
            'send_to_code': getattr(settings, 'HAIER_SEND_TO_CODE', ''),
            'supplier_code': getattr(settings, 'HAIER_SUPPLIER_CODE', '1001'),
            'password': getattr(settings, 'HAIER_PASSWORD', ''),
            'seller_password': getattr(settings, 'HAIER_SELLER_PASSWORD', ''),
            'debug': getattr(settings, 'INTEGRATIONS_API_DEBUG', False),
        })

    def _mask(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            masked = {}
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in ('authorization', 'client_secret', 'password', 'sellerpassword', 'customerpassword', 'token', 'access_token', 'secret', 'sign'):
                    masked[k] = '***'
                else:
                    masked[k] = self._mask(v)
            return masked
        if isinstance(obj, list):
            return [self._mask(v) for v in obj]
        if isinstance(obj, str) and len(obj) > 800:
            return obj[:800] + '...'
        return obj

    def _debug_log(self, event: str, payload: Dict[str, Any]):
        if not self.debug:
            return
        logger.debug("haier_api_debug %s %s", event, json.dumps(self._mask(payload), ensure_ascii=False, default=str))

    def authenticate(self) -> bool:
        try:
            body = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
            }
            token_urls = [self.token_url]
            if isinstance(self.token_url, str) and self.token_url.endswith('/oauth2/auth'):
                token_urls.append(self.token_url[:-len('/oauth2/auth')] + '/oauth2/token')

            last_res = None
            for url in token_urls:
                started = time.monotonic()
                res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(body), timeout=10)
                elapsed_ms = int((time.monotonic() - started) * 1000)
                last_res = res
                self._debug_log("auth_response", {"url": url, "status_code": res.status_code, "elapsed_ms": elapsed_ms, "text": res.text})
                if res.status_code == 200:
                    data = res.json() if res.text else {}
                    token = (
                        data.get('access_token')
                        or data.get('token')
                        or (data.get('data') or {}).get('access_token')
                        or (data.get('data') or {}).get('token')
                    )
                    if not token:
                        logger.error('haier auth no token')
                        return False
                    self.access_token = token
                    self.token_type = data.get('token_type', 'Bearer') or 'Bearer'
                    expires_in = data.get('expires_in', 3600)
                    self.token_expiry = datetime.now() + timedelta(seconds=max(int(expires_in) - 600, 300))
                    return True

            if last_res is not None:
                logger.error(f'haier auth failed: {last_res.status_code} {last_res.text}')
            else:
                logger.error('haier auth failed: no response')
            return False
        except Exception as e:
            logger.error(f'haier auth error: {str(e)}')
            return False

    def _ensure_authenticated(self) -> bool:
        if not self.access_token or not self.token_expiry or datetime.now() >= self.token_expiry:
            return self.authenticate()
        return True

    def _auth_headers(self) -> Dict[str, str]:
        return {'Authorization': self.access_token or '', 'Content-Type': 'application/json'}

    def get_products(self, product_codes: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
        if not self._ensure_authenticated():
            return None
        url = f'{self.base_url}/yilihuo/jsh-service-goods-mall-search/api/product-info/procurable-products-out/check-procurable-products'
        body: Dict[str, Any] = {
            'customerCode': self.customer_code,
            'supplierCode': self.supplier_code,
            'searchType': 'PTJSH',
            'passWord': self.password,
        }
        if self.send_to_code:
            body['sendToCode'] = self.send_to_code
        if product_codes:
            body['productCodes'] = product_codes[:20]
        try:
            self._debug_log("request", {"method": "POST", "url": url, "body": body})
            started = time.monotonic()
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._debug_log("response", {"method": "POST", "url": url, "status_code": res.status_code, "elapsed_ms": elapsed_ms, "text": res.text})
            if res.status_code != 200:
                logger.error(f'haier products failed: {res.status_code} {res.text}')
                return None
            data = res.json()
            return data if isinstance(data, list) else data.get('data') or data
        except Exception as e:
            logger.error(f'haier products error: {str(e)}')
            return None

    def get_product_prices(self, product_codes: List[str]) -> Optional[List[Dict[str, Any]]]:
        if not self._ensure_authenticated():
            return None
        url = f'{self.base_url}/yilihuo/jsh-service-goods-price/api/goods-price/price-daily-sales/price-query/pt-out-list-price'
        body = {
            'customerCode': self.customer_code,
            'sendToCode': self.send_to_code,
            'productCodes': product_codes[:20],
            'priceType': 'PT',
            'passWord': self.password,
        }
        try:
            self._debug_log("request", {"method": "POST", "url": url, "body": body})
            started = time.monotonic()
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._debug_log("response", {"method": "POST", "url": url, "status_code": res.status_code, "elapsed_ms": elapsed_ms, "text": res.text})
            if res.status_code != 200:
                logger.error(f'haier prices failed: {res.status_code} {res.text}')
                return None
            data = res.json()
            return data if isinstance(data, list) else data.get('data') or data
        except Exception as e:
            logger.error(f'haier prices error: {str(e)}')
            return None

    def check_stock(self, product_code: str, county_code: str, source: str = 'JSH-B') -> Optional[Dict[str, Any]]:
        if not self._ensure_authenticated():
            return None
        url = f'{self.base_url}/yilihuo/jsh-service-stock-mall/api/page/stock/get-available-stock-open'
        body = {
            'salesCode': self.customer_code,
            'senderCode': self.send_to_code,
            'productCode': product_code,
            'countyCode': county_code,
            'source': source,
            'sellerPassword': self.seller_password,
        }
        try:
            self._debug_log("request", {"method": "POST", "url": url, "body": body})
            started = time.monotonic()
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._debug_log("response", {"method": "POST", "url": url, "status_code": res.status_code, "elapsed_ms": elapsed_ms, "text": res.text})
            if res.status_code != 200:
                logger.error(f'haier stock failed: {res.status_code} {res.text}')
                return None
            data = res.json()
            return data if isinstance(data, dict) else {'data': data}
        except Exception as e:
            logger.error(f'haier stock error: {str(e)}')
            return None

    def get_logistics_info(self, order_code: str, delivery_record_code: Optional[str] = None, member_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if not self._ensure_authenticated():
            return None
        url = f'{self.base_url}/yilihuo/ylh-cloud-service-stock/api/page/stock/logistics/sass/get-thirdparty-logistics-info-by-order-code-auth'
        body: Dict[str, Any] = {
            'orderCode': order_code,
            'sellerCode': self.customer_code,
            'sellerPassword': self.seller_password,
        }
        if delivery_record_code:
            body['deliveryRecordCode'] = delivery_record_code
        if member_id is not None:
            body['memberId'] = member_id
        try:
            self._debug_log("request", {"method": "POST", "url": url, "body": body})
            started = time.monotonic()
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._debug_log("response", {"method": "POST", "url": url, "status_code": res.status_code, "elapsed_ms": elapsed_ms, "text": res.text})
            if res.status_code != 200:
                logger.error(f'haier logistics failed: {res.status_code} {res.text}')
                return None
            data = res.json()
            return data if isinstance(data, dict) else {'data': data}
        except Exception as e:
            logger.error(f'haier logistics error: {str(e)}')
            return None

    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        if not self._ensure_authenticated():
            return None
        url = f'{self.base_url}/yilihuo/jsh-service-finance-mall/api/page/account/account-balance-manager/get-payer-account-balance-by-customer-code'
        body = {
            'customerCode': self.customer_code,
            'customerPassword': self.customer_password,
        }
        try:
            self._debug_log("request", {"method": "POST", "url": url, "body": body})
            started = time.monotonic()
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._debug_log("response", {"method": "POST", "url": url, "status_code": res.status_code, "elapsed_ms": elapsed_ms, "text": res.text})
            if res.status_code != 200:
                logger.error(f'haier balance failed: {res.status_code} {res.text}')
                return None
            data = res.json()
            return data if isinstance(data, dict) else {'data': data}
        except Exception as e:
            logger.error(f'haier balance error: {str(e)}')
            return None
