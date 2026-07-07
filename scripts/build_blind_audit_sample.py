"""Build Stage 4 detector spot-check sample (plan §41, 2026-05-28).

**Direction (supersedes §40 random blind audit)**: F_LLM is a deterministic
exact-match metric, so the machine detector is the deterministic *operational
scorer* (NOT a gold standard). Human coding is reduced to a *diagnostic
comparator* — a detector-miss spot-check — NOT a κ≥0.70 blind-audit gate. v1.3 §7 (SHA c6c58acd…) is preserved as pre-registered
intent; this is a documented deviation (see v2.6 §4.1.2.1 (d) amendment).

Two modes:
  - ``spotcheck`` (default, §41.3): stratified sample over the 3 analyzed
    traits — ~15 *failure* cells (auto-detector empty → most likely place a
    strict match missed an obvious invocation) + ~5 *control* cells
    (detector-positive, blind control to avoid priming). Also writes the
    analyst-only ``machine_truth.csv`` (the deterministic detector result)
    so the human↔machine comparison can be computed.
  - ``random`` (legacy, §40): random + stratified-by-purpose 10+10.

Outputs (under ``reports/stage4_llm/keyword_blind_audit/``):
  - ``coders/coder_a.csv``        — Coder A input.
                                    Columns: cell_id, essay_id, trait, purpose,
                                    family, rationale_excerpt, detected (BLANK —
                                    coder fills every row 0/1; present family → 1).
  - ``coders/coder_b.csv``        — Coder B input. Identical schema.
  - ``analyst/prevalence_summary.md`` — per-cell auto-detector result + coverage.
  - ``analyst/machine_truth.csv``     — (spotcheck) deterministic detector 0/1
                                    per (cell, family), long-format. analyst-only.
  - ``analyst/spotcheck_strata.md``   — (spotcheck) failure/control labels.
                                    ANALYST-ONLY (would break the blind).

Blind protection: coders/ and analyst/ are physically separate so the
detector results never bundle with the coder files.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.paths import REPORTS_DIR
from src.alignment.llm_family_detector import (
    KEYWORD_SET,
    detect_families,
    iter_stage_c_records,
)

SMOKE_C_DIR = REPORTS_DIR / "stage4_llm" / "smoke" / "C"
OUT_DIR = REPORTS_DIR / "stage4_llm" / "keyword_blind_audit"
ANALYZED_TRAITS = ("expression_2", "organization_1", "content_1")
SAMPLE_SEED = 42
SAMPLES_PER_PURPOSE = 10
RATIONALE_EXCERPT_MAX = 600  # chars, for CSV legibility
# Spot-check (§41.3): detector-miss failure cells + blind controls.
N_FAILURE_DEFAULT = 15
N_CONTROL_DEFAULT = 5


def _build_candidate_pool(stage_c_paths: list[Path]) -> list[dict]:
    """Flatten Stage C records to (essay_id, trait, purpose, text) entries."""
    pool: list[dict] = []
    for path in stage_c_paths:
        if not path.exists():
            continue
        for record in iter_stage_c_records(path):
            essay_id = int(record["essay_id"])
            purpose = str(record.get("purpose") or path.stem)
            rationale = record.get("rationale", {}) or {}
            for trait, entry in rationale.items():
                text = entry.get("text", "") if isinstance(entry, dict) else str(entry or "")
                if not text:
                    continue
                pool.append({
                    "essay_id": essay_id,
                    "trait": str(trait),
                    "purpose": purpose,
                    "rationale_text": text,
                })
    return pool


def select_sample(
    candidates: list[dict],
    *,
    n_per_purpose: int = SAMPLES_PER_PURPOSE,
    seed: int = SAMPLE_SEED,
) -> list[dict]:
    rng = random.Random(seed)
    by_purpose: dict[str, list[dict]] = {}
    for item in candidates:
        by_purpose.setdefault(item["purpose"], []).append(item)
    chosen: list[dict] = []
    for purpose in sorted(by_purpose):
        bucket = by_purpose[purpose]
        k = min(n_per_purpose, len(bucket))
        chosen.extend(rng.sample(bucket, k))
    return sorted(chosen, key=lambda r: (r["purpose"], r["essay_id"], r["trait"]))


def select_spotcheck_sample(
    candidates: list[dict],
    *,
    n_failure: int = N_FAILURE_DEFAULT,
    n_control: int = N_CONTROL_DEFAULT,
    seed: int = SAMPLE_SEED,
    analyzed_traits: tuple[str, ...] = ANALYZED_TRAITS,
    analyzer=None,
) -> list[dict]:
    """Stratified detector-miss spot-check sample (§41.3).

    Restricts to analyzed traits, then classifies each cell by the
    deterministic auto-detector:

    - ``failure``: ``detect_families`` empty (detector found NO family) — the
      cell where a strict exact/lemma match is most likely to have missed an
      obvious invocation a human would catch. This is the diagnostic target.
    - ``control``: detector-positive (>=1 family) — blind control so the
      annotator is not primed to only find misses.

    Samples ``n_failure`` failure + ``n_control`` control cells
    (seed-deterministic), then blind-shuffles so failure/control are not
    positionally separable. The ``stratum`` key is analyst-only and is never
    written to the coder CSV.
    """
    rng = random.Random(seed)
    failure: list[dict] = []
    control: list[dict] = []
    for item in candidates:
        if item["trait"] not in analyzed_traits:
            continue
        detection = detect_families(item["rationale_text"], analyzer=analyzer)
        entry = dict(item)
        if detection.is_empty:
            entry["stratum"] = "failure"
            failure.append(entry)
        else:
            entry["stratum"] = "control"
            control.append(entry)

    def _take(pool: list[dict], k: int) -> list[dict]:
        ordered = sorted(pool, key=lambda r: (r["purpose"], r["essay_id"], r["trait"]))
        if k >= len(ordered):
            return ordered
        return rng.sample(ordered, k)

    chosen = _take(failure, n_failure) + _take(control, n_control)
    rng.shuffle(chosen)  # blind: hide failure/control ordering from the coder
    return chosen


def write_coder_csv(
    sample: list[dict],
    families: list[str],
    path: Path,
    *,
    detected_default: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "cell_id", "essay_id", "trait", "purpose", "family",
                "rationale_excerpt", "detected",
            ],
        )
        writer.writeheader()
        for cell_idx, cell in enumerate(sample, start=1):
            excerpt = cell["rationale_text"]
            if len(excerpt) > RATIONALE_EXCERPT_MAX:
                excerpt = excerpt[:RATIONALE_EXCERPT_MAX] + "…"
            for family in families:
                writer.writerow({
                    "cell_id": cell_idx,
                    "essay_id": cell["essay_id"],
                    "trait": cell["trait"],
                    "purpose": cell["purpose"],
                    "family": family,
                    "rationale_excerpt": excerpt,
                    "detected": detected_default,
                })


def write_machine_truth(
    sample: list[dict],
    families: list[str],
    path: Path,
    *,
    analyzer=None,
) -> None:
    """Write the deterministic detector result per (cell, family) — analyst-only.

    Long-format (same 160-row shape as a coder CSV) so ``keyword_blind_audit``
    can merge it against the human annotation on (essay_id, trait, family).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "cell_id", "essay_id", "trait", "purpose", "family",
                "machine_detected",
            ],
        )
        writer.writeheader()
        for cell_idx, cell in enumerate(sample, start=1):
            detected = set(detect_families(cell["rationale_text"], analyzer=analyzer).families)
            for family in families:
                writer.writerow({
                    "cell_id": cell_idx,
                    "essay_id": cell["essay_id"],
                    "trait": cell["trait"],
                    "purpose": cell["purpose"],
                    "family": family,
                    "machine_detected": 1 if family in detected else 0,
                })


def write_strata(sample: list[dict], path: Path) -> None:
    """Write failure/control labels — ANALYST ONLY (sharing breaks the blind)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Spot-Check Strata — ANALYST ONLY (do NOT share with coders)",
        "",
        "- **failure**: auto-detector found NO family (detector-miss candidate).",
        "- **control**: auto-detector positive (blind control).",
        "",
        "| cell_id | essay_id | trait | purpose | stratum |",
        "|---:|---:|---|---|---|",
    ]
    for cell_idx, cell in enumerate(sample, start=1):
        lines.append(
            f"| {cell_idx} | {cell['essay_id']} | `{cell['trait']}` | "
            f"{cell['purpose']} | {cell.get('stratum', '?')} |"
        )
    counts = Counter(c.get("stratum", "?") for c in sample)
    lines += ["", "Totals: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_prevalence_summary(
    sample: list[dict],
    families: list[str],
    out_path: Path,
) -> None:
    """Per-cell auto-detector result + analyzed-trait coverage + family prevalence."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_cell_detection: list[dict] = []
    family_positive: Counter = Counter()
    trait_counter: Counter = Counter()
    purpose_counter: Counter = Counter()
    analyzed_present = Counter()
    degenerate_cells = 0
    for cell_idx, cell in enumerate(sample, start=1):
        detection = detect_families(cell["rationale_text"])
        fams = list(detection.families)
        for f in fams:
            family_positive[f] += 1
        trait_counter[cell["trait"]] += 1
        purpose_counter[cell["purpose"]] += 1
        if cell["trait"] in ANALYZED_TRAITS:
            analyzed_present[cell["trait"]] += 1
        is_degenerate = len(fams) == 0
        if is_degenerate:
            degenerate_cells += 1
        per_cell_detection.append({
            "cell_id": cell_idx,
            "essay_id": cell["essay_id"],
            "trait": cell["trait"],
            "purpose": cell["purpose"],
            "auto_families": fams,
            "degenerate": is_degenerate,
        })

    lines = [
        "# Blind Audit Sample — Prevalence Summary",
        "",
        f"- Total cells: {len(sample)} (purpose split: "
        + ", ".join(f"{p}={n}" for p, n in sorted(purpose_counter.items())) + ")",
        f"- Families per cell: {len(families)} → "
        f"binary decisions per coder: {len(sample) * len(families)}",
        f"- Degenerate cells (auto-detector empty): {degenerate_cells} / {len(sample)}",
        "",
        "## Trait Composition",
        "",
        "| trait | n_cells | analyzed_trait? |",
        "|---|---:|---|",
    ]
    for trait, n in sorted(trait_counter.items()):
        flag = "✓ analyzed" if trait in ANALYZED_TRAITS else ""
        lines.append(f"| `{trait}` | {n} | {flag} |")
    lines += [
        "",
        f"Analyzed-trait coverage in sample: "
        f"{sum(analyzed_present.values())}/{len(sample)} cells. "
        f"Per-analyzed-trait: " + ", ".join(
            f"{t}={analyzed_present.get(t, 0)}" for t in ANALYZED_TRAITS
        ),
        "",
        "## Auto-Detector Family Prevalence (reference, not Coder input)",
        "",
        "| family | positive_cells | prevalence | diagnostic |",
        "|---|---:|---:|---|",
    ]
    n_total = max(len(sample), 1)
    for family in families:
        pos = family_positive.get(family, 0)
        prev = pos / n_total
        if pos == 0:
            diag = "DEGENERATE_ZERO (κ trivially noisy; exclude from family-level κ per v2.6 §4.1.2.1 (d) 4번)"
        elif prev < 0.20:
            diag = "LOW_PREVALENCE (interpret κ with caution)"
        else:
            diag = "INTERPRETABLE"
        lines.append(f"| `{family}` | {pos} | {prev:.2%} | {diag} |")
    lines += [
        "",
        "## Per-Cell Auto-Detector Reference",
        "",
        "| cell_id | essay_id | trait | purpose | auto_families | degenerate |",
        "|---:|---:|---|---|---|---|",
    ]
    for row in per_cell_detection:
        fams_str = ", ".join(row["auto_families"]) if row["auto_families"] else "(none)"
        deg = "**Y**" if row["degenerate"] else ""
        lines.append(
            f"| {row['cell_id']} | {row['essay_id']} | `{row['trait']}` | "
            f"{row['purpose']} | {fams_str} | {deg} |"
        )

    lines += [
        "",
        "## Diagnostic Reading Guide (P3-strict++)",
        "",
        "본 sample 은 v2.6 §4.1.2.1 (d) 1번 spec (random + stratified by purpose 10+10) "
        "그대로 추출. content_1 처럼 자동 detector 의 positive prevalence 가 0 인 "
        "family/trait 가 sample 에 나타나면, Cohen κ 계산 시 degenerate flag 처리 "
        "(v2.6 §4.1.2.1 (d) 4번 'family detection 이 한 명도 안 한 경우 제외').",
        "",
        "Blind audit κ 결과 분기 (Phase 4 §5):",
        "- κ 낮음 → keyword/instruction 재검토",
        "- κ 높음 + sufficient prevalence → detector/normalization 점검",
        "- κ 높음 + content_1 0 지속 → metric design limitation (§11 신규 항목 검토)",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke-c-dir", type=Path, default=SMOKE_C_DIR,
        help="Directory with Stage C smoke jsonl files (default: reports/stage4_llm/smoke/C)",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=OUT_DIR,
        help="Output directory for coder CSVs + prevalence summary",
    )
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    parser.add_argument(
        "--mode", choices=("spotcheck", "random"), default="spotcheck",
        help="spotcheck (§41, default): detector-miss failure + control; "
             "random (§40 legacy): stratified-by-purpose 10+10",
    )
    parser.add_argument(
        "--n-per-purpose", type=int, default=SAMPLES_PER_PURPOSE,
        help="(random mode) cells per purpose (default 10)",
    )
    parser.add_argument(
        "--n-failure", type=int, default=N_FAILURE_DEFAULT,
        help="(spotcheck mode) detector-empty failure cells (default 15)",
    )
    parser.add_argument(
        "--n-control", type=int, default=N_CONTROL_DEFAULT,
        help="(spotcheck mode) detector-positive blind control cells (default 5)",
    )
    args = parser.parse_args(argv)

    families = sorted(KEYWORD_SET.keys())

    stage_c_paths = sorted(
        p for p in args.smoke_c_dir.glob("*.jsonl")
        if not p.name.endswith(".usage.jsonl") and not p.name.endswith(".rerun.jsonl")
    )
    if not stage_c_paths:
        print(f"No Stage C jsonl files under {args.smoke_c_dir}", file=sys.stderr)
        return 2
    pool = _build_candidate_pool(stage_c_paths)
    if not pool:
        print("Empty candidate pool (no rationale texts)", file=sys.stderr)
        return 2

    if args.mode == "spotcheck":
        sample = select_spotcheck_sample(
            pool, n_failure=args.n_failure, n_control=args.n_control, seed=args.seed,
        )
    else:
        sample = select_sample(pool, n_per_purpose=args.n_per_purpose, seed=args.seed)
    # `detected` is left BLANK in both modes (§42.1): pre-filling 0 would let an
    # untouched submission read as all-zero and silently underestimate detector
    # miss. The strict parser in keyword_blind_audit rejects blanks (naming the
    # row), forcing the coder to consciously enter 0/1 for every cell.
    coder_default = ""

    # Blind protection (§36 Fix 2): coder-facing files and analyst-only files
    # live in physically separate subdirectories so machine_truth / prevalence
    # (which leak auto-detector results) are never bundled with the coder CSVs.
    coders_dir = args.out_dir / "coders"
    analyst_dir = args.out_dir / "analyst"
    coders_dir.mkdir(parents=True, exist_ok=True)
    analyst_dir.mkdir(parents=True, exist_ok=True)

    write_coder_csv(sample, families, coders_dir / "coder_a.csv", detected_default=coder_default)
    write_coder_csv(sample, families, coders_dir / "coder_b.csv", detected_default=coder_default)
    write_prevalence_summary(sample, families, analyst_dir / "prevalence_summary.md")

    print(f"Mode: {args.mode}")
    print(f"Sample size: {len(sample)} cells × {len(families)} families "
          f"= {len(sample) * len(families)} rows per coder")
    print("Outputs:")
    print(f"  [coders]  {coders_dir / 'coder_a.csv'}")
    print(f"  [coders]  {coders_dir / 'coder_b.csv'}")
    print(f"  [analyst] {analyst_dir / 'prevalence_summary.md'}  "
          f"(WARNING: coder 에게 배포 금지 - blind 보호)")

    if args.mode == "spotcheck":
        write_machine_truth(sample, families, analyst_dir / "machine_truth.csv")
        write_strata(sample, analyst_dir / "spotcheck_strata.md")
        strata = Counter(c.get("stratum", "?") for c in sample)
        print(f"  [analyst] {analyst_dir / 'machine_truth.csv'}  "
              f"(deterministic detector truth - blind 보호)")
        print(f"  [analyst] {analyst_dir / 'spotcheck_strata.md'}  "
              f"(failure/control labels - blind 보호)")
        print(f"Strata: " + ", ".join(f"{k}={v}" for k, v in sorted(strata.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
