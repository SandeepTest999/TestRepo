"""
Shared utility functions, logging setup, and common exception classes.
"""

import logging
import os
import sys
from pathlib import Path

import config


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root application logger."""
    log_dir = _get_log_dir()
    log_path = log_dir / config.LOG_FILE_NAME

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def _get_log_dir() -> Path:
    """Return the directory used for log files (temp folder)."""
    log_dir = Path.home() / config.TEMP_FOLDER_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


class WorkflowError(Exception):
    """Base exception for all workflow errors."""


class FTPError(WorkflowError):
    """Raised when an FTP operation fails."""


class TelnetError(WorkflowError):
    """Raised when a TELNET operation fails."""


class PollingTimeoutError(WorkflowError):
    """Raised when result polling exceeds the configured timeout."""


class ComparisonError(WorkflowError):
    """Raised when the comparison step fails."""


class CredentialsError(WorkflowError):
    """Raised when credentials are missing or invalid."""


class SSGGenerationError(WorkflowError):
    """Raised when SSG script generation fails."""
