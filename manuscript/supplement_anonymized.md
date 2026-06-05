# Supplementary Materials (Anonymized)

This supplement contains redacted audit summaries and reporting-convention sensitivity checks. It excludes raw student essays, raw LLM outputs, error-response text, coder identities, local filesystem paths, and internal planning logs.

## Appendix A. Smoke test details

A 90-call smoke test preceded the main run. Preparation gates passed, final smoke outputs completed 90/90, and API-level schema/validator checks passed after deterministic driver hardening. Metric axes for family detection showed two expected failures: low F_LLM non-empty rates for analysed traits and median Jaccard near zero.

## Appendix B. Manual recovery audit

| stage | purpose | output_rows | provider_calls | deterministic_recoveries |
|---|---|---:|---:|---:|
| A | expository | 2709 | 2708 | 1 |
| A | persuasive | 2151 | 2151 | 0 |
| B | expository | 2709 | 2709 | 0 |
| B | persuasive | 2151 | 2151 | 0 |
| C | expository | 2709 | 2709 | 0 |
| C | persuasive | 2151 | 2148 | 3 |
| total | all | 14580 | 14576 | 4 |

## Appendix C. Pre-registration files

The redacted package includes three pre-registration documents and a SHA256SUMS file computed over the redacted copies. Original internal author/reviewer metadata have been removed.

## Appendix D. Reporting-convention sensitivity

| axis | convention_or_method | n | W | p | rank_biserial_r | median_surface | median_content |
|---|---|---:|---:|---:|---:|---:|---:|
| empty_union | pre_registered_A0 | 4860 | 57750 | 1.96e-65 | 0.981 | 0.0000 | 0.0000 |
| empty_union | drop_both_empty | 341 | 57750 | 1.96e-65 | 0.981 | 0.3333 | 0.0000 |
| tie_handling | wilcox | 4860 | 57750 | 1.96e-65 | 0.981 | | |
| tie_handling | pratt | 4860 | 1585172 | 7.90e-74 | 0.981 | | |
| tie_handling | zsplit | 4860 | 6691642 | 1.31e-19 | 0.981 | | |

Both sensitivity axes retain the same directional interpretation. The checks are limited to reporting-convention sensitivity and do not introduce a new metric, detector, threshold, or model.

## Appendix E. Model reporting note

The public package reports the scorer as a date-stamped commercial LLM used at temperature 0.0. Provider-specific identifiers and vendor logs are withheld from the anonymous package and can be supplied after review if required by the journal.

## Appendix F. Detector miss spot-check audit

A 20-cell diagnostic spot-check compared deterministic machine detection with two human coders. Coder identities are redacted. The spot-check was descriptive, not a study-entry gate. The conservative agreed-miss subset identified seven detector-miss candidates.
