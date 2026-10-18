"""Extractor registry."""

from __future__ import annotations

from typing import Protocol

from ..schema import Invoice


class Extractor(Protocol):
    name: str

    def extract(self, pdf_path) -> tuple[Invoice, list[str]]:
        """Return the invoice and a list of low-confidence notes."""


def get_extractor(name: str) -> Extractor:
    if name == "rules":
        from .rules import RulesExtractor

        return RulesExtractor()
    if name == "llm":
        from .llm import LLMExtractor

        return LLMExtractor.from_env()
    raise ValueError(f"unknown extractor {name!r} (use 'rules' or 'llm')")
