"""Compute v2.6 §8.2 smoke 9-axis (a)-(e) API stability report.

Companion to ``scripts/llm_family_smoke_audit.py`` (which handles axes (f)-(h)).
Reads outputs from ``scripts.run_stage4 --track smoke`` and computes:

  (a) Schema error rate          — count of `_non_json` errors / total calls
  (b) Validator fail rate        — count of `_validator` errors / total calls
  (c) Null/NA rate per trait     — count of null scores per trait / non-NA total
  (d) Token usage variance       — input/output token mean ± vs cost estimator
  (e) Rerun consistency          — Stage B essay × trait exact-match rate

Outputs ``reports/stage4_llm/smoke_test/api_axes_report.md`` with pass/fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.paths import REPORTS_DIR

SMOKE_DIR = REPORTS_DIR / "stage4_llm" / "smoke"
DEFAULT_OUT = REPORTS_DIR / "stage4_llm" / "smoke_test" / "api_axes_report.md"
EXPECTED_SMOKE_CALLS = 90


# --- axis (a) (b) ---------------------------------------------------------
def _error_key(rec: dict) -> tuple[int, str, str | None] | None:
    try:
        essay_id = int(rec.get("essay_id"))
    except (TypeError, ValueError):
        return None
    stage = str(rec.get("stage") or "")
    if not stage:
        return None
    purpose = rec.get("purpose")
    return essay_id, stage, str(purpose) if purpose is not None else None


def _attempt_number(kind: str) -> int:
    if not kind.startswith("attempt"):
        return 0
    digits: list[str] = []
    for char in kind[len("attempt"):]:
        if not char.isdigit():
            break
        digits.append(char)
    return int("".join(digits)) if digits else 0


def _is_successful(
    key: tuple[int, str, str | None],
    successful_calls: set[tuple[int, str, str | None]],
) -> bool:
    if key in successful_calls:
        return True
    essay_id, stage, purpose = key
    if purpose is None:
        return any(k[0] == essay_id and k[1] == stage for k in successful_calls)
    return (essay_id, stage, None) in successful_calls


def schema_and_validator_error_rates(
    errors_jsonl: Path,
    total_calls: int,
    *,
    successful_calls: set[tuple[int, str, str | None]] | None = None,
    expected_calls: int | None = None,
) -> dict:
    """Count unresolved final call failures by kind.

    The raw error stream is per-attempt. Axis (a)/(b) should not penalize a
    non-JSON or validator attempt that was later rescued by retry, nor an old
    failed attempt for a call now present in the success JSONL.
    """
    error_groups: dict[tuple[int, str, str | None], list[str]] = {}
    successful_calls = successful_calls or set()
    if errors_jsonl.exists():
        for line in errors_jsonl.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = _error_key(rec)
            if key is None:
                continue
            kind = str(rec.get("kind", ""))
            error_groups.setdefault(key, []).append(kind)

    schema_errors = 0
    validator_errors = 0
    api_errors = 0
    for key, kinds in error_groups.items():
        if _is_successful(key, successful_calls):
            continue
        final_kind = max(kinds, key=_attempt_number)
        if "_non_json" in final_kind:
            schema_errors += 1
        elif "_validator" in final_kind:
            validator_errors += 1
        elif "_api_error" in final_kind:
            api_errors += 1

    axis_complete_pass = expected_calls is None or total_calls >= expected_calls
    return {
        "total_calls": total_calls,
        "expected_calls": expected_calls,
        "schema_errors": schema_errors,
        "validator_errors": validator_errors,
        "api_errors": api_errors,
        "axis_a_pass": schema_errors < 3,
        "axis_b_pass": validator_errors < 3,
        "axis_complete_pass": axis_complete_pass,
    }


# --- axis (c) ---------------------------------------------------------------
def null_rate_per_trait(stage_b_jsonl: Path) -> dict:
    """For Stage B output, count null scores per trait."""
    trait_total: Counter = Counter()
    trait_null: Counter = Counter()
    if not stage_b_jsonl.exists():
        return {"per_trait": {}, "axis_c_pass": True, "note": "no Stage B output"}
    for line in stage_b_jsonl.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        scores = rec.get("scores") or {}
        for trait, entry in scores.items():
            trait_total[trait] += 1
            score_val = entry.get("score") if isinstance(entry, dict) else entry
            if score_val is None:
                trait_null[trait] += 1
    per_trait = {
        t: {"n": trait_total[t], "null": trait_null[t],
            "null_rate": (trait_null[t] / trait_total[t]) if trait_total[t] else 0.0}
        for t in sorted(trait_total)
    }
    axis_pass = all(v["null_rate"] < 0.20 for v in per_trait.values())
    return {"per_trait": per_trait, "axis_c_pass": axis_pass}


# --- axis (d) ---------------------------------------------------------------
def token_usage_variance(usage_jsonls: list[Path], estimator_input: int | None = None,
                         estimator_output: int | None = None) -> dict:
    """Mean input/output tokens vs estimator. Pass if within ±30%."""
    input_tokens: list[int] = []
    output_tokens: list[int] = []
    for p in usage_jsonls:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            v_in = rec.get("input_tokens")
            v_out = rec.get("output_tokens")
            if isinstance(v_in, int):
                input_tokens.append(v_in)
            if isinstance(v_out, int):
                output_tokens.append(v_out)
    result = {
        "n_calls": len(input_tokens),
        "input_tokens_mean": (sum(input_tokens) / len(input_tokens)) if input_tokens else None,
        "output_tokens_mean": (sum(output_tokens) / len(output_tokens)) if output_tokens else None,
    }
    if estimator_input is not None and result["input_tokens_mean"] is not None:
        dev = abs(result["input_tokens_mean"] - estimator_input) / max(estimator_input, 1)
        result["input_variance"] = dev
        result["axis_d_input_pass"] = dev <= 0.30
    if estimator_output is not None and result["output_tokens_mean"] is not None:
        dev = abs(result["output_tokens_mean"] - estimator_output) / max(estimator_output, 1)
        result["output_variance"] = dev
        result["axis_d_output_pass"] = dev <= 0.30
    pass_keys = [k for k in result if k.startswith("axis_d_")]
    result["axis_d_pass"] = (bool(pass_keys) and all(result[k] for k in pass_keys))
    return result


# --- axis (e) ---------------------------------------------------------------
def rerun_consistency(stage_b_jsonl: Path, stage_b_rerun_jsonl: Path) -> dict:
    """Trait-level exact match between Stage B original and rerun outputs."""
    def _load_scores_by_essay(p: Path) -> dict:
        out: dict[int, dict] = {}
        if not p.exists():
            return out
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = int(rec.get("essay_id", -1))
            if eid < 0:
                continue
            scores = rec.get("scores") or {}
            out[eid] = {
                t: (entry.get("score") if isinstance(entry, dict) else entry)
                for t, entry in scores.items()
            }
        return out

    base = _load_scores_by_essay(stage_b_jsonl)
    rerun = _load_scores_by_essay(stage_b_rerun_jsonl)
    common = set(base) & set(rerun)
    if not common:
        return {"trait_match_rate": None, "axis_e_pass": True,
                "note": "no overlap between base and rerun"}
    total = 0
    matched = 0
    for eid in common:
        for trait in base[eid]:
            if trait in rerun[eid]:
                total += 1
                if base[eid][trait] == rerun[eid][trait]:
                    matched += 1
    rate = matched / total if total else 0.0
    return {
        "n_essays_compared": len(common),
        "n_trait_decisions": total,
        "n_matches": matched,
        "trait_match_rate": rate,
        "axis_e_pass": rate >= 0.95,
    }


# --- driver ----------------------------------------------------------------
def _load_successful_calls(jsonls: list[Path]) -> set[tuple[int, str, str | None]]:
    successful: set[tuple[int, str, str | None]] = set()
    for path in jsonls:
        stage = path.parent.name
        purpose = path.stem
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            try:
                rec = json.loads(line)
                essay_id = int(rec.get("essay_id"))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            successful.add((essay_id, stage, purpose))
    return successful


def compute_axes(smoke_dir: Path = SMOKE_DIR, expected_calls: int | None = None) -> dict:
    """Aggregate (a)-(e) across all (stage × purpose) under smoke/."""
    stages = ("A", "B", "C")
    purposes = ("설명", "설득")

    total_calls = 0
    main_jsonls: list[Path] = []
    usage_jsonls: list[Path] = []
    for stage in stages:
        for purpose in purposes:
            p = smoke_dir / stage / f"{purpose}.jsonl"
            if p.exists():
                main_jsonls.append(p)
                usage_jsonls.append(p.with_suffix(".usage.jsonl"))
                total_calls += sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line)

    errors_jsonl = smoke_dir / "errors" / "errors.jsonl"
    successful_calls = _load_successful_calls(main_jsonls)
    ab = schema_and_validator_error_rates(
        errors_jsonl,
        total_calls,
        successful_calls=successful_calls,
        expected_calls=expected_calls,
    )

    # (c) — Stage B 양 purpose 합산
    null_per_trait: dict = {}
    for purpose in purposes:
        p = smoke_dir / "B" / f"{purpose}.jsonl"
        res = null_rate_per_trait(p)
        null_per_trait[purpose] = res

    d = token_usage_variance(usage_jsonls)

    # (e) — Stage B 설명 rerun (smoke 표준 절차: 10 essay 한 purpose 만 rerun)
    e_results: dict = {}
    for purpose in purposes:
        base = smoke_dir / "B" / f"{purpose}.jsonl"
        rerun = smoke_dir / "B" / f"{purpose}.rerun.jsonl"
        if rerun.exists():
            e_results[purpose] = rerun_consistency(base, rerun)

    return {"a_b": ab, "c": null_per_trait, "d": d, "e": e_results}


def write_report(axes: dict, out_path: Path = DEFAULT_OUT) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Smoke 9-axis Report (a)-(e)", ""]

    ab = axes["a_b"]
    lines += [
        "## (a) Schema error rate / (b) Validator fail rate",
        "",
        f"- Total calls: {ab['total_calls']}",
    ]
    if ab.get("expected_calls") is not None:
        lines.append(
            f"- Expected calls: {ab['expected_calls']} — completion "
            f"**{'PASS' if ab.get('axis_complete_pass') else 'FAIL'}**"
        )
    lines += [
        f"- Schema errors: {ab['schema_errors']} → axis (a) **{'PASS' if ab['axis_a_pass'] else 'FAIL'}** (< 3 required)",
        f"- Validator errors: {ab['validator_errors']} → axis (b) **{'PASS' if ab['axis_b_pass'] else 'FAIL'}** (< 3 required)",
        f"- API errors: {ab.get('api_errors', 0)}",
        "",
    ]

    lines += ["## (c) Null rate per trait (Stage B)", ""]
    for purpose, res in axes["c"].items():
        lines.append(f"### {purpose}")
        for trait, v in res.get("per_trait", {}).items():
            lines.append(f"- `{trait}`: {v['null']}/{v['n']} ({v['null_rate']:.1%})")
        lines.append(f"- axis (c) **{'PASS' if res.get('axis_c_pass') else 'FAIL'}** (< 20% per trait)")
        lines.append("")

    d = axes["d"]
    lines += [
        "## (d) Token usage variance",
        "",
        f"- Calls with usage: {d.get('n_calls', 0)}",
        f"- Mean input tokens: {d.get('input_tokens_mean')}",
        f"- Mean output tokens: {d.get('output_tokens_mean')}",
    ]
    if "input_variance" in d:
        lines.append(f"- Input variance vs estimator: {d['input_variance']:.1%}")
    if "output_variance" in d:
        lines.append(f"- Output variance vs estimator: {d['output_variance']:.1%}")
    lines.append(f"- axis (d) **{'PASS' if d.get('axis_d_pass') else 'NEEDS estimator targets to compute'}**")
    lines.append("")

    lines += ["## (e) Rerun consistency (Stage B)", ""]
    if not axes["e"]:
        lines.append("- No rerun outputs found; axis (e) **PENDING**")
    for purpose, res in axes["e"].items():
        lines.append(f"### {purpose}")
        if res.get("trait_match_rate") is None:
            lines.append(f"- {res.get('note', 'no data')}")
        else:
            lines.append(f"- Essays compared: {res['n_essays_compared']}, "
                         f"trait decisions: {res['n_trait_decisions']}, "
                         f"matches: {res['n_matches']}")
            lines.append(f"- Trait-level exact match rate: {res['trait_match_rate']:.1%}")
        lines.append(f"- axis (e) **{'PASS' if res.get('axis_e_pass') else 'FAIL'}** (≥ 95% required)")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-dir", type=Path, default=SMOKE_DIR,
                        help="Smoke output directory (default: reports/stage4_llm/smoke)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-calls", type=int, default=EXPECTED_SMOKE_CALLS,
                        help="Expected successful smoke calls for completion check")
    args = parser.parse_args(argv)

    axes = compute_axes(args.smoke_dir, expected_calls=args.expected_calls)
    write_report(axes, args.out)
    print(f"Wrote {args.out}")
    # Exit code: 0 if (a)+(b)+(c) all pass (the core API axes). (d) needs
    # estimator targets passed in; (e) needs rerun outputs.
    core_pass = (axes["a_b"]["axis_complete_pass"]
                 and axes["a_b"]["axis_a_pass"]
                 and axes["a_b"]["axis_b_pass"]
                 and all(v.get("axis_c_pass", True) for v in axes["c"].values()))
    return 0 if core_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
