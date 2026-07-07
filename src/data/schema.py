"""
Typed data models for NIA 14-026 essay records.

These dataclasses mirror the JSON schema observed in
14-2-*-N-0A-*-*.json files. Keeping them as dataclasses (not Pydantic) to
avoid a heavy dependency; validation happens in src/data/loader.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class EssayQuestion:
    id: str
    type: str
    subject: str           # 국어 / 사회 / 과학
    topic: str
    level: str             # 상 / 중 / 하
    grade: str             # 초5 / 초6 / 중1 / 중2 / 중3
    purpose: str           # 설명 / 설득 / 친교 및 정서
    prompt: str
    len_syllable: int
    len_word: int


@dataclass(frozen=True)
class EssayAnswer:
    id: int
    region: str
    gender: str
    reference: str
    text: str
    len_syllable: int
    len_word: int
    feature: dict[str, int]  # 42-dim morphosyntactic count vector


@dataclass(frozen=True)
class TraitScore:
    """Score for a single analytic trait, from 2 raters, with feedback."""
    trait: str                 # e.g. 'content_1'
    rubric_key: str            # e.g. 'B-00A-1B-2G'
    score_rater1: int
    score_rater2: int
    feedback: str              # expert feedback text (1 rater)
    len_syllable: int
    len_word: int

    @property
    def score_mean(self) -> float:
        return (self.score_rater1 + self.score_rater2) / 2.0

    @property
    def exact_agreement(self) -> bool:
        return self.score_rater1 == self.score_rater2


@dataclass(frozen=True)
class HolisticScore:
    score_rater1: int
    score_rater2: int
    feedback: str
    len_syllable: int
    len_word: int
    min_syllable: int
    total_word: int

    @property
    def score_mean(self) -> float:
        return (self.score_rater1 + self.score_rater2) / 2.0


@dataclass(frozen=True)
class Essay:
    """Complete record — the unit of analysis."""
    source_path: str
    question: EssayQuestion
    answer: EssayAnswer
    holistic: HolisticScore
    analytic: dict[str, TraitScore]  # keys from configs.paths.TRAITS
    rubric_raw: dict                  # full rubric text block, preserved for LLM ICL
    expert_meta: dict = field(default_factory=dict)  # rater demographics
