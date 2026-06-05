# Korean K-12 AES Explanation Alignment (Anonymous Public Package)

This repository is an anonymized reproducibility package for a manuscript on score-level agreement and operational explanation alignment in Korean K-12 analytic automated essay scoring.

It includes anonymous manuscript files, redacted pre-registration copies, public aggregate result tables and figures, analysis code, and documentation for restricted corpus access. It excludes raw student essays, raw model outputs, provider logs, author/reviewer identities, local paths, and internal planning artifacts.

The manuscript file is a compact anonymized review copy derived from a longer internal working draft; supplementary audit details are provided in `manuscript/supplement_anonymized.md`.

## Quick start

```bash
python -m venv .venv
pip install -r requirements.txt
python scripts/score_level_qwk.py
python scripts/run_stage5_analysis.py
python scripts/run_stage10D_robustness.py
```
