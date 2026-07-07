"""
Stage 5 analysis orchestration — Main run 결과 종합 분석.

stats/alignment 모듈은 CLI entrypoint 미정의이므로 본 스크립트가 import +
순차 호출 + 결과 통합 markdown 작성을 담당. 모듈 코드는 무변경.

Pipeline:
    1. score-level QWK (per-trait, per-purpose) — Stage 2.2 OOF vs Stage 4 Stage B
    2. Headline variant (V1/V2/V3) — QWK ≥ 0.50 임계
    3. F_SHAP × F_LLM Jaccard alignment (essay × trait) per purpose
    4. axes (f)(g)(h) — analyzed trait family detection 분포
    5. Main contrast 통계 — Friedman → Holm-2 Wilcoxon + purpose direction gate

Outputs:
    - reports/stage5_alignment/jaccard__{purpose}.parquet  (per purpose)
    - reports/stage5_alignment/main_contrast_summary.md    (종합 본문)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd

from configs.paths import PURPOSES_IN_SCOPE, REPORTS_DIR
from src.alignment.jaccard_metric import (
    build_alignment_metric_for_purpose,
    write_alignment_metric,
)
from src.stats.headline_variant_selector import select_headline_variant
from src.stats.score_level_qwk import compute_score_qwk_for_purpose
from src.stats.trait_type_contrast import analyze_trait_type_contrast
from scripts.llm_family_smoke_audit import compute_metric_gates, ANALYZED_TRAITS

log = logging.getLogger(__name__)

MAIN_DIR = REPORTS_DIR / "stage4_llm" / "main"
STAGE5_DIR = REPORTS_DIR / "stage5_alignment"
OUT_MD = STAGE5_DIR / "main_contrast_summary.md"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    STAGE5_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Step 1: per-purpose score-level QWK ────────────────────────────────
    qwk_rows: list[pd.DataFrame] = []
    for purpose in PURPOSES_IN_SCOPE:
        stage_b_path = MAIN_DIR / "B" / f"{purpose}.jsonl"
        log.info("computing score QWK for %s (stage_b=%s)", purpose, stage_b_path)
        df = compute_score_qwk_for_purpose(purpose, stage_b_path=stage_b_path)
        df["purpose"] = purpose
        qwk_rows.append(df)
    qwk_df = pd.concat(qwk_rows, ignore_index=True)
    log.info("QWK rows: %d", len(qwk_df))

    # ─── Step 2: headline variant (V1/V2/V3) ────────────────────────────────
    headline = select_headline_variant(qwk_df, threshold=0.5)
    log.info("headline variant: %s", headline)

    # ─── Step 3 & 4: Jaccard alignment + axes (f)(g)(h) per purpose ─────────
    alignment_per_purpose: dict[str, pd.DataFrame] = {}
    gates_per_purpose: dict[str, dict] = {}
    for purpose in PURPOSES_IN_SCOPE:
        stage_c_path = MAIN_DIR / "C" / f"{purpose}.jsonl"
        log.info("building alignment metric for %s", purpose)
        align_df = build_alignment_metric_for_purpose(
            purpose, stage_c_path=stage_c_path,
        )
        align_df["purpose"] = purpose
        alignment_per_purpose[purpose] = align_df
        # write per-purpose parquet
        out_path = write_alignment_metric(align_df, purpose, out_dir=STAGE5_DIR)
        log.info("wrote %s (%d rows)", out_path, len(align_df))

        # axes (f)(g)(h): need raw llm_sets DataFrame for compute_metric_gates,
        # which expects columns (trait, llm_families, llm_family_empty).
        from src.alignment.llm_family_detector import load_stage_c_family_sets
        llm_sets = load_stage_c_family_sets(stage_c_path)
        gates = compute_metric_gates(llm_sets, alignment_df=align_df)
        gates_per_purpose[purpose] = gates

    # ─── Step 5: main contrast — Friedman + Wilcoxon + Holm-2 ───────────────
    all_alignment = pd.concat(alignment_per_purpose.values(), ignore_index=True)
    contrast = analyze_trait_type_contrast(all_alignment)
    log.info("contrast keys: %s", list(contrast.keys()))

    # ─── Markdown summary ───────────────────────────────────────────────────
    lines: list[str] = [
        "# Main Contrast Summary — Stage 5 analysis (2026-06-01)",
        "",
        "**입력**: Stage 4 main 결과 (`reports/stage4_llm/main/{B,C}/{설명,설득}.jsonl`)",
        " + Stage 2.2 OOF + Stage 3 SHAP.",
        "**총 essay**: 4,860 (설명 2,709 + 설득 2,151), validator full-sweep pass.",
        "**α pilot**: 보류 (decision_history.md 2026-06-01 entry; §6 참조).",
        "",
        "## 0. Framing notes (본문 작성 규약, 표·통계 해석 전 필독)",
        "",
        "- **`r = 0.981` 은 rank / direction 신호가 강하다는 뜻이지, absolute "
        "alignment 가 높다는 뜻이 아니다.** medians 가 모두 0 이므로 본문은 "
        "nonzero / rank pattern 중심 (§5 Descriptive robustness 참조).",
        "- 본문 claim = **form-family operational alignment** 의 nonzero / rank "
        "pattern. \"strong absolute alignment\" 표현은 금지.",
        "- **`strong_claim` / `purpose_gate` FAIL 은 숨기지 않음**: 사전등록 strong "
        "wording 미채택; **V3 / caveated wording 채택** (medians=0 + "
        "purpose_gate FAIL 명시).",
        "",
        "## 1. Score-level QWK (Stage 2.2 OOF vs Stage 4 Stage B)",
        "",
        qwk_df.to_markdown(index=False),
        "",
        f"**Headline variant**: **{getattr(headline, 'variant', headline)}** ",
        f"(threshold = QWK ≥ 0.50; "
        f"per-trait pass: {getattr(headline, 'per_trait_pass', '?')})",
        "",
        "## 2. Axes (f)(g)(h) — analyzed-trait family detection gates",
        "",
    ]
    for purpose, gates in gates_per_purpose.items():
        median_a = gates["median_a"]
        std_a = gates["std_a"]
        median_str = f"{median_a:.3f}" if median_a is not None else "NA"
        std_str = f"{std_a:.3f}" if std_a is not None else "NA"
        lines.append(f"### {purpose}")
        lines.append("")
        lines.append(
            f"- (f) non-empty rate: **{'PASS' if gates['axis_f_pass'] else 'FAIL'}** "
            f"(임계 ≥ 0.80, analyzed traits)"
        )
        lines.append(
            f"- (g) max family share: **{'PASS' if gates['axis_g_pass'] else 'FAIL'}** "
            f"(max = {gates['max_family_share']:.3f}, 임계 < 0.50)"
        )
        lines.append(
            f"- (h) Jaccard median: **{'PASS' if gates['axis_h_pass'] else 'FAIL'}** "
            f"(median = {median_str}, std = {std_str}; "
            f"임계 ∈ [0.10, 0.70], std > 0.05)"
        )
        lines.append("")
        lines.append("**per-trait non-empty rate**:")
        lines.append("")
        lines.append(gates["gate_trait_rates"].to_markdown(index=False))
        lines.append("")

    lines.extend([
        "## 3. Main contrast — Surface vs Content (Holm-2)",
        "",
    ])
    # Skip 'wide' (per-essay dump, 4,860 rows — saved separately via parquet);
    # only emit the statistical summary tables.
    for key, val in contrast.items():
        if key == "wide":
            lines.append(f"### {key} (full table omitted — see "
                         f"`reports/stage5_alignment/jaccard_alignment__*.parquet`)")
            lines.append("")
            if isinstance(val, pd.DataFrame):
                lines.append(f"shape = {val.shape}; columns = {list(val.columns)}")
                lines.append("")
            continue
        lines.append(f"### {key}")
        lines.append("")
        if isinstance(val, pd.DataFrame):
            lines.append(val.to_markdown(index=False))
        else:
            lines.append(f"```\n{val}\n```")
        lines.append("")

    lines.extend([
        "## 4. Alignment distribution summary (per purpose, analyzed traits)",
        "",
    ])
    for purpose, align_df in alignment_per_purpose.items():
        ana = align_df[align_df["trait"].isin(ANALYZED_TRAITS)]
        summary = (
            ana.groupby("trait")["jaccard"]
            .agg(["count", "mean", "median", "std"])
            .reset_index()
        )
        lines.append(f"### {purpose}")
        lines.append("")
        lines.append(summary.to_markdown(index=False))
        lines.append("")

    # ─── §5 Descriptive robustness — 0 포함 비율 + paired direction 비율 ────
    wide = contrast["wide"]  # essay_id, purpose, content, discourse, surface
    TRAIT_TYPE_COLS = [
        ("surface", "Surface (expression_2)"),
        ("discourse", "Discourse (organization_1)"),
        ("content", "Content (content_1)"),
    ]

    lines.extend([
        "## 5. Descriptive robustness (median=0 환경 보강 — 0 포함 비율 핵심)",
        "",
        "본 §3 의 통계는 `r` 가 높지만 medians 가 모두 0. 본 §5 는 그 분포 구조를 "
        "**positive / zero / negative 비율** 과 quantile 로 직접 노출. 본문은 "
        "이 표들의 nonzero / rank pattern 을 가지고 form-family operational "
        "alignment 의 비대칭을 기술해야 함 (§0 framing).",
        "",
    ])

    # 5.1 Nonzero/zero breakdown per (purpose, trait_type)
    lines.extend(["### 5.1 Nonzero / zero breakdown per (purpose, trait_type)", ""])
    rows = []
    for purpose, sub in wide.groupby("purpose", sort=False):
        n = len(sub)
        for col, label in TRAIT_TYPE_COLS:
            v = sub[col]
            pos = int((v > 0).sum()); zero = int((v == 0).sum())
            rows.append({
                "purpose": purpose, "trait_type": label, "n": n,
                "positive (>0)": pos, "% positive": f"{100*pos/n:.1f}%",
                "zero (=0)": zero,    "% zero":     f"{100*zero/n:.1f}%",
            })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")

    # 5.2 Paired difference distribution
    lines.extend(["### 5.2 Paired difference distribution (per essay Δ)", ""])
    rows = []
    for label, left, right in [("Surface − Content", "surface", "content"),
                                ("Discourse − Content", "discourse", "content")]:
        for purpose, sub in wide.groupby("purpose", sort=False):
            d = sub[left] - sub[right]
            n = len(d)
            pos = int((d > 0).sum()); zero = int((d == 0).sum()); neg = int((d < 0).sum())
            rows.append({
                "contrast": label, "purpose": purpose, "n": n,
                "+ (left>right)": f"{pos} ({100*pos/n:.1f}%)",
                "0 (=)":          f"{zero} ({100*zero/n:.1f}%)",
                "− (left<right)": f"{neg} ({100*neg/n:.1f}%)",
                "mean Δ":   f"{d.mean():.4f}",
                "median Δ": f"{d.median():.4f}",
                "p25":      f"{d.quantile(0.25):.4f}",
                "p75":      f"{d.quantile(0.75):.4f}",
                "p95":      f"{d.quantile(0.95):.4f}",
            })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")

    # 5.3 Purpose direction consistency (Surface vs Content per essay)
    lines.extend([
        "### 5.3 Purpose direction consistency (essay 단위 비교, NOT median 비교)",
        "",
    ])
    rows = []
    for label, left, right in [("Surface vs Content", "surface", "content"),
                                ("Discourse vs Content", "discourse", "content")]:
        for purpose, sub in wide.groupby("purpose", sort=False):
            n = len(sub)
            gt = int((sub[left] >  sub[right]).sum())
            eq = int((sub[left] == sub[right]).sum())
            lt = int((sub[left] <  sub[right]).sum())
            rows.append({
                "comparison": label, "purpose": purpose, "n": n,
                "left > right": f"{gt} ({100*gt/n:.1f}%)",
                "left = right": f"{eq} ({100*eq/n:.1f}%)",
                "left < right": f"{lt} ({100*lt/n:.1f}%)",
            })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")

    # 5.4 Trait-type Jaccard quantiles
    lines.extend(["### 5.4 Trait-type Jaccard quantiles", ""])
    rows = []
    for purpose, sub in wide.groupby("purpose", sort=False):
        for col, label in TRAIT_TYPE_COLS:
            v = sub[col]
            rows.append({
                "purpose": purpose, "trait_type": label,
                "q25":         f"{v.quantile(0.25):.4f}",
                "q50 (median)":f"{v.quantile(0.50):.4f}",
                "q75":         f"{v.quantile(0.75):.4f}",
                "q90":         f"{v.quantile(0.90):.4f}",
                "q95":         f"{v.quantile(0.95):.4f}",
            })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")

    # ─── §6 α pilot — 정식 보류 결정 (was §5) ───────────────────────────────
    lines.extend([
        "## 6. α pilot 판단 — **정식 보류 (2026-06-01)**",
        "",
        "**결정**: α pilot **보류** (생략 아님 — 후속/보조 분석으로 defer). 사전등록 "
        "의도 (v2.3 §4.3.2 Krippendorff α pilot) 는 보존. 결정문 정식 audit: "
        "`decision_history.md` 2026-06-01 entry.",
        "",
        "**lock 문장**: \"α pilot deferred: null trigger 미충족, V3 해결 불가, "
        "main contrast 는 V3/median-zero caveat 가 붙은 form-family operational "
        "claim 으로 보고한다.\"",
        "",
        "**근거**:",
        "- Stage B null score per-trait: max **3.8% (expression_2, 설명)** — 원 α "
        "pilot trigger 임계 (>10%) 미달.",
        "- V3 headline 문제는 α pilot 으로 해결 안 됨 (α pilot 은 Sonnet 자체 반복 "
        "안정성을 측정; V3 는 XGBoost OOF ↔ Sonnet score-level mismatch).",
        "- Stage C empty rationale per-trait: **0%** (전 trait).",
        "- 자세한 null/empty 분포: `reports/stage4_llm/main/quality_report.md` §8-9.",
        "- 분포 구조 (positive / zero / negative 비율 + quantile): 본 §5.",
    ])

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("wrote %s", OUT_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
