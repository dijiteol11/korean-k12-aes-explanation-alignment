"""
Evaluation metrics for analytic trait prediction.

The central metric is Quadratic Weighted Kappa (QWK), the de-facto
standard for AES (Shermis & Burstein, 2013). Since our XGBoost outputs
continuous regression values, we report QWK on scores rounded to the
nearest integer in [1, 5], and also provide continuous correlation
coefficients for transparency.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import cohen_kappa_score, mean_absolute_error


def clip_round(y: np.ndarray, lo: int = 1, hi: int = 5) -> np.ndarray:
    """Round to nearest integer, clip to [lo, hi]."""
    return np.clip(np.rint(np.asarray(y, dtype=float)), lo, hi).astype(int)


def quadratic_weighted_kappa(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> float:
    """QWK on rounded predictions. Labels fixed to guard against
    degenerate folds where some scores are absent."""
    yt = clip_round(y_true, labels[0], labels[-1])
    yp = clip_round(y_pred, labels[0], labels[-1])
    try:
        return float(
            cohen_kappa_score(yt, yp, weights="quadratic", labels=list(labels))
        )
    except ValueError:
        return float("nan")


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    # Guard for empty folds
    if len(yt) == 0:
        return {"n": 0, "qwk": float("nan"), "mae": float("nan"),
                "rmse": float("nan"), "pearson_r": float("nan")}
    mae = float(mean_absolute_error(yt, yp))
    rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
    # Correlation — undefined if a vector is constant
    if np.std(yt) == 0 or np.std(yp) == 0:
        pearson = float("nan")
    else:
        pearson = float(np.corrcoef(yt, yp)[0, 1])
    return {
        "n": int(len(yt)),
        "qwk": quadratic_weighted_kappa(yt, yp),
        "mae": mae,
        "rmse": rmse,
        "pearson_r": pearson,
    }
