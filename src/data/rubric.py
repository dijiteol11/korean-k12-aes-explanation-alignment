"""
Rubric types, parsing, and Markdown dump utilities.

The NIA 14-026 `rubric` object has the following verified structure
(from the sample 14-2-M1-N-0A-E-0026.json):

    {
        "type":        "논술형",
        "purpose":     "설명" | "설득" | "친교 및 정서",
        "achievement": <한 문장, purpose별 성취기준>,
        "analytic": {
            "<trait_key>": {
                "name":           <한국어 trait 이름>,
                "rubric_key":     "[X]-00A-[1{A|B|C|D}]-[2{letter}]",
                "evaluation_1":   <1점 서술>,
                "evaluation_2":   ...,
                "evaluation_3":   ...,
                "evaluation_4":   ...,
                "evaluation_5":   <5점 서술>,
            },
            ... 8 traits total (for purpose="설명")
        }
    }

Notes
-----
* `rubric` does NOT contain holistic rubric text — only analytic. The
  score object has `holistic` but any holistic LLM prompt must supply
  its own rubric description.
* The third segment of `rubric_key` (1A/1B/1C/1D) encodes the analytic
  area and maps 1:1 to our TRAITS grouping:
        1A → task        (task_1)
        1B → content     (content_1, content_2, content_3)
        1C → organization (organization_1, organization_2)
        1D → expression  (expression_1, expression_2)
* The first segment is almost certainly the purpose code
  (observed: "B" = 설명). Confirmation requires 설득/친교 samples;
  the parser does not hard-code an interpretation for segment 1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- Structural constants --------------------------------------------------
RUBRIC_AREA_FROM_TRAIT: dict[str, str] = {
    "task_1":         "task",
    "content_1":      "content",
    "content_2":      "content",
    "content_3":      "content",
    "organization_1": "organization",
    "organization_2": "organization",
    "expression_1":   "expression",
    "expression_2":   "expression",
}

# Third-segment letter → area (as observed in the 설명 sample).
# Verified by 1:1 match with TRAITS grouping.
AREA_LETTER_TO_NAME: dict[str, str] = {
    "1A": "task",
    "1B": "content",
    "1C": "organization",
    "1D": "expression",
}

_RUBRIC_KEY_RE = re.compile(
    r"^(?P<purpose_code>[A-Z])"
    r"-(?P<segment2>[^-]+)"
    r"-(?P<area>1[A-Z])"
    r"-(?P<detail>2[A-Z])$"
)


@dataclass(frozen=True)
class RubricKey:
    raw: str
    purpose_code: str   # e.g. "B"
    segment2: str       # e.g. "00A"
    area: str           # e.g. "1B"
    detail: str         # e.g. "2G"

    @property
    def area_name(self) -> str:
        return AREA_LETTER_TO_NAME.get(self.area, "unknown")

    @classmethod
    def parse(cls, raw: str) -> "RubricKey | None":
        m = _RUBRIC_KEY_RE.match(raw.strip())
        if not m:
            return None
        return cls(raw=raw, **m.groupdict())


@dataclass(frozen=True)
class AnalyticRubric:
    trait: str                  # e.g. "content_1"
    name: str                   # 한국어 이름
    rubric_key: RubricKey | None
    rubric_key_raw: str         # original string, even if unparseable
    evaluations: dict[int, str] = field(default_factory=dict)  # 1..5 → text


@dataclass(frozen=True)
class RubricBlock:
    type: str                   # "논술형"
    purpose: str                # "설명" | "설득" | "친교 및 정서"
    achievement: str            # 성취기준 한 문장
    analytic: dict[str, AnalyticRubric]
    raw: dict                   # unparsed dict, for LLM prompts

    @property
    def purpose_code(self) -> str | None:
        for ar in self.analytic.values():
            if ar.rubric_key is not None:
                return ar.rubric_key.purpose_code
        return None


def parse_rubric(raw: dict[str, Any]) -> RubricBlock:
    analytic_dict: dict[str, AnalyticRubric] = {}
    for trait_key, v in raw.get("analytic", {}).items():
        key_str = v.get("rubric_key", "")
        parsed = RubricKey.parse(key_str) if key_str else None
        evals = {
            i: v.get(f"evaluation_{i}", "")
            for i in range(1, 6)
            if v.get(f"evaluation_{i}")
        }
        analytic_dict[trait_key] = AnalyticRubric(
            trait=trait_key,
            name=v.get("name", ""),
            rubric_key=parsed,
            rubric_key_raw=key_str,
            evaluations=evals,
        )
    return RubricBlock(
        type=raw.get("type", ""),
        purpose=raw.get("purpose", ""),
        achievement=raw.get("achievement", ""),
        analytic=analytic_dict,
        raw=raw,
    )


# --- Markdown dump ---------------------------------------------------------
def rubric_to_markdown(rb: RubricBlock, *, title_prefix: str = "") -> str:
    """Pretty-print a RubricBlock as a human-readable MD document."""
    lines: list[str] = []
    title = f"{title_prefix} Rubric — {rb.purpose}".strip()
    lines.append(f"# {title}\n")
    lines.append(f"- **Type**: `{rb.type}`")
    lines.append(f"- **Purpose**: `{rb.purpose}`")
    lines.append(f"- **Purpose code (rubric_key segment 1)**: "
                  f"`{rb.purpose_code or 'n/a'}`")
    lines.append(f"- **성취기준 (achievement)**: {rb.achievement}\n")

    lines.append("## Analytic traits\n")
    lines.append("| trait | name | rubric_key | area (parsed) |")
    lines.append("|---|---|---|---|")
    for tk, ar in rb.analytic.items():
        area = ar.rubric_key.area_name if ar.rubric_key else "unparseable"
        lines.append(
            f"| `{tk}` | {ar.name} | `{ar.rubric_key_raw}` | {area} |"
        )
    lines.append("")

    lines.append("## Evaluation-level descriptors\n")
    for tk, ar in rb.analytic.items():
        lines.append(f"### `{tk}` — {ar.name}")
        lines.append(f"*rubric_key*: `{ar.rubric_key_raw}`\n")
        lines.append("| 점수 | 기준 |")
        lines.append("|---|---|")
        for i in sorted(ar.evaluations.keys(), reverse=True):
            txt = ar.evaluations[i].replace("\n", " ").strip()
            lines.append(f"| **{i}** | {txt} |")
        lines.append("")

    lines.append("---")
    lines.append("## Structural notes\n")
    lines.append(
        "- The third segment of `rubric_key` (1A/1B/1C/1D) encodes the "
        "analytic area and maps 1:1 to the trait grouping "
        "(task / content / organization / expression)."
    )
    lines.append(
        "- The first segment encodes the purpose. Cross-purpose samples "
        "are required to verify the full purpose-code mapping."
    )
    lines.append(
        "- `rubric` does not contain a holistic rubric; any holistic "
        "LLM prompt must supply its own descriptor."
    )
    return "\n".join(lines)


def dump_rubric(rb: RubricBlock, out_dir: Path, *,
                 slug: str | None = None) -> Path:
    """Write a rubric as MD to `out_dir`. Returns the written path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slug or rb.purpose.replace(" ", "_").replace("/", "_")
    path = out_dir / f"rubric__{slug}.md"
    path.write_text(rubric_to_markdown(rb), encoding="utf-8")
    return path
