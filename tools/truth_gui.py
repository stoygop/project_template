from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path

from tools.truth_manager import (
    REPO_ROOT,
    CONFIG_JSON,
    TruthConfig,
    read_project_and_truth_version,
    mint_truth,
)


class TruthTextDialog(simpledialog.Dialog):
    def body(self, master):
        self.txt = tk.Text(master, width=88, height=18)
        self.txt.pack(fill="both", expand=True)
        return self.txt

    def apply(self):
        self.result = self.txt.get("1.0", "end-1c")


class TruthGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Truth Manager")
        self.geometry("780x520")

        self.cfg = TruthConfig.load(CONFIG_JSON)

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        self.lbl_status = tk.Label(top, text="", font=("Segoe UI", 12))
        self.lbl_status.pack(side="left")

        tk.Button(top, text="Refresh", command=self.refresh).pack(side="right")

        mid = tk.Frame(self)
        mid.pack(fill="x", padx=10)

        tk.Button(mid, text="Mint New Truth", command=self.on_mint, height=2).pack(side="left")
        tk.Button(mid, text="Open _truth Folder", command=self.open_truth_folder, height=2).pack(side="left", padx=10)
        tk.Button(mid, text="Save Config", command=self.save_config, height=2).pack(side="left")

        sep = tk.Frame(self, height=2, bd=1, relief="sunken")
        sep.pack(fill="x", padx=10, pady=10)

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=5)

        left = tk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="SLIM Exception Folders (excluded from SLIM zip):").pack(anchor="w")
        self.list_exc = tk.Listbox(left, height=16)
        self.list_exc.pack(fill="both", expand=True, pady=6)

        right = tk.Frame(body)
        right.pack(side="right", fill="y", padx=(10, 0))

        tk.Button(right, text="Add Folder", command=self.add_folder).pack(fill="x", pady=2)
        tk.Button(right, text="Remove Selected", command=self.remove_selected).pack(fill="x", pady=2)

        self.refresh()

    def refresh(self) -> None:
        project, cur = read_project_and_truth_version()
        self.lbl_status.config(text=f"{project} — TRUTH_V{cur}")

        self.cfg = TruthConfig.load(CONFIG_JSON)
        self.list_exc.delete(0, tk.END)
        for f in self.cfg.slim_exclude_folders:
            self.list_exc.insert(tk.END, f)

    def add_folder(self) -> None:
        p = filedialog.askdirectory(initialdir=str(REPO_ROOT))
        if not p:
            return
        pth = Path(p).resolve()
        try:
            rel = pth.relative_to(REPO_ROOT)
        except Exception:
            messagebox.showerror("Invalid folder", "Folder must be inside the project root.")
            return

        rel_str = str(rel).replace("\\", "/").strip("/")
        if not rel_str:
            messagebox.showerror("Invalid folder", "Cannot exclude the repo root.")
            return

        token = rel_str.split("/")[0]
        if token not in self.cfg.slim_exclude_folders:
            self.cfg.slim_exclude_folders.append(token)
            self.refresh()

    def remove_selected(self) -> None:
        sel = list(self.list_exc.curselection())
        if not sel:
            return
        for idx in reversed(sel):
            val = self.list_exc.get(idx)
            if val in self.cfg.slim_exclude_folders:
                self.cfg.slim_exclude_folders.remove(val)
        self.refresh()

    def save_config(self) -> None:
        self.cfg.save(CONFIG_JSON)
        messagebox.showinfo("Saved", f"Saved {CONFIG_JSON}")

    def on_mint(self) -> None:
        project, cur = read_project_and_truth_version()
        new_ver = cur + 1

        if not messagebox.askyesno("Mint Truth", f"Mint TRUTH_V{new_ver}?"):
            return

        txt = TruthTextDialog(self, title=f"TRUTH_V{new_ver} Statement").result
        if txt is None or not txt.strip():
            messagebox.showerror("No statement", "Truth statement cannot be empty.")
            return

        try:
            v, full_zip, slim_zip = mint_truth(txt)
        except Exception as e:
            messagebox.showerror("Mint failed", str(e))
            self.refresh()
            return

        self.refresh()
        messagebox.showinfo("Minted", f"OK: minted TRUTH_V{v}\n\nFULL:\n{full_zip}\n\nSLIM:\n{slim_zip}")

    def open_truth_folder(self) -> None:
        import subprocess

        cfg = TruthConfig.load(CONFIG_JSON)
        truth_dir = (REPO_ROOT / cfg.zip_root).resolve()
        truth_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(truth_dir)])


if __name__ == "__main__":
    app = TruthGUI()
    app.mainloop()
