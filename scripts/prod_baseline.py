"""Prod baseline mechanism (Slice 0, dry-run only).

Captures file checksums for users/areas/tokens refs without opening
any database connection. The prod write guard lands in Slice 1.
"""
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROD_SUBSTRINGS: tuple[str, ...] = ("prod",)


def is_prod_connection(name: str) -> bool:
    """Return True when a connection name matches a prod alias."""
    lowered = (name or "").lower()
    matched = any(token in lowered for token in PROD_SUBSTRINGS)
    if matched:
        logger.error("[BACK][ERROR] Refusing prod connection: %s", name)
    return matched


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    logger.info("[BACK] Checksum captured: %s", path)
    return digest


def capture_baseline(paths: list[Path] | tuple[Path, ...]) -> dict[str, str]:
    """Capture {str(path): sha256} without any DB access."""
    baseline = {Path(path).as_posix(): sha256_file(path) for path in paths}
    logger.info("[BACK] Baseline captured for %d ref(s)", len(baseline))
    return baseline
