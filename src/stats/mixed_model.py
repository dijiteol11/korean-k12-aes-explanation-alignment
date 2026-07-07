"""
Supplementary mixed-model robustness scaffold.

Python-side scaffold that delegates ordinal mixed-effects fitting to R
(``ordinal::clmm``) via subprocess. Rationale:
    - ``statsmodels.MixedLM`` does not support ordinal outcomes natively
    - R ``ordinal::clmm`` is the peer-review-standard package (Yamashita
      2024 RMAL, Jin et al. 2025 EIT use this)
    - Bayesian ``brms`` (R) is an alternative — left as a second path

The v2.6 main paper no longer uses this as the primary analysis. The main
contrast is handled by ``src.stats.trait_type_contrast``; this module remains
for appendix robustness only.

Legacy formula:
    alignment ~ purpose * rubric_domain * explanation_system
              + score_level + essay_length
              + (1|prompt_id) + (1|grade) + (1|essay_id)

Inputs: Stage 5 classified alignment matrix (``src.alignment.decisions``
output). Outputs: R fit summary + model coefficients table.

The researcher must have R + ``ordinal`` package installed locally.
Claude Code writes the R script but does not execute R calls.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd

from configs.paths import PROJECT_ROOT, REPORTS_DIR

log = logging.getLogger(__name__)

STAGE5_DIR: Path = REPORTS_DIR / "stage5_alignment"
R_SCRIPT_PATH: Path = PROJECT_ROOT / "scripts" / "stage5_clmm.R"


R_SCRIPT_TEMPLATE = r"""#!/usr/bin/env Rscript
# Stage 5.1 — Ordinal mixed model (clmm) for essay × trait alignment.
# Called via subprocess from src.stats.mixed_model; do not edit by hand.

suppressMessages({
  if (!requireNamespace("ordinal", quietly = TRUE)) {
    install.packages("ordinal", repos = "https://cloud.r-project.org")
  }
  library(ordinal)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript stage5_clmm.R <input.csv> <output_dir>")
}
in_path  <- args[1]
out_dir  <- args[2]
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

df <- read.csv(in_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")

# Alignment label to ordered factor. Indeterminate is a separate category
# with no ordinal meaning — the main model treats determinate cells only,
# and a secondary logistic is run for determinate vs Indeterminate.
determinate <- subset(df, label %in% c("Aligned", "UR", "CIV"))
determinate$label <- factor(determinate$label,
                            levels = c("CIV", "UR", "Aligned"),
                            ordered = TRUE)
determinate$purpose          <- factor(determinate$purpose)
determinate$rubric_domain    <- factor(determinate$rubric_domain)
determinate$explanation_system <- factor(determinate$explanation_system)
determinate$prompt_id        <- factor(determinate$prompt_id)
determinate$grade            <- factor(determinate$grade)
determinate$essay_id         <- factor(determinate$essay_id)

# Main ordinal mixed model (v2.3 §4.5.3).
cat("Fitting clmm ...\n")
fit <- clmm(
  label ~ purpose * rubric_domain * explanation_system +
          score_level + essay_length +
          (1 | prompt_id) + (1 | grade) + (1 | essay_id),
  data = determinate,
  link = "logit",
  Hess = TRUE
)

sink(file.path(out_dir, "clmm_summary.txt"))
print(summary(fit))
sink()

# Write fixed-effect coefficients as CSV.
coefs <- as.data.frame(coef(summary(fit)))
coefs$term <- rownames(coefs)
write.csv(coefs, file.path(out_dir, "clmm_coefficients.csv"), row.names = FALSE)

# Ancillary: proportion indeterminate for secondary reporting.
indet_rate <- mean(df$label == "Indeterminate")
cat(sprintf("Indeterminate proportion: %.3f\n", indet_rate))
writeLines(
  c(sprintf("indeterminate_rate\t%.4f", indet_rate),
    sprintf("n_cells_total\t%d", nrow(df)),
    sprintf("n_cells_determinate\t%d", nrow(determinate))),
  file.path(out_dir, "stage5_summary.tsv")
)
cat("Done.\n")
"""


def write_r_script(path: Path = R_SCRIPT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(R_SCRIPT_TEMPLATE, encoding="utf-8")
    log.info("Wrote R script: %s", path)
    return path


def prepare_model_input(
    labeled_matrix: pd.DataFrame,
    out_csv: Path,
    family_rubric_map: pd.DataFrame,
) -> Path:
    """Flatten the alignment matrix into a long-form CSV for clmm.

    Long-form schema (one row per essay × trait × explanation_system):
        essay_id, purpose, rubric_domain, explanation_system, trait,
        label, score_level, essay_length, prompt_id, grade.

    ``explanation_system`` ∈ {"SHAP", "LLM", "Human"} emerges from the
    triangulation — each cell contributes three rows (one per system)
    when their individual labels are known. For now we start with a
    single-system pass (main label) and leave the three-system expansion
    for when Stage 4.3 coding produces system-level codes.
    """
    # Join rubric_domain from family_rubric_map via trait → area.
    from configs.paths import feature_family  # unused but keeps import
    # Map trait to rubric domain (task/content/organization/expression)
    from src.data.rubric import RUBRIC_AREA_FROM_TRAIT

    long = labeled_matrix.copy()
    long["rubric_domain"] = long["trait"].map(RUBRIC_AREA_FROM_TRAIT)
    if "essay_length" not in long.columns:
        long["essay_length"] = pd.NA  # populate from loader upstream later
    if "score_level" not in long.columns:
        long["score_level"] = long["human_mean"].round().astype("Int64")
    if "grade" not in long.columns:
        long["grade"] = pd.NA  # populate from loader upstream later
    if "prompt_id" not in long.columns:
        long["prompt_id"] = pd.NA

    keep = [
        "essay_id", "purpose", "rubric_domain", "trait",
        "label", "score_level", "essay_length", "prompt_id", "grade",
    ]
    # Single-system pass for now — mark as "triangulated"
    long["explanation_system"] = "triangulated"
    keep.append("explanation_system")
    long[keep].to_csv(out_csv, index=False, encoding="utf-8-sig")
    log.info("Wrote model input CSV: %s (%d rows)", out_csv, len(long))
    return out_csv


def run_clmm(
    input_csv: Path,
    out_dir: Path = STAGE5_DIR,
    r_binary: str = "Rscript",
) -> int:
    """Subprocess-call Rscript stage5_clmm.R. Returns exit code."""
    script = write_r_script()
    cmd = [r_binary, str(script), str(input_csv), str(out_dir)]
    log.info("Invoking R: %s", " ".join(cmd))
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        log.error(
            "R not found on PATH. Install R and the 'ordinal' package, "
            "or override --r-binary to a full path to Rscript."
        )
        return 127
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    return res.returncode
