# Main Contrast Summary — Stage 5 analysis (2026-06-01)

**입력**: Stage 4 main 결과 (`reports/stage4_llm/main/{B,C}/{설명,설득}.jsonl`)
 + Stage 2.2 OOF + Stage 3 SHAP.
**총 essay**: 4,860 (설명 2,709 + 설득 2,151), validator full-sweep pass.
**α pilot**: 보류 (decision_history.md 2026-06-01 entry; §6 참조).

## 0. Framing notes (본문 작성 규약, 표·통계 해석 전 필독)

- **`r = 0.981` 은 rank / direction 신호가 강하다는 뜻이지, absolute alignment 가 높다는 뜻이 아니다.** medians 가 모두 0 이므로 본문은 nonzero / rank pattern 중심 (§5 Descriptive robustness 참조).
- 본문 claim = **form-family operational alignment** 의 nonzero / rank pattern. "strong absolute alignment" 표현은 금지.
- **`strong_claim` / `purpose_gate` FAIL 은 숨기지 않음**: 사전등록 strong wording 미채택; **V3 / caveated wording 채택** (medians=0 + purpose_gate FAIL 명시).

## 1. Score-level QWK (Stage 2.2 OOF vs Stage 4 Stage B)

| trait          |    n |      qwk |   xgb_mean |   llm_mean | purpose   |
|:---------------|-----:|---------:|-----------:|-----------:|:----------|
| content_1      | 2689 | 0.23536  |    3.38185 |    3.04649 | 설명        |
| expression_2   | 2605 | 0.197619 |    3.77336 |    3.13858 | 설명        |
| organization_1 | 2708 | 0.170038 |    3.21202 |    3.3534  | 설명        |
| content_1      | 2151 | 0.273574 |    3.2709  |    3.33101 | 설득        |
| expression_2   | 2087 | 0.2665   |    3.718   |    3.23191 | 설득        |
| organization_1 | 2151 | 0.209156 |    3.22499 |    3.52534 | 설득        |

**Headline variant**: **V3** 
(threshold = QWK ≥ 0.50; per-trait pass: ?)

## 2. Axes (f)(g)(h) — analyzed-trait family detection gates

### 설명

- (f) non-empty rate: **FAIL** (임계 ≥ 0.80, analyzed traits)
- (g) max family share: **PASS** (max = 0.211, 임계 < 0.50)
- (h) Jaccard median: **FAIL** (median = 0.000, std = 0.074; 임계 ∈ [0.10, 0.70], std > 0.05)

**per-trait non-empty rate**:

| trait          |   n_cells |   positive_cells |   non_empty_rate | axis_f_pass   | prevalence_diagnostic   |
|:---------------|----------:|-----------------:|-----------------:|:--------------|:------------------------|
| content_1      |      2709 |               11 |       0.00406054 | False         | LOW_PREVALENCE          |
| expression_2   |      2709 |              626 |       0.231082   | False         | INTERPRETABLE           |
| organization_1 |      2709 |             1707 |       0.630122   | False         | INTERPRETABLE           |

### 설득

- (f) non-empty rate: **FAIL** (임계 ≥ 0.80, analyzed traits)
- (g) max family share: **PASS** (max = 0.250, 임계 < 0.50)
- (h) Jaccard median: **FAIL** (median = 0.000, std = 0.063; 임계 ∈ [0.10, 0.70], std > 0.05)

**per-trait non-empty rate**:

| trait          |   n_cells |   positive_cells |   non_empty_rate | axis_f_pass   | prevalence_diagnostic   |
|:---------------|----------:|-----------------:|-----------------:|:--------------|:------------------------|
| content_1      |      2151 |                9 |        0.0041841 | False         | LOW_PREVALENCE          |
| expression_2   |      2151 |              528 |        0.245467  | False         | INTERPRETABLE           |
| organization_1 |      2151 |             1614 |        0.750349  | False         | INTERPRETABLE           |

## 3. Main contrast — Surface vs Content (Holm-2)

### wide (full table omitted — see `reports/stage5_alignment/jaccard_alignment__*.parquet`)

shape = (4860, 5); columns = ['essay_id', 'purpose', 'content', 'discourse', 'surface']

### friedman

|    n |   statistic |     p_value |
|-----:|------------:|------------:|
| 4860 |     334.859 | 1.93318e-73 |

### primary

| contrast           | alternative   |    n |   statistic |     p_value |   rank_biserial_r |   median_left |   median_right | pooled_median_direction_pass   | effect_size_pass   | p_value_pass   | purpose_gate_pass   | strong_claim_pass   |
|:-------------------|:--------------|-----:|------------:|------------:|------------------:|--------------:|---------------:|:-------------------------------|:-------------------|:---------------|:--------------------|:--------------------|
| surface_vs_content | greater       | 4860 |       57750 | 1.95867e-65 |          0.980758 |             0 |              0 | False                          | True               | True           | False               | False               |

### exploratory

| contrast             | alternative   |    n |   statistic |     p_value |   rank_biserial_r |   median_left |   median_right |
|:---------------------|:--------------|-----:|------------:|------------:|------------------:|--------------:|---------------:|
| surface_vs_discourse | two-sided     | 4860 |     91689   | 0.88274     |       -0.00623212 |             0 |              0 |
| discourse_vs_content | two-sided     | 4860 |       490.5 | 1.44544e-68 |        0.981136   |             0 |              0 |

### exploratory_holm

| contrast             |       raw_p |   holm_threshold | holm_reject   |   holm_order |
|:---------------------|------------:|-----------------:|:--------------|-------------:|
| discourse_vs_content | 1.44544e-68 |            0.025 | True          |            1 |
| surface_vs_discourse | 0.88274     |            0.05  | False         |            2 |

### purpose_gate

| purpose   |    n |   median_surface |   median_content |   rank_biserial_r | gate_pass   |
|:----------|-----:|-----------------:|-----------------:|------------------:|:------------|
| 설득        | 2151 |                0 |                0 |          0.970767 | False       |
| 설명        | 2709 |                0 |                0 |          0.98858  | False       |

### medians

|   median_surface |   median_discourse |   median_content |
|-----------------:|-------------------:|-----------------:|
|                0 |                  0 |                0 |

## 4. Alignment distribution summary (per purpose, analyzed traits)

### 설명

| trait          |   count |        mean |   median |        std |
|:---------------|--------:|------------:|---------:|-----------:|
| content_1      |    2709 | 0.000123047 |        0 | 0.00640434 |
| expression_2   |    2709 | 0.0236803   |        0 | 0.0875322  |
| organization_1 |    2709 | 0.0272548   |        0 | 0.0912678  |

### 설득

| trait          |   count |        mean |   median |       std |
|:---------------|--------:|------------:|---------:|----------:|
| content_1      |    2151 | 0.000309933 |        0 | 0.0101618 |
| expression_2   |    2151 | 0.02223     |        0 | 0.0836323 |
| organization_1 |    2151 | 0.0149543   |        0 | 0.0688765 |

## 5. Descriptive robustness (median=0 환경 보강 — 0 포함 비율 핵심)

본 §3 의 통계는 `r` 가 높지만 medians 가 모두 0. 본 §5 는 그 분포 구조를 **positive / zero / negative 비율** 과 quantile 로 직접 노출. 본문은 이 표들의 nonzero / rank pattern 을 가지고 form-family operational alignment 의 비대칭을 기술해야 함 (§0 framing).

### 5.1 Nonzero / zero breakdown per (purpose, trait_type)

| purpose   | trait_type                 |    n |   positive (>0) | % positive   |   zero (=0) | % zero   |
|:----------|:---------------------------|-----:|----------------:|:-------------|------------:|:---------|
| 설명        | Surface (expression_2)     | 2709 |             193 | 7.1%         |        2516 | 92.9%    |
| 설명        | Discourse (organization_1) | 2709 |             222 | 8.2%         |        2487 | 91.8%    |
| 설명        | Content (content_1)        | 2709 |               1 | 0.0%         |        2708 | 100.0%   |
| 설득        | Surface (expression_2)     | 2151 |             145 | 6.7%         |        2006 | 93.3%    |
| 설득        | Discourse (organization_1) | 2151 |              97 | 4.5%         |        2054 | 95.5%    |
| 설득        | Content (content_1)        | 2151 |               2 | 0.1%         |        2149 | 99.9%    |

### 5.2 Paired difference distribution (per essay Δ)

| contrast            | purpose   |    n | + (left>right)   | 0 (=)        | − (left<right)   |   mean Δ |   median Δ |   p25 |   p75 |    p95 |
|:--------------------|:----------|-----:|:-----------------|:-------------|:-----------------|---------:|-----------:|------:|------:|-------:|
| Surface − Content   | 설명        | 2709 | 193 (7.1%)       | 2515 (92.8%) | 1 (0.0%)         |   0.0236 |          0 |     0 |     0 | 0.3333 |
| Surface − Content   | 설득        | 2151 | 145 (6.7%)       | 2004 (93.2%) | 2 (0.1%)         |   0.0219 |          0 |     0 |     0 | 0.3333 |
| Discourse − Content | 설명        | 2709 | 222 (8.2%)       | 2486 (91.8%) | 1 (0.0%)         |   0.0271 |          0 |     0 |     0 | 0.3333 |
| Discourse − Content | 설득        | 2151 | 97 (4.5%)        | 2052 (95.4%) | 2 (0.1%)         |   0.0146 |          0 |     0 |     0 | 0      |

### 5.3 Purpose direction consistency (essay 단위 비교, NOT median 비교)

| comparison           | purpose   |    n | left > right   | left = right   | left < right   |
|:---------------------|:----------|-----:|:---------------|:---------------|:---------------|
| Surface vs Content   | 설명        | 2709 | 193 (7.1%)     | 2515 (92.8%)   | 1 (0.0%)       |
| Surface vs Content   | 설득        | 2151 | 145 (6.7%)     | 2004 (93.2%)   | 2 (0.1%)       |
| Discourse vs Content | 설명        | 2709 | 222 (8.2%)     | 2486 (91.8%)   | 1 (0.0%)       |
| Discourse vs Content | 설득        | 2151 | 97 (4.5%)      | 2052 (95.4%)   | 2 (0.1%)       |

### 5.4 Trait-type Jaccard quantiles

| purpose   | trait_type                 |   q25 |   q50 (median) |   q75 |   q90 |    q95 |
|:----------|:---------------------------|------:|---------------:|------:|------:|-------:|
| 설명        | Surface (expression_2)     |     0 |              0 |     0 |     0 | 0.3333 |
| 설명        | Discourse (organization_1) |     0 |              0 |     0 |     0 | 0.3333 |
| 설명        | Content (content_1)        |     0 |              0 |     0 |     0 | 0      |
| 설득        | Surface (expression_2)     |     0 |              0 |     0 |     0 | 0.3333 |
| 설득        | Discourse (organization_1) |     0 |              0 |     0 |     0 | 0      |
| 설득        | Content (content_1)        |     0 |              0 |     0 |     0 | 0      |

## 6. α pilot 판단 — **정식 보류 (2026-06-01)**

**결정**: α pilot **보류** (생략 아님 — 후속/보조 분석으로 defer). 사전등록 의도 (v2.3 §4.3.2 Krippendorff α pilot) 는 보존. 결정문 정식 audit: `decision_history.md` 2026-06-01 entry.

**lock 문장**: "α pilot deferred: null trigger 미충족, V3 해결 불가, main contrast 는 V3/median-zero caveat 가 붙은 form-family operational claim 으로 보고한다."

**근거**:
- Stage B null score per-trait: max **3.8% (expression_2, 설명)** — 원 α pilot trigger 임계 (>10%) 미달.
- V3 headline 문제는 α pilot 으로 해결 안 됨 (α pilot 은 Sonnet 자체 반복 안정성을 측정; V3 는 XGBoost OOF ↔ Sonnet score-level mismatch).
- Stage C empty rationale per-trait: **0%** (전 trait).
- 자세한 null/empty 분포: `reports/stage4_llm/main/quality_report.md` §8-9.
- 분포 구조 (positive / zero / negative 비율 + quantile): 본 §5.
