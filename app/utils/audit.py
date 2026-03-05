import json
from datetime import datetime, timezone

from app.config import settings
from app.utils.logger import logger


def audit_event(action: str, status: str, details: dict | None = None) -> None:
    if not settings.audit_enabled:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "audit",
        "action": action,
        "status": status,
        "details": details or {},
    }
    logger.info("AUDIT %s", json.dumps(payload, sort_keys=True))
