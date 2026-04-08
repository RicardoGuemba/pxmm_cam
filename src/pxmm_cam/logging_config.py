"""Logging setup: rotating file in logs/ and console."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "pxmm_cam.log"
MAX_BYTES = 2 * 1024 * 1024  # 2 MB
BACKUP_COUNT = 3


def setup_logging(log_dir: Optional[Path] = None) -> None:
    """Configure root logger with file (rotating) and console.

    Creates log_dir if needed. Does not block UI with heavy I/O.
    """

    if log_dir is None:
        # Project root: parent of src (file is src/pxmm_cam/logging_config.py)
        project_root = Path(__file__).resolve().parent.parent.parent
        log_dir = project_root / LOG_DIR_NAME
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILE_NAME

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Avoid duplicate handlers when called multiple times
    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    logging.getLogger("pxmm_cam").setLevel(logging.DEBUG)
