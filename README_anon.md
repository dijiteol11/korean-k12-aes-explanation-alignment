cat > /c/project/NIA/plan_D/README_anon.md << 'EOF'
# Korean K-12 AES Explanation Alignment — Anonymous Reproducibility Package

Anonymized package for double-blind review: analysis code (src/, scripts/, configs/),
pre-specified documents (prereg/ — see prereg/REDACTION_NOTE.md for the anonymization
protocol and SHA-256 verification), redacted audit reports (reports/), blind-audit
coder files (audit/), and Figure 1 (figures/). Raw essays, model outputs (jsonl),
prompts, and identity-bearing originals are excluded; originals will be disclosed
upon publication. Verify: `sha256sum prereg/*.md` against prereg/REDACTION_NOTE.md.
License: MIT (see LICENSE).
