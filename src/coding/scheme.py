"""
Stage 4.3 — 4-level alignment coding scheme (plan v2.3 §4.4.1).

Each (essay_id, trait, explanation_system) triple is coded on a 4-level
ordinal scale PLUS an indeterminate bucket:

    상(2)  — rationale/feedback clearly points to a rubric-relevant element
    중(1)  — partial/implicit reference to a rubric-relevant element
    하(0)  — points to an off-rubric element (length, tone, surface cue)
    NA    — 판정 불가 (insufficient or internally contradictory cues)

Decision rule (v2.3 §4.4.1 verbatim pattern — confirm against the
preregistered `decision_table_preregistered.md` at v1.0 commit time):

    If rationale cites ≥1 span tagged as rubric-relevant AND is internally
    consistent with the score:   상
    If rationale cites rubric-relevant element only via paraphrase (no
    direct span reference):       중
    If rationale cites only surface or off-rubric cues:   하
    If rationale is too short, empty, self-contradictory, or cites spans
    that contradict the score:    NA

The codebook binding lives in `family_rubric_mapping_preregistered.md`
§4 (rubric → family mapping) + `failure_codes.py` (off-rubric taxonomy).
"""
from __future__ import annotations

from enum import IntEnum
from typing import Literal

AlignmentCode = Literal["상", "중", "하", "NA"]


class AlignmentLevel(IntEnum):
    """Numeric ordering; NA is handled separately (not in the enum)."""
    HIGH = 2    # 상
    MID = 1     # 중
    LOW = 0     # 하


INDETERMINATE: str = "NA"

LEVEL_CODES: dict[str, AlignmentCode] = {
    "HIGH": "상",
    "MID": "중",
    "LOW": "하",
    "INDETERMINATE": "NA",
}

CODE_TO_LEVEL: dict[AlignmentCode, int | None] = {
    "상": 2,
    "중": 1,
    "하": 0,
    "NA": None,
}


def is_determinate(code: AlignmentCode) -> bool:
    return code != "NA"


def numeric(code: AlignmentCode) -> int | None:
    """Return the ordinal numeric for determinate codes, None for NA.

    Downstream ordinal mixed models (plan v2.3 §4.5.3) must treat ``None``
    as an explicit category rather than silently dropping the row.
    """
    return CODE_TO_LEVEL[code]
