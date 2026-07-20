"""Deterministic local sanitization. This module never calls cloud services."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


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


# Invisible characters that split a name without changing how it reads.
_ZERO_WIDTH = frozenset("​‌‍⁠﻿­")

# Cyrillic and Greek letters that render as Latin ones. A name containing any
# of these reads identically to its ASCII form but never matched it. This is
# the common subset, not the full Unicode confusables table.
_CONFUSABLES = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X", "І": "I", "Ј": "J",
    "Ѕ": "S", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",
    "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    "α": "a", "ε": "e", "ι": "i", "ο": "o", "ρ": "p", "τ": "t", "υ": "u",
    "ν": "v", "κ": "k",
})


def _fold_char(char: str) -> str:
    """Reduce one character to the form a reader would recognise it as.

    Applies compatibility normalization (fullwidth and other presentation
    forms), maps Cyrillic and Greek lookalikes to Latin, drops combining
    marks, and removes zero-width characters entirely.
    """
    if char in _ZERO_WIDTH:
        return ""
    folded = unicodedata.normalize("NFKC", char).translate(_CONFUSABLES)
    without_marks = "".join(
        component
        for component in unicodedata.normalize("NFD", folded)
        if unicodedata.category(component) != "Mn"
    )
    return unicodedata.normalize("NFC", without_marks)


def _fold(text: str) -> tuple[str, list[int]]:
    """Fold text for matching, keeping each folded character's source index.

    Matching happens on the folded form so a lookalike or an invisible
    character cannot hide a declared name. Replacement happens on the original
    string using these indices, so a document keeps its accents and spacing
    everywhere it was not masked.
    """
    folded: list[str] = []
    source_index: list[int] = []
    for index, char in enumerate(text):
        for component in _fold_char(char):
            folded.append(component)
            source_index.append(index)
    return "".join(folded), source_index


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
    folded_value, _ = _fold(real_value)
    words = [re.escape(word) for word in folded_value.split()]
    if not words:
        # A value made only of invisible characters would otherwise compile to
        # an empty pattern that matches everywhere.
        return re.compile(r"(?!)")
    # \s* rather than \s+ so "NorthwindFreight" is caught alongside a name
    # broken over two lines.
    body = r"\s*".join(words)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def _mask_value(text: str, real_value: str, placeholder: str) -> tuple[str, int]:
    """Replace every occurrence of one declared value, returning (text, count).

    Occurrences are located in the folded text and spliced out of the original,
    so characters outside a match are returned exactly as written.
    """
    folded, source_index = _fold(text)
    matches = list(_value_pattern(real_value).finditer(folded))
    if not matches:
        return text, 0

    pieces: list[str] = []
    cursor = 0
    for match in matches:
        start = source_index[match.start()]
        end = source_index[match.end() - 1] + 1
        if start < cursor:
            # Overlapping spans cannot both be replaced; keep the first.
            continue
        pieces.append(text[cursor:start])
        pieces.append(placeholder)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), len(matches)


def sanitize(text: str, mappings: dict[str, str]) -> SanitizeResult:
    """Mask declared local values first, then common PII in deterministic order."""
    result = text
    applied: list[dict[str, str]] = []

    for real_value in sorted(mappings, key=len, reverse=True):
        placeholder = mappings[real_value]
        if not real_value:
            continue
        result, count = _mask_value(result, real_value, placeholder)
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
