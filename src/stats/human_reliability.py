"""
Stage 1.1a — 인간 기준 신뢰도 사전 점검 (plan v2.3 §4.6.1).

Computes three diagnostics the decision_table_preregistered.md §3.3
Indeterminate-gate rule depends on:

    1. Per-trait inter-rater agreement (QWK, ICC(2,1), Spearman, exact/adjacent).
       Traits with QWK < 0.70 or ICC < 0.70 are candidates for more conservative
       Stage 5 interpretation.
    2. Per-trait feedback *purity* — fraction of feedback text whose lexical
       content aligns with the trait's rubric area vs. other areas. Cells with
       off-trait ratio ≥ 50% trigger decision_table §3.3.
    3. Missing data audit — score/feedback present/absent counts per
       (purpose × grade × prompt × trait).

Outputs:
    reports/stage1/human_reliability.md      — human-readable summary
    reports/stage1/rater_agreement.csv       — per (purpose, trait): QWK, ICC, etc.
    reports/stage1/feedback_purity.csv       — per (purpose, trait): purity stats
    reports/stage1/missingness.csv           — per (purpose, trait, grade): counts
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import PROJECT_ROOT, PURPOSES_IN_SCOPE, REPORTS_DIR, TRAITS

log = logging.getLogger(__name__)

OUT_DIR: Path = REPORTS_DIR / "stage1"
DATA_ROOT_ENV: str = "AES_DATA_ROOT"

ANALYTIC_TRAITS: tuple[str, ...] = tuple(t for t in TRAITS if t != "holistic")


# --- Keyword lists (purity heuristic v1) -----------------------------------
# Shared across 설명/설득 because rubric area labels are identical. Weighted
# neutrally — a mention counts as 1 regardless of specificity. Refinement
# into LLM-assisted coding is possible if needed; the simple version is
# conservative (more false flags than false clears).
TRAIT_AREA: dict[str, str] = {
    "task_1":         "task",
    "content_1":      "content",
    "content_2":      "content",
    "content_3":      "content",
    "organization_1": "organization",
    "organization_2": "organization",
    "expression_1":   "expression",
    "expression_2":   "expression",
}

AREA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "task": (
        "프롬프트", "과제", "요구", "맥락", "조건", "지시문", "수행",
        "충실", "탁월", "미흡", "반영",
    ),
    "content": (
        "내용", "설명", "주장", "논제", "근거", "구체", "세부", "예시",
        "사실", "정보", "적절", "관련", "부합", "대상", "초점", "명료",
        "통일", "일관", "주제", "화제",
    ),
    "organization": (
        "연결", "흐름", "전환", "구성", "문단", "서론", "본론", "결론",
        "구조", "체계", "조직", "단락",
    ),
    "expression": (
        "어휘", "단어", "표현", "어법", "맞춤법", "문법", "띄어쓰기",
        "문장", "표기", "어미", "조사",
    ),
}

# Convert to sets for O(1) lookup.
_AREA_KW_SETS: dict[str, set[str]] = {a: set(kws) for a, kws in AREA_KEYWORDS.items()}


# --- Data loading ----------------------------------------------------------
def _iter_essays(data_root: Path, purposes: tuple[str, ...] = PURPOSES_IN_SCOPE):
    """Yield parsed JSON dicts for every essay matching the purpose filter."""
    for p in data_root.rglob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        purpose = raw.get("essay_question", {}).get("purpose")
        if purpose not in purposes:
            continue
        yield raw


def load_scores_and_feedback(data_root: Path) -> pd.DataFrame:
    """Long-form: (essay_id, purpose, grade, prompt_id, trait, r1_score, r2_score, feedback)."""
    rows: list[dict] = []
    for raw in _iter_essays(data_root):
        eid = raw["essay_answer"]["id"]
        q = raw["essay_question"]
        analytic = (
            raw.get("score", {})
               .get("personal", {})
               .get("analytic", {})
        )
        for trait in ANALYTIC_TRAITS:
            d = analytic.get(trait, {})
            scores = d.get("score", [])
            r1 = scores[0] if len(scores) >= 1 else None
            r2 = scores[1] if len(scores) >= 2 else None
            rows.append({
                "essay_id":  int(eid),
                "purpose":   q.get("purpose"),
                "grade":     q.get("grade"),
                "prompt_id": q.get("id"),
                "trait":     trait,
                "r1_score":  r1,
                "r2_score":  r2,
                "feedback":  d.get("feedback", ""),
            })
    df = pd.DataFrame(rows)
    log.info("Loaded %d essay-trait rows across %d essays",
             len(df), df["essay_id"].nunique())
    return df


# --- Agreement metrics ----------------------------------------------------
def _qwk(r1: np.ndarray, r2: np.ndarray) -> float:
    """QWK via existing Stage 2.2 metrics module for consistency."""
    from src.models.metrics import regression_metrics
    m = regression_metrics(r1, r2)
    return float(m.get("qwk", float("nan")))


def _icc_2_1(ratings: np.ndarray) -> float:
    """ICC(2,1) — two-way random, absolute agreement, single rater.

    ``ratings`` shape (n_targets, k_raters), no NaN.
    """
    n, k = ratings.shape
    if n < 2 or k < 2:
        return float("nan")
    grand = ratings.mean()
    row_means = ratings.mean(axis=1)
    col_means = ratings.mean(axis=0)
    ss_total = float(((ratings - grand) ** 2).sum())
    ss_targets = float(k * ((row_means - grand) ** 2).sum())
    ss_raters  = float(n * ((col_means - grand) ** 2).sum())
    ss_error = ss_total - ss_targets - ss_raters
    ms_targets = ss_targets / (n - 1)
    ms_raters  = ss_raters  / (k - 1)
    ms_error   = ss_error   / ((n - 1) * (k - 1))
    denom = ms_targets + (k - 1) * ms_error + k * (ms_raters - ms_error) / n
    return (ms_targets - ms_error) / denom if denom else float("nan")


def _spearman(r1: np.ndarray, r2: np.ndarray) -> float:
    from scipy.stats import spearmanr
    try:
        rho, _ = spearmanr(r1, r2)
        return float(rho) if not np.isnan(rho) else float("nan")
    except Exception:
        return float("nan")


def compute_rater_agreement(long_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (purpose, trait), g in long_df.groupby(["purpose", "trait"], observed=True):
        both = g.dropna(subset=["r1_score", "r2_score"])
        if len(both) < 10:
            continue
        r1 = both["r1_score"].to_numpy(dtype=float)
        r2 = both["r2_score"].to_numpy(dtype=float)
        mat = np.stack([r1, r2], axis=1)
        diff = np.abs(r1 - r2)
        rows.append({
            "purpose": purpose,
            "trait": trait,
            "n_paired": int(len(both)),
            "qwk": _qwk(r1, r2),
            "icc_2_1": _icc_2_1(mat),
            "spearman_r": _spearman(r1, r2),
            "exact_agreement_rate": float((diff == 0).mean()),
            "adjacent_agreement_rate": float((diff <= 1).mean()),
            "mean_abs_diff": float(diff.mean()),
            "r1_mean": float(r1.mean()),
            "r2_mean": float(r2.mean()),
            "severity_shift_r2_minus_r1": float((r2 - r1).mean()),
            "qwk_below_0_70": bool(_qwk(r1, r2) < 0.70),
            "icc_below_0_70": bool(_icc_2_1(mat) < 0.70),
        })
    return pd.DataFrame(rows)


# --- Feedback purity heuristic --------------------------------------------
def _count_area_mentions(text: str) -> dict[str, int]:
    """For each rubric area, count keyword occurrences in ``text``.

    Matches substring (not word-boundary) because Korean lacks whitespace
    consistency. Each keyword counted once per occurrence.
    """
    counts = {area: 0 for area in _AREA_KW_SETS}
    if not text:
        return counts
    for area, kws in _AREA_KW_SETS.items():
        for kw in kws:
            # simple substring count
            if kw in text:
                counts[area] += text.count(kw)
    return counts


def compute_feedback_purity(long_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, r in long_df.iterrows():
        fb = str(r.get("feedback", "") or "")
        if not fb.strip():
            continue
        counts = _count_area_mentions(fb)
        total = sum(counts.values())
        if total == 0:
            continue
        trait = r["trait"]
        on_area = TRAIT_AREA[trait]
        on_hits = counts[on_area]
        off_hits = total - on_hits
        rows.append({
            "essay_id": int(r["essay_id"]),
            "purpose":  r["purpose"],
            "grade":    r["grade"],
            "prompt_id": r["prompt_id"],
            "trait":    trait,
            "on_area":  on_area,
            "total_mentions": int(total),
            "on_area_mentions": int(on_hits),
            "off_area_mentions": int(off_hits),
            "off_area_ratio": float(off_hits / total),
            "impure_50pct":  bool(off_hits / total >= 0.50),
        })
    df = pd.DataFrame(rows)
    return df


def summarize_purity(purity_df: pd.DataFrame) -> pd.DataFrame:
    summ: list[dict] = []
    for (purpose, trait), g in purity_df.groupby(["purpose", "trait"], observed=True):
        summ.append({
            "purpose": purpose,
            "trait":   trait,
            "n_feedbacks":         int(len(g)),
            "mean_off_area_ratio": float(g["off_area_ratio"].mean()),
            "median_off_area_ratio": float(g["off_area_ratio"].median()),
            "pct_impure_50":       float((g["impure_50pct"]).mean() * 100),
            "mean_total_mentions": float(g["total_mentions"].mean()),
        })
    return pd.DataFrame(summ)


# --- Missingness ----------------------------------------------------------
def compute_missingness(long_df: pd.DataFrame) -> pd.DataFrame:
    long_df = long_df.copy()
    long_df["score_missing"] = long_df[["r1_score", "r2_score"]].isna().any(axis=1)
    long_df["feedback_missing"] = (
        long_df["feedback"].fillna("").str.strip().eq("")
    )
    rows: list[dict] = []
    for (purpose, trait, grade), g in long_df.groupby(
        ["purpose", "trait", "grade"], observed=True
    ):
        rows.append({
            "purpose": purpose,
            "trait":   trait,
            "grade":   grade,
            "n":       int(len(g)),
            "n_score_missing":    int(g["score_missing"].sum()),
            "n_feedback_missing": int(g["feedback_missing"].sum()),
            "pct_score_missing":    float(g["score_missing"].mean() * 100),
            "pct_feedback_missing": float(g["feedback_missing"].mean() * 100),
        })
    return pd.DataFrame(rows)


# --- Report writer --------------------------------------------------------
def write_markdown_report(
    agree_df: pd.DataFrame,
    purity_df: pd.DataFrame,
    miss_df: pd.DataFrame,
    out_path: Path,
) -> None:
    lines: list[str] = [
        "# Stage 1.1a — 인간 기준 신뢰도 사전 점검",
        "",
        "v2.3 §4.6.1 · decision_table_preregistered.md §3.3 판정 근거. "
        "본 리포트는 Stage 5 Indeterminate 귀속 판단에 직접 투입된다.",
        "",
        f"**생성 일자**: {pd.Timestamp.utcnow().isoformat(timespec='seconds')} UTC",
        "",
        "---",
        "",
        "## 1. 2-rater 점수 일치도 (per purpose × trait)",
        "",
        "QWK·ICC(2,1)·Spearman ρ·exact/adjacent agreement. v2.3 §4.6.1의 "
        "해석 완화 임계치는 **QWK < 0.70 또는 ICC < 0.70**.",
        "",
        agree_df.to_markdown(index=False, floatfmt=".3f"),
        "",
        "### 1-a. 임계치 미달 trait",
        "",
    ]
    flagged = agree_df[agree_df["qwk_below_0_70"] | agree_df["icc_below_0_70"]]
    if flagged.empty:
        lines.append("_해당 없음 — 전 trait가 QWK ≥ 0.70 AND ICC ≥ 0.70._")
    else:
        lines.append(
            flagged[[
                "purpose", "trait", "n_paired", "qwk", "icc_2_1",
                "qwk_below_0_70", "icc_below_0_70",
            ]].to_markdown(index=False, floatfmt=".3f")
        )
    lines += [
        "",
        "---",
        "",
        "## 2. 피드백 trait 순수성 (키워드 기반 heuristic v1)",
        "",
        "각 (essay, trait) 피드백 텍스트에서 rubric 영역(task / content / "
        "organization / expression)별 키워드 출현 수를 세고, 해당 trait의 "
        "영역 이외 키워드가 차지하는 비율을 `off_area_ratio`로 정의. "
        "`decision_table §3.3`의 **피드백 순수성 50% 임계치**는 "
        "off_area_ratio ≥ 0.50 cell 비율. 이 비율이 높을수록 해당 (purpose, "
        "trait)의 인간 피드백은 trait 경계 넘나듦이 크므로 Stage 5에서 인간 "
        "피드백의 해석 무게를 낮춘다.",
        "",
        "**한계**: 키워드 매칭은 단순 heuristic. 동일 단어가 다중 해석되는 "
        "경우 (예: '내용'은 content만이 아니라 task 맥락에서도 등장) 과소/"
        "과대 추정 가능. 정밀화는 LLM-assisted coding으로 추후 개선 가능.",
        "",
        summarize_purity(purity_df).to_markdown(index=False, floatfmt=".3f"),
        "",
        "---",
        "",
        "## 3. 결측 패턴",
        "",
        "per purpose × trait × grade — 점수 2인 중 하나라도 결측 OR 피드백 공란.",
        "",
        miss_df.to_markdown(index=False, floatfmt=".2f"),
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s", out_path)


# --- Orchestration --------------------------------------------------------
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data_root = Path(os.environ.get(DATA_ROOT_ENV, PROJECT_ROOT / "dataset"))
    if not data_root.exists():
        log.error("Data root not found: %s  (set %s)", data_root, DATA_ROOT_ENV)
        return 1

    long_df = load_scores_and_feedback(data_root)

    agree_df = compute_rater_agreement(long_df)
    agree_df.to_csv(OUT_DIR / "rater_agreement.csv", index=False)
    log.info("Wrote rater_agreement.csv (%d rows)", len(agree_df))

    purity_df = compute_feedback_purity(long_df)
    purity_df.to_csv(OUT_DIR / "feedback_purity.csv", index=False)
    log.info("Wrote feedback_purity.csv (%d rows)", len(purity_df))

    miss_df = compute_missingness(long_df)
    miss_df.to_csv(OUT_DIR / "missingness.csv", index=False)
    log.info("Wrote missingness.csv (%d rows)", len(miss_df))

    write_markdown_report(
        agree_df, purity_df, miss_df,
        out_path=OUT_DIR / "human_reliability.md",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
