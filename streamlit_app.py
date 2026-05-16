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

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / uploaded.name
            csv_path = tmp_path / f"{Path(uploaded.name).stem}.csv"
            pdf_path.write_bytes(uploaded.getvalue())

            with st.status("Extracting transactions…", expanded=True) as status:
                def on_progress(msg: str) -> None:
                    status.write(msg)

                orchestrator.set_progress_callback(on_progress)
                result = orchestrator.run(pdf_path, csv_path)
                if result.success:
                    status.update(label="Done!", state="complete")
                else:
                    status.update(label="Conversion failed", state="error")

        if result.success and result.output_path and result.output_path.exists():
            csv_bytes = result.output_path.read_bytes()
            st.success(
                f"Extracted **{result.row_count}** transactions "
                f"({result.template_name} · {result.strategy or 'pipeline'})"
            )

            if result.warnings:
                with st.expander(f"Warnings ({len(result.warnings)})", expanded=False):
                    for w in result.warnings[:30]:
                        st.text(w)

            st.download_button(
                label="Download CSV",
                data=csv_bytes,
                file_name=f"{Path(uploaded.name).stem}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )

            with st.expander("Preview first rows"):
                st.text(csv_bytes.decode("utf-8")[:2000])
        else:
            st.error("Conversion failed.")
            for err in result.errors:
                st.markdown(f"- {err}")
            st.markdown(
                "**Tips:**\n"
                "- Use a PDF from your bank’s website (not a scan/photo)\n"
                "- Keep **Fast mode** on\n"
                "- Try a smaller date range if the file is huge\n"
                "- Enable **Debug mode** and redeploy if it keeps failing"
            )

else:
    st.markdown(
        """
        ### How to use
        1. **Browse files** → select your bank statement PDF  
        2. **Convert to CSV** (keep *Fast mode* on)  
        3. **Download CSV** → open in Excel or Google Sheets  

        First conversion after deploy can take 1–2 minutes while the server wakes up.
        """
    )
