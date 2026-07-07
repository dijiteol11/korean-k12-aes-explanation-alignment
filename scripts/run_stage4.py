"""
Stage 4 driver — main / sensitivity / alpha_pilot track entry point.

This file is a **skeleton** for the researcher to wire the Anthropic SDK
call into. Claude Code authored this but MUST NOT execute it (per
CLAUDE.md "Out of scope"). The researcher fills ``_invoke_anthropic()``
with actual SDK logic, sets ``MODEL_ID_MAIN`` / ``MODEL_ID_SENSITIVITY``
in configs/stage4.py, and runs:

    python -m scripts.run_stage4 --track main       --stage A --purpose 설명
    python -m scripts.run_stage4 --track main       --stage B --purpose 설명
    python -m scripts.run_stage4 --track main       --stage C --purpose 설명
    python -m scripts.run_stage4 --track sensitivity --stage A --purpose 설명 --sample reports/stage4_llm/sensitivity_sample.csv
    python -m scripts.run_stage4 --track alpha_pilot --purpose 설명

Design principles:
    * Idempotent: re-running skips essays whose output already exists
    * Crash-safe: writes per-essay JSONL append-only; checkpoint on
      every success
    * Validator-gated: every response is run through
      response_validator.validate_stage_<x>() before being written
    * Snapshot-stamped: every run calls snapshot.append_to_registry()
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import sys
from pathlib import Path

# Load .env (ANTHROPIC_API_KEY etc.) early so Anthropic SDK can pick it up.
# Silent fallback if python-dotenv 미설치 — 사용자가 직접 env var export 가능.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from configs.paths import PROJECT_ROOT, PURPOSES_IN_SCOPE, REPORTS_DIR
from configs.stage4 import (
    ALPHA_PILOT_N_ESSAYS,
    ALPHA_PILOT_N_REPEATS,
    MODEL_ID_MAIN,
    MODEL_ID_SENSITIVITY,
    STAGE4_MAX_TOKENS,
    TEMPERATURE,
)
from src.llm.prompt_assembly import render_runtime
from src.llm.response_validator import (
    validate_stage_a, validate_stage_b, validate_stage_c,
)
from src.llm.snapshot import append_to_registry, make_stamp

log = logging.getLogger(__name__)

STAGE4_OUT: Path = REPORTS_DIR / "stage4_llm"
STAGE_A_EVIDENCE_TEXT_MAX: int = 120


# --- Placeholder for Anthropic SDK call (researcher fills in) --------------
def _invoke_anthropic(
    prompt: str,
    model_id: str,
    temperature: float = TEMPERATURE,
) -> tuple[str, str, dict]:
    """Call the Anthropic API.

    Returns (response_json_str, api_revision_header, usage_dict).

    Requires ``ANTHROPIC_API_KEY`` in the environment. The return metadata is
    best-effort because SDK response header access varies across versions.

    ``usage_dict`` captures token usage (input/output + cache creation/read)
    for axis (d) "token usage variance" verification. Keys are best-effort:
    missing fields are present with ``None`` value so downstream aggregation
    can detect absence vs zero.
    """
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required for Stage 4 execution") from exc

    client = Anthropic()
    # Assistant prefill with "{" forces the model to continue from an open JSON
    # object — prevents the common Sonnet behavior of wrapping output in
    # ```json ... ``` markdown code fences (axis (a) schema-error 회피). The
    # prefilled "{" is NOT echoed in response.content; we prepend it manually
    # to reconstruct the full JSON.
    response = client.messages.create(
        model=model_id,
        max_tokens=STAGE4_MAX_TOKENS,
        temperature=temperature,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "{"},
        ],
    )
    content = getattr(response, "content", None) or []
    if not content:
        raise RuntimeError("Anthropic response has no content blocks")
    raw = getattr(content[0], "text", None)
    if raw is None and isinstance(content[0], dict):
        raw = content[0].get("text")
    if not raw:
        raise RuntimeError("Anthropic response first content block has no text")
    text = "{" + raw   # prepend the prefilled "{"

    headers = getattr(response, "_headers", {}) or getattr(response, "headers", {}) or {}
    metadata = getattr(response, "response_metadata", {}) or {}
    api_revision = (
        headers.get("anthropic-version")
        or headers.get("anthropic-revision")
        or headers.get("request-id")
        or headers.get("anthropic-request-id")
        or metadata.get("api-revision")
        or metadata.get("request_id")
        or getattr(response, "_request_id", "")
        or ""
    )

    # Token usage capture (axis (d)). SDK exposes a `usage` attribute.
    usage = getattr(response, "usage", None)
    usage_dict: dict = {
        "input_tokens": None,
        "output_tokens": None,
        "cache_creation_input_tokens": None,
        "cache_read_input_tokens": None,
    }
    if usage is not None:
        for k in usage_dict:
            v = getattr(usage, k, None)
            if v is None and isinstance(usage, dict):
                v = usage.get(k)
            usage_dict[k] = v

    return str(text), str(api_revision), usage_dict


# --- Essay iteration -------------------------------------------------------
def _strip_markdown_fence(text: str) -> str:
    """Defensive strip of ```json...``` (or ```...```) wrapper around JSON.

    Sonnet often wraps JSON in markdown code fences even when prompted for raw
    JSON. F2 prefill (``{``) is the primary prevention; this helper is a
    secondary safety net that catches the residual case where the prefill
    still produces a fenced response (rare but possible if the model echoes
    the prefill character before adding markdown).
    """
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.split("\n")
    # Drop opening fence (may include language tag like ```json)
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    # Drop closing fence
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _escape_unescaped_text_value_quotes(text: str) -> str:
    """Escape raw double quotes inside Stage A evidence `text` JSON values.

    Korean essays can contain direct quotations. Sonnet occasionally copies
    those quotation marks into the JSON string without escaping them, while the
    surrounding Stage A object is otherwise well-formed.
    """
    matches = list(re.finditer(r'"text"\s*:\s*"', text))
    if not matches:
        return text

    chunks: list[str] = []
    cursor = 0
    for match in matches:
        chunks.append(text[cursor:match.end()])
        cursor = match.end()
        while cursor < len(text):
            char = text[cursor]
            if char == "\\":
                chunks.append(text[cursor:cursor + 2])
                cursor += 2
                continue
            if char == '"':
                tail = text[cursor:]
                if re.match(r'"\s*,\s*"tag"\s*:', tail):
                    chunks.append(char)
                    cursor += 1
                    break
                chunks.append('\\"')
                cursor += 1
                continue
            chunks.append(char)
            cursor += 1
    chunks.append(text[cursor:])
    return "".join(chunks)


def _load_corpus_essays(purpose: str) -> list[dict]:
    root = Path(os.environ.get("AES_DATA_ROOT", PROJECT_ROOT / "dataset"))
    out: list[dict] = []
    for p in root.rglob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("essay_question", {}).get("purpose") == purpose:
            out.append(raw)
    out.sort(key=lambda r: r["essay_answer"]["id"])
    return out


def _load_sensitivity_sample_ids(sample_csv: Path) -> set[int]:
    import pandas as pd
    df = pd.read_csv(sample_csv)
    return set(df["essay_id"].astype(int).tolist())


def _load_done_ids(out_path: Path) -> set[tuple[int, int]]:
    """Resume support keyed by ``(essay_id, repeat_index)``."""
    if not out_path.exists():
        return set()
    done: set[tuple[int, int]] = set()
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            rec = json.loads(line)
            done.add((int(rec.get("essay_id", -1)), int(rec.get("_repeat_index", 0))))
        except Exception:
            continue
    return done


_PRIOR_STAGE_CACHE: dict[tuple[str, str, str], dict[int, dict]] = {}


def _load_prior_stage(purpose: str, essay_id: int, track: str, stage: str) -> dict | None:
    """Read Stage A (or B) output for the given essay, if present.

    Caches the entire jsonl as ``essay_id -> record`` on first access per
    ``(track, stage, purpose)`` so the dependency lookup is O(1) per call.
    Without this, building/processing a 4,860-essay Stage B/C run becomes
    O(n^2) on file size. The cache is per-process and stale-safe within a
    single ``run_track`` invocation (current-stage outputs are appended, not
    re-read; previous stages are read-only).
    """
    if stage not in ("A", "B"):
        return None
    cache_key = (track, stage, purpose)
    cache = _PRIOR_STAGE_CACHE.get(cache_key)
    if cache is None:
        cache = {}
        path = STAGE4_OUT / track / stage / f"{purpose}.jsonl"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                eid = rec.get("essay_id")
                if eid is not None:
                    cache[int(eid)] = rec
        _PRIOR_STAGE_CACHE[cache_key] = cache
    return cache.get(int(essay_id))


def _normalized_with_offsets(text: str) -> tuple[str, list[int]]:
    import re

    chars: list[str] = []
    offsets: list[int] = []
    for idx, char in enumerate(text):
        if re.match(r"[\s　 \.,!?]+", char):
            continue
        chars.append(char)
        offsets.append(idx)
    return "".join(chars), offsets


def _find_excerpt_span(essay_text: str, excerpt: str) -> tuple[int, int] | None:
    if not excerpt:
        return None
    exact = essay_text.find(excerpt)
    if exact >= 0:
        return exact, exact + len(excerpt)

    normalized_essay, offsets = _normalized_with_offsets(essay_text)
    normalized_excerpt, _ = _normalized_with_offsets(excerpt)
    if not normalized_excerpt:
        return None
    normalized_pos = normalized_essay.find(normalized_excerpt)
    if normalized_pos < 0:
        return None
    start = offsets[normalized_pos]
    end = offsets[normalized_pos + len(normalized_excerpt) - 1] + 1
    return start, end


def _repair_stage_a_evidence_spans(resp: dict, essay_text: str) -> int:
    """Normalize Stage A evidence spans to validator-safe exact substrings.

    Repairs common smoke-test failures: overly long spans, end offsets beyond
    essay length, and offsets that disagree with the quoted text. Unrepairable
    evidence items are dropped; an empty evidence list is valid for Stage A.
    """
    if not isinstance(resp, dict) or not isinstance(resp.get("evidence"), dict):
        return 0
    repairs = 0
    for items in resp["evidence"].values():
        if not isinstance(items, list):
            continue
        repaired_items: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                repairs += 1
                continue
            span = item.get("span")
            text = item.get("text")
            if (
                not isinstance(span, list)
                or len(span) != 2
                or not all(isinstance(x, int) for x in span)
                or not isinstance(text, str)
            ):
                repairs += 1
                continue
            start, end = span
            if not essay_text:
                repairs += 1
                continue

            found = _find_excerpt_span(essay_text, text)
            if found is not None:
                start, end = found
            elif 0 <= start < len(essay_text):
                end = min(max(end, start + 1), len(essay_text))
            else:
                repairs += 1
                continue

            clipped_end = min(end, start + STAGE_A_EVIDENCE_TEXT_MAX, len(essay_text))
            if clipped_end <= start:
                repairs += 1
                continue
            repaired_text = essay_text[start:clipped_end]
            if item.get("span") != [start, clipped_end] or item.get("text") != repaired_text:
                repairs += 1
            item["span"] = [start, clipped_end]
            item["text"] = repaired_text
            repaired_items.append(item)
        items[:] = repaired_items
    return repairs


def _repair_stage_b_span_refs(resp: dict, stage_a_evidence: dict | None) -> int:
    """Drop Stage B span_refs that no longer point to Stage A evidence.

    Stage A smoke repair may drop unrepairable evidence items. A later Stage B
    response can still cite the pre-repair indices it inferred from the prompt,
    so prune invalid references before validator gating.
    """
    if not isinstance(resp, dict) or not isinstance(stage_a_evidence, dict):
        return 0
    scores = resp.get("scores")
    if not isinstance(scores, dict):
        return 0

    repairs = 0
    for trait, entry in scores.items():
        if not isinstance(entry, dict):
            continue
        refs = entry.get("span_refs")
        if not isinstance(refs, list):
            continue
        ev_list = stage_a_evidence.get(trait, [])
        max_refs = len(ev_list) if isinstance(ev_list, list) else 0
        valid_refs = [ref for ref in refs if isinstance(ref, int) and 0 <= ref < max_refs]
        if valid_refs != refs:
            repairs += len(refs) - len(valid_refs)
            entry["span_refs"] = valid_refs
        if entry.get("score") is not None and not valid_refs:
            if max_refs > 0:
                entry["span_refs"] = [0]
            else:
                entry["score"] = None
                entry["reason"] = "insufficient_evidence"
                entry["span_refs"] = []
            repairs += 1
    return repairs


# --- Shared response processing (sync + batch) ----------------------------
def _process_stage_response(
    resp_text: str,
    api_rev: str,
    usage: dict,
    *,
    essay: dict,
    purpose: str,
    stage: str,
    track: str,
    out_path: Path,
    repeat_index: int = 0,
    attempt: int = 1,
) -> tuple[bool, str]:
    """Parse → repair → validate → append one stage response.

    Shared by the synchronous path (``_run_stage_one``) and the Batch path
    (``_process_batch_results``). Returns ``(True, "")`` after a successful
    write, or ``(False, error_message)`` after recording the failure. The
    caller owns retry / orchestration and already holds ``api_rev``.
    """
    eid = essay["essay_answer"]["id"]

    # F1 fence-strip safety net (F2 prefill is primary prevention)
    cleaned_text = _strip_markdown_fence(resp_text)
    try:
        resp = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        parse_error: Exception = e
        resp = None
        if stage == "A":
            repaired_text = _escape_unescaped_text_value_quotes(cleaned_text)
            if repaired_text != cleaned_text:
                try:
                    resp = json.loads(repaired_text)
                    resp_text = repaired_text
                    log.info("essay %d stage A attempt %d: escaped quoted evidence text",
                             eid, attempt)
                except json.JSONDecodeError as repaired_error:
                    parse_error = repaired_error
        if resp is None:
            last_error = f"non-JSON response: {parse_error}"
            log.error("essay %d stage %s attempt %d: %s", eid, stage, attempt, last_error)
            _record_error(
                out_path.parent, eid, stage, f"attempt{attempt}_non_json", resp_text,
                purpose=purpose,
            )
            return False, last_error

    try:
        if stage == "A":
            n_repairs = _repair_stage_a_evidence_spans(
                resp,
                essay["essay_answer"]["text"],
            )
            if n_repairs:
                log.info("essay %d stage A attempt %d: clipped %d long evidence spans",
                         eid, attempt, n_repairs)
            validate_stage_a(resp, essay_text=essay["essay_answer"]["text"])
        elif stage == "B":
            prior_a = _load_prior_stage(purpose, eid, track, "A")
            stage_a_evidence = (prior_a or {}).get("evidence")
            n_repairs = _repair_stage_b_span_refs(resp, stage_a_evidence)
            if n_repairs:
                log.info("essay %d stage B attempt %d: repaired %d span_refs/NA fields",
                         eid, attempt, n_repairs)
            validate_stage_b(resp, stage_a_evidence=stage_a_evidence)
        else:
            prior_b = _load_prior_stage(purpose, eid, track, "B")
            prior_a = _load_prior_stage(purpose, eid, track, "A")
            if prior_b is not None and prior_a is not None:
                _repair_stage_b_span_refs(prior_b, prior_a.get("evidence"))
            validate_stage_c(resp, stage_b_scores=(prior_b or {}).get("scores"))
    except Exception as e:
        last_error = f"validator failed: {e}"
        log.error("essay %d stage %s attempt %d: %s", eid, stage, attempt, last_error)
        _record_error(
            out_path.parent, eid, stage, f"attempt{attempt}_validator", resp_text,
            purpose=purpose,
        )
        return False, last_error

    if track == "alpha_pilot":
        resp["_repeat_index"] = repeat_index
    resp["_api_revision"] = api_rev
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(resp, ensure_ascii=False) + "\n")
    _record_usage(out_path, eid, stage, usage, repeat_index=repeat_index, attempt=attempt)
    return True, ""


# --- Single-essay pipeline step -------------------------------------------
def _run_stage_one(
    *,
    essay: dict,
    purpose: str,
    stage: str,
    track: str,
    model_id: str,
    assembled_prompt: str,
    out_path: Path,
    repeat_index: int = 0,
) -> tuple[bool, str]:
    """Invoke the LLM for one (essay, stage), validate, append."""
    eid = essay["essay_answer"]["id"]

    stage_a_json: str | None = None
    stage_b_json: str | None = None
    if stage in ("B", "C"):
        prior_a = _load_prior_stage(purpose, eid, track, "A")
        if prior_a is None:
            log.error("Missing Stage A for essay %d (%s/%s) — run Stage A first",
                      eid, purpose, track)
            return False, ""
        stage_a_json = json.dumps(prior_a, ensure_ascii=False)
    if stage == "C":
        prior_b = _load_prior_stage(purpose, eid, track, "B")
        if prior_b is None:
            log.error("Missing Stage B for essay %d (%s/%s) — run Stage B first",
                      eid, purpose, track)
            return False, ""
        if prior_a is not None:
            _repair_stage_b_span_refs(prior_b, prior_a.get("evidence"))
        stage_b_json = json.dumps(prior_b, ensure_ascii=False)

    final_prompt = render_runtime(
        assembled_prompt=assembled_prompt,
        essay_question=essay["essay_question"],
        essay_id=eid,
        essay_text=essay["essay_answer"]["text"],
        stage_a_json=stage_a_json,
        stage_b_json=stage_b_json,
    )

    last_error = ""
    for attempt in (1, 2):
        try:
            resp_text, api_rev, usage = _invoke_anthropic(final_prompt, model_id, TEMPERATURE)
        except Exception as e:
            last_error = f"api error: {type(e).__name__}: {e}"
            log.error("essay %d stage %s attempt %d: %s", eid, stage, attempt, last_error)
            _record_error(
                out_path.parent, eid, stage, f"attempt{attempt}_api_error", last_error,
                purpose=purpose,
            )
            continue
        ok, err = _process_stage_response(
            resp_text, api_rev, usage,
            essay=essay, purpose=purpose, stage=stage, track=track,
            out_path=out_path, repeat_index=repeat_index, attempt=attempt,
        )
        if ok:
            return True, api_rev
        last_error = err

    log.error("essay %d stage %s: failed after retry — %s", eid, stage, last_error)
    return False, ""


def _record_usage(
    out_path: Path,
    essay_id: int,
    stage: str,
    usage: dict,
    *,
    repeat_index: int = 0,
    attempt: int = 1,
) -> None:
    """Append a token usage row alongside the main JSONL output.

    Path: ``{out_path stem}.usage.jsonl`` — separate stream so the main
    JSONL stays schema-clean for downstream parsing while axis (d)
    aggregation has a stable source.
    """
    import datetime as _dt

    usage_path = out_path.with_suffix(".usage.jsonl")
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "essay_id": essay_id,
        "stage": stage,
        "repeat_index": repeat_index,
        "attempt": attempt,
        **(usage or {}),
    }
    with usage_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _record_error(
    dir_path: Path,
    essay_id: int,
    stage: str,
    kind: str,
    body: str,
    purpose: str | None = None,
) -> None:
    """Record a per-call error as both a per-file txt and an aggregated jsonl.

    Per-file: ``errors/essay{N}_stage{X}_{kind}.txt`` (full body for debugging).
    Aggregated: ``errors/errors.jsonl`` (essay_id, stage, kind, timestamp, excerpt)
    for axis (a) schema error / axis (b) validator fail rate aggregation by
    ``scripts/smoke_api_axes_audit.py``.
    """
    import datetime as _dt

    err_dir = dir_path.parent / "errors"
    err_dir.mkdir(parents=True, exist_ok=True)
    p = err_dir / f"essay{essay_id}_stage{stage}_{kind}.txt"
    p.write_text(body, encoding="utf-8")
    agg_path = err_dir / "errors.jsonl"
    row = {
        "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "essay_id": essay_id,
        "stage": stage,
        "kind": kind,
        "body_excerpt": body[:200],
    }
    if purpose is not None:
        row["purpose"] = purpose
    with agg_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# --- Batch API path --------------------------------------------------------
# custom_id must be ASCII ([a-zA-Z0-9_-], <=64 chars), so Korean purpose names
# are encoded to short reversible codes.
_PURPOSE_CODE: dict[str, str] = {"설명": "EXP", "설득": "PER"}
_PURPOSE_FROM_CODE: dict[str, str] = {v: k for k, v in _PURPOSE_CODE.items()}


def _batch_custom_id(purpose: str, stage: str, essay_id: int, repeat_index: int) -> str:
    return f"{_PURPOSE_CODE[purpose]}_{stage}_{int(essay_id)}_{int(repeat_index)}"


def _parse_custom_id(custom_id: str) -> tuple[str, str, int, int]:
    code, stage, eid, ri = custom_id.split("_")
    return _PURPOSE_FROM_CODE[code], stage, int(eid), int(ri)


def _batch_meta_path(track: str) -> Path:
    return STAGE4_OUT / track / "_batch_meta.jsonl"


def _append_batch_meta(track: str, row: dict) -> None:
    import datetime as _dt
    path = _batch_meta_path(track)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"logged_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), **row}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_batch_meta(track: str) -> list[dict]:
    path = _batch_meta_path(track)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _batch_in_flight(track: str, purpose: str, stage: str) -> str | None:
    """batch_id of a submitted-but-not-retrieved batch for (purpose, stage)."""
    submitted: list[str] = []
    retrieved: set[str] = set()
    for row in _load_batch_meta(track):
        if (row.get("event") == "submit" and row.get("purpose") == purpose
                and row.get("stage") == stage):
            submitted.append(row["batch_id"])
        elif row.get("event") == "retrieve":
            retrieved.add(row.get("batch_id"))
    for bid in submitted:
        if bid not in retrieved:
            return bid
    return None


def _anthropic_client():
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required for Stage 4 Batch execution") from exc
    return Anthropic()


def _build_batch_request(
    essay: dict, *, purpose: str, stage: str, track: str,
    assembled_prompt: str, model_id: str, repeat_index: int,
) -> dict | None:
    """Build one Anthropic batch request dict, or None if a prior stage is missing.

    Mirrors the prompt assembly + prefill of ``_invoke_anthropic`` so batch and
    sync responses are processed identically.
    """
    eid = essay["essay_answer"]["id"]
    stage_a_json: str | None = None
    stage_b_json: str | None = None
    prior_a = None
    if stage in ("B", "C"):
        prior_a = _load_prior_stage(purpose, eid, track, "A")
        if prior_a is None:
            log.error("batch: missing Stage A for essay %d (%s/%s)", eid, purpose, track)
            return None
        stage_a_json = json.dumps(prior_a, ensure_ascii=False)
    if stage == "C":
        prior_b = _load_prior_stage(purpose, eid, track, "B")
        if prior_b is None:
            log.error("batch: missing Stage B for essay %d (%s/%s)", eid, purpose, track)
            return None
        if prior_a is not None:
            _repair_stage_b_span_refs(prior_b, prior_a.get("evidence"))
        stage_b_json = json.dumps(prior_b, ensure_ascii=False)

    final_prompt = render_runtime(
        assembled_prompt=assembled_prompt,
        essay_question=essay["essay_question"],
        essay_id=eid,
        essay_text=essay["essay_answer"]["text"],
        stage_a_json=stage_a_json,
        stage_b_json=stage_b_json,
    )
    return {
        "custom_id": _batch_custom_id(purpose, stage, eid, repeat_index),
        "params": {
            "model": model_id,
            "max_tokens": STAGE4_MAX_TOKENS,
            "temperature": TEMPERATURE,
            "messages": [
                {"role": "user", "content": final_prompt},
                {"role": "assistant", "content": "{"},
            ],
        },
    }


def _submit_batch_stage(
    *, track: str, stage: str, purpose: str,
    todo: list[dict], done: set[tuple[int, int]], n_repeats: int,
    model_id: str, assembled_prompt: str, out_path: Path, stamp,
) -> int:
    """Submit one Batch for (track, stage, purpose). Idempotent: refuses to
    resubmit while a prior batch for the same slice is still in flight."""
    inflight = _batch_in_flight(track, purpose, stage)
    if inflight is not None:
        log.warning("batch already in flight for %s/%s (%s) — run --batch-poll to retrieve; "
                    "not resubmitting", purpose, stage, inflight)
        return 0

    requests: list[dict] = []
    skipped = 0
    for essay in todo:
        eid = int(essay["essay_answer"]["id"])
        for ri in range(n_repeats):
            if (eid, ri) in done:
                continue
            req = _build_batch_request(
                essay, purpose=purpose, stage=stage, track=track,
                assembled_prompt=assembled_prompt, model_id=model_id, repeat_index=ri,
            )
            if req is None:
                skipped += 1
                continue
            requests.append(req)

    if skipped:
        # A prior stage is incomplete for some pending essays. Refuse to submit
        # a partial batch (avoids paid spend on an incomplete stage and the
        # silent "exit 0 looks like success" trap). Record why we aborted.
        _append_batch_meta(track, {
            "event": "abort_missing_prior",
            "purpose": purpose,
            "stage": stage,
            "track": track,
            "n_skipped_missing_prior": skipped,
            "n_buildable": len(requests),
        })
        log.error("batch: %d essays missing a prior stage for %s/%s — complete/retrieve the "
                  "prior stage before submitting this batch (refusing partial submit)",
                  skipped, purpose, stage)
        return 1

    if not requests:
        log.info("batch: nothing to submit for %s/%s (all done)", purpose, stage)
        return 0

    client = _anthropic_client()
    batch = client.messages.batches.create(requests=requests)
    batch_id = getattr(batch, "id", None) or ""
    import datetime as _dt
    _append_batch_meta(track, {
        "event": "submit",
        "batch_id": batch_id,
        "purpose": purpose,
        "stage": stage,
        "track": track,
        "model_id": model_id,
        "submit_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "n_requests": len(requests),
        "n_skipped_missing_prior": skipped,
    })
    append_to_registry(dataclasses.replace(stamp, api_revision=f"batch_submit:{batch_id}"))
    log.info("batch submitted: %s — %d requests (%s/%s). Poll with --batch-poll.",
             batch_id, len(requests), purpose, stage)
    return 0


def _batch_result_text_and_usage(message) -> tuple[str, dict]:
    """Reconstruct response text (with prefill '{') + usage dict from a batch
    result Message — mirrors the extraction in ``_invoke_anthropic``."""
    content = getattr(message, "content", None) or []
    raw = ""
    if content:
        raw = getattr(content[0], "text", None) or ""
        if not raw and isinstance(content[0], dict):
            raw = content[0].get("text", "") or ""
    text = "{" + raw
    usage = getattr(message, "usage", None)
    usage_dict: dict = {
        "input_tokens": None, "output_tokens": None,
        "cache_creation_input_tokens": None, "cache_read_input_tokens": None,
    }
    if usage is not None:
        for k in usage_dict:
            v = getattr(usage, k, None)
            if v is None and isinstance(usage, dict):
                v = usage.get(k)
            usage_dict[k] = v
    return text, usage_dict


def _process_batch_results(
    track: str, *, batch_id: str, purpose: str, stage: str,
    essays_by_id: dict[int, dict], client=None,
) -> tuple[int, int]:
    """Retrieve + process one ended batch via the shared response pipeline.

    Returns ``(n_succeeded, n_failed)``. Idempotent: skips (essay, repeat) pairs
    already present in the stage output JSONL.
    """
    if client is None:
        client = _anthropic_client()
    out_path = STAGE4_OUT / track / stage / f"{purpose}.jsonl"
    done = _load_done_ids(out_path)
    n_ok = 0
    n_fail = 0
    for entry in client.messages.batches.results(batch_id):
        custom_id = getattr(entry, "custom_id", "")
        try:
            p, st, eid, ri = _parse_custom_id(custom_id)
        except Exception:
            log.error("batch: unparseable custom_id %r", custom_id)
            n_fail += 1
            continue
        if p != purpose or st != stage:
            # custom_id disagrees with the batch's recorded (purpose, stage).
            # Skip this entry (don't abort the whole retrieval) and flag it.
            log.error("batch: custom_id %r (%s/%s) does not match batch meta (%s/%s) — skipping",
                      custom_id, p, st, purpose, stage)
            n_fail += 1
            continue
        if (eid, ri) in done:
            continue
        essay = essays_by_id.get(eid)
        if essay is None:
            log.error("batch: essay %d not found in %s corpus", eid, purpose)
            n_fail += 1
            continue
        result = getattr(entry, "result", None)
        rtype = getattr(result, "type", None)
        if rtype != "succeeded":
            body = f"batch result type={rtype}: {getattr(result, 'error', '')}"
            _record_error(out_path.parent, eid, stage, f"batch_{rtype or 'unknown'}",
                          body, purpose=purpose)
            n_fail += 1
            continue
        text, usage = _batch_result_text_and_usage(getattr(result, "message", None))
        ok, _err = _process_stage_response(
            text, f"batch:{batch_id}", usage,
            essay=essay, purpose=p, stage=st, track=track,
            out_path=out_path, repeat_index=ri, attempt=1,
        )
        if ok:
            n_ok += 1
            done.add((eid, ri))
        else:
            n_fail += 1
    return n_ok, n_fail


def poll_and_retrieve_batches(
    track: str = "main", *, wait: bool = False, poll_interval_s: int = 60,
) -> int:
    """Poll in-flight batches recorded in ``_batch_meta`` and retrieve ended ones.

    ``wait=False`` (default): report status of not-yet-ended batches and move on
    (researcher reruns ``--batch-poll`` later). ``wait=True``: sleep-loop until
    each batch ends (only sensible for tiny test batches).
    """
    import time as _time
    meta = _load_batch_meta(track)
    retrieved = {r["batch_id"] for r in meta if r.get("event") == "retrieve"}
    submits = [r for r in meta
               if r.get("event") == "submit" and r.get("batch_id") not in retrieved]
    if not submits:
        log.info("batch: no in-flight batches to poll for track=%s", track)
        return 0

    client = _anthropic_client()
    corpus: dict[str, dict[int, dict]] = {}
    rc = 0
    for row in submits:
        bid = row["batch_id"]
        purpose = row["purpose"]
        stage = row["stage"]
        batch = client.messages.batches.retrieve(bid)
        while getattr(batch, "processing_status", None) != "ended" and wait:
            log.info("batch %s (%s/%s) status=%s — waiting %ds",
                     bid, purpose, stage, getattr(batch, "processing_status", None),
                     poll_interval_s)
            _time.sleep(poll_interval_s)
            batch = client.messages.batches.retrieve(bid)
        if getattr(batch, "processing_status", None) != "ended":
            log.info("batch %s (%s/%s) status=%s — not ended; rerun --batch-poll later",
                     bid, purpose, stage, getattr(batch, "processing_status", None))
            continue
        if purpose not in corpus:
            corpus[purpose] = {int(e["essay_answer"]["id"]): e
                               for e in _load_corpus_essays(purpose)}
        n_ok, n_fail = _process_batch_results(
            track, batch_id=bid, purpose=purpose, stage=stage,
            essays_by_id=corpus[purpose], client=client,
        )
        import datetime as _dt
        _append_batch_meta(track, {
            "event": "retrieve",
            "batch_id": bid,
            "purpose": purpose,
            "stage": stage,
            "retrieved_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "n_succeeded": n_ok,
            "n_failed": n_fail,
        })
        log.info("batch %s (%s/%s) retrieved: %d ok / %d failed", bid, purpose, stage, n_ok, n_fail)
        if n_fail:
            rc = 1
    return rc


# --- Track orchestration --------------------------------------------------
def run_track(
    *,
    track: str,
    stage: str | None,
    purpose: str,
    sample_csv: Path | None = None,
    sample_size: int | None = None,
    repeats: int = 1,
    rerun: bool = False,
    use_batch: bool = False,
) -> int:
    """Run a single (track × stage × purpose) slice."""
    if track == "main":
        model_id = MODEL_ID_MAIN
    elif track == "sensitivity":
        model_id = MODEL_ID_SENSITIVITY
    elif track == "alpha_pilot":
        model_id = MODEL_ID_MAIN
        stage = "B"  # α pilot only runs Stage B per v2.3 §4.3.2
    elif track == "smoke":
        # Smoke uses MODEL_ID_MAIN with restricted sample. Outputs go to
        # STAGE4_OUT/smoke/ so they do not pollute the eventual main run dir.
        model_id = MODEL_ID_MAIN
    else:
        raise ValueError(track)

    if use_batch and track != "main":
        raise ValueError("--batch is only valid for the main track")
    if rerun and track != "smoke":
        raise ValueError("--rerun is only valid for --track smoke (axis (e) check)")

    assert stage in ("A", "B", "C")
    assembled_path = PROJECT_ROOT / "prompts" / purpose / f"{stage}.md"
    assembled = assembled_path.read_text(encoding="utf-8")

    essays = _load_corpus_essays(purpose)
    if track == "sensitivity":
        assert sample_csv is not None, "sensitivity track requires --sample"
        keep = _load_sensitivity_sample_ids(sample_csv)
        essays = [e for e in essays if int(e["essay_answer"]["id"]) in keep]
    elif track == "alpha_pilot":
        # First ALPHA_PILOT_N_ESSAYS essays (grade-stratified shuffling is handled
        # externally — see src/llm/sensitivity_sampler.py pattern for reference).
        essays = essays[:ALPHA_PILOT_N_ESSAYS]
    elif track == "smoke":
        # Deterministic canonical base sample (seed=42 per v2.6 §8.1). Always
        # size 15 per purpose so that rerun subsets are prefixes of the base
        # (axis (e) requires same essays as Stage A/B). `random.sample(k=N)` 가
        # k 값에 따라 다른 subset 을 주므로 base 를 먼저 fix 한 후 subset 추출.
        import random
        rng = random.Random(42)
        base = sorted(rng.sample(essays, min(15, len(essays))),
                      key=lambda r: r["essay_answer"]["id"])
        if rerun:
            # Rerun: subset of base 15 (default 10) for axis (e) consistency.
            n = sample_size if sample_size is not None else 10
            essays = base[:n]
        else:
            # Normal smoke: take sample_size (default 15) — typically the full base.
            n = sample_size if sample_size is not None else 15
            essays = base[:n] if n <= len(base) else base

    # Output path. Smoke + --rerun writes to {stage}.rerun.jsonl to keep the
    # original smoke output intact for axis (e) consistency comparison.
    if track == "smoke" and rerun:
        out_path = STAGE4_OUT / track / stage / f"{purpose}.rerun.jsonl"
    else:
        out_path = STAGE4_OUT / track / stage / f"{purpose}.jsonl"
    done = _load_done_ids(out_path)
    n_repeats = ALPHA_PILOT_N_REPEATS if track == "alpha_pilot" else repeats
    pending_keys = {
        (int(e["essay_answer"]["id"]), ri)
        for e in essays
        for ri in range(n_repeats)
        if (int(e["essay_answer"]["id"]), ri) not in done
    }
    todo = [e for e in essays if any((int(e["essay_answer"]["id"]), ri) in pending_keys for ri in range(n_repeats))]
    log.info("track=%s stage=%s purpose=%s model=%s — %d todo / %d total (%d already done)",
             track, stage, purpose, model_id, len(todo), len(essays), len(done))

    stamp = make_stamp(
        stage=stage, purpose=purpose,
        n_essays=len(pending_keys),
        prompt_path=assembled_path,
        track=track,
    )

    if use_batch:
        return _submit_batch_stage(
            track=track, stage=stage, purpose=purpose,
            todo=todo, done=done, n_repeats=n_repeats,
            model_id=model_id, assembled_prompt=assembled,
            out_path=out_path, stamp=stamp,
        )

    failures = 0
    registry_written = False
    for essay in todo:
        eid = int(essay["essay_answer"]["id"])
        for ri in range(n_repeats):
            if (eid, ri) in done:
                continue
            ok, api_revision = _run_stage_one(
                essay=essay, purpose=purpose, stage=stage, track=track,
                model_id=model_id, assembled_prompt=assembled,
                out_path=out_path, repeat_index=ri,
            )
            if ok and not registry_written:
                append_to_registry(dataclasses.replace(stamp, api_revision=api_revision))
                registry_written = True
            if not ok:
                failures += 1
    if not registry_written:
        append_to_registry(dataclasses.replace(stamp, api_revision="NO_SUCCESSFUL_CALL"))
    log.info("Done: %d calls, %d failures. Output: %s",
             len(pending_keys), failures, out_path)
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=("main", "sensitivity", "alpha_pilot", "smoke"), required=True)
    parser.add_argument("--stage", choices=("A", "B", "C"))
    parser.add_argument("--purpose", choices=list(PURPOSES_IN_SCOPE),
                        help="required except with --batch-poll (which polls all in-flight)")
    parser.add_argument("--sample", type=Path,
                        help="sensitivity sample CSV (required for --track sensitivity)")
    parser.add_argument("--sample-size", type=int, default=None,
                        help="random N essay subset (default 15 for smoke). seed=42.")
    parser.add_argument("--repeats", type=int, default=1,
                        help="override repeat count (main/sensitivity default 1)")
    parser.add_argument("--rerun", action="store_true",
                        help="smoke: write to {stage}.rerun.jsonl for axis (e) consistency")
    parser.add_argument("--batch", action="store_true",
                        help="submit main track via Batch API after smoke/audit gates")
    parser.add_argument("--batch-poll", action="store_true",
                        help="poll + retrieve in-flight Batch jobs from _batch_meta.jsonl "
                             "(ignores --stage/--purpose; polls all for the track)")
    parser.add_argument("--batch-wait", action="store_true",
                        help="with --batch-poll: sleep-loop until batches end (tiny test only)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")

    if args.batch_poll:
        return poll_and_retrieve_batches(args.track, wait=args.batch_wait)

    if args.purpose is None:
        parser.error("--purpose is required (except with --batch-poll)")
    if args.track == "alpha_pilot" and args.stage is not None and args.stage != "B":
        log.warning("alpha_pilot only runs Stage B; overriding --stage")
    if args.track in ("main", "sensitivity", "smoke") and args.stage is None:
        parser.error(f"--stage required for track={args.track}")

    return run_track(
        track=args.track,
        stage=args.stage,
        purpose=args.purpose,
        sample_csv=args.sample,
        sample_size=args.sample_size,
        repeats=args.repeats,
        rerun=args.rerun,
        use_batch=args.batch,
    )


if __name__ == "__main__":
    sys.exit(main())
