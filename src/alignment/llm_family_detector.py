"""Detect feature-family mentions in Stage C LLM rationales.

This module implements the v1.3 addendum convention for ``F_LLM(i,t)``:
content morpheme filtering followed by exact 1-3 lemma-token keyword matches.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from configs.paths import FEATURE_FAMILIES

Keyword = tuple[str, ...]
KeywordSet = dict[str, tuple[Keyword, ...]]

CONTENT_POS: frozenset[str] = frozenset({
    "NNG", "NNP", "VV", "VA", "VV-I", "VA-I", "MAG", "MAJ", "XR", "SN",
})

KEYWORD_SET: KeywordSet = {
    "meta": (
        ("길이",), ("분량",), ("글", "길이"), ("문장", "수"), ("어절", "수"),
    ),
    "morph_prop": (
        ("어미",), ("종결",), ("시제",), ("품사",), ("동사", "비율"),
    ),
    "lex": (
        ("어휘",), ("단어", "선택"), ("표현", "다양"), ("어휘", "다양"),
    ),
    "vocab_grade": (
        ("어휘", "등급"), ("초급", "어휘"), ("고급", "어휘"), ("어휘", "수준"),
    ),
    "syn": (
        ("문장", "구조"), ("문법", "구조"), ("연결", "어미"), ("문장", "형식"),
    ),
    "case_marker": (
        ("조사",), ("격조사",), ("조사", "사용"), ("어절", "결합"),
    ),
    "dis_nonSBERT": (
        ("접속어",), ("연결어",), ("응집",), ("문단", "연결"), ("전개", "흐름"),
    ),
    "dis_SBERT": (
        ("의미", "일관성"), ("주제", "유지"), ("내용", "흐름"),
        ("맥락", "연결"), ("문단", "일관성"),
    ),
}

_FALLBACK_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
_KIWI_ANALYZER = None
_KIWI_IMPORT_FAILED = False


@dataclass(frozen=True)
class FamilyDetection:
    tokens: tuple[str, ...]
    families: tuple[str, ...]
    matched_keywords: dict[str, tuple[Keyword, ...]]

    @property
    def is_empty(self) -> bool:
        return not self.families


def _normalize(text: str) -> str:
    return text.strip().lower()


def _token_fields(token) -> tuple[str, str]:
    if isinstance(token, tuple) and len(token) >= 2:
        form = token[0]
        tag = token[1]
    else:
        form = getattr(token, "lemma", None) or getattr(token, "form", "")
        tag = getattr(token, "tag", "")
    return str(form), str(tag)


def _iter_kiwi_tokens(text: str):
    global _KIWI_ANALYZER, _KIWI_IMPORT_FAILED
    if _KIWI_IMPORT_FAILED:
        return None
    try:
        if _KIWI_ANALYZER is None:
            from kiwipiepy import Kiwi
            _KIWI_ANALYZER = Kiwi()
            # Kiwi splits '연결어' into 연결+어, so the pre-registered
            # dis_nonSBERT keyword ('연결어',) could never match. Register it
            # as a single noun to recover the keyword's intended behavior.
            _KIWI_ANALYZER.add_user_word("연결어", "NNG")
    except ImportError:
        _KIWI_IMPORT_FAILED = True
        return None
    return _KIWI_ANALYZER.tokenize(text)


def content_lemmas(text: str, *, analyzer=None) -> tuple[str, ...]:
    """Return lowercase content lemmas from Korean rationale text.

    ``analyzer`` is injectable for tests. It may return tuple-like tokens or
    kiwipiepy token objects.
    """
    if analyzer is None:
        analyzed = _iter_kiwi_tokens(text)
    else:
        analyzed = analyzer(text)
    if analyzed is None:
        return tuple(_normalize(tok) for tok in _FALLBACK_TOKEN_RE.findall(text))

    tokens: list[str] = []
    for token in analyzed:
        form, tag = _token_fields(token)
        if tag in CONTENT_POS:
            normalized = _normalize(form)
            if normalized:
                tokens.append(normalized)
    return tuple(tokens)


def match_keyword(tokens: tuple[str, ...], keyword: Keyword) -> bool:
    if not keyword or len(keyword) > len(tokens):
        return False
    width = len(keyword)
    normalized_keyword = tuple(_normalize(tok) for tok in keyword)
    return any(tokens[i:i + width] == normalized_keyword for i in range(len(tokens) - width + 1))


def detect_families(
    text: str,
    *,
    keyword_set: KeywordSet = KEYWORD_SET,
    analyzer=None,
) -> FamilyDetection:
    tokens = content_lemmas(text, analyzer=analyzer)
    matched: dict[str, tuple[Keyword, ...]] = {}
    for family in FEATURE_FAMILIES:
        keywords = keyword_set.get(family, ())
        hits = tuple(keyword for keyword in keywords if match_keyword(tokens, keyword))
        if hits:
            matched[family] = hits
    return FamilyDetection(
        tokens=tokens,
        families=tuple(family for family in FEATURE_FAMILIES if family in matched),
        matched_keywords=matched,
    )


def find_keyword_duplicates(keyword_set: KeywordSet = KEYWORD_SET) -> dict[Keyword, tuple[str, ...]]:
    owners: dict[Keyword, list[str]] = {}
    for family, keywords in keyword_set.items():
        for keyword in keywords:
            normalized = tuple(_normalize(tok) for tok in keyword)
            owners.setdefault(normalized, []).append(family)
    return {
        keyword: tuple(families)
        for keyword, families in owners.items()
        if len(set(families)) > 1
    }


def _rationale_text(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("text", "") or "")
    return str(entry or "")


def iter_stage_c_records(path: Path) -> Iterable[dict]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def build_llm_family_sets(
    records: Iterable[dict],
    *,
    traits: Iterable[str] | None = None,
    analyzer=None,
) -> pd.DataFrame:
    trait_filter = set(traits) if traits is not None else None
    rows: list[dict] = []
    for record in records:
        essay_id = int(record["essay_id"])
        purpose = record.get("purpose")
        rationale = record.get("rationale", {})
        for trait, entry in rationale.items():
            if trait_filter is not None and trait not in trait_filter:
                continue
            text = _rationale_text(entry)
            detection = detect_families(text, analyzer=analyzer)
            rows.append({
                "essay_id": essay_id,
                "purpose": purpose,
                "trait": trait,
                "rationale_text": text,
                "llm_families": list(detection.families),
                "llm_family_count": len(detection.families),
                "llm_family_empty": detection.is_empty,
                "llm_tokens": list(detection.tokens),
                "llm_matched_keywords": {
                    family: [" ".join(keyword) for keyword in keywords]
                    for family, keywords in detection.matched_keywords.items()
                },
            })
    return pd.DataFrame(rows)


def load_stage_c_family_sets(
    path: Path,
    *,
    traits: Iterable[str] | None = None,
    analyzer=None,
) -> pd.DataFrame:
    return build_llm_family_sets(iter_stage_c_records(path), traits=traits, analyzer=analyzer)
