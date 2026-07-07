"""
Stage 4.4 — Drift management (plan v2.3 §6.4).

Codebook drift during manual 4-level coding is controlled by:

    * 10–15% double-coded sample per 1,000 coding units.
    * Drift check after every 1,000 units: compare earlier vs. later
      blocks of the same coder via κ; drop below preregistered threshold
      → coder re-training session + re-coding previous block.
    * Adjudication log (JSONL) for every within-coder κ dispute.

**STUB** — full implementation pending §4.4 coding start. Stubbed so
downstream modules can import ``drift.check_intracoder_kappa`` without
NotImplementedError during test collection.
"""
from __future__ import annotations

import numpy as np


DOUBLE_CODE_FRACTION: float = 0.125    # 12.5% — midpoint of 10-15%
DRIFT_BLOCK_SIZE: int = 1000           # §6.4 units
KAPPA_DRIFT_THRESHOLD: float = 0.75    # UNRATIFIED — confirm with research team


def check_intracoder_kappa(
    block_a: np.ndarray,
    block_b: np.ndarray,
) -> float:
    """Cohen's κ between two 1-D arrays of coded values from the same coder.

    Returns NaN if either input is empty or constant; the caller must
    handle degenerate cases (usually: treat as "no evidence of drift").
    """
    from sklearn.metrics import cohen_kappa_score

    a = np.asarray(block_a)
    b = np.asarray(block_b)
    if a.size == 0 or b.size == 0 or a.size != b.size:
        return float("nan")
    try:
        return float(cohen_kappa_score(a, b))
    except ValueError:
        return float("nan")
