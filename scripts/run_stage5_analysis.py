from pathlib import Path
import pandas as pd

def main() -> int:
    base = Path("data/derived_public")
    qwk = pd.read_csv(base / "table1_score_level_qwk.csv")
    nonzero = pd.read_csv(base / "table2_alignment_nonzero_breakdown.csv")
    direction = pd.read_csv(base / "table3_surface_content_direction.csv")
    out = Path("reports/main_contrast_summary_redacted.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Redacted main contrast summary\n\n## Score-level QWK\n\n" + qwk.to_markdown(index=False) + "\n\n## Alignment nonzero breakdown\n\n" + nonzero.to_markdown(index=False) + "\n\n## Direction counts\n\n" + direction.to_markdown(index=False) + "\n", encoding="utf-8")
    print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
