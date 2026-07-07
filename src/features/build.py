"""
Stage 2.1 feature-matrix builder.

Combines meta + morphology + (optional) SBERT discourse features into
a single analysis-ready parquet at:

    data/processed/feature_matrix__{embedding_key}.parquet

Running order
-------------
1. Load parsed essays via src.data.loader.load_all
2. Compute non-SBERT features (fast, CPU-only)
3. Compute SBERT coherence features (optional; requires
   sentence-transformers + the target embedding model)
4. Merge into a single DataFrame keyed by essay_id
5. Persist + print a summary

Usage
-----
    # Fast path — skip SBERT (useful for wiring tests)
    python -m src.features.build --no-sbert

    # Full run — primary embedding
    python -m src.features.build

    # Robustness check — another embedding model
    AES_EMBEDDING=robust_2 python -m src.features.build
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402

from configs.paths import (  # noqa: E402
    ACTIVE_EMBEDDING,
    DATA_ROOT,
    EMBEDDING_MODELS,
    PROCESSED_DIR,
    REPORTS_DIR,
    TRAITS,
    VOCAB_GRADE_XLSX,
    VOCAB_GRADE_CACHE,
)
from src.data.loader import load_all  # noqa: E402
from src.features.meta import extract_meta  # noqa: E402
from src.features.morphology import extract_morphology  # noqa: E402
from src.features.vocabulary import VocabGradeLookup, extract_vocab_features  # noqa: E402
from src.features.sentence_complexity import extract_case_markers  # noqa: E402

log = logging.getLogger(__name__)


def build_nonsbert_frame(essays, vocab_lookup: VocabGradeLookup | None = None) -> pd.DataFrame:
    """Per-essay row with meta + morphology + vocab_grade + case_marker features."""
    rows = []
    for e in essays:
        row = {"essay_id": e.answer.id}
        row.update(extract_meta(e))
        row.update(extract_morphology(e))

        # KICE AES features: vocabulary grade (Kim 2023)
        if vocab_lookup is not None:
            row.update(extract_vocab_features(e, vocab_lookup))

        # KICE AES features: case markers (격조사)
        row.update(extract_case_markers(e))

        # Meta for downstream filtering / stratification
        row["grade"] = e.question.grade
        row["subject"] = e.question.subject
        row["level"] = e.question.level
        row["purpose"] = e.question.purpose
        row["region"] = e.answer.region
        row["gender"] = e.answer.gender
        # Prompt identifiers for cross-prompt CV (plan §4, robustness)
        row["prompt_id"] = e.question.id
        row["topic"] = e.question.topic
        # Target columns: mean of the 2 raters' scores per trait
        row["target__holistic"] = e.holistic.score_mean
        for t in TRAITS:
            row[f"target__{t}"] = e.analytic[t].score_mean
        rows.append(row)
    return pd.DataFrame(rows)


def build(include_sbert: bool = True, purpose: str | None = None) -> pd.DataFrame:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log.info("Loading corpus from %s", DATA_ROOT)

    from configs.paths import PURPOSES_IN_SCOPE
    if purpose is not None and purpose not in PURPOSES_IN_SCOPE:
        log.warning(
            "Requested purpose %r is outside PURPOSES_IN_SCOPE %r. "
            "Proceeding anyway, but verify plan §4.1.3.",
            purpose, PURPOSES_IN_SCOPE,
        )
    filter_tuple = (purpose,) if purpose else PURPOSES_IN_SCOPE
    essays = load_all(DATA_ROOT, purposes=filter_tuple)
    log.info("Loaded %d essays (purposes=%s)", len(essays), filter_tuple)
    if not essays:
        log.error("No essays found — aborting.")
        sys.exit(1)

    # Initialize vocabulary grade lookup (Kim 2023)
    vocab_lookup: VocabGradeLookup | None = None
    if VOCAB_GRADE_XLSX.exists():
        try:
            vocab_lookup = VocabGradeLookup(VOCAB_GRADE_XLSX, VOCAB_GRADE_CACHE)
            log.info("Vocab grade lookup initialized: %s", VOCAB_GRADE_XLSX)
        except Exception as e:
            log.warning("Failed to load vocab grade lookup: %s", e)
    else:
        log.warning("Vocab grade Excel not found: %s", VOCAB_GRADE_XLSX)

    frame = build_nonsbert_frame(essays, vocab_lookup)
    log.info("Non-SBERT features: %s", frame.shape)

    if include_sbert:
        import os as _os
        from src.features.discourse import extract_discourse, sbert_cache_name

        batch_size = int(_os.environ.get("AES_SBERT_BATCH_SIZE", "32"))
        log.info("Running SBERT with %s → %s (batch_size=%d)",
                 ACTIVE_EMBEDDING, EMBEDDING_MODELS[ACTIVE_EMBEDDING],
                 batch_size)
        sbert_df = extract_discourse(
            essays,
            batch_size=batch_size,
            cache_name=sbert_cache_name(ACTIVE_EMBEDDING, purpose),
        )
        frame = frame.merge(sbert_df, on="essay_id", how="left")
        log.info("Full feature matrix: %s", frame.shape)
        embed_suffix = f"__{ACTIVE_EMBEDDING}"
    else:
        log.info("SBERT skipped.")
        embed_suffix = "__no_sbert"

    # Filename encodes purpose and embedding so that the four+ output
    # parquets (2 purposes × 3 embeddings) never collide.
    purpose_slug = (purpose or "ALL").replace(" ", "_").replace("/", "_")
    suffix = f"__{purpose_slug}{embed_suffix}"

    out_path = PROCESSED_DIR / f"feature_matrix{suffix}.parquet"
    try:
        frame.to_parquet(out_path, index=False)
        log.info("Wrote %s", out_path)
    except (ImportError, ValueError) as e:
        out_path = out_path.with_suffix(".csv")
        frame.to_csv(out_path, index=False)
        log.warning("parquet engine unavailable (%s); wrote CSV instead: %s",
                    e, out_path)

    # Summary report
    report_dir = REPORTS_DIR / "stage2_features"
    report_dir.mkdir(parents=True, exist_ok=True)

    feature_cols = [
        c for c in frame.columns
        if not c.startswith("target__")
        and c not in {"essay_id", "grade", "subject", "level",
                       "purpose", "region", "gender",
                       "prompt_id", "topic"}
    ]
    desc = frame[feature_cols].describe().T
    desc.to_csv(report_dir / f"feature_describe{suffix}.csv")

    nulls = frame[feature_cols].isnull().sum()
    nulls_nonzero = nulls[nulls > 0]
    if len(nulls_nonzero):
        log.warning("Null counts > 0:\n%s", nulls_nonzero.to_string())
    log.info("n_features=%d  n_rows=%d", len(feature_cols), len(frame))

    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-sbert", action="store_true",
                        help="Skip SBERT coherence features.")
    parser.add_argument(
        "--purpose",
        type=str,
        default=None,
        help="Build matrix only for essays of this purpose "
             "(e.g. '설명' or '설득'). If omitted, builds one combined "
             "matrix for all purposes in PURPOSES_IN_SCOPE. For the "
             "v2.1 design, run this once per purpose value.",
    )
    args = parser.parse_args()
    build(include_sbert=not args.no_sbert, purpose=args.purpose)


if __name__ == "__main__":
    main()
