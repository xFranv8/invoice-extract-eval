"""Field definitions shared by extractors, validation and evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal

# Order matters: it is the column order in reports and spreadsheets.
FIELDS: tuple[str, ...] = (
    "invoice_number",
    "invoice_date",
    "supplier_name",
    "supplier_vat_id",
    "customer_name",
    "currency",
    "subtotal",
    "tax_amount",
    "total",
)

MONEY_FIELDS = frozenset({"subtotal", "tax_amount", "total"})
DATE_FIELDS = frozenset({"invoice_date"})


@dataclass
class Invoice:
    """Normalised invoice fields. ``None`` means "not found"."""

    invoice_number: str | None = None
    invoice_date: date | None = None
    supplier_name: str | None = None
    supplier_vat_id: str | None = None
    customer_name: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    total: Decimal | None = None

    def to_jsonable(self) -> dict[str, str | None]:
        out: dict[str, str | None] = {}
        for key, value in asdict(self).items():
            out[key] = None if value is None else str(value)
        return out

    @classmethod
    def from_jsonable(cls, data: dict[str, str | None]) -> Invoice:
        kwargs: dict[str, object] = {}
        for key in FIELDS:
            raw = data.get(key)
            if raw is None or raw == "":
                kwargs[key] = None
            elif key in MONEY_FIELDS:
                kwargs[key] = Decimal(raw)
            elif key in DATE_FIELDS:
                kwargs[key] = date.fromisoformat(raw)
            else:
                kwargs[key] = raw
        return cls(**kwargs)  # type: ignore[arg-type]


@dataclass
class ExtractionResult:
    """What an extractor returns for one document."""

    source: str
    invoice: Invoice
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
