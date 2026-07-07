"""Score-level agreement premise check for v1.3."""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from configs.paths import REPORTS_DIR
from src.models.metrics import quadratic_weighted_kappa

ANALYZED_TRAITS: tuple[str, ...] = ("expression_2", "organization_1", "content_1")
STAGE2_DIR: Path = REPORTS_DIR / "stage2_models"
STAGE4_DIR: Path = REPORTS_DIR / "stage4_llm"


def load_oof_predictions(
    purpose: str,
    *,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    stage2_dir: Path = STAGE2_DIR,
) -> pd.DataFrame:
    path = stage2_dir / f"oof_predictions__{purpose}__{embedding}__{cv_label}.csv"
    if not path.exists():
        raise FileNotFoundError(f"OOF prediction file missing: {path}")
    return pd.read_csv(path)


def load_llm_stage_b_scores(path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        essay_id = int(record["essay_id"])
        purpose = record.get("purpose")
        for trait, entry in record.get("scores", {}).items():
            rows.append({
                "essay_id": essay_id,
                "purpose": purpose,
                "trait": trait,
                "llm_score": entry.get("score"),
                "llm_confidence": entry.get("confidence"),
                "llm_is_na": entry.get("score") is None,
            })
    return pd.DataFrame(rows)


def compute_score_qwk(
    oof_df: pd.DataFrame,
    llm_scores: pd.DataFrame,
    *,
    traits: Iterable[str] = ANALYZED_TRAITS,
) -> pd.DataFrame:
    required_oof = {"essay_id", "trait", "y_pred"}
    required_llm = {"essay_id", "trait", "llm_score"}
    missing_oof = required_oof - set(oof_df.columns)
    missing_llm = required_llm - set(llm_scores.columns)
    if missing_oof:
        raise KeyError(f"OOF dataframe missing columns: {sorted(missing_oof)}")
    if missing_llm:
        raise KeyError(f"LLM score dataframe missing columns: {sorted(missing_llm)}")

    merged = oof_df.merge(llm_scores, on=["essay_id", "trait"], how="inner")
    merged = merged[merged["trait"].isin(tuple(traits))]
    merged = merged[merged["llm_score"].notna()]

    rows: list[dict] = []
    for trait, group in merged.groupby("trait", sort=True):
        rows.append({
            "trait": trait,
            "n": int(len(group)),
            "qwk": quadratic_weighted_kappa(
                group["y_pred"].to_numpy(dtype=float),
                group["llm_score"].to_numpy(dtype=float),
            ),
            "xgb_mean": float(group["y_pred"].mean()),
            "llm_mean": float(group["llm_score"].mean()),
        })
    return pd.DataFrame(rows)


def compute_score_qwk_for_purpose(
    purpose: str,
    *,
    stage_b_path: Path,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    traits: Iterable[str] = ANALYZED_TRAITS,
) -> pd.DataFrame:
    return compute_score_qwk(
        load_oof_predictions(purpose, embedding=embedding, cv_label=cv_label),
        load_llm_stage_b_scores(stage_b_path),
        traits=traits,
    )
