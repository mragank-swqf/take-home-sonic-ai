#!/usr/bin/env python3
"""Build explanation.pdf (2–3 pages, ≥10pt) from docs/explanation.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "explanation.md"
OUT = ROOT / "explanation.pdf"


def build_with_fpdf(text: str) -> int:
    from fpdf import FPDF

    class PDF(FPDF):
        def footer(self) -> None:
            self.set_y(-12)
            self.set_font("Helvetica", size=9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, f"{self.page_no()}", align="C")

    pdf = PDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_margins(16, 14, 16)

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            pdf.ln(2)
            i += 1
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 6, _safe(line[2:].strip()))
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 5.5, _safe(line[3:].strip()))
            pdf.ln(0.5)
        elif line.startswith("```"):
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            pdf.set_font("Courier", size=9)
            pdf.set_fill_color(245, 245, 245)
            pdf.multi_cell(0, 4.2, _safe("\n".join(block)), fill=True)
            pdf.ln(1)
        elif line.strip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if "---" not in lines[i]:
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    rows.append(cells)
                i += 1
            _draw_table(pdf, rows)
            continue
        elif line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 4.8, _safe(line.strip("*").strip()))
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 4.8, _safe(_inline(line)))
        i += 1

    pdf.output(str(OUT))
    return pdf.page_no()


def _draw_table(pdf, rows: list[list[str]]) -> None:
    if not rows:
        return
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols = max(len(r) for r in rows)
    widths = [usable / cols] * cols
    pdf.set_font("Helvetica", size=9)
    for r_i, row in enumerate(rows):
        # estimate height
        line_h = 4.2
        max_lines = 1
        cells = []
        for c_i in range(cols):
            cell = row[c_i] if c_i < len(row) else ""
            cell = _safe(_inline(cell))
            cells.append(cell)
            # rough wrap count
            approx = max(1, int(pdf.get_string_width(cell) / max(widths[c_i] - 1, 1)) + 1)
            max_lines = max(max_lines, approx)
        row_h = line_h * max_lines + 1
        if pdf.get_y() + row_h > pdf.h - pdf.b_margin:
            pdf.add_page()
        y0 = pdf.get_y()
        x0 = pdf.l_margin
        for c_i, cell in enumerate(cells):
            pdf.set_xy(x0 + sum(widths[:c_i]), y0)
            if r_i == 0:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_fill_color(230, 235, 232)
                pdf.rect(x0 + sum(widths[:c_i]), y0, widths[c_i], row_h, style="DF")
            else:
                pdf.set_font("Helvetica", size=9)
                pdf.rect(x0 + sum(widths[:c_i]), y0, widths[c_i], row_h, style="D")
            pdf.set_xy(x0 + sum(widths[:c_i]) + 0.8, y0 + 0.5)
            pdf.multi_cell(widths[c_i] - 1.6, line_h, cell)
        pdf.set_y(y0 + row_h)
    pdf.ln(1)


def _inline(s: str) -> str:
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    return s


def _safe(s: str) -> str:
    # Helvetica core fonts are Latin-1
    return (
        s.replace("→", "->")
        .replace("—", "-")
        .replace("–", "-")
        .replace("×", "x")
        .replace("≥", ">=")
        .replace("−", "-")
        .replace("'", "'")
        .replace(""", '"')
        .replace(""", '"')
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    text = SRC.read_text(encoding="utf-8")
    pages = build_with_fpdf(text)
    print(f"Wrote {OUT} ({pages} pages)")
    if pages < 2 or pages > 3:
        print(f"WARNING: expected 2-3 pages, got {pages}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
