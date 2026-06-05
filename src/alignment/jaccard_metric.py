from __future__ import annotations
import pandas as pd

def normalize_family_set(value) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, float) and pd.isna(value):
        return frozenset()
    if isinstance(value, str):
        return frozenset(part.strip() for part in value.split("|") if part.strip())
    return frozenset(str(part) for part in value if str(part))

def jaccard(left, right) -> float:
    left_set = normalize_family_set(left)
    right_set = normalize_family_set(right)
    union = left_set | right_set
    return 0.0 if not union else len(left_set & right_set) / len(union)
