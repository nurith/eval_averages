#!/usr/bin/env python3
"""Desktop UI for running extract.py over a local PDF directory and computing summary via calculate.py.

- Pick a folder containing PDFs
- Run extraction (uses extract.process_pdf_file)
- Saves results.json and results.csv
- Computes Top1/Top2/Mean (uses calculate.Rating)
"""

import csv
import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import extract
import calculate


def _safe_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows):
    if not rows:
        # write empty file with no headers
        path.write_text("", encoding="utf-8")
        return
    headers = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _compute_summary(extracted_rows):
    # extracted_rows are dicts from extract.process_pdf_file
    ratings = [calculate.Rating.from_dict(x) for x in extracted_rows]
    if not ratings:
        return None

    total = calculate.Rating.zero()
    for r in ratings:
        total = total.add(r)

    # calculate.py's main prints Top1/Top2/Mean using aggregated rating percentages.
    # We'll mirror that.
    return {
        "Top1_percent": total.get_top1(),
        "Top2_percent": total.get_top2(),
        "Mean": total.get_mean(),
    }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Eval Extractor + Summary (Desktop)")
        self.geometry("860x520")
        self.minsize(860, 520)

        self.pdf_dir = tk.StringVar(value="")
        self.out_dir = tk.StringVar(value=str(Path.cwd()))
        self.status = tk.StringVar(value="Choose a PDF folder to begin.")
        self.progress = tk.DoubleVar(value=0.0)

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)

        # Directory pickers
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text="PDF folder:").pack(side="left")
        ttk.Entry(row1, textvariable=self.pdf_dir).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(row1, text="Browse…", command=self.browse_pdf_dir).pack(side="left")

        row2 = ttk.Frame(frm)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="Output folder:").pack(side="left")
        ttk.Entry(row2, textvariable=self.out_dir).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(row2, text="Browse…", command=self.browse_out_dir).pack(side="left")

        # Options
        opt = ttk.Frame(frm)
        opt.pack(fill="x", **pad)
        self.include_subdirs = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="Include subfolders", variable=self.include_subdirs).pack(side="left")

        self.overwrite = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="Overwrite existing results", variable=self.overwrite).pack(side="left", padx=(20, 0))

        # Run button
        run_row = ttk.Frame(frm)
        run_row.pack(fill="x", **pad)
        self.run_btn = ttk.Button(run_row, text="Run", command=self.run, state="disabled")
        self.run_btn.pack(side="left")
        ttk.Button(run_row, text="Open output folder", command=self.open_out_dir).pack(side="left", padx=(10, 0))

        # Progress + status
        prog_row = ttk.Frame(frm)
        prog_row.pack(fill="x", **pad)
        self.pbar = ttk.Progressbar(prog_row, variable=self.progress, maximum=100)
        self.pbar.pack(side="left", fill="x", expand=True)
        ttk.Label(prog_row, textvariable=self.status).pack(side="left", padx=(10, 0))

        # Log box
        log_row = ttk.Frame(frm)
        log_row.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        ttk.Label(log_row, text="Log:").pack(anchor="w")
        self.log = tk.Text(log_row, height=16, wrap="word")
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        self.pdf_dir.trace_add("write", lambda *args: self._validate())
        self.out_dir.trace_add("write", lambda *args: self._validate())

    def _validate(self):
        pdf_ok = self.pdf_dir.get().strip() and Path(self.pdf_dir.get().strip()).exists()
        out_ok = self.out_dir.get().strip() and Path(self.out_dir.get().strip()).exists()
        self.run_btn.configure(state=("normal" if (pdf_ok and out_ok) else "disabled"))

    def browse_pdf_dir(self):
        d = filedialog.askdirectory(title="Select folder containing PDFs")
        if d:
            self.pdf_dir.set(d)

    def browse_out_dir(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.out_dir.set(d)

    def open_out_dir(self):
        d = self.out_dir.get().strip()
        if not d:
            return
        path = Path(d)
        if not path.exists():
            messagebox.showerror("Error", "Output folder does not exist.")
            return

        # Cross-platform open
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def run(self):
        pdf_dir = Path(self.pdf_dir.get().strip())
        out_dir = Path(self.out_dir.get().strip())

        if not pdf_dir.exists():
            messagebox.showerror("Error", "PDF folder does not exist.")
            return
        if not out_dir.exists():
            messagebox.showerror("Error", "Output folder does not exist.")
            return

        results_json = out_dir / "results.json"
        results_csv = out_dir / "results.csv"

        if (results_json.exists() or results_csv.exists()) and not self.overwrite.get():
            messagebox.showwarning(
                "Not overwriting",
                "results.json/results.csv already exist and overwrite is disabled.",
            )
            return

        self.run_btn.configure(state="disabled")
        self.progress.set(0.0)
        self.status.set("Scanning PDFs…")
        self._log("Starting run…")

        def worker():
            try:
                pattern = "**/*.pdf" if self.include_subdirs.get() else "*.pdf"
                pdfs = sorted(pdf_dir.glob(pattern))
                if not pdfs:
                    self._ui_done(error="No PDFs found in the selected folder.")
                    return

                self._ui_status(f"Found {len(pdfs)} PDFs. Extracting…")
                extracted = []
                total = len(pdfs)

                for i, p in enumerate(pdfs, start=1):
                    self._ui_status(f"Extracting {i}/{total}: {p.name}")
                    self._ui_progress((i - 1) / total * 100)

                    try:
                        row = extract.process_pdf_file(str(p))
                        if row is not None:
                            extracted.append(row)
                        else:
                            self._ui_log(f"[warn] No data extracted from: {p}")
                    except Exception as e:
                        self._ui_log(f"[error] Failed on {p}: {e}")

                self._ui_progress(100)
                self._ui_status("Writing results…")
                _write_json(results_json, extracted)
                _write_csv(results_csv, extracted)

                summary = _compute_summary(extracted)
                if summary:
                    summary_txt = (
                        f"Top1: {summary['Top1_percent']:.2f}%  "
                        f"Top2: {summary['Top2_percent']:.2f}%  "
                        f"Mean: {summary['Mean']:.3f}"
                    )
                    (out_dir / "summary.txt").write_text(summary_txt + "\n", encoding="utf-8")
                    self._ui_log("Summary: " + summary_txt)
                else:
                    self._ui_log("No summary (no extracted rows).")

                self._ui_log(f"Wrote: {results_json}")
                self._ui_log(f"Wrote: {results_csv}")
                self._ui_done(ok=True)
            except Exception as e:
                self._ui_done(error=str(e))

        threading.Thread(target=worker, daemon=True).start()

    # Thread-safe UI updates
    def _ui_log(self, msg):
        self.after(0, lambda: self._log(msg))

    def _ui_status(self, msg):
        self.after(0, lambda: self.status.set(msg))

    def _ui_progress(self, v):
        self.after(0, lambda: self.progress.set(v))

    def _ui_done(self, ok=False, error=None):
        def finish():
            if error:
                self.status.set("Failed")
                messagebox.showerror("Run failed", error)
            else:
                self.status.set("Done")
                if ok:
                    messagebox.showinfo("Done", "Extraction and summary complete.")
            self._validate()  # re-enable run button if inputs still valid
        self.after(0, finish)


if __name__ == "__main__":
    import sys  # needed in open_out_dir
    try:
        App().mainloop()
    except Exception as e:
        messagebox.showerror("Fatal error", str(e))
