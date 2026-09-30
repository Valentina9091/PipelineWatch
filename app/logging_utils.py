import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("pipelinewatch")
if not logger.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def log_event(level: str, event: str, **fields) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "service": "pipelinewatch",
        "event": event,
        **fields,
    }
    message = json.dumps(payload, default=str, separators=(",", ":"))
    getattr(logger, level.lower(), logger.info)(message)
