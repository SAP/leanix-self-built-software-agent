"""Structured logging configuration for the MCP server.

This module configures structlog for structured logging with JSON output in production
and pretty console output for local development.
"""

import logging
import sys
from typing import Any

import structlog

from src.config.config import DEFAULT_IS_LOCAL

DEFAULT_LOG_FORMAT = "%(message)s"
TIMESTAMP_FORMAT_ISO = "iso"

def configure_structlog() -> None:
    """Configure structlog for the Json format.

    Sets up structured logging with:
    - JSON output for production environments
    - Pretty console output for local development
    - Context variables integration
    - Standard library logging integration
    """

    # Configure standard library logging first
    logging.basicConfig(
        format=DEFAULT_LOG_FORMAT,
        stream=sys.stdout,
        level=logging.INFO,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt=TIMESTAMP_FORMAT_ISO, utc=True),
        structlog.processors.CallsiteParameterAdder(
            {structlog.processors.CallsiteParameter.LINENO}
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if DEFAULT_IS_LOCAL:
        final_processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        final_processors = [*shared_processors, structlog.processors.JSONRenderer()]

    structlog.configure(
        processors=final_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the calling module's name.

    Returns:
        A configured structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
