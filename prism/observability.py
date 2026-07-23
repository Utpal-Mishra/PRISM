"""Logging, audit, and optional error-reporting utilities."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prism.config import settings

LOG_DIR = Path(settings.log_directory)
AUDIT_FILE = LOG_DIR / "audit.jsonl"


def configure_logging() -> logging.Logger:
    """Configure application logging once and return the PRISM logger."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("prism")
    if logger.handlers:
        return logger
    logger.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.app_env,
                release=settings.app_version,
                traces_sample_rate=0.0,
            )
            logger.info("Optional Sentry error reporting enabled")
        except Exception:
            logger.exception("Unable to initialise Sentry")
    return logger


def record_audit_event(event: str, session_id: str, **details: Any) -> None:
    """Append a privacy-conscious activity event to the local audit log."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "session_id": session_id,
        "details": details,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, default=str) + "\n")


def read_audit_log() -> str:
    """Return the current audit log as text for administrator export."""
    return AUDIT_FILE.read_text(encoding="utf-8") if AUDIT_FILE.exists() else ""
