from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out, _ = p.communicate()
    return p.returncode, out


class DraftTextDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Paste TRUTH statement (end with 'END' line).").pack(anchor="w")
        self.txt = scrolledtext.ScrolledText(master, width=100, height=24)
        self.txt.pack(fill="both", expand=True)
        return self.txt

    def apply(self):
        self.result = self.txt.get("1.0", "end").strip() + "\n"


class StoplightGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stoplight Truth Control")
        self.geometry("900x620")

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        self.phase_lbl = tk.Label(top, text="Phase: (unknown)", font=("Segoe UI", 12, "bold"), width=22)
        self.phase_lbl.pack(side="left")

        self.ver_lbl = tk.Label(top, text="TRUTH_V?: ?", font=("Segoe UI", 11))
        self.ver_lbl.pack(side="left", padx=(10, 0))

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=10, pady=6)

        self.btn_refresh = tk.Button(btns, text="Refresh Phase", command=self.refresh)
        self.btn_open = tk.Button(btns, text="Open Draft", command=self.open_draft)
        self.btn_mint = tk.Button(btns, text="Mint/Overwrite Draft", command=self.mint_draft)
        self.btn_confirm = tk.Button(btns, text="Confirm Draft", command=self.confirm_draft)
        self.btn_revert = tk.Button(btns, text="Revert Draft", command=self.revert_draft)
        self.btn_doc_pre = tk.Button(btns, text="Doctor PRE", command=lambda: self.run_doctor("pre"))
        self.btn_doc_post = tk.Button(btns, text="Doctor POST", command=lambda: self.run_doctor("post"))
        self.btn_open_folders = tk.Button(btns, text="Open Folders", command=self.open_folders)

        for i, b in enumerate(
            [
                self.btn_refresh,
                self.btn_open,
                self.btn_mint,
                self.btn_confirm,
                self.btn_revert,
                self.btn_doc_pre,
                self.btn_doc_post,
                self.btn_open_folders,
            ]
        ):
            b.grid(row=0, column=i, padx=4, pady=4)

        self.log = scrolledtext.ScrolledText(self, width=110, height=28)
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh()

    def log_line(self, s: str):
        self.log.insert("end", s.rstrip() + "\n")
        self.log.see("end")

    def _status(self) -> dict:
        rc, out = _run([PYTHON, "-m", "tools.truth_manager", "status", "--json"])
        if rc != 0:
            return {"error": out.strip(), "draft_pending": None, "next": None, "confirmed": None, "project": None}
        try:
            return json.loads(out)
        except Exception:
            return {"error": f"Failed to parse status JSON:\n{out}", "draft_pending": None}

    def refresh(self):
        st = self._status()
        if "error" in st and st["error"]:
            self.phase_lbl.config(text="Phase: ERROR", bg="gray", fg="white")
            self.ver_lbl.config(text="Status error")
            self.log_line(st["error"])
            return

        confirmed = st.get("confirmed")
        nxt = st.get("next")
        pending = st.get("draft_pending")
        self.ver_lbl.config(text=f"Current: V{confirmed}  Next: V{nxt}")

        if pending:
            self.phase_lbl.config(text="Phase: Draft (🔴)", bg="red", fg="white")
        else:
            self.phase_lbl.config(text="Phase: No Draft", bg="gray", fg="white")

        has_draft = bool(pending and pending.get("path"))
        self.btn_open.config(state=("normal" if has_draft else "disabled"))
        self.btn_confirm.config(state=("normal" if has_draft else "disabled"))
        self.btn_revert.config(state=("normal" if has_draft else "disabled"))

        self.log_line("Refreshed.")
        if pending:
            self.log_line(f"Draft: V{pending.get('ver')}  {pending.get('path')}")
        else:
            self.log_line("No pending draft found.")

    def open_draft(self):
        st = self._status()
        pending = st.get("draft_pending")
        if not pending:
            messagebox.showinfo("No draft", "No draft to open.")
            return
        p = Path(pending["path"])
        if not p.exists():
            messagebox.showerror("Missing file", f"Draft path not found:\n{p}")
            return
        # open with default editor
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["cmd", "/c", "start", "", str(p)], cwd=str(REPO_ROOT))
            else:
                subprocess.Popen(["open", str(p)], cwd=str(REPO_ROOT))
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def mint_draft(self):
        dlg = DraftTextDialog(self, title="Mint/Overwrite Draft")
        if not dlg.result:
            return

        # Write input to canonical draft input file for CLI consumption
        draft_dir = REPO_ROOT / "_truth_drafts"
        draft_dir.mkdir(exist_ok=True)
        input_path = draft_dir / "_draft_input.txt"
        input_path.write_text(dlg.result, encoding="utf-8")

        self.log_line(f"Minting draft from: {input_path}")
        rc, out = _run([PYTHON, "-m", "tools.truth_manager", "mint-draft", "--statement-file", str(input_path), "--overwrite"])
        self.log_line(out)
        if rc == 0:
            messagebox.showinfo("OK", "Draft minted/updated.")
        else:
            messagebox.showerror("Mint failed", out[-2000:] if out else "Unknown error")
        self.refresh()

    def confirm_draft(self):
        if not messagebox.askyesno("Confirm Draft", "Confirm draft? This will bump TRUTH_VERSION and generate artifacts."):
            return
        self.log_line("Confirming draft...")
        p = subprocess.Popen([PYTHON, "-m", "tools.truth_manager", "confirm-draft"], cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out, _ = p.communicate()
        self.log_line(out)
        if p.returncode == 0:
            messagebox.showinfo("OK", "Draft confirmed.")
        else:
            messagebox.showerror("Confirm failed", out[-2000:] if out else "Unknown error")
        self.refresh()

    def revert_draft(self):
        self.log_line("Reverting draft from backup...")
        rc, out = _run([PYTHON, "-m", "tools.truth_manager", "revert-draft"])
        self.log_line(out)
        if rc == 0:
            messagebox.showinfo("OK", "Draft reverted from backup.")
        else:
            messagebox.showerror("Revert failed", out[-2000:] if out else "Unknown error")
        self.refresh()

    def run_doctor(self, phase: str):
        self.log_line(f"Running doctor ({phase})...")
        rc, out = _run([PYTHON, "-m", "tools.doctor", "--phase", phase])
        self.log_line(out)
        if rc == 0:
            messagebox.showinfo("OK", f"Doctor {phase}: OK")
        else:
            messagebox.showerror("Doctor failed", out[-2000:] if out else "Unknown error")

    def open_folders(self):
        # open repo root, _truth, _ai_index, _truth_drafts if exist
        targets = [REPO_ROOT, REPO_ROOT / "_truth", REPO_ROOT / "_ai_index", REPO_ROOT / "_truth_drafts", REPO_ROOT / "_truth_backups"]
        for t in targets:
            if not t.exists():
                continue
            try:
                if sys.platform.startswith("win"):
                    subprocess.Popen(["explorer", str(t)])
                else:
                    subprocess.Popen(["open", str(t)])
            except Exception:
                pass


def main() -> int:
    app = StoplightGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())