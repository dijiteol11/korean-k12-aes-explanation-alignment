"""
Global aggregation + QWK pre-flight + cross-embedding Jaccard.

* ``global_family_shap(long_df)`` — trait × family mean |SHAP| with Top-K
  family list per trait (K from ``configs.shap.JACCARD_TOP_K``).
* ``qwk_preflight(purpose, embedding, thresholds)`` — reads Stage 2.2
  aggregate LOPO QWK CSV and emits a trait × threshold flag table. Main
  threshold is ``configs.shap.QWK_PREFLIGHT_MIN``; extras enable appendix
  sensitivity analysis.
* ``jaccard_top_k(long_a, long_b)`` — reserved for Stage 3 D (primary ↔
  robust_1 cross-embedding Top-K overlap).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from configs.paths import FEATURE_FAMILIES, REPORTS_DIR
from configs.shap import JACCARD_INSTABILITY, JACCARD_TOP_K, QWK_PREFLIGHT_MIN

log = logging.getLogger(__name__)

OOF_DIR: Path = REPORTS_DIR / "stage2_models"


def global_family_shap(long_df: pd.DataFrame) -> pd.DataFrame:
    """Trait × family mean |SHAP|, plus dense rank (1 = highest)."""
    agg = (
        long_df
        .assign(abs_shap=lambda d: d["shap_sum"].abs())
        .groupby(["trait", "family"], observed=True)["abs_shap"]
        .mean()
        .reset_index(name="mean_abs_shap")
    )
    agg["rank"] = (
        agg.groupby("trait")["mean_abs_shap"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    return agg.sort_values(["trait", "rank"]).reset_index(drop=True)


def top_k_families(global_df: pd.DataFrame, k: int = JACCARD_TOP_K) -> dict[str, list[str]]:
    """Per-trait Top-K family list, ordered by rank (stable tie-break by name)."""
    out: dict[str, list[str]] = {}
    for trait, sub in global_df.groupby("trait"):
        top = sub.nsmallest(k, "rank")
        out[trait] = top.sort_values(["rank", "family"])["family"].tolist()
    return out


def qwk_preflight(
    purpose: str,
    embedding: str,
    thresholds: list[float] | None = None,
) -> pd.DataFrame:
    """Flag traits whose LOPO (cross_prompt) QWK falls below each threshold.

    The MAIN threshold (``configs.shap.QWK_PREFLIGHT_MIN``) feeds Stage 5;
    extras (0.10, 0.20 by default) constitute the pre-registered sensitivity
    analysis.
    """
    if thresholds is None:
        # Main + appendix sensitivity (researcher-approved 2026-04-22).
        thresholds = [0.10, QWK_PREFLIGHT_MIN, 0.20]
    csv = OOF_DIR / f"cv_cross_prompt__{purpose}__{embedding}__agg.csv"
    if not csv.exists():
        raise FileNotFoundError(csv)
    df = pd.read_csv(csv)[["trait", "qwk_mean"]].copy()
    df["purpose"] = purpose
    df["embedding"] = embedding
    for t in thresholds:
        col = f"flag_qwk_lt_{int(round(t*100)):02d}"
        df[col] = df["qwk_mean"] < t
    main_col = f"flag_qwk_lt_{int(round(QWK_PREFLIGHT_MIN*100)):02d}"
    df["low_signal_main"] = df[main_col]
    return df


def jaccard_top_k(
    long_a: pd.DataFrame,
    long_b: pd.DataFrame,
    k: int = JACCARD_TOP_K,
) -> pd.DataFrame:
    """Per-trait Jaccard of Top-K family sets between two SHAP long tables.

    Intended for Stage 3 D (primary ↔ robust_1). Both inputs must share the
    same ``trait`` set and use the same 8-family classification.
    """
    ga = global_family_shap(long_a)
    gb = global_family_shap(long_b)
    top_a = top_k_families(ga, k=k)
    top_b = top_k_families(gb, k=k)
    rows: list[dict] = []
    traits = sorted(set(top_a) & set(top_b))
    for t in traits:
        a, b = set(top_a[t]), set(top_b[t])
        inter = a & b
        union = a | b
        jac = len(inter) / len(union) if union else float("nan")
        rows.append({
            "trait": t,
            "top_a": "|".join(top_a[t]),
            "top_b": "|".join(top_b[t]),
            "intersection": "|".join(sorted(inter)),
            "jaccard": jac,
            "unstable": jac < JACCARD_INSTABILITY if union else False,
        })
    return pd.DataFrame(rows)
