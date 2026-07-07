"""
Vocabulary grade feature extraction based on Kim (2023) vocabulary list.

The Kim 2023 list contains ~40,000 Korean words classified into 5 grade levels
(1학년-5학년). This module provides:
1. VocabGradeLookup: dictionary lookup with pickle caching
2. extract_vocab_features(): per-essay vocabulary grade distribution features

Feature family: vocab_grade
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.loader import Essay

log = logging.getLogger(__name__)


class VocabGradeLookup:
    """
    Dictionary-based vocabulary grade lookup with caching.

    Loads from Excel on first access, then caches to pickle for fast reload.
    Grade values: 1-5 (1학년-5학년); None for out-of-vocabulary words.
    """

    def __init__(
        self,
        xlsx_path: Path | str,
        cache_path: Path | str | None = None,
    ):
        self.xlsx_path = Path(xlsx_path)
        if cache_path is None:
            cache_path = self.xlsx_path.with_suffix(".pkl")
        self.cache_path = Path(cache_path)
        self._lookup: dict[str, int] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load lookup table on first access."""
        if self._loaded:
            return

        if self.cache_path.exists():
            self._load_from_cache()
        else:
            self._load_from_excel()
            self._save_to_cache()

        self._loaded = True
        log.info(
            "VocabGradeLookup loaded: %d entries from %s",
            len(self._lookup),
            self.cache_path if self.cache_path.exists() else self.xlsx_path,
        )

    def _load_from_excel(self) -> None:
        """Load vocabulary grades from Excel file (single sheet)."""
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError("pandas required for Excel loading") from e

        log.info("Loading vocabulary grades from Excel: %s", self.xlsx_path)
        df = pd.read_excel(self.xlsx_path, sheet_name=0, engine="openpyxl")

        # Columns: [등급(학년), 단어, ...]
        # First column: grade (1학년-5학년)
        # Second column: word
        grade_col = df.columns[0]
        word_col = df.columns[1]

        for _, row in df.iterrows():
            word = str(row[word_col]).strip()
            grade_str = str(row[grade_col]).strip()

            # Parse grade from "1등급" or "1학년" -> 1
            # The Excel may use either "등급" or "학년" suffix
            grade_str_clean = grade_str.replace("등급", "").replace("학년", "").strip()
            try:
                grade = int(grade_str_clean)
                if 1 <= grade <= 5:
                    # Keep the lower grade for duplicate words
                    # (simpler vocabulary = earlier grade)
                    if word not in self._lookup or grade < self._lookup[word]:
                        self._lookup[word] = grade
            except ValueError:
                continue

    def _load_from_cache(self) -> None:
        """Load from pickle cache."""
        log.info("Loading vocabulary grades from cache: %s", self.cache_path)
        with open(self.cache_path, "rb") as f:
            self._lookup = pickle.load(f)

    def _save_to_cache(self) -> None:
        """Save to pickle cache."""
        log.info("Saving vocabulary grades to cache: %s", self.cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "wb") as f:
            pickle.dump(self._lookup, f)

    def grade(self, word: str) -> int | None:
        """
        Look up grade for a single word.

        Returns:
            Grade (1-5) or None if out-of-vocabulary.
        """
        self._ensure_loaded()
        return self._lookup.get(word.strip())

    def batch_grade(self, words: list[str]) -> list[int | None]:
        """Look up grades for multiple words."""
        self._ensure_loaded()
        return [self._lookup.get(w.strip()) for w in words]

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._lookup)

    def __contains__(self, word: str) -> bool:
        self._ensure_loaded()
        return word.strip() in self._lookup


def extract_vocab_features(
    essay: "Essay",
    lookup: VocabGradeLookup,
) -> dict[str, float]:
    """
    Extract vocabulary grade features from essay content.

    Uses Kiwi morphological analysis to extract content words (nouns, verbs,
    adjectives, adverbs) and looks up their grade levels.

    Features (vocab_grade family):
        vocab_grade_1_ratio: proportion of grade-1 words
        vocab_grade_2_ratio: proportion of grade-2 words
        vocab_grade_3_ratio: proportion of grade-3 words
        vocab_grade_4_ratio: proportion of grade-4 words
        vocab_grade_5_ratio: proportion of grade-5 words
        vocab_grade_mean: mean grade of graded words (higher = more advanced)
        vocab_out_of_grade_ratio: proportion of words not in the lexicon
        vocab_graded_count: total number of words that received a grade

    Args:
        essay: Essay object with answer.content text
        lookup: VocabGradeLookup instance

    Returns:
        Dictionary of vocabulary grade features.
    """
    try:
        from src.features.kiwi_analyzer import get_kiwi
        kiwi = get_kiwi()
    except ImportError:
        log.warning("kiwipiepy not available; returning zero vocab features")
        return _zero_vocab_features()

    text = essay.answer.text or ""

    # Analyze with Kiwi (shared instance)
    tokens = kiwi.tokenize(text)

    # Content word POS tags (nouns, verbs, adjectives, adverbs)
    content_pos = {
        "NNG",  # 일반 명사
        "NNP",  # 고유 명사
        "NNB",  # 의존 명사
        "VV",   # 동사
        "VA",   # 형용사
        "MAG",  # 일반 부사
    }

    # Extract content word lemmas
    content_words = []
    for token in tokens:
        if token.tag in content_pos:
            # Use form (surface form) for lookup
            content_words.append(token.form)

    if not content_words:
        return _zero_vocab_features()

    # Grade lookup
    grades = lookup.batch_grade(content_words)

    # Count by grade
    grade_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    graded_words = []
    out_of_vocab = 0

    for grade in grades:
        if grade is not None:
            grade_counts[grade] += 1
            graded_words.append(grade)
        else:
            out_of_vocab += 1

    total = len(content_words)
    graded_count = len(graded_words)

    features = {
        "vocab_grade_1_ratio": grade_counts[1] / total,
        "vocab_grade_2_ratio": grade_counts[2] / total,
        "vocab_grade_3_ratio": grade_counts[3] / total,
        "vocab_grade_4_ratio": grade_counts[4] / total,
        "vocab_grade_5_ratio": grade_counts[5] / total,
        "vocab_out_of_grade_ratio": out_of_vocab / total,
        "vocab_graded_count": graded_count,
    }

    # Mean grade (only for graded words)
    if graded_words:
        features["vocab_grade_mean"] = sum(graded_words) / len(graded_words)
    else:
        features["vocab_grade_mean"] = 0.0

    return features


def _zero_vocab_features() -> dict[str, float]:
    """Return zero-valued vocabulary features for fallback."""
    return {
        "vocab_grade_1_ratio": 0.0,
        "vocab_grade_2_ratio": 0.0,
        "vocab_grade_3_ratio": 0.0,
        "vocab_grade_4_ratio": 0.0,
        "vocab_grade_5_ratio": 0.0,
        "vocab_out_of_grade_ratio": 0.0,
        "vocab_grade_mean": 0.0,
        "vocab_graded_count": 0,
    }
