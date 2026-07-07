"""
Stage 4 sensitivity sub-study — 4-way stratified sampler (n=1000).

Per SOTA review.md §"권고 설계" (2026-04-24): the Opus sensitivity audit
must sample along grade × prompt × score_band × NA-flag to surface
model-dependence patterns that could be masked by a uniform random draw
(Jin et al., 2025; Saricaoglu & Bilki, 2025; Wang et al., 2024).

Strata:
    - grade:      초5, 초6, 중1, 중2, 중3
    - prompt_id:  per-purpose prompt set (11 설명, 12 설득)
    - score_band: derived from Sonnet main Stage B average across 8 traits —
                  low(avg<2.5), mid(2.5≤avg<4.0), high(avg≥4.0)
    - na_flag:    True if any trait's Sonnet Stage B score is null

Sampling is proportional within the joint stratification, floor-1 per
non-empty cell. If the total exceeds the target n, cells are subsampled
proportionally while retaining ≥1 per cell. The sampled essay_ids are
written to ``reports/stage4_llm/sensitivity_sample.csv`` with their
stratum labels, pre-registered before Opus calls begin.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import REPORTS_DIR
from configs.stage4 import SENSITIVITY_N_ESSAYS

log = logging.getLogger(__name__)

OUT_PATH: Path = REPORTS_DIR / "stage4_llm" / "sensitivity_sample.csv"
DEFAULT_SEED: int = 42


def assign_score_band(avg_score: float) -> str:
    if np.isnan(avg_score):
        return "na"
    if avg_score < 2.5:
        return "low"
    if avg_score < 4.0:
        return "mid"
    return "high"


def build_strata(main_scores_long: pd.DataFrame, essay_meta: pd.DataFrame) -> pd.DataFrame:
    """Join Sonnet main Stage B scores with essay metadata and label strata.

    Args:
        main_scores_long: columns essay_id, trait, score (int|None).
        essay_meta:       columns essay_id, grade, prompt_id (from loader).
    """
    # per-essay score-band & na-flag from trait-level long form
    agg = (
        main_scores_long
        .assign(
            _any_na=lambda d: d["score"].isna(),
            _score=lambda d: d["score"].astype(float),
        )
        .groupby("essay_id")
        .agg(avg_score=("_score", "mean"), na_flag=("_any_na", "any"))
        .reset_index()
    )
    agg["score_band"] = agg["avg_score"].map(assign_score_band)
    joined = agg.merge(essay_meta, on="essay_id", how="inner", validate="one_to_one")
    joined["stratum"] = (
        joined["grade"].astype(str)
        + "|" + joined["prompt_id"].astype(str)
        + "|" + joined["score_band"]
        + "|" + joined["na_flag"].astype(str)
    )
    return joined


def stratified_sample(
    strata_df: pd.DataFrame,
    n_target: int = SENSITIVITY_N_ESSAYS,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    groups = strata_df.groupby("stratum", sort=True)
    n_cells = groups.ngroups
    if n_cells > n_target:
        raise RuntimeError(
            f"{n_cells} strata > n_target {n_target}; cannot floor-1. "
            "Collapse score_band or drop prompt_id from strata."
        )

    # First pass: one per cell.
    picks: list[pd.DataFrame] = []
    for _, g in groups:
        idx = rng.choice(len(g), size=1, replace=False)
        picks.append(g.iloc[idx])
    base = pd.concat(picks, ignore_index=True)

    remaining_target = n_target - len(base)
    if remaining_target > 0:
        # Proportional allocation across remaining pool.
        pool = strata_df.drop(index=base.index, errors="ignore").reset_index(drop=True)
        # Allocate slot count per cell proportional to cell size (minus 1 already taken).
        cell_counts = pool.groupby("stratum").size()
        weights = cell_counts / cell_counts.sum()
        extra_per_cell = np.floor(weights * remaining_target).astype(int)
        # Fill leftover slots greedily by largest residual.
        shortfall = remaining_target - int(extra_per_cell.sum())
        residuals = (weights * remaining_target) - extra_per_cell
        if shortfall > 0:
            top = residuals.sort_values(ascending=False).head(shortfall).index
            for s in top:
                extra_per_cell[s] = extra_per_cell.get(s, 0) + 1
        extra_picks: list[pd.DataFrame] = []
        for stratum, k in extra_per_cell.items():
            if k <= 0:
                continue
            subset = pool[pool["stratum"] == stratum]
            k_eff = int(min(k, len(subset)))
            if k_eff == 0:
                continue
            idx = rng.choice(len(subset), size=k_eff, replace=False)
            extra_picks.append(subset.iloc[idx])
        if extra_picks:
            base = pd.concat([base] + extra_picks, ignore_index=True)

    out = base.sort_values(["grade", "prompt_id", "essay_id"]).reset_index(drop=True)
    log.info("Sensitivity sample: %d essays across %d strata (target %d)",
             len(out), strata_df["stratum"].nunique(), n_target)
    return out


def write_sample(sample_df: pd.DataFrame, path: Path = OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_csv(path, index=False)
    log.info("Wrote %s (%d rows)", path, len(sample_df))
