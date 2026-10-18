"""Synthetic invoice generator with ground truth.

Every company name, person and VAT number here is invented at random. The layouts imitate
the variety seen in real supplier invoices: different languages, label wording, number and
date formats, discount/shipping lines, and a "Total" column header that is not the total.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .schema import Invoice

LAYOUTS = ("classic_es", "modern_en", "compact_codes", "reverse_charge_eu")
# Written after the rules extractor was frozen. Results on it are reported as-is, untuned.
HELD_OUT_LAYOUTS = ("held_out_vendor",)

_SUPPLIER_PREFIX = ["Talleres", "Suministros", "Ingeniería", "Distribuciones", "Servicios"]
_SUPPLIER_CORE = ["Albor", "Nexo", "Cierzo", "Lumen", "Brújula", "Orbe", "Tajo", "Vértice"]
_SUPPLIER_SUFFIX = ["S.L.", "S.A.", "SLU"]
_EN_SUPPLIERS = [
    "Northgate Components Ltd",
    "Bluefin Analytics BV",
    "Kestrel Tooling GmbH",
    "Harbor Line Logistics",
    "Quillstone Software SAS",
    "Ridgeway Parts Ltd",
]
_CUSTOMERS = [
    "Mecanizados Duero S.L.",
    "Grupo Alcor Retail S.A.",
    "Agroveg Levante S.Coop.",
    "Rivet & Bolt Trading Ltd",
    "Puerto Seco Logística S.L.",
    "Nimbus Field Ops BV",
]
_ITEMS_ES = [
    "Rodamiento 6204-2RS",
    "Horas de mantenimiento",
    "Cable apantallado 4x1,5 (m)",
    "Sensor inductivo M12",
    "Licencia anual software",
    "Transporte palé",
]
_ITEMS_EN = [
    "Consulting hours",
    "Bracket kit A-12",
    "Cloud hosting (monthly)",
    "Calibration service",
    "Spare belt 1220mm",
    "Annual support plan",
]
_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CENT = Decimal("0.01")
_REVERSE_CHARGE_NOTE = (
    "Reverse charge: VAT to be accounted for by the recipient (Art. 196 Directive 2006/112/EC)."
)


def _en_date(d: date) -> str:
    return f"{_MONTHS_EN[d.month - 1]} {d.day}, {d.year}"


@dataclass
class Line:
    description: str
    qty: int
    unit_price: Decimal

    @property
    def amount(self) -> Decimal:
        return (self.unit_price * self.qty).quantize(CENT, ROUND_HALF_UP)


def _eu(value: Decimal) -> str:
    """1234.5 -> '1.234,50'"""
    s = f"{value:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _us(value: Decimal) -> str:
    return f"{value:,.2f}"


def _vat_id(rng: random.Random, country: str) -> str:
    if country == "ES":
        return f"ES{rng.choice('ABG')}{rng.randint(10_000_000, 99_999_999)}"
    if country == "NL":
        return f"NL{rng.randint(100_000_000, 999_999_999)}B01"
    if country == "DE":
        return f"DE{rng.randint(100_000_000, 999_999_999)}"
    return f"FR{rng.randint(10, 99)}{rng.randint(100_000_000, 999_999_999)}"


def _lines(rng: random.Random, items: list[str]) -> list[Line]:
    return [
        Line(rng.choice(items), rng.randint(1, 12), Decimal(rng.randint(500, 90_000)) / 100)
        for _ in range(rng.randint(2, 5))
    ]


def _draw_table(c: Canvas, y: float, lines: list[Line], fmt, headers: tuple[str, ...]) -> float:
    xs = (20 * mm, 120 * mm, 140 * mm, 170 * mm)
    c.setFont("Helvetica-Bold", 9)
    for x, h in zip(xs, headers, strict=True):
        c.drawString(x, y, h)
    c.line(20 * mm, y - 2 * mm, 190 * mm, y - 2 * mm)
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    for ln in lines:
        c.drawString(xs[0], y, ln.description)
        c.drawString(xs[1], y, str(ln.qty))
        c.drawString(xs[2], y, fmt(ln.unit_price))
        c.drawString(xs[3], y, fmt(ln.amount))
        y -= 6 * mm
    return y


def generate_one(path: Path, layout: str, seed: int) -> Invoice:
    """Render one invoice PDF to ``path`` and return its ground truth."""
    rng = random.Random(seed)
    issue = date(2026, 1, 1) + timedelta(days=rng.randint(0, 280))
    c = Canvas(str(path), pagesize=A4)
    width, height = A4
    top = height - 20 * mm

    if layout == "classic_es":
        supplier = " ".join(
            rng.choice(part) for part in (_SUPPLIER_PREFIX, _SUPPLIER_CORE, _SUPPLIER_SUFFIX)
        )
        vat = _vat_id(rng, "ES")
        customer = rng.choice(_CUSTOMERS)
        number = f"F-{issue.year}-{rng.randint(1, 9999):04d}"
        lines = _lines(rng, _ITEMS_ES)
        discount = Decimal(rng.choice([0, 0, 25, 50])).quantize(CENT)
        subtotal = sum((ln.amount for ln in lines), Decimal(0)) - discount
        rate = Decimal(rng.choice([21, 21, 10]))
        tax = (subtotal * rate / 100).quantize(CENT, ROUND_HALF_UP)
        total = subtotal + tax
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20 * mm, top, supplier)
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, top - 6 * mm, f"CIF: {vat}")
        c.drawString(20 * mm, top - 11 * mm, "C/ Inventada 12, 50001 Zaragoza")
        c.setFont("Helvetica-Bold", 18)
        c.drawString(140 * mm, top, "FACTURA")
        c.setFont("Helvetica", 10)
        c.drawString(140 * mm, top - 8 * mm, f"Nº Factura: {number}")
        c.drawString(140 * mm, top - 14 * mm, f"Fecha: {issue:%d/%m/%Y}")
        c.drawString(20 * mm, top - 26 * mm, "Cliente:")
        c.drawString(20 * mm, top - 31 * mm, customer)
        y = _draw_table(c, top - 45 * mm, lines, _eu, ("Concepto", "Uds.", "Precio", "Total"))
        y -= 4 * mm
        if discount:
            c.drawString(130 * mm, y, f"Descuento: -{_eu(discount)} €")
            y -= 6 * mm
        c.drawString(130 * mm, y, f"Base imponible: {_eu(subtotal)} €")
        c.drawString(130 * mm, y - 6 * mm, f"IVA ({rate}%): {_eu(tax)} €")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(130 * mm, y - 13 * mm, f"TOTAL: {_eu(total)} €")
        currency = "EUR"

    elif layout == "modern_en":
        supplier = rng.choice(_EN_SUPPLIERS)
        vat = _vat_id(rng, rng.choice(["NL", "DE"]))
        customer = rng.choice(_CUSTOMERS)
        number = f"INV-{rng.randint(1, 99999):05d}"
        lines = _lines(rng, _ITEMS_EN)
        shipping = Decimal(rng.choice([0, 15, 29.9])).quantize(CENT)
        subtotal = sum((ln.amount for ln in lines), Decimal(0)) + shipping
        rate = Decimal(rng.choice([19, 21]))
        tax = (subtotal * rate / 100).quantize(CENT, ROUND_HALF_UP)
        total = subtotal + tax
        symbol = rng.choice(["€", "$"])
        currency = "EUR" if symbol == "€" else "USD"
        c.setFont("Helvetica-Bold", 22)
        c.drawString(20 * mm, top, "Invoice")
        c.setFont("Helvetica", 9)
        c.drawRightString(190 * mm, top, supplier)
        c.drawRightString(190 * mm, top - 5 * mm, f"VAT ID {vat}")
        c.drawRightString(190 * mm, top - 10 * mm, "1 Example Street, Rotterdam")
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, top - 14 * mm, f"Invoice # {number}")
        c.drawString(20 * mm, top - 20 * mm, f"Issue date: {_en_date(issue)}")
        due = issue + timedelta(days=30)
        c.drawString(20 * mm, top - 26 * mm, f"Due date: {_en_date(due)}")
        c.drawString(110 * mm, top - 20 * mm, "Bill to")
        c.drawString(110 * mm, top - 26 * mm, customer)
        y = _draw_table(c, top - 42 * mm, lines, _us, ("Description", "Qty", "Unit", "Total"))
        y -= 4 * mm
        if shipping:
            c.drawString(130 * mm, y, f"Shipping {symbol}{_us(shipping)}")
            y -= 6 * mm
        c.drawString(130 * mm, y, f"Subtotal {symbol}{_us(subtotal)}")
        c.drawString(130 * mm, y - 6 * mm, f"VAT {rate}% {symbol}{_us(tax)}")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(130 * mm, y - 13 * mm, f"Amount due {symbol}{_us(total)}")

    elif layout == "compact_codes":
        supplier = f"{rng.choice(_SUPPLIER_CORE)} Industrial {rng.choice(_SUPPLIER_SUFFIX)}"
        vat = _vat_id(rng, "ES")
        customer = rng.choice(_CUSTOMERS)
        number = f"{issue.year}{rng.randint(100, 999)}"
        lines = _lines(rng, _ITEMS_ES)
        subtotal = sum((ln.amount for ln in lines), Decimal(0))
        rate = Decimal(21)
        tax = (subtotal * rate / 100).quantize(CENT, ROUND_HALF_UP)
        total = subtotal + tax
        currency = "EUR"
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, top, supplier)
        c.setFont("Helvetica", 8)
        c.drawString(20 * mm, top - 5 * mm, f"NIF/VAT: {vat}")
        c.drawString(20 * mm, top - 14 * mm, "Invoice No.")
        c.drawString(55 * mm, top - 14 * mm, number)
        c.drawString(100 * mm, top - 14 * mm, "Date")
        c.drawString(120 * mm, top - 14 * mm, issue.isoformat())
        c.drawString(20 * mm, top - 20 * mm, "Customer")
        c.drawString(55 * mm, top - 20 * mm, customer)
        headers = ("Item", "Q", "Price", "Total")
        y = _draw_table(c, top - 32 * mm, lines, lambda v: f"{v:.2f}", headers)
        y -= 4 * mm
        c.drawString(120 * mm, y, f"Net EUR {subtotal:.2f}")
        c.drawString(120 * mm, y - 5 * mm, f"Tax 21% EUR {tax:.2f}")
        c.drawString(120 * mm, y - 10 * mm, f"Gross total EUR {total:.2f}")

    elif layout == "reverse_charge_eu":
        supplier = rng.choice(_EN_SUPPLIERS)
        vat = _vat_id(rng, rng.choice(["DE", "FR", "NL"]))
        customer = rng.choice(_CUSTOMERS)
        number = f"{issue.year}/{rng.randint(1, 999)}"
        lines = _lines(rng, _ITEMS_EN)
        subtotal = sum((ln.amount for ln in lines), Decimal(0))
        tax = Decimal("0.00")
        total = subtotal
        currency = "EUR"
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20 * mm, top, supplier)
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, top - 6 * mm, f"VAT: {vat}")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, top - 18 * mm, f"INVOICE {number}")
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, top - 24 * mm, f"Date of issue {issue:%d.%m.%Y}")
        c.drawString(110 * mm, top - 18 * mm, "Customer:")
        c.drawString(110 * mm, top - 24 * mm, customer)
        c.drawString(110 * mm, top - 30 * mm, f"VAT: {_vat_id(rng, 'ES')}")
        y = _draw_table(c, top - 44 * mm, lines, _eu, ("Service", "Qty", "Rate", "Total"))
        y -= 4 * mm
        c.drawString(120 * mm, y, f"Total net: {_eu(subtotal)} EUR")
        c.drawString(120 * mm, y - 6 * mm, "VAT 0% (reverse charge): 0,00 EUR")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(120 * mm, y - 13 * mm, f"Total due: {_eu(total)} EUR")
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(20 * mm, 20 * mm, _REVERSE_CHARGE_NOTE)
    elif layout == "held_out_vendor":
        supplier = f"{rng.choice(_SUPPLIER_CORE)} Robotics {rng.choice(['S.L.', 'Ltd'])}"
        vat = _vat_id(rng, "ES")
        customer = rng.choice(_CUSTOMERS)
        number = f"A{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"
        lines = _lines(rng, _ITEMS_EN)
        subtotal = sum((ln.amount for ln in lines), Decimal(0))
        tax = (subtotal * Decimal(21) / 100).quantize(CENT, ROUND_HALF_UP)
        total = subtotal + tax
        currency = "EUR"
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        c.rect(20 * mm, top - 12 * mm, 30 * mm, 14 * mm)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(24 * mm, top - 6 * mm, "LOGO")
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, top - 20 * mm, f"Issued by {supplier}")
        c.drawString(20 * mm, top - 25 * mm, f"Tax ID {vat}")
        c.drawString(130 * mm, top - 2 * mm, "Invoice Number")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(130 * mm, top - 8 * mm, number)
        c.setFont("Helvetica", 9)
        c.drawString(130 * mm, top - 15 * mm, "Invoice Date")
        c.drawString(130 * mm, top - 20 * mm, f"{issue.day} {months[issue.month - 1]} {issue.year}")
        c.drawString(20 * mm, top - 36 * mm, f"Recipient: {customer}")
        y = _draw_table(c, top - 50 * mm, lines, _eu, ("Item", "Units", "Price", "Line total"))
        y -= 4 * mm
        c.drawString(120 * mm, y, f"Amount before tax {_eu(subtotal)}")
        c.drawString(120 * mm, y - 6 * mm, f"Sales tax 21% {_eu(tax)}")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(120 * mm, y - 13 * mm, f"Total amount (EUR) {_eu(total)}")
    else:
        raise ValueError(f"unknown layout {layout!r}")

    c.showPage()
    c.save()
    return Invoice(
        invoice_number=number,
        invoice_date=issue,
        supplier_name=supplier,
        supplier_vat_id=vat,
        customer_name=customer,
        currency=currency,
        subtotal=subtotal.quantize(CENT),
        tax_amount=tax.quantize(CENT),
        total=total.quantize(CENT),
    )


def generate_dataset(
    out_dir: Path, per_layout: int = 10, seed: int = 7, scanned: int = 3
) -> list[Path]:
    """Write ``per_layout`` PDFs per layout plus one ``.truth.json`` next to each.

    ``scanned`` extra documents are rasterised to image-only PDFs (no text layer) to show
    how the pipeline routes them to review instead of returning confident garbage.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for li, layout in enumerate(LAYOUTS + HELD_OUT_LAYOUTS):
        for i in range(per_layout):
            pdf = out_dir / f"{layout}_{i:02d}.pdf"
            truth = generate_one(pdf, layout, seed=seed * 10_000 + li * 1_000 + i)
            pdf.with_suffix(".truth.json").write_text(
                json.dumps(truth.to_jsonable(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            paths.append(pdf)
    for i in range(scanned):
        source = paths[i * per_layout]  # one per base layout
        target = out_dir / f"scanned_{i:02d}.pdf"
        if _rasterise(source, target):
            truth = source.with_suffix(".truth.json").read_text(encoding="utf-8")
            target.with_suffix(".truth.json").write_text(truth, encoding="utf-8")
            paths.append(target)
    return paths


def _rasterise(source: Path, target: Path) -> bool:
    """Image-only copy of a PDF via poppler's pdftoppm + Pillow. Skipped if unavailable."""
    import shutil
    import subprocess
    import tempfile

    if shutil.which("pdftoppm") is None:
        return False
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "page"
        subprocess.run(
            ["pdftoppm", "-r", "110", "-gray", "-png", "-singlefile", str(source), str(prefix)],
            check=True,
        )
        Image.open(f"{prefix}.png").convert("RGB").save(target, "PDF", resolution=110)
    return True
