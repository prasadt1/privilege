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


# The same client name can be written so it reads as its declared form but does
# not match it byte for byte: lowercased, split across a PDF line break, run
# together, padded, in fullwidth or small-capital glyphs, spelled with a
# Cyrillic or Greek lookalike letter, or carrying an invisible formatting
# character. Matching runs on a folded form that neutralizes all of these, while
# replacement splices the original string so unmatched text keeps its exact
# bytes, accents, and layout.
#
# Two rules below are category based rather than enumerated, so they are
# complete for their class instead of a list that a new code point can slip
# past:
#   - every format and control character (Cf, and Cc that is not whitespace) is
#     removed, which covers zero-width spaces, bidi marks, the tag block, and
#     invisible math operators;
#   - every combining mark (Mn, Mc, Me) is removed, which strips accents and
#     the marks used to disguise a letter.
#
# Cross-script lookalikes cannot be derived by category and are listed. This is
# the common subset, not the full Unicode confusables table; see MASKING LIMITS
# in the README.
_STRIP_CATEGORIES = frozenset({"Cf", "Mn", "Mc", "Me"})

_CONFUSABLES = {
    # Cyrillic
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X", "І": "I", "Ј": "J",
    "Ѕ": "S", "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h",
    "о": "o", "р": "p", "с": "c", "т": "t", "у": "y", "х": "x", "і": "i",
    "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h", "ԛ": "q", "ԝ": "w",
    # Greek
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    "α": "a", "ε": "e", "ι": "i", "ο": "o", "ρ": "p", "τ": "t", "υ": "u",
    "ν": "v", "κ": "k", "ϲ": "c", "ϳ": "j",
    # Armenian
    "օ": "o", "օ".upper(): "O", "ս": "u", "ց": "g", "ի": "h", "ո": "n",
    # Cherokee (visually Latin capitals)
    "Ꭺ": "A", "Ᏼ": "B", "Ꮯ": "C", "Ꭼ": "E", "Ꮐ": "G", "Ꭹ": "y", "Ꮋ": "H",
    "Ꭻ": "J", "Ꮶ": "K", "Ꮮ": "L", "Ꮇ": "M", "Ꮲ": "P", "Ꮢ": "R", "Ꮪ": "S",
    "Ꭲ": "I", "Ꭵ": "i", "Ꮤ": "W", "Ꮓ": "Z", "Ꮷ": "d", "Ꮙ": "V",
    # Coptic
    "Ⲥ": "C", "ⲥ": "c", "Ⲟ": "O", "ⲟ": "o", "Ⲣ": "P", "ⲣ": "p", "Ⲧ": "T",
    "Ⲏ": "H", "Ⲕ": "K", "Ⲙ": "M", "Ⲛ": "N", "Ⲭ": "X",
}


def _latin_letter_from_name(char: str) -> str:
    """Recover the Latin letter a stylised code point stands in for.

    Small-capital, modifier, phonetic, and similar Latin-block glyphs decompose
    to nothing under NFKD but their Unicode name ends in the letter they draw,
    e.g. "LATIN LETTER SMALL CAPITAL A" or "LATIN SMALL LETTER SCRIPT G". This
    catches that whole class without listing every code point.
    """
    name = unicodedata.name(char, "")
    if not name.startswith("LATIN "):
        return ""
    last = name.rsplit(" ", 1)[-1]
    return last.lower() if len(last) == 1 and last.isalpha() and last.isascii() else ""


def _fold_char(char: str) -> str:
    """Reduce one character to the letter a reader would recognise it as.

    Returns "" for a character that carries no readable letter (an invisible
    format character or a combining mark), otherwise the folded letters.
    """
    category = unicodedata.category(char)
    if category in _STRIP_CATEGORIES:
        return ""
    if category == "Cc" and char not in "\t\n\r\f\v":
        return ""
    if char in _CONFUSABLES:
        return _CONFUSABLES[char]
    # NFKD turns fullwidth and accented letters into a base letter plus marks;
    # the marks are dropped as combining characters on the recursion.
    decomposed = unicodedata.normalize("NFKD", char)
    if decomposed != char:
        return "".join(_fold_char(component) for component in decomposed)
    return _latin_letter_from_name(char) or char


def _fold(text: str) -> tuple[str, list[int]]:
    """Fold text for matching, recording each folded character's source index.

    Matching happens on the folded form so a lookalike or an invisible
    character cannot hide a declared name. Replacement uses these indices to
    splice the original string, so a document keeps its accents and spacing
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
    if not folded:
        return text, 0

    pieces: list[str] = []
    cursor = 0
    count = 0
    for match in _value_pattern(real_value).finditer(folded):
        lo, hi = match.start(), match.end()
        # Require the match to begin and end on a source-character boundary. A
        # single glyph can fold to several characters (℃ -> "°C"); matching part
        # of one and splicing the whole glyph would delete the rest, e.g. the
        # degree sign. Skip a match that starts or ends inside an expansion.
        if lo > 0 and source_index[lo] == source_index[lo - 1]:
            continue
        if hi < len(source_index) and source_index[hi] == source_index[hi - 1]:
            continue
        start = source_index[lo]
        end = source_index[hi - 1] + 1
        if start < cursor:
            # Overlapping spans cannot both be replaced; keep the first.
            continue
        pieces.append(text[cursor:start])
        pieces.append(placeholder)
        cursor = end
        count += 1
    if not count:
        return text, 0
    pieces.append(text[cursor:])
    return "".join(pieces), count


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
