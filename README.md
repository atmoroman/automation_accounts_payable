# ProcureMind — AI Assistant for Accounts Payable

ProcureMind automates the most manual part of procure-to-pay: reading supplier invoices, checking them against company policy, and flagging suspicious payments, while keeping a human in the loop for every payment decision.

> Built as a learning and portfolio project inspired by SAP Business AI scenarios (document information extraction, Joule-style assistants, AI agents for finance).

## Features

| # | Module | Status | AI techniques |
|---|---|---|---|
| 1 | **Invoice extraction**: PDF → validated structured JSON | Done | LLM, prompt engineering, JSON mode, Pydantic validation, self-repair loop |
| 2 | **Policy Q&A (RAG)**: "Can I pay this invoice?" answered from policy documents with citations | Next | Embeddings, chunking, vector search, grounding |
| 3 | **Anomaly detection**: duplicate, spiked or suspicious invoices | Planned | Isolation Forest, feature engineering, precision/recall |
| 4 | **AI agent**: checks budget and supplier history, drafts a purchase order | Planned | Function calling / tool use, ReAct |
| 5 | **Evaluation & Responsible AI** | Partial | Ground-truth eval, PII masking, audit log |

## Architecture (Module 1)

```
PDF ──► text extraction (pypdf) ──► LLM in JSON mode ──► Pydantic schema validation
                                          ▲                     │ invalid?
                                          └──── self-repair ◄───┘ (1 retry with error message)
                                                                │ valid
                                                                ▼
                                            business-rule checks (totals add up, dates consistent)
                                                                ▼
                                                   Invoice + warnings ──► UI / downstream
```

**Design decisions**
- **Provider-agnostic LLM layer**: one OpenAI-compatible client works with Groq and Google Gemini; switching takes one line in `.env`.
- **Don't trust the LLM**: every output is schema-validated, and amounts are re-computed with plain code (`consistency_checks`).
- **Temperature 0** for deterministic extraction.
- **Testable**: the LLM sits behind a small interface, so unit tests use a fake client and need no API key.
- **Measured, not guessed**: `scripts/evaluate_extraction.py` scores every field against ground truth.

## Quick start

```bash
git clone https://github.com/<you>/procuremind.git && cd procuremind
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # then paste your free Groq or Gemini API key
python scripts/generate_data.py --n 20                 # synthetic invoices + ground truth
streamlit run app.py                                   # demo UI
python scripts/evaluate_extraction.py                  # accuracy report
pytest -q                                              # unit tests (no API key needed)
```

## Results

| Metric | Value |
|---|---|
| Schema-valid outputs | _run evaluation_ |
| Field-level accuracy | _run evaluation_ |
| Line items exactly correct | _run evaluation_ |
| Avg latency per invoice | _run evaluation_ |

*Dataset: 20 synthetic invoices, 2 layouts, 4 currencies, EU and UK number and date formats.*

## Data

All data is synthetic (`scripts/generate_data.py`):
- `data/invoices/` — PDF invoices in two different layouts (EU `1.234,56` and UK `1,234.56` formats)
- `data/ground_truth/` — correct values for evaluation
- `data/policies/` — six procurement policies (approval limits, three-way match, supplier and payment rules, AI usage policy) for the RAG module
- `data/invoice_history.csv` — 3,000 historical invoices with ~3% labelled anomalies for the ML module

## Project structure

```
procuremind/
├── procuremind/        # library code
│   ├── config.py       # provider / model settings from .env
│   ├── llm.py          # OpenAI-compatible client with retry + backoff
│   ├── schemas.py      # Pydantic Invoice model + business-rule checks
│   ├── pdf_utils.py    # PDF → text
│   └── extraction.py   # Module 1 pipeline
├── scripts/            # data generation, evaluation
├── tests/              # unit tests with a fake LLM
├── data/               # synthetic dataset
└── app.py              # Streamlit UI
```

## Roadmap
- [ ] RAG over `data/policies` with local embeddings (sentence-transformers + ChromaDB)
- [ ] Anomaly detection notebook on `invoice_history.csv`
- [ ] Tool-using agent (budget check, supplier history, PO draft via SAP Business Accelerator Hub sandbox API)
- [ ] PII masking before LLM calls, audit log of AI decisions
- [ ] OCR for scanned invoices, Docker image

## License
MIT
