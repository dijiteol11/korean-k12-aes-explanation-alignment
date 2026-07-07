"""
Stage 4-A — Evidence extraction (plan v2.3 §4.3.1 step A).

For each essay × trait, the LLM returns structured evidence spans —
token offsets and short excerpts it will cite as justification in
later stages. No scoring here: the call is strictly an indexing pass.

Output JSON schema (per essay)::

    {
      "essay_id": int,
      "purpose": "설명" | "설득",
      "evidence": {
        "task_1":         [{"span": [start, end], "text": str, "tag": str}, ...],
        "content_1":      [...], "content_2":      [...], "content_3":      [...],
        "organization_1": [...], "organization_2": [...],
        "expression_1":   [...], "expression_2":   [...],
        "holistic":       [...]
      }
    }

``tag`` is a free-form short category the prompt asks the LLM to assign
(e.g. "thesis_statement", "counterargument", "transition_word").

**Execution policy**: this module is authored here but executed by the
researcher from a separate shell; Claude Code does not call the API.
See ``src/llm/__init__.py``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from configs.paths import PROJECT_ROOT, REPORTS_DIR
from src.llm.snapshot import MODEL_ID, TEMPERATURE, append_to_registry, make_stamp

log = logging.getLogger(__name__)

PROMPT_DIR: Path = PROJECT_ROOT / "prompts"
OUTPUT_DIR: Path = REPORTS_DIR / "stage4_llm" / "evidence"


def prompt_path(purpose: str) -> Path:
    return PROMPT_DIR / purpose / "A.md"


def run_evidence(
    purpose: str,
    essays: list[dict],
    *,
    batch_size: int = 10,
) -> None:
    """Stream evidence JSON to ``OUTPUT_DIR / {purpose}.jsonl``.

    Args:
        purpose:     "설명" or "설득".
        essays:      list of {"essay_id": int, "text": str} dicts.
        batch_size:  LLM batch size (prompt concatenates up to N essays).

    The call is idempotent: reruns overwrite the entire JSONL file.
    To append incrementally, the researcher should chunk the essay list
    externally and pass subsets.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{purpose}.jsonl"
    p = prompt_path(purpose)
    if not p.exists():
        raise FileNotFoundError(
            f"Evidence prompt missing: {p}. Author it from prompts/_template.md."
        )

    stamp = make_stamp(stage="A", purpose=purpose, n_essays=len(essays), prompt_path=p)
    append_to_registry(stamp)

    # NOTE: API client wiring lives in the researcher's shell, not here.
    # The function body below is intentionally left as a sketch — fill in
    # with the Anthropic SDK call matching the snapshot.MODEL_ID pin.
    raise NotImplementedError(
        "Stage 4-A evidence extraction is executed manually by the "
        "researcher. Wire the Anthropic SDK call here before running. "
        f"Pin: model={MODEL_ID}, temperature={TEMPERATURE}, "
        f"prompt={p}, output={out}"
    )


def load_evidence(purpose: str) -> list[dict]:
    path = OUTPUT_DIR / f"{purpose}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
