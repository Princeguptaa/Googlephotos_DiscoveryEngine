"""
Structured logging for the pipeline.

Each log line includes [STAGE] [SOURCE] for easy grep-ability.
Example output:
    [COLLECT]  [play_store] Scraped 450 items
    [FILTER]   [play_store] 450 in → 412 passed, 38 dropped
    [CLASSIFY] Processing item 127/1102...
"""

import logging
import sys


# Configure root logger once at import time
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))

_logger = logging.getLogger("discovery_engine")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(_handler)


def log(stage: str, message: str, source: str = "") -> None:
    """Log a structured message with stage and optional source prefix.

    Args:
        stage: Pipeline stage name (e.g. "COLLECT", "FILTER", "CLASSIFY").
        message: The log message.
        source: Optional data source name (e.g. "play_store", "reddit").

    Example:
        log("COLLECT", "Scraped 450 items", "play_store")
        # Output: [COLLECT]  [play_store] Scraped 450 items

        log("CLASSIFY", "Processing item 127/1102...")
        # Output: [CLASSIFY] Processing item 127/1102...
    """
    stage_tag = f"[{stage}]".ljust(11)
    if source:
        prefix = f"{stage_tag} [{source}]"
    else:
        prefix = stage_tag
    _logger.info(f"{prefix} {message}")


def log_warning(stage: str, message: str, source: str = "") -> None:
    """Log a warning with stage and optional source prefix."""
    stage_tag = f"[{stage}]".ljust(11)
    if source:
        prefix = f"{stage_tag} [{source}]"
    else:
        prefix = stage_tag
    _logger.warning(f"{prefix} {message}")


def log_error(stage: str, message: str, source: str = "") -> None:
    """Log an error with stage and optional source prefix."""
    stage_tag = f"[{stage}]".ljust(11)
    if source:
        prefix = f"{stage_tag} [{source}]"
    else:
        prefix = stage_tag
    _logger.error(f"{prefix} {message}")
