# Smoke 9-axis Report (a)-(e)

## (a) Schema error rate / (b) Validator fail rate

- Total calls: 90
- Expected calls: 90 — completion **PASS**
- Schema errors: 0 → axis (a) **PASS** (< 3 required)
- Validator errors: 0 → axis (b) **PASS** (< 3 required)
- API errors: 0

## (c) Null rate per trait (Stage B)

### 설명
- `content_1`: 0/15 (0.0%)
- `content_2`: 0/15 (0.0%)
- `content_3`: 0/15 (0.0%)
- `expression_1`: 0/15 (0.0%)
- `expression_2`: 0/15 (0.0%)
- `organization_1`: 0/15 (0.0%)
- `organization_2`: 0/15 (0.0%)
- `task_1`: 0/15 (0.0%)
- axis (c) **PASS** (< 20% per trait)

### 설득
- `content_1`: 0/15 (0.0%)
- `content_2`: 0/15 (0.0%)
- `content_3`: 0/15 (0.0%)
- `expression_1`: 0/15 (0.0%)
- `expression_2`: 0/15 (0.0%)
- `organization_1`: 0/15 (0.0%)
- `organization_2`: 0/15 (0.0%)
- `task_1`: 0/15 (0.0%)
- axis (c) **PASS** (< 20% per trait)

## (d) Token usage variance

- Calls with usage: 90
- Mean input tokens: 7577.4111111111115
- Mean output tokens: 1593.7444444444445
- axis (d) **NEEDS estimator targets to compute**

## (e) Rerun consistency (Stage B)

### 설명
- Essays compared: 10, trait decisions: 80, matches: 77
- Trait-level exact match rate: 96.2%
- axis (e) **PASS** (≥ 95% required)
