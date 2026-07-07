"""
Cross-validation splitters (plan §4.2.2 + robustness).

Two schemes:

1. GradeStratifiedKFold (PRIMARY)
   5-fold stratified on `grade` so each fold preserves the
   초5:초6:중1:중2:중3 distribution. This is the default reporting
   scheme in the main results table.

2. LeaveOnePromptOut (ROBUSTNESS)
   Rotates over unique prompt identifiers: each fold trains on all
   other prompts and evaluates on the held-out prompt. This tests
   generalization to unseen writing topics — a stronger
   validity check (Ridley et al., 2021; Do et al., 2023).

Both splitters yield (train_idx, test_idx, fold_label) tuples so
the training loop can name folds consistently in reports.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold


class GradeStratifiedKFold:
    def __init__(self, n_splits: int = 5, random_state: int = 42):
        self.n_splits = n_splits
        self.random_state = random_state

    def split(
        self, df: pd.DataFrame, stratify_col: str = "grade"
    ) -> Iterator[tuple[np.ndarray, np.ndarray, str]]:
        skf = StratifiedKFold(
            n_splits=self.n_splits,
            shuffle=True,
            random_state=self.random_state,
        )
        y_strat = df[stratify_col].to_numpy()
        for fold_i, (tr, te) in enumerate(skf.split(df, y_strat), start=1):
            yield tr, te, f"grade_fold_{fold_i}"


class LeaveOnePromptOut:
    """Leave-one-prompt-out (LOPO)."""

    def __init__(self, prompt_col: str = "prompt_id"):
        self.prompt_col = prompt_col

    def split(
        self, df: pd.DataFrame, stratify_col: str | None = None
    ) -> Iterator[tuple[np.ndarray, np.ndarray, str]]:
        prompts = df[self.prompt_col].unique()
        # Sort for determinism
        for pid in sorted(prompts):
            mask = (df[self.prompt_col] == pid).to_numpy()
            test_idx = np.where(mask)[0]
            train_idx = np.where(~mask)[0]
            # Skip if the held-out prompt has no data or the training side
            # is empty (degenerate corpus)
            if len(test_idx) == 0 or len(train_idx) == 0:
                continue
            yield train_idx, test_idx, f"prompt_{pid}"


SPLITTERS = {
    "grade_stratified": GradeStratifiedKFold,
    "cross_prompt":     LeaveOnePromptOut,
}
