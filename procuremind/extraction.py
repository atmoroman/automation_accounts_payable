"""Module 1: extract structured invoice data from unstructured text with an LLM.

Pipeline:  PDF -> text -> LLM (JSON mode) -> Pydantic validation
           -> (on failure) one self-repair retry -> business-rule checks
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .llm import LLMClient, OpenAICompatibleClient
from .pdf_utils import pdf_to_text
from .schemas import Invoice, consistency_checks

SYSTEM_PROMPT = """You are an accounts-payable assistant that extracts data from invoices.
Return ONLY a JSON object with exactly these keys:
{
  "invoice_number": string,
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD" or null,
  "supplier_name": string,
  "supplier_vat_id": string or null,
  "buyer_name": string,
  "currency": 3-letter ISO code (e.g. "EUR"),
  "subtotal": number,
  "tax_amount": number,
  "total_amount": number,
  "line_items": [{"description": string, "quantity": number, "unit_price": number, "total": number}]
}
Rules:
- Copy values exactly as they appear; convert dates to YYYY-MM-DD.
- Numbers must be plain numbers without currency symbols or thousands separators.
- If a field is missing in the document, use null. Never invent values."""

REPAIR_PROMPT = """Your previous JSON failed validation with these errors:
{errors}

Previous JSON:
{previous}

Return a corrected JSON object only."""


@dataclass
class ExtractionResult:
    invoice: Invoice | None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    attempts: int = 0
    latency_s: float = 0.0
    model: str = ""

    @property
    def ok(self) -> bool:
        return self.invoice is not None


def _parse(raw: str) -> Invoice:
    return Invoice.model_validate(json.loads(raw))


def extract_from_text(text: str, client: LLMClient | None = None) -> ExtractionResult:
    client = client or OpenAICompatibleClient()
    start = time.perf_counter()
    user_msg = f"Invoice text:\n\"\"\"\n{text}\n\"\"\""

    raw = client.complete_json(SYSTEM_PROMPT, user_msg)
    attempts = 1
    try:
        invoice = _parse(raw)
    except (json.JSONDecodeError, ValidationError) as e:
        # Self-repair: show the model its own mistake and ask for a fix.
        raw = client.complete_json(
            SYSTEM_PROMPT, user_msg + "\n\n" + REPAIR_PROMPT.format(errors=e, previous=raw)
        )
        attempts = 2
        try:
            invoice = _parse(raw)
        except (json.JSONDecodeError, ValidationError) as e2:
            return ExtractionResult(
                invoice=None, error=str(e2), attempts=attempts,
                latency_s=time.perf_counter() - start, model=client.model,
            )

    return ExtractionResult(
        invoice=invoice,
        warnings=consistency_checks(invoice),
        attempts=attempts,
        latency_s=time.perf_counter() - start,
        model=client.model,
    )


def extract_from_pdf(path: str | Path, client: LLMClient | None = None) -> ExtractionResult:
    return extract_from_text(pdf_to_text(path), client=client)
