"""
Morphological and derived linguistic features.

Input: Essay.answer.feature  (dict of morpheme-tag counts, 42 keys typical)

Outputs three groups:

1. morph_prop_*    — each tag count divided by total morpheme count.
                      Scale-invariant; feeds XGBoost without further scaling.
2. lex_*            — lexical features (TTR, POS diversity)
3. syn_*            — syntactic features (ending/clause ratios)
4. dis_*_nonSBERT   — discourse features that do NOT require embeddings
                      (connective adverb rate, pronoun density)

SBERT-based discourse features live in src.features.discourse.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from configs.paths import MORPH_TAGS, POS_FAMILIES
from src.data.schema import Essay

# Simple Korean syllable pattern for a lightweight TTR over eojeols (어절).
# A more rigorous TTR would require a morphological analyzer (e.g. Kiwi);
# here we use eojeol-level TTR as a stable proxy that is widely reported
# in Korean L1 essay studies.
_WHITESPACE_RE = re.compile(r"\s+")


def _total_morphemes(feature: dict[str, int]) -> int:
    """Sum of all morph-tag counts except the '문장수' meta key."""
    return sum(v for k, v in feature.items() if k != "문장수")


def _morph_proportions(feature: dict[str, int]) -> dict[str, float]:
    total = _total_morphemes(feature)
    if total == 0:
        return {f"morph_prop__{tag}": 0.0 for tag in MORPH_TAGS if tag != "문장수"}
    return {
        f"morph_prop__{tag}": feature.get(tag, 0) / total
        for tag in MORPH_TAGS
        if tag != "문장수"
    }


def _ttr(text: str) -> tuple[float, int, int]:
    """Eojeol-level Type-Token Ratio.

    Returns (TTR, n_types, n_tokens). Stable for Korean since eojeol
    segmentation is whitespace-based.
    """
    tokens = [t for t in _WHITESPACE_RE.split(text) if t]
    if not tokens:
        return 0.0, 0, 0
    n_types = len(set(tokens))
    n_tokens = len(tokens)
    return n_types / n_tokens, n_types, n_tokens


def _pos_shannon_entropy(feature: dict[str, int]) -> float:
    """Shannon entropy over POS family proportions.

    Higher = more balanced use across noun/verb/adjective/adverb/etc.
    Low entropy indicates over-reliance on one category
    (e.g., noun-only writing).
    """
    fam_totals = {
        fam: sum(feature.get(t, 0) for t in tags)
        for fam, tags in POS_FAMILIES.items()
    }
    total = sum(fam_totals.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for count in fam_totals.values():
        if count == 0:
            continue
        p = count / total
        ent -= p * math.log2(p)
    return ent


def _family_sum(feature: dict[str, int], family: str) -> int:
    return sum(feature.get(t, 0) for t in POS_FAMILIES[family])


def extract_morphology(essay: Essay) -> dict[str, float]:
    feat = essay.answer.feature
    n_word = essay.answer.len_word or 1  # avoid div-by-zero
    n_sent = feat.get("문장수", 0) or 1
    total_morph = _total_morphemes(feat) or 1

    out: dict[str, float] = {}

    # 1. Normalized morph-tag proportions
    out.update(_morph_proportions(feat))

    # 2. Lexical features
    ttr, n_types, n_tokens = _ttr(essay.answer.text)
    out["lex_ttr_eojeol"] = ttr
    out["lex_n_types_eojeol"] = float(n_types)
    out["lex_pos_entropy"] = _pos_shannon_entropy(feat)

    # Morpheme-level TTR (requires kiwipiepy). NaN if unavailable —
    # downstream XGBoost handles NaN natively, so the feature is safely
    # skipped in the fallback path.
    from src.features.korean_analyzer import morpheme_ttr
    m_ttr, m_types, m_tokens = morpheme_ttr(essay.answer.text)
    out["lex_ttr_morph"] = m_ttr
    out["lex_n_types_morph"] = float(m_types) if m_tokens > 0 else float("nan")

    # 3. Syntactic features
    out["syn_connective_ending_rate_per_sent"] = (
        _family_sum(feat, "connective_ending") / n_sent
    )
    out["syn_final_ending_rate_per_sent"] = (
        _family_sum(feat, "final_ending") / n_sent
    )
    out["syn_adnominal_ending_rate_per_morph"] = (
        _family_sum(feat, "adnominal_ending") / total_morph
    )
    out["syn_verb_ratio"] = _family_sum(feat, "verb") / total_morph
    out["syn_adjective_ratio"] = _family_sum(feat, "adjective") / total_morph
    out["syn_noun_ratio"] = _family_sum(feat, "noun") / total_morph

    # 4. Discourse (non-SBERT) features
    out["dis_connective_adv_per_sent"] = feat.get("접속 부사", 0) / n_sent
    out["dis_pronoun_density"] = _family_sum(feat, "pronoun") / n_word
    # Conjunctive particle rate (접속 조사) is another cohesion signal
    out["dis_conj_particle_per_sent"] = feat.get("접속 조사", 0) / n_sent

    return out
