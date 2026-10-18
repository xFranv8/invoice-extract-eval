"""Optional LLM extractor for any OpenAI-compatible chat endpoint.

Works with a hosted provider (set ``LLM_API_KEY``) or fully locally with Ollama /
llama.cpp / vLLM by pointing ``LLM_BASE_URL`` at them (no key needed). Uses only the
standard library so the base install stays small.

Environment:
    LLM_BASE_URL   default https://api.openai.com/v1
    LLM_API_KEY    required for hosted providers, ignored by most local servers
    LLM_MODEL      default gpt-4o-mini
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..normalize import normalize_text, normalize_vat_id, parse_amount, parse_date
from ..pdf_text import read_lines
from ..schema import FIELDS, Invoice

PROMPT = """You extract fields from an invoice. Reply with a single JSON object with exactly
these keys: {fields}. Use null when a field is not present. Do not guess.
- invoice_date: ISO format YYYY-MM-DD
- subtotal, tax_amount, total: plain numbers with a dot as decimal separator
- currency: ISO 4217 code
- supplier_name is the issuer of the invoice, customer_name is the recipient.

Invoice text (columns separated by ' | '):
---
{text}
---"""

Transport = Callable[[str, dict, dict], dict]


def _http_transport(url: str, headers: dict, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - URL comes from config
        return json.loads(resp.read())


@dataclass
class LLMExtractor:
    base_url: str
    model: str
    api_key: str | None = None
    transport: Transport = _http_transport
    name: str = "llm"

    @classmethod
    def from_env(cls) -> LLMExtractor:
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("LLM_API_KEY"),
        )

    def extract(self, pdf_path: Path) -> tuple[Invoice, list[str]]:
        lines, _ = read_lines(Path(pdf_path))
        text = "\n".join(" | ".join(s.text for s in line.segments) for line in lines)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "user", "content": PROMPT.format(fields=", ".join(FIELDS), text=text)}
            ],
        }
        response = self.transport(f"{self.base_url}/chat/completions", headers, payload)
        content = response["choices"][0]["message"]["content"]
        return parse_llm_json(content), []


def parse_llm_json(content: str) -> Invoice:
    """Normalise model output with the same parsers the rules extractor uses."""
    start, end = content.find("{"), content.rfind("}")
    data = json.loads(content[start : end + 1]) if start != -1 else {}

    def s(key: str) -> str | None:
        value = data.get(key)
        return None if value in (None, "") else str(value)

    return Invoice(
        invoice_number=normalize_text(s("invoice_number")),
        invoice_date=parse_date(s("invoice_date") or ""),
        supplier_name=normalize_text(s("supplier_name")),
        supplier_vat_id=normalize_vat_id(s("supplier_vat_id") or ""),
        customer_name=normalize_text(s("customer_name")),
        currency=(s("currency") or "").upper() or None,
        subtotal=parse_amount(s("subtotal") or ""),
        tax_amount=parse_amount(s("tax_amount") or ""),
        total=parse_amount(s("total") or ""),
    )
