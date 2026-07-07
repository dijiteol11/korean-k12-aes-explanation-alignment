"""
Stage 3 TreeSHAP / stability constants (plan v2.3 §4.2.3).

Centralised so the values remain discoverable and reviewable. Items with
an 'UNRATIFIED' comment are currently drawn from the STUB versions of
``decision_table_preregistered.md`` / ``family_rubric_mapping_preregistered.md``
and MUST be re-bound once those files are committed at v1.0 (see
``CLAUDE.md`` pre-registration policy).
"""
from __future__ import annotations

# --- TreeSHAP numerical tolerances -----------------------------------------
# Max allowed |base + Σ family_shap - y_pred|. Tree SHAP is exact up to
# float32 rounding on XGBoost JSON models, so 1e-4 is generous.
ADDITIVITY_TOL: float = 1e-4

# --- Explainer configuration (plan v2.3 §4.2.3, researcher-approved) -------
# "interventional" with a per-fold training-set background subsample. This
# is more correlation-robust than tree_path_dependent but ~2-5× slower with
# small backgrounds. n=100 is the shap library's standard recommendation
# and keeps per-fold SHAP time under a minute on this feature count.
FEATURE_PERTURBATION: str = "interventional"
BACKGROUND_N: int = 100
BACKGROUND_SEED: int = 42

# --- Stage 3 entry pre-flight (researcher-approved 2026-04-22) -------------
# Per-trait LOPO QWK below this threshold triggers a "low-signal" flag.
# The flag contributes ONE signal toward Stage 5 Indeterminate classification
# but does not force it on its own (see decision_table §3.3 "2 or more"
# combining rule).
QWK_PREFLIGHT_MIN: float = 0.15

# --- Stability thresholds (UNRATIFIED — stub values) -----------------------
# Drawn from ``decision_table_preregistered.md`` §3.1 which is currently
# marked ``Status: STUB``. Must be re-confirmed at preregistration v1.0.
KENDALL_TAU_INSTABILITY: float = 0.5       # UNRATIFIED
JACCARD_INSTABILITY: float = 0.5           # UNRATIFIED
JACCARD_TOP_K: int = 3                     # UNRATIFIED — family_rubric_mapping §4

# --- Reporting --------------------------------------------------------------
# Where Stage 3 writes parquet + CSV outputs.
REPORT_SUBDIR: str = "stage3_shap"
