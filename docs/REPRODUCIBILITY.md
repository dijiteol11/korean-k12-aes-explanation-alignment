# Reproducibility

1. Install dependencies from `requirements.txt` or `environment.yml`.
2. Use public derived tables under `data/derived_public/` to regenerate manuscript summary tables.
3. Use restricted raw data only in a private environment after obtaining independent corpus access.
4. Run `python scripts/score_level_qwk.py`, `python scripts/run_stage5_analysis.py`, and `python scripts/run_stage10D_robustness.py`.

This anonymous package provides aggregate reproducibility. Full raw-text replication requires restricted corpus access and private model-output logs, neither of which is redistributed here.
