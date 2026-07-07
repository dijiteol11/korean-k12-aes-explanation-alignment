"""
TreeSHAP attribution for Stage 2.2 XGBoost regressors, aggregated to the
8 pre-registered feature families (plan v2.3 §4.2.3).

Stage 3 milestones:
    A (this module, single-cell POC) — load one (purpose, embedding, trait,
      cv, fold) model + its test essays, compute local SHAP, aggregate to
      families, verify TreeSHAP additivity (base + Σ feature_shap ≈ y_pred).
    C — sweep both purposes × primary × both CV schemes.
    D — add robust_1; compute cross-embedding Jaccard.

Background policy (researcher-approved 2026-04-22): ``interventional``
with a per-fold training-set subsample of size ``configs.shap.BACKGROUND_N``.
See ``configs/shap.py``.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import (
    FEATURE_FAMILIES,
    PROCESSED_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    feature_family,
)
from configs.shap import (
    ADDITIVITY_TOL,
    BACKGROUND_N,
    BACKGROUND_SEED,
    FEATURE_PERTURBATION,
    REPORT_SUBDIR,
)
from src.models.train import _feature_columns

log = logging.getLogger(__name__)

MODELS_DIR: Path = PROJECT_ROOT / "models" / "xgb"
OOF_DIR: Path = REPORTS_DIR / "stage2_models"
SHAP_REPORT_DIR: Path = REPORTS_DIR / REPORT_SUBDIR


@dataclass(frozen=True)
class CellSpec:
    """A single (purpose, embedding, trait, cv, fold) slice."""

    purpose: str
    embedding: str
    trait: str
    cv_label: str
    fold_label: str

    @property
    def model_path(self) -> Path:
        return (
            MODELS_DIR
            / f"{self.purpose}__{self.embedding}"
            / f"{self.trait}__{self.cv_label}__{self.fold_label}.json"
        )

    @property
    def matrix_path(self) -> Path:
        stem = f"feature_matrix__{self.purpose}__{self.embedding}"
        p = PROCESSED_DIR / f"{stem}.parquet"
        return p if p.exists() else PROCESSED_DIR / f"{stem}.csv"

    @property
    def oof_path(self) -> Path:
        return (
            OOF_DIR
            / f"oof_predictions__{self.purpose}__{self.embedding}__{self.cv_label}.csv"
        )


def _load_matrix(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def _load_xgb_model(path: Path):
    import xgboost as xgb

    model = xgb.XGBRegressor()
    model.load_model(str(path))
    return model


def _fold_test_essay_ids(oof: pd.DataFrame, trait: str, fold_label: str) -> np.ndarray:
    mask = (oof["trait"] == trait) & (oof["fold"] == fold_label)
    return oof.loc[mask, "essay_id"].to_numpy()


def _fold_train_background(
    df: pd.DataFrame,
    feat_cols: list[str],
    test_essay_ids: np.ndarray,
    n: int,
    seed: int,
) -> np.ndarray:
    """Sample ``n`` rows from the training complement of ``test_essay_ids``.

    The interventional SHAP explainer integrates out features using the
    background distribution — here, a per-fold subsample of essays that
    this model was trained on (all rows not in its test fold). Seeding
    the RNG keeps Stage 3 reproducible across reruns.
    """
    all_ids = df["essay_id"].to_numpy()
    train_mask = ~pd.Index(all_ids).isin(test_essay_ids)
    train_df = df.loc[train_mask, feat_cols]
    take = min(n, len(train_df))
    return train_df.sample(n=take, random_state=seed).to_numpy(dtype=np.float32)


def compute_cell_shap(spec: CellSpec) -> dict:
    """Compute local SHAP for one cell, aggregate to families, verify additivity.

    Returns a dict with:
        ``long_df``       — DataFrame(essay_id, family, shap_sum) long form
        ``family_matrix`` — DataFrame(essay_id, <one col per family>)
        ``base_value``    — scalar TreeSHAP base value
        ``y_pred``        — array aligned with ``family_matrix`` rows
        ``additivity_max_abs_error`` — float
        ``feat_cols``     — list[str] feature columns in model order
    """
    import shap

    log.info("Loading %s", spec.model_path)
    model = _load_xgb_model(spec.model_path)

    df = _load_matrix(spec.matrix_path)
    feat_cols = _feature_columns(df)

    oof = pd.read_csv(spec.oof_path)
    essay_ids = _fold_test_essay_ids(oof, spec.trait, spec.fold_label)
    if essay_ids.size == 0:
        raise RuntimeError(
            f"No OOF rows for {spec.trait}/{spec.fold_label} in {spec.oof_path.name}"
        )

    slice_df = df.set_index("essay_id").loc[essay_ids]
    X = slice_df[feat_cols].to_numpy(dtype=np.float32)

    background = _fold_train_background(
        df, feat_cols, essay_ids, n=BACKGROUND_N, seed=BACKGROUND_SEED,
    )
    t0 = time.perf_counter()
    explainer = shap.TreeExplainer(
        model, data=background, feature_perturbation=FEATURE_PERTURBATION,
    )
    explanation = explainer(X)
    elapsed = time.perf_counter() - t0
    shap_values = np.asarray(explanation.values)           # (n, n_features)
    base_values = np.asarray(explanation.base_values)      # (n,) or scalar
    if np.ndim(base_values) == 0:
        base_scalar = float(base_values)
    else:
        uniq = np.unique(np.round(base_values, 6))
        assert uniq.size == 1, f"Non-constant base values: {uniq}"
        base_scalar = float(uniq.item())

    y_pred = model.predict(X)
    additivity_error = np.abs(
        base_scalar + shap_values.sum(axis=1) - y_pred
    )
    log.info(
        "SHAP %s/%s: n=%d bg=%d elapsed=%.2fs max_add_err=%.2e",
        spec.trait, spec.fold_label, X.shape[0], background.shape[0],
        elapsed, float(additivity_error.max()),
    )

    fam_for_col = np.array([feature_family(c) for c in feat_cols])
    fam_matrix = pd.DataFrame(
        {
            fam: shap_values[:, fam_for_col == fam].sum(axis=1)
            for fam in FEATURE_FAMILIES
        },
        index=essay_ids,
    )
    fam_matrix.index.name = "essay_id"

    long_df = fam_matrix.reset_index().melt(
        id_vars="essay_id", var_name="family", value_name="shap_sum"
    )
    long_df["purpose"] = spec.purpose
    long_df["embedding"] = spec.embedding
    long_df["trait"] = spec.trait
    long_df["cv_label"] = spec.cv_label
    long_df["fold_label"] = spec.fold_label

    unknown_cols = [c for c, f in zip(feat_cols, fam_for_col) if f == "unknown"]
    if unknown_cols:
        raise RuntimeError(
            f"feature_family() returned 'unknown' for {len(unknown_cols)} cols: "
            f"{unknown_cols[:5]}"
        )

    return {
        "long_df": long_df,
        "family_matrix": fam_matrix,
        "base_value": base_scalar,
        "y_pred": y_pred,
        "additivity_max_abs_error": float(additivity_error.max()),
        "shap_elapsed_sec": elapsed,
        "feat_cols": feat_cols,
    }


def _cli_poc(spec: CellSpec, *, tol: float = ADDITIVITY_TOL) -> None:
    out = compute_cell_shap(spec)
    n = len(out["family_matrix"])
    print(f"\n== Stage 3 POC — {spec.purpose}/{spec.embedding}/{spec.trait}"
          f"/{spec.cv_label}/{spec.fold_label} ==")
    print(f"  n_essays={n}  n_features={len(out['feat_cols'])}")
    print(f"  feature_perturbation={FEATURE_PERTURBATION}  bg_n={BACKGROUND_N}  "
          f"elapsed={out['shap_elapsed_sec']:.2f}s")
    print(f"  base_value={out['base_value']:.6f}")
    print(f"  max |base + Σ shap - y_pred| = {out['additivity_max_abs_error']:.2e}")
    assert out["additivity_max_abs_error"] < tol, (
        f"TreeSHAP additivity failed: {out['additivity_max_abs_error']} >= {tol}"
    )
    print("  ✓ additivity holds (< {:.0e})".format(tol))

    fam = out["family_matrix"]
    mean_abs = fam.abs().mean().sort_values(ascending=False)
    print("\n  Mean |family SHAP| (this fold):")
    for k, v in mean_abs.items():
        nonzero = int((fam[k] != 0).sum())
        print(f"    {k:14s}  {v:.5f}   (nonzero in {nonzero}/{n} essays)")

    SHAP_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SHAP_REPORT_DIR / (
        f"POC__{spec.purpose}__{spec.embedding}__{spec.trait}"
        f"__{spec.cv_label}__{spec.fold_label}.parquet"
    )
    out["long_df"].to_parquet(out_path, index=False)
    print(f"\n  wrote {out_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Milestone A: one cell
    spec = CellSpec(
        purpose="설명",
        embedding="primary",
        trait="task_1",
        cv_label="grade_stratified",
        fold_label="grade_fold_1",
    )
    _cli_poc(spec)
