"""
Stage 4.5 — Failure-type codebook (plan v2.3 §6.3).

Small, pre-registered typology of failure modes used when an alignment
code is 하(0) or NA. Each failure code is one reason a rationale's
cue is judged off-rubric or indeterminate. Codebook is intentionally
short — a long typology kills coding reliability.

The final taxonomy is pinned at preregistration v1.0. This module
provides only the string constants so imports don't drift; the
binding of code → natural-language label sits in
`decision_table_preregistered.md` Appendix (to be authored).
"""
from __future__ import annotations

from typing import Literal

# Off-rubric / surface cue codes
FailureCode = Literal[
    "LEN",        # length/word count used as quality proxy
    "TONE",       # tone, politeness, formality cited instead of rubric
    "TYPO",       # spelling/typo cited in a non-expression trait
    "GRADE",      # grade-level proxy (e.g., "초5 치곤 잘 씀")
    "NONE_VISIBLE",  # rationale empty or generic ("글이 좋음")
    "CONTRA",     # rationale contradicts the score
    "SCOPE",      # rationale addresses a different trait
]

FAILURE_LABELS: dict[FailureCode, str] = {
    "LEN":          "길이·분량 기반 판단",
    "TONE":         "어조·격식 기반 판단 (해당 trait 범위 밖)",
    "TYPO":         "철자·맞춤법 언급 (표현 trait이 아닌 경우)",
    "GRADE":        "학년 기대치 기반 판단",
    "NONE_VISIBLE": "구체 근거 부재 / 범용 표현",
    "CONTRA":       "점수와 근거 내용이 상충",
    "SCOPE":        "지정 trait 외의 내용 언급",
}
