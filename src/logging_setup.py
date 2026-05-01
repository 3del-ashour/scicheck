"""Structured logging. Member 1 owns this."""
from __future__ import annotations

import logging

import structlog

from src.config import get_settings


def configure_logging() -> None:
    s = get_settings()
    logging.basicConfig(level=s.log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


def get_logger(name: str):
    return structlog.get_logger(name)
