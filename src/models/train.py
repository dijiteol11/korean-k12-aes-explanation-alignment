"""
Per-trait XGBoost regressor training with configurable CV.

For each of the 8 analytic traits (+ holistic), trains one XGBoost
regressor per CV fold, collects predictions, and persists:

    1. Per-fold metrics (QWK, MAE, RMSE, Pearson r)
    2. Aggregated metrics (mean ± SD across folds)
    3. Out-of-fold prediction vector (for SHAP stage 3 and triangulation)
    4. Trained model artifacts (one per fold, for local SHAP explainers)

Hyperparameters are fixed defaults (conservative, widely defensible).
Trait-specific Optuna tuning is a separate follow-up module
(src/models/hyperparams.py) and is not enabled by default.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import PROJECT_ROOT, REPORTS_DIR, TRAITS
from src.models.cv import GradeStratifiedKFold, LeaveOnePromptOut
from src.models.metrics import regression_metrics

log = logging.getLogger(__name__)


# --- Default hyperparameters ------------------------------------------------
DEFAULT_XGB_PARAMS: dict = {
    "objective": "reg:squarederror",
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "random_state": 42,
    "tree_method": "hist",
    "n_jobs": -1,
}

# Ordinal classifier variant (v2.3 §5.3 body robustness table).
# Treats the 1..5 score as a 5-class target and predicts the expected
# class value — a softmax Frank-Hall-like approach that respects the
# discrete/class structure of the rubric.
DEFAULT_XGB_ORDINAL_PARAMS: dict = {
    "objective": "multi:softprob",
    "num_class": 5,
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "random_state": 42,
    "tree_method": "hist",
    "n_jobs": -1,
}

MODELS_DIR = PROJECT_ROOT / "models" / "xgb"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# --- Backend loader ---------------------------------------------------------
def _load_xgb():
    try:
        import xgboost as xgb  # type: ignore
        return xgb
    except ImportError as e:
        raise RuntimeError(
            "xgboost is required for Stage 2.2. Install with: pip install xgboost"
        ) from e


# --- Result container -------------------------------------------------------
@dataclass
class TraitResult:
    trait: str
    cv_scheme: str
    fold_metrics: list[dict] = field(default_factory=list)
    oof_predictions: pd.DataFrame | None = None

    @property
    def agg_metrics(self) -> dict[str, float]:
        if not self.fold_metrics:
            return {}
        keys = ("qwk", "mae", "rmse", "pearson_r")
        out: dict[str, float] = {"n_folds": float(len(self.fold_metrics))}
        for k in keys:
            vals = np.array([m[k] for m in self.fold_metrics], dtype=float)
            out[f"{k}_mean"] = float(np.nanmean(vals))
            out[f"{k}_std"] = float(np.nanstd(vals, ddof=1)) if len(vals) > 1 else 0.0
        return out


# --- Core training loop -----------------------------------------------------
def _feature_columns(df: pd.DataFrame) -> list[str]:
    exclude = {
        "essay_id", "grade", "subject", "level", "purpose",
        "region", "gender", "prompt_id", "topic",
    }
    return [
        c for c in df.columns
        if not c.startswith("target__") and c not in exclude
    ]


def train_trait(
    df: pd.DataFrame,
    trait: str,
    splitter,
    params: dict | None = None,
    *,
    save_models: bool = True,
    cv_label: str = "grade_stratified",
    objective: str = "regression",
) -> TraitResult:
    """Train one XGBoost model per fold for a single trait.

    Parameters
    ----------
    objective : {"regression", "ordinal"}
        "regression" — XGBRegressor w/ reg:squarederror (primary analysis).
        "ordinal"    — XGBClassifier w/ multi:softprob on 5 classes;
                       predictions are expected values over the class
                       distribution, respecting the 1-5 rubric's discrete
                       order. Robustness variant for v2.3 §5.3.
    """
    if objective not in ("regression", "ordinal"):
        raise ValueError(f"objective must be 'regression' or 'ordinal', got {objective!r}")

    xgb = _load_xgb()
    default = DEFAULT_XGB_ORDINAL_PARAMS if objective == "ordinal" else DEFAULT_XGB_PARAMS
    params = {**default, **(params or {})}
    target_col = f"target__{trait}"
    if target_col not in df.columns:
        raise KeyError(f"{target_col} missing from feature matrix")

    feat_cols = _feature_columns(df)
    X_all = df[feat_cols].to_numpy()
    y_all = df[target_col].to_numpy(dtype=float)

    result = TraitResult(trait=trait, cv_scheme=cv_label)
    oof_rows: list[dict] = []

    class_values = np.arange(1, 6, dtype=float)  # [1,2,3,4,5]

    for tr_idx, te_idx, fold_label in splitter.split(df):
        X_tr, y_tr = X_all[tr_idx], y_all[tr_idx]
        X_te, y_te = X_all[te_idx], y_all[te_idx]

        # Cross-prompt test folds can be very small; guard against
        # fit failures on degenerate target variance
        if len(tr_idx) < 10 or np.std(y_tr) == 0:
            log.warning(
                "Skipping fold %s for %s (n_train=%d, y_std=%.3f)",
                fold_label, trait, len(tr_idx), np.std(y_tr),
            )
            continue

        if objective == "ordinal":
            # Rubric scores are held as floats but are integers 1..5 by
            # construction. XGBClassifier wants integer class labels in
            # [0, num_class). We remap 1..5 → 0..4 for training and
            # then convert expected-value prediction back to the 1..5 scale.
            y_tr_int = np.rint(y_tr).astype(int) - 1
            if y_tr_int.min() < 0 or y_tr_int.max() > 4:
                raise ValueError(
                    f"{trait}/{fold_label}: ordinal target outside 1..5 "
                    f"(range {y_tr.min()}..{y_tr.max()})"
                )
            # Ensure training set sees all 5 classes. If not, softprob
            # silently drops classes, breaking expected-value prediction.
            uniq = np.unique(y_tr_int)
            if len(uniq) < 2:
                log.warning(
                    "Skipping ordinal fold %s for %s (only %d unique class)",
                    fold_label, trait, len(uniq),
                )
                continue
            model = xgb.XGBClassifier(**params)
            model.fit(X_tr, y_tr_int, verbose=False)
            proba = model.predict_proba(X_te)  # shape (n_test, n_classes_seen)
            # Expand proba to the full 5-class space so expected value is
            # always over {1..5} even if a class was absent in training.
            full_proba = np.zeros((proba.shape[0], 5), dtype=float)
            for j, cls in enumerate(model.classes_):
                full_proba[:, int(cls)] = proba[:, j]
            y_pred = full_proba @ class_values
        else:
            model = xgb.XGBRegressor(**params)
            model.fit(X_tr, y_tr, verbose=False)
            y_pred = model.predict(X_te)

        metrics = regression_metrics(y_te, y_pred)
        metrics["fold"] = fold_label
        metrics["trait"] = trait
        metrics["n_train"] = int(len(tr_idx))
        result.fold_metrics.append(metrics)

        essay_ids = df.iloc[te_idx]["essay_id"].to_numpy()
        for eid, yt, yp in zip(essay_ids, y_te, y_pred):
            oof_rows.append({
                "essay_id": int(eid),
                "trait": trait,
                "fold": fold_label,
                "y_true": float(yt),
                "y_pred": float(yp),
            })

        if save_models:
            model_path = (
                MODELS_DIR / f"{trait}__{cv_label}__{fold_label}.json"
            )
            model.save_model(model_path)

    result.oof_predictions = pd.DataFrame(oof_rows) if oof_rows else None
    return result


def train_all_traits(
    df: pd.DataFrame,
    splitter,
    cv_label: str,
    traits: tuple[str, ...] = TRAITS,
    *,
    include_holistic: bool = True,
    params: dict | None = None,
    objective: str = "regression",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run training for every trait; return (fold_metrics_df, agg_metrics_df)."""
    fold_rows: list[dict] = []
    agg_rows: list[dict] = []
    all_oof: list[pd.DataFrame] = []

    targets: tuple[str, ...] = traits + (("holistic",) if include_holistic else ())

    for trait in targets:
        log.info("── Trait: %s ── [%s, %s]", trait, cv_label, objective)
        res = train_trait(
            df, trait, splitter, params,
            cv_label=cv_label, objective=objective,
        )
        fold_rows.extend(res.fold_metrics)
        agg = {"trait": trait, "cv_scheme": cv_label, **res.agg_metrics}
        agg_rows.append(agg)
        if res.oof_predictions is not None:
            all_oof.append(res.oof_predictions)

    # Persist out-of-fold predictions for downstream SHAP / triangulation
    oof_dir = REPORTS_DIR / "stage2_models"
    oof_dir.mkdir(parents=True, exist_ok=True)
    if all_oof:
        pd.concat(all_oof, ignore_index=True).to_csv(
            oof_dir / f"oof_predictions__{cv_label}.csv", index=False
        )

    return pd.DataFrame(fold_rows), pd.DataFrame(agg_rows)
