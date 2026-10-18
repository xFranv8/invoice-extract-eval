"""Parsing helpers for the messy formats found on real invoices."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

_MONTHS = {
    # English
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
    # Spanish
    "ene": 1,
    "abr": 4,
    "ago": 8,
    "dic": 12,
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# A money token: optional sign, digits with optional thousands separators, optional decimals.
AMOUNT_RE = re.compile(
    r"(?<![\w.,])-?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?(?![\w])"
    r"|-?\d+(?:[.,]\d{2})"
)

_CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP"}
_CURRENCY_CODES = ("EUR", "USD", "GBP", "CHF")


def parse_amount(text: str) -> Decimal | None:
    """Parse '1.234,56', '1,234.56', '1 234,56', '1234.56' or '-50,00' into a Decimal.

    The decimal separator is the last '.' or ',' followed by exactly two digits.
    """
    if text is None:
        return None
    cleaned = re.sub(r"[^\d,.\-\s]", "", text).strip()
    cleaned = cleaned.replace(" ", "").replace("\u00a0", "")
    if not cleaned or not re.search(r"\d", cleaned):
        return None
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("-")
    match = re.search(r"[.,](\d{2})$", cleaned)
    if match:
        integer_part = re.sub(r"[.,]", "", cleaned[: match.start()])
        number = f"{integer_part or '0'}.{match.group(1)}"
    else:
        number = re.sub(r"[.,]", "", cleaned)
    try:
        value = Decimal(number)
    except InvalidOperation:
        return None
    return -value if negative else value


def find_amounts(line: str, require_decimals: bool = False) -> list[Decimal]:
    """All money-looking values on a line, left to right (percentages are skipped).

    With ``require_decimals`` only tokens with a two-digit decimal part count, which keeps
    article numbers, years and legal references ("Art. 196", "2006/112") out of totals.
    """
    values: list[Decimal] = []
    for match in AMOUNT_RE.finditer(line):
        if require_decimals and not re.search(r"[.,]\d{2}$", match.group(0)):
            continue
        tail = line[match.end() : match.end() + 2]
        if tail.lstrip().startswith("%"):
            continue
        value = parse_amount(match.group(0))
        if value is not None:
            values.append(value)
    return values


def parse_date(text: str) -> date | None:
    """Parse common European, ISO and English date formats. Day-first when ambiguous."""
    if not text:
        return None
    text = text.strip()
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b", text)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    # "Oct 18, 2026" / "October 18 2026"
    m = re.search(r"\b([A-Za-zé]{3,10})\.?\s+(\d{1,2}),?\s+(\d{4})\b", text)
    if m and m.group(1).lower() in _MONTHS:
        return _safe_date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    # "18 Oct 2026" / "18 de octubre de 2026"
    m = re.search(r"\b(\d{1,2})\s+(?:de\s+)?([A-Za-zé]{3,10})\.?\s+(?:de\s+)?(\d{4})\b", text)
    if m and m.group(2).lower() in _MONTHS:
        return _safe_date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def detect_currency(text: str) -> str | None:
    """Most frequent currency marker in the document text."""
    counts: dict[str, int] = {}
    for symbol, code in _CURRENCY_SYMBOLS.items():
        counts[code] = counts.get(code, 0) + text.count(symbol)
    for code in _CURRENCY_CODES:
        counts[code] = counts.get(code, 0) + len(re.findall(rf"\b{code}\b", text))
    best = max(counts.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else None


# Simplified national formats (structure only, no checksum validation).
VAT_ID_RE = re.compile(
    r"^(?:ES[A-Z0-9]\d{7}[A-Z0-9]|DE\d{9}|FR[A-Z0-9]{2}\d{9}|NL\d{9}B\d{2}"
    r"|IT\d{11}|PT\d{9}|BE[01]\d{9}|IE\d{7}[A-Z]{1,2}|AT U\d{8})$"
)


def normalize_vat_id(text: str) -> str | None:
    """First token in ``text`` that looks like an EU VAT number, e.g. 'ESB12345678'."""
    if not text:
        return None
    for token in text.upper().split():
        candidate = re.sub(r"[.\-:;,()]", "", token)
        if VAT_ID_RE.match(candidate):
            return candidate
    return None


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip(" :;,-")
    return collapsed or None
