"""Select the v1.3 score-premise headline variant."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

QWK_PREMISE_THRESHOLD: float = 0.50


@dataclass(frozen=True)
class HeadlineVariant:
    variant: str
    n_passing_traits: int
    threshold: float
    headline_note: str


def select_headline_variant(
    qwk_df: pd.DataFrame,
    *,
    threshold: float = QWK_PREMISE_THRESHOLD,
) -> HeadlineVariant:
    if "qwk" not in qwk_df.columns:
        raise KeyError("qwk_df must contain a 'qwk' column")
    n_passing = int((qwk_df["qwk"] >= threshold).sum())
    if n_passing >= 3:
        return HeadlineVariant(
            variant="V1",
            n_passing_traits=n_passing,
            threshold=threshold,
            headline_note=(
                "All analyzed traits meet the score-level premise; use lower-bound "
                "human reliability wording."
            ),
        )
    if n_passing == 2:
        return HeadlineVariant(
            variant="V2",
            n_passing_traits=n_passing,
            threshold=threshold,
            headline_note=(
                "Two analyzed traits meet the score-level premise; name the failing "
                "trait and weaken the score-level wording."
            ),
        )
    return HeadlineVariant(
        variant="V3",
        n_passing_traits=n_passing,
        threshold=threshold,
        headline_note="Score-level premise is not met; remove score-level premise wording.",
    )
