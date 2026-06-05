from __future__ import annotations
import pandas as pd
FAMILY_ORDER = ["lex", "vocab_grade", "case_marker", "morph_prop", "syn", "dis_nonSBERT", "dis_SBERT", "meta"]

def top_families_for_cell(local_shap_df: pd.DataFrame, essay_id: int, trait: str, *, k: int = 3) -> tuple[str, ...]:
    cell = local_shap_df[(local_shap_df["essay_id"].astype(int) == int(essay_id)) & (local_shap_df["trait"].astype(str) == str(trait))].copy()
    if cell.empty:
        return ()
    order = {family: i for i, family in enumerate(FAMILY_ORDER)}
    cell["_abs_shap"] = cell["shap_sum"].abs()
    cell["_family_order"] = cell["family"].map(lambda x: order.get(str(x), len(order)))
    ranked = cell.sort_values(["_abs_shap", "_family_order", "family"], ascending=[False, True, True], kind="mergesort")
    return tuple(ranked.head(k)["family"].astype(str))
