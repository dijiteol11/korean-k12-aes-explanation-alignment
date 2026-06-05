from __future__ import annotations

def require_keys(obj: dict, keys: set[str]) -> None:
    missing = keys - set(obj)
    if missing:
        raise ValueError(f"missing required keys: {sorted(missing)}")

def validate_rationale_text(text: str, *, max_chars: int = 240) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("rationale text must be a non-empty string")
    if len(text) > max_chars:
        raise ValueError(f"rationale text exceeds {max_chars} characters")
