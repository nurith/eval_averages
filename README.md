# PDF Eval Extractor + Summary (Desktop UI)

This is a **local desktop app** (Tkinter) that bundles your `extract.py` and `calculate.py`.

## What it does
1. You choose a **folder** containing PDFs (optionally including subfolders)
2. It runs `extract.process_pdf_file()` on each PDF
3. Writes:
   - `results.json`
   - `results.csv`
   - `summary.txt` (Top1 / Top2 / Mean)

## Requirements
- Python 3.9+ (3.10+ recommended)
- Tkinter (usually included with Python on Windows/macOS; on some Linux distros you may need to install it)
- `pdftotext` (Poppler) installed on your system (required by `extract.py`)

### Install Poppler (pdftotext)
**Ubuntu/Debian**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

**macOS (Homebrew)**
```bash
brew install poppler
```

**Windows**
- Install Poppler for Windows and ensure `pdftotext.exe` is on your PATH.
  (Common approach: download a Poppler release, then add its `bin` folder to PATH.)

## Run
From the folder containing `desktop_ui.py`:
```bash
python desktop_ui.py
```

## Notes
- Results are written to the output folder you choose (default: the current directory).
- If you get errors about `pdftotext` not found, install Poppler and ensure it is on your PATH.
