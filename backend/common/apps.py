from django.apps import AppConfig
import logging
import os


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"

    def ready(self):
        # Optional startup self-check for WeChat Pay config
        if os.getenv('SKIP_WECHAT_PAY_CONFIG_CHECK', '').lower() in {'1', 'true', 'yes'}:
            logging.getLogger(__name__).warning('WeChat Pay config startup check skipped')
            return
        try:
            from .health import _check_wechatpay_config
            _check_wechatpay_config(strict=True)
        except Exception as exc:
            logging.getLogger(__name__).error(f'WeChat Pay config check failed: {exc}')
            raise
