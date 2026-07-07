# Main Contrast Preregistered Addendum v1.3

Created: 2026-05-25
Status: Stage 4 pre-entry registration addendum

This addendum registers the main contrast added after Stage 3 and before any
Stage 4 LLM main run. It supplements, but does not edit,
`decision_table_preregistered.md` v1.1 and
`family_rubric_mapping_preregistered.md` v1.2.

## 1. Main Claim

The main claim is limited to whether SHAP-LLM explanation alignment is higher
for a surface trait than for a content trait in the in-scope Korean K-12 AES
corpus. Score-level agreement is a premise check, not the main claim.

System pair for the premise check:

- Feature-based XGBoost AES out-of-fold predictions from Stage 2.2.
- Sonnet 4.6 Stage B LLM scores from Stage 4.

Premise threshold:

- Per-trait QWK >= 0.50 for each analyzed trait is interpreted only as
  comparable to the lower bound of human-human reliability observed in this
  dataset.

Headline weakening rule:

- V1: all 3 analyzed traits meet QWK >= 0.50.
- V2: 2 analyzed traits meet QWK >= 0.50.
- V3: 0-1 analyzed traits meet QWK >= 0.50; remove score-level premise wording.

## 2. Analyzed Traits

The main paper uses exactly these traits:

- Surface: `expression_2`
- Discourse-structure: `organization_1`, exploratory only
- Content: `content_1`

The main strong claim is Surface > Content only. Discourse is not included in
the abstract or introduction contribution statement.

## 3. Alignment Metric

For essay `i` and trait `t`:

`A(i,t) = J(F_SHAP(i,t), F_LLM(i,t))`

where `J` is Jaccard overlap. If both sets are empty, `A(i,t)=0`.

`F_SHAP(i,t)` is the top-3 feature-family set from
`reports/stage3_shap/local_shap__{purpose}__primary__grade_stratified.parquet`.
Rows are filtered to `(essay_id=i, trait=t)`, ranked by `abs(shap_sum)`
descending, and ties are broken by `configs.paths.FEATURE_FAMILIES`.

`F_LLM(i,t)` is detected from Stage C rationale text using kiwipiepy content
morphemes and exact 1-3 lemma-token keyword matches.

## 4. LLM Keyword Governance

Keywords are a measurement convention for preregistered consistency. They are
not a claim that rubric families are conceptually disjoint.

Rules:

- Each keyword sequence must have a source tag from v1.2 mapping, Park 2008
  rubric terminology, or NIA rubric text.
- A lemma sequence may appear in at most one family.
- Ambiguous sequences are assigned to the most specific family and documented
  here before the Stage 4 main run.
- No keyword may be added or removed after Stage 4 main execution begins.

## 5. Keyword List

| Family | Lemma sequence | Source tag |
|---|---|---|
| `meta` | `길이` | v1.2/meta |
| `meta` | `분량` | NIA/meta |
| `meta` | `글 길이` | v1.2/meta |
| `meta` | `문장 수` | NIA/meta |
| `meta` | `어절 수` | NIA/meta |
| `morph_prop` | `어미` | v1.2/morph_prop |
| `morph_prop` | `종결` | NIA/morph_prop |
| `morph_prop` | `시제` | v1.2/morph_prop |
| `morph_prop` | `품사` | v1.2/morph_prop |
| `morph_prop` | `동사 비율` | v1.2/morph_prop |
| `lex` | `어휘` | Park2008/expression |
| `lex` | `단어 선택` | Park2008/expression |
| `lex` | `표현 다양` | Park2008/expression |
| `lex` | `어휘 다양` | v1.2/lex |
| `vocab_grade` | `어휘 등급` | v1.2/vocab_grade |
| `vocab_grade` | `초급 어휘` | v1.2/vocab_grade |
| `vocab_grade` | `고급 어휘` | v1.2/vocab_grade |
| `vocab_grade` | `어휘 수준` | v1.2/vocab_grade |
| `syn` | `문장 구조` | v1.2/syn |
| `syn` | `문법 구조` | Park2008/expression |
| `syn` | `연결 어미` | v1.2/syn |
| `syn` | `문장 형식` | NIA/expression |
| `case_marker` | `조사` | v1.2/case_marker |
| `case_marker` | `격조사` | v1.2/case_marker |
| `case_marker` | `조사 사용` | NIA/case_marker |
| `case_marker` | `어절 결합` | v1.2/case_marker |
| `dis_nonSBERT` | `접속어` | v1.2/dis_nonSBERT |
| `dis_nonSBERT` | `연결어` | v1.2/dis_nonSBERT |
| `dis_nonSBERT` | `응집` | HallidayHasan/discourse |
| `dis_nonSBERT` | `문단 연결` | Park2008/organization |
| `dis_nonSBERT` | `전개 흐름` | Park2008/organization |
| `dis_SBERT` | `의미 일관성` | v1.2/dis_SBERT |
| `dis_SBERT` | `주제 유지` | v1.2/dis_SBERT |
| `dis_SBERT` | `내용 흐름` | NIA/content |
| `dis_SBERT` | `맥락 연결` | v1.2/dis_SBERT |
| `dis_SBERT` | `문단 일관성` | Park2008/organization |

## 6. Statistical Tests

- Strong claim: one-sided paired Wilcoxon signed-rank test for Surface >
  Content, raw p < 0.05, rank-biserial r >= 0.10, pooled median direction, and
  purpose-direction consistency gate.
- Exploratory discourse: two-sided Surface vs Discourse and Discourse vs
  Content tests with Holm correction across the two p-values.
- Supportive descriptive: Friedman omnibus and pooled/per-purpose median
  triplets.

## 7. Smoke And Audit Gates

The Stage 4 main run requires:

- Smoke test: 30 essays, 15 per purpose, 3 stages.
- API axes: schema errors < 3, validator final failures < 3, per-trait null
  rate < 20%, token usage within +/-30%, rerun exact match >= 95%.
- Metric axes: per-trait `F_LLM` non-empty rate >= 80%, max family share <
  0.50, median `A` in [0.10, 0.70], and std(`A`) > 0.05.
- Blind audit: overall Cohen kappa >= 0.70 and per-family kappa >= 0.60 when
  family prevalence is non-degenerate.
