"""
Web UI for PDF bank statement → CSV conversion.
Streamlit Cloud: set Main file path to app.py or streamlit_app.py
"""

from __future__ import annotations

import uuid
from pathlib import Path

import streamlit as st

from convert import convert_pdf_bytes
from utils.logging_setup import setup_logging

APP_VERSION = "2.3.0"

st.set_page_config(
    page_title="Bank Statement PDF → CSV",
    page_icon="📄",
    layout="centered",
)

st.title("Bank Statement PDF → CSV")
st.sidebar.caption(f"**Version {APP_VERSION}**")

st.sidebar.markdown(
    "**Deploy check:** Sidebar must show **2.3.0**.  \n"
    "Old deploy says only *Conversion failed* with 3 tips."
)

uploaded = st.file_uploader("Choose a PDF bank statement", type=["pdf"])

if uploaded is not None:
    st.info(f"**{uploaded.name}** · {uploaded.size / 1024:.1f} KB")

    if st.button("Convert to CSV", type="primary", use_container_width=True):
        setup_logging(debug=True)
        pdf_bytes = uploaded.getvalue()

        with st.status("Converting…", expanded=True) as status:
            status.write(f"File size: {len(pdf_bytes)} bytes")

            csv_bytes, info = convert_pdf_bytes(pdf_bytes, debug=True, fast_mode=True)

            status.write(
                f"PDF: {info['pages']} pages · "
                f"{info['chars_page1']} chars on page 1"
            )
            status.write(f"Bank: {info['template']} · Strategy: {info['strategy'] or 'none'}")

            if info["success"]:
                status.update(label=f"Done — {info['row_count']} rows", state="complete")
            elif info["partial"]:
                status.update(label=f"Partial — {info['row_count']} rows", state="complete")
            else:
                status.update(label="Failed", state="error")

        if csv_bytes:
            st.success(
                f"**{info['row_count']}** rows · {info['template']} · {info['strategy']}"
            )
            if info["warnings"]:
                with st.expander("Warnings"):
                    for w in info["warnings"][:20]:
                        st.text(w)
            st.download_button(
                "Download CSV",
                data=csv_bytes,
                file_name=f"{Path(uploaded.name).stem}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
            with st.expander("Preview"):
                st.text(csv_bytes.decode("utf-8")[:4000])
        else:
            st.error(f"**Conversion failed (v{APP_VERSION})**")
            for e in info["errors"]:
                st.markdown(f"- {e}")
            if info["chars_page1"] < 50:
                st.warning(
                    "Almost no text on page 1 — use a PDF downloaded from your bank, "
                    "not a photo or scan."
                )
            if info["page1_sample"]:
                with st.expander("Page 1 text (what the server reads)"):
                    st.code(info["page1_sample"])
            else:
                st.warning("Could not read any text from page 1.")

else:
    st.markdown(
        """
        1. Upload PDF  
        2. Convert  
        3. Download CSV  

        **Monzo Business** PDFs work best.
        """
    )
