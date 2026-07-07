"""
Assemble Stage 4 LLM prompts from a purpose-neutral wrapper and the
dataset's verbatim rubric text (plan v2.3 §4.3.1 + appendix A).

Design principle — minimize prompt-engineering confound:
    1. Rubric content (9 trait × 5 grade descriptors per purpose) is read
       directly from the NIA 14-026 ``rubric.analytic.<trait>.evaluation_{1..5}``
       JSON fields via ``src.data.rubric.parse_rubric``. No paraphrase.
    2. Wrapper templates under ``prompts/_wrapper/{A,B,C}.md`` are
       purpose-neutral (same wrapper for 설명 and 설득). Any observed
       purpose difference in LLM output is therefore attributable to
       rubric content or essay data, never to wrapper text.
    3. Assembled final prompts are written to ``prompts/{purpose}/{stage}.md``
       and their SHA-256 is recorded. Stage 4 calls load the *assembled*
       file, never the wrapper template.

Usage::

    python -m src.llm.prompt_assembly                 # assemble all 6
    python -m src.llm.prompt_assembly --purpose 설명 --stage B
    python -m src.llm.prompt_assembly --check         # verify SHAs match

Sensitivity variants under ``prompts/_sensitivity/`` (optional) share
the same placeholder contract and can be assembled with ``--wrapper-dir``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

from configs.paths import PROJECT_ROOT, PURPOSES_IN_SCOPE, TRAITS
from src.data.rubric import RubricBlock, parse_rubric

log = logging.getLogger(__name__)

WRAPPER_DIR: Path = PROJECT_ROOT / "prompts" / "_wrapper"
OUTPUT_DIR: Path = PROJECT_ROOT / "prompts"
DATA_ROOT_ENV: str = "AES_DATA_ROOT"

# Ordered list of analytic traits to render (holistic is excluded per
# plan v2.3 §4.3.1 "analytic-only" scope).
ANALYTIC_TRAIT_ORDER: tuple[str, ...] = tuple(
    t for t in TRAITS if t != "holistic"
)

# Pre-registered surgical patches for documented corpus-level data
# corruption. Each entry is (exact_source, replacement, reason). Applied
# only when ``source`` appears verbatim in a grade descriptor. The list
# is committed with the preregistered prompts; adding new entries after
# commit invalidates Stage 4 SHAs.
#
# The `+N82:N121` string is an Excel cell-reference artifact serialized
# into every 설득/task_1/evaluation_5 field of the NIA 14-026 corpus
# — verified by `grep '+N82' dataset/**/*.json`. Leaving it in would
# present garbled text to the LLM for no semantic reason.
RUBRIC_PATCHES: tuple[tuple[str, str, str], ...] = (
    (
        "탁월하게 수+N82:N121행한다",
        "탁월하게 수행한다",
        "NIA 14-026 corpus: Excel cell-reference artifact in 설득 task_1 evaluation_5",
    ),
)


def _apply_patches(text: str) -> str:
    for src, dst, _reason in RUBRIC_PATCHES:
        text = text.replace(src, dst)
    return text


def _sample_essay_for_purpose(purpose: str) -> Path:
    """Return one NIA 14-026 JSON path known to carry the target purpose's rubric.

    Rubric content is corpus-wide identical per purpose (verified by
    ``scripts/dump_rubrics.py`` — one variant per purpose). Any single
    matching essay suffices.
    """
    import os
    data_root = Path(os.environ[DATA_ROOT_ENV])
    for p in data_root.rglob("*.json"):
        raw = json.loads(p.read_text(encoding="utf-8"))
        if raw.get("essay_question", {}).get("purpose") == purpose:
            return p
    raise FileNotFoundError(
        f"No essay with purpose={purpose!r} under {data_root}. "
        f"Set {DATA_ROOT_ENV} to the NIA 14-026 corpus root."
    )


def load_rubric(purpose: str) -> RubricBlock:
    """Load the authoritative rubric for ``purpose`` from the dataset."""
    sample = _sample_essay_for_purpose(purpose)
    raw = json.loads(sample.read_text(encoding="utf-8"))
    rb = parse_rubric(raw.get("rubric", {}))
    if rb.purpose != purpose:
        raise RuntimeError(
            f"Sample rubric purpose mismatch: expected {purpose}, got {rb.purpose}"
        )
    return rb


def render_rubric_markdown(rb: RubricBlock) -> str:
    """Render the 8 analytic traits' evaluation descriptors verbatim.

    Output is a single markdown fragment intended to be injected into
    the wrapper at ``{{RUBRIC_INSERT}}``. Each trait block contains the
    5 grade descriptors verbatim from ``ar.evaluations``.
    """
    lines: list[str] = [
        f"**Purpose**: `{rb.purpose}` — 성취기준: {rb.achievement}",
        "",
    ]
    for trait in ANALYTIC_TRAIT_ORDER:
        ar = rb.analytic.get(trait)
        if ar is None:
            raise KeyError(f"Rubric for purpose={rb.purpose} missing trait={trait}")
        lines.append(f"### `{trait}` — {ar.name}")
        lines.append(f"_rubric_key_: `{ar.rubric_key_raw}`")
        lines.append("")
        lines.append("| 점수 | 등급 기준 (dataset verbatim) |")
        lines.append("|---|---|")
        for score in (5, 4, 3, 2, 1):
            desc = ar.evaluations.get(score, "").strip()
            if not desc:
                raise ValueError(
                    f"Trait {trait} missing evaluation_{score} for {rb.purpose}"
                )
            # Apply pre-registered surgical patches for known corpus
            # corruption, then normalize whitespace so table renders cleanly.
            desc = _apply_patches(desc)
            desc_flat = " ".join(desc.split())
            lines.append(f"| **{score}** | {desc_flat} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def assemble(
    purpose: str,
    stage: str,
    *,
    wrapper_dir: Path = WRAPPER_DIR,
) -> tuple[str, str]:
    """Assemble a (purpose, stage) prompt. Returns (assembled_text, sha256_hex)."""
    assert stage in ("A", "B", "C"), stage
    assert purpose in PURPOSES_IN_SCOPE, (purpose, PURPOSES_IN_SCOPE)

    wrapper_path = wrapper_dir / f"{stage}.md"
    if not wrapper_path.exists():
        raise FileNotFoundError(wrapper_path)
    wrapper = wrapper_path.read_text(encoding="utf-8")

    rubric_block = load_rubric(purpose)
    rubric_md = render_rubric_markdown(rubric_block)

    # Build-time markers (substituted now, SHA-locked):
    #   {{PURPOSE}}, {{RUBRIC_INSERT}}
    # Runtime markers (left intact; substituted per-essay by render_runtime):
    #   {{GRADE}}, {{PROMPT}}, {{TOPIC}}, {{LEVEL}}, {{LEN_SYLLABLE}},
    #   {{LEN_WORD}}, {{TYPE}}, {{ESSAY_ID}}, {{ESSAY_TEXT}},
    #   {{STAGE_A_OUTPUT_JSON}}, {{STAGE_B_OUTPUT_JSON}}
    for marker in ("{{PURPOSE}}", "{{RUBRIC_INSERT}}"):
        if marker not in wrapper:
            raise RuntimeError(
                f"Wrapper {wrapper_path} missing required marker {marker}"
            )
    assembled = (
        wrapper
        .replace("{{PURPOSE}}", purpose)
        .replace("{{RUBRIC_INSERT}}", rubric_md)
    )
    sha = hashlib.sha256(assembled.encode("utf-8")).hexdigest()
    return assembled, sha


def render_runtime(
    assembled_prompt: str,
    essay_question: dict,
    essay_id: int,
    essay_text: str,
    stage_a_json: str | None = None,
    stage_b_json: str | None = None,
) -> str:
    """Substitute per-essay runtime markers into an assembled prompt.

    Called by the researcher's Stage 4 driver right before an API call.
    Keeps SHA integrity: the assembled-prompt SHA registered in
    ``snapshot_registry.md`` corresponds to the ``essay_question`` fields'
    *placeholder template*, not any specific essay's values. The final
    string the LLM sees additionally carries the per-essay fields below.
    """
    out = assembled_prompt
    q_fields = {
        "{{GRADE}}":      str(essay_question.get("grade", "")),
        "{{PROMPT}}":     str(essay_question.get("prompt", "")),
        "{{TOPIC}}":      str(essay_question.get("topic", "")),
        "{{LEVEL}}":      str(essay_question.get("level", "")),
        "{{TYPE}}":       str(essay_question.get("type", "")),
        "{{ESSAY_ID}}":   str(essay_id),
        "{{ESSAY_TEXT}}": essay_text,
    }
    for k, v in q_fields.items():
        out = out.replace(k, v)
    if stage_a_json is not None:
        out = out.replace("{{STAGE_A_OUTPUT_JSON}}", stage_a_json)
    if stage_b_json is not None:
        out = out.replace("{{STAGE_B_OUTPUT_JSON}}", stage_b_json)
    return out


def write_assembled(purpose: str, stage: str, *, wrapper_dir: Path = WRAPPER_DIR) -> Path:
    text, sha = assemble(purpose, stage, wrapper_dir=wrapper_dir)
    out_dir = OUTPUT_DIR / purpose
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{stage}.md"
    # Prepend provenance header as HTML comment so it does not reach the LLM
    # when the researcher strips comments before the API call.
    header = (
        f"<!-- ASSEMBLED by src/llm/prompt_assembly.py — DO NOT HAND-EDIT.\n"
        f"     wrapper: prompts/_wrapper/{stage}.md\n"
        f"     rubric:  NIA 14-026 corpus, purpose={purpose} (dataset verbatim)\n"
        f"     sha256:  {sha}\n"
        f"-->\n\n"
    )
    out.write_text(header + text, encoding="utf-8")
    log.info("wrote %s  sha256=%s", out, sha[:16])
    return out


def check_all() -> int:
    """Re-assemble every (purpose × stage) and diff against disk. Returns drift count."""
    drift = 0
    for purpose in PURPOSES_IN_SCOPE:
        for stage in ("A", "B", "C"):
            text, sha = assemble(purpose, stage)
            on_disk = (OUTPUT_DIR / purpose / f"{stage}.md").read_text(encoding="utf-8")
            # Extract the SHA from the header for comparison.
            header_sha = ""
            for line in on_disk.splitlines()[:6]:
                if "sha256:" in line:
                    header_sha = line.split("sha256:")[1].strip().rstrip("-->").strip()
                    break
            if header_sha != sha:
                drift += 1
                log.warning("DRIFT %s/%s: disk=%s  fresh=%s",
                            purpose, stage, header_sha[:16], sha[:16])
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", choices=list(PURPOSES_IN_SCOPE) + ["all"], default="all")
    parser.add_argument("--stage", choices=("A", "B", "C", "all"), default="all")
    parser.add_argument("--check", action="store_true",
                        help="verify disk prompts match freshly assembled versions")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.check:
        drift = check_all()
        if drift:
            log.error("%d prompt(s) drifted — re-run without --check to rewrite", drift)
            return 1
        log.info("all prompts match their assembled form")
        return 0

    purposes = list(PURPOSES_IN_SCOPE) if args.purpose == "all" else [args.purpose]
    stages = ("A", "B", "C") if args.stage == "all" else (args.stage,)
    for p in purposes:
        for s in stages:
            write_assembled(p, s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
