"""
Centralized path and constant configuration.

Allows override via environment variable AES_DATA_ROOT.
During development with /mnt/project samples, set AES_DATA_ROOT=/mnt/project
to run smoke tests. For the full 20K corpus, point to the full extracted JSON
directory.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Project root -----------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# --- Data roots -------------------------------------------------------------
# Default: /mnt/project (the sample corpus). Override with env var for full data.
DATA_ROOT: Path = Path(os.environ.get("AES_DATA_ROOT", "/mnt/project"))

RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR: Path = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"

for _d in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Rubric traits (fixed by the NIA 14-026 schema) -------------------------
# Order matters for downstream tables.
TRAITS: tuple[str, ...] = (
    "task_1",
    "content_1",
    "content_2",
    "content_3",
    "organization_1",
    "organization_2",
    "expression_1",
    "expression_2",
)

TRAIT_NAMES_KO: dict[str, str] = {
    "task_1":         "과제 수행의 충실성",
    "content_1":      "설명의 명료성",
    "content_2":      "설명의 구체성",
    "content_3":      "설명의 적절성",
    "organization_1": "문장의 연결성",
    "organization_2": "글의 통일성",
    "expression_1":   "어휘의 적절성",
    "expression_2":   "어법의 적절성",
}

# Trait families for the Messick analysis (plan §4.5.2).
TRAIT_FAMILY: dict[str, str] = {
    "task_1":         "task",
    "content_1":      "content",
    "content_2":      "content",
    "content_3":      "content",
    "organization_1": "organization",
    "organization_2": "organization",
    "expression_1":   "expression",
    "expression_2":   "expression",
}

SCORE_MIN, SCORE_MAX = 1, 5  # analytic and holistic both on 1–5

# --- Study scope (plan v2.3 §4.1.3) ----------------------------------------
# 친교 및 정서 excluded per research design; 사회·과학 not available.
PURPOSES_IN_SCOPE: tuple[str, ...] = ("설명", "설득")


# --- Sentence embedding models ---------------------------------------------
# Primary: KR-SBERT (SNU, 2021) — established, peer-reviewed lineage
# Robust 1: KoSimCSE-RoBERTa — strong KorSTS, 512-token context
# Robust 2: ModernBERT-korean-preview — 8192 context; preview status flagged
#
# The code path is identical for all three; switching `ACTIVE_EMBEDDING`
# rebuilds the coherence feature column group. Stage 5 will compare SHAP
# patterns across the three to defend the primary choice.
EMBEDDING_MODELS: dict[str, str] = {
    "primary":  "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
    "robust_1": "BM-K/KoSimCSE-roberta",
    "robust_2": "sigridjineth/ModernBERT-korean-large-preview",
}
ACTIVE_EMBEDDING: str = os.environ.get("AES_EMBEDDING", "primary")

# Token/length caps applied during embedding, to bound memory for ModernBERT's
# 8192 max. Korean middle-school essay sentences are almost always ≤ 128 tokens.
EMBEDDING_MAX_TOKENS: int = 256


# --- Feature configuration (plan §4.2.1) -----------------------------------
# Morphological features: the 42 tags that appear in the NIA 14-026 JSON
# `feature` field. Not all tags appear in every essay; absent keys are
# treated as zero.
# This list is the union observed across the corpus; extending it is safe.
MORPH_TAGS: tuple[str, ...] = (
    "일반 명사", "명사 파생 접미사", "보조사", "붙임표", "관형격 조사",
    "주격 조사", "부사격 조사", "동사 파생 접미사", "관형형 전성 어미",
    "목적격 조사", "동사 파생 접미사+종결 어미", "마침표, 물음표, 느낌표",
    "연결 어미", "보조 용언+선어말 어미+연결 어미", "구분자",
    "동사+연결 어미", "형용사", "숫자", "단위를 나타내는 명사", "동사",
    "보조 용언", "종결 어미", "동사+관형형 전성 어미", "의존 명사",
    "접속 부사", "긍정 지정사+관형형 전성 어미", "동사+종결 어미",
    "접속 조사", "일반 부사", "긍정 지정사",
    "형용사 파생 접미사+관형형 전성 어미", "명사형 전성 어미",
    "보조 용언+종결 어미", "대명사", "동사 파생 접미사+관형형 전성 어미",
    "수사", "관형사", "긍정 지정사+연결 어미", "동사 파생 접미사+연결 어미",
    "형용사+연결 어미+보조 용언+관형형 전성 어미", "동사+연결 어미+보조 용언",
    "문장수",  # kept as an explicit key so we can read it cleanly
)

# Grouping for derived features (used in morphology.py)
POS_FAMILIES: dict[str, tuple[str, ...]] = {
    "noun":      ("일반 명사", "의존 명사", "단위를 나타내는 명사"),
    "verb":      ("동사", "동사+연결 어미", "동사+종결 어미",
                   "동사+관형형 전성 어미", "동사+연결 어미+보조 용언"),
    "adjective": ("형용사", "형용사+연결 어미+보조 용언+관형형 전성 어미",
                   "형용사 파생 접미사+관형형 전성 어미"),
    "adverb":    ("일반 부사", "접속 부사"),
    "pronoun":   ("대명사",),
    "numeral":   ("수사", "숫자"),
    "determiner":("관형사",),
    "connective_ending": ("연결 어미", "동사+연결 어미",
                           "동사 파생 접미사+연결 어미",
                           "긍정 지정사+연결 어미"),
    "final_ending":      ("종결 어미", "동사+종결 어미",
                           "동사 파생 접미사+종결 어미",
                           "보조 용언+종결 어미"),
    "adnominal_ending":  ("관형형 전성 어미", "동사+관형형 전성 어미",
                           "동사 파생 접미사+관형형 전성 어미",
                           "긍정 지정사+관형형 전성 어미",
                           "형용사 파생 접미사+관형형 전성 어미"),
}


# --- Feature families for SHAP interpretation (plan v2.3 §4.2.1) -----------
# Interpretation and alignment analysis operate at family level, not individual
# features, to mitigate correlation-induced SHAP instability.
# Updated with KICE AES Feature Spec (송민호 외 2025) additions.
FEATURE_FAMILIES: tuple[str, ...] = (
    "meta",          # 음절수, 어절수, 문장수, 평균 문장 길이
    "morph_prop",    # JSON feature의 정규화된 품사·어미 태그 비율 (41개)
    "lex",           # TTR, 타입 수, POS 계열 Shannon 엔트로피
    "vocab_grade",   # NEW: Kim 2023 어휘 등급 기반 (1-5학년 비율, 평균 등급)
    "syn",           # 연결·종결·관형 어미 계열 비율, 동사·형용사·명사 비율
    "case_marker",   # NEW: KICE 격조사 분포 (주격/목적격/부사격 등)
    "dis_nonSBERT",  # 접속부사·대명사·접속조사 밀도
    "dis_SBERT",     # 인접 문장 코사인 mean/std/min, 전체 쌍 mean
)

# --- Kim 2023 Vocabulary Grade Lexicon ------------------------------------
VOCAB_GRADE_XLSX: Path = PROJECT_ROOT / "KOR voca list(Kim 2023).xlsx"
VOCAB_GRADE_CACHE: Path = PROCESSED_DIR / "vocab_grade_lookup.pkl"


def feature_family(col: str) -> str:
    """Map a feature column name to its family for SHAP aggregation.

    Prefix convention (as emitted by src/features/*.py as of 2026-04-22):
        meta_*        → meta           (length / sentence count / averages)
        morph_prop__* → morph_prop     (41 NIA JSON POS-tag proportions)
        lex_*         → lex            (TTR, type counts, POS entropy)
        vocab_*       → vocab_grade    (Kim 2023 — 8 cols)
        syn_*         → syn            (ending rates, POS ratios)
        josa_*, case_diversity → case_marker  (KICE 격조사 — 16 cols)
        dis_*         → dis_nonSBERT   (connective / pronoun / conj particle)
        sbert_*, coh_* → dis_SBERT     (coherence, only present w/ SBERT)
    """
    if col.startswith("meta_"):
        return "meta"
    if col.startswith("morph_"):
        return "morph_prop"
    if col.startswith("lex_"):
        return "lex"
    if col.startswith("vocab_"):
        return "vocab_grade"
    if col.startswith("josa_") or col == "case_diversity":
        return "case_marker"
    if col.startswith("syn_"):
        return "syn"
    # Order matters: dis_sbert_* must be caught before the generic dis_* branch.
    if col.startswith("dis_sbert_") or col.startswith("sbert_") or col.startswith("coh_"):
        return "dis_SBERT"
    if col.startswith("dis_"):
        return "dis_nonSBERT"
    return "unknown"
