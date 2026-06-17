from django.apps import AppConfig
import logging
import os


def _is_production() -> bool:
    return os.getenv("DJANGO_ENV", "development") == "production"


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"

    def ready(self):
        if _is_production():
            from django.conf import settings

            xframe_middleware = "django.middleware.clickjacking.XFrameOptionsMiddleware"
            if xframe_middleware not in settings.MIDDLEWARE:
                settings.MIDDLEWARE.append(xframe_middleware)

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
