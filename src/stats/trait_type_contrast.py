from __future__ import annotations
import numpy as np
from scipy.stats import wilcoxon

def rank_biserial_from_wilcoxon(x, y, *, alternative="greater", zero_method="wilcox"):
    diff = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    stat, p = wilcoxon(diff, alternative=alternative, zero_method=zero_method)
    nonzero = diff[diff != 0]
    if len(nonzero) == 0:
        return float(stat), float(p), 0.0
    return float(stat), float(p), float(1.0 - (2.0 * float(stat) / (len(nonzero) * (len(nonzero) + 1) / 2)))
