"""Build a simple anonymized PDF from sanitized plain text.

Layout fidelity of the original client PDF is not preserved — the point for the
consultant demo is file-in / file-out: upload a PDF, download a safer PDF.
"""

from __future__ import annotations

import base64
import re
from io import BytesIO


def text_to_pdf_bytes(text: str, *, title: str = "Privilege anonymized document") -> bytes:
    """Render sanitized text to a minimal multi-page PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_title(title)
    pdf.set_author("Privilege (local)")
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, _pdf_safe(title))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0,
        5,
        "Processed by Privilege on this machine. Placeholders replace terms declared "
        "in the selected engagement policy. The check does not cover undeclared names "
        "or facts.",
    )
    pdf.ln(4)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "", 11)
    body = (text or "").strip() or "(empty)"
    for block in re.split(r"\n{2,}", body):
        line = " ".join(block.split())
        if not line:
            continue
        pdf.multi_cell(0, 6, _pdf_safe(line))
        pdf.ln(3)
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def text_to_pdf_base64(text: str, *, title: str = "Privilege anonymized document") -> str:
    return base64.b64encode(text_to_pdf_bytes(text, title=title)).decode("ascii")


def _pdf_safe(value: str) -> str:
    # Helvetica core fonts are Latin-1; drop characters that would crash output.
    return value.encode("latin-1", "replace").decode("latin-1")
