"""PII masking used by logs, audit records and AI activity summaries."""

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b"), "[PHONE]"),
]

SENSITIVE_KEYS = {"password", "token", "member_id", "license_number", "ssn", "dob", "secret", "authorization"}


def mask_text(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def mask_identifier(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return "•" * len(value)
    return "•" * (len(value) - visible) + value[-visible:]


def mask_dict(data: dict) -> dict:
    out: dict = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS:
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = mask_dict(v)
        elif isinstance(v, str):
            out[k] = mask_text(v)
        else:
            out[k] = v
    return out
