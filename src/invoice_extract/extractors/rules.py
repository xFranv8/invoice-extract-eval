"""Deterministic, offline extractor: label anchors + layout-aware lookups.

No network, no API key. It is the baseline every LLM pipeline should beat, and in
production it doubles as a cheap first pass whose output an LLM only has to confirm.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..normalize import (
    detect_currency,
    find_amounts,
    normalize_text,
    normalize_vat_id,
    parse_date,
)
from ..pdf_text import Segment, TextLine, read_lines
from ..schema import Invoice

_NUMBER_LABEL = re.compile(
    r"(invoice\s*(?:no\.?|number|#)|n[º°o]\.?\s*(?:de\s*)?factura|factura\s*n[º°o]\.?|^invoice\b|^factura\b)",
    re.IGNORECASE,
)
_NUMBER_TOKEN = re.compile(r"^[A-Z0-9][A-Z0-9\-/.]*\d[A-Z0-9\-/.]*$", re.IGNORECASE)
_DATE_LABEL = re.compile(
    r"(fecha(?:\s+de\s+(?:emisi[oó]n|factura))?|issue\s*date|invoice\s*date|date\s+of\s+issue|^date\b)",
    re.IGNORECASE,
)
_DUE_LABEL = re.compile(r"(due|vencimiento)", re.IGNORECASE)
_CUSTOMER_LABEL = re.compile(
    r"^(cliente|customer|bill(?:ed)?\s+to|facturar\s+a|sold\s+to)\b\s*:?", re.IGNORECASE
)
_SUBTOTAL_LABEL = re.compile(
    r"(base\s+imponible|subtotal|total\s+net|\bnet\b|\bneto\b)", re.IGNORECASE
)
_TAX_LABEL = re.compile(r"(\biva\b|\bvat\b|\btax\b|impuesto)", re.IGNORECASE)
_TOTAL_LABEL = re.compile(
    r"(total\s+due|amount\s+due|gross\s+total|importe\s+total|total\s+factura|^total\b)",
    re.IGNORECASE,
)
_TITLE_WORDS = re.compile(r"^(invoice|factura|bill|receipt|recibo)\b", re.IGNORECASE)
_LABELISH = re.compile(r"(:|\b(cif|nif|vat|tel|email|www)\b)", re.IGNORECASE)


class RulesExtractor:
    name = "rules"

    def extract(self, pdf_path: Path) -> tuple[Invoice, list[str]]:
        lines, _height = read_lines(Path(pdf_path))
        notes: list[str] = []
        full_text = "\n".join(line.text for line in lines)

        invoice = Invoice(
            invoice_number=self._invoice_number(lines),
            invoice_date=self._invoice_date(lines),
            supplier_vat_id=normalize_vat_id(full_text),
            currency=detect_currency(full_text),
        )
        invoice.supplier_name, supplier_note = self._supplier_name(lines)
        if supplier_note:
            notes.append(supplier_note)
        invoice.customer_name = self._customer_name(lines)
        invoice.subtotal, invoice.tax_amount, invoice.total = self._amounts(lines)
        return invoice, notes

    # -- identifiers -------------------------------------------------------------------

    @staticmethod
    def _value_after_label(line: TextLine, idx: int, match: re.Match) -> str:
        """Text after the label in the same segment, or the next segment on the line."""
        rest = line.segments[idx].text[match.end() :].strip(" :#")
        if rest:
            return rest
        if idx + 1 < len(line.segments):
            return line.segments[idx + 1].text
        return ""

    def _invoice_number(self, lines: list[TextLine]) -> str | None:
        for line in lines:
            for idx, seg in enumerate(line.segments):
                m = _NUMBER_LABEL.search(seg.text)
                if not m:
                    continue
                for token in self._value_after_label(line, idx, m).split():
                    token = token.strip(":,;")
                    if _NUMBER_TOKEN.match(token):
                        return token
        return None

    def _invoice_date(self, lines: list[TextLine]) -> object:
        for line in lines:
            for idx, seg in enumerate(line.segments):
                m = _DATE_LABEL.search(seg.text)
                if not m or _DUE_LABEL.search(seg.text[: m.end()]):
                    continue
                parsed = parse_date(self._value_after_label(line, idx, m))
                if parsed:
                    return parsed
        return None

    # -- parties -----------------------------------------------------------------------

    def _supplier_name(self, lines: list[TextLine]) -> tuple[str | None, str | None]:
        """Issuer is usually the first plain text block at the top of the page."""
        for line in lines[:8]:
            for seg in line.segments:
                text = seg.text.strip()
                if (
                    _TITLE_WORDS.match(text)
                    or _LABELISH.search(text)
                    or re.search(r"\d", text)
                    or len(text) < 3
                ):
                    continue
                return normalize_text(text), "supplier_name inferred from page position"
        return None, "supplier_name not found"

    def _customer_name(self, lines: list[TextLine]) -> str | None:
        for li, line in enumerate(lines):
            for idx, seg in enumerate(line.segments):
                m = _CUSTOMER_LABEL.search(seg.text)
                if not m:
                    continue
                same = self._value_after_label(line, idx, m)
                if same and re.search(r"[A-Za-z]", same) and not normalize_vat_id(same):
                    return normalize_text(same)
                below = self._segment_below(lines, li, seg)
                if below:
                    return normalize_text(below.text)
        return None

    @staticmethod
    def _segment_below(lines: list[TextLine], li: int, anchor: Segment) -> Segment | None:
        for line in lines[li + 1 : li + 3]:
            for seg in line.segments:
                if abs(seg.x0 - anchor.x0) < 20:
                    return seg
        return None

    # -- money -------------------------------------------------------------------------

    def _amounts(self, lines: list[TextLine]):
        subtotal = tax = total = None
        for line in lines:
            text = line.text
            amounts = find_amounts(text, require_decimals=True)
            if not amounts:
                continue
            value = amounts[-1]
            if _TOTAL_LABEL.search(text) and not _SUBTOTAL_LABEL.search(text):
                total = value
            elif _SUBTOTAL_LABEL.search(text):
                subtotal = value
            elif _TAX_LABEL.search(text) and not normalize_vat_id(text):
                tax = value
        return subtotal, tax, total
