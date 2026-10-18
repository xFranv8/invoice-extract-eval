"""Business-rule checks that decide whether a document goes to the human review queue."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .schema import FIELDS, Invoice

REQUIRED = ("invoice_number", "invoice_date", "supplier_name", "total")
TOLERANCE = Decimal("0.02")


def review_reasons(invoice: Invoice, notes: list[str], today: date | None = None) -> list[str]:
    """Return why this extraction should be checked by a person (empty list = auto-accept).

    Positional guesses (e.g. "supplier inferred from page position") are informational:
    they are reported in ``notes`` but do not by themselves block auto-acceptance.
    """
    today = today or date.today()
    reasons: list[str] = []

    if all(getattr(invoice, f) is None for f in FIELDS):
        return ["no text extracted (image-only PDF?): needs OCR or a vision model"]

    for name in REQUIRED:
        if getattr(invoice, name) is None:
            reasons.append(f"missing {name}")

    s, t, g = invoice.subtotal, invoice.tax_amount, invoice.total
    if None not in (s, t, g):
        if abs((s + t) - g) > TOLERANCE:
            reasons.append(f"subtotal + tax ({s + t}) != total ({g})")
    elif g is not None:
        reasons.append("cannot cross-check total (subtotal or tax missing)")

    if invoice.invoice_date and invoice.invoice_date > today:
        reasons.append("invoice date is in the future")
    if invoice.supplier_vat_id is None:
        reasons.append("no supplier VAT ID found")

    reasons.extend(n for n in notes if "not found" in n)
    return reasons
