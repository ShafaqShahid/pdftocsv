"""Single entry point for PDF → CSV conversion (used by Streamlit and CLI)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from parser.orchestrator import PipelineOrchestrator


def convert_pdf_bytes(
    pdf_bytes: bytes,
    debug: bool = False,
    fast_mode: bool = True,
) -> tuple[bytes | None, dict[str, Any]]:
    """
    Convert PDF bytes to CSV bytes.
    Returns (csv_bytes, info_dict).
    """
    info: dict[str, Any] = {
        "success": False,
        "partial": False,
        "row_count": 0,
        "template": "",
        "strategy": "",
        "errors": [],
        "warnings": [],
        "pages": 0,
        "chars_page1": 0,
        "page1_sample": "",
    }

    if not pdf_bytes or len(pdf_bytes) < 100:
        info["errors"].append("File is empty or not a valid PDF.")
        return None, info

    from parser.pdf_reader import pdf_page_count, read_pdf_page_text

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "statement.pdf"
        csv_path = Path(tmp) / "output.csv"
        pdf_path.write_bytes(pdf_bytes)

        info["pages"] = pdf_page_count(pdf_path)
        sample = read_pdf_page_text(pdf_path, 0)
        info["chars_page1"] = len(sample)
        info["page1_sample"] = sample[:2000]

        orch = PipelineOrchestrator(debug=debug, fast_mode=fast_mode)
        result = orch.run(pdf_path, csv_path)

        info["template"] = result.template_name
        info["strategy"] = result.strategy
        info["errors"] = result.errors
        info["warnings"] = result.warnings
        info["row_count"] = result.row_count
        info["success"] = result.success
        info["partial"] = result.partial

        if result.output_path and result.output_path.exists():
            return result.output_path.read_bytes(), info

    return None, info
