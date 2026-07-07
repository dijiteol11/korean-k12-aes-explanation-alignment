"""
Stability diagnostics for Stage 3 SHAP (plan v2.3 §4.2.3).

Within a single (purpose, embedding, cv) slice:
    * Per-trait fold-to-fold Kendall τ on family-|SHAP| rankings.
    * Per-essay sign-consistency across folds (only meaningful when an
      essay participates in multiple folds — i.e. across *embeddings*,
      not across folds of the same CV, since each essay is in exactly
      one fold per CV).

Cross-embedding Jaccard is deferred to ``aggregate.jaccard_top_k`` because
it operates on two sweep outputs.
"""
from __future__ import annotations

import logging
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from configs.paths import FEATURE_FAMILIES
from configs.shap import KENDALL_TAU_INSTABILITY

log = logging.getLogger(__name__)


def _family_rank_per_fold(long_df: pd.DataFrame) -> pd.DataFrame:
    """For each (trait, fold_label), rank the 8 families by mean |shap_sum|.

    Returns a DataFrame indexed by (trait, fold_label) with 8 columns
    (one per family) holding the ordinal rank (1 = highest mean |SHAP|).
    """
    agg = (
        long_df
        .assign(abs_shap=lambda d: d["shap_sum"].abs())
        .groupby(["trait", "fold_label", "family"], observed=True)["abs_shap"]
        .mean()
        .reset_index()
    )
    pivoted = agg.pivot(
        index=["trait", "fold_label"], columns="family", values="abs_shap"
    )
    # Missing families (empty) become NaN → fill with 0 for ranking.
    pivoted = pivoted.reindex(columns=list(FEATURE_FAMILIES)).fillna(0.0)
    ranks = pivoted.rank(axis=1, ascending=False, method="min")
    return ranks


def kendall_tau_by_trait(long_df: pd.DataFrame) -> pd.DataFrame:
    """Mean pairwise Kendall τ on family-rank vectors across folds per trait.

    Returns a DataFrame with columns::

        trait, n_folds, n_pairs, tau_mean, tau_min, tau_max,
        unstable  (bool — tau_mean < KENDALL_TAU_INSTABILITY)
    """
    ranks = _family_rank_per_fold(long_df)
    rows: list[dict] = []
    for trait, sub in ranks.groupby(level="trait"):
        fold_matrix = sub.to_numpy()
        n_folds = fold_matrix.shape[0]
        if n_folds < 2:
            rows.append({
                "trait": trait, "n_folds": n_folds, "n_pairs": 0,
                "tau_mean": np.nan, "tau_min": np.nan, "tau_max": np.nan,
                "unstable": False,
            })
            continue
        taus: list[float] = []
        for i, j in combinations(range(n_folds), 2):
            tau, _ = kendalltau(fold_matrix[i], fold_matrix[j])
            if not np.isnan(tau):
                taus.append(tau)
        arr = np.asarray(taus, dtype=float)
        rows.append({
            "trait": trait,
            "n_folds": int(n_folds),
            "n_pairs": int(arr.size),
            "tau_mean": float(arr.mean()) if arr.size else np.nan,
            "tau_min": float(arr.min()) if arr.size else np.nan,
            "tau_max": float(arr.max()) if arr.size else np.nan,
            "unstable": bool(arr.mean() < KENDALL_TAU_INSTABILITY) if arr.size else False,
        })
    return pd.DataFrame(rows).sort_values("trait").reset_index(drop=True)
