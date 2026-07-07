"""
Shared Kiwi morphological analyzer instance.

Kiwi initialization is slow (~1-2 seconds), so we use a singleton pattern
to avoid reinitializing for every essay during feature extraction.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiwipiepy import Kiwi

log = logging.getLogger(__name__)

_kiwi_instance: "Kiwi | None" = None


def get_kiwi() -> "Kiwi":
    """Get or create the shared Kiwi instance."""
    global _kiwi_instance
    if _kiwi_instance is None:
        try:
            from kiwipiepy import Kiwi
            log.info("Initializing shared Kiwi instance...")
            _kiwi_instance = Kiwi()
            log.info("Kiwi initialized successfully")
        except ImportError:
            raise ImportError(
                "kiwipiepy is required for Korean morphological analysis. "
                "Install with: pip install kiwipiepy"
            )
    return _kiwi_instance


def reset_kiwi() -> None:
    """Reset the shared Kiwi instance (for testing)."""
    global _kiwi_instance
    _kiwi_instance = None
