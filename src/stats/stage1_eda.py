"""
Stage 1 EDA: corpus-level sanity checks.

Produces:
    reports/stage1/score_distribution.csv
    reports/stage1/inter_rater_agreement.csv
    reports/stage1/text_length_by_grade.csv
    reports/stage1/rubric_coverage.csv
    reports/stage1/summary.md

These outputs feed the 'Data and measurement' section of the paper
(cf. plan §4.1) and flag any integrity issues before modeling begins.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402

from configs.paths import DATA_ROOT, REPORTS_DIR, TRAITS, TRAIT_NAMES_KO  # noqa: E402
from src.data.loader import load_all, to_dataframe  # noqa: E402

log = logging.getLogger(__name__)


def score_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Score histogram per trait, aggregated across both raters."""
    long_scores = pd.concat([
        df[["trait", "score_rater1"]].rename(columns={"score_rater1": "score"}),
        df[["trait", "score_rater2"]].rename(columns={"score_rater2": "score"}),
    ])
    counts = (
        long_scores.groupby(["trait", "score"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=["_holistic", *TRAITS])
    )
    counts.columns = [f"score_{int(c)}" for c in counts.columns]
    counts["n_total"] = counts.sum(axis=1)
    counts["trait_name_ko"] = counts.index.map(
        lambda t: "_holistic (총체적)" if t == "_holistic" else TRAIT_NAMES_KO.get(t, t)
    )
    return counts.reset_index()


def inter_rater_agreement(df: pd.DataFrame) -> pd.DataFrame:
    """Exact agreement, adjacent agreement, quadratic weighted kappa per trait.

    Uses only the 2-rater subset (every row is 2-rater by construction).
    """
    from sklearn.metrics import cohen_kappa_score

    rows: list[dict] = []
    for trait, sub in df.groupby("trait"):
        r1 = sub["score_rater1"].to_numpy()
        r2 = sub["score_rater2"].to_numpy()
        exact = (r1 == r2).mean()
        adjacent = (abs(r1 - r2) <= 1).mean()
        # Weighted kappa is undefined for a single point or degenerate labels
        try:
            qwk = cohen_kappa_score(r1, r2, weights="quadratic")
        except ValueError:
            qwk = float("nan")
        rows.append({
            "trait": trait,
            "trait_name_ko": "_holistic (총체적)" if trait == "_holistic"
                              else TRAIT_NAMES_KO.get(trait, trait),
            "n": len(sub),
            "exact_pct": round(100 * exact, 2),
            "adjacent_pct": round(100 * adjacent, 2),
            "qwk": round(qwk, 4) if qwk == qwk else None,
            "mean_score": round(float(((r1 + r2) / 2).mean()), 3),
        })
    out = pd.DataFrame(rows)
    trait_order = ["_holistic", *TRAITS]
    out["__order"] = out["trait"].map({t: i for i, t in enumerate(trait_order)})
    return out.sort_values("__order").drop(columns="__order").reset_index(drop=True)


def text_length_by_grade(df: pd.DataFrame) -> pd.DataFrame:
    # One row per essay — deduplicate on essay_id
    essays = df.drop_duplicates("essay_id")
    return (
        essays.groupby("grade")
        .agg(
            n=("essay_id", "count"),
            mean_syllable=("len_syllable", "mean"),
            median_syllable=("len_syllable", "median"),
            min_syllable=("len_syllable", "min"),
            max_syllable=("len_syllable", "max"),
            mean_word=("len_word", "mean"),
        )
        .round(1)
        .reset_index()
    )


def rubric_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """How many distinct rubric_keys appear per trait across the corpus.

    The 14-026 rubric system uses a keyed tree (e.g. B-00A-1B-2G). If the
    corpus draws from multiple rubric variants per trait, LLM prompting
    must be conditioned on the correct variant per essay.
    """
    ana = df[df["trait"] != "_holistic"]
    cov = (
        ana.groupby("trait")["rubric_key"]
        .nunique()
        .rename("n_unique_rubric_keys")
        .reset_index()
    )
    cov["trait_name_ko"] = cov["trait"].map(TRAIT_NAMES_KO)
    return cov


def corpus_composition(df: pd.DataFrame) -> pd.DataFrame:
    """Grade × subject × purpose × level cross-tabulation.

    This is the diagnostic that determines the analytic scope of the study
    (see progress.md §11). If `purpose` has multiple values, rubric trees
    likely differ across them and the trait-set assumption must be verified.
    """
    essays = df.drop_duplicates("essay_id")
    tab = (
        essays.groupby(["grade", "subject", "purpose", "level"])
        .size()
        .rename("n")
        .reset_index()
        .sort_values(["grade", "subject", "purpose", "level"])
    )
    return tab


def rubric_by_purpose(df: pd.DataFrame) -> pd.DataFrame:
    """For each (purpose × trait), the set of rubric_key variants observed.

    If the rubric_key changes across purposes for the same trait name,
    the traits are NOT directly comparable across purposes. This is the
    central diagnostic for deciding study scope.
    """
    ana = df[df["trait"] != "_holistic"].copy()
    # Attach purpose from the essay-level metadata (already on every row)
    out = (
        ana.groupby(["purpose", "trait"])["rubric_key"]
        .agg(["nunique", lambda s: sorted(s.dropna().unique())[:5]])
        .rename(columns={"nunique": "n_unique_keys",
                          "<lambda_0>": "sample_keys"})
        .reset_index()
    )
    return out


def trait_presence_by_purpose(df: pd.DataFrame) -> pd.DataFrame:
    """Which traits appear for which purposes.

    A trait absent for a given purpose means any pooled model of that trait
    would silently drop all essays of that purpose.
    """
    ana = df[df["trait"] != "_holistic"].copy()
    pivot = (
        ana.groupby(["purpose", "trait"])["essay_id"]
        .nunique()
        .unstack(fill_value=0)
    )
    return pivot.reset_index()


def rubric_structure_summary(essays) -> pd.DataFrame:
    """Summarize rubric block structure observed across the corpus.

    Returns one row per unique (purpose, n_traits, purpose_code,
    achievement) combination with an essay count. Reveals whether
    different purposes share rubric templates or diverge.
    """
    from collections import Counter
    from src.data.rubric import parse_rubric

    bucket: Counter = Counter()
    for e in essays:
        if not e.rubric_raw:
            continue
        rb = parse_rubric(e.rubric_raw)
        key = (rb.purpose, len(rb.analytic), rb.purpose_code or "",
                rb.achievement[:80])
        bucket[key] += 1

    rows = [
        {
            "purpose": k[0],
            "n_traits": k[1],
            "purpose_code": k[2],
            "achievement_preview": k[3] + ("…" if len(k[3]) == 80 else ""),
            "n_essays": n,
        }
        for k, n in bucket.most_common()
    ]
    return pd.DataFrame(rows)


def write_summary_md(
    out_dir: Path,
    n_essays: int,
    dist: pd.DataFrame,
    irr: pd.DataFrame,
    length: pd.DataFrame,
    cov: pd.DataFrame,
    composition: pd.DataFrame,
    rub_by_purp: pd.DataFrame,
    trait_pres: pd.DataFrame,
    rub_struct: pd.DataFrame,
) -> None:
    lines = [
        "# Stage 1 EDA Summary",
        "",
        f"- **N essays**: {n_essays}",
        "",
        "## ⚠ Scope diagnostic — read first",
        "",
        "This section determines whether the TRAIT set in configs/paths.py "
        "applies to the entire corpus, or only to essays of a specific "
        "purpose. If `purpose` contains values beyond '설명' AND the rubric "
        "trees differ, the study scope must be restricted before Stage 2.2.",
        "",
        "### Rubric-block structure summary",
        "",
        "One row per unique (purpose × n_traits × purpose_code × "
        "achievement) combination. If multiple rows share a purpose but "
        "differ on any other column, the rubric has variants that must be "
        "handled separately by the LLM prompt builder.",
        "",
        rub_struct.to_markdown(index=False),
        "",
        "Full text of every unique rubric variant is dumped to "
        "`reports/rubrics/rubric__<purpose>.md` — run "
        "`python -m scripts.dump_rubrics`.",
        "",
        "### Corpus composition (grade × subject × purpose × level)",
        "",
        composition.to_markdown(index=False),
        "",
        "### Rubric key diversity per (purpose × trait)",
        "",
        "If `n_unique_keys` > 1 for the same (purpose, trait), more than one "
        "rubric variant is present and the LLM prompt must condition on the "
        "correct variant per essay.",
        "",
        rub_by_purp.to_markdown(index=False),
        "",
        "### Trait presence across purposes",
        "",
        "A zero here indicates the given trait is absent for essays of that "
        "purpose. Any zero implies a pooled model would silently drop those "
        "essays. Decide study scope accordingly.",
        "",
        trait_pres.to_markdown(index=False),
        "",
        "## Text length by grade (syllables)",
        "",
        length.to_markdown(index=False),
        "",
        "## Inter-rater agreement (2-rater Cohen's weighted κ)",
        "",
        irr.to_markdown(index=False),
        "",
        "## Score distribution (both raters pooled)",
        "",
        dist.to_markdown(index=False),
        "",
        "## Rubric coverage (n unique rubric_keys per trait, corpus-wide)",
        "",
        cov.to_markdown(index=False),
        "",
        "## Integrity checks",
        "",
        "- Essays missing one of the 8 traits are still parsed (lenient "
        "mode) but their missing trait scores are NaN. Non-zero counts in "
        "the trait-presence table below the expected total flag this.",
        "- QWK values below ~0.40 warrant examining rater-pair composition "
        "for that trait (plan §4.1 implicitly assumes adequate human IRR).",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out_dir = REPORTS_DIR / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Lenient load: tolerate purpose-heterogeneous rubrics so we can
    # enumerate the corpus even if it contains 설득 / 친교 및 정서 essays
    # with different trait sets.
    essays = load_all(DATA_ROOT, strict_traits=False)
    if not essays:
        log.error("No essays found under %s", DATA_ROOT)
        return

    df = to_dataframe(essays)
    log.info("Loaded %d essays → %d trait-score rows", len(essays), len(df))

    dist = score_distribution(df)
    irr = inter_rater_agreement(df)
    length = text_length_by_grade(df)
    cov = rubric_coverage(df)
    composition = corpus_composition(df)
    rub_by_purp = rubric_by_purpose(df)
    trait_pres = trait_presence_by_purpose(df)
    rub_struct = rubric_structure_summary(essays)

    dist.to_csv(out_dir / "score_distribution.csv", index=False)
    irr.to_csv(out_dir / "inter_rater_agreement.csv", index=False)
    length.to_csv(out_dir / "text_length_by_grade.csv", index=False)
    cov.to_csv(out_dir / "rubric_coverage.csv", index=False)
    composition.to_csv(out_dir / "corpus_composition.csv", index=False)
    rub_by_purp.to_csv(out_dir / "rubric_by_purpose.csv", index=False)
    trait_pres.to_csv(out_dir / "trait_presence_by_purpose.csv", index=False)
    rub_struct.to_csv(out_dir / "rubric_structure_summary.csv", index=False)
    write_summary_md(
        out_dir, len(essays), dist, irr, length, cov,
        composition, rub_by_purp, trait_pres, rub_struct,
    )

    log.info("Wrote Stage 1 outputs to %s", out_dir)


if __name__ == "__main__":
    main()
