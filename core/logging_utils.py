from __future__ import annotations

import json
import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **context: Any) -> None:
    serialized_context = json.dumps(context, default=str, sort_keys=True)
    logger.log(level, "event=%s context=%s", event, serialized_context)
