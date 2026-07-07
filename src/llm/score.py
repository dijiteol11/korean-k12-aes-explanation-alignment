"""
Stage 4-B — Scoring (plan v2.3 §4.3.1 step B).

Consumes Stage A evidence + the essay text; returns per-trait scores
(1-5), confidence (0.0-1.0), and pointers into evidence spans.

Output JSON schema (per essay)::

    {
      "essay_id": int,
      "purpose": "설명" | "설득",
      "scores": {
        "task_1":         {"score": int, "confidence": float, "span_refs": [int, ...]},
        ...
        "holistic":       {"score": int, "confidence": float, "span_refs": [int, ...]}
      }
    }

``span_refs`` indexes into the Stage-A evidence list for that trait.
No natural-language justification here — that's Stage C.

**Execution policy**: see ``src/llm/__init__.py``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from configs.paths import PROJECT_ROOT, REPORTS_DIR
from src.llm.evidence import load_evidence
from src.llm.snapshot import MODEL_ID, TEMPERATURE, append_to_registry, make_stamp

log = logging.getLogger(__name__)

PROMPT_DIR: Path = PROJECT_ROOT / "prompts"
OUTPUT_DIR: Path = REPORTS_DIR / "stage4_llm" / "scores"


def prompt_path(purpose: str) -> Path:
    return PROMPT_DIR / purpose / "B.md"


def run_scoring(
    purpose: str,
    essays: list[dict],
    *,
    batch_size: int = 10,
) -> None:
    """Stream scores to ``OUTPUT_DIR / {purpose}.jsonl``.

    Requires Stage A output to exist (``load_evidence`` returns non-empty).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{purpose}.jsonl"
    p = prompt_path(purpose)
    if not p.exists():
        raise FileNotFoundError(
            f"Scoring prompt missing: {p}. Author it from prompts/_template.md."
        )
    ev = load_evidence(purpose)
    if not ev:
        raise RuntimeError(
            f"Stage A evidence not found for {purpose}. Run evidence.py first."
        )

    stamp = make_stamp(stage="B", purpose=purpose, n_essays=len(essays), prompt_path=p)
    append_to_registry(stamp)

    raise NotImplementedError(
        "Stage 4-B scoring is executed manually by the researcher. "
        f"Pin: model={MODEL_ID}, temperature={TEMPERATURE}, "
        f"prompt={p}, output={out}. Consume evidence: {len(ev)} records."
    )


def load_scores(purpose: str) -> list[dict]:
    path = OUTPUT_DIR / f"{purpose}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
