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
from utils.logging_setup import setup_logging

st.set_page_config(
    page_title="Bank Statement PDF → CSV",
    page_icon="📄",
    layout="centered",
)

st.title("Bank Statement PDF → CSV")
st.caption(
    "Upload a bank statement PDF and download a structured CSV. "
    "No install needed — runs in the cloud."
)

with st.sidebar:
    st.header("Options")
    debug = st.checkbox("Debug mode", help="More detailed logs (for troubleshooting)")
    fast_mode = st.checkbox(
        "Fast mode (recommended)",
        value=True,
        help="Skips slow Camelot step. Usually finishes in under a minute.",
    )
    st.markdown("---")
    st.markdown("**Supported banks (auto-detected)**")
    st.markdown("Monzo · HSBC · Barclays · Generic UK")
    st.markdown("---")
    st.markdown(
        "Works best with **digital PDFs** (not phone photos). "
        "Large statements may take 1–2 minutes."
    )

uploaded = st.file_uploader(
    "Choose a PDF bank statement",
    type=["pdf"],
    help="Your file is processed in memory and not stored permanently.",
)

if uploaded is not None:
    st.info(f"**{uploaded.name}** · {uploaded.size / 1024:.1f} KB")

    if uploaded.size > 15 * 1024 * 1024:
        st.warning("Large file (>15 MB) — conversion may take several minutes or time out.")

    if st.button("Convert to CSV", type="primary", use_container_width=True):
        run_id = uuid.uuid4().hex[:8]
        setup_logging(debug=debug)
        orchestrator = PipelineOrchestrator(
            debug=debug, run_id=run_id, fast_mode=fast_mode
        )

        csv_bytes: bytes | None = None
        result = None
        debug_text_sample = ""

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Safe filename (avoids path/encoding issues on Streamlit Cloud)
            pdf_path = tmp_path / "statement.pdf"
            csv_path = tmp_path / "output.csv"
            pdf_bytes = uploaded.getvalue()
            if not pdf_bytes:
                st.error("Uploaded file is empty.")
                st.stop()
            pdf_path.write_bytes(pdf_bytes)

            if debug:
                try:
                    import pdfplumber

                    with pdfplumber.open(pdf_path) as pdf:
                        debug_text_sample = (pdf.pages[0].extract_text() or "")[:500]
                except Exception as ex:
                    debug_text_sample = f"PDF read error: {ex}"

            with st.status("Extracting transactions…", expanded=True) as status:
                def on_progress(msg: str) -> None:
                    status.write(msg)

                orchestrator.set_progress_callback(on_progress)
                result = orchestrator.run(pdf_path, csv_path)

                if result.success:
                    status.update(label="Done!", state="complete")
                elif result.partial:
                    status.update(
                        label=f"Partial — {result.row_count} rows exported",
                        state="complete",
                    )
                else:
                    status.update(label="No rows extracted", state="error")

            if result and result.output_path and result.output_path.exists():
                csv_bytes = result.output_path.read_bytes()

        has_csv = csv_bytes is not None and len(csv_bytes) > 0

        if has_csv and result:
            if result.success:
                st.success(
                    f"Extracted **{result.row_count}** transactions "
                    f"({result.template_name} · {result.strategy or 'pipeline'})"
                )
            elif result.partial:
                st.warning(
                    f"**Partial conversion** — **{result.row_count}** of "
                    f"**{result.rows_extracted}** extracted rows saved. "
                    f"Review the CSV; some rows may be missing or need fixing."
                )
            else:
                st.info(f"Exported **{result.row_count}** rows.")

            if result.errors:
                with st.expander(f"Issues ({len(result.errors)})", expanded=result.partial):
                    for err in result.errors[:40]:
                        st.text(err)

            if result.warnings:
                with st.expander(f"Warnings ({len(result.warnings)})", expanded=False):
                    for w in result.warnings[:40]:
                        st.text(w)

            st.download_button(
                label="Download CSV"
                + (" (partial)" if result.partial else ""),
                data=csv_bytes,
                file_name=f"{Path(uploaded.name).stem}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )

            with st.expander("Preview first rows"):
                st.text(csv_bytes.decode("utf-8")[:3000])

        elif result:
            st.error("Could not extract any transactions from this PDF.")
            for err in result.errors:
                st.markdown(f"- {err}")
            st.markdown(
                f"**Detected:** {result.template_name or 'unknown'} bank template · "
                f"**Strategy tried:** {result.strategy or 'none'}"
            )
            if debug and debug_text_sample:
                st.code(
                    debug_text_sample
                    if debug_text_sample
                    else "(no text on page 1 — scanned PDF?)"
                )
            st.markdown(
                "**Tips:**\n"
                "- Use a PDF downloaded from your bank (not a photo scan)\n"
                "- Push the latest code to GitHub and redeploy Streamlit\n"
                "- Enable **Debug mode** to see if page 1 has readable text"
            )

else:
    st.markdown(
        """
        ### How to use
        1. **Browse files** → select your bank statement PDF  
        2. **Convert to CSV** (keep *Fast mode* on)  
        3. **Download CSV** → open in Excel or Google Sheets  

        If conversion is incomplete, you can still **download a partial CSV** with the rows we found.
        """
    )
