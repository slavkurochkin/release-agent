"""Structured logging configuration for production.

This module sets up structured JSON logging using structlog, which is
essential for production observability. JSON logs can be:
- Parsed by Cloud Logging (GCP)
- Queried in BigQuery via log sinks
- Correlated with traces using request IDs

Why structured logging?
Plain text logs like "Processing request for repo myorg/api" are human-
readable but machine-hostile. Structured logs like:
  {"event": "processing_request", "repo": "myorg/api", "pr": 123}
can be filtered, aggregated, and alerted on programmatically.

Usage:
    from release_agent.logging_config import setup_logging, get_logger

    setup_logging(environment="production")
    logger = get_logger(__name__)
    logger.info("processing_request", repo="myorg/api", pr_number=123)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


def setup_logging(
    environment: str | None = None,
    log_level: str | None = None,
) -> None:
    """Configure structured logging for the application.

    In development: Pretty-printed, colorized output for readability.
    In production: JSON output for Cloud Logging ingestion.

    Args:
        environment: "development" or "production". Reads from
                     ENVIRONMENT env var if not provided.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
                   Reads from LOG_LEVEL env var if not provided.
    """

    # 1. Resolve environment and log level:
    env = environment or os.environ.get("ENVIRONMENT", "development")
    level = log_level or os.environ.get("LOG_LEVEL", "INFO")

    # 2. Configure structlog processors:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # 3. Set up environment-specific rendering:
    if env == "production":
        # JSON output for Cloud Logging
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty output for development
        renderer = structlog.dev.ConsoleRenderer()

    # 4. Configure structlog:
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    #
    # 5. Also configure standard library logging (for third-party libs):
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        A structlog bound logger
    """
    return structlog.get_logger(name)
