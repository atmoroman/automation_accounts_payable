"""Data model for an invoice. Pydantic validates whatever the LLM returns."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LineItem(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    total: float = Field(ge=0)


class Invoice(BaseModel):
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    supplier_name: str
    supplier_vat_id: Optional[str] = None
    buyer_name: str
    currency: str = Field(description="ISO 4217 code, e.g. EUR")
    subtotal: float = Field(ge=0)
    tax_amount: float = Field(ge=0)
    total_amount: float = Field(ge=0)
    line_items: list[LineItem] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3:
            raise ValueError("currency must be a 3-letter ISO code")
        return v


def consistency_checks(inv: Invoice, tol: float = 0.02) -> list[str]:
    """Business-rule checks. We never blindly trust LLM output:
    numbers must add up, dates must make sense."""
    issues: list[str] = []
    if inv.line_items:
        items_sum = round(sum(li.total for li in inv.line_items), 2)
        if abs(items_sum - inv.subtotal) > tol:
            issues.append(f"Line items sum to {items_sum}, but subtotal is {inv.subtotal}")
        for li in inv.line_items:
            if abs(li.quantity * li.unit_price - li.total) > tol:
                issues.append(f"Line '{li.description}': qty x price != total")
    if abs(inv.subtotal + inv.tax_amount - inv.total_amount) > tol:
        issues.append(
            f"subtotal + tax = {inv.subtotal + inv.tax_amount:.2f}, but total is {inv.total_amount}"
        )
    if inv.due_date and inv.due_date < inv.invoice_date:
        issues.append("Due date is before invoice date")
    return issues
