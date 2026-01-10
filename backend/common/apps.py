from django.apps import AppConfig
import logging


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"

    def ready(self):
        # Optional startup self-check for WeChat Pay config
        try:
            from .health import _check_wechatpay_config
            _check_wechatpay_config(strict=True)
        except Exception as exc:
            logging.getLogger(__name__).error(f'WeChat Pay config check failed: {exc}')
            raise
