"""
Stage 4 main-vs-sensitivity agreement metrics (plan v2.3 §4.5 + SOTA review.md 2026-04-24).

Eight metrics reported per (trait × sensitivity slice) when comparing Sonnet
main-track output against Opus sensitivity-track output on the same 1,000
stratified essays. Correlation alone is insufficient in rationale-dependent
research (Wang et al., 2024 EMNLP Findings; SOTA review.md §"권고 설계").

    qwk                     — quadratic weighted κ on integer scores
    weighted_kappa_linear   — linear weighted κ on integer scores
    exact_agreement_rate    — p(main.score == sensitivity.score)
    adjacent_agreement_rate — p(|main.score - sensitivity.score| ≤ 1)
    mean_severity_shift     — mean(sensitivity.score - main.score)
    rationale_coding_wk     — weighted κ on 4-level rationale codings (Stage 4.3)
    mid_category_inflation  — main p(중) / sensitivity p(중)
    na_f1                   — precision/recall/F1 on NA (score=null) decisions

Each metric's per-trait pass threshold lives in ``configs.stage4``.
The pass/fail classification (ROBUST / PARTIALLY_ROBUST / NOT_ROBUST) is
applied per trait and aggregated per (purpose × CV slice) by the
downstream Stage 5 alignment matrix.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from configs.stage4 import (
    SENSITIVITY_PASS_EXACT_AGREEMENT_MIN,
    SENSITIVITY_PASS_MID_INFLATION_MAX,
    SENSITIVITY_PASS_NA_F1_MIN,
    SENSITIVITY_PASS_RATIONALE_WK_MIN,
    SENSITIVITY_PASS_SCORE_QWK_MIN,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgreementResult:
    trait: str
    n: int                                  # non-NA paired essays
    qwk: float
    weighted_kappa_linear: float
    exact_agreement_rate: float
    adjacent_agreement_rate: float
    mean_severity_shift: float
    rationale_coding_wk: float | None       # None until Stage 4.3 coding complete
    mid_category_inflation: float | None    # None until Stage 4.3 coding complete
    na_f1: float
    na_precision: float
    na_recall: float
    na_rate_main: float
    na_rate_sensitivity: float

    @property
    def robust_status(self) -> str:
        """ROBUST / PARTIALLY_ROBUST / NOT_ROBUST per §SENSITIVITY_PASS_*."""
        passed = 0
        total = 5
        if not np.isnan(self.qwk) and self.qwk >= SENSITIVITY_PASS_SCORE_QWK_MIN:
            passed += 1
        if self.exact_agreement_rate >= SENSITIVITY_PASS_EXACT_AGREEMENT_MIN:
            passed += 1
        if (
            self.rationale_coding_wk is not None
            and self.rationale_coding_wk >= SENSITIVITY_PASS_RATIONALE_WK_MIN
        ):
            passed += 1
        if (
            self.mid_category_inflation is not None
            and self.mid_category_inflation <= SENSITIVITY_PASS_MID_INFLATION_MAX
        ):
            passed += 1
        if self.na_f1 >= SENSITIVITY_PASS_NA_F1_MIN:
            passed += 1
        if passed == total:
            return "ROBUST"
        if passed >= total - 2:
            return "PARTIALLY_ROBUST"
        return "NOT_ROBUST"


def _qwk(main: np.ndarray, sens: np.ndarray, min_rating: int = 1, max_rating: int = 5) -> float:
    """Quadratic weighted κ over integer ratings."""
    from src.models.metrics import regression_metrics  # already used for Stage 2.2
    m = regression_metrics(main, sens)
    return float(m.get("qwk", float("nan")))


def _linear_kappa(main: np.ndarray, sens: np.ndarray) -> float:
    from sklearn.metrics import cohen_kappa_score
    try:
        return float(cohen_kappa_score(main, sens, weights="linear"))
    except ValueError:
        return float("nan")


def _na_f1(
    main_na: np.ndarray, sens_na: np.ndarray
) -> tuple[float, float, float]:
    """Treat Opus(sensitivity) NA as the reference; report Sonnet NA agreement."""
    from sklearn.metrics import precision_recall_fscore_support
    prec, rec, f1, _ = precision_recall_fscore_support(
        sens_na.astype(int), main_na.astype(int),
        average="binary", zero_division=0,
    )
    return float(prec), float(rec), float(f1)


def compute_per_trait(
    main_df: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
    *,
    coding_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join main and sensitivity scoring on essay_id and compute 8 metrics.

    Args:
        main_df:        Sonnet Stage B output long form, columns:
                        essay_id, trait, score (int|None), reason (str|None).
        sensitivity_df: Opus Stage B output, same schema.
        coding_df:      Optional — Stage 4.3 4-level rationale codes joined on
                        (essay_id, trait). If omitted, rationale-based metrics
                        are reported as None (filled in after Stage 4.3 coding).
    """
    rows: list[AgreementResult] = []
    key = ["essay_id", "trait"]
    merged = main_df.merge(
        sensitivity_df, on=key, suffixes=("_main", "_sens"), validate="one_to_one",
    )
    for trait, sub in merged.groupby("trait"):
        both = sub.dropna(subset=["score_main", "score_sens"])
        if len(both) < 10:
            log.warning("trait %s: only %d non-NA paired — skipping", trait, len(both))
            continue
        m = both["score_main"].to_numpy().astype(int)
        s = both["score_sens"].to_numpy().astype(int)

        na_main = sub["score_main"].isna().to_numpy()
        na_sens = sub["score_sens"].isna().to_numpy()
        prec, rec, f1 = _na_f1(na_main, na_sens)

        rat_wk = None
        mid_infl = None
        if coding_df is not None:
            # Placeholder — populated once Stage 4.3 coding joins on (essay_id, trait).
            pass

        rows.append(AgreementResult(
            trait=trait,
            n=len(both),
            qwk=_qwk(m, s),
            weighted_kappa_linear=_linear_kappa(m, s),
            exact_agreement_rate=float((m == s).mean()),
            adjacent_agreement_rate=float((np.abs(m - s) <= 1).mean()),
            mean_severity_shift=float((s - m).mean()),
            rationale_coding_wk=rat_wk,
            mid_category_inflation=mid_infl,
            na_f1=f1,
            na_precision=prec,
            na_recall=rec,
            na_rate_main=float(na_main.mean()),
            na_rate_sensitivity=float(na_sens.mean()),
        ))
    out = pd.DataFrame([dataclass_asdict_shallow(r) for r in rows])
    out["robust_status"] = [r.robust_status for r in rows]
    return out


def dataclass_asdict_shallow(obj) -> dict:
    """Shallow asdict — avoids pandas DataFrame constructor quirks with nested NaN."""
    return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
