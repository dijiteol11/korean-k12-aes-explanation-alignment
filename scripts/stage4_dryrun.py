"""
Stage 4 dry-run — end-to-end prompt assembly validation (no LLM calls).

For ``n_samples`` essays per purpose:
    1. Load essay + essay_question from corpus
    2. Render assembled prompts via render_runtime() for A/B/C
    3. Validate final prompt has no leftover placeholders
    4. Estimate token count for each stage
    5. Run a mock Stage A → B → C cycle with synthetic valid JSON
       responses to verify validator behavior end-to-end
    6. Save samples to ``reports/stage4_llm/dryrun/`` for researcher
       inspection before real SDK wiring

Invoke: ``python -m scripts.stage4_dryrun --n 5``
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

from configs.paths import PROJECT_ROOT, PURPOSES_IN_SCOPE, REPORTS_DIR
from src.llm.prompt_assembly import render_runtime
from src.llm.response_validator import (
    ANALYTIC_TRAITS,
    EVIDENCE_TAGS,
    validate_stage_a,
    validate_stage_b,
    validate_stage_c,
)

log = logging.getLogger(__name__)

OUT_DIR: Path = REPORTS_DIR / "stage4_llm" / "dryrun"
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


def _load_sample_essays(purpose: str, n: int) -> list[dict]:
    root = Path(os.environ.get("AES_DATA_ROOT", PROJECT_ROOT / "dataset"))
    out: list[dict] = []
    for p in root.rglob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("essay_question", {}).get("purpose") != purpose:
            continue
        out.append(raw)
        if len(out) >= n:
            break
    return out


def _synth_stage_a(essay: dict) -> dict:
    """Generate a synthetic Stage A output for dry-run validator check."""
    text = essay["essay_answer"]["text"]
    # Pick a short span from early in the essay.
    span = [0, min(30, len(text))]
    evidence = {
        trait: [{
            "span": span,
            "text": text[span[0]:span[1]],
            "tag": "rubric_cue",
        }]
        for trait in ANALYTIC_TRAITS
    }
    return {
        "essay_id": essay["essay_answer"]["id"],
        "purpose": essay["essay_question"]["purpose"],
        "evidence": evidence,
    }


def _synth_stage_b(essay: dict) -> dict:
    scores = {}
    for i, trait in enumerate(ANALYTIC_TRAITS):
        if i == 0:  # first trait: NA example
            scores[trait] = {
                "score": None, "confidence": 0.2,
                "span_refs": [], "reason": "insufficient_evidence",
            }
        else:
            scores[trait] = {
                "score": 3, "confidence": 0.8,
                "span_refs": [0], "reason": None,
            }
    return {
        "essay_id": essay["essay_answer"]["id"],
        "purpose": essay["essay_question"]["purpose"],
        "scores": scores,
    }


def _synth_stage_c(essay: dict, b_out: dict) -> dict:
    rationale = {}
    for trait in ANALYTIC_TRAITS:
        sc = b_out["scores"][trait]["score"]
        if sc is None:
            rationale[trait] = {
                "text": f"{trait}에 대해 Stage A 증거가 빈약하여 판정 불가함.",
                "cited_spans": [],
            }
        else:
            rationale[trait] = {
                "text": f"{trait}의 rubric {sc}점 기준에 부합하는 증거 관찰됨.",
                "cited_spans": [0],
            }
    return {
        "essay_id": essay["essay_answer"]["id"],
        "purpose": essay["essay_question"]["purpose"],
        "rationale": rationale,
    }


def dryrun_one(essay: dict, purpose: str, out_dir: Path) -> dict:
    """Run one essay through A→B→C mock pipeline, return per-stage diagnostics."""
    eid = essay["essay_answer"]["id"]
    text = essay["essay_answer"]["text"]
    question = essay["essay_question"]

    diags = {"essay_id": eid, "purpose": purpose, "stages": {}}

    for stage in ("A", "B", "C"):
        assembled_path = PROJECT_ROOT / "prompts" / purpose / f"{stage}.md"
        assembled = assembled_path.read_text(encoding="utf-8")

        # Stage-specific prior outputs
        prior_a = None
        prior_b = None
        if stage != "A":
            prior_a = json.dumps(_synth_stage_a(essay), ensure_ascii=False)
        if stage == "C":
            prior_b = json.dumps(_synth_stage_b(essay), ensure_ascii=False)

        final = render_runtime(
            assembled_prompt=assembled,
            essay_question=question,
            essay_id=eid,
            essay_text=text,
            stage_a_json=prior_a,
            stage_b_json=prior_b,
        )

        leftover = PLACEHOLDER_RE.findall(final)
        n_chars = len(final)
        est_tokens = max(1, int(n_chars / 2.5))

        diags["stages"][stage] = {
            "leftover_placeholders": leftover,
            "prompt_chars": n_chars,
            "est_tokens": est_tokens,
        }

        # Save sample for the first essay of each purpose for researcher inspection.
        sample_path = out_dir / f"sample__{purpose}__stage{stage}__essay{eid}.txt"
        sample_path.write_text(final, encoding="utf-8")

    # Validator roundtrip with synthetic outputs
    a = _synth_stage_a(essay)
    b = _synth_stage_b(essay)
    c = _synth_stage_c(essay, b)
    try:
        validate_stage_a(a, essay_text=text)
        diags["validator_A"] = "pass"
    except Exception as e:
        diags["validator_A"] = f"FAIL: {e}"
    try:
        validate_stage_b(b, stage_a_evidence=a["evidence"])
        diags["validator_B"] = "pass"
    except Exception as e:
        diags["validator_B"] = f"FAIL: {e}"
    try:
        validate_stage_c(c, stage_b_scores=b["scores"])
        diags["validator_C"] = "pass"
    except Exception as e:
        diags["validator_C"] = f"FAIL: {e}"

    return diags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3,
                        help="essays per purpose (default 3)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    for purpose in PURPOSES_IN_SCOPE:
        essays = _load_sample_essays(purpose, args.n)
        log.info("Loaded %d sample essays for %s", len(essays), purpose)
        for essay in essays:
            diags = dryrun_one(essay, purpose, OUT_DIR)
            summary.append(diags)

    # Report
    total = len(summary)
    any_leftover = sum(
        1 for d in summary
        if any(d["stages"][s]["leftover_placeholders"] for s in ("A", "B", "C"))
    )
    validator_fails = sum(
        1 for d in summary
        if any(str(d.get(f"validator_{s}", "")).startswith("FAIL") for s in ("A", "B", "C"))
    )
    avg_tokens = {
        s: sum(d["stages"][s]["est_tokens"] for d in summary) / total
        for s in ("A", "B", "C")
    }

    print("=" * 70)
    print(f"Stage 4 dry-run — {total} essays, {len(PURPOSES_IN_SCOPE)} purposes")
    print("=" * 70)
    print(f"  essays with leftover placeholders: {any_leftover}/{total}")
    print(f"  validator failures:                {validator_fails}/{total}")
    print("  avg est_tokens per stage:")
    for s, v in avg_tokens.items():
        print(f"    stage {s}: {v:.0f} tokens")
    print(f"\n  sample assembled prompts written to: {OUT_DIR}")
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  per-essay diagnostics JSON:          {summary_path}")

    if any_leftover or validator_fails:
        print("\n  ⚠  Issues detected — inspect sample outputs before real run.")
        return 1
    print("\n  ✓  Dry-run clean: prompts render, validators pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
