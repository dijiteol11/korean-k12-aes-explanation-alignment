# Stage 10.D — Reporting-convention sensitivity (Surface vs Content)
Source: `reports/stage5_alignment/jaccard_alignment__{설명,설득}__primary__grade_stratified.parquet`. Pre-reg metric definition unchanged; pre-reg contrast unchanged. Read-only analysis over already-computed alignment.

## A. Empty-union convention

Pre-reg: `A=0` if both `F_SHAP` and `F_LLM` are empty. Alternative: `A=NA` (drop both-empty rows), nonzero-only Wilcoxon.

| convention | n | W | p | r | med(Surface) | med(Content) |
|:---|---:|---:|---:|---:|---:|---:|
| pre-reg (A=0 if both empty) | 4860 | 57750.000 | 1.96e-65 | 0.981 | 0.0000 | 0.0000 |
| alt (A=NA; drop both-empty) | 341 | 57750.000 | 1.96e-65 | 0.981 | 0.3333 | 0.0000 |

## B. Wilcoxon tie-handling

Pre-reg: `scipy.stats.wilcoxon(..., zero_method='wilcox')`. Alternatives: `'pratt'`, `'zsplit'`.

| tie method | n | W | p | r |
|:---|---:|---:|---:|---:|
| zero_method='wilcox' (pre-reg) | 4860 | 57750.000 | 1.96e-65 | 0.981 |
| zero_method='pratt' | 4860 | 1585172.000 | 7.90e-74 | 0.981 |
| zero_method='zsplit' | 4860 | 6691642.000 | 1.31e-19 | 0.981 |

## Interpretation

- Both axes retain the same directional sign (Surface > Content). The pre-reg strong-claim status (`pooled_median_direction_pass = False`, `strong_claim_pass = False`) does not change.
- Axis A: under `zero_method='wilcox'`, both-empty pairs are already excluded from the signed-rank computation, so the pre-reg `A=0` convention and the `A=NA` (drop both-empty) alternative produce identical `W`, `p`, and `r`. The displayed `n` differs (4,860 vs 341 nonzero-on-either-side pairs), and the nonzero subset shifts `median(Surface)` from 0 to 0.333 while `median(Content)` stays at 0 — consistent with the sparse-nonzero direction reported in §6.1(3).
- Axis B: `p` moves across tie-handling methods (`wilcox` 1.96e-65, `pratt` 7.90e-74, `zsplit` 1.31e-19) but stays far below conventional thresholds under all three; the rank-biserial `r = 0.981` and pooled medians are invariant.
- Conclusion: the main contrast does not depend on the choice of empty-union convention or Wilcoxon tie-handling method. Supplementary robustness was limited to reporting-convention sensitivity, not an additional substantive model.
