"""Evaluate extraction quality against ground truth.

Reports field-level accuracy, line-item accuracy, schema-valid rate and latency.
This gives you a REAL number for your resume (e.g. "96% field accuracy on 20 invoices").

Run:  python scripts/evaluate_extraction.py            (all invoices)
      python scripts/evaluate_extraction.py --limit 5  (quick check)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from procuremind.extraction import extract_from_pdf  # noqa: E402
from procuremind.llm import OpenAICompatibleClient  # noqa: E402

FIELDS = ["invoice_number", "invoice_date", "due_date", "supplier_name", "supplier_vat_id",
          "buyer_name", "currency", "subtotal", "tax_amount", "total_amount"]


def same(a, b) -> bool:
    if isinstance(b, (int, float)) and a is not None:
        try:
            return abs(float(a) - float(b)) < 0.011
        except (TypeError, ValueError):
            return False
    return str(a).strip().lower() == str(b).strip().lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=2.0, help="pause between calls (free-tier rate limits)")
    args = ap.parse_args()

    pdfs = sorted((ROOT / "data" / "invoices").glob("*.pdf"))[: args.limit]
    if not pdfs:
        sys.exit("No invoices found. Run: python scripts/generate_data.py")

    client = OpenAICompatibleClient()
    field_hits = {f: 0 for f in FIELDS}
    valid = items_ok = 0
    latencies, per_doc = [], []

    for pdf in pdfs:
        truth = json.loads((ROOT / "data" / "ground_truth" / f"{pdf.stem}.json").read_text())
        res = extract_from_pdf(pdf, client=client)
        latencies.append(res.latency_s)
        doc = {"file": pdf.name, "ok": res.ok, "errors": [], "warnings": res.warnings}
        if res.ok:
            valid += 1
            pred = json.loads(res.invoice.model_dump_json())
            for f in FIELDS:
                if same(pred.get(f), truth[f]):
                    field_hits[f] += 1
                else:
                    doc["errors"].append(f"{f}: got {pred.get(f)!r}, expected {truth[f]!r}")
            if len(pred["line_items"]) == len(truth["line_items"]) and all(
                same(p["total"], t["total"]) for p, t in zip(pred["line_items"], truth["line_items"])
            ):
                items_ok += 1
        else:
            doc["errors"].append(res.error)
        status = "OK " if res.ok and not doc["errors"] else "ERR"
        print(f"[{status}] {pdf.name}  {res.latency_s:.1f}s  {'; '.join(doc['errors'])[:120]}")
        per_doc.append(doc)
        time.sleep(args.sleep)

    n = len(pdfs)
    total_fields = sum(field_hits.values())
    summary = {
        "model": client.model,
        "documents": n,
        "schema_valid_rate": round(valid / n, 3),
        "field_accuracy": round(total_fields / (n * len(FIELDS)), 3),
        "line_items_exact_rate": round(items_ok / n, 3),
        "avg_latency_s": round(sum(latencies) / n, 2),
        "per_field_accuracy": {f: round(h / n, 3) for f, h in field_hits.items()},
    }
    print("\n" + json.dumps(summary, indent=2))
    out = ROOT / "results"; out.mkdir(exist_ok=True)
    (out / "extraction_eval.json").write_text(json.dumps({"summary": summary, "documents": per_doc}, indent=2))
    print(f"\nSaved to results/extraction_eval.json")


if __name__ == "__main__":
    main()
