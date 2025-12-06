"""
WeChat mini program client helpers (access token + subscription message sending).
"""
import logging
from typing import Tuple

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class WeChatMiniProgramClient:
    """Lightweight client for sending mini program subscription messages."""

    def __init__(self, appid: str | None = None, secret: str | None = None):
        self.appid = appid or getattr(settings, 'WECHAT_APPID', '')
        self.secret = secret or getattr(settings, 'WECHAT_SECRET', '')

    def _cache_key(self) -> str:
        return f'wechat_access_token:{self.appid}'

    def get_access_token(self) -> str | None:
        if not self.appid or not self.secret:
            return None

        cached = cache.get(self._cache_key())
        if cached:
            return cached

        try:
            resp = requests.get(
                'https://api.weixin.qq.com/cgi-bin/token',
                params={
                    'grant_type': 'client_credential',
                    'appid': self.appid,
                    'secret': self.secret,
                },
                timeout=5,
            )
            data = resp.json() if resp.content else {}
            token = data.get('access_token')
            expires_in = int(data.get('expires_in', 0) or 0)
            if token:
                cache.set(self._cache_key(), token, max(expires_in - 120, 300))
                return token
            logger.warning('Failed to fetch WeChat access token: %s', data)
        except Exception as exc:
            logger.error('WeChat access token request failed: %s', exc)
        return None

    def send_subscribe_message(
        self,
        touser: str,
        template_id: str,
        page: str | None = None,
        data: dict | None = None,
        lang: str = 'zh_CN',
    ) -> Tuple[bool, str]:
        """Send a subscription message; returns (success, error message)."""
        token = self.get_access_token()
        if not token:
            return False, 'missing_access_token'

        payload = {
            'touser': touser,
            'template_id': template_id,
            'data': data or {},
            'lang': lang,
            'miniprogram_state': 'trial' if getattr(settings, 'DEBUG', False) else 'formal',
        }
        if page:
            payload['page'] = page

        try:
            resp = requests.post(
                f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}',
                json=payload,
                timeout=5,
            )
            resp_data = resp.json() if resp.content else {}
            if resp.status_code == 200 and resp_data.get('errcode') == 0:
                return True, ''
            return False, resp_data.get('errmsg') or f'http_status_{resp.status_code}'
        except Exception as exc:
            logger.error('WeChat subscribe message send failed: %s', exc)
            return False, str(exc)
