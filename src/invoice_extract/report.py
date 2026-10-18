"""Markdown and standalone HTML accuracy reports."""

from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .evaluate import Evaluation
from .schema import FIELDS, ExtractionResult


def _group(source: str) -> str:
    return re.sub(r"_\d+$", "", Path(source).stem)


def _per_group(ev: Evaluation) -> dict[str, tuple[int, int, int]]:
    """group -> (docs, fully correct, sent to review)"""
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for d in ev.docs:
        g = acc[_group(d.source)]
        g[0] += 1
        g[1] += d.fully_correct
        g[2] += d.needs_review
    return {k: (v[0], v[1], v[2]) for k, v in sorted(acc.items())}


def to_markdown(ev: Evaluation, results: list[ExtractionResult], extractor: str) -> str:
    lines = [
        "# Extraction accuracy report",
        "",
        f"- Extractor: `{extractor}`",
        f"- Documents: {ev.n}",
        f"- Fully correct documents: {ev.doc_accuracy:.0%}",
        f"- Sent to human review: {ev.n - len(ev.auto_accepted)} of {ev.n}",
        f"- Errors caught by the review queue: {ev.errors_caught:.0%}",
        f"- Auto-accepted documents that still had an error: {ev.auto_accepted_error_rate:.0%}",
        "",
        "## Accuracy per field",
        "",
        "| Field | Accuracy |",
        "|---|---|",
    ]
    lines += [f"| {f} | {a:.0%} |" for f, a in ev.field_accuracy().items()]
    lines += [
        "",
        "## Per layout",
        "",
        "| Layout | Docs | Fully correct | Sent to review |",
        "|---|---|---|---|",
    ]
    for g, (n, ok, rev) in _per_group(ev).items():
        lines.append(f"| {g} | {n} | {ok} | {rev} |")
    flagged = [r for r in results if r.needs_review]
    if flagged:
        lines += ["", "## Review queue", "", "| Document | Reasons |", "|---|---|"]
        lines += [f"| {Path(r.source).name} | {'; '.join(r.review_reasons)} |" for r in flagged]
    wrong = [d for d in ev.docs if d.wrong_fields]
    if wrong:
        lines += [
            "",
            "## Field errors",
            "",
            "| Document | Wrong fields | In review queue |",
            "|---|---|---|",
        ]
        lines += [
            f"| {Path(d.source).name} | {', '.join(d.wrong_fields)} | "
            f"{'yes' if d.needs_review else '**no**'} |"
            for d in wrong
        ]
    return "\n".join(lines) + "\n"


_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:32px;color:#1f2328;
max-width:1000px}
h1{font-size:24px;margin:0 0 4px} .sub{color:#57606a;margin-bottom:24px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}
.card{border:1px solid #d0d7de;border-radius:8px;padding:14px}
.card b{display:block;font-size:26px} .card span{color:#57606a;font-size:13px}
table{border-collapse:collapse;width:100%;margin-bottom:28px;font-size:14px}
th,td{border-bottom:1px solid #d8dee4;padding:7px 8px;text-align:left}
th{background:#f6f8fa} .bar{background:#eaeef2;border-radius:4px;height:10px;width:220px}
.bar i{display:block;height:10px;border-radius:4px;background:#2da44e}
.bad{color:#cf222e;font-weight:600} h2{font-size:17px;margin-top:8px}
"""


def to_html(ev: Evaluation, results: list[ExtractionResult], extractor: str) -> str:
    e = html.escape
    cards = [
        (f"{ev.doc_accuracy:.0%}", "documents fully correct"),
        (f"{ev.n - len(ev.auto_accepted)}/{ev.n}", "sent to human review"),
        (f"{ev.errors_caught:.0%}", "of errors caught by review"),
        (f"{ev.auto_accepted_error_rate:.0%}", "auto-accepted with an error"),
    ]
    out = [
        f"<!doctype html><meta charset='utf-8'><title>Extraction report</title>"
        f"<style>{_CSS}</style>",
        "<h1>Invoice extraction: accuracy report</h1>",
        f"<div class='sub'>Extractor <code>{e(extractor)}</code> · {ev.n} documents · "
        f"generated {datetime.now():%Y-%m-%d %H:%M}</div><div class='cards'>",
    ]
    out += [f"<div class='card'><b>{v}</b><span>{e(t)}</span></div>" for v, t in cards]
    out.append(
        "</div><h2>Accuracy per field</h2><table><tr><th>Field</th><th></th><th>Accuracy</th></tr>"
    )
    for f, a in ev.field_accuracy().items():
        out.append(
            f"<tr><td>{f}</td><td><div class='bar'><i style='width:{a * 100:.0f}%'>"
            f"</i></div></td><td>{a:.0%}</td></tr>"
        )
    out.append(
        "</table><h2>Per layout</h2><table><tr><th>Layout</th><th>Docs</th>"
        "<th>Fully correct</th><th>Sent to review</th></tr>"
    )
    for g, (n, ok, rev) in _per_group(ev).items():
        out.append(f"<tr><td>{e(g)}</td><td>{n}</td><td>{ok}</td><td>{rev}</td></tr>")
    out.append("</table>")
    flagged = [r for r in results if r.needs_review]
    if flagged:
        out.append("<h2>Review queue</h2><table><tr><th>Document</th><th>Reasons</th></tr>")
        out += [
            f"<tr><td>{e(Path(r.source).name)}</td><td>{e('; '.join(r.review_reasons))}</td></tr>"
            for r in flagged
        ]
        out.append("</table>")
    wrong = [d for d in ev.docs if d.wrong_fields]
    if wrong:
        out.append(
            "<h2>Field errors</h2><table><tr><th>Document</th><th>Wrong fields</th>"
            "<th>In review queue</th></tr>"
        )
        for d in wrong:
            flag = "yes" if d.needs_review else "<span class='bad'>no</span>"
            out.append(
                f"<tr><td>{e(Path(d.source).name)}</td>"
                f"<td>{e(', '.join(d.wrong_fields))}</td><td>{flag}</td></tr>"
            )
        out.append("</table>")
    return "\n".join(out)


def write_reports(out_dir: Path, ev: Evaluation, results, extractor: str) -> None:
    (out_dir / "report.md").write_text(to_markdown(ev, results, extractor), encoding="utf-8")
    (out_dir / "report.html").write_text(to_html(ev, results, extractor), encoding="utf-8")


__all__ = ["to_markdown", "to_html", "write_reports", "FIELDS"]
