import json
from pathlib import Path

import pytest

from invoice_extract.cli import main, run_pipeline
from invoice_extract.evaluate import evaluate
from invoice_extract.extractors.llm import LLMExtractor, parse_llm_json
from invoice_extract.samples import LAYOUTS, generate_dataset
from invoice_extract.schema import Invoice


@pytest.fixture(scope="module")
def dataset(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("samples")
    generate_dataset(out, per_layout=4, seed=11, scanned=2)
    return out


def _truths(results):
    return {
        r.source: Invoice.from_jsonable(
            json.loads(Path(r.source).with_suffix(".truth.json").read_text())
        )
        for r in results
    }


def test_rules_on_known_layouts_and_review_safety(dataset):
    results = run_pipeline(dataset, "rules")
    ev = evaluate(results, _truths(results))
    known = [d for d in ev.docs if Path(d.source).stem.rsplit("_", 1)[0] in LAYOUTS]
    assert known and all(d.fully_correct for d in known)
    # The property that matters in production: nothing wrong slips through unflagged.
    assert ev.auto_accepted_error_rate == 0.0
    assert ev.errors_caught == 1.0


def test_scanned_pdfs_go_to_review(dataset):
    results = run_pipeline(dataset, "rules")
    scanned = [r for r in results if Path(r.source).name.startswith("scanned_")]
    assert scanned and all(r.needs_review for r in scanned)
    assert all("OCR" in r.review_reasons[0] for r in scanned)


def test_cli_writes_outputs(dataset, tmp_path):
    assert main(["run", "--input", str(dataset), "--out", str(tmp_path)]) == 0
    for name in ("extracted.json", "extracted.xlsx", "report.md", "report.html"):
        assert (tmp_path / name).exists()


def test_llm_extractor_with_fake_transport(dataset):
    captured = {}

    def fake_transport(url, headers, payload):
        captured.update(url=url, payload=payload)
        content = json.dumps(
            {
                "invoice_number": "INV-1",
                "invoice_date": "2026-10-18",
                "supplier_name": "Acme Ltd",
                "supplier_vat_id": "DE123456789",
                "customer_name": "Foo S.L.",
                "currency": "eur",
                "subtotal": "100.00",
                "tax_amount": "21.00",
                "total": "121.00",
            }
        )
        return {"choices": [{"message": {"content": content}}]}

    extractor = LLMExtractor(
        base_url="http://localhost:11434/v1", model="local", transport=fake_transport
    )
    invoice, _ = extractor.extract(next(dataset.glob("modern_en_*.pdf")))
    assert captured["url"].endswith("/chat/completions")
    assert "Invoice" in captured["payload"]["messages"][0]["content"]
    assert invoice.total is not None and str(invoice.total) == "121.00"
    assert invoice.currency == "EUR"


def test_parse_llm_json_tolerates_prose_and_nulls():
    inv = parse_llm_json('Here you go: {"total": "1.234,50", "invoice_date": null}')
    assert str(inv.total) == "1234.50"
    assert inv.invoice_date is None
