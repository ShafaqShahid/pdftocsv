# Deploy the web UI (no Python on your computer)

GitHub Pages **cannot** run this Python parser. Use **Streamlit Cloud** (free): it connects to your GitHub repo and gives you a public link like `https://your-app.streamlit.app`.

## Step 1 — Push code to GitHub

```bash
cd "c:\Users\Shafaq\Desktop\pdf to csv"
git init
git add .
git commit -m "Add PDF to CSV extractor with web UI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pdf-to-csv.git
git push -u origin main
```

(Create the empty repo on GitHub first: **New repository** → name it `pdf-to-csv`.)

## Step 2 — Deploy on Streamlit Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.
2. Click **New app**.
3. Select your repo `pdf-to-csv` and branch `main`.
4. Set **Main file path** to: `streamlit_app.py`
5. Click **Deploy**.

First deploy may take 5–10 minutes (installs Python packages + Ghostscript from `packages.txt`).

## Step 3 — Use the site

1. Open your app URL (e.g. `https://pdf-to-csv-xxx.streamlit.app`).
2. **Browse files** → choose your bank statement PDF.
3. Click **Convert to CSV**.
4. Click **Download CSV**.

No Python install on your PC.

## Updating the app

Push changes to GitHub:

```bash
git add .
git commit -m "Update parser"
git push
```

Streamlit Cloud redeploys automatically.

## Limits (free tier)

- PDF size: about 50 MB (see `.streamlit/config.toml`).
- Scanned/image-only PDFs may fail (no OCR in v1).
- Cold start: first visit after idle can be slow.

## Alternative hosts

| Host | Notes |
|------|--------|
| [Streamlit Cloud](https://share.streamlit.io) | Easiest, free, uses this repo |
| [Hugging Face Spaces](https://huggingface.co/spaces) | Docker/SDK, good for heavier deps |
| GitHub Pages | Static only — would need a full JavaScript rewrite |

## Privacy

Uploaded PDFs are processed in the Streamlit server session and are not saved by this app code. For sensitive statements, deploy your own private Streamlit app or run locally with Docker.
