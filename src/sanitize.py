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


def _value_pattern(real_value: str) -> re.Pattern[str]:
    """Build a tolerant matcher for one declared value.

    A literal, case-sensitive match is not enough for real documents. The same
    client name appears lowercased in prose, split across a line break by PDF
    text extraction, run together when a layout drops the space, or padded with
    extra whitespace. Each of those previously passed straight through to the
    model as a real name.

    Word boundaries keep a short declared value such as "port" from being
    masked inside "important".
    """
    words = [re.escape(word) for word in real_value.split()]
    # \s* rather than \s+ so "NorthwindFreight" is caught alongside a name
    # broken over two lines.
    body = r"\s*".join(words)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def sanitize(text: str, mappings: dict[str, str]) -> SanitizeResult:
    """Mask declared local values first, then common PII in deterministic order."""
    result = text
    applied: list[dict[str, str]] = []

    for real_value in sorted(mappings, key=len, reverse=True):
        placeholder = mappings[real_value]
        if not real_value:
            continue
        result, count = _value_pattern(real_value).subn(placeholder, result)
        if count:
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
