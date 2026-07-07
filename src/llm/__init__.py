"""Stage 4 — LLM 3-step explanation scaffold (plan v2.3 §4.3.1).

Three separated calls per essay-trait cell, structured JSON outputs:

    A. Evidence extraction (``evidence.py``)
    B. Scoring           (``score.py``)
    C. Rationale         (``rationale.py``)

Model provenance is recorded per-run via ``snapshot.py`` into
``reports/snapshot_registry.md`` (plan v2.3 §6.5, Appendix B).

**Execution policy** (CLAUDE.md "Out of scope for Claude Code"):
Actual LLM invocations must be run by the researcher from the shell,
not by Claude Code agents. These modules are authored and reviewed by
Claude Code but exercised only by the human.
"""
