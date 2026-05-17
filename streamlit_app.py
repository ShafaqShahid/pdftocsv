"""
Web UI for PDF bank statement → CSV conversion.
Streamlit Cloud main file: streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from convert import convert_pdf_bytes
from utils.logging_setup import setup_logging

APP_VERSION = "2.4.0"

st.set_page_config(
    page_title="Bank Statement PDF → CSV",
    page_icon="📄",
    layout="centered",
)

st.title("Bank Statement PDF → CSV")
st.sidebar.caption(f"**Version {APP_VERSION}**")
st.sidebar.markdown("Monzo Business PDFs · ~30–60 sec on cloud")

uploaded = st.file_uploader("Choose a PDF bank statement", type=["pdf"])

if uploaded is not None:
    st.info(f"**{uploaded.name}** · {uploaded.size / 1024:.1f} KB")

    if st.button("Convert to CSV", type="primary", use_container_width=True):
        setup_logging(debug=True)
        pdf_bytes = uploaded.getvalue()

        progress_msgs: list[str] = []

        with st.status("Converting…", expanded=True) as status:

            def on_step(msg: str) -> None:
                progress_msgs.append(msg)
                status.write(msg)

            on_step(f"File size: {len(pdf_bytes):,} bytes")

            try:
                csv_bytes, info = convert_pdf_bytes(
                    pdf_bytes,
                    debug=True,
                    fast_mode=True,
                    on_progress=on_step,
                )
            except Exception as ex:
                status.update(label="Error", state="error")
                st.exception(ex)
                st.stop()

            if info.get("success"):
                status.update(label=f"Done — {info['row_count']} rows", state="complete")
            elif info.get("partial"):
                status.update(label=f"Partial — {info['row_count']} rows", state="complete")
            else:
                status.update(label="Failed", state="error")

        if csv_bytes:
            st.success(
                f"**{info['row_count']}** rows · "
                f"{info['template']} · {info['strategy']}"
            )
            if info.get("warnings"):
                with st.expander("Warnings"):
                    for w in info["warnings"][:15]:
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
            st.markdown(
                f"Pages: **{info.get('pages', '?')}** · "
                f"Chars page 1: **{info.get('chars_page1', 0)}** · "
                f"Strategy: **{info.get('strategy') or 'none'}**"
            )
            for e in info.get("errors", []):
                st.markdown(f"- {e}")
            if info.get("page1_sample"):
                with st.expander("Page 1 text sample"):
                    st.code(info["page1_sample"][:1500])
            with st.expander("Conversion log"):
                st.text("\n".join(progress_msgs) if progress_msgs else "(no steps logged)")

else:
    st.markdown(
        """
        1. Upload PDF from your bank (digital download)  
        2. Click **Convert to CSV** — wait ~30–60 seconds  
        3. Download CSV  

        Sidebar must show **2.4.0**.
        """
    )
