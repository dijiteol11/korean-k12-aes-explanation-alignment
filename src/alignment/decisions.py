"""
Stage 5 — Messick 4-범주 결정표 적용 (decision_table_preregistered.md §3).

Reads the essay × trait alignment matrix from ``matrix.py`` and applies
pre-registered rules to classify each cell as one of:

    Aligned         — 세 증거가 rubric-relevant 요소를 수렴적으로 지시 (§3.4)
    UR              — 구인 과소대표 (§3.1)
    CIV             — 구인 무관 변량 (§3.2)
    Indeterminate   — 귀속 불가 (§3.3, priority 최우선 §4)

Thresholds are sourced from configs.shap (UR gate) and
configs.stage4 placeholders for the CIV 10% and feedback purity 50%
values. Both live in the pre-registered documents as "Internal
consensus scope" (Path β, 2026-04-24).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from configs.paths import REPORTS_DIR

log = logging.getLogger(__name__)

Label = Literal["Aligned", "UR", "CIV", "Indeterminate"]

# Thresholds — currently replicate v2.3 §4.5.2 original values. Update in
# lockstep with `decision_table_preregistered.md` §3 after v1.0 commit.
CIV_JUSTIFICATION_MAX: float = 0.10   # §3.2 — rationale+feedback rubric-mapping ≤10%
FEEDBACK_PURITY_OFF_MAX: float = 0.50  # §3.3 — trait feedback off-area ratio ≥50% flag
INDETERMINATE_MIN_CONDITIONS: int = 2  # §3.3 "2 이상"


@dataclass(frozen=True)
class CellClassification:
    essay_id: int
    trait: str
    label: Label
    triggered_rules: tuple[str, ...]
    priority_rank: int   # 1=Indeterminate ... 4=Aligned per §4


# --- Individual signal evaluators ----------------------------------------
def _shap_absent_for_rubric(row) -> bool:
    """§3.1 UR condition: rubric-relevant family missing from SHAP Top-3.

    Needs family_rubric_mapping; hydrated externally. Here we approximate
    by treating "SHAP unstable" (τ<0.5 OR Jaccard<0.5) as the UR gate.
    Full family-mapping check is folded in via `family_rubric_match` flag
    set by the caller after consulting family_rubric_mapping_preregistered.md.
    """
    unstable = bool(row.get("tau_unstable_any") or row.get("jaccard_unstable"))
    no_match = bool(row.get("family_rubric_match") is False)
    return unstable or no_match


def _civ_justification_low(row) -> bool:
    """§3.2 CIV: rationale/feedback 매핑 비율 ≤10%."""
    r = row.get("justification_rate")
    if pd.isna(r):
        return False
    return float(r) <= CIV_JUSTIFICATION_MAX


def _indeterminate_conditions(row) -> tuple[str, ...]:
    """§3.3 Indeterminate: 2 이상 동시 충족."""
    conds: list[str] = []
    tau = bool(row.get("tau_unstable_any"))
    jac = bool(row.get("jaccard_unstable"))
    if tau and jac:
        conds.append("both_tau_and_jaccard_unstable")
    if str(row.get("llm_code")) == "NA" or bool(row.get("llm_is_na")):
        conds.append("llm_na")
    if str(row.get("human_code")) == "NA":
        conds.append("human_na")
    if bool(row.get("feedback_impure_50")):
        conds.append("feedback_impure_50")
    return tuple(conds)


def _aligned_condition(row) -> bool:
    """§3.4 Aligned: Top-3 mapping + LLM상 + Human상/중."""
    mapped = bool(row.get("family_rubric_match"))
    llm = str(row.get("llm_code"))
    human = str(row.get("human_code"))
    return mapped and llm == "상" and human in ("상", "중")


# --- Cell-level classifier -----------------------------------------------
def classify_cell(row) -> CellClassification:
    """§4 priority: Indeterminate (1) > UR/CIV (2/3) > Aligned (4)."""
    inder_conds = _indeterminate_conditions(row)
    if len(inder_conds) >= INDETERMINATE_MIN_CONDITIONS:
        return CellClassification(
            essay_id=int(row["essay_id"]),
            trait=str(row["trait"]),
            label="Indeterminate",
            triggered_rules=inder_conds,
            priority_rank=1,
        )

    rules: list[str] = []
    ur = _shap_absent_for_rubric(row)
    civ = _civ_justification_low(row)
    if ur:
        rules.append("shap_absent_or_unstable")
    if civ:
        rules.append("rationale_mapping_below_10pct")

    if ur and not civ:
        return CellClassification(int(row["essay_id"]), str(row["trait"]),
                                  "UR", tuple(rules), 2)
    if civ and not ur:
        return CellClassification(int(row["essay_id"]), str(row["trait"]),
                                  "CIV", tuple(rules), 3)
    if ur and civ:
        # Both conditions trigger — default UR per §4 ordering; record both.
        return CellClassification(int(row["essay_id"]), str(row["trait"]),
                                  "UR", tuple(rules + ["also_civ_triggered"]), 2)

    if _aligned_condition(row):
        return CellClassification(int(row["essay_id"]), str(row["trait"]),
                                  "Aligned", ("converge_on_rubric_relevant",), 4)

    # Residual: no condition triggered but evidence incomplete → Indeterminate
    # conservative default, per §4 "Indeterminate 최우선".
    return CellClassification(int(row["essay_id"]), str(row["trait"]),
                              "Indeterminate",
                              ("residual_no_decisive_evidence",), 1)


# --- Matrix-wide driver --------------------------------------------------
def classify_matrix(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """Apply classify_cell to every row and return the augmented matrix.

    Requires precomputed columns:
      - family_rubric_match (bool) — set externally via family_rubric_mapping
      - justification_rate (float | NaN) — from Stage 4.3 coding matching
    If these are absent, classifier falls back on conservative behavior:
      - family_rubric_match=NaN → treated as not-matching for UR; not-matching for Aligned
      - justification_rate=NaN → CIV not triggered
    """
    rows: list[dict] = []
    for _, r in matrix_df.iterrows():
        c = classify_cell(r)
        rows.append({
            "essay_id": c.essay_id,
            "trait":    c.trait,
            "label":    c.label,
            "triggered_rules": "|".join(c.triggered_rules),
            "priority_rank":   c.priority_rank,
        })
    out = pd.DataFrame(rows)
    merged = matrix_df.merge(out, on=["essay_id", "trait"], how="left")
    return merged


def summarize_labels(labeled_df: pd.DataFrame) -> pd.DataFrame:
    """Per (purpose, trait) label distribution."""
    return (
        labeled_df
        .groupby(["purpose", "trait", "label"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )


def write_labeled_matrix(
    matrix_df: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Apply classify_matrix and persist the labeled matrix.

    v2.6 §9.2 Stage 5→6 interface contract — Stage 6
    (``src.alignment.triangulate``) reads only this artifact, not the raw
    matrix. Format dispatch by suffix: ``.parquet`` (preferred) or ``.csv``.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    labeled = classify_matrix(matrix_df)
    if out.suffix == ".parquet":
        labeled.to_parquet(out, index=False)
    elif out.suffix == ".csv":
        labeled.to_csv(out, index=False)
    else:
        raise ValueError(
            f"Unsupported output suffix {out.suffix!r}; use .parquet or .csv"
        )
    log.info("wrote labeled matrix: %s (%d rows)", out, len(labeled))
    return out
