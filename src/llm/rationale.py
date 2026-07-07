"""
Stage 4-C — Rationale (plan v2.3 §4.3.1 step C).

Given Stage A evidence + Stage B scores, produces per-trait natural-
language justifications. This is the ONLY stage that generates the
rationale strings coded downstream in Stage 4.3 (4-level alignment).

Output JSON schema (per essay)::

    {
      "essay_id": int,
      "purpose": "설명" | "설득",
      "rationale": {
        "task_1":         {"text": str, "cited_spans": [int, ...]},
        ...
        "holistic":       {"text": str, "cited_spans": [int, ...]}
      }
    }

The 3-step separation (A evidence → B score → C rationale) is mandated
by plan v2.3 §4.3.1 to avoid **circular justification** (score and
rationale produced in one call tend to validate each other).

**Execution policy**: see ``src/llm/__init__.py``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from configs.paths import PROJECT_ROOT, REPORTS_DIR
from src.llm.evidence import load_evidence
from src.llm.score import load_scores
from src.llm.snapshot import MODEL_ID, TEMPERATURE, append_to_registry, make_stamp

log = logging.getLogger(__name__)

PROMPT_DIR: Path = PROJECT_ROOT / "prompts"
OUTPUT_DIR: Path = REPORTS_DIR / "stage4_llm" / "rationale"


def prompt_path(purpose: str) -> Path:
    return PROMPT_DIR / purpose / "C.md"


def run_rationale(
    purpose: str,
    essays: list[dict],
    *,
    batch_size: int = 10,
) -> None:
    """Stream rationale JSON to ``OUTPUT_DIR / {purpose}.jsonl``.

    Requires Stage A + Stage B outputs to exist.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{purpose}.jsonl"
    p = prompt_path(purpose)
    if not p.exists():
        raise FileNotFoundError(
            f"Rationale prompt missing: {p}. Author it from prompts/_template.md."
        )
    ev = load_evidence(purpose)
    sc = load_scores(purpose)
    if not ev or not sc:
        raise RuntimeError(
            f"Stage A or B missing for {purpose}. Run evidence.py and score.py first."
        )

    stamp = make_stamp(stage="C", purpose=purpose, n_essays=len(essays), prompt_path=p)
    append_to_registry(stamp)

    raise NotImplementedError(
        "Stage 4-C rationale is executed manually by the researcher. "
        f"Pin: model={MODEL_ID}, temperature={TEMPERATURE}, "
        f"prompt={p}, output={out}."
    )


def load_rationale(purpose: str) -> list[dict]:
    path = OUTPUT_DIR / f"{purpose}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
