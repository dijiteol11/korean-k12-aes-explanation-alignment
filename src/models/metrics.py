from __future__ import annotations
import numpy as np

def quadratic_weighted_kappa(y_true, y_pred, min_rating: int = 1, max_rating: int = 5) -> float:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    n = max_rating - min_rating + 1
    obs = np.zeros((n, n), dtype=float)
    for a, b in zip(y_true, y_pred):
        if min_rating <= a <= max_rating and min_rating <= b <= max_rating:
            obs[a - min_rating, b - min_rating] += 1
    expected = np.outer(obs.sum(axis=1), obs.sum(axis=0)) / max(obs.sum(), 1.0)
    weights = np.fromfunction(lambda i, j: ((i - j) ** 2) / ((n - 1) ** 2), (n, n))
    denom = (weights * expected).sum()
    return 1.0 if denom == 0 else 1.0 - (weights * obs).sum() / denom
