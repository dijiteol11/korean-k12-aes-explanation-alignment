"""
Central Kiwi analyzer — single source of truth for Korean NLP operations.

Kiwipiepy (Kiwi, Python binding) is used for:
    1. Sentence splitting (replaces KSS)
    2. Morpheme-level TTR  (supplements JSON's morph counts)

The JSON `feature` field's 42 morpheme-tag counts remain the *primary*
morphological feature set (NIA 14-026 corpus standard). Kiwipiepy is
additive: it enables reproducible sentence boundaries and morpheme-level
TTR that are not available from the JSON alone.

Design
------
* Single analyzer instance, lazily loaded. Constructing Kiwi is non-trivial
  (loads model files) so we share one instance across the pipeline.
* All Kiwi-dependent operations degrade gracefully if the library is
  missing: sentence splitting falls back to a punctuation regex, and
  morpheme-TTR is reported as NaN (clearly flagged, not silently zero).
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache

log = logging.getLogger(__name__)

_PUNCT_SPLIT_RE = re.compile(r"(?<=[.!?。？！])\s+")


@lru_cache(maxsize=1)
def get_kiwi():
    """Return a shared Kiwi() instance, or None if kiwipiepy is unavailable."""
    try:
        from kiwipiepy import Kiwi  # type: ignore
    except ImportError:
        log.warning(
            "kiwipiepy not installed — sentence splitting will use a regex "
            "fallback and morpheme-TTR will be NaN. "
            "Install with: pip install kiwipiepy"
        )
        return None
    return Kiwi()


def split_sentences(text: str) -> list[str]:
    """Split a Korean text into sentences using Kiwi; regex fallback."""
    kiwi = get_kiwi()
    if kiwi is None:
        return [s.strip() for s in _PUNCT_SPLIT_RE.split(text) if s.strip()]
    return [s.text for s in kiwi.split_into_sents(text) if s.text.strip()]


def analyze_morphemes(text: str) -> list[tuple[str, str]]:
    """Return (form, tag) tuples for every morpheme in `text`.

    Empty list if Kiwi is unavailable.
    """
    kiwi = get_kiwi()
    if kiwi is None:
        return []
    result = kiwi.analyze(text, top_n=1)
    if not result:
        return []
    tokens = result[0][0]  # best parse
    return [(tok.form, tok.tag) for tok in tokens]


def morpheme_ttr(text: str) -> tuple[float, int, int]:
    """Morpheme-level Type-Token Ratio.

    Excludes punctuation/symbol tags (SF, SP, SS, SE, SO, SW) so that
    TTR reflects lexical diversity rather than punctuation noise.

    Returns (TTR, n_types, n_tokens). (nan, 0, 0) if Kiwi unavailable.
    """
    morphs = analyze_morphemes(text)
    if not morphs:
        return float("nan"), 0, 0
    content = [m for m, t in morphs if not t.startswith("S")]
    if not content:
        return 0.0, 0, 0
    n_types = len(set(content))
    n_tokens = len(content)
    return n_types / n_tokens, n_types, n_tokens
