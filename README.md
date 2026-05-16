# PDF Bank Statement to CSV Extractor

Production-ready Python tool to convert bank statement PDFs into structured CSV files with high accuracy. Extracts transactions in order with columns: **Date**, **Description**, **Amount**, **Balance**.

## Features

- Multi-strategy extraction: Camelot (lattice/stream) → pdfplumber → regex fallback
- Bank template detection (Monzo, HSBC, Barclays, generic)
- Multi-line description merging
- Header/footer and duplicate removal
- Validation (dates, amounts, balance continuity)
- CLI single-file and batch modes
- Debug mode with intermediate artifacts
- Docker support and GitHub Actions CI

## Requirements

- Python 3.11+
- [Ghostscript](https://ghostscript.com/) (required for Camelot)

### Windows Ghostscript

Install Ghostscript and optionally set:

```powershell
$env:GS_PATH = "C:\Program Files\gs\gs10.xx.x\bin\gswin64c.exe"
```

## Installation

```bash
git clone <your-repo-url>
cd pdf-to-csv

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Web UI (no Python install)

Use the app in your browser after deploying to **Streamlit Cloud** (free, linked to GitHub):

1. Push this repo to GitHub (see [DEPLOY.md](DEPLOY.md)).
2. Deploy at [share.streamlit.io](https://share.streamlit.io) with main file `streamlit_app.py`.
3. Open your app URL → upload PDF → download CSV.

**GitHub Pages cannot run this tool** (it needs Python server-side). Streamlit Cloud is the recommended free option.

## Usage (command line)

### Single PDF

```bash
python main.py statement.pdf output.csv
```

### Batch mode

Place PDFs in a folder and run:

```bash
python main.py ./pdfs ./outputs
```

Each `statement.pdf` becomes `outputs/statement.csv`.

### Debug mode

```bash
python main.py statement.pdf output.csv --debug
```

Writes verbose logs to `logs/` and intermediate tables to `logs/debug/`.

## Project structure

```
├── main.py                 # CLI entry point
├── config.py               # Regex patterns, footer keywords, settings
├── csv_generator.py        # Pandas CSV output
├── parser/                 # Extraction and reconstruction
├── validators/             # Row validation and balance checks
├── utils/                  # Dates, amounts, logging
├── tests/                  # Pytest suite
├── logs/                   # Runtime logs (gitignored)
└── sample_output/          # Example CSV format
```

## Adding a new bank template

1. Create `parser/templates/yourbank.py` subclassing `BankTemplate`
2. Implement `detect_score()` with bank-specific keywords
3. Override `normalize_row()` if column layout differs
4. Register in `parser/bank_detector.py` → `ALL_TEMPLATES`

## Calibrating with your first PDF

1. Run with `--debug`
2. Check `logs/parsing_*.log` for detected template and strategy
3. Inspect `logs/debug/` for raw extraction output
4. Tune regex and column logic in the matching template file
5. Add anonymized test fixtures (never commit real account data)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No rows extracted | PDF may be scanned/image-only; text extraction returns empty |
| Wrong columns | Run `--debug`, check template detection, adjust template |
| Camelot errors | Ensure Ghostscript is installed; pdfplumber/regex still run as fallback |
| Wrapped descriptions split | Row reconstructor merges lines without date anchors |

## Docker

```bash
docker compose build
mkdir -p pdfs outputs
# Copy PDFs into pdfs/
docker compose run --rm parser python main.py /data/in/statement.pdf /data/out/statement.csv
```

Batch:

```bash
docker compose run --rm parser python main.py /data/in /data/out
```

## Deployment (another machine)

```bash
git clone <repo>
cd pdf-to-csv
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
# Install Ghostscript on the host
python main.py /path/to/statements ./outputs
```

## GitHub setup

1. Push this repository to GitHub
2. CI runs automatically on push/PR to `main` (see `.github/workflows/test.yml`)
3. Clone on any machine and follow Installation above

## Running tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=parser --cov=validators
```

## Example output

See [`sample_output/example.csv`](sample_output/example.csv).

## License

MIT (adjust as needed for your project).
