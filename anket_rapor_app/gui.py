from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from report_builder import generate_report


DEFAULT_CONFIG = "config/config_rizepem_2026_2.yaml"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Anket Rapor Uygulaması")
        self.geometry("760x500")

        self.excel_var = tk.StringVar()
        self.config_var = tk.StringVar(value=DEFAULT_CONFIG)
        self.output_var = tk.StringVar(value="output")

        self._build_ui()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        def row_selector(label: str, var: tk.StringVar, cmd):
            r = ttk.Frame(frm)
            r.pack(fill="x", pady=4)
            ttk.Label(r, text=label, width=16).pack(side="left")
            ttk.Entry(r, textvariable=var).pack(side="left", fill="x", expand=True, padx=8)
            ttk.Button(r, text="Seç", command=cmd).pack(side="left")

        row_selector("Excel", self.excel_var, self.pick_excel)
        row_selector("Config", self.config_var, self.pick_config)
        row_selector("Çıktı Klasörü", self.output_var, self.pick_output)

        ttk.Button(frm, text="Rapor Üret", command=self.run_report).pack(anchor="w", pady=8)

        self.log = tk.Text(frm, height=18)
        self.log.pack(fill="both", expand=True)

    def append_log(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def pick_excel(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if path:
            self.excel_var.set(path)

    def pick_config(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("YAML", "*.yaml *.yml")])
        if path:
            self.config_var.set(path)

    def pick_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_var.set(path)

    def run_report(self) -> None:
        excel = self.excel_var.get().strip()
        cfg = self.config_var.get().strip() or DEFAULT_CONFIG
        out = self.output_var.get().strip() or "output"

        if not excel:
            messagebox.showerror("Hata", "Lütfen Excel dosyası seçin.")
            return

        def _task():
            try:
                self.append_log("Rapor üretimi başlatıldı...")
                pdf = generate_report(excel, cfg, out, log=self.append_log)
                self.append_log(f"Tamamlandı: {pdf}")
                messagebox.showinfo("Başarılı", f"Rapor üretildi:\n{pdf}")
            except Exception as exc:
                self.append_log(f"Hata: {exc}")
                messagebox.showerror("Hata", str(exc))

        threading.Thread(target=_task, daemon=True).start()


if __name__ == "__main__":
    Path("output").mkdir(exist_ok=True)
    app = App()
    app.mainloop()
