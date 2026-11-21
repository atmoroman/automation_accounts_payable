"""Unit tests run WITHOUT an API key: a fake LLM client returns canned answers."""
import json
from pathlib import Path

import pytest

from procuremind.extraction import extract_from_text
from procuremind.schemas import Invoice, consistency_checks

GOOD = {
    "invoice_number": "INV-1", "invoice_date": "2026-03-01", "due_date": "2026-03-31",
    "supplier_name": "ACME", "supplier_vat_id": None, "buyer_name": "SAP Demo",
    "currency": "eur", "subtotal": 100.0, "tax_amount": 23.0, "total_amount": 123.0,
    "line_items": [{"description": "Paper", "quantity": 4, "unit_price": 25.0, "total": 100.0}],
}


class FakeClient:
    model = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete_json(self, system, user):
        self.calls += 1
        return self.replies.pop(0)


def test_happy_path():
    res = extract_from_text("dummy", client=FakeClient([json.dumps(GOOD)]))
    assert res.ok and res.attempts == 1
    assert res.invoice.currency == "EUR"  # normalised by validator
    assert res.warnings == []


def test_self_repair_after_invalid_json():
    client = FakeClient(["not json at all", json.dumps(GOOD)])
    res = extract_from_text("dummy", client=client)
    assert res.ok and res.attempts == 2 and client.calls == 2


def test_gives_up_after_second_failure():
    res = extract_from_text("dummy", client=FakeClient(["{}", "{}"]))
    assert not res.ok and res.error


def test_consistency_checks_catch_bad_totals():
    bad = dict(GOOD, total_amount=999.0)
    issues = consistency_checks(Invoice.model_validate(bad))
    assert any("total" in i for i in issues)


def test_generated_ground_truth_is_valid():
    gt = Path(__file__).resolve().parents[1] / "data" / "ground_truth"
    files = list(gt.glob("*.json"))
    if not files:
        pytest.skip("run scripts/generate_data.py first")
    for f in files:
        inv = Invoice.model_validate(json.loads(f.read_text()))
        assert consistency_checks(inv) == [], f.name
