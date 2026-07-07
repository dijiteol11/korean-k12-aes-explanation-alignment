"""Compute v1.3 smoke-test family detection QA metrics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.paths import REPORTS_DIR
from src.alignment.jaccard_metric import compute_alignment_metric
from src.alignment.llm_family_detector import load_stage_c_family_sets
from src.alignment.shap_top_families import build_shap_family_sets

DEFAULT_OUT = REPORTS_DIR / "stage4_llm" / "smoke_test" / "dictionary_coverage.md"
ANALYZED_TRAITS: tuple[str, ...] = ("expression_2", "organization_1", "content_1")
NON_EMPTY_RATE_MIN: float = 0.80
MAX_FAMILY_SHARE_MAX: float = 0.50
JACCARD_MEDIAN_MIN: float = 0.10
JACCARD_MEDIAN_MAX: float = 0.70
JACCARD_STD_MIN: float = 0.05


def _family_share(llm_sets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    n_cells = max(1, len(llm_sets))
    for families in llm_sets["llm_families"]:
        for family in families:
            rows.append({"family": family})
    if not rows:
        return pd.DataFrame(columns=["family", "detected_cells", "cell_share"])
    counts = pd.DataFrame(rows).value_counts("family").reset_index(name="detected_cells")
    counts["cell_share"] = counts["detected_cells"] / n_cells
    return counts.sort_values("family")


def _non_empty_by_trait(llm_sets: pd.DataFrame) -> pd.DataFrame:
    if llm_sets.empty:
        return pd.DataFrame(columns=["trait", "n_cells", "positive_cells", "non_empty_rate"])
    rows = []
    for trait, group in llm_sets.groupby("trait", observed=True, sort=True):
        positives = int((~group["llm_family_empty"]).sum())
        total = int(len(group))
        rows.append({
            "trait": str(trait),
            "n_cells": total,
            "positive_cells": positives,
            "non_empty_rate": positives / total if total else 0.0,
        })
    return pd.DataFrame(rows)


def _prevalence_diagnostic(rate: float, positive_cells: int) -> str:
    if positive_cells == 0:
        return "DEGENERATE_ZERO"
    if rate < 0.20:
        return "LOW_PREVALENCE"
    return "INTERPRETABLE"


def compute_metric_gates(
    llm_sets: pd.DataFrame,
    *,
    alignment_df: pd.DataFrame | None,
    analyzed_traits: tuple[str, ...] = ANALYZED_TRAITS,
) -> dict:
    """Compute v2.6 §8.2 axes (f)(g)(h) pass/fail for analyzed traits."""
    trait_rates = _non_empty_by_trait(llm_sets)
    analyzed_set = set(analyzed_traits)
    gate_rates = trait_rates[trait_rates["trait"].isin(analyzed_set)].copy()
    present_traits = set(gate_rates["trait"].astype(str))
    missing_traits = [trait for trait in analyzed_traits if trait not in present_traits]
    if missing_traits:
        gate_rates = pd.concat([
            gate_rates,
            pd.DataFrame([
                {
                    "trait": trait,
                    "n_cells": 0,
                    "positive_cells": 0,
                    "non_empty_rate": 0.0,
                }
                for trait in missing_traits
            ]),
        ], ignore_index=True)
    gate_rates["axis_f_pass"] = gate_rates["non_empty_rate"] >= NON_EMPTY_RATE_MIN
    gate_rates["prevalence_diagnostic"] = [
        _prevalence_diagnostic(float(row.non_empty_rate), int(row.positive_cells))
        for row in gate_rates.itertuples(index=False)
    ]
    gate_rates = gate_rates.sort_values("trait").reset_index(drop=True)

    gate_llm = llm_sets[llm_sets["trait"].isin(analyzed_set)].copy()
    family_share = _family_share(gate_llm)
    max_share = float(family_share["cell_share"].max()) if not family_share.empty else 0.0
    axis_g_pass = max_share < MAX_FAMILY_SHARE_MAX

    median_a: float | None = None
    std_a: float | None = None
    axis_h_pass = False
    if alignment_df is not None and not alignment_df.empty:
        gate_alignment = alignment_df[alignment_df["trait"].isin(analyzed_set)].copy()
        if not gate_alignment.empty:
            median_a = float(gate_alignment["jaccard"].median())
            std_a = float(gate_alignment["jaccard"].std(ddof=0))
            axis_h_pass = (
                JACCARD_MEDIAN_MIN <= median_a <= JACCARD_MEDIAN_MAX
                and std_a > JACCARD_STD_MIN
            )

    axis_f_pass = bool(gate_rates["axis_f_pass"].all())
    return {
        "analyzed_traits": analyzed_traits,
        "trait_rates": trait_rates,
        "gate_trait_rates": gate_rates,
        "family_share": family_share,
        "max_family_share": max_share,
        "median_a": median_a,
        "std_a": std_a,
        "axis_f_pass": axis_f_pass,
        "axis_g_pass": axis_g_pass,
        "axis_h_pass": axis_h_pass,
        "overall_pass": axis_f_pass and axis_g_pass and axis_h_pass,
    }


def _pass_text(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.3f}"


def write_report(
    llm_sets: pd.DataFrame,
    *,
    alignment_df: pd.DataFrame | None,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gates = compute_metric_gates(llm_sets, alignment_df=alignment_df)
    non_empty = gates["trait_rates"]
    family_share = _family_share(llm_sets)
    max_share = float(family_share["cell_share"].max()) if not family_share.empty else 0.0

    lines = [
        "# Stage 4 LLM Family Smoke Audit",
        "",
        f"- Cells: {len(llm_sets)}",
        f"- Max family cell share: {max_share:.3f}",
        f"- Metric gate overall: **{_pass_text(gates['overall_pass'])}**",
        "",
        "## Gate Summary (Analyzed Traits)",
        "",
        f"- Analyzed traits: {', '.join(gates['analyzed_traits'])}",
        f"- (f) Non-empty rate: **{_pass_text(gates['axis_f_pass'])}** "
        f"(threshold: each analyzed trait >= {NON_EMPTY_RATE_MIN:.2f})",
        f"- (g) Max family share: **{_pass_text(gates['axis_g_pass'])}** "
        f"(analyzed-trait max={gates['max_family_share']:.3f}, threshold < {MAX_FAMILY_SHARE_MAX:.2f})",
        f"- (h) Jaccard sanity: **{_pass_text(gates['axis_h_pass'])}** "
        f"(median={_fmt_optional(gates['median_a'])}, std={_fmt_optional(gates['std_a'])})",
        "",
        gates["gate_trait_rates"].to_markdown(index=False),
        "",
        "## Non-Empty Rate By Trait",
        "",
        non_empty.to_markdown(index=False),
        "",
        "## Family Coverage",
        "",
        family_share.to_markdown(index=False) if not family_share.empty else "No family detections.",
        "",
    ]
    if alignment_df is not None and not alignment_df.empty:
        lines.extend([
            "## Jaccard Sanity",
            "",
            f"- Median A: {alignment_df['jaccard'].median():.3f}",
            f"- Std A: {alignment_df['jaccard'].std(ddof=0):.3f}",
            "",
        ])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-c", type=Path, required=True)
    parser.add_argument("--local-shap", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    llm_sets = load_stage_c_family_sets(args.stage_c)
    alignment_df = None
    if args.local_shap is not None:
        local = pd.read_parquet(args.local_shap)
        shap_sets = build_shap_family_sets(local, traits=llm_sets["trait"].unique())
        alignment_df = compute_alignment_metric(shap_sets, llm_sets)
    write_report(llm_sets, alignment_df=alignment_df, out_path=args.out)
    gates = compute_metric_gates(llm_sets, alignment_df=alignment_df)
    print(f"Wrote {args.out}")
    return 0 if gates["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
