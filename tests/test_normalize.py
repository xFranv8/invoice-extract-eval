from datetime import date
from decimal import Decimal

import pytest

from invoice_extract.normalize import (
    detect_currency,
    find_amounts,
    normalize_vat_id,
    parse_amount,
    parse_date,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.234,56 €", Decimal("1234.56")),
        ("$1,234.56", Decimal("1234.56")),
        ("1 234,56", Decimal("1234.56")),
        ("1234.56", Decimal("1234.56")),
        ("-50,00", Decimal("-50.00")),
        ("12.000", Decimal("12000")),
        ("abc", None),
    ],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


def test_find_amounts_skips_percentages_and_references():
    assert find_amounts("IVA (21%): 1.341,14 €") == [Decimal("1341.14")]
    line = "Reverse charge (Art. 196 Directive 2006/112/EC)"
    assert find_amounts(line, require_decimals=True) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("18/10/2026", date(2026, 10, 18)),
        ("18.10.2026", date(2026, 10, 18)),
        ("2026-10-18", date(2026, 10, 18)),
        ("Oct 18, 2026", date(2026, 10, 18)),
        ("18 de octubre de 2026", date(2026, 10, 18)),
        ("31/02/2026", None),
    ],
)
def test_parse_date(text, expected):
    assert parse_date(text) == expected


def test_vat_ids():
    assert normalize_vat_id("CIF: ESB12345678") == "ESB12345678"
    assert normalize_vat_id("VAT ID NL123456789B01") == "NL123456789B01"
    assert normalize_vat_id("Phone 600123456") is None


def test_currency():
    assert detect_currency("Total 10,00 € and 5,00 €") == "EUR"
    assert detect_currency("Amount due $19.00") == "USD"
    assert detect_currency("no money here") is None
