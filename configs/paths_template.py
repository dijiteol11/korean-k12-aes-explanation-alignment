from __future__ import annotations
import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("AES_DATA_ROOT", PROJECT_ROOT / "data" / "restricted_not_shared"))
DERIVED_PUBLIC_DIR = PROJECT_ROOT / "data" / "derived_public"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = PROJECT_ROOT / "figures"
PURPOSES_IN_SCOPE = ("expository", "persuasive")
ANALYSED_TRAITS = ("content_1", "expression_2", "organization_1")
FEATURE_FAMILIES = ("lex", "vocab_grade", "case_marker", "morph_prop", "syn", "dis_nonSBERT", "dis_SBERT", "meta")
