"""Streamlit demo UI.  Run:  streamlit run app.py"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from procuremind.extraction import extract_from_pdf

ROOT = Path(__file__).parent
SAMPLES = sorted((ROOT / "data" / "invoices").glob("*.pdf"))

st.set_page_config(page_title="ProcureMind", layout="wide")
st.title("ProcureMind")
st.caption("AI assistant for accounts payable · Module 1: invoice data extraction")

with st.sidebar:
    st.header("Input")
    uploaded = st.file_uploader("Upload an invoice PDF", type=["pdf"])
    sample = st.selectbox("…or pick a sample", ["—"] + [p.name for p in SAMPLES])
    run = st.button("Extract", type="primary", use_container_width=True)

if run:
    if uploaded:
        tmp = Path(tempfile.mkdtemp()) / uploaded.name
        tmp.write_bytes(uploaded.getvalue())
        path = tmp
    elif sample != "—":
        path = ROOT / "data" / "invoices" / sample
    else:
        st.warning("Upload a PDF or choose a sample first.")
        st.stop()

    with st.spinner("Reading invoice with the LLM…"):
        try:
            res = extract_from_pdf(path)
        except Exception as e:  # show config/API problems nicely
            st.error(f"{type(e).__name__}: {e}")
            st.stop()

    if not res.ok:
        st.error(f"Extraction failed after {res.attempts} attempt(s): {res.error}")
        st.stop()

    inv = res.invoice
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Supplier", inv.supplier_name)
    c2.metric("Invoice #", inv.invoice_number)
    c3.metric("Total", f"{inv.total_amount:,.2f} {inv.currency}")
    c4.metric("Latency", f"{res.latency_s:.1f}s", help=f"model: {res.model}, attempts: {res.attempts}")

    if res.warnings:
        for w in res.warnings:
            st.warning(w)
    else:
        st.success("All business-rule checks passed (amounts add up, dates are consistent).")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Line items")
        st.dataframe(pd.DataFrame([li.model_dump() for li in inv.line_items]), use_container_width=True)
    with right:
        st.subheader("Structured output (JSON)")
        st.json(inv.model_dump(mode="json"))
else:
    st.info("Choose an invoice in the sidebar and press **Extract**.")
