"""
NIA 14-026 JSON corpus loader.

Discovers all essay JSON files under a root directory, parses each into
a typed Essay, and exposes a pandas-friendly flattening.

Design notes
------------
* The sample corpus under /mnt/project contains only a handful of files
  (one per grade). The full corpus (20,000 essays) is expected to follow
  the identical JSON schema — this loader is therefore directly reusable.
* We deliberately do NOT use the per-grade CSV files. They are a lossy
  view of the JSON (no rubric, no 2-rater breakdown). JSON is canonical.
* Validation is defensive but not exhaustive; hard failures raise so that
  schema drift is caught early rather than silently producing NaNs.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Iterable, Iterator

# Make configs importable whether run as script or module
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.paths import TRAITS  # noqa: E402
from src.data.schema import (  # noqa: E402
    Essay,
    EssayAnswer,
    EssayQuestion,
    HolisticScore,
    TraitScore,
)

log = logging.getLogger(__name__)

# Filename convention: 14-2-{grade_code}-N-0{X}-{subject_code}-{seq}.json
# where X can be A, B, etc. depending on the rubric variant.
# Only pick up corpus JSON, skip any unrelated JSON that might live in the tree.
ESSAY_FILENAME_RE = r"^14-2-[EM]\d-N-0[A-Z]-[A-Z]-\d+\.json$"


def discover_essay_files(root: Path) -> list[Path]:
    """Find all corpus-format JSON files under `root`."""
    import re

    pattern = re.compile(ESSAY_FILENAME_RE)
    paths = sorted(p for p in root.rglob("*.json") if pattern.match(p.name))
    log.info("Discovered %d essay files under %s", len(paths), root)
    return paths


def _parse_trait(trait_key: str, raw: dict) -> TraitScore:
    score = raw["score"]
    if not (isinstance(score, list) and len(score) == 2):
        raise ValueError(f"{trait_key}: expected 2-rater score list, got {score!r}")
    return TraitScore(
        trait=trait_key,
        rubric_key=raw["rubric_key"],
        score_rater1=int(score[0]),
        score_rater2=int(score[1]),
        feedback=raw.get("feedback", ""),
        len_syllable=int(raw.get("len_syllable", 0)),
        len_word=int(raw.get("len_word", 0)),
    )


def parse_essay(path: Path, *, strict_traits: bool = True) -> Essay:
    """Load and validate a single essay JSON.

    Parameters
    ----------
    strict_traits : bool
        If True (default, used by training pipeline), raise when any of the
        8 expected analytic traits is absent. If False (used by Stage 1 EDA),
        missing traits are populated with a placeholder `TraitScore` carrying
        None scores so that purpose-heterogeneous corpora can still be
        enumerated for diagnostic purposes.
    """
    with path.open("r", encoding="utf-8") as f:
        d = json.load(f)

    q = d["essay_question"]
    a = d["essay_answer"]
    holistic_raw = d["score"]["personal"]["holistic"]
    analytic_raw = d["score"]["personal"]["analytic"]

    missing = [t for t in TRAITS if t not in analytic_raw]
    if missing and strict_traits:
        raise ValueError(f"{path.name}: missing traits {missing}")
    if missing:
        log.warning("%s: missing traits %s — parsed in lenient mode",
                     path.name, missing)

    # Cross-check: the rubric block should describe the same purpose as
    # the essay_question. A mismatch indicates either a data integrity
    # issue or a purpose-code assumption error in our pipeline.
    rubric_raw = d.get("rubric", {})
    rubric_purpose = rubric_raw.get("purpose", "")
    q_purpose = q.get("purpose", "")
    if rubric_purpose and q_purpose and rubric_purpose != q_purpose:
        log.warning(
            "%s: purpose mismatch — essay_question=%r, rubric=%r",
            path.name, q_purpose, rubric_purpose,
        )

    def _parse_trait_lenient(trait_key: str, raw: dict | None) -> TraitScore:
        if raw is None:
            return TraitScore(
                trait=trait_key,
                rubric_key="",
                score_rater1=-1,
                score_rater2=-1,
                feedback="",
                len_syllable=0,
                len_word=0,
            )
        return _parse_trait(trait_key, raw)

    analytic_parsed = {
        t: _parse_trait_lenient(t, analytic_raw.get(t)) for t in TRAITS
    }

    return Essay(
        source_path=str(path),
        question=EssayQuestion(
            id=q["id"],
            type=q["type"],
            subject=q["subject"],
            topic=q["topic"],
            level=q["level"],
            grade=q["grade"],
            purpose=q["purpose"],
            prompt=q["prompt"],
            len_syllable=int(q["len_syllable"]),
            len_word=int(q["len_word"]),
        ),
        answer=EssayAnswer(
            id=int(a["id"]),
            region=a["region"],
            gender=a["gender"],
            reference=a["reference"],
            text=a["text"],
            len_syllable=int(a["len_syllable"]),
            len_word=int(a["len_word"]),
            feature=dict(a.get("feature", {})),
        ),
        holistic=HolisticScore(
            score_rater1=int(holistic_raw["score"][0]),
            score_rater2=int(holistic_raw["score"][1]),
            feedback=holistic_raw.get("feedback", ""),
            len_syllable=int(holistic_raw.get("len_syllable", 0)),
            len_word=int(holistic_raw.get("len_word", 0)),
            min_syllable=int(holistic_raw.get("min_syllable", 0)),
            total_word=int(holistic_raw.get("total_word", 0)),
        ),
        analytic=analytic_parsed,
        rubric_raw=d.get("rubric", {}),
        expert_meta=d.get("expert", {}),
    )


def iter_essays(
    root: Path,
    *,
    strict: bool = False,
    strict_traits: bool = True,
    purposes: tuple[str, ...] | None = None,
) -> Iterator[Essay]:
    """Yield parsed essays. `strict=False` logs and skips malformed files.
    `strict_traits=False` additionally tolerates trait schema differences
    (e.g. essays from other purpose rubrics).
    `purposes`, if given, restricts output to essays whose
    `essay_question.purpose` is in the tuple (plan v2.1 §4.1.3)."""
    for path in discover_essay_files(root):
        try:
            essay = parse_essay(path, strict_traits=strict_traits)
        except Exception as e:
            if strict:
                raise
            log.warning("Skipping %s: %s", path.name, e)
            continue
        if purposes is not None and essay.question.purpose not in purposes:
            continue
        yield essay


def load_all(
    root: Path,
    *,
    strict: bool = False,
    strict_traits: bool = True,
    purposes: tuple[str, ...] | None = None,
) -> list[Essay]:
    return list(iter_essays(
        root, strict=strict, strict_traits=strict_traits, purposes=purposes,
    ))


def to_dataframe(essays: Iterable[Essay]):
    """Flatten essays into a long-format DataFrame (one row per trait score).

    Columns:
        essay_id, source_path, grade, subject, topic, level, purpose,
        region, gender, reference, len_syllable, len_word,
        trait, rubric_key, score_rater1, score_rater2, score_mean,
        exact_agreement, feedback_len
    Plus a 'holistic' row per essay with trait='_holistic'.
    """
    import pandas as pd

    rows: list[dict] = []
    for e in essays:
        base = {
            "essay_id": e.answer.id,
            "source_path": e.source_path,
            "grade": e.question.grade,
            "subject": e.question.subject,
            "topic": e.question.topic,
            "level": e.question.level,
            "purpose": e.question.purpose,
            "region": e.answer.region,
            "gender": e.answer.gender,
            "reference": e.answer.reference,
            "len_syllable": e.answer.len_syllable,
            "len_word": e.answer.len_word,
        }
        # Holistic row
        rows.append({
            **base,
            "trait": "_holistic",
            "rubric_key": None,
            "score_rater1": e.holistic.score_rater1,
            "score_rater2": e.holistic.score_rater2,
            "score_mean": e.holistic.score_mean,
            "exact_agreement": e.holistic.score_rater1 == e.holistic.score_rater2,
            "feedback_len": e.holistic.len_syllable,
        })
        # Analytic rows
        for trait_key, ts in e.analytic.items():
            # Placeholder traits (from lenient parse) carry -1 scores; emit NaN
            if ts.score_rater1 < 0 or ts.score_rater2 < 0:
                rows.append({
                    **base,
                    "trait": trait_key,
                    "rubric_key": ts.rubric_key or None,
                    "score_rater1": None,
                    "score_rater2": None,
                    "score_mean": None,
                    "exact_agreement": None,
                    "feedback_len": 0,
                    "trait_present": False,
                })
                continue
            rows.append({
                **base,
                "trait": trait_key,
                "rubric_key": ts.rubric_key,
                "score_rater1": ts.score_rater1,
                "score_rater2": ts.score_rater2,
                "score_mean": ts.score_mean,
                "exact_agreement": ts.exact_agreement,
                "feedback_len": ts.len_syllable,
                "trait_present": True,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":  # smoke test
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from configs.paths import DATA_ROOT

    essays = load_all(DATA_ROOT)
    log.info("Loaded %d essays", len(essays))
    if essays:
        df = to_dataframe(essays)
        log.info("Long-format frame: %s", df.shape)
        print(df.head(10).to_string())
