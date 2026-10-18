"""Turn a PDF page into reading-order lines split into visual segments (columns).

Plain ``extract_text()`` glues side-by-side blocks together ("Issue date: Jul 23 Bill to").
Splitting a line wherever the horizontal gap between words is large keeps those blocks apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

LINE_TOLERANCE = 3.0  # points: words whose tops differ less than this share a line
COLUMN_GAP = 28.0  # points (~10 mm): a wider gap starts a new segment


@dataclass
class Segment:
    x0: float
    text: str


@dataclass
class TextLine:
    top: float
    segments: list[Segment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments)


def read_lines(pdf_path: Path) -> tuple[list[TextLine], float]:
    """Return lines of the first page (top to bottom) and the page height."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
        height = float(page.height)
    words.sort(key=lambda w: (round(w["top"]), w["x0"]))

    rows: list[list[dict]] = []
    for word in words:
        if rows and abs(rows[-1][0]["top"] - word["top"]) <= LINE_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])

    lines: list[TextLine] = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        line = TextLine(top=float(row[0]["top"]))
        current: list[dict] = [row[0]]
        for prev, word in zip(row, row[1:], strict=False):
            if word["x0"] - prev["x1"] > COLUMN_GAP:
                line.segments.append(_segment(current))
                current = []
            current.append(word)
        line.segments.append(_segment(current))
        lines.append(line)
    return lines, height


def _segment(words: list[dict]) -> Segment:
    return Segment(x0=float(words[0]["x0"]), text=" ".join(w["text"] for w in words))
