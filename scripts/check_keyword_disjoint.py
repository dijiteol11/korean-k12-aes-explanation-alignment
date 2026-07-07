"""Validate v1.3 LLM keyword family disjointness."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.alignment.llm_family_detector import KEYWORD_SET, find_keyword_duplicates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addendum", type=Path, default=Path("main_contrast_preregistered_v1.3.md"))
    args = parser.parse_args(argv)

    if not args.addendum.exists():
        print(f"Addendum not found: {args.addendum}", file=sys.stderr)
        return 2

    duplicates = find_keyword_duplicates(KEYWORD_SET)
    if duplicates:
        for keyword, families in duplicates.items():
            print(f"duplicate keyword {' '.join(keyword)!r}: {', '.join(families)}", file=sys.stderr)
        return 1

    addendum_text = args.addendum.read_text(encoding="utf-8")
    missing = []
    for family, keywords in KEYWORD_SET.items():
        if f"`{family}`" not in addendum_text:
            missing.append(family)
        for keyword in keywords:
            phrase = " ".join(keyword)
            if phrase not in addendum_text:
                missing.append(f"{family}:{phrase}")
    if missing:
        print("Addendum is missing registered keyword entries:", file=sys.stderr)
        for item in missing:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"OK: {sum(len(v) for v in KEYWORD_SET.values())} keyword sequences are family-disjoint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
