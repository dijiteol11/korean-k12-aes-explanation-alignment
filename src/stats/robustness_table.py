"""
Stage 2.2c — robustness comparison table (plan v2.3 §5.3 body table).

Synthesizes Stage 2.2 CV aggregates + Stage 3 SHAP artifacts into a single
per-trait table across four model/embedding axes:

    * ``primary``             — main regressor on KR-SBERT-V40K
    * ``robust_1``            — regressor on KoSimCSE-roberta
    * ``primary__ordinal``    — ordinal XGBClassifier on KR-SBERT-V40K
    * ``no_sbert``            — wiring baseline without SBERT (descriptive)

For each trait the table reports:

    * Grade-stratified QWK / MAE (goodness-of-fit)
    * Cross-prompt QWK / MAE    (generalization — primary indicator v2.3 §4.2.2)
    * SHAP Top-3 family (primary vs robust_1, Jaccard)
    * Cross-embedding sign-match rate (primary ↔ robust_1)
    * Pre-flight flag @ {0.10, 0.15, 0.20} on the main ``primary`` LOPO QWK

Outputs one CSV per purpose::

    reports/stage2_models/robustness_table__{purpose}.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from configs.paths import REPORTS_DIR
from src.shap_analysis.aggregate import global_family_shap, top_k_families

log = logging.getLogger(__name__)

OOF_DIR: Path = REPORTS_DIR / "stage2_models"
SHAP_DIR: Path = REPORTS_DIR / "stage3_shap"
EMBEDDINGS = ("no_sbert", "primary", "robust_1", "robust_2", "primary__ordinal")


def _read_agg(purpose: str, embedding: str, cv: str) -> pd.DataFrame:
    p = OOF_DIR / f"cv_{cv}__{purpose}__{embedding}__agg.csv"
    if not p.exists():
        return pd.DataFrame(columns=["trait"])
    df = pd.read_csv(p)[["trait", "qwk_mean", "mae_mean"]].copy()
    df.rename(
        columns={
            "qwk_mean": f"qwk_{cv}__{embedding}",
            "mae_mean": f"mae_{cv}__{embedding}",
        },
        inplace=True,
    )
    return df


def _load_top3(purpose: str, embedding: str) -> dict[str, list[str]]:
    path = SHAP_DIR / f"global_shap__{purpose}__{embedding}.csv"
    if not path.exists():
        return {}
    g = pd.read_csv(path)
    return top_k_families(g, k=3)


def _load_jaccard(purpose: str) -> pd.DataFrame:
    p = SHAP_DIR / f"jaccard__{purpose}__primary_vs_robust_1.csv"
    if not p.exists():
        return pd.DataFrame(columns=["trait", "jaccard"])
    return pd.read_csv(p)[["trait", "jaccard"]].rename(
        columns={"jaccard": "jaccard_primary_vs_robust_1"}
    )


def _load_sign_consistency_overall(purpose: str) -> pd.DataFrame:
    p = SHAP_DIR / f"sign_consistency__{purpose}.csv"
    if not p.exists():
        return pd.DataFrame(columns=["trait", "sign_match_mean"])
    df = pd.read_csv(p)
    return (
        df.groupby("trait")["match_rate"]
        .mean()
        .reset_index(name="sign_match_mean")
    )


def _load_preflight(purpose: str, embedding: str) -> pd.DataFrame:
    p = SHAP_DIR / f"preflight_qwk__{purpose}__{embedding}.csv"
    if not p.exists():
        return pd.DataFrame(columns=["trait"])
    df = pd.read_csv(p)
    keep = ["trait", "flag_qwk_lt_10", "flag_qwk_lt_15", "flag_qwk_lt_20"]
    return df[keep].rename(columns={
        "flag_qwk_lt_10": "preflight_lt_10",
        "flag_qwk_lt_15": "preflight_lt_15",
        "preflight_lt_20": "preflight_lt_20",
    }, errors="ignore").rename(columns={"flag_qwk_lt_20": "preflight_lt_20"})


def build(purpose: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for emb in EMBEDDINGS:
        for cv in ("grade_stratified", "cross_prompt"):
            frames.append(_read_agg(purpose, emb, cv))
    merged: pd.DataFrame | None = None
    for f in frames:
        if f.empty:
            continue
        merged = f if merged is None else merged.merge(f, on="trait", how="outer")
    assert merged is not None, f"No agg CSVs found for {purpose}"

    top3_primary = _load_top3(purpose, "primary")
    top3_robust1 = _load_top3(purpose, "robust_1")
    top3_robust2 = _load_top3(purpose, "robust_2")
    merged["top3_primary"] = merged["trait"].map(
        lambda t: "|".join(top3_primary.get(t, []))
    )
    merged["top3_robust_1"] = merged["trait"].map(
        lambda t: "|".join(top3_robust1.get(t, []))
    )
    merged["top3_robust_2"] = merged["trait"].map(
        lambda t: "|".join(top3_robust2.get(t, []))
    )

    jac = _load_jaccard(purpose)
    if not jac.empty:
        merged = merged.merge(jac, on="trait", how="left")
    # primary ↔ robust_2 appendix Jaccard
    jac2_path = SHAP_DIR / f"jaccard__{purpose}__primary_vs_robust_2.csv"
    if jac2_path.exists():
        jac2 = pd.read_csv(jac2_path)[["trait", "jaccard"]].rename(
            columns={"jaccard": "jaccard_primary_vs_robust_2"}
        )
        merged = merged.merge(jac2, on="trait", how="left")
    sc = _load_sign_consistency_overall(purpose)
    if not sc.empty:
        merged = merged.merge(sc, on="trait", how="left")
    pf = _load_preflight(purpose, "primary")
    if not pf.empty:
        merged = merged.merge(pf, on="trait", how="left")

    merged.insert(0, "purpose", purpose)
    # Stable trait ordering — task first, then content/organization/expression, then holistic
    trait_order = [
        "task_1",
        "content_1", "content_2", "content_3",
        "organization_1", "organization_2",
        "expression_1", "expression_2",
        "holistic",
    ]
    merged["_order"] = merged["trait"].map(
        {t: i for i, t in enumerate(trait_order)}
    ).fillna(len(trait_order)).astype(int)
    merged = merged.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return merged


def run(purpose: str) -> Path:
    df = build(purpose)
    out = OOF_DIR / f"robustness_table__{purpose}.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (rows=%d, cols=%d)", out, len(df), len(df.columns))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--purpose", choices=("설명", "설득", "both"), default="both",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    purposes = ["설명", "설득"] if args.purpose == "both" else [args.purpose]
    for p in purposes:
        run(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
