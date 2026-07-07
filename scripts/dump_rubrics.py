"""
Dump every unique rubric variant in the corpus as Markdown.

The NIA 14-026 corpus contains 3 purposes (설명 / 설득 / 친교 및 정서).
Each purpose may define a different analytic trait set and different
evaluation descriptors. To decide study scope (progress.md §11), we need
to SEE each rubric. This script collects every unique rubric block
observed in the corpus and writes one MD file per distinct rubric.

Uniqueness is determined by a structural fingerprint:
    (purpose, tuple(sorted(analytic trait keys)),
     tuple(sorted(rubric_key values)))

Usage
-----
    python -m scripts.dump_rubrics
        → reports/rubrics/rubric__설명.md
        → reports/rubrics/rubric__설득.md (if present)
        → reports/rubrics/rubric__친교_및_정서.md (if present)
        → reports/rubrics/_index.md  (summary table)
"""
from __future__ import annotations

import logging
import sys
from collections import OrderedDict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.paths import DATA_ROOT, REPORTS_DIR  # noqa: E402
from src.data.loader import discover_essay_files  # noqa: E402
from src.data.rubric import (  # noqa: E402
    RubricBlock,
    dump_rubric,
    parse_rubric,
)


def rubric_fingerprint(rb: RubricBlock) -> tuple:
    """Structural signature used to deduplicate rubric variants."""
    traits = tuple(sorted(rb.analytic.keys()))
    keys = tuple(sorted(ar.rubric_key_raw for ar in rb.analytic.values()))
    return (rb.purpose, traits, keys)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    import json

    paths = discover_essay_files(DATA_ROOT)
    logging.info("Scanning %d essays for rubric variants …", len(paths))

    variants: "OrderedDict[tuple, tuple[RubricBlock, list[str]]]" = OrderedDict()

    for p in paths:
        try:
            with p.open("r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            logging.warning("Skipping %s: %s", p.name, e)
            continue
        raw = d.get("rubric", {})
        if not raw:
            continue
        rb = parse_rubric(raw)
        fp = rubric_fingerprint(rb)
        if fp not in variants:
            variants[fp] = (rb, [p.name])
        else:
            variants[fp][1].append(p.name)

    out_dir = REPORTS_DIR / "rubrics"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write one MD per variant
    index_rows: list[dict] = []
    for i, (fp, (rb, sources)) in enumerate(variants.items(), start=1):
        slug = f"{rb.purpose.replace(' ', '_').replace('/', '_')}"
        # Disambiguate if multiple variants share the same purpose
        if sum(1 for _fp, (_rb, _) in variants.items()
                if _rb.purpose == rb.purpose) > 1:
            slug = f"{slug}__v{i}"
        md_path = dump_rubric(rb, out_dir, slug=slug)
        n_traits = len(rb.analytic)
        index_rows.append({
            "purpose":       rb.purpose,
            "purpose_code":  rb.purpose_code or "",
            "n_traits":      n_traits,
            "trait_keys":    ", ".join(sorted(rb.analytic.keys())),
            "n_essays":      len(sources),
            "sample_source": sources[0],
            "md_file":       md_path.name,
        })
        logging.info("Wrote %s (%d traits, %d essays share this rubric)",
                     md_path.name, n_traits, len(sources))

    # Index file
    idx = out_dir / "_index.md"
    lines = [
        "# Rubric variants found in the corpus",
        "",
        f"Scanned {len(paths)} essays, found **{len(variants)}** distinct "
        "rubric variants.",
        "",
        "| # | purpose | purpose_code | n_traits | n_essays | trait keys | md file |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(index_rows, start=1):
        lines.append(
            f"| {i} | {r['purpose']} | `{r['purpose_code']}` | "
            f"{r['n_traits']} | {r['n_essays']} | "
            f"`{r['trait_keys']}` | [{r['md_file']}]({r['md_file']}) |"
        )
    idx.write_text("\n".join(lines), encoding="utf-8")
    logging.info("Index: %s", idx)


if __name__ == "__main__":
    main()
