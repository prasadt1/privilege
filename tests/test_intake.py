"""Local file intake tests.

Written outside Codex after the Codex quota was exhausted.
"""

import pytest

from src.intake import (
    DocumentExtractionError,
    UnsupportedDocumentError,
    extract_text,
)


def test_reads_plain_text(tmp_path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("Northwind Freight operates 14 depots.")
    assert "14 depots" in extract_text(path)


def test_reads_markdown(tmp_path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# Heading\n\nBaltic corridor volumes fell 22%.")
    assert "22%" in extract_text(path)


def test_reads_docx_paragraphs_and_tables(tmp_path) -> None:
    docx = pytest.importorskip("docx")
    path = tmp_path / "brief.docx"
    document = docx.Document()
    document.add_paragraph("Northwind Freight operating review.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Corridor"
    table.rows[0].cells[1].text = "Baltic"
    document.save(str(path))

    text = extract_text(path)
    assert "Northwind Freight operating review." in text
    assert "Corridor | Baltic" in text


def test_reads_pdf(tmp_path) -> None:
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)

    # A blank page yields no text, which must be refused rather than imported
    # as an empty document.
    with pytest.raises(DocumentExtractionError):
        extract_text(path)


def test_planned_format_says_not_yet(tmp_path) -> None:
    path = tmp_path / "model.xlsx"
    path.write_bytes(b"not really a spreadsheet")
    with pytest.raises(UnsupportedDocumentError) as error:
        extract_text(path)
    assert "not supported yet" in str(error.value)


def test_unknown_format_is_refused(tmp_path) -> None:
    path = tmp_path / "archive.zip"
    path.write_bytes(b"PK")
    with pytest.raises(UnsupportedDocumentError):
        extract_text(path)


def test_missing_file_is_refused(tmp_path) -> None:
    with pytest.raises(DocumentExtractionError):
        extract_text(tmp_path / "nope.txt")
