"""Logging helpers for framework entry points."""

from __future__ import annotations

import logging
from typing import Final

from rich.logging import RichHandler

LOG_FORMAT: Final[str] = "%(message)s"


def configure_logging(level: int | str = logging.INFO) -> None:
    """Configure process logging with Rich output."""
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(markup=True, rich_tracebacks=True)],
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named framework logger."""
    return logging.getLogger(name)

