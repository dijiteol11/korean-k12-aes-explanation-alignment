from __future__ import annotations
import re
KEYWORD_SET = {
    "lex": [("word",), ("vocabulary",), ("expression",)],
    "vocab_grade": [("level", "vocabulary")],
    "case_marker": [("particle",), ("case", "marker")],
    "morph_prop": [("morphology",), ("ending",)],
    "syn": [("sentence", "structure"), ("grammar",)],
    "dis_nonSBERT": [("connective",), ("cohesion",), ("paragraph", "connection")],
    "dis_SBERT": [("coherence",), ("flow",)],
    "meta": [("length",), ("word", "count")],
}
TOKEN_RE = re.compile(r"[A-Za-z_]+")

def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]

def detect_families(text: str) -> set[str]:
    tokens = tokenize(text)
    found: set[str] = set()
    for family, keywords in KEYWORD_SET.items():
        for keyword in keywords:
            n = len(keyword)
            if any(tuple(tokens[i:i+n]) == keyword for i in range(max(len(tokens)-n+1, 0))):
                found.add(family)
                break
    return found
