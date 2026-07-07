"""Detector miss diagnostic spot-check + (legacy) keyword blind audit scoring.

**Direction (plan §41, 2026-05-28)**: F_LLM is a deterministic exact-match
metric, so the machine detector is the deterministic *operational scorer* (NOT
a gold standard) and inter-coder κ is NOT a primary validity gate. Human coding
is a *diagnostic comparator* — a detector-miss spot-check: does the strict
matcher miss (or over-detect) family invocations a human judges present?
(human=1 ∧ machine=0 = miss candidate; the machine is not assumed correct.)
v1.3 §7 κ≥0.70 gate is preserved as pre-registered intent; this is a documented
deviation.

PRIMARY output (when ``machine_truth.csv`` is available):
  - Detector **miss** (human=1 ∧ machine=0) / **false-positive** (human=0 ∧
    machine=1) rates, overall + per analyzed trait + per family
    (``compute_spotcheck``).

Descriptive / legacy layer (kept; not a gate):
  - Inter-coder Cohen κ overall + per-family (``compute_audit``)
  - analyzed-trait coverage, per-family prevalence flag (DEGENERATE_ZERO /
    LOW_PREVALENCE / INTERPRETABLE), content_1 low-prevalence warning
    (§35.3 비판 1: F_LLM family vs content trait 의 본질적 mismatch 가능성)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.paths import REPORTS_DIR

DEFAULT_OUT = REPORTS_DIR / "stage4_llm" / "keyword_blind_audit.md"

# Sync with scripts.llm_family_smoke_audit.ANALYZED_TRAITS to avoid drift.
ANALYZED_TRAITS: tuple[str, ...] = ("expression_2", "organization_1", "content_1")
LOW_PREVALENCE_THRESHOLD: float = 0.20    # < 20% positive → LOW_PREVALENCE flag
CONTENT_1_WARN_THRESHOLD: float = 0.05    # < 5% positive on content_1 → §35.3 비판 1 경고


def _parse_detected_strict(series: pd.Series, source_path: Path) -> pd.Series:
    """Strict boolean parse for the coder-filled ``detected`` column.

    Only {0, 1, true, false} (case-insensitive) are accepted. NaN / blank /
    any other token raises ValueError naming the offending row — protecting
    against the silent ``astype(bool)`` failure where NaN and "" both coerce
    to True (which would corrupt κ).

    Row numbers in the error are 1-based with +2 offset (1 for header, 1 for
    0-index) so they match the spreadsheet line a coder would see.
    """
    out: list[bool] = []
    for idx, val in series.items():
        if pd.isna(val):
            raise ValueError(
                f"{source_path}: row {idx + 2} 'detected' is blank/missing - "
                f"every row must be filled with 0 or 1."
            )
        token = str(val).strip().lower()
        if token in ("1", "true"):
            out.append(True)
        elif token in ("0", "false"):
            out.append(False)
        else:
            raise ValueError(
                f"{source_path}: row {idx + 2} 'detected'={val!r} is invalid - "
                f"expected one of 0/1/true/false."
            )
    return pd.Series(out, index=series.index)


def _load(path: Path, coder_label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"essay_id", "trait", "family", "detected"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"{path} missing columns: {sorted(missing)}")
    df = df[list(required)].copy()
    df["coder"] = coder_label
    df["detected"] = _parse_detected_strict(df["detected"], path)
    return df


def _load_machine(path: Path) -> pd.DataFrame:
    """Load the deterministic detector truth (analyst/machine_truth.csv)."""
    df = pd.read_csv(path)
    required = {"essay_id", "trait", "family", "machine_detected"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"{path} missing columns: {sorted(missing)}")
    df = df[list(required)].copy()
    df["machine_detected"] = _parse_detected_strict(df["machine_detected"], path)
    return df


def _spotcheck_grouped(merged: pd.DataFrame, by: str) -> pd.DataFrame:
    grouped = merged.groupby(by, sort=True).agg(
        n=("detected", "size"),
        human_pos=("detected", "sum"),
        machine_pos=("machine_detected", "sum"),
        miss=("_miss", "sum"),
        false_pos=("_fp", "sum"),
        agree=("_agree", "sum"),
    ).reset_index()
    for col in ("n", "human_pos", "machine_pos", "miss", "false_pos", "agree"):
        grouped[col] = grouped[col].astype(int)
    grouped["agreement_rate"] = (grouped["agree"] / grouped["n"]).round(3)
    return grouped.drop(columns=["agree"])


def compute_spotcheck(
    annotator: pd.DataFrame, machine: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Compare one annotator's keyword-presence judgment to the deterministic
    detector (§41.4). Returns (per_family, per_analyzed_trait, summary).

    Signals (the non-redundant value of human coding):
      - **miss**: human=1 ∧ machine=0 — strict exact/lemma match missed an
        invocation the human judged present (detector too strict).
      - **false_pos**: human=0 ∧ machine=1 — detector matched where the human
        saw no invocation.

    This is a *diagnostic*, NOT a κ≥0.70 gate (F_LLM is deterministic).
    """
    key = ["essay_id", "trait", "family"]
    merged = annotator.merge(machine, on=key, how="inner")
    cols = ["family", "n", "human_pos", "machine_pos", "miss", "false_pos", "agreement_rate"]
    if merged.empty:
        empty_fam = pd.DataFrame(columns=cols)
        empty_trait = pd.DataFrame(columns=["trait"] + cols[1:])
        return empty_fam, empty_trait, {
            "n": 0, "miss_total": 0, "false_pos_total": 0,
            "human_pos_total": 0, "machine_pos_total": 0, "agreement_rate": None,
        }

    human = merged["detected"].astype(bool)
    mach = merged["machine_detected"].astype(bool)
    merged = merged.assign(_miss=human & ~mach, _fp=~human & mach, _agree=human == mach)

    per_family = _spotcheck_grouped(merged, "family")
    analyzed = merged[merged["trait"].isin(ANALYZED_TRAITS)]
    per_trait = (
        _spotcheck_grouped(analyzed, "trait")
        if not analyzed.empty
        else pd.DataFrame(columns=["trait"] + cols[1:])
    )

    summary = {
        "n": int(len(merged)),
        "miss_total": int(merged["_miss"].sum()),
        "false_pos_total": int(merged["_fp"].sum()),
        "human_pos_total": int(human.sum()),
        "machine_pos_total": int(mach.sum()),
        "agreement_rate": float(merged["_agree"].mean()),
    }
    return per_family, per_trait, summary


def _fmt_rate(num: int, den: int) -> str:
    if den == 0:
        return f"{num}/0 (n/a)"
    return f"{num}/{den} ({num / den:.1%})"


def _spotcheck_lines(
    per_family: pd.DataFrame,
    per_trait: pd.DataFrame,
    summary: dict,
    label: str,
) -> list[str]:
    agree = summary.get("agreement_rate")
    agree_str = f"{agree:.1%}" if agree is not None else "n/a"
    return [
        f"## Detector Spot-Check — {label} vs machine (PRIMARY diagnostic)",
        "",
        "F_LLM 은 deterministic exact-match metric. 본 절은 strict matcher 가 "
        "사람이 보기에 명백한 family 호출을 **놓치는지 (miss)** / **과검출하는지 "
        "(false-positive)** 진단한다. **κ gate 아님** (v2.6 §4.1.2.1 (d) 2026-05-28 "
        "deviation: human coding = diagnostic spot-check, not F_LLM replacement).",
        "",
        f"- Decisions compared: {summary['n']}",
        f"- Human-positive: {summary['human_pos_total']} · "
        f"Machine-positive: {summary['machine_pos_total']}",
        f"- **Detector miss** (human=1 ∧ machine=0): "
        f"{_fmt_rate(summary['miss_total'], summary['human_pos_total'])} of human-positive "
        f"← PRIMARY 신호",
        f"- Detector false-positive (human=0 ∧ machine=1): "
        f"{summary['false_pos_total']} (count) — *descriptive sanity check only*: "
        f"FP 는 machine-positive (≈control cells, n 작음) 에서만 발생하므로 "
        f"calibrated FP *rate* 로 해석 금지. FP 를 강하게 보려면 "
        f"`build_blind_audit_sample --n-control` 증가.",
        f"- Agreement rate: {agree_str}",
        "",
        "### Per analyzed trait",
        "",
        per_trait.to_markdown(index=False) if not per_trait.empty else "(no analyzed-trait cells)",
        "",
        "### Per family",
        "",
        per_family.to_markdown(index=False) if not per_family.empty else "(no families)",
        "",
        "**해석 (§35.5 분기):** form-family (syn/dis_*) miss 높음 → detector/lemma "
        "너무 엄격 → normalization 보강 (SHA cascade 없음). content_1 에서 human 도 "
        "miss 거의 0 (= human positive 자체가 0) → metric-design 한계 확정 "
        "(§11 신규 limitation, P2 본 실행 with caveat).",
        "",
    ]


def write_spotcheck_only_report(spotcheck_sections: list[str], out_path: Path) -> None:
    """Single-annotator report (no inter-coder κ)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Detector Spot-Check (single annotator)",
        "",
        "Inter-coder κ not computed (single annotator). F_LLM is deterministic; "
        "inter-coder κ is not a primary validity gate "
        "(v2.6 §4.1.2.1 (d) deviation 2026-05-28).",
        "",
        *spotcheck_sections,
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _kappa(left: pd.Series, right: pd.Series) -> float | None:
    combined = pd.concat([left.astype(int), right.astype(int)], ignore_index=True)
    if combined.nunique() < 2:
        return None
    return float(cohen_kappa_score(left.astype(int), right.astype(int)))


def _prevalence_flag(positive_count: int, total: int) -> str:
    if total == 0:
        return "EMPTY"
    if positive_count == 0:
        return "DEGENERATE_ZERO"
    rate = positive_count / total
    if rate < LOW_PREVALENCE_THRESHOLD:
        return "LOW_PREVALENCE"
    return "INTERPRETABLE"


def compute_audit(
    coder_a: pd.DataFrame, coder_b: pd.DataFrame
) -> tuple[pd.DataFrame, float | None, dict]:
    """Compute overall + per-family κ plus diagnostic context.

    Returns (per_family_df, overall_kappa, diagnostics).

    ``diagnostics`` keys:
        - cell_count, family_count
        - analyzed_coverage: dict[trait → cells]
        - non_analyzed_coverage: dict[trait → cells]
        - content_1_warning: bool — True if positive rate on content_1 cells
          across both coders < CONTENT_1_WARN_THRESHOLD
        - content_1_positive_rate: float | None
    """
    key = ["essay_id", "trait", "family"]
    merged = coder_a.merge(coder_b, on=key, suffixes=("_a", "_b"), how="inner")
    if merged.empty:
        raise ValueError("No overlapping audit cells between coder files")

    overall = _kappa(merged["detected_a"], merged["detected_b"])

    rows: list[dict] = []
    for family, group in merged.groupby("family", sort=True):
        n_total = int(len(group))
        positive_a = int(group["detected_a"].sum())
        positive_b = int(group["detected_b"].sum())
        # Prevalence flag uses *either coder positive* — sensitive enough to
        # flag near-zero family even if only one coder marked anything.
        either_positive = int(((group["detected_a"]) | (group["detected_b"])).sum())
        value = _kappa(group["detected_a"], group["detected_b"])
        rows.append({
            "family": str(family),
            "n": n_total,
            "positive_a": positive_a,
            "positive_b": positive_b,
            "either_positive": either_positive,
            "kappa": value,
            "skipped_degenerate": value is None,
            "agreement_rate": float((group["detected_a"] == group["detected_b"]).mean()),
            "prevalence_flag": _prevalence_flag(either_positive, n_total),
        })
    per_family = pd.DataFrame(rows)

    # Sample composition diagnostics (cells = unique essay×trait pairs).
    unique_cells = merged.drop_duplicates(subset=["essay_id", "trait"])
    trait_cells = unique_cells.groupby("trait", sort=True).size().to_dict()
    analyzed_cov = {t: int(trait_cells.get(t, 0)) for t in ANALYZED_TRAITS}
    non_analyzed_cov = {
        t: int(n) for t, n in trait_cells.items() if t not in ANALYZED_TRAITS
    }

    # content_1 prevalence (§35.3 비판 1: F_LLM family vs content trait 의
    # 본질적 mismatch 가능성 진단). Two metrics — the warning trigger uses the
    # *cell-level* rate (cells where any family is either-positive), which is
    # the meaningful "can the detector find ANY family here" signal. The
    # decision-level rate (rows = cells × families) is reported alongside for
    # transparency but is a by-product of family-disjoint structure.
    content_1_rows = merged[merged["trait"] == "content_1"]
    content_1_decision_rate: float | None = None
    content_1_cell_rate: float | None = None
    content_1_warning = False
    if len(content_1_rows) > 0:
        # decision-level: rows (cells × families) with either coder positive
        either_pos_rows = ((content_1_rows["detected_a"]) | (content_1_rows["detected_b"])).sum()
        content_1_decision_rate = float(either_pos_rows) / float(len(content_1_rows))
        # cell-level: unique (essay_id) cells where ANY family is either-positive
        content_1_rows = content_1_rows.assign(
            _either=(content_1_rows["detected_a"] | content_1_rows["detected_b"])
        )
        per_cell_any = content_1_rows.groupby("essay_id")["_either"].any()
        content_1_cell_rate = float(per_cell_any.mean()) if len(per_cell_any) else 0.0
        # Trigger on cell-level (the diagnostic-meaningful metric)
        content_1_warning = content_1_cell_rate < CONTENT_1_WARN_THRESHOLD

    diagnostics = {
        "cell_count": int(len(unique_cells)),
        "family_count": int(per_family["family"].nunique()),
        "analyzed_coverage": analyzed_cov,
        "non_analyzed_coverage": non_analyzed_cov,
        "content_1_decision_rate": content_1_decision_rate,
        "content_1_cell_rate": content_1_cell_rate,
        "content_1_warning": content_1_warning,
    }
    return per_family, overall, diagnostics


def write_report(
    per_family: pd.DataFrame,
    overall: float | None,
    diagnostics: dict,
    out_path: Path,
    *,
    spotcheck_sections: list[str] | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    overall_text = "NA (degenerate prevalence)" if overall is None else f"{overall:.3f}"

    # --- Analyzed-trait coverage block ---
    analyzed = diagnostics.get("analyzed_coverage", {})
    cell_count = diagnostics.get("cell_count", 0)
    analyzed_total = sum(analyzed.values())
    coverage_lines = [
        f"- `{t}`: {analyzed.get(t, 0)} cells" for t in ANALYZED_TRAITS
    ]
    coverage_summary = (
        f"{analyzed_total} / {cell_count} cells "
        f"({analyzed_total / cell_count:.1%} of sample)"
        if cell_count else "no overlap"
    )

    lines = [
        "# Keyword Blind Audit",
        "",
        f"- Inter-coder Cohen kappa (descriptive only — NOT a validity gate; "
        f"F_LLM is deterministic): **{overall_text}**",
        f"- Total cells (unique essay × trait): {cell_count}",
        f"- Analyzed-trait coverage: {coverage_summary}",
        "",
    ]
    if spotcheck_sections:
        lines += spotcheck_sections
    lines += [
        "## Analyzed-Trait Coverage (P3-strict++ §35.3 비판 2 보강)",
        "",
        *coverage_lines,
        "",
    ]

    non_analyzed = diagnostics.get("non_analyzed_coverage", {})
    if non_analyzed:
        lines.append("Non-analyzed traits in sample (informational):")
        lines.extend([f"- `{t}`: {n} cells" for t, n in sorted(non_analyzed.items())])
        lines.append("")

    # --- Per-family κ table with degenerate flag ---
    display_cols = [
        "family", "n", "either_positive", "kappa",
        "skipped_degenerate", "agreement_rate", "prevalence_flag",
    ]
    table_df = per_family[display_cols].copy() if not per_family.empty else per_family
    lines += [
        "## Per-Family κ + Prevalence Flag (v2.6 §4.1.2.1 (d) 4번)",
        "",
        "Flag legend:",
        "- **DEGENERATE_ZERO**: 두 coder 모두 한 번도 detect 안 함. v2.6 §4.1.2.1 (d) 4번 'family detection 이 한 명도 안 한 경우 제외' → κ 산출 의미 없음.",
        "- **LOW_PREVALENCE** (< 20%): positive 가 sample 의 20% 미만. κ 계산 가능하나 noisy.",
        "- **INTERPRETABLE**: prevalence 충분, κ 직접 해석 가능.",
        "",
        table_df.to_markdown(index=False) if not table_df.empty else "(no families)",
        "",
    ]

    # --- content_1 warning block ---
    cell_rate = diagnostics.get("content_1_cell_rate")
    decision_rate = diagnostics.get("content_1_decision_rate")
    cell_str = f"{cell_rate:.2%}" if cell_rate is not None else "n/a"
    decision_str = f"{decision_rate:.2%}" if decision_rate is not None else "n/a"
    if diagnostics.get("content_1_warning"):
        lines += [
            "## ⚠️ content_1 Low-Prevalence Warning",
            "",
            f"- **Cell-level prevalence (trigger metric)**: {cell_str} "
            f"(content_1 cells 중 어느 family 라도 either-positive 인 cells 비율; "
            f"< {CONTENT_1_WARN_THRESHOLD:.0%} 임계 → trigger)",
            f"- Decision-level prevalence (참고): {decision_str} "
            f"(content_1 의 모든 row = cells × families 중 either-positive 비율)",
            "",
            "본 패턴은 **plan file §35.3 비판 1** (F_LLM family vs content trait "
            "의 본질적 mismatch 가능성) 의 실증 신호일 수 있음. 즉, v1.3 의 8 family "
            "가 모두 *형태계열* (meta/morph/lex/vocab/syn/case/dis_*) 인 반면, "
            "content_1 rationale 은 *내용적* 어휘 (\"설명 대상\", \"초점화\", "
            "\"체계적 분석\") 위주로 작성되어 family keyword 매칭이 본질적으로 "
            "낮음. dictionary 보강만으로는 한계 가능성이 있으며, P3-strict++ §35 의 "
            "4-way 분기 중 **'κ 높음 + content_1 0 지속 → metric design limitation "
            "(§11 신규 항목 검토)'** path 진입 후보.",
            "",
            "후속 결정: ",
            "- κ 높음 ∧ 본 경고 trigger → v2.6 §11 신규 limitation 추가 검토 + Phase 5 본 실행 진입 (P2 with caveat)",
            "- κ 낮음 ∧ 본 경고 trigger → keyword/instruction governance 재검토 (P1 path)",
            "",
        ]
    elif cell_rate is not None:
        lines += [
            "## content_1 Prevalence (informational)",
            "",
            f"- Cell-level prevalence: **{cell_str}** "
            f"(≥ {CONTENT_1_WARN_THRESHOLD:.0%} 임계, 정상 범위)",
            f"- Decision-level prevalence: {decision_str} (참고)",
            "",
        ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


def _default_machine_path(coder_a: Path) -> Path:
    """coders/coder_a.csv → ../analyst/machine_truth.csv."""
    return coder_a.parent.parent / "analyst" / "machine_truth.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coder-a", type=Path, required=True)
    parser.add_argument(
        "--coder-b", type=Path, default=None,
        help="Optional second annotator (inter-coder κ descriptive only).",
    )
    parser.add_argument(
        "--machine", type=Path, default=None,
        help="machine_truth.csv (default: <coder-a>/../../analyst/machine_truth.csv)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    coder_a = _load(args.coder_a, "A")
    coder_b = _load(args.coder_b, "B") if args.coder_b else None

    machine_path = args.machine or _default_machine_path(args.coder_a)
    machine = _load_machine(machine_path) if machine_path.exists() else None

    spotcheck_sections: list[str] = []
    if machine is not None:
        pf_a, pt_a, sum_a = compute_spotcheck(coder_a, machine)
        spotcheck_sections += _spotcheck_lines(pf_a, pt_a, sum_a, "Coder A")
        if coder_b is not None:
            pf_b, pt_b, sum_b = compute_spotcheck(coder_b, machine)
            spotcheck_sections += _spotcheck_lines(pf_b, pt_b, sum_b, "Coder B")
    else:
        spotcheck_sections += [
            "## ⚠️ Detector Spot-Check unavailable",
            "",
            f"machine_truth not found at `{machine_path}`. Run "
            "`python -m scripts.build_blind_audit_sample` (spotcheck mode) first.",
            "",
        ]

    if coder_b is not None:
        # Inter-coder κ is computed but reported as descriptive only (no gate).
        per_family, overall, diagnostics = compute_audit(coder_a, coder_b)
        write_report(
            per_family, overall, diagnostics, args.out,
            spotcheck_sections=spotcheck_sections,
        )
    else:
        write_spotcheck_only_report(spotcheck_sections, args.out)

    print(f"Wrote {args.out}")
    if machine is None:
        print(f"  (machine_truth absent at {machine_path} — spot-check skipped)")
    # Diagnostic tool: no κ pass/fail gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
