"""
Stage 4.2 — LLM consistency pilot (plan v2.3 §4.3.2).

Re-runs Stage B scoring five times (same temperature=0) on a stratified
500-essay pilot per purpose to measure LLM internal consistency via
Krippendorff's α per (purpose, trait). Traits with α < 0.80 are
EXCLUDED from the main analysis — the exclusion itself is reported
("LLM 이 특정 영역에서 일관된 판정을 내리지 못함", v2.3 §4.3.2).

This module is authored but **executed manually by the researcher**.
See ``src/llm/__init__.py`` execution policy.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import REPORTS_DIR
from configs.shap import REPORT_SUBDIR  # unused but documents import convention

log = logging.getLogger(__name__)

PILOT_DIR: Path = REPORTS_DIR / "stage4_llm" / "pilot_consistency"
ALPHA_MIN: float = 0.80  # §4.3.2 exclusion threshold
N_PILOT: int = 500        # essays per purpose
N_REPEAT: int = 5         # scoring passes


def krippendorff_alpha_ordinal(scores: np.ndarray) -> float:
    """Compute ordinal Krippendorff's α for an (n_items, n_raters) matrix.

    ``scores`` holds integer scores in {1,2,3,4,5}; NaN represents missing.
    Uses ordinal difference function Δ(c, k) = (c - k)^2.

    Returns α in (-inf, 1]. α=1 perfect; α=0 chance-level; α<0 worse than chance.
    """
    x = np.asarray(scores, dtype=float)
    n_items, n_raters = x.shape
    mask = ~np.isnan(x)
    counts_per_item = mask.sum(axis=1)
    valid_items = counts_per_item >= 2
    if not valid_items.any():
        return float("nan")

    # Observed disagreement: sum over items of pairwise squared diffs / n_pairs
    observed = 0.0
    n_pairs_total = 0
    for i in np.where(valid_items)[0]:
        vals = x[i, mask[i]]
        n = vals.size
        pair_sum = 0.0
        for a in range(n):
            for b in range(a + 1, n):
                pair_sum += (vals[a] - vals[b]) ** 2
        observed += pair_sum
        n_pairs_total += n * (n - 1) / 2
    Do = observed / n_pairs_total if n_pairs_total else float("nan")

    # Expected disagreement: pairwise squared diffs across all ratings
    all_vals = x[mask]
    N = all_vals.size
    expected = 0.0
    for a in range(N):
        for b in range(a + 1, N):
            expected += (all_vals[a] - all_vals[b]) ** 2
    De = expected / (N * (N - 1) / 2) if N > 1 else float("nan")
    return 1.0 - (Do / De) if De else float("nan")


def load_pilot_repeats(purpose: str) -> pd.DataFrame:
    """Load the 5-repeat pilot scoring output into long form.

    Expects the researcher to have run ``score.py`` 5× with output at::

        reports/stage4_llm/pilot_consistency/{purpose}/run_{1..5}.jsonl
    """
    out_dir = PILOT_DIR / purpose
    rows: list[dict] = []
    for run_id in range(1, N_REPEAT + 1):
        p = out_dir / f"run_{run_id}.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            rec = json.loads(line)
            for trait, info in rec["scores"].items():
                rows.append({
                    "essay_id": rec["essay_id"],
                    "run_id": run_id,
                    "trait": trait,
                    "score": info["score"],
                })
    return pd.DataFrame(rows)


def compute_per_trait_alpha(purpose: str) -> pd.DataFrame:
    df = load_pilot_repeats(purpose)
    if df.empty:
        raise RuntimeError(f"No pilot repeats found for {purpose}")
    rows: list[dict] = []
    for trait, sub in df.groupby("trait"):
        pivot = sub.pivot(index="essay_id", columns="run_id", values="score")
        mat = pivot.to_numpy(dtype=float)
        alpha = krippendorff_alpha_ordinal(mat)
        rows.append({
            "purpose": purpose,
            "trait": trait,
            "n_items": int(pivot.shape[0]),
            "n_raters": int(pivot.shape[1]),
            "alpha": alpha,
            "exclude_from_main": bool(alpha < ALPHA_MIN) if not np.isnan(alpha) else True,
        })
    out = pd.DataFrame(rows)
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(PILOT_DIR / f"alpha__{purpose}.csv", index=False)
    log.info("Wrote alpha table for %s: %d traits, %d excluded",
             purpose, len(out), int(out["exclude_from_main"].sum()))
    return out
