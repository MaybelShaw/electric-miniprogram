import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class HaierAPI:
    def __init__(self, config: Dict[str, Any]):
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.token_url = config.get('token_url')
        self.base_url = config.get('base_url')
        self.customer_code = config.get('customer_code')
        self.send_to_code = config.get('send_to_code')
        self.supplier_code = config.get('supplier_code', '1001')
        self.password = config.get('password')
        self.seller_password = config.get('seller_password')
        self.customer_password = config.get('customer_password', self.password)
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
        })

    def authenticate(self) -> bool:
        try:
            body = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
            }
            res = requests.post(self.token_url, headers={'Content-Type': 'application/json'}, data=json.dumps(body), timeout=10)
            if res.status_code != 200:
                logger.error(f'haier auth failed: {res.status_code} {res.text}')
                return False
            data = res.json() if res.text else {}
            token = data.get('access_token') or data.get('token') or (data.get('data') or {}).get('access_token') or (data.get('data') or {}).get('token')
            if not token:
                logger.error('haier auth no token')
                return False
            self.access_token = token
            self.token_type = data.get('token_type', 'Bearer')
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=max(int(expires_in) - 600, 300))
            return True
        except Exception as e:
            logger.error(f'haier auth error: {str(e)}')
            return False

    def _ensure_authenticated(self) -> bool:
        if not self.access_token or not self.token_expiry or datetime.now() >= self.token_expiry:
            return self.authenticate()
        return True

    def _auth_headers(self) -> Dict[str, str]:
        return {'Authorization': f'{self.access_token}', 'Content-Type': 'application/json'}

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
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
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
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
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
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
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
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
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
            res = requests.post(url, headers=self._auth_headers(), data=json.dumps(body), timeout=30)
            if res.status_code != 200:
                logger.error(f'haier balance failed: {res.status_code} {res.text}')
                return None
            data = res.json()
            return data if isinstance(data, dict) else {'data': data}
        except Exception as e:
            logger.error(f'haier balance error: {str(e)}')
            return None


if __name__ == '__main__':
    test_config = {
        'client_id': '7RKuo0yBew5yRAq9oSwZw8PseXkNHpLb',
        'client_secret': 'y8Dt0YYDoQSY3DphKa79XkfpWoDqPnGp',
        'token_url': 'https://openplat-test.haier.net/oauth2/auth',
        'base_url': 'https://openplat-test.haier.net',
        'customer_code': '8800627808',
        'send_to_code': '8800627808',
        'supplier_code': '1001',
        'password': 'Test,123',
        'seller_password': 'Test,123',
    }
    api = HaierAPI(test_config)
    ok = api.authenticate()
    print('auth:', ok)
    if ok:
        prods = api.get_products(product_codes=['NQ0054000'])
        print('products sample:', str(prods)[:200])
        prices = api.get_product_prices(['NQ0054000'])
        print('prices sample:', str(prices)[:200])
        stock = api.check_stock('NQ0054000', '110101')
        print('stock sample:', str(stock)[:200])
        logistics = api.get_logistics_info('SO.20190106.000003', 'SO.20190106.000003.F1', 12345)
        print('logistics sample:', str(logistics)[:200])
        balance = api.get_account_balance()
        print('balance sample:', str(balance)[:200])
