"""
Stage 5 — essay × trait alignment matrix.

Joins four evidence sources into a long-form dataframe at the essay × trait cell:

    SHAP side       — Stage 3 local_shap__*.parquet + stability + Jaccard (§4.2.3)
    LLM side        — Stage 4 Sonnet main A/B/C + Stage 4.3 4-level coding
    Human side      — dataset score.personal.analytic + Stage 4.3 4-level coding of feedback
    Stage 1.1a      — feedback purity, 2-rater agreement

The v2.6 main contrast uses essay-level SHAP-LLM Jaccard ``A(i,t)`` as the
primary analysis unit. The older 4-level labels remain supplementary.

Running requires all Stage 3/4 artifacts in place; raises FileNotFoundError
with a descriptive pointer otherwise (prevents half-pipeline runs).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from configs.paths import (
    PROJECT_ROOT,
    PURPOSES_IN_SCOPE,
    REPORTS_DIR,
    TRAITS,
)
from configs.shap import JACCARD_TOP_K, KENDALL_TAU_INSTABILITY, JACCARD_INSTABILITY

log = logging.getLogger(__name__)

ANALYTIC_TRAITS: tuple[str, ...] = tuple(t for t in TRAITS if t != "holistic")

SHAP_DIR: Path = REPORTS_DIR / "stage3_shap"
LLM_DIR: Path = REPORTS_DIR / "stage4_llm"
CODING_DIR: Path = REPORTS_DIR / "stage4_llm" / "coding"
STAGE1_DIR: Path = REPORTS_DIR / "stage1"
OUT_DIR: Path = REPORTS_DIR / "stage5_alignment"


# --- Preregistration SHA integrity check ---------------------------------
PREREG_FILES: tuple[Path, ...] = (
    PROJECT_ROOT / "decision_table_preregistered.md",
    PROJECT_ROOT / "family_rubric_mapping_preregistered.md",
    PROJECT_ROOT / "main_contrast_preregistered_v1.3.md",
)

# Pre-registration baseline SHAs — Stage 5 진입 시 자동 검출 가드.
# Bump alongside decision_table / family_rubric_mapping version transitions.
# Full audit trail: reports/snapshot_registry.md.
PREREG_BASELINE_SHAS: dict[str, str] = {
    "decision_table_preregistered.md":
        "490df99a0b495028a166170ab7c31b59807ba0c4fd82d71f3908ecb7586d101f",  # v1.1 (2026-05-15)
    "family_rubric_mapping_preregistered.md":
        "5f8e5a72c12e33b01dfe49c08e3686ca89c383ea37000af224fd88fbb614139c",  # v1.2 (2026-05-15)
    "main_contrast_preregistered_v1.3.md":
        "c6c58acdee918addbf57288adbf15b35fe19b2db10f9d61ee708b8f253526804",  # v1.3 (2026-05-25)
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_prereg_integrity(expected_shas: dict[str, str] | None = None) -> dict[str, str]:
    """Verify preregistration documents match the team-consensus SHA.

    If ``expected_shas`` is provided (e.g. loaded from snapshot_registry.md
    after v1.0 commit), compare and raise on mismatch. Returns the current
    SHA map of the two pre-reg files for logging/registration.
    """
    current = {p.name: _sha256(p) for p in PREREG_FILES if p.exists()}
    if expected_shas is not None:
        for name, sha in expected_shas.items():
            if name not in current:
                raise FileNotFoundError(f"pre-reg file missing: {name}")
            if current[name] != sha:
                raise RuntimeError(
                    f"pre-reg SHA drift on {name}: expected {sha[:16]}…, "
                    f"got {current[name][:16]}…. Stage 5 must halt per "
                    f"decision_table_preregistered.md §5."
                )
    return current


# --- SHAP side loader ----------------------------------------------------
def load_shap_top_families(purpose: str, embedding: str = "primary", k: int = JACCARD_TOP_K) -> pd.DataFrame:
    """Per-trait Top-K family list (global aggregation across CVs).

    Returns: DataFrame(trait, top_families [list[str]]).
    """
    p = SHAP_DIR / f"global_shap__{purpose}__{embedding}.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"Stage 3 global_shap missing for {purpose}/{embedding}: {p}. "
            "Run: python -m src.shap_analysis.cli --purpose X --embedding Y"
        )
    df = pd.read_csv(p)
    rows = []
    for trait, g in df.groupby("trait"):
        top = g.nsmallest(k, "rank").sort_values("rank")["family"].tolist()
        rows.append({"trait": trait, "top_families": top})
    return pd.DataFrame(rows)


def load_shap_stability_flags(purpose: str, embedding: str = "primary") -> pd.DataFrame:
    """Per-trait UR-gate flags: Kendall τ (fold) × Jaccard (embedding)."""
    rows = []
    for cv in ("grade_stratified", "cross_prompt"):
        p = SHAP_DIR / f"stability__{purpose}__{embedding}__{cv}.csv"
        if not p.exists():
            continue
        s = pd.read_csv(p)
        for _, r in s.iterrows():
            rows.append({
                "trait": r["trait"], "cv": cv,
                "tau_mean": r["tau_mean"],
                "tau_unstable": bool(r["tau_mean"] < KENDALL_TAU_INSTABILITY),
            })
    tau_df = pd.DataFrame(rows)

    jac_path = SHAP_DIR / f"jaccard__{purpose}__primary_vs_robust_1.csv"
    if jac_path.exists():
        jac = pd.read_csv(jac_path)[["trait", "jaccard"]].copy()
        jac["jaccard_unstable"] = jac["jaccard"] < JACCARD_INSTABILITY
    else:
        jac = pd.DataFrame(columns=["trait", "jaccard", "jaccard_unstable"])

    # Aggregate τ across CVs (any unstable CV flags the trait)
    trait_agg = (
        tau_df.groupby("trait")
        .agg(
            tau_mean_min=("tau_mean", "min"),
            tau_unstable_any=("tau_unstable", "any"),
        )
        .reset_index()
    )
    return trait_agg.merge(jac, on="trait", how="left")


# --- LLM side loader -----------------------------------------------------
def load_llm_scores(purpose: str, track: str = "main") -> pd.DataFrame:
    """Stage 4 B-output per (essay_id, trait): score, confidence, reason."""
    path = LLM_DIR / track / "B" / f"{purpose}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Stage 4 B output missing for {purpose}/{track}: {path}. "
            "Run: python -m scripts.run_stage4 --track main --stage B --purpose X"
        )
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        rec = json.loads(line)
        eid = int(rec["essay_id"])
        for trait, entry in rec["scores"].items():
            rows.append({
                "essay_id": eid, "trait": trait,
                "llm_score": entry.get("score"),
                "llm_confidence": entry.get("confidence"),
                "llm_reason": entry.get("reason"),
                "llm_is_na": entry.get("score") is None,
            })
    return pd.DataFrame(rows)


def load_llm_rationale_coding(purpose: str) -> pd.DataFrame | None:
    """Stage 4.3 4-level coding of LLM rationale. Returns None until coding done."""
    p = CODING_DIR / f"llm_rationale_coding__{purpose}.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)  # expected columns: essay_id, trait, code (상/중/하/NA)


# --- Human side loader ---------------------------------------------------
def load_human_scores(data_root: Path, purpose: str) -> pd.DataFrame:
    """Mean of 2-rater integer scores + disagreement flag per (essay_id, trait)."""
    rows = []
    for p in data_root.rglob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("essay_question", {}).get("purpose") != purpose:
            continue
        eid = int(raw["essay_answer"]["id"])
        question = raw.get("essay_question", {})
        answer = raw.get("essay_answer", {})
        analytic = raw.get("score", {}).get("personal", {}).get("analytic", {})
        for trait in ANALYTIC_TRAITS:
            d = analytic.get(trait, {})
            scores = d.get("score", [])
            if len(scores) < 2:
                continue
            r1, r2 = float(scores[0]), float(scores[1])
            rows.append({
                "essay_id": eid, "trait": trait,
                "human_r1": r1, "human_r2": r2,
                "human_mean": (r1 + r2) / 2.0,
                "human_disagreement": abs(r1 - r2),
                "prompt_id": question.get("id"),
                "grade": question.get("grade"),
                "essay_length": answer.get("len_word") or answer.get("len_syllable"),
            })
    return pd.DataFrame(rows)


def load_human_feedback_coding(purpose: str) -> pd.DataFrame | None:
    """Stage 4.3 4-level coding of human feedback. Returns None until coding done."""
    p = CODING_DIR / f"human_feedback_coding__{purpose}.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)  # essay_id, trait, code


def load_feedback_purity() -> pd.DataFrame:
    """Stage 1.1a per-cell feedback purity (off-area ratio, impure flag)."""
    p = STAGE1_DIR / "feedback_purity.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"Stage 1.1a feedback_purity missing: {p}. "
            "Run: python -m src.stats.human_reliability"
        )
    return pd.read_csv(p)[["essay_id", "purpose", "trait",
                           "off_area_ratio", "impure_50pct"]]


def load_rater_agreement() -> pd.DataFrame:
    """Stage 1.1a per-trait inter-rater agreement."""
    p = STAGE1_DIR / "rater_agreement.csv"
    if not p.exists():
        raise FileNotFoundError(f"Stage 1.1a rater_agreement missing: {p}")
    return pd.read_csv(p)[["purpose", "trait", "qwk", "icc_2_1",
                           "qwk_below_0_70", "icc_below_0_70"]]


def load_main_alignment_metric(
    purpose: str,
    *,
    embedding: str = "primary",
    cv_label: str = "grade_stratified",
    llm_track: str = "main",
) -> pd.DataFrame | None:
    """Load or compute v2.6 essay-level SHAP-LLM Jaccard if inputs exist."""
    cached = OUT_DIR / f"jaccard_alignment__{purpose}__{embedding}__{cv_label}.parquet"
    if cached.exists():
        return pd.read_parquet(cached)

    local_shap = SHAP_DIR / f"local_shap__{purpose}__{embedding}__{cv_label}.parquet"
    stage_c = LLM_DIR / llm_track / "C" / f"{purpose}.jsonl"
    if not local_shap.exists() or not stage_c.exists():
        return None

    from src.alignment.jaccard_metric import (
        build_alignment_metric_for_purpose,
        write_alignment_metric,
    )

    metric = build_alignment_metric_for_purpose(
        purpose,
        stage_c_path=stage_c,
        embedding=embedding,
        cv_label=cv_label,
    )
    write_alignment_metric(metric, purpose, embedding=embedding, cv_label=cv_label)
    return metric


# --- Main matrix builder -------------------------------------------------
@dataclass(frozen=True)
class BuildResult:
    matrix: pd.DataFrame
    prereg_shas: dict[str, str]
    purpose: str
    n_cells: int


def build_matrix(
    purpose: str,
    data_root: Path,
    *,
    embedding: str = "primary",
    llm_track: str = "main",
) -> BuildResult:
    """Assemble the essay × trait alignment matrix for one purpose.

    The matrix has one row per (essay_id, trait) with columns from all
    four evidence sources. Rows whose LLM or Human side is missing still
    appear — ``Stage5_gate`` columns mark which rows are analyzable.
    """
    prereg_shas = check_prereg_integrity(expected_shas=PREREG_BASELINE_SHAS)

    # Load each side (some may be None if Stage 4.3 coding not done).
    shap_top = load_shap_top_families(purpose, embedding=embedding)
    shap_stab = load_shap_stability_flags(purpose, embedding=embedding)
    llm_b = load_llm_scores(purpose, track=llm_track)
    llm_code = load_llm_rationale_coding(purpose)
    human_sc = load_human_scores(data_root, purpose)
    human_code = load_human_feedback_coding(purpose)
    purity = load_feedback_purity()
    rater = load_rater_agreement()
    main_metric = load_main_alignment_metric(
        purpose,
        embedding=embedding,
        cv_label="grade_stratified",
        llm_track=llm_track,
    )

    # Base: essay × trait rows from human_scores (authoritative set of cells).
    m = human_sc.copy()
    m = m.merge(llm_b, on=["essay_id", "trait"], how="left")
    m = m.merge(
        shap_top.rename(columns={"top_families": "shap_top_families"}),
        on="trait", how="left",
    )
    m = m.merge(shap_stab, on="trait", how="left")
    m = m.merge(
        purity[purity["purpose"] == purpose][["essay_id", "trait",
                                               "off_area_ratio", "impure_50pct"]]
            .rename(columns={"impure_50pct": "feedback_impure_50"}),
        on=["essay_id", "trait"], how="left",
    )
    m = m.merge(
        rater[rater["purpose"] == purpose][["trait", "qwk_below_0_70",
                                             "icc_below_0_70"]]
            .rename(columns={"qwk_below_0_70": "rater_qwk_low",
                             "icc_below_0_70": "rater_icc_low"}),
        on="trait", how="left",
    )
    if llm_code is not None:
        m = m.merge(llm_code.rename(columns={"code": "llm_code"}),
                    on=["essay_id", "trait"], how="left")
    else:
        m["llm_code"] = pd.NA
    if human_code is not None:
        m = m.merge(human_code.rename(columns={"code": "human_code"}),
                    on=["essay_id", "trait"], how="left")
    else:
        m["human_code"] = pd.NA
    if main_metric is not None:
        metric_cols = [
            "essay_id", "trait", "jaccard", "shap_families_pipe",
            "llm_families_pipe", "llm_family_empty",
            "family_union_size", "family_intersection_size",
        ]
        available = [col for col in metric_cols if col in main_metric.columns]
        m = m.merge(main_metric[available], on=["essay_id", "trait"], how="left")
    if "family_rubric_match" not in m.columns:
        m["family_rubric_match"] = pd.NA
    if "justification_rate" not in m.columns:
        m["justification_rate"] = pd.NA

    m.insert(0, "purpose", purpose)
    return BuildResult(matrix=m, prereg_shas=prereg_shas,
                       purpose=purpose, n_cells=len(m))


def write_matrix(result: BuildResult, out_dir: Path = OUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"matrix__{result.purpose}.parquet"
    result.matrix.to_parquet(out, index=False)
    log.info("Wrote %s (%d cells)", out, result.n_cells)
    # Also drop SHA provenance for audit
    sha_out = out_dir / f"matrix__{result.purpose}.sha_provenance.json"
    sha_out.write_text(json.dumps({
        "purpose": result.purpose,
        "n_cells": result.n_cells,
        "prereg_shas": result.prereg_shas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
