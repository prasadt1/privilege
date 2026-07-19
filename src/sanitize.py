"""Deterministic local sanitization. This module never calls cloud services."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SanitizeResult:
    text: str
    applied: list[dict[str, str]]


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# A plus-prefixed international number or a hyphenated local number. Requiring
# this signal prevents a spaced card run from being consumed before CARD_RE.
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[ .-]?\d{2,4}[ .-]\d{3,4}[ .-]\d{3,4}|\(?\d{2,4}\)?-\d{3,4}-\d{3,4})(?!\w)"
)
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}\d(?!\d)")


def sanitize(text: str, mappings: dict[str, str]) -> SanitizeResult:
    """Mask declared local values first, then common PII in deterministic order."""
    result = text
    applied: list[dict[str, str]] = []

    for real_value in sorted(mappings, key=len, reverse=True):
        placeholder = mappings[real_value]
        if real_value and real_value in result:
            result = result.replace(real_value, placeholder)
            applied.append({"real": real_value, "placeholder": placeholder})

    for pattern, placeholder in (
        (EMAIL_RE, "[EMAIL]"),
        (PHONE_RE, "[PHONE]"),
        (CARD_RE, "[CARD]"),
    ):
        def replace(match: re.Match[str]) -> str:
            applied.append({"real": match.group(0), "placeholder": placeholder})
            return placeholder

        result = pattern.sub(replace, result)

    return SanitizeResult(text=result, applied=applied)


def restore(sanitized_text: str, mappings: dict[str, str]) -> str:
    """Restore declared placeholders locally; regex-masked PII is intentionally absent."""
    result = sanitized_text
    inverse = {placeholder: real for real, placeholder in mappings.items()}
    for placeholder in sorted(inverse, key=len, reverse=True):
        result = result.replace(placeholder, inverse[placeholder])
    return result
