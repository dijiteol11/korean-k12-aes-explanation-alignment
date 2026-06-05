# Separating Score-Level Agreement from Operational Explanation Alignment in Korean K-12 Analytic AES: SHAP Feature Families and LLM Rationales

## Abstract

This study analyses the separation between score-level agreement and operational explanation alignment in Korean K-12 analytic automated essay scoring (AES). Across 4,860 student essays (2,709 expository and 2,151 persuasive), we compute a pre-registered form-family operational alignment: the essay-by-trait Jaccard A(i,t)=J(F_SHAP(i,t), F_LLM(i,t)) between the top SHAP feature families of a tree-ensemble AES model and a deterministic family set extracted from LLM rationale text. The Surface-vs-Content contrast is statistically significant in rank and direction (Wilcoxon p=1.96e-65; rank-biserial r=0.981), but all trait-type medians are zero. The finding is therefore interpreted as a sparse nonzero direction pattern, not as high absolute alignment. The pre-registered score-level premise (per-trait QWK >= .50) is not met for any analysed trait, so the headline is a caveated V3 claim. Content-trait alignment is near floor (0.04% / 0.09% nonzero), consistent with a metric-design limitation: semantic content rationales do not lexically map onto form-based feature families. Reporting-convention sensitivity checks retain the same directional interpretation.

**Keywords:** automated essay scoring; explanation alignment; SHAP attribution; large language model rationales; pre-registered analysis

## 1. Introduction

Korean K-12 analytic AES systems are commonly evaluated at the score level, for example by per-trait quadratic weighted kappa (QWK). This paper separates that score-level question from an explanation-level question: whether a model's feature attribution invokes the same form-family cues that an independent LLM rationale invokes for the same essay and trait. We pre-register a Jaccard alignment metric between Stage 3 SHAP feature families and Stage 4 LLM rationale families, and test a Surface-vs-Content asymmetry across 4,860 essays.

The main contribution is deliberately narrow. We test whether Surface-trait rationale (`expression_2`) invokes pre-registered form families more often than Content-trait rationale (`content_1`). The Discourse trait (`organization_1`) is reported only as an exploratory result because of its separate reliability limitation.

Strong-form interpretation was pre-registered as conditional on a score-level premise. That premise was not met: no analysed trait reached QWK >= .50. The manuscript therefore adopts V3 wording, reports median-zero and sparse-pattern caveats first, and avoids claims of high absolute alignment.

## 2. Related Work

The study builds on automated essay evaluation as an established assessment field (Shermis & Burstein, 2013) and on recent Korean essay scoring work using the same national AI-Hub corpus (Ryoo, Cho, & Jo, 2026). Unlike score-only AES studies, this paper asks whether feature-family attributions from an AES model and rationale-family invocations from an independent LLM scorer show a directional pattern.

SHAP provides a unified framework for interpreting model predictions (Lundberg & Lee, 2017). The present study applies SHAP at the feature-family level to a tree-ensemble AES regressor. Recent work has also examined LLM-based essay scoring on English L2 essays (Mizumoto & Eguchi, 2023), while this paper focuses on whether LLM rationale text can be compared to feature-family attribution through a pre-registered operational detector.

The analysis is also shaped by pre-registration practice (Nosek et al., 2018). The central claim is not that LLM rationales are semantically equivalent to SHAP attributions, but that a pre-registered form-family operational alignment shows a sparse Surface-vs-Content direction.

## 3. Materials and Methods

For each essay i and trait t, the primary indicator is A(i,t)=J(F_SHAP(i,t), F_LLM(i,t)). F_SHAP is the top-three feature-family set by absolute local SHAP sum. F_LLM is the set of families detected in Stage C rationale text by exact 1-to-3 lemma-token matching against the pre-registered v1.3 keyword list. When both sets are empty, A is recorded as 0; Appendix D evaluates the alternative convention of dropping both-empty rows.

The primary contrast is Surface > Content using a one-sided Wilcoxon signed-rank test. Exploratory contrasts compare Surface vs Discourse and Discourse vs Content with Holm-2 correction. Strong-claim status requires p-value, rank-biserial direction, pooled-median direction, and purpose-gate criteria to pass jointly. In the observed data, p-value and rank direction pass, but median-direction and purpose-gate criteria fail.

The main LLM run produced 14,580 stage-output rows (three stages times 4,860 essays). Of these, 14,576 were model-provider calls and four were deterministic local recoveries from saved outputs. No raw student essays or raw LLM outputs are included in this redacted repository. Public derived tables and audit summaries are provided instead.

## 4. Results

Three framing facts govern the interpretation. First, the score-level premise is not met: all six trait-by-purpose QWK cells are below .50. Second, the pooled median of A(i,t) is zero for Surface, Discourse, and Content. Third, the asymmetry signal is sparse: most essays have zero alignment for both Surface and Content, but the minority nonzero cases are overwhelmingly in the Surface > Content direction.

**Table 1. Per-trait QWK between Stage 2.2 XGBoost OOF predictions and Stage 4 LLM scores.**

| trait | purpose | n | QWK | XGB mean | LLM mean |
|---|---:|---:|---:|---:|---:|
| content_1 | expository | 2689 | 0.235 | 3.382 | 3.046 |
| expression_2 | expository | 2605 | 0.198 | 3.773 | 3.139 |
| organization_1 | expository | 2708 | 0.170 | 3.212 | 3.353 |
| content_1 | persuasive | 2151 | 0.274 | 3.271 | 3.331 |
| expression_2 | persuasive | 2087 | 0.267 | 3.718 | 3.232 |
| organization_1 | persuasive | 2151 | 0.209 | 3.225 | 3.525 |

**Table 2. Trait-type nonzero / zero breakdown of A(i,t).**

| purpose | trait_type | n | positive (>0) | % positive | zero (=0) | % zero |
|---|---|---:|---:|---:|---:|---:|
| expository | Surface (`expression_2`) | 2709 | 193 | 7.1 | 2516 | 92.9 |
| expository | Discourse (`organization_1`) | 2709 | 222 | 8.2 | 2487 | 91.8 |
| expository | Content (`content_1`) | 2709 | 1 | 0.04 | 2708 | 99.96 |
| persuasive | Surface (`expression_2`) | 2151 | 145 | 6.7 | 2006 | 93.3 |
| persuasive | Discourse (`organization_1`) | 2151 | 97 | 4.5 | 2054 | 95.5 |
| persuasive | Content (`content_1`) | 2151 | 2 | 0.09 | 2149 | 99.91 |

**Table 3. Paired direction consistency at the essay level.**

| comparison | purpose | n | left > right | left = right | left < right |
|---|---|---:|---:|---:|---:|
| Surface vs Content | expository | 2709 | 193 (7.1%) | 2515 (92.8%) | 1 (0.04%) |
| Surface vs Content | persuasive | 2151 | 145 (6.7%) | 2004 (93.2%) | 2 (0.09%) |
| Discourse vs Content | expository | 2709 | 222 (8.2%) | 2486 (91.8%) | 1 (0.04%) |
| Discourse vs Content | persuasive | 2151 | 97 (4.5%) | 2052 (95.4%) | 2 (0.09%) |

The Friedman omnibus test over three trait types is significant (n=4,860, statistic=334.86, p=1.93e-73). The primary Surface-vs-Content Wilcoxon contrast is significant (W=57,750, p=1.96e-65; rank-biserial r=0.981). This r is interpreted only as a rank/direction signal within the minority nonzero subset, not as an effect-size magnitude. Exploratory Holm-2 results show Discourse > Content (p=1.45e-68) and no detectable Surface-vs-Discourse difference (p=.88).

## 5. Discussion

The result is not that operational alignment is high overall. The result is that when pre-registered form-family alignment is nonzero, it is almost always Surface or Discourse rather than Content. This distinction matters because 92.8% to 93.2% of the primary paired comparisons are zero ties.

The near-floor Content value does not mean that content quality is meaningless. It indicates that content rationales use semantic vocabulary that is not lexically represented by the form-based feature-family keywords in this operational metric. Semantic-level family detection is therefore left as future work.

## 6. Limitations

The six pre-registered limitations are summarised here in anonymized form. The canonical Korean pre-registration intent lock is retained outside this anonymous package as Supplement S1; this English version preserves the meaning but not the internal file identifiers.

1. The LLM scorer is treated as an engineering-quality explanation source, not as a gold-standard human rater.
2. Keyword matching is an operational measurement convention and does not prove that the full construct of a rubric domain has been captured.
3. Smoke tests and spot-checks demonstrate operational consistency, not construct completeness.
4. Conventional kappa benchmarks are descriptive guidelines, not decisive validity thresholds.
5. The Discourse trait is retained as exploratory because organisation-related reliability is weaker than the Surface/Content contrast.
6. Content-trait family detection is near floor because semantic content vocabulary does not lexically map onto form-based feature-family keywords.
7. Grade-level developmental differences are partly controlled through grade-stratified validation, but the family mapping itself is held constant across grades.

## 7. Conclusion

This study reports a sparse nonzero direction pattern in form-family operational alignment: Surface-trait rationale invokes pre-registered form-family cues more often than Content-trait rationale, while score-level agreement remains weak and absolute alignment remains near floor. The result is therefore a caveated operational finding, not a claim of semantic equivalence between SHAP attributions and LLM rationales.

## 8. References

- Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174.
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. In *Advances in Neural Information Processing Systems 30* (pp. 4765-4774). Curran Associates.
- Mizumoto, A., & Eguchi, M. (2023). Exploring the potential of using an AI language model for automated essay scoring. *Research Methods in Applied Linguistics*, 2(2), 100050. https://doi.org/10.1016/j.rmal.2023.100050
- Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences*, 115(11), 2600-2606. https://doi.org/10.1073/pnas.1708274114
- Ryoo, J. H., Cho, J., & Jo, Y. (2026). Automated scoring for Korean essays utilizing the neural pairwise contrastive regression along with Korean NLP models. *Frontiers in Education*. https://doi.org/10.3389/feduc.2026.1775485
- Shermis, M. D., & Burstein, J. (Eds.). (2013). *Handbook of automated essay evaluation: Current applications and new directions*. Routledge.
