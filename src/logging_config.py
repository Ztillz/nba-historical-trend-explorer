import logging
from pathlib import Path


def configure_logging(log_file: Path) -> logging.Logger:
    """
    Configure logging to both the terminal and a log file.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("nba_pipeline")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers when the script is run repeatedly
    # in the same Python process.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger