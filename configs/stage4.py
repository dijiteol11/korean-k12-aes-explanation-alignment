"""
Stage 4 LLM scoring — pre-registered configuration (plan v2.3 §4.3 + 외부 review 2026-04-24).

Design basis: SOTA review.md (researcher-approved 2026-04-24) — 강화형 Option C.

Main analysis uses the cost-efficient Sonnet tier; Opus is reserved for a
stratified sensitivity audit at pilot scale. Rationale:
    - Frontier-status is not a top-tier requirement in current AES literature
      (Naismith 2023, Yancey 2023, Yamashita 2024, Saricaoglu & Bilki 2025).
    - Task decomposition and rubric design dominate model tier in AES
      outcomes (Lee et al., 2024 Findings-EMNLP; Yoshida 2025a,b).
    - Direct Opus vs Sonnet AES benchmarks are absent; we empirically
      estimate model dependence rather than cite unverified numbers.

Cross-vendor comparison (Claude vs GPT vs Gemini) is deliberately out of
scope for this paper — see SOTA review.md §"권고 설계" and is reserved
for a follow-up paper (scope hygiene per Jin et al., 2025).
"""
from __future__ import annotations

# --- Model pins (PINNED 2026-05-26) -----------------------------------------
# Anthropic 모델 snapshot은 date-stamped (e.g. "claude-sonnet-4-5-YYYYMMDD")
# 형식이 재현성 측면에서 필수. Alias (예: "claude-sonnet-4-5") 사용 시 Anthropic
# 측 silent model rotation으로 재현 불가능해질 수 있음.
#
# **모델 선택 결정 (2026-05-26 update — v2.6 §1.1 재현성 우선)**:
#   pinned: Sonnet 4.5 date-stamped (`claude-sonnet-4-5-20250929`)
#
#   원래 v2.6 §1.1 + 2026-05-15 결정은 Sonnet 4.6 + Opus 4.6 이었으나,
#   2026-05-26 Anthropic Console / API 확인 결과 Sonnet 4.6 은 alias
#   (`claude-sonnet-4-6`) 만 노출되고 date-stamped snapshot 이 publicly
#   제공되지 않는 상황 확인. v2.6 §1.1 의 *재현성 우선 원칙* (date-stamped
#   MODEL_ID 의무) 에 따라 Sonnet 4.5 date-stamped 로 deviate.
#
#   Capability rationale:
#   - 4.5 는 AES literature SOTA range (Farag et al., 2018; Mizumoto & Eguchi,
#     2023). 4.5 ↔ 4.6 차이는 v2.6 §11.1 의 "engineering QA threshold" framing
#     안에서 absorb 가능.
#   - 4.7 회피 결정 유지 (새 tokenizer input/output inflation + cost
#     uncertainty 회피).
#
#   Pre-registration 보존:
#   - v1.3 (`main_contrast_preregistered_v1.3.md` §1) 의 "Sonnet 4.6" spec 은
#     pre-registration *시점의 의도* lock 으로 보존 (SHA `c6c58acd…` 무변경).
#   - Deviation 은 본 파일 + CLAUDE.md + progress.md + v2.6 plan appendix +
#     snapshot_registry.md + memory + paper methods 에 *각주* 형태로 문서화.
#
#   참조:
#   - `memory/project_stage4_model_decision.md`
#   - `progress.md` §0 "Stage 4 model decision (2026-05-26 update)"
#   - `AES_재포지셔닝_계획_v2.6.md` 부록 "Model Deviation Note 2026-05-26"
#   - `reports/snapshot_registry.md` "Manual pin events" 섹션
#
# 실행 직전 연구자 체크리스트:
#   1) `GET https://api.anthropic.com/v1/models` 호출로 현재 유효한 4.5 snapshot
#      재확인 (claude-sonnet-4-5-20250929 또는 그 이후 4.5 dated snapshot)
#   2) 아래 상수가 위 ID 와 일치하는지 verify
#   3) 변경 시점을 snapshot_registry.md "Manual pin events" 섹션에 기록 완료
#   4) 전체 실행 동안 MODEL_ID 변경 금지 (중단-재개도 동일 snapshot 고수)
#
# **Batch API 권장 (2026-05-15 결정)**: dry-run + 첫 ~100 essay smoke test는
# non-Batch (즉시 응답) → 나머지 95% Batch (`client.messages.batches.create()`)
# 전환. 50% cost 절감 + 24시간 내 처리. AES 비동기 워크로드에 적합.
MODEL_ID_MAIN: str = "claude-sonnet-4-5-20250929"     # pinned 2026-05-26; deviation from v2.6 §1.1 4.6 spec (alias-only)
MODEL_ID_SENSITIVITY: str = "claude-opus-4-x-TBD"     # deferred (v2.6 cost ceiling 0)
TEMPERATURE: float = 0.0  # v2.3 §4.3.1 — deterministic scoring
STAGE4_MAX_TOKENS: int = 8000  # Stage A smoke can exceed 4k when evidence spans are dense.

# **재현성 보고 5항목 (Methods 섹션 필수)**:
#   1. API model version: claude-sonnet-4-6-YYYYMMDD / claude-opus-4-6-YYYYMMDD
#   2. Tokenizer version: 4.6 시점 (4.7 inflation 회피 명시)
#   3. 호출 시점: A4 실행 start/end UTC datetime
#   4. Cache policy: 5분 cache 채택 (1시간 cache 미채택 사유)
#   5. Temperature: 0.0 (deterministic)

# --- Main analysis ---------------------------------------------------------
# Full 4,860 essays × 3 stages (A evidence → B scoring → C rationale).
MAIN_N_ESSAYS: int = 4860

# --- α consistency pilot (v2.3 §4.3.2) -------------------------------------
# Main-model repeatability. Stage B only (scoring is the α-sensitive call).
ALPHA_PILOT_N_ESSAYS: int = 500
ALPHA_PILOT_N_REPEATS: int = 5
ALPHA_EXCLUSION_THRESHOLD: float = 0.80  # traits with α<0.80 dropped from main

# --- Opus sensitivity sub-study --------------------------------------------
# Strengthened per SOTA review.md: n≥1000, 4-way stratified, 8 metrics,
# dual-criterion pass/fail.
SENSITIVITY_N_ESSAYS: int = 1000
SENSITIVITY_STRATA: tuple[str, ...] = (
    "grade",       # 초5, 초6, 중1, 중2, 중3
    "prompt_id",   # per-purpose prompt set
    "score_band",  # discretised Sonnet main score band: low(1-2) / mid(3) / high(4-5)
    "na_flag",     # Sonnet main score is null for any trait
)

# --- Cross-embedding agreement metrics reported in sensitivity audit -------
# Per SOTA review.md §"권고 설계": correlation alone is insufficient for
# rationale-dependent research. Each listed metric must be computed and
# reported per trait (exception: rationale metrics are per trait too, but
# human-coded on a pilot).
SENSITIVITY_METRICS: tuple[str, ...] = (
    "qwk",                      # quadratic weighted κ on integer scores
    "weighted_kappa_linear",    # linear weighted κ on integer scores
    "exact_agreement_rate",     # p(Sonnet.score == Opus.score)
    "adjacent_agreement_rate",  # p(|Sonnet.score - Opus.score| ≤ 1)
    "mean_severity_shift",      # mean(Opus.score - Sonnet.score) per trait
    "rationale_coding_wk",      # weighted κ on 4-level Stage 4.3 codes (상/중/하/NA)
    "mid_category_inflation",   # Sonnet p(중) / Opus p(중) ratio on Stage 4.3 codes
    "na_f1",                    # precision/recall/F1 of Sonnet NA vs Opus NA
)

# --- Pre-registered dual pass/fail criterion -------------------------------
# Separate score-level and explanation-level thresholds. Main design robust
# only when BOTH axes pass. Partial pass = report with caveat.
SENSITIVITY_PASS_SCORE_QWK_MIN: float = 0.70       # per-trait QWK floor
SENSITIVITY_PASS_EXACT_AGREEMENT_MIN: float = 0.55  # per-trait exact agreement floor
SENSITIVITY_PASS_RATIONALE_WK_MIN: float = 0.50     # per-trait rationale coding κ floor
SENSITIVITY_PASS_MID_INFLATION_MAX: float = 1.50    # Sonnet mid-rate / Opus mid-rate
SENSITIVITY_PASS_NA_F1_MIN: float = 0.50

# Classification of sensitivity outcome (applied per-trait, then aggregated):
#   ROBUST:           all 5 criteria pass
#   PARTIALLY_ROBUST: 3-4 criteria pass (score axis intact, explanation axis fails OR vice versa)
#   NOT_ROBUST:       ≤2 criteria pass — triggers main-model reconsideration
# See SOTA review.md §"권고 설계" final paragraph.

# --- Cost ceilings (researcher-approved 2026-04-24, 2026-05-15 4.6+Batch 재분석) --
# 실측 token 기반 cost (char/2.5 estimator + Anthropic pricing,
# `src/llm/cost_estimator.py` 2026-04-24 실행 결과 + 2026-05-15 4.6+Batch 재추정):
#
# **2026-04-24 4.7 추정 (legacy, 참고용)**:
#   Main (Sonnet 4.7):       $356 cached / $458 uncached
#   Sensitivity (Opus 4.7):  $366 cached / $471 uncached  ← 초기 $200 ceiling 초과
#   Alpha pilot (Sonnet 4.7): $60 cached / $98 uncached
#   Grand total:             $782 cached / $1,027 uncached
#
# **2026-05-15 4.6 + Batch 재추정 (legacy)**:
#   Non-Batch path (4.6, Opus inflation 제거):  $661 baseline ~ $753 ceiling
#   Batch API path (4.6, 50% 할인):              $331 baseline ~ $377 ceiling
#
# **2026-05-29 Batch readiness 재확인 (Sonnet 4.5 pinned, char/2.5 estimator)**:
#   `python -m src.llm.cost_estimator` 실측:
#     Main non-Batch:     $458 uncached / $356 cached
#     Main Batch (×0.5):  ~$229 uncached / ~$178 cached  → MAIN ceiling $400 내 (여유)
#     α pilot Batch:      ~$49 uncached / ~$30 cached     → ALPHA ceiling $60 내
#     Grand (sensitivity deferred): Batch ~$208-278       → GRAND $500 내
#   주의: Main non-Batch *uncached* ($458) 은 $400 main ceiling 을 초과하므로
#   non-Batch 경로는 caching 이 필수. Batch 경로는 cached/uncached 어느 기준이든
#   ceiling 내 → Batch 권장 재확인. (Batch 는 prompt caching 미적용해도 안전.)
#
# Ceiling은 보수 측 유지 (non-Batch fallback 가능성 대비 + Anthropic pricing
# 변동 + token 실측 오차 방어). Ceiling 초과 시 실행 중단 대신 경보만
# (수정은 configs/stage4.py 단독으로).
MAIN_COST_CEILING_USD: float = 400.0        # Sonnet 4.6 main via Batch path
ALPHA_PILOT_COST_CEILING_USD: float = 60.0  # Sonnet 4.6 alpha pilot
SENSITIVITY_COST_CEILING_USD: float = 0.0   # Opus sensitivity deferred in v2.6
GRAND_CEILING_USD: float = 500.0            # v2.6 hard ceiling
