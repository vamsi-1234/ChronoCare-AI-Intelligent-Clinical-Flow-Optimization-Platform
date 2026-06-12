"""Logging configuration for ChronoCare AI."""
import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """Configure structured logging for the application.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
               Falls back to the LOG_LEVEL env var, then INFO.
    """
    import os

    effective_level = level or os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, effective_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Quieten chatty third-party libraries
    for noisy in ("uvicorn.access", "lightgbm", "shap", "numba"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
