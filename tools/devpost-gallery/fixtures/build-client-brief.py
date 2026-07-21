#!/usr/bin/env python3
"""Build a denser demo client PDF for gallery / judge walkthroughs.

Keeps Northwind Freight + Baltic corridor facts so the restructuring template
and demo attacker still have material to work with. Layout is consulting-memo
style, not a one-paragraph stub.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[2]
OUT_PDF = Path(__file__).resolve().parent / "client-brief.pdf"
OUT_TXT = Path(__file__).resolve().parent / "engagement_notes.txt"


class BriefPDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 5, "Northwind Freight  |  Operating review  |  CONFIDENTIAL", align="L")
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}  |  Internal use only", align="C")


def _safe(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


def h1(pdf: BriefPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(25, 25, 25)
    pdf.multi_cell(0, 8, _safe(text))
    pdf.ln(2)


def h2(pdf: BriefPDF, text: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(35, 35, 35)
    pdf.multi_cell(0, 7, _safe(text))
    pdf.ln(1)


def body(pdf: BriefPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5.2, _safe(text))
    pdf.ln(2)


def bullet(pdf: BriefPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.set_x(pdf.l_margin + 4)
    pdf.multi_cell(0, 5.2, _safe(f"-  {text}"))
    pdf.ln(1)


def meta_row(pdf: BriefPDF, label: str, value: str) -> None:
    x0 = pdf.l_margin
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(x0)
    pdf.cell(38, 5, _safe(label), new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(pdf.epw - 38, 5, _safe(value))


def rule(pdf: BriefPDF) -> None:
    y = pdf.get_y()
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(4)


PLAIN_TEXT = """\
NORTHWIND FREIGHT - OPERATING REVIEW (CONFIDENTIAL)
Prepared for: Board operating committee
Date: 14 July 2026
Classification: Client confidential - do not forward outside engagement team

1. Purpose
This note summarises cost pressure and network options for Northwind Freight ahead of the Q3 board discussion. It is not a public announcement and must not be treated as a decision to exit any corridor.

2. Network snapshot
Northwind Freight operates 14 depots across Northern and Central Europe. The Baltic corridor accounts for roughly one fifth of lane-km and a disproportionate share of lease and empty-return cost. Baltic corridor volumes fell 22% year on year. Depot leases in that corridor expire in Q3. The board has not yet announced any change to the corridor.

3. Cost structure (indicative)
- Depot leases and site security: rising ahead of renewals on Baltic corridor sites.
- Empty repositioning: higher empty-km on eastbound return legs.
- Labour and overtime: overtime spikes on peak Baltic corridor sailings.
- Fuel and tolls: corridor-specific surcharge volatility.

4. Options under review (not decided)
A. Hold network - renew Baltic corridor leases on current footprint; accept margin compression.
B. Reshape - consolidate two smaller Baltic corridor depots into a hub-and-spoke pattern; retain commercial coverage.
C. Withdraw - exit selected Baltic corridor lanes after lease expiry; reallocate equipment to higher-yield lanes.

Northwind Freight withdrawing from the Baltic corridor is protected until the client announces it. No option has been approved. Management has asked for an external cost and risk view only.

5. Timing
- Lease notices: mid-Q3 for several Baltic corridor sites.
- Board pack: circulating for the late-Q3 operating committee.
- External counsel / landlord discussions: not started for Option C.

6. Ask of external AI assistance (after local preflight)
Summarise depot cost structure, flag timing risks around lease expiry, and draft questions the operating committee should put to management - without naming the client or implying a decided exit.
"""


def build_pdf() -> bytes:
    pdf = BriefPDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    pdf.set_fill_color(245, 240, 230)
    pdf.rect(0, 0, pdf.w, 28, "F")
    pdf.set_xy(18, 8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(120, 70, 20)
    pdf.cell(0, 6, "CONFIDENTIAL  |  ENGAGEMENT WORKING PAPER")
    pdf.ln(10)

    h1(pdf, "Northwind Freight - Operating review")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(0, 5, "Depot cost structure, Baltic corridor pressure, and options for the Q3 board pack")
    pdf.ln(3)
    rule(pdf)

    meta_row(pdf, "Prepared for", "Board operating committee")
    meta_row(pdf, "Prepared by", "Engagement team (working draft)")
    meta_row(pdf, "Date", "14 July 2026")
    meta_row(pdf, "Status", "Draft for discussion - not a board decision")
    meta_row(pdf, "Distribution", "Engagement team only; do not forward to client distribution lists")
    pdf.ln(2)
    rule(pdf)

    h2(pdf, "1. Purpose of this note")
    body(
        pdf,
        "This working paper frames the cost and timing questions Northwind Freight faces on "
        "its Northern European network. The intent is to support a structured discussion at "
        "the late-Q3 operating committee. Nothing in this note constitutes a public announcement, "
        "a landlord notice, or a commitment to exit any lane or depot.",
    )

    h2(pdf, "2. Network snapshot")
    body(
        pdf,
        "Northwind Freight operates 14 depots across Northern and Central Europe. Throughput "
        "is concentrated on a small set of corridors; the Baltic corridor accounts for roughly "
        "one fifth of lane-kilometres and a disproportionate share of lease and empty-return cost. "
        "Baltic corridor volumes fell 22% year on year. Depot leases in that corridor expire in Q3. "
        "The board has not yet announced any change to the corridor.",
    )
    body(
        pdf,
        "Local management reports rising empty repositioning on eastbound return legs and "
        "overtime spikes on peak Baltic corridor sailings. Fuel and toll surcharges on the "
        "corridor have been more volatile than the network average over the last four quarters.",
    )

    h2(pdf, "3. Indicative cost pressure")
    bullet(pdf, "Depot leases and site security - renewal risk concentrated on Baltic corridor sites.")
    bullet(pdf, "Empty repositioning - higher empty-km versus prior year on the same corridor.")
    bullet(pdf, "Labour and overtime - peak-day overtime above plan on Baltic corridor hubs.")
    bullet(pdf, "Fuel and tolls - corridor-specific surcharge volatility versus network average.")
    body(
        pdf,
        "Figures in the full pack remain indicative until finance closes the Q2 flash. For this "
        "note, the material point is direction and timing: volume decline plus near-term lease "
        "expiry creates a decision window before Northwind Freight must signal renewals.",
    )

    pdf.add_page()
    h2(pdf, "4. Options under review (none decided)")
    body(
        pdf,
        "Three options are framed for discussion. They are deliberately ordered from least to "
        "most disruptive. Northwind Freight withdrawing from the Baltic corridor is protected "
        "until the client announces it. No option has been approved by the board.",
    )
    bullet(
        pdf,
        "Option A - Hold network. Renew Baltic corridor leases on the current footprint; "
        "accept near-term margin compression while volumes recover or pricing resets.",
    )
    bullet(
        pdf,
        "Option B - Reshape. Consolidate two smaller Baltic corridor depots into a hub-and-spoke "
        "pattern; retain commercial coverage with a smaller fixed-cost base.",
    )
    bullet(
        pdf,
        "Option C - Withdraw selected lanes. Exit selected Baltic corridor lanes after lease "
        "expiry; reallocate equipment and crews to higher-yield lanes. Requires landlord and "
        "works-council sequencing that has not started.",
    )
    body(
        pdf,
        "Management has asked only for an external cost and risk view. Landlord outreach, "
        "customer communication, and works-council consultation remain internal and unstarted "
        "for Option C.",
    )

    h2(pdf, "5. Timing and decision gates")
    bullet(pdf, "Mid-Q3 - lease notice windows open for several Baltic corridor sites.")
    bullet(pdf, "Late Q3 - board operating committee pack circulates.")
    bullet(pdf, "Post-committee - any customer or landlord messaging only after formal decision.")
    body(
        pdf,
        "If Option C remains live into the notice window, Northwind Freight will need a clear "
        "sequence for which sites renew, which reshape, and which wind down - and a consistent "
        "external narrative. Premature disclosure of a withdrawal would be material to counterparties.",
    )

    h2(pdf, "6. Suggested asks for AI-assisted analysis (after local preflight)")
    body(
        pdf,
        "Once this brief has been masked and attack-verified locally, useful prompts for an "
        "external model include:",
    )
    bullet(pdf, "Summarise the depot cost structure and where timing risk concentrates.")
    bullet(pdf, "List questions the operating committee should put to management on Options A-C.")
    bullet(pdf, "Draft a risk register entry for lease-expiry sequencing without naming the client.")
    body(
        pdf,
        "Do not ask an external model to identify the client, map the corridor to a real operator, "
        "or draft customer-facing exit language from this draft.",
    )

    rule(pdf)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0,
        4.5,
        _safe(
            "End of working paper. Synthetic engagement content for Privilege demos - "
            "not a real client document. Names and corridor facts are invented for the hackathon."
        ),
    )
    return bytes(pdf.output())


def main() -> None:
    OUT_TXT.write_text(PLAIN_TEXT)
    OUT_PDF.write_bytes(build_pdf())
    print(f"Wrote {OUT_PDF} ({OUT_PDF.stat().st_size} bytes)")
    print(f"Wrote {OUT_TXT} ({OUT_TXT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
