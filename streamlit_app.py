"""
Web UI for PDF bank statement → CSV conversion.
Deploy free on Streamlit Cloud (connected to your GitHub repo).
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import streamlit as st

from parser.orchestrator import PipelineOrchestrator
from parser.pdf_reader import pdf_page_count, read_pdf_page_text
from utils.logging_setup import setup_logging

APP_VERSION = "2.2.0"

st.set_page_config(
    page_title="Bank Statement PDF → CSV",
    page_icon="📄",
    layout="centered",
)

st.title("Bank Statement PDF → CSV")
st.caption(f"Version {APP_VERSION} · Upload a digital bank statement PDF")

with st.sidebar:
    st.header("Options")
    debug = st.checkbox("Debug mode", help="Show PDF text sample if conversion fails")
    st.markdown("**Fast mode is always on** for cloud (reliable).")
    st.markdown("---")
    st.markdown("**Best results:** Monzo Business PDF from app/web")
    st.markdown("---")
    st.caption(f"App version: **{APP_VERSION}**")

uploaded = st.file_uploader(
    "Choose a PDF bank statement",
    type=["pdf"],
    help="Digital PDF from your bank — not a photo or screenshot.",
)

if uploaded is not None:
    st.info(f"**{uploaded.name}** · {uploaded.size / 1024:.1f} KB")

    if uploaded.size > 15 * 1024 * 1024:
        st.warning("Large file (>15 MB) — may take 1–2 minutes.")

    if st.button("Convert to CSV", type="primary", use_container_width=True):
        run_id = uuid.uuid4().hex[:8]
        setup_logging(debug=True)
        orchestrator = PipelineOrchestrator(
            debug=True, run_id=run_id, fast_mode=True
        )

        csv_bytes: bytes | None = None
        result = None
        diag_pages = 0
        diag_chars = 0
        diag_sample = ""

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / "statement.pdf"
            csv_path = tmp_path / "output.csv"
            pdf_bytes = uploaded.getvalue()
            if not pdf_bytes or len(pdf_bytes) < 100:
                st.error("Uploaded file is empty or too small to be a valid PDF.")
                st.stop()
            pdf_path.write_bytes(pdf_bytes)

            diag_pages = pdf_page_count(pdf_path)
            diag_sample = read_pdf_page_text(pdf_path, 0)
            diag_chars = len(diag_sample)

            with st.status("Extracting transactions…", expanded=True) as status:
                status.write(f"PDF: {diag_pages} pages, {diag_chars} chars on page 1")

                if diag_chars < 30:
                    status.write(
                        "⚠️ Very little text on page 1 — scanned PDFs may not work."
                    )

                def on_progress(msg: str) -> None:
                    status.write(msg)

                orchestrator.set_progress_callback(on_progress)
                result = orchestrator.run(pdf_path, csv_path)

                if result.success:
                    status.update(label="Done!", state="complete")
                elif result.partial:
                    status.update(
                        label=f"Partial — {result.row_count} rows",
                        state="complete",
                    )
                else:
                    status.update(label="Failed", state="error")

            if result and result.output_path and result.output_path.exists():
                csv_bytes = result.output_path.read_bytes()

        has_csv = csv_bytes is not None and len(csv_bytes) > 0

        if has_csv and result:
            st.success(
                f"**{result.row_count}** transactions · "
                f"{result.template_name} · {result.strategy}"
            )
            if result.warnings:
                with st.expander("Warnings"):
                    for w in result.warnings[:25]:
                        st.text(w)
            st.download_button(
                label="Download CSV",
                data=csv_bytes,
                file_name=f"{Path(uploaded.name).stem}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
            with st.expander("Preview"):
                st.text(csv_bytes.decode("utf-8")[:4000])

        elif result:
            st.error("Conversion failed — no transactions extracted.")
            st.markdown(
                f"**App version:** {APP_VERSION} · "
                f"**Bank:** {result.template_name} · "
                f"**Strategy:** {result.strategy or 'none'}"
            )
            st.markdown(
                f"**PDF check:** {diag_pages} pages · "
                f"{diag_chars} characters readable on page 1"
            )
            for err in result.errors:
                st.markdown(f"- {err}")

            if diag_sample:
                with st.expander("Page 1 text sample (what the parser sees)"):
                    st.code(diag_sample[:1500])
            else:
                st.warning(
                    "No text could be read from page 1. "
                    "Download the statement from your bank as PDF (not a scan)."
                )

            st.markdown(
                "**Next steps:**\n"
                "1. Confirm sidebar shows version **2.2.0** (else redeploy from GitHub)\n"
                "2. Use the original PDF from Monzo/bank website\n"
                "3. `git push` latest code and reboot Streamlit app"
            )
        else:
            st.error("Unexpected error — no result returned.")

else:
    st.markdown(
        """
        ### Steps
        1. Upload your bank statement PDF  
        2. Click **Convert to CSV**  
        3. Download the file  

        **Monzo Business** statements work best. Other banks may vary.
        """
    )
