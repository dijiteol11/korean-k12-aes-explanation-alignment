"""Trait-type contrast tests for the v1.3 main alignment claim."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon

TRAIT_TYPE_TRAITS: dict[str, str] = {
    "surface": "expression_2",
    "discourse": "organization_1",
    "content": "content_1",
}


@dataclass(frozen=True)
class WilcoxonResult:
    contrast: str
    alternative: str
    n: int
    statistic: float
    p_value: float
    rank_biserial_r: float
    median_left: float
    median_right: float


def rank_biserial_paired(left: np.ndarray, right: np.ndarray) -> float:
    diff = np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
    diff = diff[np.isfinite(diff) & (diff != 0)]
    if len(diff) == 0:
        return 0.0
    ranks = rankdata(np.abs(diff))
    positive = float(ranks[diff > 0].sum())
    negative = float(ranks[diff < 0].sum())
    total = positive + negative
    if total == 0:
        return 0.0
    return (positive - negative) / total


def holm_bonferroni(p_values: dict[str, float], *, alpha: float = 0.05) -> pd.DataFrame:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    m = len(ordered)
    rows: list[dict] = []
    for rank, (name, p_value) in enumerate(ordered, start=1):
        threshold = alpha / (m - rank + 1)
        rows.append({
            "contrast": name,
            "raw_p": float(p_value),
            "holm_threshold": float(threshold),
            "holm_reject": bool(p_value < threshold),
            "holm_order": rank,
        })
    return pd.DataFrame(rows).sort_values("contrast").reset_index(drop=True)


def wide_trait_type_table(metric_df: pd.DataFrame, *, value_col: str = "jaccard") -> pd.DataFrame:
    required = {"essay_id", "trait", value_col}
    missing = required - set(metric_df.columns)
    if missing:
        raise KeyError(f"metric dataframe missing columns: {sorted(missing)}")

    rows = metric_df[metric_df["trait"].isin(TRAIT_TYPE_TRAITS.values())].copy()
    reverse = {trait: trait_type for trait_type, trait in TRAIT_TYPE_TRAITS.items()}
    rows["trait_type"] = rows["trait"].map(reverse)
    index_cols = ["essay_id"]
    if "purpose" in rows.columns:
        index_cols.append("purpose")
    wide = (
        rows.pivot_table(
            index=index_cols,
            columns="trait_type",
            values=value_col,
            aggfunc="mean",
        )
        .reset_index()
    )
    return wide.dropna(subset=list(TRAIT_TYPE_TRAITS.keys()))


def _wilcoxon_result(
    wide: pd.DataFrame,
    left_col: str,
    right_col: str,
    *,
    alternative: str,
) -> WilcoxonResult:
    left = wide[left_col].to_numpy(dtype=float)
    right = wide[right_col].to_numpy(dtype=float)
    if len(left) == 0:
        return WilcoxonResult(
            contrast=f"{left_col}_vs_{right_col}",
            alternative=alternative,
            n=0,
            statistic=float("nan"),
            p_value=float("nan"),
            rank_biserial_r=float("nan"),
            median_left=float("nan"),
            median_right=float("nan"),
        )
    result = wilcoxon(left, right, alternative=alternative, zero_method="wilcox")
    return WilcoxonResult(
        contrast=f"{left_col}_vs_{right_col}",
        alternative=alternative,
        n=int(len(left)),
        statistic=float(result.statistic),
        p_value=float(result.pvalue),
        rank_biserial_r=float(rank_biserial_paired(left, right)),
        median_left=float(np.median(left)),
        median_right=float(np.median(right)),
    )


def purpose_direction_gate(wide: pd.DataFrame) -> pd.DataFrame:
    if "purpose" not in wide.columns:
        raise KeyError("purpose_direction_gate requires a 'purpose' column")
    rows: list[dict] = []
    for purpose, group in wide.groupby("purpose", sort=True):
        r = rank_biserial_paired(group["surface"].to_numpy(), group["content"].to_numpy())
        median_surface = float(group["surface"].median())
        median_content = float(group["content"].median())
        rows.append({
            "purpose": purpose,
            "n": int(len(group)),
            "median_surface": median_surface,
            "median_content": median_content,
            "rank_biserial_r": float(r),
            "gate_pass": bool(median_surface > median_content and r > 0),
        })
    return pd.DataFrame(rows)


def analyze_trait_type_contrast(metric_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    wide = wide_trait_type_table(metric_df)
    friedman = friedmanchisquare(
        wide["surface"].to_numpy(dtype=float),
        wide["discourse"].to_numpy(dtype=float),
        wide["content"].to_numpy(dtype=float),
    )
    primary = _wilcoxon_result(
        wide,
        "surface",
        "content",
        alternative="greater",
    )
    exploratory_results = [
        _wilcoxon_result(wide, "surface", "discourse", alternative="two-sided"),
        _wilcoxon_result(wide, "discourse", "content", alternative="two-sided"),
    ]
    exploratory_df = pd.DataFrame([r.__dict__ for r in exploratory_results])
    exploratory_holm = holm_bonferroni(
        dict(zip(exploratory_df["contrast"], exploratory_df["p_value"]))
    )
    gate = purpose_direction_gate(wide) if "purpose" in wide.columns else pd.DataFrame()
    primary_df = pd.DataFrame([primary.__dict__])
    primary_df["pooled_median_direction_pass"] = bool(primary.median_left > primary.median_right)
    primary_df["effect_size_pass"] = bool(primary.rank_biserial_r >= 0.10)
    primary_df["p_value_pass"] = bool(primary.p_value < 0.05)
    primary_df["purpose_gate_pass"] = bool(gate["gate_pass"].all()) if not gate.empty else pd.NA
    primary_df["strong_claim_pass"] = (
        primary_df["p_value_pass"]
        & primary_df["effect_size_pass"]
        & primary_df["pooled_median_direction_pass"]
        & primary_df["purpose_gate_pass"].fillna(False)
    )
    medians = pd.DataFrame([{
        "median_surface": float(wide["surface"].median()),
        "median_discourse": float(wide["discourse"].median()),
        "median_content": float(wide["content"].median()),
    }])
    friedman_df = pd.DataFrame([{
        "n": int(len(wide)),
        "statistic": float(friedman.statistic),
        "p_value": float(friedman.pvalue),
    }])
    return {
        "wide": wide,
        "friedman": friedman_df,
        "primary": primary_df,
        "exploratory": exploratory_df,
        "exploratory_holm": exploratory_holm,
        "purpose_gate": gate,
        "medians": medians,
    }
