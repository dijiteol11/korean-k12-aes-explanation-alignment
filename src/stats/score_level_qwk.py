from __future__ import annotations
from pathlib import Path
import pandas as pd
from src.models.metrics import quadratic_weighted_kappa

def compute_qwk_table(df: pd.DataFrame, *, trait_col="trait", human_col="xgb_score", llm_col="llm_score") -> pd.DataFrame:
    rows = []
    for (purpose, trait), cell in df.groupby(["purpose", trait_col], sort=True):
        rows.append({"purpose": purpose, "trait": trait, "n": len(cell), "qwk": quadratic_weighted_kappa(cell[human_col], cell[llm_col]), "xgb_mean": float(cell[human_col].mean()), "llm_mean": float(cell[llm_col].mean())})
    return pd.DataFrame(rows)

def main() -> int:
    print(pd.read_csv(Path("data/derived_public/table1_score_level_qwk.csv")).to_markdown(index=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
