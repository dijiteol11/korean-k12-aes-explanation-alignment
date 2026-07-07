"""Compute the v1.3 essay-level SHAP-LLM family Jaccard metric."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from configs.paths import REPORTS_DIR
from src.alignment.llm_family_detector import load_stage_c_family_sets
from src.alignment.shap_top_families import load_shap_family_sets

OUT_DIR: Path = REPORTS_DIR / "stage5_alignment"


def normalize_family_set(value) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, float) and pd.isna(value):
        return frozenset()
    if isinstance(value, str):
        if not value:
            return frozenset()
        return frozenset(part.strip() for part in value.split("|") if part.strip())
    return frozenset(str(part) for part in value if str(part))


def jaccard(left, right) -> float:
    left_set = normalize_family_set(left)
    right_set = normalize_family_set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def compute_alignment_metric(shap_sets: pd.DataFrame, llm_sets: pd.DataFrame) -> pd.DataFrame:
    """Merge ``F_SHAP`` and ``F_LLM`` tables and compute ``A(i,t)``."""
    required_shap = {"essay_id", "trait", "shap_families"}
    required_llm = {"essay_id", "trait", "llm_families"}
    missing_shap = required_shap - set(shap_sets.columns)
    missing_llm = required_llm - set(llm_sets.columns)
    if missing_shap:
        raise KeyError(f"SHAP set table missing columns: {sorted(missing_shap)}")
    if missing_llm:
        raise KeyError(f"LLM set table missing columns: {sorted(missing_llm)}")

    merged = shap_sets.merge(llm_sets, on=["essay_id", "trait"], how="inner")
    if "purpose" not in merged.columns:
        if "purpose_x" in merged.columns:
            merged["purpose"] = merged["purpose_x"]
        elif "purpose_y" in merged.columns:
            merged["purpose"] = merged["purpose_y"]

    rows: list[dict] = []
    for _, row in merged.iterrows():
        shap_families = normalize_family_set(row["shap_families"])
        llm_families = normalize_family_set(row["llm_families"])
        union = shap_families | llm_families
        rows.append({
            **row.to_dict(),
            "shap_families_pipe": "|".join(sorted(shap_families)),
            "llm_families_pipe": "|".join(sorted(llm_families)),
            "jaccard": 0.0 if not union else len(shap_families & llm_families) / len(union),
            "shap_family_empty": len(shap_families) == 0,
            "llm_family_empty": len(llm_families) == 0,
            "family_union_size": len(union),
            "family_intersection_size": len(shap_families & llm_families),
        })
    return pd.DataFrame(rows)


def build_alignment_metric_for_purpose(
    purpose: str,
    *,
    stage_c_path: Path,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    traits: Iterable[str] | None = None,
) -> pd.DataFrame:
    shap_sets = load_shap_family_sets(
        purpose,
        embedding=embedding,
        cv_label=cv_label,
        traits=traits,
    )
    llm_sets = load_stage_c_family_sets(stage_c_path, traits=traits)
    return compute_alignment_metric(shap_sets, llm_sets)


def write_alignment_metric(
    df: pd.DataFrame,
    purpose: str,
    *,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    out_dir: Path = OUT_DIR,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"jaccard_alignment__{purpose}__{embedding}__{cv_label}.parquet"
    df.to_parquet(path, index=False)
    return path
