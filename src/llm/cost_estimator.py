"""
Stage 4 cost estimator — token-based precise figures.

Reads each assembled prompt + a sample essay batch to estimate:
    - Per-call tokens (input + output) by stage
    - Prompt caching benefit (assumed 90% of wrapper+rubric cached,
      essay+prior-stage outputs uncached)
    - Per-track total cost (main Sonnet, sensitivity Opus, α pilot Sonnet)

Pricing (confirmed by researcher before run; stored in ``PRICING``).
Token counting uses a simple char/2.5 estimator as default (Korean
tokens roughly 2-3 chars/token). Researcher can override with the
actual Anthropic tokenizer before large-scale execution.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from configs.paths import PROJECT_ROOT, PURPOSES_IN_SCOPE
from configs.stage4 import (
    ALPHA_PILOT_N_ESSAYS,
    ALPHA_PILOT_N_REPEATS,
    MAIN_N_ESSAYS,
    SENSITIVITY_N_ESSAYS,
)

log = logging.getLogger(__name__)


# Pricing placeholders (researcher confirms actual Anthropic rates before run).
# Figures are USD per million tokens. Caching assumption: cached read is 10%
# of normal input (Anthropic standard), cache write is 25% surcharge on first use.
PRICING: dict[str, dict[str, float]] = {
    "sonnet_4_x": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "opus_4_x":   {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
}

# Estimated output tokens per call (based on typical JSON shapes).
OUTPUT_TOKENS_BY_STAGE: dict[str, int] = {
    "A": 1000,  # evidence JSON with ~5-10 spans per trait × 8 traits
    "B": 500,   # scores JSON with 8 trait entries, each ~40 tokens
    "C": 2500,  # rationale JSON with 8 × (1-3 sentences × Korean)
}

# Cache block split — fraction of input tokens that is cacheable (wrapper +
# rubric, common across all essays of the same purpose).
CACHEABLE_FRACTION_BY_STAGE: dict[str, float] = {
    "A": 0.85,  # only essay text + task fields vary
    "B": 0.70,  # essay + Stage A output vary
    "C": 0.55,  # essay + Stage A + Stage B all vary
}


def _estimate_tokens(text: str) -> int:
    """Rough estimator: 1 token ≈ 2.5 chars for Korean+English mix."""
    return max(1, int(len(text) / 2.5))


@dataclass(frozen=True)
class StageCost:
    stage: str
    n_calls: int
    input_tokens_per_call: int
    output_tokens_per_call: int
    cached_fraction: float
    cost_uncached_usd: float
    cost_cached_usd: float
    savings_usd: float


def _load_assembled_prompt(purpose: str, stage: str) -> str:
    p = PROJECT_ROOT / "prompts" / purpose / f"{stage}.md"
    return p.read_text(encoding="utf-8")


def _sample_essay_text(purpose: str) -> str:
    """Return a medium-length essay from the corpus for token estimation."""
    root = Path(os.environ.get("AES_DATA_ROOT", PROJECT_ROOT / "dataset"))
    lengths: list[tuple[int, str]] = []
    for p in root.rglob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("essay_question", {}).get("purpose") != purpose:
            continue
        t = raw.get("essay_answer", {}).get("text", "")
        lengths.append((len(t), t))
        if len(lengths) >= 200:
            break
    lengths.sort(key=lambda x: x[0])
    # median
    return lengths[len(lengths) // 2][1] if lengths else ""


def estimate_stage(
    purpose: str,
    stage: str,
    n_calls: int,
    pricing_key: str,
    stage_a_output_tokens: int = 0,
    stage_b_output_tokens: int = 0,
) -> StageCost:
    prompt = _load_assembled_prompt(purpose, stage)
    essay = _sample_essay_text(purpose)

    # Assembled prompt tokens (before runtime task/essay/prior-stage injection).
    assembled_tokens = _estimate_tokens(prompt)
    essay_tokens = _estimate_tokens(essay)

    # Task block (grade/prompt/topic/level/type) ~60 tokens.
    task_tokens = 60

    if stage == "A":
        input_tokens = assembled_tokens + task_tokens + essay_tokens
    elif stage == "B":
        input_tokens = assembled_tokens + task_tokens + essay_tokens + stage_a_output_tokens
    else:  # C
        input_tokens = (
            assembled_tokens + task_tokens + essay_tokens
            + stage_a_output_tokens + stage_b_output_tokens
        )

    output_tokens = OUTPUT_TOKENS_BY_STAGE[stage]
    cache_frac = CACHEABLE_FRACTION_BY_STAGE[stage]

    p = PRICING[pricing_key]
    cached_in = input_tokens * cache_frac
    uncached_in = input_tokens * (1 - cache_frac)

    # Uncached scenario (no prompt caching used):
    cost_u = (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
    # Cached scenario (amortised — assume first call pays write surcharge on
    # cached_in, every subsequent of n_calls pays cache_read; all pay uncached_in):
    per_call_cache = uncached_in * p["input"] + cached_in * p["cache_read"]
    first_call_cache = uncached_in * p["input"] + cached_in * p["cache_write"]
    total_input_cost = first_call_cache + per_call_cache * (n_calls - 1)
    total_output_cost = output_tokens * p["output"] * n_calls
    cost_c_total = (total_input_cost + total_output_cost) / 1_000_000
    cost_c_per_call = cost_c_total / max(n_calls, 1)

    return StageCost(
        stage=stage,
        n_calls=n_calls,
        input_tokens_per_call=input_tokens,
        output_tokens_per_call=output_tokens,
        cached_fraction=cache_frac,
        cost_uncached_usd=cost_u * n_calls,
        cost_cached_usd=cost_c_total,
        savings_usd=cost_u * n_calls - cost_c_total,
    )


def estimate_main_track() -> list[StageCost]:
    """Main analysis: Sonnet × 2 purposes × 4860/2≈2430 essays × 3 stages."""
    per_purpose = {
        "설명": 2709,
        "설득": 2151,
    }
    out: list[StageCost] = []
    for purpose, n in per_purpose.items():
        a = estimate_stage(purpose, "A", n, "sonnet_4_x")
        b = estimate_stage(purpose, "B", n, "sonnet_4_x",
                           stage_a_output_tokens=OUTPUT_TOKENS_BY_STAGE["A"])
        c = estimate_stage(purpose, "C", n, "sonnet_4_x",
                           stage_a_output_tokens=OUTPUT_TOKENS_BY_STAGE["A"],
                           stage_b_output_tokens=OUTPUT_TOKENS_BY_STAGE["B"])
        a_named = StageCost(
            stage=f"A-{purpose}", n_calls=a.n_calls,
            input_tokens_per_call=a.input_tokens_per_call,
            output_tokens_per_call=a.output_tokens_per_call,
            cached_fraction=a.cached_fraction,
            cost_uncached_usd=a.cost_uncached_usd,
            cost_cached_usd=a.cost_cached_usd,
            savings_usd=a.savings_usd,
        )
        b_named = StageCost(
            stage=f"B-{purpose}", n_calls=b.n_calls,
            input_tokens_per_call=b.input_tokens_per_call,
            output_tokens_per_call=b.output_tokens_per_call,
            cached_fraction=b.cached_fraction,
            cost_uncached_usd=b.cost_uncached_usd,
            cost_cached_usd=b.cost_cached_usd,
            savings_usd=b.savings_usd,
        )
        c_named = StageCost(
            stage=f"C-{purpose}", n_calls=c.n_calls,
            input_tokens_per_call=c.input_tokens_per_call,
            output_tokens_per_call=c.output_tokens_per_call,
            cached_fraction=c.cached_fraction,
            cost_uncached_usd=c.cost_uncached_usd,
            cost_cached_usd=c.cost_cached_usd,
            savings_usd=c.savings_usd,
        )
        out.extend([a_named, b_named, c_named])
    return out


def estimate_sensitivity_track() -> list[StageCost]:
    """Opus on n=1000 essays × 3 stages (both purposes, unstratified at this level)."""
    out: list[StageCost] = []
    for purpose in PURPOSES_IN_SCOPE:
        n_per = SENSITIVITY_N_ESSAYS // len(PURPOSES_IN_SCOPE)  # 500 per purpose
        a = estimate_stage(purpose, "A", n_per, "opus_4_x")
        b = estimate_stage(purpose, "B", n_per, "opus_4_x",
                           stage_a_output_tokens=OUTPUT_TOKENS_BY_STAGE["A"])
        c = estimate_stage(purpose, "C", n_per, "opus_4_x",
                           stage_a_output_tokens=OUTPUT_TOKENS_BY_STAGE["A"],
                           stage_b_output_tokens=OUTPUT_TOKENS_BY_STAGE["B"])
        out.extend([
            StageCost(f"A-{purpose}-sens", a.n_calls, a.input_tokens_per_call,
                      a.output_tokens_per_call, a.cached_fraction,
                      a.cost_uncached_usd, a.cost_cached_usd, a.savings_usd),
            StageCost(f"B-{purpose}-sens", b.n_calls, b.input_tokens_per_call,
                      b.output_tokens_per_call, b.cached_fraction,
                      b.cost_uncached_usd, b.cost_cached_usd, b.savings_usd),
            StageCost(f"C-{purpose}-sens", c.n_calls, c.input_tokens_per_call,
                      c.output_tokens_per_call, c.cached_fraction,
                      c.cost_uncached_usd, c.cost_cached_usd, c.savings_usd),
        ])
    return out


def estimate_alpha_pilot() -> list[StageCost]:
    """Sonnet × Stage B only × n=500 essays × 5 repeats × 2 purposes."""
    out: list[StageCost] = []
    for purpose in PURPOSES_IN_SCOPE:
        n_calls = ALPHA_PILOT_N_ESSAYS * ALPHA_PILOT_N_REPEATS
        b = estimate_stage(purpose, "B", n_calls, "sonnet_4_x",
                           stage_a_output_tokens=OUTPUT_TOKENS_BY_STAGE["A"])
        out.append(StageCost(f"B-{purpose}-α", b.n_calls, b.input_tokens_per_call,
                             b.output_tokens_per_call, b.cached_fraction,
                             b.cost_uncached_usd, b.cost_cached_usd, b.savings_usd))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "markdown"), default="text")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    main_costs = estimate_main_track()
    sens_costs = estimate_sensitivity_track()
    alpha_costs = estimate_alpha_pilot()

    def _total(costs: list[StageCost]) -> tuple[float, float]:
        return sum(c.cost_uncached_usd for c in costs), sum(c.cost_cached_usd for c in costs)

    m_u, m_c = _total(main_costs)
    s_u, s_c = _total(sens_costs)
    a_u, a_c = _total(alpha_costs)
    grand_u = m_u + s_u + a_u
    grand_c = m_c + s_c + a_c

    print("=" * 80)
    print("Stage 4 Cost Estimate (rough, char/2.5 token estimator)")
    print("=" * 80)
    for label, costs, (u, c) in [
        ("Main (Sonnet)",        main_costs,  (m_u, m_c)),
        ("Sensitivity (Opus)",   sens_costs,  (s_u, s_c)),
        ("α pilot (Sonnet)",     alpha_costs, (a_u, a_c)),
    ]:
        print(f"\n--- {label} ---")
        print(f"{'stage':<20}{'n_calls':>10}{'in_tok':>10}{'out_tok':>10}"
              f"{'cost_nocache':>15}{'cost_cache':>15}{'saved':>10}")
        for sc in costs:
            print(f"{sc.stage:<20}{sc.n_calls:>10}"
                  f"{sc.input_tokens_per_call:>10}{sc.output_tokens_per_call:>10}"
                  f"{sc.cost_uncached_usd:>15.2f}{sc.cost_cached_usd:>15.2f}"
                  f"{sc.savings_usd:>10.2f}")
        print(f"  subtotal:       uncached=${u:.2f}   cached=${c:.2f}   saved=${u - c:.2f}")

    print("\n" + "=" * 80)
    print(f"GRAND TOTAL: uncached=${grand_u:.2f}   cached=${grand_c:.2f}   saved=${grand_u - grand_c:.2f}")
    print("=" * 80)
    print("\nNote: estimator uses char/2.5 tokens; confirm with Anthropic tokenizer"
          " before executing. Pricing values in src/llm/cost_estimator.py PRICING.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
