"""Generate a synthetic dataset for ProcureMind.

Outputs:
  data/invoices/*.pdf          sample invoices (2 different layouts, EN/DE style)
  data/ground_truth/*.json     the correct answer for each invoice (for evaluation)
  data/invoice_history.csv     ~3,000 historical invoices with injected anomalies (module 3)

Run:  python scripts/generate_data.py --n 20
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SUPPLIERS = [
    ("Nordwind Office Supplies GmbH", "DE811234567", "EUR"),
    ("Celtic Cloud Services Ltd", "IE6388047V", "EUR"),
    ("Baltic Hardware OU", "EE101234567", "EUR"),
    ("Alpine IT Consulting AG", "CHE-123.456.789", "CHF"),
    ("Thames Logistics plc", "GB123456789", "GBP"),
    ("Vistula Print Sp. z o.o.", "PL5260001246", "PLN"),
    ("Iberia Catering S.L.", "ESB12345678", "EUR"),
    ("Danube Facility Management Kft", "HU12345678", "EUR"),
]
BUYERS = ["SAP Demo Company Ireland Ltd", "Contoso Manufacturing GmbH", "Fabrikam Retail BV"]
CATALOG = {
    "Nordwind Office Supplies GmbH": [("A4 copy paper, box of 5 reams", 24.90), ("Ergonomic office chair", 289.00), ("Whiteboard markers, set of 12", 11.50), ("Desk lamp LED", 39.99)],
    "Celtic Cloud Services Ltd": [("Cloud VM hosting, monthly", 420.00), ("Managed database, monthly", 310.00), ("Premium support plan", 199.00)],
    "Baltic Hardware OU": [("Laptop 14\" business", 1149.00), ("27\" monitor", 229.00), ("USB-C docking station", 159.00), ("Wireless keyboard", 49.00)],
    "Alpine IT Consulting AG": [("SAP S/4HANA consulting, per day", 1350.00), ("Solution architecture workshop", 2400.00), ("Travel expenses (flat)", 380.00)],
    "Thames Logistics plc": [("Pallet freight UK-IE", 185.00), ("Express parcel", 32.50), ("Warehousing per pallet/week", 14.00)],
    "Vistula Print Sp. z o.o.": [("Business cards, 500 pcs", 120.00), ("Roll-up banner", 340.00), ("Brochures A5, 1000 pcs", 610.00)],
    "Iberia Catering S.L.": [("Lunch buffet, per person", 18.50), ("Coffee break, per person", 6.20), ("Event staff, per hour", 28.00)],
    "Danube Facility Management Kft": [("Office cleaning, monthly", 980.00), ("HVAC maintenance visit", 450.00), ("Window cleaning", 260.00)],
}
TAX_RATES = {"EUR": 0.23, "CHF": 0.081, "GBP": 0.20, "PLN": 0.23}


def make_invoice(i: int, rng: random.Random) -> dict:
    name, vat, cur = rng.choice(SUPPLIERS)
    inv_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))
    items = []
    for desc, price in rng.sample(CATALOG[name], k=rng.randint(1, min(3, len(CATALOG[name])))):
        qty = rng.choice([1, 1, 2, 3, 5, 10, 20])
        items.append({"description": desc, "quantity": qty, "unit_price": price, "total": round(qty * price, 2)})
    subtotal = round(sum(x["total"] for x in items), 2)
    tax = round(subtotal * TAX_RATES[cur], 2)
    return {
        "invoice_number": f"{rng.choice(['INV', 'RE', 'FV', 'BILL'])}-2026-{1000 + i}",
        "invoice_date": inv_date.isoformat(),
        "due_date": (inv_date + timedelta(days=rng.choice([14, 30, 45, 60]))).isoformat(),
        "supplier_name": name,
        "supplier_vat_id": vat,
        "buyer_name": rng.choice(BUYERS),
        "currency": cur,
        "subtotal": subtotal,
        "tax_amount": tax,
        "total_amount": round(subtotal + tax, 2),
        "line_items": items,
    }


def fmt_money(x: float, style: str) -> str:
    s = f"{x:,.2f}"
    if style == "eu":  # 1.234,56
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def fmt_date(iso: str, style: str) -> str:
    d = date.fromisoformat(iso)
    return d.strftime("%d.%m.%Y") if style == "eu" else d.strftime("%d %B %Y")


def draw_pdf(inv: dict, path: Path, layout: int) -> None:
    """Two visually different layouts so the extractor can't rely on fixed positions."""
    style = "eu" if layout == 1 else "uk"
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 25 * mm
    if layout == 0:
        c.setFont("Helvetica-Bold", 18); c.drawString(20 * mm, y, "INVOICE")
        c.setFont("Helvetica", 10)
        c.drawRightString(w - 20 * mm, y, inv["supplier_name"])
        c.drawRightString(w - 20 * mm, y - 5 * mm, f"VAT ID: {inv['supplier_vat_id']}")
        y -= 20 * mm
        for label, val in [("Invoice No.", inv["invoice_number"]), ("Date", fmt_date(inv["invoice_date"], style)),
                           ("Payment due", fmt_date(inv["due_date"], style)), ("Bill to", inv["buyer_name"])]:
            c.drawString(20 * mm, y, f"{label}: {val}"); y -= 6 * mm
    else:
        c.setFont("Helvetica-Bold", 13); c.drawString(20 * mm, y, inv["supplier_name"])
        c.setFont("Helvetica", 9); c.drawString(20 * mm, y - 5 * mm, f"USt-IdNr./VAT: {inv['supplier_vat_id']}")
        y -= 18 * mm
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, y, f"Customer: {inv['buyer_name']}")
        c.drawRightString(w - 20 * mm, y, f"Rechnung / Invoice #{inv['invoice_number']}")
        c.drawRightString(w - 20 * mm, y - 6 * mm, f"Issued {fmt_date(inv['invoice_date'], style)}")
        c.drawRightString(w - 20 * mm, y - 12 * mm, f"Due by {fmt_date(inv['due_date'], style)}")
        y -= 18 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    cols = [20 * mm, 110 * mm, 135 * mm, 165 * mm]
    for x, t in zip(cols, ["Description", "Qty", "Unit price", "Amount"]):
        c.drawString(x, y, t)
    c.line(20 * mm, y - 2 * mm, w - 20 * mm, y - 2 * mm)
    c.setFont("Helvetica", 10); y -= 8 * mm
    for li in inv["line_items"]:
        c.drawString(cols[0], y, li["description"])
        c.drawString(cols[1], y, str(li["quantity"]))
        c.drawString(cols[2], y, fmt_money(li["unit_price"], style))
        c.drawString(cols[3], y, fmt_money(li["total"], style))
        y -= 6 * mm
    y -= 6 * mm
    cur = inv["currency"]
    rate = round(inv["tax_amount"] / inv["subtotal"] * 100, 1) if inv["subtotal"] else 0
    for label, val in [("Net amount", inv["subtotal"]), (f"VAT {rate}%", inv["tax_amount"]), ("TOTAL", inv["total_amount"])]:
        c.setFont("Helvetica-Bold" if label == "TOTAL" else "Helvetica", 10)
        c.drawRightString(160 * mm, y, label)
        c.drawRightString(w - 20 * mm, y, f"{fmt_money(val, style)} {cur}")
        y -= 6 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, 20 * mm, "Please quote the invoice number with your payment. Thank you for your business.")
    c.save()


def make_history(rng: random.Random, n: int = 3000) -> list[dict]:
    """Historical invoices for anomaly detection. ~3% are labeled anomalies."""
    rows = []
    typical = {s[0]: (sum(p for _, p in CATALOG[s[0]]) / len(CATALOG[s[0]])) * 4 for s in SUPPLIERS}
    for i in range(n):
        name, _, cur = rng.choice(SUPPLIERS)
        d = date(2024, 1, 1) + timedelta(days=rng.randint(0, 1000))
        amount = round(max(10, rng.lognormvariate(0, 0.45) * typical[name]), 2)
        rows.append({"invoice_id": f"H{i:05d}", "supplier": name, "currency": cur, "invoice_date": d.isoformat(),
                     "amount": amount, "days_to_due": rng.choice([14, 30, 30, 30, 45, 60]),
                     "approved_by": rng.choice(["m.keane", "a.byrne", "j.murphy", "s.walsh"]),
                     "anomaly_type": ""})
    for row in rng.sample(rows, k=int(n * 0.03)):
        kind = rng.choice(["amount_spike", "duplicate", "weekend", "round_amount", "short_due"])
        row["anomaly_type"] = kind
        if kind == "amount_spike":
            row["amount"] = round(row["amount"] * rng.uniform(6, 15), 2)
        elif kind == "weekend":
            d = date.fromisoformat(row["invoice_date"])
            row["invoice_date"] = (d + timedelta(days=(5 - d.weekday()) % 7)).isoformat()
        elif kind == "round_amount":
            row["amount"] = float(rng.choice([5000, 9900, 10000, 25000]))
        elif kind == "short_due":
            row["days_to_due"] = rng.choice([0, 1, 2])
        elif kind == "duplicate":
            src = rng.choice(rows)
            row.update({k: src[k] for k in ["supplier", "currency", "invoice_date", "amount"]})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="number of PDF invoices")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    (DATA / "invoices").mkdir(parents=True, exist_ok=True)
    (DATA / "ground_truth").mkdir(parents=True, exist_ok=True)
    for i in range(args.n):
        inv = make_invoice(i, rng)
        stem = f"invoice_{i:03d}"
        draw_pdf(inv, DATA / "invoices" / f"{stem}.pdf", layout=i % 2)
        (DATA / "ground_truth" / f"{stem}.json").write_text(json.dumps(inv, indent=2), encoding="utf-8")

    rows = make_history(rng)
    with open(DATA / "invoice_history.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader(); wr.writerows(rows)

    print(f"Wrote {args.n} invoices to data/invoices, ground truth to data/ground_truth, "
          f"{len(rows)} rows to data/invoice_history.csv")


if __name__ == "__main__":
    main()
