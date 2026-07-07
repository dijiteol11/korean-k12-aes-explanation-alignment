# Stage 4 LLM Family Smoke Audit

- Cells: 120
- Max family cell share: 0.125
- Metric gate overall: **FAIL**

## Gate Summary (Analyzed Traits)

- Analyzed traits: expression_2, organization_1, content_1
- (f) Non-empty rate: **FAIL** (threshold: each analyzed trait >= 0.80)
- (g) Max family share: **PASS** (analyzed-trait max=0.222, threshold < 0.50)
- (h) Jaccard sanity: **FAIL** (median=0.000, std=0.090)

| trait          |   n_cells |   positive_cells |   non_empty_rate | axis_f_pass   | prevalence_diagnostic   |
|:---------------|----------:|-----------------:|-----------------:|:--------------|:------------------------|
| content_1      |        15 |                0 |         0        | False         | DEGENERATE_ZERO         |
| expression_2   |        15 |                4 |         0.266667 | False         | INTERPRETABLE           |
| organization_1 |        15 |               10 |         0.666667 | False         | INTERPRETABLE           |

## Non-Empty Rate By Trait

| trait          |   n_cells |   positive_cells |   non_empty_rate |
|:---------------|----------:|-----------------:|-----------------:|
| content_1      |        15 |                0 |         0        |
| content_2      |        15 |                0 |         0        |
| content_3      |        15 |                0 |         0        |
| expression_1   |        15 |               15 |         1        |
| expression_2   |        15 |                4 |         0.266667 |
| organization_1 |        15 |               10 |         0.666667 |
| organization_2 |        15 |                0 |         0        |
| task_1         |        15 |                0 |         0        |

## Family Coverage

| family       |   detected_cells |   cell_share |
|:-------------|-----------------:|-------------:|
| case_marker  |                3 |   0.025      |
| dis_nonSBERT |               10 |   0.0833333  |
| lex          |               15 |   0.125      |
| morph_prop   |                2 |   0.0166667  |
| syn          |                1 |   0.00833333 |

## Jaccard Sanity

- Median A: 0.000
- Std A: 0.070
