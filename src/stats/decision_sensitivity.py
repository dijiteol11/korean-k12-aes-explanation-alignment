"""Sensitivity grid for supplementary attribution-table thresholds.

This is deliberately separate from the v1.3 main Jaccard contrast, whose
metric is continuous and has no UR/CIV threshold perturbation.
"""
from __future__ import annotations

from itertools import product

import pandas as pd


def perturb_attribution_thresholds(
    labeled_df: pd.DataFrame,
    *,
    justification_thresholds: tuple[float, ...] = (0.05, 0.10, 0.15),
    jaccard_unstable_thresholds: tuple[float, ...] = (0.40, 0.50, 0.60),
) -> pd.DataFrame:
    required = {"justification_rate", "jaccard"}
    missing = required - set(labeled_df.columns)
    if missing:
        raise KeyError(f"labeled dataframe missing columns: {sorted(missing)}")

    rows: list[dict] = []
    for justification_max, jaccard_min in product(
        justification_thresholds,
        jaccard_unstable_thresholds,
    ):
        civ = labeled_df["justification_rate"].fillna(1.0) <= justification_max
        ur = labeled_df["jaccard"].fillna(0.0) < jaccard_min
        rows.append({
            "justification_max": float(justification_max),
            "jaccard_min": float(jaccard_min),
            "n": int(len(labeled_df)),
            "civ_rate": float(civ.mean()),
            "ur_rate": float(ur.mean()),
            "any_flag_rate": float((civ | ur).mean()),
        })
    return pd.DataFrame(rows)
