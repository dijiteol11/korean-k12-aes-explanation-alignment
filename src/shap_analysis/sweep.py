"""
Iterate the single-cell TreeSHAP primitive over every (trait, fold) for a
given (purpose, embedding, cv), and emit one long-form parquet per CV.

Long-form schema::

    essay_id  family  shap_sum  purpose  embedding  trait  cv_label  fold_label

One row per (essay × family) in the fold's test set. Each essay appears in
exactly one fold per CV, so a full sweep writes ``n_essays × 9 traits × 8
families`` rows per (purpose, embedding, cv) parquet.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from configs.shap import ADDITIVITY_TOL
from src.shap_analysis.treeshap import (
    CellSpec, MODELS_DIR, SHAP_REPORT_DIR, compute_cell_shap,
)

log = logging.getLogger(__name__)

_FILENAME_RE = re.compile(r"^(?P<trait>.+?)__(?P<cv>[^_]+(?:_[^_]+)?)__(?P<fold>.+)\.json$")


def _discover_cells(purpose: str, embedding: str, cv_label: str) -> list[tuple[str, str]]:
    """Enumerate (trait, fold_label) pairs by parsing model filenames."""
    model_dir = MODELS_DIR / f"{purpose}__{embedding}"
    if not model_dir.exists():
        raise FileNotFoundError(f"Model dir not found: {model_dir}")
    pairs: list[tuple[str, str]] = []
    for p in sorted(model_dir.glob("*.json")):
        # expected: {trait}__{cv_label}__{fold_label}.json
        stem = p.stem
        # Split on double underscore to respect multi-token trait names like organization_1.
        parts = stem.split("__")
        if len(parts) != 3:
            log.warning("Skipping unparseable filename: %s", p.name)
            continue
        trait, cv_tag, fold_label = parts
        if cv_tag == cv_label:
            pairs.append((trait, fold_label))
    return pairs


def run_sweep(purpose: str, embedding: str, cv_label: str) -> pd.DataFrame:
    """Run ``compute_cell_shap`` over every (trait, fold) for the slice."""
    cells = _discover_cells(purpose, embedding, cv_label)
    if not cells:
        raise RuntimeError(
            f"No cells discovered for {purpose}/{embedding}/{cv_label}"
        )
    log.info("Sweep %s/%s/%s: %d cells",
             purpose, embedding, cv_label, len(cells))

    long_parts: list[pd.DataFrame] = []
    max_err = 0.0
    for i, (trait, fold_label) in enumerate(cells, 1):
        spec = CellSpec(
            purpose=purpose, embedding=embedding, trait=trait,
            cv_label=cv_label, fold_label=fold_label,
        )
        out = compute_cell_shap(spec)
        err = out["additivity_max_abs_error"]
        max_err = max(max_err, err)
        if err > ADDITIVITY_TOL:
            log.warning("High additivity error %.2e > %.0e for %s",
                        err, ADDITIVITY_TOL, spec.model_path.name)
        long_parts.append(out["long_df"])
        if i % 10 == 0 or i == len(cells):
            log.info("  %d/%d cells done (running max err=%.2e)",
                     i, len(cells), max_err)

    long_df = pd.concat(long_parts, ignore_index=True)
    log.info("Sweep done: %d rows, max additivity_err=%.2e",
             len(long_df), max_err)
    return long_df


def write_sweep(purpose: str, embedding: str, cv_label: str) -> Path:
    df = run_sweep(purpose, embedding, cv_label)
    SHAP_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SHAP_REPORT_DIR / f"local_shap__{purpose}__{embedding}__{cv_label}.parquet"
    df.to_parquet(out_path, index=False)
    log.info("Wrote %s", out_path)
    return out_path
