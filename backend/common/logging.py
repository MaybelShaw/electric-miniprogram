import logging

logger = logging.getLogger(__name__)

def log_security(event: str, detail: str, extra: dict | None = None, level=logging.WARNING):
    """统一的安全/风控日志入口，便于后续接入告警。"""
    payload = {'event': event, 'detail': detail}
    if extra:
        payload.update(extra)
    logger.log(level, payload)

