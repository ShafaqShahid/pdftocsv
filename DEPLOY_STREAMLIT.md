# Fix "Conversion failed" on Streamlit

You are seeing the **old app** if the error says only:

> Conversion failed  
> Tips: Use a PDF from your bank's website…

The **new app (v2.3.0)** says:

> **Conversion failed (v2.3.0)**  
> and shows PDF pages / characters on page 1

## Steps (do all of them)

### 1. Push code

```powershell
cd "C:\Users\Shafaq\Desktop\pdf to csv"
git add .
git commit -m "v2.3.0 Streamlit fix pypdf primary app.py"
git push
```

### 2. Streamlit Cloud settings

1. Go to https://share.streamlit.io → your app → **Manage app**
2. **Main file path:** set to `app.py` (or `streamlit_app.py`)
3. Click **Save**
4. Click **Reboot app** and wait until status is Running

### 3. Verify version

Open the app. Sidebar must show **Version 2.3.0**.

If not, the deploy did not update — repeat step 2.

### 4. Convert your PDF

Use the Monzo PDF downloaded from the website (not a photo).

## Still failing?

On the error screen, check **characters on page 1**:

- **0–50** → PDF has no readable text (scanned PDF)
- **500+** → Text is readable; open an issue with the page 1 sample shown
