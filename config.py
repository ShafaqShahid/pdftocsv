"""Central configuration for PDF bank statement extraction."""

from __future__ import annotations

import os
import re
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "logs"
DEBUG_DIR = LOGS_DIR / "debug"
SAMPLE_OUTPUT_DIR = PROJECT_ROOT / "sample_output"

# Output columns (fixed order)
OUTPUT_COLUMNS = ["Date", "Description", "Amount", "Balance"]

# Extraction strategy order (CLI / full mode — camelot is slow on cloud)
EXTRACTION_STRATEGIES = [
    "camelot_lattice",
    "camelot_stream",
    "pdfplumber",
    "regex",
]

# Fast mode for web/Streamlit: skip camelot, pdfplumber first
FAST_EXTRACTION_STRATEGIES = [
    "monzo_text",
    "pdfplumber",
    "regex",
]

# Per-strategy timeouts (seconds) — prevents infinite "loading"
STRATEGY_TIMEOUT_SECONDS = {
    "camelot_lattice": 45,
    "camelot_stream": 45,
    "monzo_text": 60,
    "pdfplumber": 90,
    "regex": 60,
}

# Auto fast mode on Streamlit Cloud
FAST_MODE = bool(
    os.environ.get("STREAMLIT_SERVER_PORT")
    or os.environ.get("STREAMLIT_RUNTIME_ENV")
    or os.environ.get("PDF_CSV_FAST_MODE", "").lower() in ("1", "true", "yes")
)

# Minimum quality score (0-1) to accept extraction result
QUALITY_SCORE_THRESHOLD = 0.5

# Bank detection
TEMPLATE_DETECT_THRESHOLD = 0.3

# Balance continuity tolerance
BALANCE_TOLERANCE = 0.02

# Ghostscript path (Windows / custom installs)
GS_PATH = os.environ.get("GS_PATH", "")

# Locale date patterns
DATE_PATTERNS: dict[str, list[str]] = {
    "uk": [
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"\d{1,2}-\d{1,2}-\d{2,4}",
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}",
        r"\d{1,2}\s+\d{1,2}\s+\d{4}",
    ],
    "us": [
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"\d{1,2}-\d{1,2}-\d{2,4}",
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}",
    ],
    "eu": [
        r"\d{1,2}\.\d{1,2}\.\d{2,4}",
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"\d{1,2}-\d{1,2}-\d{2,4}",
    ],
}

# Compiled date anchors (line start)
def _compile_date_anchors() -> dict[str, re.Pattern[str]]:
    anchors: dict[str, list[str]] = {}
    for locale, patterns in DATE_PATTERNS.items():
        combined = "|".join(f"(?:{p})" for p in patterns)
        anchors[locale] = re.compile(rf"^\s*({combined})\b", re.IGNORECASE)
    return anchors


DATE_ANCHORS = _compile_date_anchors()

# Amount patterns
AMOUNT_PATTERN = re.compile(
    r"(?:£|\$|€)?\s*"
    r"(?:\([\d,]+\.?\d*\)|"  # (123.45) negative
    r"-?[\d,]+\.?\d*)",
    re.IGNORECASE,
)

AMOUNT_AT_END = re.compile(
    r"(?:£|\$|€)?\s*"
    r"(?:\([\d,]+\.?\d*\)|-?[\d,]+\.?\d*)\s*$",
    re.IGNORECASE,
)

# Footer keywords (case-insensitive substring match)
FOOTER_KEYWORDS = [
    "page ",
    "page:",
    "continued",
    "continued on",
    "total payments",
    "total debits",
    "total credits",
    "balance brought forward",
    "balance carried forward",
    "statement period",
    "registered office",
    "fca registered",
    "sort code",
    "account number",
    "iban",
    "bic",
    "www.",
    "http",
    "call ",
    "telephone",
    "customer service",
]

# Header row patterns (column titles)
HEADER_PATTERNS = [
    re.compile(r"^date\b", re.I),
    re.compile(r"^description\b", re.I),
    re.compile(r"^details\b", re.I),
    re.compile(r"^narrative\b", re.I),
    re.compile(r"^money\s+out\b", re.I),
    re.compile(r"^money\s+in\b", re.I),
    re.compile(r"^debit\b", re.I),
    re.compile(r"^credit\b", re.I),
    re.compile(r"^amount\b", re.I),
    re.compile(r"^balance\b", re.I),
    re.compile(r"^paid\s+out\b", re.I),
    re.compile(r"^paid\s+in\b", re.I),
]

PAGE_NUMBER_PATTERN = re.compile(
    r"^\s*page\s+\d+\s+of\s+\d+\s*$",
    re.IGNORECASE,
)

# Debug mode saves intermediate artifacts
DEBUG_SAVE_INTERMEDIATE = True
