"""Essay-level SHAP top-family extraction for the v1.3 main contrast."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from configs.paths import FEATURE_FAMILIES, REPORTS_DIR
from configs.shap import JACCARD_TOP_K

SHAP_DIR: Path = REPORTS_DIR / "stage3_shap"

FAMILY_ORDER: dict[str, int] = {family: i for i, family in enumerate(FEATURE_FAMILIES)}


def _family_order(family: str) -> int:
    return FAMILY_ORDER.get(str(family), len(FAMILY_ORDER))


def local_shap_path(
    purpose: str,
    *,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    shap_dir: Path = SHAP_DIR,
) -> Path:
    return shap_dir / f"local_shap__{purpose}__{embedding}__{cv_label}.parquet"


def load_local_shap(
    purpose: str,
    *,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    shap_dir: Path = SHAP_DIR,
) -> pd.DataFrame:
    path = local_shap_path(purpose, embedding=embedding, cv_label=cv_label, shap_dir=shap_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"Local SHAP parquet missing: {path}. "
            "Run src.shap_analysis.sweep for this purpose/embedding/CV first."
        )
    return pd.read_parquet(path)


def top_families_for_cell(
    local_shap_df: pd.DataFrame,
    essay_id: int,
    trait: str,
    *,
    k: int = JACCARD_TOP_K,
) -> tuple[str, ...]:
    """Return ``F_SHAP(i,t)`` using abs(shap_sum) and registered tie-breaks."""
    required = {"essay_id", "trait", "family", "shap_sum"}
    missing = required - set(local_shap_df.columns)
    if missing:
        raise KeyError(f"local SHAP dataframe missing columns: {sorted(missing)}")

    cell = local_shap_df[
        (local_shap_df["essay_id"].astype(int) == int(essay_id))
        & (local_shap_df["trait"].astype(str) == str(trait))
    ].copy()
    if cell.empty:
        return ()
    cell["_abs_shap"] = cell["shap_sum"].abs()
    cell["_family_order"] = cell["family"].map(_family_order)
    ranked = cell.sort_values(
        ["_abs_shap", "_family_order", "family"],
        ascending=[False, True, True],
        kind="mergesort",
    )
    return tuple(ranked.head(k)["family"].astype(str).tolist())


def build_shap_family_sets(
    local_shap_df: pd.DataFrame,
    *,
    traits: Iterable[str] | None = None,
    k: int = JACCARD_TOP_K,
) -> pd.DataFrame:
    trait_filter = set(traits) if traits is not None else None
    df = local_shap_df.copy()
    if trait_filter is not None:
        df = df[df["trait"].isin(trait_filter)]
    if df.empty:
        return pd.DataFrame(columns=["essay_id", "trait", "shap_families", "shap_family_count"])

    rows: list[dict] = []
    for (essay_id, trait), group in df.groupby(["essay_id", "trait"], sort=True):
        families = top_families_for_cell(group, int(essay_id), str(trait), k=k)
        rows.append({
            "essay_id": int(essay_id),
            "trait": str(trait),
            "shap_families": list(families),
            "shap_family_count": len(families),
        })
    return pd.DataFrame(rows)


def load_shap_family_sets(
    purpose: str,
    *,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    traits: Iterable[str] | None = None,
    k: int = JACCARD_TOP_K,
    shap_dir: Path = SHAP_DIR,
) -> pd.DataFrame:
    return build_shap_family_sets(
        load_local_shap(purpose, embedding=embedding, cv_label=cv_label, shap_dir=shap_dir),
        traits=traits,
        k=k,
    )
