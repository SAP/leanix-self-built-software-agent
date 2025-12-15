"""Structured logging configuration for SBS AI Discovery Agent.

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

# Custom processor to filter out non-error logs
def filter_errors(_, __, event_dict):
    print(event_dict.get("level") )
    if event_dict.get("level") == "error":
        return event_dict
    else:
        return None

def _create_structlog_processor_chain() -> list[Any]:
    """Create the structlog processor chain based on environment.

    Returns:
        List of structlog processors
    """
    TIMESTAMP_FORMAT_ISO = "iso"

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
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    return shared_processors


def _configure_stdlib_logging(log_level: int, handler: logging.Handler) -> None:
    """Configure Python's standard library logging.

    Args:
        log_level: The logging level to set
        handler: The logging handler to attach
    """

    # List of third-party loggers that should use structured logging
    third_party_loggers = [
        # Uvicorn and FastAPI related
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "starlette",
        # HTTP clients
        "httpx",
        "httpcore",
        # GraphQL and transport
        "gql",
        "gql.transport",
        # FastMCP related
        "fastmcp",
        # Other common libraries
        "opentelemetry",
    ]

    # Configure each third-party logger to use structured logging:
    # - Clear existing handlers to prevent duplicate logs
    # - Disable propagation to avoid conflicts with root logger formatting
    for logger_name in third_party_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.handlers.clear()
        logger.handlers = [handler]
        logger.propagate = False

def should_use_pretty_format(is_local: bool, log_format_json: bool | None) -> bool:
    """Determine format based on IS_LOCAL and LOG_FORMAT_JSON override

    Options:
    - IS_LOCAL=true: Use pretty format by default
    - IS_LOCAL=false: Use JSON format by default
    - LOG_FORMAT_JSON: Override the default behavior
    Returns:
        bool: True if pretty format should be used, False for JSON format
    """
    use_pretty_format = not log_format_json if log_format_json is not None else is_local

    return use_pretty_format

def configure_structlog() -> None:
    """Configure structlog for the MCP server.

    Sets up structured logging with:
    - JSON output in production
    - Pretty console output in local development
    - Context variables integration
    - Clean integration with third-party library loggers
    - Standard library logging integration
    """

    # Convert string log level to logging constant
    log_level = logging.WARNING
    is_local = DEFAULT_IS_LOCAL
    use_pretty_format = should_use_pretty_format(is_local, is_local)

    # Create processor chain: JSON by default, pretty only when explicitly requested
    processors = _create_structlog_processor_chain()

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    console_renderer = structlog.dev.ConsoleRenderer(colors=True) if use_pretty_format else structlog.processors.JSONRenderer()

    # Configure stdlib logging with environment-aware formatter
    # ProcessorFormatter handles both structlog and stdlib (uvicorn) logs
    formatter = structlog.stdlib.ProcessorFormatter(
        # For stdlib logs (like uvicorn), process them through these steps first
        foreign_pre_chain=[
            # Add log level
            structlog.stdlib.add_log_level,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
        ],
        # Final processors for all logs (both structlog and stdlib)
        processors=[
            # Remove internal structlog keys
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # Render with environment-aware renderer
            console_renderer,
        ],
    )

    # Create handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger to use JSON format (catches all library logs)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Clear existing handlers to prevent duplicates
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Configure standard library logging
    _configure_stdlib_logging(log_level, handler)

def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the calling module's name.

    Returns:
        A configured structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
