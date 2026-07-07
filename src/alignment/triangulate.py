"""
Stage 6 — 3-way triangulation (Supplementary only under v2.6).

**v2.6 framework 위치**: Supplementary 전용. 본 plan §1.1 의 main contrast
(Surface > Content SHAP-LLM Jaccard) 는 ``src/stats/trait_type_contrast.py`` 가
담당. 본 모듈은 부록 D-1/D-2 + Discussion supplementary 보고용으로만 사용.

**Deprecated frame (legacy reference)**: v2.3 §5.4 의 RQ3 ("인간 피드백과의
삼각검증 결과, SHAP 귀인과 LLM rationale 중 인간 피드백과 더 높은 수렴을
보이는 설명 체계는 루브릭 영역별로 어떻게 분포하는가?") 에 대응했으나, v2.6
§2.6 + §16 에서 broad triangulation claim 본문 사용 금지 + RQ3 폐기. 본 모듈의
module-level 산출물 (per_cell_agreement, per_trait_convergence,
per_domain_convergence) 은 보존하되 본문 핵심 기여 문장에서 인용 금지.

Design principle (legacy reference, v2.3 §5.4): human feedback is treated as a
**fallible evidence source** rather than ground truth. Per Stage 1.1a
(2026-04-24 실측):
    - 14/16 trait QWK < 0.70 → 2-rater score 신뢰도 제한적
    - task_1 / organization_2 feedback 90%+ impure → trait 경계 모호
Accordingly, this module produces BOTH unweighted and fallibility-weighted
triangulation. v2.6 framework: weighted / unweighted 모두 supplementary
(부록 D-1/D-2) 보고용 — main paper primary 사용 금지 (v2.6 §5.2 mixed model
부록 D 격하와 동일).

Inputs (all produced by earlier stages):
    1. Stage 5 `matrix.py` labeled alignment matrix (essay × trait)
    2. Stage 4.3 coding of LLM rationale and human feedback (4-level)
    3. Stage 3 family rank tables (primary + robust_1)
    4. Stage 1.1a rater_agreement.csv + feedback_purity.csv

Outputs (Supplementary only):
    reports/stage6_triangulation/per_cell_agreement.parquet
    reports/stage6_triangulation/per_trait_convergence.csv
    reports/stage6_triangulation/per_domain_convergence.csv
    reports/stage6_triangulation/supplementary_convergence.md
    (v2.6 framework change: rq3_answer.md → supplementary_convergence.md.
    ``write_rq3_summary`` is retained as a deprecated alias for backward
    compatibility.)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import PROJECT_ROOT, PURPOSES_IN_SCOPE, REPORTS_DIR, TRAITS
from configs.shap import JACCARD_TOP_K
from src.coding.scheme import CODE_TO_LEVEL, INDETERMINATE
from src.data.rubric import RUBRIC_AREA_FROM_TRAIT

log = logging.getLogger(__name__)

ANALYTIC_TRAITS: tuple[str, ...] = tuple(t for t in TRAITS if t != "holistic")
OUT_DIR: Path = REPORTS_DIR / "stage6_triangulation"

STAGE1_DIR: Path = REPORTS_DIR / "stage1"
STAGE3_DIR: Path = REPORTS_DIR / "stage3_shap"
STAGE4_DIR: Path = REPORTS_DIR / "stage4_llm"
STAGE5_DIR: Path = REPORTS_DIR / "stage5_alignment"


# --- Inputs ---------------------------------------------------------------
def load_stage5_matrix(purpose: str) -> pd.DataFrame:
    p = STAGE5_DIR / f"matrix__{purpose}.parquet"
    if not p.exists():
        raise FileNotFoundError(
            f"Stage 5 matrix missing for {purpose}: {p}. "
            f"Run src.alignment.matrix.build_matrix first."
        )
    return pd.read_parquet(p)


def load_shap_top_families(purpose: str, embedding: str = "primary") -> dict[str, list[str]]:
    from src.alignment.matrix import load_shap_top_families as _load
    return dict(zip(_load(purpose, embedding=embedding, k=JACCARD_TOP_K)["trait"],
                    _load(purpose, embedding=embedding, k=JACCARD_TOP_K)["top_families"]))


def load_coding_long(purpose: str, source: str) -> pd.DataFrame:
    """Stage 4.3 coding — ``source`` ∈ {"llm", "human"}.

    Expected columns: essay_id, trait, code (상/중/하/NA), optional
    mapped_family_list (pipe-separated families the coder identified the
    rationale/feedback as pointing to).
    """
    assert source in ("llm", "human")
    p = STAGE4_DIR / "coding" / f"{source}_coding__{purpose}.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"Stage 4.3 {source} coding missing for {purpose}: {p}. "
            f"Requires 4-level coding by 2-3 coders before Stage 6 runs."
        )
    return pd.read_csv(p)


def load_stage1_reliability() -> tuple[pd.DataFrame, pd.DataFrame]:
    ra = pd.read_csv(STAGE1_DIR / "rater_agreement.csv")
    fp = pd.read_csv(STAGE1_DIR / "feedback_purity.csv")
    return ra, fp


# --- Fallibility weights (§5.4) ------------------------------------------
def compute_trait_reliability_weight(rater_df: pd.DataFrame) -> pd.DataFrame:
    """Per (purpose, trait) reliability weight from Stage 1.1a QWK.

    Mapping: w_reliability = clip(QWK / 0.70, 0.20, 1.00)
        - QWK = 0.70+ → weight = 1.0 (fully trusted)
        - QWK = 0.14 → weight = 0.20 (floor, still contributes)
        - QWK < 0 (pathological) → weight = 0.20
    The 0.70 anchor matches v2.3 §4.6.1's decision threshold.
    """
    r = rater_df[["purpose", "trait", "qwk"]].copy()
    r["w_reliability"] = np.clip(r["qwk"].fillna(0.0) / 0.70, 0.20, 1.00)
    return r


def compute_cell_purity_weight(feedback_df: pd.DataFrame) -> pd.DataFrame:
    """Per (essay_id, purpose, trait) purity weight from Stage 1.1a.

    Mapping: w_purity = 1 - off_area_ratio
        - on-topic feedback (off_area_ratio=0) → weight = 1.0
        - heavily off-topic (0.9) → weight = 0.1
    Purity is cell-level (not trait-level) because it varies per essay.
    Combined trait-level weight: w = w_reliability × mean(w_purity over cells).
    """
    p = feedback_df[["essay_id", "purpose", "trait", "off_area_ratio"]].copy()
    p["w_purity"] = 1.0 - p["off_area_ratio"].clip(0.0, 1.0)
    return p


# --- Agreement metrics on 4-level codes ----------------------------------
def _linear_weighted_kappa_4level(a: list[str], b: list[str]) -> float:
    """Weighted κ on 4-level (상/중/하/NA) codes with NA as separate category.

    We apply linear weights on the 상>중>하 ordinal direction; NA is treated
    as an unordered category (receives no partial credit when mismatched).
    """
    if not a or len(a) != len(b):
        return float("nan")
    # Map to numeric: NA=-1 (separate category), 하=0, 중=1, 상=2
    def _m(c: str) -> int:
        return CODE_TO_LEVEL[c] if c in CODE_TO_LEVEL and CODE_TO_LEVEL[c] is not None else -1
    a_n = np.array([_m(x) for x in a])
    b_n = np.array([_m(x) for x in b])
    categories = [-1, 0, 1, 2]
    n = len(a_n)
    if n == 0:
        return float("nan")
    # Observed and expected disagreement matrices.
    w = np.zeros((4, 4))
    for i, ci in enumerate(categories):
        for j, cj in enumerate(categories):
            if ci == -1 or cj == -1:
                # NA mismatch = maximal disagreement; NA match = 0 (handled below)
                w[i, j] = 0.0 if ci == cj else 1.0
            else:
                w[i, j] = abs(ci - cj) / 2.0  # normalized to [0, 1] on 3-point ordinal
    obs = np.zeros((4, 4))
    for ai, bi in zip(a_n, b_n):
        obs[categories.index(ai), categories.index(bi)] += 1
    obs /= n
    marginal_a = obs.sum(axis=1)
    marginal_b = obs.sum(axis=0)
    exp = np.outer(marginal_a, marginal_b)
    num = float((w * obs).sum())
    den = float((w * exp).sum())
    if den == 0:
        return float("nan")
    return 1.0 - (num / den)


def compute_shap_human_agreement(
    shap_top: dict[str, list[str]],
    human_mapped_families: pd.DataFrame,
) -> pd.DataFrame:
    """Per-trait Jaccard between SHAP Top-3 family set and the set of families
    mentioned in human feedback (via Stage 4.3 coding `mapped_family_list`).

    Expected ``human_mapped_families`` columns: essay_id, trait,
    mapped_family_list (pipe-separated). Essays without mapping contribute NaN.
    """
    rows = []
    for trait, top_list in shap_top.items():
        shap_set = set(top_list)
        sub = human_mapped_families[human_mapped_families["trait"] == trait]
        per_essay_jac: list[float] = []
        for _, r in sub.iterrows():
            fams = str(r.get("mapped_family_list", "") or "").split("|")
            fams = set(f.strip() for f in fams if f.strip())
            if not fams:
                continue
            union = shap_set | fams
            inter = shap_set & fams
            per_essay_jac.append(len(inter) / len(union) if union else np.nan)
        if per_essay_jac:
            rows.append({
                "trait": trait,
                "n_essays_with_mapping": len(per_essay_jac),
                "jaccard_mean_shap_human": float(np.nanmean(per_essay_jac)),
                "jaccard_median_shap_human": float(np.nanmedian(per_essay_jac)),
            })
    return pd.DataFrame(rows)


def compute_llm_human_agreement(
    llm_codes: pd.DataFrame,
    human_codes: pd.DataFrame,
) -> pd.DataFrame:
    """Per-trait weighted κ between LLM rationale coding and human feedback coding.

    Both dfs expected to have columns: essay_id, trait, code.
    """
    merged = llm_codes.merge(
        human_codes, on=["essay_id", "trait"], suffixes=("_llm", "_human"),
        validate="one_to_one",
    )
    rows = []
    for trait, sub in merged.groupby("trait"):
        if len(sub) < 10:
            continue
        kappa = _linear_weighted_kappa_4level(
            sub["code_llm"].tolist(), sub["code_human"].tolist(),
        )
        # Compare also label distribution shift (for descriptive)
        dist_llm = sub["code_llm"].value_counts(normalize=True).to_dict()
        dist_human = sub["code_human"].value_counts(normalize=True).to_dict()
        rows.append({
            "trait": trait,
            "n": len(sub),
            "kappa_llm_human": kappa,
            "na_rate_llm": float(dist_llm.get(INDETERMINATE, 0.0)),
            "na_rate_human": float(dist_human.get(INDETERMINATE, 0.0)),
        })
    return pd.DataFrame(rows)


def compute_shap_llm_agreement(
    shap_top: dict[str, list[str]],
    llm_mapped_families: pd.DataFrame,
) -> pd.DataFrame:
    """Per-trait Jaccard on SHAP Top-3 vs LLM rationale's referenced families.

    Same shape as compute_shap_human_agreement but with LLM-side mapping.
    """
    return _compute_family_jaccard(shap_top, llm_mapped_families, system="llm")


def _compute_family_jaccard(
    shap_top: dict[str, list[str]],
    mapped_df: pd.DataFrame,
    *,
    system: str,
) -> pd.DataFrame:
    rows = []
    for trait, top_list in shap_top.items():
        shap_set = set(top_list)
        sub = mapped_df[mapped_df["trait"] == trait]
        per_essay_jac: list[float] = []
        for _, r in sub.iterrows():
            fams = str(r.get("mapped_family_list", "") or "").split("|")
            fams = set(f.strip() for f in fams if f.strip())
            if not fams:
                continue
            union = shap_set | fams
            inter = shap_set & fams
            per_essay_jac.append(len(inter) / len(union) if union else np.nan)
        if per_essay_jac:
            rows.append({
                "trait": trait,
                "system": system,
                "n_essays_with_mapping": len(per_essay_jac),
                f"jaccard_mean_shap_{system}": float(np.nanmean(per_essay_jac)),
                f"jaccard_median_shap_{system}": float(np.nanmedian(per_essay_jac)),
            })
    return pd.DataFrame(rows)


# --- Convergence ranking per rubric domain (Supplementary only) ----------
@dataclass(frozen=True)
class DomainConvergence:
    purpose: str
    rubric_domain: str
    n_traits: int
    shap_human_agreement: float
    llm_human_agreement: float
    shap_llm_agreement: float
    closer_to_human: str                # "SHAP" | "LLM" | "tied"
    margin: float                        # |shap_human - llm_human|
    weighted_closer_to_human: str        # after fallibility re-weighting
    weighted_margin: float


def aggregate_per_domain(
    purpose: str,
    trait_agreements: pd.DataFrame,
    trait_weights: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate per-trait agreements to rubric domain (1A/1B/1C/1D).

    Reports BOTH unweighted and fallibility-weighted convergence. v2.6 framework:
    본 산출물은 부록 D supplementary. 본문 main contrast (Surface > Content) 는
    ``src/stats/trait_type_contrast.py`` 가 담당. weighted / unweighted 모두
    부록 D-1/D-2 supplementary 보고용.

    Required columns in ``trait_agreements``:
        trait, jaccard_mean_shap_human, jaccard_mean_shap_llm, kappa_llm_human
    """
    df = trait_agreements.copy()
    df["rubric_domain"] = df["trait"].map(RUBRIC_AREA_FROM_TRAIT)
    df = df.merge(
        trait_weights[["trait", "w_reliability"]],
        on="trait", how="left",
    )
    out_rows: list[dict] = []
    for domain, sub in df.groupby("rubric_domain"):
        w = sub["w_reliability"].fillna(1.0).to_numpy()
        sh_hu = sub["jaccard_mean_shap_human"].to_numpy()
        ll_hu_k = sub["kappa_llm_human"].to_numpy()
        sh_ll = sub.get("jaccard_mean_shap_llm", pd.Series([np.nan] * len(sub))).to_numpy()

        def _wmean(vals: np.ndarray) -> float:
            mask = ~np.isnan(vals) & ~np.isnan(w)
            if not mask.any():
                return float("nan")
            return float(np.average(vals[mask], weights=w[mask]))

        def _mean(vals: np.ndarray) -> float:
            mask = ~np.isnan(vals)
            return float(np.nanmean(vals[mask])) if mask.any() else float("nan")

        u_sh_hu = _mean(sh_hu)
        u_ll_hu = _mean(ll_hu_k)
        u_sh_ll = _mean(sh_ll)
        w_sh_hu = _wmean(sh_hu)
        w_ll_hu = _wmean(ll_hu_k)

        def _closer(a: float, b: float) -> tuple[str, float]:
            if np.isnan(a) and np.isnan(b):
                return "tied", 0.0
            if np.isnan(a):
                return "LLM", float("nan")
            if np.isnan(b):
                return "SHAP", float("nan")
            if abs(a - b) < 0.05:
                return "tied", abs(a - b)
            return ("SHAP" if a > b else "LLM"), abs(a - b)

        u_close, u_margin = _closer(u_sh_hu, u_ll_hu)
        w_close, w_margin = _closer(w_sh_hu, w_ll_hu)

        out_rows.append({
            "purpose": purpose,
            "rubric_domain": domain,
            "n_traits": int(len(sub)),
            "shap_human_agreement": u_sh_hu,
            "llm_human_agreement": u_ll_hu,
            "shap_llm_agreement": u_sh_ll,
            "closer_to_human_unweighted": u_close,
            "margin_unweighted": u_margin,
            "shap_human_agreement_weighted": w_sh_hu,
            "llm_human_agreement_weighted": w_ll_hu,
            "closer_to_human_weighted": w_close,
            "margin_weighted": w_margin,
        })
    return pd.DataFrame(out_rows)


# --- Orchestration -------------------------------------------------------
def run_triangulation(purpose: str, data_root: Path | None = None) -> dict[str, pd.DataFrame]:
    """End-to-end: load all inputs, compute 3-way agreement + domain aggregation."""
    matrix = load_stage5_matrix(purpose)
    rater, purity = load_stage1_reliability()
    weights = compute_trait_reliability_weight(rater)
    weights_this = weights[weights["purpose"] == purpose]

    shap_top = load_shap_top_families(purpose)

    # Coding outputs — supplementary 4-level coding (부록 D), may be missing in
    # dev. Return partial results if absent.
    try:
        llm_codes = load_coding_long(purpose, source="llm")
    except FileNotFoundError as e:
        log.warning("%s — LLM coding not ready, skipping llm_human_agreement", e)
        llm_codes = None
    try:
        human_codes = load_coding_long(purpose, source="human")
    except FileNotFoundError as e:
        log.warning("%s — human coding not ready, skipping llm_human_agreement", e)
        human_codes = None

    per_trait_rows: list[dict] = []
    for trait in ANALYTIC_TRAITS:
        per_trait_rows.append({"trait": trait, "rubric_domain": RUBRIC_AREA_FROM_TRAIT[trait]})
    per_trait = pd.DataFrame(per_trait_rows)

    if llm_codes is not None and "mapped_family_list" in llm_codes.columns:
        sh_ll = _compute_family_jaccard(shap_top, llm_codes, system="llm")
        per_trait = per_trait.merge(
            sh_ll[["trait", "jaccard_mean_shap_llm"]], on="trait", how="left",
        )
    if human_codes is not None and "mapped_family_list" in human_codes.columns:
        sh_hu = _compute_family_jaccard(shap_top, human_codes, system="human")
        per_trait = per_trait.merge(
            sh_hu[["trait", "jaccard_mean_shap_human"]], on="trait", how="left",
        )
    if llm_codes is not None and human_codes is not None:
        ll_hu = compute_llm_human_agreement(llm_codes, human_codes)
        per_trait = per_trait.merge(
            ll_hu[["trait", "kappa_llm_human", "n"]], on="trait", how="left",
        )

    per_domain = aggregate_per_domain(purpose, per_trait, weights_this)

    return {
        "per_trait_agreement": per_trait,
        "per_domain_convergence": per_domain,
        "trait_weights": weights_this,
    }


def write_outputs(result: dict[str, pd.DataFrame], purpose: str, out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    result["per_trait_agreement"].to_csv(
        out_dir / f"per_trait_agreement__{purpose}.csv", index=False,
    )
    result["per_domain_convergence"].to_csv(
        out_dir / f"per_domain_convergence__{purpose}.csv", index=False,
    )
    result["trait_weights"].to_csv(
        out_dir / f"trait_weights__{purpose}.csv", index=False,
    )


def write_supplementary_convergence(
    results_per_purpose: dict[str, dict], out_dir: Path = OUT_DIR
) -> None:
    """Compose the supplementary 3-way convergence markdown.

    v2.6 framework: 본 산출물은 supplementary (부록 D). 본문 main contrast
    (Surface > Content SHAP-LLM Jaccard) 는 ``src/stats/trait_type_contrast.py``
    가 담당. 본 함수는 인간 피드백 fallibility-weighted convergence 의 부록
    보고용.
    """
    out = out_dir / "supplementary_convergence.md"
    lines: list[str] = [
        "# Supplementary — SHAP / LLM rationale / 인간 피드백 3-way 수렴도",
        "",
        "**v2.6 framework 위치**: 본 표는 부록 D supplementary. 본문 main "
        "contrast (Surface > Content SHAP-LLM Jaccard) 의 보조 자료로만 "
        "사용. 이전 v2.3 §3 의 triangulation main question (RQ3) 은 v2.6 "
        "§2.6 + §16 에서 폐기되었음. 본문 핵심 기여 문장에서 인용 금지.",
        "",
        "**방법 (legacy reference, v2.3 §5.4)**: 인간 피드백은 *fallible "
        "evidence source*로 다룬다. Stage 1.1a 실측 기반의 fallibility "
        "weighting (QWK 기반 trait 신뢰도 × feedback purity)을 적용한 결과와 "
        "unweighted 결과를 함께 보고. v2.6 framework: weighted / unweighted "
        "모두 supplementary 보고용 (v2.6 §5.2 mixed model 부록 D 격하와 동일).",
        "",
    ]
    for purpose, result in results_per_purpose.items():
        lines.append(f"## {purpose}")
        lines.append("")
        lines.append(result["per_domain_convergence"].to_markdown(index=False, floatfmt=".3f"))
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s", out)


def write_rq3_summary(
    results_per_purpose: dict[str, dict], out_dir: Path = OUT_DIR
) -> None:
    """Deprecated alias for :func:`write_supplementary_convergence`.

    v2.6 framework change: RQ3 / "주 지표" framing 폐기. 본 함수는 외부 호출
    호환성을 위해 유지되나, 신규 호출은 ``write_supplementary_convergence``
    사용 권장.
    """
    import warnings

    warnings.warn(
        "write_rq3_summary is deprecated under v2.6; "
        "use write_supplementary_convergence",
        DeprecationWarning,
        stacklevel=2,
    )
    write_supplementary_convergence(results_per_purpose, out_dir)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    results_per_purpose: dict[str, dict] = {}
    for purpose in PURPOSES_IN_SCOPE:
        try:
            r = run_triangulation(purpose)
            write_outputs(r, purpose)
            results_per_purpose[purpose] = r
        except FileNotFoundError as e:
            log.error("[%s] %s", purpose, e)
            return 1
    write_supplementary_convergence(results_per_purpose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
