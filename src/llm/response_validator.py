"""
Stage 4 LLM response JSON schema validator.

Each of Stage A/B/C returns a structured JSON that must conform to the
wrapper spec. We validate at runtime and log malformed responses rather
than silently accepting them. A malformed response triggers:
    - Automatic retry once (at temperature 0, output should be stable)
    - If second attempt also fails, record in ``reports/stage4_llm/errors/``
      and skip this essay's stage (downstream fills score=null / reason).

Schemas are intentionally strict — if the researcher updates the wrapper,
these validators must be updated in lockstep.
"""
from __future__ import annotations

import logging
from typing import Any

from configs.paths import PURPOSES_IN_SCOPE

log = logging.getLogger(__name__)

ANALYTIC_TRAITS: tuple[str, ...] = (
    "task_1", "content_1", "content_2", "content_3",
    "organization_1", "organization_2", "expression_1", "expression_2",
)

EVIDENCE_TAGS: frozenset[str] = frozenset({
    "rubric_cue", "topic_frame", "structural_marker", "transition",
    "claim_or_thesis", "definition_or_concept", "content_detail",
    "factual_evidence", "example_case", "causal_reasoning",
    "lexical_choice", "grammatical_usage", "unspecified",
})

B_REASONS: frozenset[str] = frozenset({"insufficient_evidence", "rubric_ambiguous"})


class ResponseError(ValueError):
    """Raised for Stage 4 response schema violations."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ResponseError(msg)


def _require_int_range(val: Any, lo: int, hi: int, field: str) -> None:
    _require(isinstance(val, int) and not isinstance(val, bool),
             f"{field} must be int, got {type(val).__name__}")
    _require(lo <= val <= hi, f"{field} out of range [{lo},{hi}]: {val}")


def _require_float_range(val: Any, lo: float, hi: float, field: str) -> None:
    _require(isinstance(val, (int, float)) and not isinstance(val, bool),
             f"{field} must be number, got {type(val).__name__}")
    _require(lo <= float(val) <= hi, f"{field} out of range [{lo},{hi}]: {val}")


def validate_stage_a(resp: dict, essay_text: str | None = None) -> None:
    """Validate evidence extraction response (Stage A wrapper schema)."""
    _require(isinstance(resp, dict), "response must be a dict")
    _require("essay_id" in resp, "missing essay_id")
    _require(resp.get("purpose") in PURPOSES_IN_SCOPE, f"bad purpose: {resp.get('purpose')}")
    ev = resp.get("evidence")
    _require(isinstance(ev, dict), "evidence must be dict")
    for trait in ANALYTIC_TRAITS:
        _require(trait in ev, f"evidence missing trait '{trait}'")
        items = ev[trait]
        _require(isinstance(items, list), f"evidence.{trait} must be list")
        for i, item in enumerate(items):
            _require(isinstance(item, dict), f"evidence.{trait}[{i}] must be dict")
            span = item.get("span")
            _require(
                isinstance(span, list) and len(span) == 2
                and all(isinstance(x, int) for x in span) and span[0] < span[1],
                f"evidence.{trait}[{i}].span must be [start<end] ints",
            )
            text = item.get("text")
            _require(isinstance(text, str) and text, f"evidence.{trait}[{i}].text must be non-empty str")
            _require(len(text) <= 120, f"evidence.{trait}[{i}].text exceeds 120 chars")
            tag = item.get("tag")
            _require(tag in EVIDENCE_TAGS, f"evidence.{trait}[{i}].tag not in controlled vocab: {tag}")
            # Optional: substring-with-whitespace-tolerance check against essay_text
            if essay_text is not None:
                _check_span_substring(essay_text, span, text, trait, i)


def _check_span_substring(essay: str, span: list[int], text: str, trait: str, idx: int) -> None:
    """Allow whitespace/punctuation variance (A-4 (c) decision)."""
    import re
    if span[1] > len(essay):
        raise ResponseError(f"evidence.{trait}[{idx}].span out of essay length")
    region = essay[span[0]:span[1]]
    normalize = lambda s: re.sub(r"[\s　 \.,!?]+", "", s)
    if normalize(text) not in normalize(region):
        # Soft warning: do not raise, but caller can inspect.
        log.debug(
            "evidence.%s[%d] text %r not substring of span region (normalized)",
            trait, idx, text[:30],
        )


def validate_stage_b(resp: dict, stage_a_evidence: dict | None = None) -> None:
    """Validate scoring response (Stage B wrapper schema) — NA-aware."""
    _require(isinstance(resp, dict), "response must be a dict")
    _require("essay_id" in resp, "missing essay_id")
    _require(resp.get("purpose") in PURPOSES_IN_SCOPE, f"bad purpose: {resp.get('purpose')}")
    scores = resp.get("scores")
    _require(isinstance(scores, dict), "scores must be dict")
    for trait in ANALYTIC_TRAITS:
        _require(trait in scores, f"scores missing trait '{trait}'")
        entry = scores[trait]
        _require(isinstance(entry, dict), f"scores.{trait} must be dict")
        # score: int 1-5 OR null
        sc = entry.get("score")
        reason = entry.get("reason")
        if sc is None:
            _require(reason in B_REASONS,
                     f"scores.{trait}: null score requires reason in {sorted(B_REASONS)}, got {reason}")
        else:
            _require_int_range(sc, 1, 5, f"scores.{trait}.score")
            _require(reason is None, f"scores.{trait}: integer score requires reason=null, got {reason}")
        _require_float_range(entry.get("confidence"), 0.0, 1.0, f"scores.{trait}.confidence")
        refs = entry.get("span_refs")
        _require(isinstance(refs, list), f"scores.{trait}.span_refs must be list")
        for r in refs:
            _require(isinstance(r, int) and r >= 0, f"scores.{trait}.span_refs entry must be nonneg int")
        # If we have Stage A evidence, validate indices are in-range per trait
        if stage_a_evidence is not None:
            ev_list = stage_a_evidence.get(trait, [])
            for r in refs:
                _require(r < len(ev_list),
                         f"scores.{trait}.span_refs[{r}] out of bounds (A has {len(ev_list)} items)")


def validate_stage_c(resp: dict, stage_b_scores: dict | None = None) -> None:
    """Validate rationale response (Stage C wrapper schema)."""
    _require(isinstance(resp, dict), "response must be a dict")
    _require("essay_id" in resp, "missing essay_id")
    _require(resp.get("purpose") in PURPOSES_IN_SCOPE, f"bad purpose: {resp.get('purpose')}")
    rat = resp.get("rationale")
    _require(isinstance(rat, dict), "rationale must be dict")
    for trait in ANALYTIC_TRAITS:
        _require(trait in rat, f"rationale missing trait '{trait}'")
        entry = rat[trait]
        _require(isinstance(entry, dict), f"rationale.{trait} must be dict")
        text = entry.get("text")
        _require(isinstance(text, str) and text.strip(),
                 f"rationale.{trait}.text must be non-empty str")
        _require(len(text) <= 240,
                 f"rationale.{trait}.text exceeds 240 chars ({len(text)} given)")
        cs = entry.get("cited_spans")
        _require(isinstance(cs, list), f"rationale.{trait}.cited_spans must be list")
        for r in cs:
            _require(isinstance(r, int) and r >= 0,
                     f"rationale.{trait}.cited_spans entry must be nonneg int")
        # C-4 rule: integer score requires ≥1 cited span; NA score allows empty.
        if stage_b_scores is not None:
            sc = stage_b_scores.get(trait, {}).get("score")
            if sc is not None and len(cs) == 0:
                raise ResponseError(
                    f"rationale.{trait}: integer score {sc} requires ≥1 cited_span, got 0"
                )
