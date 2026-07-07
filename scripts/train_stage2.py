"""
Stage 2.2 CLI entry point.

Runs two CV schemes in sequence:

    1. Grade-stratified 5-fold (PRIMARY reporting)
    2. Leave-one-prompt-out     (ROBUSTNESS table)

For each scheme, trains 8 analytic + holistic XGBoost models.

Usage
-----
    # Default: primary embedding's feature matrix
    python -m scripts.train_stage2

    # Specific matrix
    python -m scripts.train_stage2 \
        --feature-matrix data/processed/feature_matrix__primary.parquet
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd

from configs.paths import ACTIVE_EMBEDDING, PROCESSED_DIR, REPORTS_DIR
from src.models.cv import GradeStratifiedKFold, LeaveOnePromptOut
from src.models.train import train_all_traits


def _read_feature_matrix(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        try:
            return pd.read_parquet(path)
        except ImportError:
            raise RuntimeError(
                f"{path} is parquet but no parquet engine is installed. "
                "Install pyarrow or fastparquet."
            )
    return pd.read_csv(path)


def _default_feature_matrix_path() -> Path:
    # Prefer parquet for the active embedding, then any CSV sibling
    for suffix in (f"__{ACTIVE_EMBEDDING}", "__no_sbert"):
        for ext in (".parquet", ".csv"):
            p = PROCESSED_DIR / f"feature_matrix{suffix}{ext}"
            if p.exists():
                return p
    raise FileNotFoundError(
        f"No feature matrix found under {PROCESSED_DIR}. "
        "Run `python -m src.features.build` first."
    )


def _extract_purpose_from_path(path: Path) -> str:
    """Extract purpose key from feature matrix filename.

    e.g. feature_matrix__설명__no_sbert.csv -> 설명
         feature_matrix__설득__primary.parquet -> 설득
    """
    stem = path.stem  # feature_matrix__설명__no_sbert
    parts = stem.split("__")
    if len(parts) >= 2:
        return parts[1]  # 설명 or 설득
    return "unknown"


def _extract_embedding_from_path(path: Path) -> str:
    """Extract embedding key from feature matrix filename.

    e.g. feature_matrix__설명__no_sbert.csv -> no_sbert
         feature_matrix__설득__primary.parquet -> primary
         feature_matrix__설명__robust_1.parquet -> robust_1
    """
    stem = path.stem
    parts = stem.split("__")
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feature-matrix",
        type=Path,
        default=None,
        help="Path to feature matrix parquet or CSV. "
              "Auto-detect if omitted.",
    )
    parser.add_argument(
        "--skip-cross-prompt",
        action="store_true",
        help="Run only the primary grade-stratified CV.",
    )
    parser.add_argument(
        "--objective",
        choices=("regression", "ordinal"),
        default="regression",
        help="Training objective. 'regression' (default) = XGBRegressor "
              "w/ reg:squarederror. 'ordinal' = XGBClassifier w/ multi:softprob "
              "+ expected-value prediction, for v2.3 §5.3 body robustness.",
    )
    args = parser.parse_args()

    fm_path = args.feature_matrix or _default_feature_matrix_path()
    logging.info("Reading feature matrix: %s", fm_path)
    df = _read_feature_matrix(fm_path)
    logging.info("Matrix shape: %s", df.shape)

    # Extract purpose and embedding key from filename for output naming
    purpose = _extract_purpose_from_path(fm_path)
    embedding = _extract_embedding_from_path(fm_path)
    logging.info("Detected purpose: %s | embedding: %s | objective: %s",
                 purpose, embedding, args.objective)

    # Ordinal variant gets an extra filename suffix so it coexists with the
    # regression primary outputs of the same (purpose, embedding).
    obj_suffix = "" if args.objective == "regression" else f"__{args.objective}"

    # Purpose × embedding × objective combined into one output tag.
    tag = f"{purpose}__{embedding}{obj_suffix}"

    report_dir = REPORTS_DIR / "stage2_models"
    report_dir.mkdir(parents=True, exist_ok=True)

    # train_all_traits writes oof_predictions__{cv_label}.csv to report_dir
    # without any key. We rename after each run so that consecutive
    # (purpose, embedding) runs don't clobber each other's oof vectors.
    def _stash_oof(cv_label: str) -> None:
        src = report_dir / f"oof_predictions__{cv_label}.csv"
        if src.exists():
            dst = report_dir / f"oof_predictions__{tag}__{cv_label}.csv"
            src.replace(dst)

    # --- Primary: grade-stratified ----------------------------------------
    logging.info("\n=== PRIMARY: Grade-stratified 5-fold ===")
    splitter = GradeStratifiedKFold(n_splits=5, random_state=42)
    fold_df, agg_df = train_all_traits(
        df, splitter, cv_label="grade_stratified",
        objective=args.objective,
    )
    fold_df.to_csv(report_dir / f"cv_grade_stratified__{tag}__folds.csv", index=False)
    agg_df.to_csv(report_dir / f"cv_grade_stratified__{tag}__agg.csv", index=False)
    _stash_oof("grade_stratified")
    print(f"\nGrade-stratified aggregate results ({tag}):")
    print(agg_df.to_string(index=False))

    # --- Robustness: cross-prompt (LOPO) ----------------------------------
    if not args.skip_cross_prompt:
        logging.info("\n=== ROBUSTNESS: Cross-prompt (LOPO) ===")
        splitter = LeaveOnePromptOut(prompt_col="prompt_id")
        fold_df2, agg_df2 = train_all_traits(
            df, splitter, cv_label="cross_prompt",
            objective=args.objective,
        )
        fold_df2.to_csv(report_dir / f"cv_cross_prompt__{tag}__folds.csv", index=False)
        agg_df2.to_csv(report_dir / f"cv_cross_prompt__{tag}__agg.csv", index=False)
        _stash_oof("cross_prompt")
        print(f"\nCross-prompt aggregate results ({tag}):")
        print(agg_df2.to_string(index=False))


if __name__ == "__main__":
    main()
