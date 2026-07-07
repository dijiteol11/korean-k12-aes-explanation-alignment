# Stage 4 LLM Family Smoke Audit

- Cells: 120
- Max family cell share: 0.150
- Metric gate overall: **FAIL**

## Gate Summary (Analyzed Traits)

- Analyzed traits: expression_2, organization_1, content_1
- (f) Non-empty rate: **FAIL** (threshold: each analyzed trait >= 0.80)
- (g) Max family share: **PASS** (analyzed-trait max=0.244, threshold < 0.50)
- (h) Jaccard sanity: **FAIL** (median=0.000, std=0.069)

| trait          |   n_cells |   positive_cells |   non_empty_rate | axis_f_pass   | prevalence_diagnostic   |
|:---------------|----------:|-----------------:|-----------------:|:--------------|:------------------------|
| content_1      |        15 |                1 |        0.0666667 | False         | LOW_PREVALENCE          |
| expression_2   |        15 |                3 |        0.2       | False         | INTERPRETABLE           |
| organization_1 |        15 |               11 |        0.733333  | False         | INTERPRETABLE           |

## Non-Empty Rate By Trait

| trait          |   n_cells |   positive_cells |   non_empty_rate |
|:---------------|----------:|-----------------:|-----------------:|
| content_1      |        15 |                1 |        0.0666667 |
| content_2      |        15 |                0 |        0         |
| content_3      |        15 |                2 |        0.133333  |
| expression_1   |        15 |               15 |        1         |
| expression_2   |        15 |                3 |        0.2       |
| organization_1 |        15 |               11 |        0.733333  |
| organization_2 |        15 |                0 |        0         |
| task_1         |        15 |                0 |        0         |

## Family Coverage

| family       |   detected_cells |   cell_share |
|:-------------|-----------------:|-------------:|
| case_marker  |                1 |   0.00833333 |
| dis_nonSBERT |               11 |   0.0916667  |
| lex          |               18 |   0.15       |
| syn          |                3 |   0.025      |

## Jaccard Sanity

- Median A: 0.000
- Std A: 0.048
