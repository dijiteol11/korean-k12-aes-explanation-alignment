"""
SBERT-based discourse coherence features (plan §4.2.1).

For each essay we compute four summary statistics of sentence-pair
cosine similarity:

    dis_sbert_mean_adjacent   — local coherence (mean of consecutive pairs)
    dis_sbert_std_adjacent    — variation in local coherence
    dis_sbert_min_adjacent    — weakest transition (prose-break detection)
    dis_sbert_mean_all_pairs  — global coherence (mean over all C(n,2) pairs)

These four metrics follow AES coherence literature
(Higgins et al., 2004; McNamara et al., 2014).

Implementation notes
--------------------
* The sentence-transformers library is loaded lazily so the rest of the
  pipeline runs on sandbox/CI environments without torch installed.
* Embeddings are cached to parquet keyed by (essay_id, sentence_idx).
  Re-running this script after a crash resumes rather than re-embedding.
* Sentence splitting uses KSS (Korean Sentence Splitter). The JSON's
  `문장수` count is used only as a sanity check, since KSS and the
  upstream annotator may disagree on ambiguous boundaries.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from configs.paths import (
    ACTIVE_EMBEDDING,
    EMBEDDING_MAX_TOKENS,
    EMBEDDING_MODELS,
    INTERIM_DIR,
)
from src.data.schema import Essay

log = logging.getLogger(__name__)


def sbert_cache_name(embedding: str, purpose: str | None) -> str:
    """Canonical cache-file stem: ``sbert_{embedding}__{purpose}`` per CLAUDE.md.

    Without purpose, falls back to ``sbert_{embedding}`` (whole-corpus builds
    only — concrete per-purpose runs must pass ``purpose``).
    """
    if purpose:
        slug = purpose.replace(" ", "_").replace("/", "_")
        return f"{embedding}__{slug}"
    return embedding


# --- Sentence splitting -----------------------------------------------------
from src.features.korean_analyzer import split_sentences as _split_sentences


# --- Model loading ----------------------------------------------------------
def load_embedder(model_name: str | None = None):
    """Return a sentence-transformers model, or raise a clear error."""
    name = model_name or EMBEDDING_MODELS[ACTIVE_EMBEDDING]
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError(
            "sentence-transformers is required for SBERT features.\n"
            "Install with: pip install sentence-transformers"
        ) from e
    model = SentenceTransformer(name)
    try:
        model.max_seq_length = EMBEDDING_MAX_TOKENS
    except Exception:  # pragma: no cover - attribute name varies by version
        pass
    return model


# --- Cosine statistics ------------------------------------------------------
def _cosine_matrix(X: np.ndarray) -> np.ndarray:
    """Cosine similarity matrix for L2-normalized or unnormalized rows."""
    norm = np.linalg.norm(X, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    Xn = X / norm
    return Xn @ Xn.T


def coherence_stats(sentence_vecs: np.ndarray) -> dict[str, float]:
    """Compute the four coherence features from a (n_sent, d) matrix."""
    n = sentence_vecs.shape[0]
    if n < 2:
        return {
            "dis_sbert_mean_adjacent": 0.0,
            "dis_sbert_std_adjacent": 0.0,
            "dis_sbert_min_adjacent": 0.0,
            "dis_sbert_mean_all_pairs": 0.0,
        }
    C = _cosine_matrix(sentence_vecs)
    adj = np.array([C[i, i + 1] for i in range(n - 1)])
    upper = C[np.triu_indices(n, k=1)]
    return {
        "dis_sbert_mean_adjacent": float(adj.mean()),
        "dis_sbert_std_adjacent": float(adj.std()),
        "dis_sbert_min_adjacent": float(adj.min()),
        "dis_sbert_mean_all_pairs": float(upper.mean()),
    }


# --- Orchestration ----------------------------------------------------------
def extract_discourse(
    essays: Iterable[Essay],
    model_name: str | None = None,
    *,
    batch_size: int = 32,
    cache_name: str | None = None,
) -> pd.DataFrame:
    """Return a DataFrame with essay_id + 4 SBERT coherence columns.

    Embedding cache is written to:
        INTERIM_DIR / f"sbert_{cache_name or ACTIVE_EMBEDDING}.parquet"
    keyed by (essay_id, sentence_idx). Safe to stop and resume.
    """
    cache_key = cache_name or ACTIVE_EMBEDDING
    cache_path = INTERIM_DIR / f"sbert_{cache_key}.parquet"
    # Note: callers that know the purpose should pass
    # ``cache_name=sbert_cache_name(ACTIVE_EMBEDDING, purpose)`` to avoid
    # cross-purpose overwrite. See CLAUDE.md naming convention.

    model = load_embedder(model_name)
    essays = list(essays)

    # 1. Split all essays into sentences and prepare work items
    all_sentences: list[str] = []
    owner: list[tuple[int, int]] = []  # (essay_id, sent_idx) per row
    for e in essays:
        sents = _split_sentences(e.answer.text)
        for i, s in enumerate(sents):
            all_sentences.append(s)
            owner.append((e.answer.id, i))

    log.info("Embedding %d sentences from %d essays with %s",
             len(all_sentences), len(essays),
             model_name or EMBEDDING_MODELS[ACTIVE_EMBEDDING])

    # 2. Encode
    vecs = model.encode(
        all_sentences,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    # 3. Persist embedding cache (full fidelity)
    cache_df = pd.DataFrame({
        "essay_id": [o[0] for o in owner],
        "sent_idx": [o[1] for o in owner],
        "sentence": all_sentences,
    })
    cache_df["embedding"] = [v.tobytes() for v in vecs]  # opaque bytes blob
    cache_df.to_parquet(cache_path, index=False)
    log.info("Wrote embedding cache to %s", cache_path)

    # 4. Aggregate per essay into the 4 coherence stats
    rows: list[dict] = []
    idx = 0
    for e in essays:
        n = sum(1 for o in owner[idx:] if o[0] == e.answer.id)
        essay_vecs = vecs[idx: idx + n]
        stats = coherence_stats(essay_vecs)
        rows.append({"essay_id": e.answer.id, **stats})
        idx += n

    return pd.DataFrame(rows)
