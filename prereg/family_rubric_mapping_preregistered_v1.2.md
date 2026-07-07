# Pre-registered Feature Family ↔ Rubric 영역 매핑

**Status**: **Internal methodological consensus document** (v1.2 2026-05-15 확정 — v1.0 2026-05-13 기준 + v1.1 citation audit + v1.2 post-V1/V2/V3 reference verification framing 강화).
팀 내부 review·drift 방지 목적. AIED (Springer LNCS conference / IJAIED) 투고
scope에서 외부 formal pre-registration (git commit, OSF registration, DOI 발급)은
venue 요구사항이 아니므로 수행하지 않음. 향후 SSCI venue (Assessing Writing,
Language Testing 등) 재투고 결정 시 이 파일을 그대로 OSF에 업로드하여 formal
pre-registration으로 upgrade 가능.

Stage 5 실행 중 본 파일 수정 금지 — 수정 시 Stage 5 결과 폐기 + adjudication
log 기록 후 재실행 원칙 유지.

**근거**: 연구계획서 v2.3 §4.5.1, 부록 C

**팀 합의 최종 확정일**: 2026-05-13 ([Coder A / domain expert] review 회신 반영 후 [author] 동결)

---

## 1. 배경

본 매핑은 SHAP 귀인(피처 family 단위)을 루브릭 영역(1A–1D)과 대조하여 **"SHAP 상위 family가 해당 영역의 평가 기준과 의미적으로 부합하는가"**를 판정하기 위한 **사전등록된 이론 기반 매핑**이다. 이 매핑은 연구자 전문 판단에 기반하며, 판정 후 사후 수정 불가.

**본 매핑의 해석 수위 (v1.0+ 명시; v1.1에서 그대로 유지)**: 각 family는 해당 rubric 영역의 평가 구인
**전체가 아니라 측정 가능한 일부를 대리**한다 ([Coder A / domain expert] 2026-05-13 review 권고).
형태소 분석·임베딩 기반 피처 family는 의미적 판단(주제 명료성, 사실 정확성,
사고 창의성 등)을 직접 측정하지 못하며, 본 매핑은 이러한 한계 안에서 정의된
proxy 매핑이다. 자세한 대리 범위는 §3 각 영역별 "대리 범위" 항목 및 §5의 한계
서술 참조.

## 2. 매핑 표 (v2.3 부록 C 원문)

| 루브릭 영역 | 일차 매핑 family | 이차 매핑 family | 비매핑 family (negative cue) |
|---|---|---|---|
| **`1A` task** (과제 이해·반영) | `meta`, `morph_prop` (종결 어미) | `syn` | — |
| **`1B` content** (내용) | `lex`, `dis_SBERT` | `morph_prop` (명사·체언) | `meta` (길이) |
| **`1C` organization** (조직) | `dis_SBERT`, `dis_nonSBERT` | `syn` (연결·종결 어미) | `meta` (길이) |
| **`1D` expression** (표현) | `syn`, `morph_prop` (어미) | `lex` (TTR) | `dis_SBERT` |

**표 footer (v1.0+ 명료화; v1.1에서 그대로 유지)**:
- 1C organization 이차 매핑의 `syn`(연결·종결 어미 분포)은 `morph_prop`의 접속·연결 어미 비율과 부분 중첩한다. [Coder A / domain expert](2026-05-13) review의 대안② ("접속어미를 조직 영역에 추가 — 부분적으로 타당하나 보조적 역할에 그칠 것") 지적에 따라, `syn`의 어미 계열 분포를 1C 이차 매핑의 보조적 지표로 해석하며, `morph_prop` 접속·연결 어미를 별도 이차 매핑으로 추가하지는 않는다 (조직 평가의 구조적 완결성·문단 통일성은 어미 빈도로 포착되지 않으므로).
- 1B content의 비매핑 `meta`(길이)는 [Coder A / domain expert](2026-05-13) review의 대안① ("글 길이를 내용 2차에 포함 — 동의 어려움") 지적에 따라 **v1.0에서도 비매핑 유지**. 글이 길다고 내용이 풍부한 것은 아니라는 reviewer 판단이 사전 결정과 부합.
- 1D expression의 비매핑 `dis_SBERT`는 reviewer의 대안③ ("접속부사 밀도를 표현에 포함 — 동의 어려움, 조직과 중복") 지적과 별개 항목이나, 같은 원리(범주 혼동 방지)에 따라 비매핑 유지.

## 3. 매핑 근거 (이론 기반)

### 3.1 `1A` task — 과제 이해·반영

**NIA 14-026 루브릭 정의 (dataset verbatim)**:
- 성취기준: "제시된 의사소통 맥락과 조건(지시문의 요구와 조건)에 맞게 과제를 수행했는가?"
- `task_1` 과제 수행의 충실성 (설명·설득 공통 trait):
  - 5점: "제시된 의사소통 맥락과 조건을 고려하여 과제를 탁월하게 수행한다."
  - 1점: "제시된 의사소통 맥락과 조건을 고려하지 못하고 과제 수행도 미흡하다."
  - 설득 trait는 동일 descriptor에 "설득적 뉘앙스" 강도 표현이 추가됨 (수술적 패치 적용).

**매핑 근거**:
- **일차**: `meta`(글 전체 규모: 글자/어절/문장 수)는 과제 요구에 비례한 기본 응답 여부의 지표. `morph_prop`의 종결 어미 패턴(평서/의문/명령/청유)은 과제가 요구하는 글의 양식(설명체/주장체)을 반영.
- **이차**: `syn`(동사·형용사·명사 비율, 어미 계열)은 과제 장르 특성 반영.

**대리 범위 (proxy coverage)**:
- *본 매핑이 대리하는 측면*: 과제 응답 여부(분량), 글의 양식(설명체/주장체 종결어미).
- *본 매핑이 대리하지 못하는 측면*: 과제가 요구하는 **내용·방향이 글에 반영되었는지** 여부 (의미적 판단). [Coder A / domain expert](2026-05-13) review 지적과 일치: "'우리 동네의 자랑거리를 소개하는 글을 쓰시오'라는 과제에서 종결어미를 설명체로 맞췄더라도 자랑거리가 아닌 내용을 썼다면 과제를 제대로 이해한 것으로 보기 어렵다." Stage 5 해석 시 이 한계를 명시하여 1A 영역에서 SHAP가 일차 매핑과 부합하더라도 "과제 내용 반영" 측면은 LLM rationale·인간 피드백 검토를 통해 보강 판정해야 함.

### 3.2 `1B` content — 내용

**NIA 14-026 루브릭 정의 (dataset verbatim)**:
- 설명 trait:
  - `content_1` 설명의 명료성: "설명하고자 하는 대상에 초점을 맞추어 내용을 [탁월하게/충실하게/...] 제시한다."
  - `content_2` 설명의 구체성: "풍부하고 구체적인 세부 내용을 제시하여 대상을 [탁월하게/...] 설명한다."
  - `content_3` 설명의 적절성: "설명하고자 하는 대상의 특성과 부합하는 내용을 [탁월하게/...] 제시한다 (설명대상의 특성 4개 이상)."
- 설득 trait:
  - `content_1` 주장의 명료성: "합리성과 참신성을 고려하여 주장을 명료하게 제시한다."
  - `content_2` 주장의 적절성: "논제를 체계적으로 분석하여 논리적이고 독창적인 주장을 제시한다."
  - `content_3` 근거의 타당성: "주장을 풍부하고 구체적인 근거로 타당하게 뒷받침한다 (근거 4개 이상)."

**매핑 근거**:
- **일차**: `lex`(어휘 다양성: TTR, 엔트로피, 어휘 등급 분포)는 내용의 풍부성과 직결. `dis_SBERT`(문장 간 의미 응집)는 내용의 일관된 전개.
- **이차**: `morph_prop` 중 명사·체언 비율은 주제어의 밀도 지표.
- **비매핑**: `meta`의 **글 길이**만으로 내용 품질을 평가하는 것은 구인 무관 변량(CIV)의 전형.

**대리 범위 (proxy coverage)**:
- 박영목(2008, 작문교육론 p.308)이 제시한 내용 평가 5기준 — 풍부성/정확성/연관성/명료성과 타당성/창의성 — 대비 본 매핑의 대리 범위:
  - **풍부성**: `lex`(어휘 다양성·등급)·`vocab_grade`로 *부분* 대리. 단 어휘가 다양하다고 내용이 풍부한 것은 아님 — 주제 무관 단어 다양도 수치를 높이므로 ([Coder A / domain expert] 2026-05-13).
  - **정확성**: *미대리*. 사실 정확성은 형태소·임베딩 기반 피처로 직접 측정 불가.
  - **연관성**: `dis_SBERT`로 *부분* 대리. 단 인접 문장 의미 유사도 측정이라 문단 간/글 전체 논리적 연관성까지 보장되지 않음.
  - **명료성과 타당성**: *미대리*. 의미론적 판단 영역.
  - **창의성**: *미대리*. 의미론적 판단 영역.
- *해석적 함의*: 본 매핑에서 1B 영역의 일차 family가 SHAP 상위에 나타나는 것은 *부분 대리 측면에서의 정합*이지 내용 구인 전체와의 정합이 아니다. Stage 5에서 1B Aligned 판정 시 이 단서를 본문에 명시.
- *재해석 기회*: [Coder A / domain expert](2026-05-13) review의 부차 지적: "이 한계는 형태소 분석 기반 피처가 가진 한계가 아닐까 싶습니다. 그래서 오히려 이 부분이 이 연구가 밝히고자 하는 갈라지는 평가 구인의 증거가 될 수도 있지 않을까라는 생각도 듭니다." — 본 연구의 RQ4 (목적 간 분기 패턴) 해석에 활용 가능.

### 3.3 `1C` organization — 조직

**NIA 14-026 루브릭 정의 (dataset verbatim)**:
- `organization_1` 문장 (및 문단)의 연결성: "소주제를 중심으로 문장과 문단을 체계적이고 논리적으로 구성하고, 문장 간·문단 간 연결이 긴밀하고 자연스럽다."
- `organization_2` 글의 통일성: "글을 체계적이고 논리적으로 조직하여 하나의 주제를 중심으로 통일성을 갖춘 글을 구성한다."

**매핑 근거**:
- **일차**: `dis_SBERT`(인접 문장 응집)와 `dis_nonSBERT`(접속부사·대명사 밀도)는 조직의 논리적 연결성 지표.
- **이차**: `syn`의 연결·종결 어미 분포는 문단 구조 신호. (§2 footer 참고: `morph_prop` 접속·연결 어미와 부분 중첩하나 별도 이차 매핑으로 추가하지 않음.)
- **비매핑**: `meta`의 길이는 조직 품질과 무관.

**대리 범위 (proxy coverage)**:
- *본 매핑이 대리하는 측면*: 인접 문장 의미 응집(`dis_SBERT`), 접속·대명사 밀도(`dis_nonSBERT`), 연결·종결 어미 분포(`syn`).
- *본 매핑이 대리하지 못하는 측면*: 서론·본론·결론의 구조적 완결성, 문단의 통일성 자체(글 전체 주제와의 정합), 문단 간 논리 전개의 적절성. [Coder A / domain expert](2026-05-13) review 대안②에 대한 평가: "조직 평가에서 서론·본론·결론의 구조적 완결성이나 문단의 통일성은 접속어미 빈도로 포착되지 않는다는 점에서, 추가하더라도 보조적 역할에 그칠 것" — 본 매핑의 이차 family들도 이러한 한계 안에서 작동.

### 3.4 `1D` expression — 표현 (어법·어휘)

**NIA 14-026 루브릭 정의 (dataset verbatim)**:
- `expression_1` 어휘 (및 문장)의 적절성:
  - 5점: "어휘 선택이 탁월하고 문장이 어법에 맞으며 **수려하다**."
  - 4점: "어휘 선택이 우수하고 문장이 어법에 맞으며 **자연스럽다**."
  - 3점: "어휘 선택과 문장 표현이 적절하다."
- `expression_2` 어법의 [적절성/정확성]: "[모든 경우/대부분/...] 어법에 맞는 맞춤법과 띄어쓰기를 사용한다."

NIA 1D 정의는 권순희 외(2018, 작문교육론 pp.306–308)가 제시한 표현 영역 정의
("어법 정확성, 어휘의 적절성, 문장의 적절성, 표현의 유창성")의 세 측면을 다음과 같이 포함:
- 어법 정확성 → `expression_2` 직접 정의
- 어휘의 적절성 → `expression_1` "어휘 선택이 탁월/우수/적절"
- 문장의 적절성 → `expression_1` "문장 표현이 적절"
- 표현의 유창성 → `expression_1` 5점/4점 "수려하다/자연스럽다"

**매핑 근거**:
- **일차**: `syn`(어미 계열 비율: 평서/의문/명령/청유 종결, 연결 어미 종류)과 `morph_prop`(어미 태그: EF/EC/ETN/ETM 등)은 한국어 어법 정확성의 직접 지표 → `expression_2` "어법에 맞는 맞춤법과 띄어쓰기"의 형태소 수준 신호로 작동.
- **이차**: `lex`의 TTR·어휘 등급 다양성은 `expression_1` "어휘 선택의 적절성·다양성"의 신호.
- **비매핑**: `dis_SBERT`(인접 문장 의미 응집)는 표현의 정확성·적절성과 직접 관련이 없으며, 표현 영역 SHAP에서 상위에 오면 **CIV 경고**.

**대리 범위 (proxy coverage)**:
- *본 매핑이 대리하는 측면*: 어법 정확성(`syn`, `morph_prop`, `case_marker` 격조사 분포), 어휘 다양성(`lex`, `vocab_grade`).
- *본 매핑이 대리하지 못하는 측면*: 문장 표현의 "수려함"·"자연스러움"(NIA 5점/4점 descriptor 핵심 변별), 어휘 선택의 *적절성*(맥락 적합성, 어휘가 다양하다는 사실과 별개). 권순희 외(2018)의 "표현 유창성"은 의미·문체 차원이라 형태소·구문 피처로 직접 측정 불가.
- *해석적 함의*: SHAP 상위 family가 일차 매핑(`syn`, `morph_prop`)과 부합하더라도, NIA 1D는 단순 어법 정확성보다 **넓은 정의**(수려함·유창성 포함)이므로, Stage 5에서 1D Aligned 판정은 "어법 정확성 축에서의 정합"으로 해석 수위를 제한.
- *CIV 경보 발동 경위*: Stage 3 (2026-04-23) 관찰 결과, 설득 expression rank_1에 `dis_SBERT`, 설명 expression rank_2에 `dis_SBERT`가 등장 — Stage 4 LLM rationale이 이 신호를 "어법" 또는 "수려함"으로 정당화하는지가 UR/CIV 판정의 핵심.

## 4. Stage 5에서의 사용

정합성 판정에서:

1. 각 (essay, trait, purpose) 셀에 대해 trait의 rubric 영역(1A/1B/1C/1D)을 식별
2. 해당 셀의 local family-SHAP Top-3 family 리스트를 추출
3. 다음 중 하나 판정:
   - **일차 매핑 family**가 Top-3에 포함 → Aligned 후보
   - **이차 매핑 family**만 Top-3에 포함 → Aligned 후보 (약한)
   - **비매핑 family(negative cue)**가 Top-3에 포함 → CIV 경고 (의심 셀)
   - 매핑된 family가 Top-3에 전혀 없음 → UR 후보

이 판정은 §4.5.2 결정표의 다른 증거(LLM/인간)와 결합되어 최종 4범주로 귀속된다.
**해석 수위 제한 (v1.0+ 명시; v1.1·v1.2에서 그대로 유지)**: 일차 매핑 family가 Top-3에 포함된 Aligned
판정은 §3의 "대리 범위" 항목에 명시된 *부분 측면에서의* 정합이며, 해당 rubric
영역 구인 전체와의 정합이 아니다. 본문 해석에서 이 단서를 명시한다.

**임계치 출처 명료화 (v1.2 post-V1/V2/V3 verification 명시)**: §3 일차/이차/
비매핑 family와 결합되는 Stage 5 SHAP stability cutoff (τ ≥ 0.5, Jaccard ≥ 0.5
Top-K=3)은 `decision_table_preregistered.md` §3.1에 명시. Nogueira, Sechidis, &
Brown (2018) *JMLR* 18(174) framework은 stability *measure*만 제공하며 specific
cutoff은 prescribe하지 않음. 0.5 cutoff은 본 연구의 pre-registered conservative
working threshold이며 부록 D §1에서 0.3/0.5/0.6 sensitivity 보고.

## 5. 매핑의 한계 (v2.3 §7.6 해석 식별성)

### 5.1 구인 부분 대리 (proxy coverage)

본 매핑은 형태소 분석·임베딩 기반 피처로 구성되어 의미론적 판단(주제 명료성,
사실 정확성, 창의성 등)을 직접 측정하지 않는다. §3 각 영역의 "대리 범위"
항목에 명시되어 있듯이, 본 매핑이 대리하는 측면과 대리하지 못하는 측면을
박영목(2008) 내용 평가 5기준에 따라 요약하면:

| 박영목(2008) 내용 5기준 | 본 매핑 대리 family | 대리 정도 |
|---|---|---|
| 풍부성 (어휘·어휘 등급 다양도) | `lex`, `vocab_grade` | 부분 |
| 정확성 (사실 기반) | (없음) | 미대리 |
| 연관성 (문장간 의미) | `dis_SBERT` | 부분 (인접 문장만) |
| 명료성과 타당성 (주제 의미) | (없음) | 미대리 |
| 창의성 (사고 참신성) | (없음) | 미대리 |

표현 영역에서는 권순희 외(2018, pp.306-308)의 표현 4기준 — 어법 정확성, 어휘
적절성, 문장 적절성, 표현 유창성 — 중 어법 정확성과 어휘 다양성은 부분 대리
하나, "문장 표현의 수려함·자연스러움"(NIA 1D 5점/4점 핵심 변별)은 미대리이다
(§3.4 참조).

이로부터 다음 두 해석 원칙이 도출된다:

1. **본 연구의 SHAP 귀인 결과는 구인 전체가 아니라 부분 대리 영역에서의
   모델 학습 패턴**이다. Stage 5 Aligned 판정은 이 부분 대리 측면에 한정된
   정합이며, 본문 해석에서 이 한정을 명시한다.
2. **목적 간 분기 패턴 (RQ4)의 해석 기회**: [Coder A / domain expert](2026-05-13) review의
   부차 지적과 같이, 본 매핑의 부분 대리 한계 자체가 두 목적(설명·설득)이
   서로 다른 평가 구인을 강조하는 증거로 해석될 가능성. Stage 5에서 설명·
   설득 간 family 분포 차이를 이 관점으로 보고.

### 5.2 학년 발달 단계 misinterpretation

본 연구는 초등 5학년부터 중학교 3학년까지(5개 학년) 동일한 매핑으로 분석한다.
같은 어휘 다양성(TTR) 수치 또는 어미 비율이 초5와 중3 학생 글에서 갖는 의미는
동일하지 않을 수 있다 — 학생들의 쓰기 발달 단계 차이로 인해 동일 수치가 학년에
따라 다른 평가 함의를 가질 가능성 ([Coder A / domain expert] 2026-05-13 review 추가 지적).

- *부분 통제*: v2.3 §4.5.3 ordinal mixed model의 `(1|grade)` random intercept
  로 학년별 평균 정합도 편차를 흡수한다.
- *미통제*: **매핑 자체가 학년 발달 단계에 따라 다른 구인을 측정한다는 문제**.
  예컨대 초5의 종결어미 패턴은 양식 인식의 신호이지만 중3의 종결어미 패턴은
  문체 의도의 신호일 수 있다. 본 매핑은 이러한 학년별 의미 변동을 구분하지
  않는다.
- *해석적 함의*: Stage 5 분석에서 학년별 정합 패턴 차이가 관찰되면, 이는 단순
  "학년별 모델 성능 차이"로 해석되어서는 안 되며 **매핑 자체의 학년별 구인
  변동 가능성**을 고려해야 한다. 본문에서 이 caveat을 명시한다.

### 5.3 대안 매핑 — robustness 분석 범위

본 매핑 자체가 연구자의 **이론 기반 사전 판단**이며, 다음 대안 매핑이 가능
하다:
- `1B` content에 `meta`를 이차 매핑에 포함할 여지 (길이가 내용 전개의 표지일
  수도). → [Coder A / domain expert](2026-05-13) review 대안① 평가: "동의하기 어렵다." → v1.0
  매핑 비포함 유지.
- `1C` organization에 `morph_prop`(접속 어미)를 추가할 여지. → review 대안②
  평가: "부분적으로 타당하나 보조적 역할에 그칠 것." → §2 footer로 명료화하되
  별도 이차 매핑 미추가.
- `1D` expression에 `dis_nonSBERT`(접속부사 밀도)를 포함할 여지. → review
  대안③ 평가: "조직과 중복." → 매핑 비포함 유지.

이 대안들 자체는 **사전등록 이후 본 매핑에 대한 robustness 분석**에서 부록 D
self-audit 결과로 보고 가능하다 (decision_table v1.0 §3 임계치 sensitivity와
함께). 본 연구의 주 결론과는 **별도로** 보고한다.

## 6. 보호 절차 (internal consensus scope)

AIED 투고에서는 외부 timestamp (git commit, OSF) 미요구이나, 팀 내부 drift
방지를 위해 다음 절차 유지:

- [x] 본 파일의 v1.0 SHA-256을 `reports/snapshot_registry.md`에 팀 합의 확정일
  (2026-05-13)과 함께 기록 — v1.0 row 추가됨.
- [x] v1.1 (citation audit 정정) SHA-256 `reports/snapshot_registry.md`에 추가 — v1.0은 superseded 표기 (2026-05-14).
- [ ] Stage 5 분석 스크립트(`src/alignment/matrix.py`) 시작 시 파일 SHA 대조,
  불일치 시 중단.
- [ ] 매핑 수정 불가피 시 Stage 5 결과 폐기 + adjudication log 기록 + 재실행.
- [x] 합의 참여자 review·confirm 1 copy 보관 (`review 1.txt`, [Coder A / domain expert]
  2026-05-13).

## 7. 버전 이력

| 버전 | 일자 | 변경 |
|---|---|---|
| 0.1 (draft) | 2026-04-21 | 스텁 작성 (v2.3 부록 C 원문 복제 + 근거 서술 추가) |
| 0.2 (review-assigned) | 2026-04-24 | 합의 참여자 2인 지정: [Coder A / domain expert]([institution]), [redacted]([institution]). 내용 수정 없음 |
| 1.0 (internal consensus, superseded) | 2026-05-13 | [Coder A / domain expert] review (`review 1.txt`) 반영. §1에 본 매핑의 해석 수위 명시 추가; §2 표 footer 명료화 (대안 ①②③에 대한 v1.0 처분 명시); §3 각 영역(1A–1D)에 NIA 14-026 dataset verbatim 루브릭 정의 + 대리 범위(proxy coverage) 항목 추가; §4 해석 수위 제한 강조 단락 추가; §5 한계 절을 5.1 구인 부분 대리(박영목 1999 5기준 표) / 5.2 학년 발달 단계 misinterpretation / 5.3 대안 매핑 robustness 세 절로 확장. 본질적 매핑 변경 없음 — 매핑 표 §2는 v0.2 그대로 유지. AIED 투고 scope 기준 최종판, git commit·OSF 미수행 |
| 1.1 initial (citation audit, superseded) | 2026-05-14 | Citation audit 결과 반영 (web verification + 사용자 카탈로그 확인). 박영목 (1999) → 박영목 (2008) — 작문교육론 (역락) 5건 치환 (§5.1 §1·§5 본문 + 표 헤더). 권순희 외 (2019) → 권순희 외 (2018) — 사회평론아카데미 ISBN 9791188108787 2건 치환 (§3.4 §5.1). 본문/매핑 표/대리 범위 framing 변경 없음 — citation year만 정정. SHA는 `reports/snapshot_registry.md` 참조 |
| 1.1 post-audit cosmetic (superseded by v1.2) | 2026-05-14 | v1.1 initial 직후 비판적 review에서 §1·§4의 "(v1.0 명시)" 태그를 "(v1.0+ 명시; v1.1에서 그대로 유지)"으로 명료화 (lines 37, 53, 159). 본문/매핑 표/citation 변경 없음. AIED 투고 scope 기준 최종판. SHA는 `reports/snapshot_registry.md` 참조 (recursive SHA self-reference 방지를 위해 in-file 미기재). |
| **1.2 (post-V1/V2/V3 reference verification)** | **2026-05-15** | **§4 끝에 "임계치 출처 명료화" note 추가 — Stage 5 SHAP stability cutoff (τ/Jaccard 0.5)을 `decision_table` §3.1에 명시되어 있으며 Nogueira 2018 attribution이 아닌 본 연구의 pre-registered conservative working threshold임을 명시. 매핑 표 §2 + 대리 범위 §3 + 한계 §5는 v1.1 post-audit cosmetic 그대로. SHA는 `reports/snapshot_registry.md` 참조** |
| (옵션) 1.2+OSF | — | 다른 venue 재투고 결정 시 OSF registration upgrade 가능 |
