"""
Stage 3 entry point — sweep, stability, global aggregation, QWK pre-flight.

Typical usage::

    python -m src.shap_analysis.cli --purpose 설명 --embedding primary

Runs the full pipeline for both ``grade_stratified`` and ``cross_prompt`` CVs,
writes:

    reports/stage3_shap/local_shap__{purpose}__{embedding}__{cv}.parquet
    reports/stage3_shap/global_shap__{purpose}__{embedding}.csv
    reports/stage3_shap/stability__{purpose}__{embedding}__{cv}.csv
    reports/stage3_shap/preflight_qwk__{purpose}__{embedding}.csv
"""
from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from src.shap_analysis.aggregate import global_family_shap, qwk_preflight
from src.shap_analysis.stability import kendall_tau_by_trait
from src.shap_analysis.sweep import write_sweep
from src.shap_analysis.treeshap import SHAP_REPORT_DIR

log = logging.getLogger(__name__)

CV_SCHEMES = ("grade_stratified", "cross_prompt")


def run_purpose_embedding(purpose: str, embedding: str) -> None:
    SHAP_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    per_cv_local: dict[str, pd.DataFrame] = {}

    for cv in CV_SCHEMES:
        log.info("=== sweep %s / %s / %s ===", purpose, embedding, cv)
        parquet_path = write_sweep(purpose, embedding, cv)
        long_df = pd.read_parquet(parquet_path)
        per_cv_local[cv] = long_df

        stab = kendall_tau_by_trait(long_df)
        stab.insert(0, "purpose", purpose)
        stab.insert(1, "embedding", embedding)
        stab.insert(2, "cv_label", cv)
        stab_path = SHAP_REPORT_DIR / f"stability__{purpose}__{embedding}__{cv}.csv"
        stab.to_csv(stab_path, index=False)
        log.info("Wrote %s", stab_path)

    combined = pd.concat(
        [df.assign(cv_label=cv) for cv, df in per_cv_local.items()],
        ignore_index=True,
    )
    global_df = global_family_shap(combined)
    global_df.insert(0, "purpose", purpose)
    global_df.insert(1, "embedding", embedding)
    gpath = SHAP_REPORT_DIR / f"global_shap__{purpose}__{embedding}.csv"
    global_df.to_csv(gpath, index=False)
    log.info("Wrote %s", gpath)

    pf = qwk_preflight(purpose, embedding)
    pfp = SHAP_REPORT_DIR / f"preflight_qwk__{purpose}__{embedding}.csv"
    pf.to_csv(pfp, index=False)
    log.info("Wrote %s", pfp)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", required=True, choices=("설명", "설득"))
    parser.add_argument("--embedding", required=True,
                        choices=("primary", "robust_1", "robust_2"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    run_purpose_embedding(args.purpose, args.embedding)
    return 0


if __name__ == "__main__":
    sys.exit(main())
