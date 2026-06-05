from __future__ import annotations
import pandas as pd

def select_headline_variant(qwk_df: pd.DataFrame, threshold: float = 0.50) -> str:
    analysed = qwk_df[qwk_df["trait"].isin(["content_1", "expression_2", "organization_1"])]
    pass_count = int((analysed["qwk"] >= threshold).sum())
    if pass_count == len(analysed):
        return "V1"
    if pass_count > 0:
        return "V2"
    return "V3"
