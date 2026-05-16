"""Logging configuration for extraction runs."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

import config


def setup_logging(debug: bool = False) -> tuple[logging.Logger, str]:
    """Configure root logger and return run-scoped logger with run_id."""
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if debug:
        config.DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    log_file = config.LOGS_DIR / f"parsing_{run_id}.log"

    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    logger = logging.getLogger("pdf_to_csv")
    logger.info("Run started: %s", run_id)
    logger.info("Log file: %s", log_file)
    return logger, run_id


def get_validation_log_path(run_id: str) -> Path:
    return config.LOGS_DIR / f"validation_{run_id}.log"


def get_failed_rows_path(run_id: str) -> Path:
    return config.LOGS_DIR / f"failed_rows_{run_id}.jsonl"
