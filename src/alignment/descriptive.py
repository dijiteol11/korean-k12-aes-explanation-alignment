"""
Stage 5.2 — χ² descriptive (plan v2.3 §4.5.3 — v2.2 주 분석에서 강등됨).

v2.3은 "nested 구조(essay⊂prompt⊂grade, trait 반복측정) 무시"를 이유로 χ²를
주 통계에서 제외하고 ordinal mixed model로 대체. 본 모듈은 **서술 통계
보조용**으로만 남는다:

    - label × purpose 단순 분할표 + χ² p-value (nested 구조 무시하므로
      해석 무게는 낮다)
    - label × rubric_domain 분할표
    - label × grade 분할표

Reviewer에게 "exploratory descriptive"로 명시하여 본 분석과 무게가 다름을
밝힌다. 의심 가는 pattern을 main clmm에서 재검증하는 탐색 장치로만.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from configs.paths import REPORTS_DIR

log = logging.getLogger(__name__)

OUT_DIR: Path = REPORTS_DIR / "stage5_alignment" / "descriptive"


def crosstab_chi2(
    df: pd.DataFrame,
    rows_col: str,
    cols_col: str = "label",
) -> dict:
    """Contingency table + χ² test (no nested correction — v2.3 §4.5.3)."""
    tab = pd.crosstab(df[rows_col], df[cols_col])
    try:
        chi2, p, dof, expected = chi2_contingency(tab)
    except ValueError as e:
        log.warning("χ² on %s × %s failed: %s", rows_col, cols_col, e)
        return {"crosstab": tab, "chi2": np.nan, "p": np.nan, "dof": 0}
    return {"crosstab": tab, "chi2": float(chi2), "p": float(p), "dof": int(dof)}


def run_all(labeled_df: pd.DataFrame, out_dir: Path = OUT_DIR) -> None:
    """Run the three descriptive χ² tests and write results."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for rows_col in ("purpose", "rubric_domain", "grade"):
        if rows_col not in labeled_df.columns:
            log.warning("skip χ² on %s × label — column missing", rows_col)
            continue
        result = crosstab_chi2(labeled_df, rows_col)
        tab_path = out_dir / f"crosstab__{rows_col}_x_label.csv"
        result["crosstab"].to_csv(tab_path)
        meta_path = out_dir / f"chi2__{rows_col}_x_label.txt"
        meta_path.write_text(
            f"χ² (descriptive only, nested structure ignored — v2.3 §4.5.3)\n"
            f"  rows: {rows_col}  ×  cols: label\n"
            f"  chi2 = {result['chi2']:.3f}\n"
            f"  dof  = {result['dof']}\n"
            f"  p    = {result['p']:.4f}\n"
            f"  N    = {int(result['crosstab'].values.sum())}\n",
            encoding="utf-8",
        )
        log.info("Wrote %s + %s", tab_path.name, meta_path.name)
