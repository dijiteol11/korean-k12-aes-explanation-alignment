"""
Cross-embedding Jaccard Top-K diagnostic (plan v2.3 §4.2.3).

Loads the long-form SHAP parquets for two embeddings (default
``primary`` vs ``robust_1``) for a single purpose, combines across CV
schemes, and emits a per-trait Jaccard table:

    reports/stage3_shap/jaccard__{purpose}__{emb_a}_vs_{emb_b}.csv

A trait is flagged ``unstable`` when Jaccard < ``configs.shap.JACCARD_INSTABILITY``
(currently 0.5, UNRATIFIED — see configs/shap.py).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.shap_analysis.aggregate import jaccard_top_k
from src.shap_analysis.treeshap import SHAP_REPORT_DIR

log = logging.getLogger(__name__)


def _load_combined(purpose: str, embedding: str) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for cv in ("grade_stratified", "cross_prompt"):
        p = SHAP_REPORT_DIR / f"local_shap__{purpose}__{embedding}__{cv}.parquet"
        if not p.exists():
            raise FileNotFoundError(p)
        parts.append(pd.read_parquet(p))
    return pd.concat(parts, ignore_index=True)


def run(purpose: str, emb_a: str, emb_b: str) -> Path:
    log.info("Loading %s × %s and %s", purpose, emb_a, emb_b)
    long_a = _load_combined(purpose, emb_a)
    long_b = _load_combined(purpose, emb_b)
    jac = jaccard_top_k(long_a, long_b)
    jac.insert(0, "purpose", purpose)
    jac.insert(1, "embedding_a", emb_a)
    jac.insert(2, "embedding_b", emb_b)
    out = SHAP_REPORT_DIR / f"jaccard__{purpose}__{emb_a}_vs_{emb_b}.csv"
    jac.to_csv(out, index=False)
    log.info("Wrote %s", out)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", required=True, choices=("설명", "설득"))
    parser.add_argument("--emb-a", default="primary")
    parser.add_argument("--emb-b", default="robust_1")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    run(args.purpose, args.emb_a, args.emb_b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
