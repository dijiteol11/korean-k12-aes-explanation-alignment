"""
Sentence complexity features based on KICE AES specification.

Category II features: case particle (격조사) distributions.
Uses Kiwi morphological analyzer for consistent tagging.

Feature family: case_marker
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.loader import Essay

log = logging.getLogger(__name__)


# Kiwi POS tags for Korean case particles (격조사)
CASE_MARKER_TAGS = {
    "JKS": "josa_subject",      # 주격 조사 (이/가)
    "JKO": "josa_object",       # 목적격 조사 (을/를)
    "JKB": "josa_adverbial",    # 부사격 조사 (에/에서/으로)
    "JKV": "josa_vocative",     # 호격 조사 (아/야)
    "JKQ": "josa_quotative",    # 인용격 조사 (라고/고)
    "JKC": "josa_complement",   # 보격 조사 (이/가 in complement)
    "JKG": "josa_genitive",     # 관형격 조사 (의)
}

# Additional particle types for comprehensive analysis
PARTICLE_TAGS = {
    "JX": "particle_auxiliary",  # 보조사 (은/는/도/만)
    "JC": "particle_conjunctive", # 접속 조사 (와/과/하고)
}


def extract_case_markers(essay: "Essay") -> dict[str, float]:
    """
    Extract case marker (격조사) features from essay content.

    Uses Kiwi morphological analyzer for POS tagging.

    Features (case_marker family):
        josa_subject_count: raw count of subject case markers (이/가)
        josa_object_count: raw count of object case markers (을/를)
        josa_adverbial_count: raw count of adverbial case markers (에/에서/으로)
        josa_vocative_count: raw count of vocative case markers (아/야)
        josa_quotative_count: raw count of quotative case markers (라고/고)
        josa_complement_count: raw count of complement case markers
        josa_genitive_count: raw count of genitive case markers (의)
        josa_total_count: total case markers
        josa_subject_ratio: proportion relative to total case markers
        josa_object_ratio: proportion relative to total case markers
        josa_adverbial_ratio: proportion relative to total case markers
        case_diversity: number of distinct case marker types used

    Args:
        essay: Essay object with answer.content text

    Returns:
        Dictionary of case marker features.
    """
    try:
        from src.features.kiwi_analyzer import get_kiwi
        kiwi = get_kiwi()
    except ImportError:
        log.warning("kiwipiepy not available; returning zero case marker features")
        return _zero_case_features()

    text = essay.answer.text or ""

    if not text.strip():
        return _zero_case_features()

    # Analyze with Kiwi
    tokens = kiwi.tokenize(text)

    # Count case markers
    counts: dict[str, int] = {name: 0 for name in CASE_MARKER_TAGS.values()}

    for token in tokens:
        if token.tag in CASE_MARKER_TAGS:
            feature_name = CASE_MARKER_TAGS[token.tag]
            counts[feature_name] += 1

    total_case_markers = sum(counts.values())

    # Build features
    features: dict[str, float] = {}

    # Raw counts
    for name, count in counts.items():
        features[f"{name}_count"] = float(count)

    features["josa_total_count"] = float(total_case_markers)

    # Ratios (relative to total case markers)
    if total_case_markers > 0:
        for name, count in counts.items():
            features[f"{name}_ratio"] = count / total_case_markers
    else:
        for name in counts:
            features[f"{name}_ratio"] = 0.0

    # Case diversity: number of distinct case marker types used
    case_diversity = sum(1 for c in counts.values() if c > 0)
    features["case_diversity"] = float(case_diversity)

    return features


def _zero_case_features() -> dict[str, float]:
    """Return zero-valued case marker features for fallback."""
    features: dict[str, float] = {}

    for name in CASE_MARKER_TAGS.values():
        features[f"{name}_count"] = 0.0
        features[f"{name}_ratio"] = 0.0

    features["josa_total_count"] = 0.0
    features["case_diversity"] = 0.0

    return features
