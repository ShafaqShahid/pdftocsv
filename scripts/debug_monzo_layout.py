import pdfplumber
from pathlib import Path
from collections import defaultdict

p = Path("pdfs/Monzo_bank_statement_2026-04-01-2026-05-01_4868_260501_123744.pdf")
with pdfplumber.open(p) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    lines = defaultdict(list)
    for w in words:
        y = round(w["top"] / 3) * 3
        lines[y].append(w)
    for y in sorted(lines.keys())[18:42]:
        ws = sorted(lines[y], key=lambda x: x["x0"])
        parts = [f"{w['text']}@{int(w['x0'])}" for w in ws]
        print(y, "|", " | ".join(parts))
