"""
Stage 3.1 — cross-embedding sign consistency (plan v2.3 §4.2.3, 3rd metric).

For each (essay_id, trait, family, cv_label) cell that appears in both
``primary`` and ``robust_1`` sweep outputs, determine whether the two
embeddings agree on the SHAP *direction*. Cells with very small magnitude
in both embeddings (``|shap| < eps``) are treated as "near-zero" and
counted as matching (both embeddings agree the family is negligible).

Emits ``reports/stage3_shap/sign_consistency__{purpose}.csv`` with per
(trait × family) match rates.
"""
from __future__ import annotations

import argparse
import logging
import sys

import numpy as np
import pandas as pd

from configs.paths import FEATURE_FAMILIES
from src.shap_analysis.treeshap import SHAP_REPORT_DIR

log = logging.getLogger(__name__)

# Noise floor for sign determination. Typical family |SHAP| means are in
# 0.02–0.25 range (POC observation); 1e-3 is ~1% of that — values below
# this are treated as "no meaningful contribution" and collapse to sign=0.
SHAP_EPS: float = 1e-3


def _load_all_cvs(purpose: str, embedding: str) -> pd.DataFrame:
    parts = []
    for cv in ("grade_stratified", "cross_prompt"):
        p = SHAP_REPORT_DIR / f"local_shap__{purpose}__{embedding}__{cv}.parquet"
        parts.append(pd.read_parquet(p))
    return pd.concat(parts, ignore_index=True)


def _discretize(x: np.ndarray, eps: float = SHAP_EPS) -> np.ndarray:
    """Map continuous SHAP values to {-1, 0, +1} with noise floor eps."""
    out = np.zeros_like(x, dtype=np.int8)
    out[x > eps] = 1
    out[x < -eps] = -1
    return out


def compute_sign_consistency(purpose: str, eps: float = SHAP_EPS) -> pd.DataFrame:
    a = _load_all_cvs(purpose, "primary")
    b = _load_all_cvs(purpose, "robust_1")
    key = ["essay_id", "trait", "family", "cv_label"]
    merged = a.merge(
        b, on=key, suffixes=("_primary", "_robust_1"), validate="one_to_one",
    )
    merged["sign_primary"] = _discretize(merged["shap_sum_primary"].to_numpy(), eps)
    merged["sign_robust_1"] = _discretize(merged["shap_sum_robust_1"].to_numpy(), eps)
    merged["match"] = merged["sign_primary"] == merged["sign_robust_1"]
    merged["both_zero"] = (merged["sign_primary"] == 0) & (merged["sign_robust_1"] == 0)
    merged["both_nonzero_match"] = merged["match"] & ~merged["both_zero"]
    merged["opposite"] = (
        (merged["sign_primary"] == 1) & (merged["sign_robust_1"] == -1)
    ) | (
        (merged["sign_primary"] == -1) & (merged["sign_robust_1"] == 1)
    )

    by_tf = (
        merged.groupby(["trait", "family"], observed=True)
        .agg(
            n=("match", "size"),
            match_rate=("match", "mean"),
            both_zero_rate=("both_zero", "mean"),
            nonzero_match_rate=("both_nonzero_match", "mean"),
            opposite_rate=("opposite", "mean"),
        )
        .reset_index()
    )
    by_tf.insert(0, "purpose", purpose)
    # Keep rows sorted by trait then FEATURE_FAMILIES order for readability.
    fam_order = {f: i for i, f in enumerate(FEATURE_FAMILIES)}
    by_tf["_fam_order"] = by_tf["family"].map(fam_order)
    by_tf = by_tf.sort_values(["trait", "_fam_order"]).drop(columns="_fam_order")
    return by_tf.reset_index(drop=True)


def run(purpose: str) -> None:
    df = compute_sign_consistency(purpose)
    out = SHAP_REPORT_DIR / f"sign_consistency__{purpose}.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (rows=%d)", out, len(df))

    overall_match = df["match_rate"].mean()
    opposite_share = df["opposite_rate"].mean()
    log.info(
        "%s sign match (trait×family avg): %.3f  | opposite share: %.4f",
        purpose, overall_match, opposite_share,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", required=True, choices=("설명", "설득"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    run(args.purpose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
