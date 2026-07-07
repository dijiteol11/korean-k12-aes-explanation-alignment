"""
Per-run model / prompt / API snapshot recorder (plan v2.3 §6.5, App. B).

Every LLM call in Stage 4 must record:
    * model id (fully qualified, dated)
    * API revision header (from the call response)
    * temperature
    * prompt file SHA-256
    * run start timestamp (UTC)
    * n_essays, purpose, stage (A/B/C)

Entries append to ``reports/snapshot_registry.md`` as markdown table rows.
The registry is append-only; never rewrite earlier rows.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import logging
from pathlib import Path

from configs.paths import PROJECT_ROOT, REPORTS_DIR

log = logging.getLogger(__name__)

REGISTRY_PATH: Path = REPORTS_DIR / "snapshot_registry.md"

# Model pins imported from configs.stage4 (pre-registered per SOTA review.md
# 2026-04-24 — 강화형 Option C). Two tracks:
#   * MODEL_ID_MAIN        — Sonnet, used for the full 4,860-essay analysis
#   * MODEL_ID_SENSITIVITY — Opus,   used for the 1,000-essay stratified audit
# Both must be set to exact date-stamped snapshots (e.g. "claude-sonnet-4-x-YYYYMMDD")
# before the researcher starts a pre-registered run. Claude Code MUST NOT
# change these during an active run — any change requires a new
# snapshot_registry row and a note in progress.md.
from configs.stage4 import (
    MODEL_ID_MAIN,
    MODEL_ID_SENSITIVITY,
    TEMPERATURE,
)

# Back-compat alias for callers that pre-date the dual-track decision.
# New code should import MODEL_ID_MAIN / MODEL_ID_SENSITIVITY explicitly.
MODEL_ID: str = MODEL_ID_MAIN

# Prompts are loaded from `prompts/{purpose}/{stage}.md` (assembled files,
# not `_wrapper/`). Always point ``make_stamp(prompt_path=...)`` at the
# assembled output so the recorded SHA matches what the LLM actually saw.


@dataclasses.dataclass(frozen=True)
class RunStamp:
    stage: str          # "A" | "B" | "C"
    purpose: str        # "설명" | "설득"
    track: str          # "main" | "sensitivity" | "alpha_pilot"
    n_essays: int
    prompt_path: Path
    prompt_sha256: str
    model_id: str = MODEL_ID_MAIN
    temperature: float = TEMPERATURE
    api_revision: str = ""   # filled after first successful call
    started_at_utc: str = dataclasses.field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    )


def prompt_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_stamp(
    stage: str,
    purpose: str,
    n_essays: int,
    prompt_path: Path,
    *,
    track: str = "main",
    model_id: str | None = None,
) -> RunStamp:
    """Build a RunStamp for the given pipeline call.

    Args:
        track:     "main" (Sonnet), "sensitivity" (Opus audit), or
                   "alpha_pilot" (main model, repeated scoring).
        model_id:  Override the default model for this track. Leave as
                   None to use the track's registered pin
                   (MODEL_ID_MAIN / MODEL_ID_SENSITIVITY).
    """
    if model_id is None:
        model_id = (
            MODEL_ID_SENSITIVITY if track == "sensitivity"
            else MODEL_ID_MAIN
        )
    return RunStamp(
        stage=stage,
        purpose=purpose,
        track=track,
        n_essays=n_essays,
        prompt_path=prompt_path,
        prompt_sha256=prompt_sha256(prompt_path),
        model_id=model_id,
    )


def append_to_registry(stamp: RunStamp) -> None:
    """Append a markdown table row to ``REGISTRY_PATH`` (create with header if absent)."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "| started_at_utc | stage | purpose | track | n_essays | model_id | "
        "api_revision | temperature | prompt_sha256 | prompt_path |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(
            "# Stage 4 LLM snapshot registry\n\n"
            "Append-only log. Never rewrite earlier rows.\n"
            "See plan v2.3 §6.5, Appendix B.\n\n" + header,
            encoding="utf-8",
        )
    rel_prompt = stamp.prompt_path.relative_to(PROJECT_ROOT)
    row = (
        f"| {stamp.started_at_utc} | {stamp.stage} | {stamp.purpose} | "
        f"{stamp.track} | {stamp.n_essays} | {stamp.model_id} | "
        f"{stamp.api_revision or 'TBD'} | {stamp.temperature} | "
        f"{stamp.prompt_sha256[:16]}… | {rel_prompt} |\n"
    )
    with REGISTRY_PATH.open("a", encoding="utf-8") as f:
        f.write(row)
    log.info("Appended snapshot: %s stage=%s purpose=%s n=%d",
             stamp.started_at_utc, stamp.stage, stamp.purpose, stamp.n_essays)
