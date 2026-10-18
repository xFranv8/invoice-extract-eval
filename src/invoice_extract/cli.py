"""Command line: generate sample invoices, extract, evaluate, report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .excel import write_workbook
from .extractors import get_extractor
from .report import write_reports
from .schema import ExtractionResult, Invoice
from .validate import review_reasons


def cmd_generate(args: argparse.Namespace) -> int:
    from .samples import generate_dataset

    paths = generate_dataset(
        Path(args.out), per_layout=args.per_layout, seed=args.seed, scanned=args.scanned
    )
    print(f"wrote {len(paths)} invoices (+ .truth.json) to {args.out}")
    return 0


def run_pipeline(input_dir: Path, extractor_name: str) -> list[ExtractionResult]:
    extractor = get_extractor(extractor_name)
    results: list[ExtractionResult] = []
    for pdf in sorted(input_dir.glob("*.pdf")):
        try:
            invoice, notes = extractor.extract(pdf)
        except Exception as exc:  # one bad file must not stop a batch
            invoice, notes = Invoice(), [f"extractor error: {exc}"]
        reasons = review_reasons(invoice, notes)
        if any(n.startswith("extractor error") for n in notes):
            reasons = notes + reasons
        results.append(ExtractionResult(str(pdf), invoice, bool(reasons), reasons))
    return results


def cmd_run(args: argparse.Namespace) -> int:
    input_dir, out_dir = Path(args.input), Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = run_pipeline(input_dir, args.extractor)
    if not results:
        print(f"no PDFs found in {input_dir}", file=sys.stderr)
        return 1

    (out_dir / "extracted.json").write_text(
        json.dumps(
            [
                {
                    "file": Path(r.source).name,
                    **r.invoice.to_jsonable(),
                    "needs_review": r.needs_review,
                    "review_reasons": r.review_reasons,
                }
                for r in results
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    evaluation = None
    truths = {
        r.source: Invoice.from_jsonable(json.loads(t.read_text(encoding="utf-8")))
        for r in results
        if (t := Path(r.source).with_suffix(".truth.json")).exists()
    }
    if len(truths) == len(results):
        from .evaluate import evaluate

        evaluation = evaluate(results, truths)
        write_reports(out_dir, evaluation, results, args.extractor)
        print(
            f"documents fully correct: {evaluation.doc_accuracy:.0%} | "
            f"sent to review: {sum(r.needs_review for r in results)}/{len(results)} | "
            f"auto-accepted with error: {evaluation.auto_accepted_error_rate:.0%}"
        )
    else:
        print("no ground truth for every file: skipping accuracy report")
    write_workbook(out_dir / "extracted.xlsx", results, evaluation)
    print(f"outputs in {out_dir}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="invoice-extract", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="write synthetic invoices with ground truth")
    g.add_argument("--out", default="samples")
    g.add_argument("--per-layout", type=int, default=10)
    g.add_argument("--scanned", type=int, default=3, help="image-only PDFs to add")
    g.add_argument("--seed", type=int, default=7)
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("run", help="extract a folder of PDFs and (if truth exists) evaluate")
    r.add_argument("--input", default="samples")
    r.add_argument("--out", default="out")
    r.add_argument("--extractor", choices=["rules", "llm"], default="rules")
    r.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
