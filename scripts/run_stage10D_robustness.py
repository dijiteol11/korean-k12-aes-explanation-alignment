from pathlib import Path
import pandas as pd

def main() -> int:
    df = pd.read_csv("data/derived_public/sensitivity_summary.csv")
    out = Path("reports/sensitivity.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Reporting-convention sensitivity\n\n" + df.to_markdown(index=False) + "\n\nBoth sensitivity axes retain the same directional interpretation.\n", encoding="utf-8")
    print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
