# Pre-registered Messick Decision Table

**Status**: **Internal methodological consensus document** (v1.1 2026-05-15
확정 — v1.0 2026-05-13 기준 + V1/V2/V3 reference verification 후속 framing 강화).
팀 내부 review·drift 방지 목적. AIED (Springer LNCS conference /
IJAIED) 투고 scope에서 외부 formal pre-registration (git commit, OSF
registration, DOI 발급)은 venue 요구사항이 아니므로 수행하지 않음. 향후
SSCI venue (Assessing Writing, Language Testing 등) 재투고 결정 시 이 파일을
그대로 OSF에 업로드하여 formal pre-registration으로 upgrade 가능
(subset→superset 관계).

Stage 5 실행 중 본 파일 수정 금지 — 수정 시 Stage 5 결과 폐기 + adjudication
log 기록 후 재실행 원칙 유지 (venue 무관 방법론적 규율).

**근거**: 연구계획서 v2.3 §4.5.2

**팀 합의 최종 확정일**: 2026-05-13 ([Coder A / domain expert] review 수신 + [redacted]의
detailed stat review decline 수신 후 [author] 동결)

---

## 1. 배경

본 결정표는 각 essay × trait 셀에서 관찰된 세 가지 설명 체계 증거(SHAP family 귀인, LLM-generated rationale 4수준 코딩, 인간 피드백 4수준 코딩)를 네 가지 해석 범주 중 하나로 잠정 분류하기 위한 **사전등록된 규칙**이다. 이 결정표는 **탐색적 분류(exploratory attribution)**를 위한 것이며 확정적 판정이 아니다(§7.6).

### 1.1 Indeterminate novel category 정당화 (v1.1 post-V1/V2/V3 verification 추가)

본 결정표의 4 categories 중 **Indeterminate**는 Messick (1989)의 standard 3
categories (Aligned/UR/CIV)에 본 연구가 추가한 **novel category**임. AES
validity 선행 문헌 (Ferrara, Steedle, Berkowitz, & Sweet, 2022 *JEM*;
Williamson, Xi, & Breyer, 2012 *EMIP*) 검토 결과 "Indeterminate"를 first-class
validity category로 채택한 선례 없음.

**정당화**:
- Kane (2013) *JEM* validity argument framework의 "warrant not evaluable" 개념과
  analogous — 증거 chain (scoring → generalization → extrapolation → implication)
  중 어느 단계라도 증거가 상충하거나 신뢰할 수 없으면 보수적으로 판정 보류.
- v2.3 §5.4 "fallible evidence source" framing의 직접 적용 — 인간 피드백·
  LLM rationale·SHAP 귀인 각각이 fallible source임을 전제로 하면, 세 증거의
  수렴/분기 패턴 중 "수렴 안 됨 + 신뢰할 수 없음" 영역은 별도 처리해야 함.
- Stage 1.1a 결과 (14/16 trait QWK<0.70)에서 보듯, 인간 기준 자체가 substandard
  reliability를 갖는 trait에서 Aligned/UR/CIV 셋 중 하나로 강제 분류하는 것은
  measurement error를 무시하는 결정. Indeterminate은 이런 셀의 honest
  classification.

**해석적 함의**: Indeterminate 비율 자체가 본 연구의 **research finding**으로
보고됨 — "어느 trait/영역에서 SHAP·LLM·human 증거 chain이 가장 fragile한가"의
경험적 답. 단순 "noise" 또는 "분류 실패"로 해석되지 않음.

## 2. 결정 규칙 (v2.3 §4.5.2 사전등록 원문)

| 조건 | 잠정적 해석 |
|---|---|
| 세 증거가 모두 rubric-relevant 요소를 지시 → **수렴** | **상대적으로 정합 (Aligned)** |
| 인간 피드백 + LLM rationale이 동일 요소를 반복 지시하는데, 해당 요소가 SHAP 상위 family에 **지속적으로 나타나지 않음** | **Construct underrepresentation (UR)** 가능성 |
| SHAP 상위 family가 길이·표면 빈도·프롬프트 특이 proxy에 과도 집중하고, 인간 피드백·LLM rationale이 그 요소를 **정당화하지 않음** | **Construct-irrelevant variance (CIV)** 가능성 |
| 세 증거가 모두 불안정하거나 상충하여 귀속 불가 | **Indeterminate** |

## 3. 조작화

### 3.1 "지속적으로 나타나지 않음" (UR 조건)

다음 두 기준 중 **적어도 하나 이상**이 만족될 때 "지속적 부재"로 판정:

- **Fold 간 Kendall τ < 0.5** (§4.2.3 안정성 지표) — 5-fold × trait에서 family rank의 안정성이 낮음
- **Embedding 간 Jaccard < 0.5** (Top-K=3) — primary와 robustness_1 사이 Top-3 family 집합의 overlap이 낮음

**임계치 정당화 (v1.1 post-V1/V2/V3 verification 명시)**:
Nogueira, Sechidis, & Brown (2018) *JMLR* 18(174), 1–54는 SHAP feature ranking
stability *measure* + CI를 제공하나 **specific numeric cutoff (예: τ ≥ 0.5,
Jaccard ≥ 0.5)을 prescribe하지 않음**. 본 연구의 0.5 cutoff은 **pre-registered
conservative working threshold**이며, 다음 두 근거에 기반:
- Top-K=3 Jaccard 0.5는 수학적 중간값 (2개 일치) — Top-3 family 집합 중
  과반수 overlap 요구.
- Stage 3 (2026-04-23) 관측 분포 (τ_mean 0.643–0.943, Jaccard primary↔robust_1
  J_mean 0.89–1.00 vs primary↔robust_2 0.61–0.67)에서 0.5는 "stable" vs
  "unstable" 분기점.

부록 D §1에서 0.3/0.5/0.6 임계치 sensitivity 보고. 본 cutoff을 community
standard로 attribute하지 않음 — Nogueira et al. 2018 framework은 stability
metric으로만 인용.

**주의**: 두 지표 모두 "해당 trait에 대해 어떤 family가 중요한가"가 불안정한 상태를 의미한다. 여기에 더해 **인간 피드백 + LLM rationale에서 반복 지시되는 요소**의 family(부록 C 매핑)가 상기 불안정 또는 하위 랭크에 머무를 때 UR로 분류한다.

### 3.2 "정당화하지 않음" (CIV 조건)

LLM rationale과 인간 피드백의 코딩 단위에서, SHAP 상위 family에 매핑되는 어휘·증거 유형의 출현 비율이 **10% 이하**일 때 "정당화 부재"로 판정. 부록 C의 "비매핑 family (negative cue)"가 SHAP 상위에 나타나는 경우도 CIV 경고 신호로 간주한다.

### 3.3 "상충하여 귀속 불가" (Indeterminate 조건)

다음 중 **둘 이상** 만족 시 Indeterminate:
- §3.1의 안정성 지표 둘 다 불만족 (Kendall τ < 0.5 AND Jaccard < 0.5)
- LLM rationale 4수준 코딩이 "판정 불가(NA)"
- 인간 피드백 4수준 코딩이 "판정 불가(NA)"
- 인간 피드백의 trait 순수성 사전 점검(§4.6.1)에서 해당 trait의 피드백이 50% 이상 다른 trait 내용과 혼입

### 3.4 "수렴" (Aligned 조건)

- SHAP 상위 3개 family 중 **적어도 하나**가 부록 C의 해당 rubric 영역 "일차/이차 매핑 family"에 해당
- LLM rationale 코딩 = 상(2)
- 인간 피드백 코딩 = 상(2) 또는 중(1) (인간 기준 완화 허용; 리뷰 §5.4 수용)

## 4. 범주 간 우선순위

여러 조건이 동시에 해당할 경우:
1. **Indeterminate**가 최우선 — 세 증거 중 하나라도 신뢰할 수 없으면 보수적으로 판정 불가로 귀속
2. 그 다음 **UR/CIV** 분기
3. 마지막으로 **Aligned**

## 5. Stage 5 실행 시 체크리스트 (internal consensus scope)

AIED 투고에서는 외부 timestamp (git commit, OSF) 미요구이나, 팀 내부 drift
방지를 위해 다음 절차 유지:

- [x] 본 파일의 v1.0 SHA-256을 `reports/snapshot_registry.md`에 팀 합의 확정일 (2026-05-13)과 함께 기록 — v1.0 row 추가됨
- [ ] Stage 5 분석 스크립트(`src/alignment/matrix.py`) 시작 시 본 파일의 현재 hash와 snapshot hash를 대조하여 불일치 시 중단
- [ ] 결정표 수정이 불가피한 이유가 발견되면, **Stage 5 결과는 폐기**하고 수정 사유를 adjudication log에 기록한 후 재실행
- [x] 합의 참여자 review·confirm 1 copy 보관: `review 1.txt` ([Coder A / domain expert] 2026-05-13). [redacted] 회신은 detailed stat review decline (2026-05-13) — 본문 §6 audit trail 참조

## 6. 통계 review decline + 부록 D self-audit (v1.0 audit trail)

**Event log**:
- 2026-04-24: 합의 참여자 2인 지정, v0.2 draft 두 분께 송부
- 2026-05-13: [Coder A / domain expert] `review 1.txt` 회신 — `family_rubric_mapping_preregistered.md`
  v1.0에 반영 (해당 파일 §1·§2 footer·§3·§5 보강). 본 파일 §3-4 조작화는 review 영역 외라 변경 없음.
- 2026-05-13: [redacted] 회신 — "본 수준의 detailed stat questions에 대해
  답할 자신이 없음"으로 detailed stat review declined. Acknowledgments 문구는
  "methodological review"에서 "methodological consultation"으로 약화하여 유지
  (review 시도 사실은 인정).

**Plan B 결정 (2026-05-13, [author])**: 본 v1.0은 §3-4 조작화 내용을 v0.2에서
변경 없이 동결한다. 대신 §3.1-3.4의 임계치 4건에 대한 **본 연구 자체 sensitivity
분석을 부록 D self-audit으로 추가**한다 (Stage 5 결과 후 실행):

1. **§3.1 안정성 임계치 (Kendall τ < 0.5, Jaccard < 0.5)** — 0.3/0.5/0.6
   임계치별 UR 후보 셀 수 변동표. (Stage 3 결과상 0/72 unstable이라 현
   임계치에서 UR 후보 0건; sensitivity 임계치에서도 변동 관측 가능성 낮음)
2. **§3.2 정당화 부재 조건 (매핑 어휘 출현 비율 10%)** — 5%/10%/15%/20%
   임계치별 CIV 후보 셀 수 변동표. (Stage 4.3 코딩 완료 후 실행 가능)
3. **§3.3 Indeterminate 결합 규칙 ("둘 이상" 만족)** — 4개 조건의 pairwise
   dependence 분석 + "한 가지" vs "둘 이상" vs "셋 이상" Indeterminate 비율
   변동표.
4. **Fallibility weighting (`triangulate.py`의 `w_reliability = clip(QWK/0.70,
   0.20, 1.00)`)** — cutoff 0.50/0.60/0.70 × floor 0.10/0.20/0.30 grid 9
   조합 × Indeterminate ratio 표.

추가 self-audit ([redacted]가 응답할 경우 review 영역 밖이었지만 본 연구
robustness 강화 목적):

5. **v2.3 §4.5.3 ordinal mixed model 3-way interaction 식별성** — 3-way
   interaction(`purpose * rubric_domain * explanation_system`) 대 2-way 축소
   모델 (`purpose × explanation_system` 단독, AIC/BIC 비교) — `clmm` 수렴
   안정성 진단.
6. **Multiple comparison 보정** — 16 traits × 2 purposes × 3 systems × 4
   categories에서 FDR-BH 보정 전후 trait-level significance 변동표.

**구현 위치**: `src/stats/decision_sensitivity.py` 신설 (Stage 5 결과 후 추가).
부록 D 보고서: `reports/appendix_d_self_audit/sensitivity.md` 신설 예정.

**Path α upgrade 시 재engagement 정책**: 다른 venue (Assessing Writing 등 SSCI)
재투고 결정 시 외부 통계 reviewer 재engagement 또는 second methodology reviewer
신규 발굴 권장. 본 부록 D 결과를 reviewer comment 사전 답변 자료로 활용 가능.

### 2026-05-15 V1/V2/V3 reference verification 후속 (v1.1)

6 methodology pillar 23 reference 검증 (V1: P1 inter-rater + P2 AES QWK / V2:
P3 SHAP stability + P4 multiple comparison / V3: P5 ordinal mixed model + P6
validity framework). 결과:
- **Fabrication 0건**. 모든 reference 존재 verification ✓.
- **NOT_STANDARD operational claim 2건 식별**:
  - **τ/Jaccard 0.5 cutoff (§3.1)**: Nogueira et al. 2018 framework은 stability
    metric만 제공, specific cutoff 미prescribe. → §3.1에 정당화 단락 추가 (위
    `**임계치 정당화 (v1.1 ...)**` 블록), pre-registered conservative working
    threshold로 reframe.
  - **Indeterminate 4th category (§1)**: AES validity 선행 문헌 무선례.
    → §1.1 신설로 Kane (2013) "warrant not evaluable" analogous 정당화.
- **권장 추가 reference (연구계획서 §8에 추가됨)**:
  - **Ferrara, S., Steedle, J. T., Berkowitz, M., & Sweet, S. J. (2022).
    Validity arguments for AI-based automated scores: Essay scoring as an
    illustration.** *Journal of Educational Measurement, 59*(3), 288–313. —
    본 연구의 직접 AES validity argument precedent.
  - **Chen, H., Janizek, J. D., Lundberg, S., & Lee, S.-I. (2020). *True to
    the model or true to the data?*** arXiv:2006.16234 — SHAP interventional
    vs conditional 논쟁 정리, P3 강화.
  - **Taghipour, K., & Ng, H. T. (2016). A neural approach to automated essay
    scoring.** *EMNLP 2016* — rint+clip+QWK workflow canonical 근거, P2 강화.
- **C.10 deferred**: AERA Standards 2014 인용에서 FDR-BH 정당화 제거는 부록 D
  본문(`reports/appendix_d_self_audit/sensitivity.md`) 작성 시점에 적용 — 현재
  파일 미존재로 본 v1.1에서 미적용.

§3.1–3.4 조작화 본문 numeric value (10%, 0.5, "둘 이상" 등) 변경 없음 —
framing·정당화만 강화.

## 7. 버전 이력

| 버전 | 일자 | 변경 |
|---|---|---|
| 0.1 (draft) | 2026-04-21 | 스텁 작성 (v2.3 §4.5.2 원문 복제) |
| 0.2 (review-assigned) | 2026-04-24 | 합의 참여자 2인 지정: [Coder A / domain expert]([institution]), [redacted]([institution]). 내용 수정 없음 |
| 1.0 (internal consensus, superseded by v1.1) | 2026-05-13 | [Coder A / domain expert] review 회신 (review 1.txt) + [redacted]의 detailed stat review decline 수신 후 동결. §1-4 조작화 내용 v0.2에서 변경 없음. 변경 사항: ① Status block을 v1.0으로 표기, ② 팀 합의 최종 확정일 = 2026-05-13, ③ 합의 참여자 메모에 두 reviewer의 회신/decline 사실 명시, ④ Acknowledgments 문구를 "methodological review" → "methodological consultation"으로 약화, ⑤ §5 체크리스트 일부 완료 상태로 갱신, ⑥ §6 신설: Plan B 결정 audit trail + 부록 D self-audit 계획 (`src/stats/decision_sensitivity.py` 신설 예정). AIED 투고 scope 기준 최종판, git commit·OSF 미수행 |
| **1.1 (post-V1/V2/V3 reference verification)** | **2026-05-15** | **§1.1 신설: Indeterminate 4th category novel contribution 정당화 (Kane 2013 "warrant not evaluable" analogous, Ferrara 2022 / Williamson 2012 AES 선행 무선례 명시). §3.1 임계치 정당화 단락 추가: τ/Jaccard 0.5 cutoff을 Nogueira 2018 attribution에서 "pre-registered conservative working threshold"로 reframe. §6 audit trail에 V1/V2/V3 검증 결과 + 추가 reference (Ferrara 2022 / Chen 2020 / Taghipour & Ng 2016) 명시. §3.1–3.4 조작화 본문 numeric value 변경 없음 — framing·정당화만 강화. AIED 투고 scope 기준 최종판. SHA baseline `reports/snapshot_registry.md` 참조** |
| (옵션) 1.1+OSF | — | 다른 venue 재투고 결정 시 OSF registration upgrade + 외부 통계 reviewer 재engagement 권장 |
