# Decision History (Deprecated Options Archive)

이 문서는 `CLAUDE.md`에서 분리된 **과거 의사결정의 이력**이다.
리뷰 §8의 지적(CLAUDE.md에 fixed decisions와 open decisions가
공존하여 혼란을 야기)에 따라 현행 문서와 분리하여 보존한다.

현행 결정 상태는 `CLAUDE.md`, `AES_재포지셔닝_계획_v2.6.md`, 그리고
`main_contrast_preregistered_v1.3.md`에 있다.
이 파일은 **참조용**이며, 실행 코드나 실험 설계의 근거로 사용하지 않는다.

---

## 논문 작성 언어 흐름 결정 — 한국어 우선 (2026-07-02)

**결정**: 논문(P13)을 **한국어 canonical 소스에서 완전히 새로 작성** → 저자가
섹션별로 내용을 검증 → 검증본을 영어로 번역한다. `manuscript_ko_v0.1.md` 가
저자 검증 대상이고, `manuscript_en_v1.0.md` 가 번역 산출물이다. 기존
`manuscript_en_v0.1.md` 는 **authoring source 가 아니라 prior artifact**(커버리지
교차확인용)로만 보존하며 편집·권위 부여하지 않는다.

**근거**:
- 저자의 내용 검증은 한국어에서 더 엄밀하게 이뤄진다.
- 한국어 canonical 소스(`연구계획서_D_v2.4.md`, `AES_재포지셔닝_계획_v2.6.md`,
  결과 리포트, 3 pre-reg)를 **그대로 반영**한다(수치·framing 추적 가능).
- §6 Limitations 는 v2.6 §11.1–§11.5 + §11.7 한국어 wording 을 canonical source
  로 재사용 → 영문 §6.1–§6.6 == v2.6 §11 mirror-lock 이 올바른 방향으로 보존.

**lock 문장**: "본 논문은 한국어 canonical 소스에서 새로 작성·검증하고 영어로
번역한다; §6 Limitations 는 v2.6 §11 Korean wording 을 canonical source 로
재사용한다."

**처리**: `paper/working_plan.md` P13 순서에 한국어 authoring 단계(P13.2k)를
번역·변환 앞에 삽입; 집필용 소스 팩 `paper/manuscript_ko_source_pack.md` 생성
(수치·§6 verbatim·claim 인벤토리 집약); AW Guide 준수 결과(아래 entry) 반영.
`progress.md` §0 + `CLAUDE.md` next milestone 갱신. pre-reg SHA 3파일·KEYWORD_SET
무변경, paid API 0.

---

## Guide-for-Authors 확인 — P13.1b conditionals 해소 (2026-07-02)

**결정**: *Assessing Writing* "Guide for Authors" (Elsevier, 2026 판; PDF
`paper/`) 확인으로 `revision_plan_p13_1b.md` 의 conditional actions 를 확정한다.
상세: `paper/guide_for_authors_compliance.md` (P13.1c).

**판정 요지**:
- GAP-1 초록 (≤250 words, structured 불요) → 현 213 words 유지, 변환 미발동.
- GAP-2 §6 Limitations 별도 섹션 → 허용, 유지(mirror-lock 보존).
- GAP-3 부록 A–F → inline 유지(Supplementary 분리 불요), **단 표 번호
  `Table B1→B.1` 형식 수정** 필요.
- GAP-4 참고문헌 6 → 제출 시점 개수 제약 없음, 유지.
- GAP-5 → **Highlights 필수**(3–5 bullet, ≤85자) + title page(별도, 저자정보·
  감사말·COI) + Declaration of generative AI use + Data statement(Option C) +
  CRediT + keywords(1–7 영어) + `.docx/.tex` + British English. 전부 P13.4.

**처리**: 본문 구조 무변경(부록 표 번호만 수정). 위 필수 항목은 P13.4 submission
package 로 라우팅. 본 노트가 P13.1b 의 "pending AW Guide confirmation" 상태를
supersede (revision_plan 파일은 보존).

---

## P9 supplementary robustness 수행 결정 (2026-06-02)

**결정**: §10.D 를 **performed, scope-limited** supplementary robustness 로
채운다. 사용자 권고 (2026-06-02) 에 따라 main contrast 해석을 바꾸는 새
모델 / 새 metric / 새 detector / 새 threshold 탐색은 금지하고, 두 보고
관례 (reporting-convention) sensitivity 만 audit 한다.

**Lock 문장 (본문 §10.D 동일 wording)**:
> "Supplementary robustness was limited to reporting-convention
> sensitivity, not an additional substantive model."
>
> "Both checks retained the same directional interpretation: sparse
> nonzero cases favored Surface (and Discourse) over Content, while
> absolute alignment remained near floor."

**수행 내용 (2 axis · 표 2개)**:
1. **Empty-union convention**: 사전등록 `A=0 (both empty)` ↔ alternative
   `A=NA (drop both-empty)`. 결과: `zero_method='wilcox'` 가 both-empty
   pair 를 이미 signed-rank 계산에서 제외하므로 `W = 57,750 / p = 1.96 ×
   10⁻⁶⁵ / r = 0.981` 두 convention 에서 동일; 표시 `n` 만 4,860 → 341.
2. **Wilcoxon tie-handling**: `wilcox` / `pratt` / `zsplit`. 결과: `p` 가
   `1.96e-65 / 7.90e-74 / 1.31e-19` 로 이동하나 세 방법 모두 통상 임계
   하회; `r = 0.981` invariant.

**결론**: 두 axis 모두 동일 방향 해석 유지 (Surface > Content sparse
nonzero direction), `strong_claim_pass = False` / `pooled_median_direction
_pass = False` 사전등록 상태 그대로. **본문 §6 / §7 claim 무변경**.

**구현 / audit 위치**:
- `scripts/run_stage10D_robustness.py` (신규, read-only over alignment
  parquets).
- `reports/stage10D_robustness/sensitivity.md` (audit log).
- `연구계획서_D_v2.4.md` §10.D (표 2개 + 3-4 문장 narrative).

**범위 lock (재진입 금지)**:
- 새 metric / detector / threshold / 모델 도입 금지.
- F_SHAP top-K 변경 금지 (pre-reg metric 정의 영역).
- pre-reg SHA 3종 무변경 (`PREREG_BASELINE_SHAS` match).
- §8 mirror 6/6 line-ending-normalized body wording match 유지.

---

## α pilot 보류 결정 (2026-06-01)

**결정**: α pilot **보류**. *생략* 이 아니라 *trigger 불충족 + V3 해결 불가 →
후속 / 보조 분석으로 defer*. 사전등록 의도 (v2.3 §4.3.2 Krippendorff α pilot)
는 보존; 본 paper 범위 밖.

**lock 문장 (본문 / 후속 문서 동일 wording)**:
> "α pilot deferred: null trigger 미충족, V3 해결 불가, main contrast 는
> V3 / median-zero caveat 가 붙은 form-family operational claim 으로 보고한다."

**근거 4 점**:
1. **Stage B null trigger 불충족**: per-trait null score max **3.8%
   (expression_2, 설명)** — 원 α pilot trigger 임계 (> 10%) 미달. 운영 안정성
   trigger 가 없음.
2. **V3 해결 불가**: V3 headline ("Score-level premise NOT met") 은 XGBoost
   OOF ↔ Sonnet score-level mismatch 문제이지 Sonnet 자체 반복 안정성 문제가
   아님. α pilot 은 Sonnet 의 self-consistency 만 측정하므로 V3 해결과 무관.
3. **Main finding pattern 정합**: Surface ≈ Discourse > Content (primary
   `rank_biserial_r = 0.981`, `medians = 0`). 이 패턴은 §11.7 content_1 floor
   caveat 와 정확히 정합.
4. **메시지 분산 위험**: 비용은 작지만 ($30-49 추가), 지금 α pilot 을 돌리면
   논문 메시지가 "V3 한계 보완" 이 아니라 "LLM 점수 반복 안정성 추가 확인"
   으로 분산. V3 / median-zero caveat 정리 쪽이 paper-defense 우선순위.

**대신 수행한 보강 (paid 0)**:
- `scripts/run_stage5_analysis.py` 확장 → §5 Descriptive robustness:
  (5.1) nonzero / zero breakdown per (purpose, trait_type),
  (5.2) paired difference distribution (positive / zero / negative 비율 +
  mean / quantile),
  (5.3) purpose direction consistency (essay 단위 Surface vs Content 비율),
  (5.4) trait-type Jaccard quantiles.
- `main_contrast_summary.md` 첫머리 §0 Framing notes 신설 (r=0.981 caveat,
  form-family operational alignment 용어, strong_claim FAIL 명시).

**갱신 파일**: `decision_history.md` (본 entry), `progress.md` (§0 상태 +
α pilot 항목 갱신), `scripts/run_stage5_analysis.py` (§5 신설 + §6 α pilot 정식
보류 블록), `reports/stage5_alignment/main_contrast_summary.md` (재생성).
pre-reg SHA-lock 3 파일·`KEYWORD_SET`·ceiling 상수 무변경.

---

## Batch readiness 구현 + 하드닝 (2026-05-29)

**구현** (`scripts/run_stage4.py`): Anthropic Message Batches 경로 추가.
- `_process_stage_response` 공유 추출 → sync + batch 가 동일 parse/repair/
  validate/write 경로 사용 (회귀 위험 ↓).
- `--batch` (stage 별 submit, **3-stage 순차 A→B→C**, custom_id
  `{EXP/PER}_{stage}_{eid}_{ri}`, `_batch_meta.jsonl`) + `--batch-poll
  [--batch-wait]` (retrieve→공유 파이프라인). idempotent + `_batch_in_flight`
  중복 제출 가드.

**하드닝 (검토 반영)**:
- **P1**: prior-stage 누락 시 hard fail — `skipped>0` → `_batch_meta` abort row +
  `return 1` (부분 batch 제출 거부). 기존 silent `return 0` 오해 제거.
- **P2**: custom_id ↔ batch meta (purpose/stage) 불일치 entry skip + n_fail
  (hard assert 아님 — 나머지 retrieved 결과 보존).

**cost 재확인 (Sonnet 4.5, char/2.5 estimator)**: Batch main ~$178-229,
α pilot Batch ~$30-49, grand (sensitivity deferred) ~$208-278 — 모두 v2.6
ceiling (Main $400 / Alpha $60 / Grand $500) 내. non-Batch *uncached* main
$458 은 $400 초과 → non-Batch 는 caching 필수, Batch 는 어느 기준이든 안전.
- **legacy 추정 보존**: 2026-05-15 4.6 시점 추정 = non-Batch $661-753 /
  Batch $331-377 / GRAND $1,400. 현행(4.5 + v2.6 ceiling)이 supersede; 실행
  안내 문서에는 현행 수치만 노출 (이 figure 는 본 entry 에만 과거 기록).

**검증**: pytest 108/108 (test_stage4_batch 7건 포함). paid full run 은
researcher 트리거 (목적별 2회; paid 직전 Anthropic Console batch limits 확인).
pre-reg SHA·`KEYWORD_SET`·`PREREG_BASELINE_SHAS`·§11.7 mirror 본문 무변경.

---

## P2 본 scoring 진입 결정 (2026-05-29)

**결정문**: Smoke gate (f)(h) 는 formal pass 하지 못했으나, Phase 4 spot-check
결과 content_1 floor 가 detector bug 보다는 metric-design limitation 임을
확인했다. 따라서 F_LLM–F_SHAP alignment 는 semantic truth claim 이 아니라
pre-registered form-family operational alignment 로 제한하여 본 실행을
진행한다 (P2-with-caveat).

**근거**: (1) main contrast 가 Surface vs Content, (2) F_LLM 은 keyword-family
exact match 라는 measurement convention, (3) blind spot-check 에서 보수 coder
([Coder B]) 도 content_1 family 호출을 거의 확인하지 않음 (agreed-miss 0),
(4) §11 limitation 으로 claim modesty 명시. cell 12 fix 후 organization_1 은
설명 0.40→0.67 / 설득 0.53→0.73 개선됐으나 (f)(h) 임계는 여전히 미달 — §11.7
(content_1 floor) + §11.1 (engineering-QA ≠ theoretical) 로 문서화하고 진행.

**5 framing 조건 (본문 작성 규약, lock)**:
1. §11.7 content_1 floor limitation 게재 (locked mirror v2.6/v2.4/CLAUDE.md/
   progress.md + 부록 C 반영 완료).
2. 본문에서 "semantic alignment" 표현 **금지**.
3. "form-family operational alignment" / "form-family alignment" 용어로 표기.
4. content 의 낮은 값은 "무의미한 failure" 가 아니라 "content rationale 의
   semantic vocabulary 가 form-based feature family 와 비매핑" 으로 조심스럽게 해석.
5. effect size / 절대 alignment 값 해석은 caveat; contrast 는 *방향* 해석에 한정.

**처리**: §41/Phase 5 게이트 #6 (사용자 명시 승인) 충족. #7 (`--batch` 활성화 +
paid full run) 은 **별도 후속 Phase (Batch readiness)** — Batch 구현 여부 결정 /
cost ceiling 재확인 / small dry-run·mock / paid trigger=researcher.
pre-reg SHA·`KEYWORD_SET`·`PREREG_BASELINE_SHAS` 무변경.

→ 이 entry 시점의 "#7 은 별도 후속 Phase" 결정은 이후 **2026-05-29 "Batch
readiness 구현 + 하드닝" entry 로 superseded** (동일 날짜 후속 실행 — 본 파일
상단 entry 참조).

---

## Phase 4 spot-check 완료 + cell 12 detector fix + 라벨 정리 (2026-05-29)

**Spot-check 결과** (`reports/stage4_llm/keyword_blind_audit.md` +
`analyst/spotcheck_decision_summary.md`):
- Coder A = [Coder A / domain expert] (broad, 35/160), Coder B = [Coder B] (conservative, 11/160),
  machine 5/160. B positive ⊂ A positive. inter-coder κ=0.417 (**descriptive
  only — gate 아님**). agreed human-positive (A∧B) 11, **agreed-miss 7**.
- 두 coder threshold 상이 → **A-only 24 는 detector 수정 근거로 직접 사용
  금지**. agreed-miss 7 만 1차 검토 대상.

**agreed-miss 7 family별 처리 결정**:
- **cell 12 (dis_nonSBERT) 만 detector-only 복구** — Kiwi 가 `'연결어'` 를
  `연결`+`어` 로 split 하여 v1.3 키워드 `('연결어',)` 가 매칭 불가능했던
  *구현 버그*. `_iter_kiwi_tokens` 에 `add_user_word('연결어','NNG')` 로 기존
  키워드 의도 회복. **`KEYWORD_SET`·v1.3 SHA 무변경 → cascade 없음** (단순
  normalization 아닌 deviation 우려는 *키워드 추가/인접완화* 에만 해당; 본 건은
  기존 키워드 토큰화 복구라 해당 없음). dead keyword 추가 진단: `('응집',)` 도
  Kiwi 가 `집` 으로 축소 → **보고만, 미수정** (scope 고정, 후속 사용자 결정).
- cells 3·20 (syn: 주어 불일치 / 문장 연결), 4·10 (dis_nonSBERT: '연결 표현'·
  비인접 문단연결·접속표현) — 개념이 v1.3 키워드 **부재**. 잡으려면 키워드 확장
  → **v1.3 SHA cascade**. 본 실행 전 **보류 (deferred)**, documented deviation
  (v2.6 §11.1/§11.2 틀). detector 과소검출은 한계로 기록.
- cells 11 (dis_SBERT, per-family κ=0.083), 14 (morph_prop, κ=0.146) — 낮은
  inter-coder 신뢰도 + family 경계 중첩 → **비추격** (불안정 신호).
- **content_1: agreed-miss 0** (보수 coder content_1 positive 0). detector
  버그 아닌 **구조적 metric-design 한계 → P2 with caveat** (claim-clarity 어휘
  가 형식-자질 키워드와 어휘적으로 겹치지 않음). Surface > Content 비대칭 방향은
  smoke 에서 이미 성립.

**cell 12 fix 후 smoke 재계산** (API 0호출, 기존 Stage C jsonl 재처리):
organization_1 non-empty 설명 0.400→0.667 / 설득 0.533→0.733 (dis_nonSBERT
+4/+3 cells). expression_2·content_1 불변. axes (f)(h) 여전히 FAIL (예상대로),
axis (g) PASS 유지. → 80% engineering-QA 임계는 미달이나, 미달분은 위 한계로
문서화. (v2.6 §11.1: engineering-QA threshold ≠ theoretical threshold.)

**Coder A/B 라벨 정리**: 실제 반환 파일 `coder_a_[Coder A / domain expert].csv` /
`coder_b_[Coder B].csv` 가 ground truth (사용자 결정 2026-05-29). 2026-05-28
*의도* 할당 (A=[Coder B]/B=[Coder A / domain expert]) 과 스왑됨 — A/B 는 파일 식별자일 뿐 의미 없고
independence (둘 다 비-제1저자) 불변. 문서 정정: `progress.md` 4.3-4.4,
`CLAUDE.md` gate #5, `memory/project_coder_b_assignment.md`. **미정정 (배포/
historical artifact, 후속 사용자 판단)**: `AES_재포지셔닝_계획_v2.6.md` §618
책임자 줄, `reports/stage4_llm/keyword_blind_audit/coders/{README,instructions}`.

**갱신 파일**: `src/alignment/llm_family_detector.py` (cell 12 fix),
`tests/test_llm_family_detector.py` (회귀), `reports/stage4_llm/smoke_test/
dictionary_coverage__{설명,설득}.md` (재계산), `progress.md`·`CLAUDE.md`·
`memory/*`. **무변경 확인**: `KEYWORD_SET`, `PREREG_BASELINE_SHAS`, 3개
pre-reg SHA-lock 파일.

---

## Blind audit → Detector miss diagnostic spot-check 전환 (2026-05-28, plan §41)

**현행 결정**:
- v2.6 §4.1.2.1 (d) 의 *random 2-coder blind-audit-as-gate* (Cohen's κ ≥ 0.70
  / family 별 ≥ 0.60 을 본 실행 진입 gate 로) 를 **detector miss diagnostic
  spot-check** 로 전환 (§4.1.2.1 (d′) amendment).
- **사유**: `F_LLM` 은 deterministic exact-match metric. (1) 인간이 random
  sample 에서 keyword presence 를 재현하는 것은 기계 detector 와 redundant,
  (2) content trait 의 near-zero prevalence 에서 inter-coder κ 는 통계적으로
  degenerate. 비-redundant 가치는 "strict match 가 사람 눈에 명백한 family
  호출을 놓치는가" 진단 하나.
- **설계**: 기계 detector = 결정론적 operational scorer (F_LLM 산출 주체; gold standard 아님). 인간 = detector miss 진단
  spot-check (대체 아님). Sample = 3 analyzed trait 의 detector empty *failure*
  cell ~15 + detector-positive *control* cell ~5 blind 혼합 (seed=42). 핵심
  산출 = detector miss rate (human=1 ∧ machine=0) / false-positive rate.
  **κ≥0.70 은 더 이상 gate 아님** (2명 coder 시 descriptive only).
- **고려했으나 비채택**: R1 (full 2-coder + machine 3-way agreement audit,
  random 160행) — redundancy 잔존; R2 (별도 semantic validation study) —
  off-purpose; R3 (v1.3 §7 자체 수정) — SHA cascade 부담.
- **Pre-registration 처리**: `main_contrast_preregistered_v1.3.md` §7 의 κ gate
  는 사전등록 *의도* 로 **보존** (SHA `c6c58acd…` 무변경, `PREREG_BASELINE_SHAS`
  cascade 없음). 본 전환은 그로부터의 *documented deviation* — 모델 deviation
  (4.6→4.5) 과 동일 패턴. lock 문장 paper methods 게재:
  "Human coding was used only as diagnostic spot-check, not as replacement for
  F_LLM." / "Because F_LLM is deterministic, inter-coder κ is not treated as a
  primary validity gate."

**갱신 파일**: `AES_재포지셔닝_계획_v2.6.md` §4.1.2.1 (d′), `progress.md` §0 +
Phase 4, `scripts/build_blind_audit_sample.py` (spotcheck mode + machine_truth +
strata), `scripts/keyword_blind_audit.py` (detector miss/FP, κ gate 제거),
`reports/stage4_llm/keyword_blind_audit/coders/` (README + instructions),
`tests/test_detector_spotcheck.py` (신규). v1.3 / pre-reg SHA 무변경.

---

## Blind audit Coder A 변경 — independence 강화 (2026-05-28)

**현행 결정**:
- v2.6 §4.1.2.1 (d) blind audit 의 **Coder A 를 [author] → [Coder B] ([institution])** 으로 교체. [Coder B]은 제1저자와 동일 기관이나 claim 저자 아니므로 coding 독립성 충족.
- **사유**: 제1저자 ([author]) 가 본인이 제기하는 claim 의 dictionary 를
  직접 coding 하면 *independence 위배 (conflict of interest)* 리스크. 두 coder
  ([Coder B] + [Coder A / domain expert]) 모두 제1저자 아닌 협력자로 구성하여 audit 독립성 확보.
- [author] 는 연구 설계·결과 분석·adjudication 감독 역할 (coding 미참여).
- 동일 원칙을 720-cell main 4-level coding (v2.6 §14) 에도 적용 — [Coder B]
  (Coder A) + [Coder A / domain expert] (Coder B) + Coder C adjudicator.

**갱신 파일**: `AES_재포지셔닝_계획_v2.6.md` §4.1.2.1 (d) + 인적 코딩 계획,
`progress.md` Phase 4.3, `reports/stage4_llm/keyword_blind_audit/coders/`
(README + instructions), `scripts/build_blind_audit_sample.py` docstring,
`memory/project_coder_b_assignment.md`. v2.1-v2.4 archive 는 과거 버전 보존
위해 미변경. pre-reg 파일 (decision_table, family_rubric_mapping) 의 [author] 는 *제1저자* 맥락이므로 미변경 (SHA 보존).

---

## Smoke test 실행 + axes 결과 (2026-05-28)

**현행 결정**:
- Phase 1 prep 5 gates ALL PASS (2026-05-26)
- Phase 2 smoke 90/90 PASS, failures 0 (2026-05-28)
- Phase 3 axes (a)-(e)(g) PASS; **(f)(h) 임계 미달** — 분석 대상 3 trait
  의 F_LLM non-empty rate 가 v2.6 §8.2 (f) 80% 임계 미달, 특히 content_1
  거의 0% detection. (h) median A = 0.000 이탈.
- Phase 4 blind audit 진행 결정 보류 — Coder A/B ([Coder A / domain expert]) 작업 후 κ 결과로
  P1 (dictionary 재검토) vs P2 (본 실행 진행) 결정.

**Stage 4 driver fixes 6건** (smoke 통과를 위한 patch):
- F1 fence-strip / F2 prefill / F4 span repair
- Stage A 따옴표 escape / Stage B span_ref prune
- `_record_error` 경로 fix / `STAGE4_MAX_TOKENS=8000` / Kiwi 캐시
- pytest 57/57 passed

**모델 deviation 보존**:
- `MODEL_ID_MAIN = claude-sonnet-4-5-20250929` (4.6 alias-only 회피, v2.6 §1.1
  재현성 우선 원칙. v1.3 SHA `c6c58acd…` 보존, 각주 deviation 6 파일 cascade)

---

## v2.6 / v1.3 addendum (2026-05-25)

**현행 결정**:
- 본문 strong claim을 Surface(`expression_2`) > Content(`content_1`)
  SHAP-LLM family Jaccard asymmetry로 축소.
- Discourse(`organization_1`)는 exploratory only로 분리하고 abstract/intro
  핵심 기여 문장에서 제외.
- score-level agreement는 XGBoost OOF vs Sonnet Stage B QWK premise check로
  제한하고, V1/V2/V3 headline weakening을 적용.
- `main_contrast_preregistered_v1.3.md`를 신설해 `F_SHAP`, `F_LLM`, keyword
  governance, smoke 9-axis, blind audit, 통계 gate를 동결.
- Stage 5 SHA guard가 v1.1/v1.2/v1.3 세 preregistration 파일을 모두 확인.

**v2.3에서 폐기 또는 격하된 부분**:
- broad triangulation claim과 deployment guideline 표현.
- mixed model primary 분석 지위. 현재는 appendix robustness 전용.
- full 3-tier ordering strong claim. 현재는 Surface-Content strong,
  Discourse exploratory.

---

## v1 → v2 (1차 개정, 2026-04-21 초반)

**당시 결정**: 루브릭 구조 감사 후 설계 확정
- 3축(과목·목적·학교급)에 걸친 20,000건 전체를 원안 범위로 설정
- CV 스킴을 Grade-stratified 5-fold + LOPO 이중으로 확정
- 형태소 분석기를 kiwipiepy로 고정
- SBERT primary/robustness 스택 확정
- 루브릭 key의 세그먼트 3이 영역 코드(1A/1B/1C/1D)임을 확정

**폐기 사유**: v2 범위는 범위가 너무 넓어 trait 해석 체계의 일관성을
유지할 수 없다는 판단이 이어졌다.

---

## v2 → v2.1 (2차 개정)

**당시 결정**: 범위를 의사표현 목적 2종으로 좁혀 목적 간 비교를 주요 기여로 승격
- 정보전달 + 설득, ~16,900건 (당시 추정)
- 친교 및 정서 제외 (구인 이질성)
- 모든 Stage를 목적별 병렬 파이프라인으로 전환
- 노벨티 기여 차원에 "목적 간 일반화" 추가

**폐기 사유**: 사회·과학 교과 데이터 미보유 확인 후 국어과로 범위 재축소.
RQ4(목적 간 비교)를 primary로 뒀던 서술은 리뷰 §6.1 지적에 따라 v2.3에서
secondary로 격하.

---

## v2.1 → v2.2 (3차 개정)

**당시 결정**: 국어과 단독으로 최종 범위 축소
- 국어과 4,860건 (설명 2,709 + 설득 2,151)
- 친교 및 정서 2,468건 제외, 사회·과학 미보유로 제외
- 세 목적 모두 **동일 8-trait 구조 확인** (이전 "목적별 trait 상이" 가정 기각)
- API 비용을 15만 원 수준으로 재산정

**이 결정에서 유지된 부분**: 국어과 단독 범위, 4,860건 규모, 8-trait
단일 구조는 **v2.3에서도 유지**.

**폐기된 부분**:
- §4.5의 "Global SHAP Top-K + 20K coding 직접 결합" 분석 구조
  → v2.3에서 essay × trait 1차 단위 + global 2차 집계로 재설계
- χ² 중심 통계 → ordinal mixed model로 교체
- "구인 타당도 검증" 표현 → "validity argument/evidence 조직화"로 완화
- holistic 재구성 → 본 분석에서 제외, 부록으로 이동
- 정합성 코딩 상/중/하 3수준 → 판정 불가(NA) 포함 4수준

---

## v2.2 → v2.3 (4차 개정, 외부 리뷰 반영)

**당시 리뷰 지적 요약**:
1. alignment를 곧바로 validity 검증으로 해석하는 과잉 주장 위험
2. global SHAP과 essay-level rationale을 한 프레임에 결합하는 분석 수준 혼합
3. χ² 중심 통계 계획의 독립성 가정 위반 가능성
4. 문서 내부 불일치 (trait 구조, pilot 규모, scope 문구)
5. LLM을 "설명"이 아닌 "post-hoc rationale"로 재표기 필요
6. preview embedding의 재현성 리스크

**v2.3의 대응** (상세는 `docs/연구계획서_D_v2.md` 개정 요약 참조):
- 제목과 용어의 주장 수위 완화
- 분석 1차 단위를 essay × trait로 재설계
- Messick 결정표에 indeterminate 범주 추가
- Ordinal mixed model을 주 통계로 채택
- LLM 호출을 점수/증거/근거 3단계로 분리
- preview embedding을 부록 전용으로 격하
- 인간 피드백을 "fallible evidence source"로 재정의
- 해석 식별성의 한계를 §7.6에 명시

**이것이 현행 v2.3**. 이후 추가 개정이 있을 때 이 섹션 아래에 v2.3 → v2.4
블록을 추가한다.

---

## Archived Open Decisions (v2.2 CLAUDE.md 하단에 있던 내용)

리뷰 §8이 지적한, CLAUDE.md 하단에 남아 있던 "Open decisions" 블록의 원문.
v2.2에서 이미 결정이 내려진 후에도 문구가 남아 혼란을 야기한 부분.
아래는 원문 그대로이며, 현재는 **전부 closed/deprecated**.

> Open decisions — check progress.md §11 before Stage 2.2 training
>
> The corpus spans 3 subjects × 3 communicative purposes. The 8 TRAITs in
> `configs/paths.py` assume the "설명" rubric. Before running Stage 2.2
> on the full corpus, inspect:
>
>     reports/stage1/corpus_composition.csv
>     reports/stage1/rubric_by_purpose.csv
>     reports/stage1/trait_presence_by_purpose.csv
>
> and confirm study scope with the user (options A–D in progress.md §11).
> The current provisional default is **option B** (설명 purpose only, all subjects).

**현 상태** (v2.3):
- 범위는 국어과 × (설명 + 설득)로 최종 확정 (v2.2에서 결정됨)
- TRAITS는 세 목적 공통으로 확인되어 `configs/paths.py` 단일 정의로 족함
- progress.md §11은 더 이상 존재하지 않음; 현행 §6에서 계속 관리되는
  미결 결정(설득 trait 구조 재확인 등)은 이미 반영 완료

---

## Pre-registration document evolution (2026-04-21 → 2026-05-15)

연구계획서 v2.3는 동결 상태이나, **두 사전등록 stub 파일 (`decision_table_
preregistered.md`, `family_rubric_mapping_preregistered.md`)은 별도의 버전
체계로 진화**. 본 evolution은 본문 framing의 점진적 강화 — methodology decisions
(§3 numeric values) 자체는 v0.1 이래 변경 없음.

| 버전 | 일자 | 핵심 변화 |
|---|---|---|
| 0.1 (draft) | 2026-04-21 | 스텁 작성, v2.3 §4.5.2 / 부록 C 원문 복제 |
| 0.2 (review-assigned) | 2026-04-24 | 합의 참여자 3인 ([author] + [Coder A / domain expert] + [redacted]) 지정; Path β (AIED venue, internal consensus only) 결정 |
| **1.0 (internal consensus)** | 2026-05-13 | [Coder A / domain expert] review (`review 1.txt`) 도메인 검토 회신 반영 + [redacted]의 detailed stat review decline → **Plan B 채택**: §3-4 조작화 내용 v0.2 그대로 동결 + 부록 D self-audit 계획 신설 |
| 1.1 family_rubric_mapping (citation audit) | 2026-05-14 | 박영목 (1999) → 박영목 (2008) 5건 + 권순희 외 (2019) → 권순희 외 (2018) 2건 citation year 정정 |
| **1.1 decision_table / 1.2 family_rubric_mapping (post-V1/V2/V3 reference verification)** | 2026-05-15 | 6 methodology pillar 23 reference 검증 (Fabrication 0건). Framing 강화: (a) §1.1 Indeterminate novel category 정당화 (Kane 2013 "warrant not evaluable" analogous), (b) §3.1 τ/Jaccard 0.5 cutoff을 "pre-registered conservative working threshold"로 reframe (Nogueira 2018 misattribution 정정), (c) §6 audit trail에 reference verification 결과 + 신규 reference (Ferrara 2022 / Chen 2020 / Taghipour & Ng 2016) 추가 |

전 단계 SHA-256 audit trail은 `reports/snapshot_registry.md` 참조. 현 Stage 5
baseline:
- `decision_table_preregistered.md` v1.1: `490df99a0b495028a166170ab7c31b59807ba0c4fd82d71f3908ecb7586d101f`
- `family_rubric_mapping_preregistered.md` v1.2: `5f8e5a72c12e33b01dfe49c08e3686ca89c383ea37000af224fd88fbb614139c`

이 두 SHA는 `src/alignment/matrix.py::PREREG_BASELINE_SHAS`에도 hardcode되어
Stage 5 entry에서 자동 drift 검출 (D4 SHA drift guard, 2026-05-15 활성화).

---

## Stage 4 model decision evolution

| 날짜 | 결정 | 근거 |
|---|---|---|
| 2026-04-24 | Sonnet main + Opus sensitivity (SOTA review.md 강화형 Option C) | cost-efficient main + 1,000 stratified audit |
| **2026-05-15** | **Sonnet 4.6 / Opus 4.6 채택 (4.7 아님)** + **Batch API 권장** | 4.7 토크나이저 inflation 회피 ($30-50 절감); Batch 50% 할인 ($661-$753 → $331-$377); AES 정확도 4.6 vs 4.7 차이 미보고 (Farag 2018, Mizumoto & Eguchi 2023) |

자세한 운영 가이드는 `progress.md` §0 "Stage 4 진입 가이드"; 결정 근거는
`memory/project_stage4_model_decision.md` 참조.
