"""
Meta-level features: text length, word count, sentence count.

All three are present in the JSON (len_syllable, len_word, feature['문장수']),
but we re-expose them as engineered features so downstream modeling has a
single source of truth.
"""
from __future__ import annotations

from src.data.schema import Essay


def extract_meta(essay: Essay) -> dict[str, float]:
    n_sent = float(essay.answer.feature.get("문장수", 0))
    n_syl = float(essay.answer.len_syllable)
    n_word = float(essay.answer.len_word)

    mean_sent_syllable = n_syl / n_sent if n_sent > 0 else 0.0
    mean_sent_word = n_word / n_sent if n_sent > 0 else 0.0

    return {
        "meta_len_syllable": n_syl,
        "meta_len_word": n_word,
        "meta_n_sentence": n_sent,
        "meta_mean_sent_syllable": mean_sent_syllable,
        "meta_mean_sent_word": mean_sent_word,
    }
