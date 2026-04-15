"""
GUI del pipeline autónomo — tkinter (ligero, compatible con RPi 5).
Un botón → pipeline completo → resultados.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from .controller import PipelineController


class PipelineGUI:
    """Ventana principal del pipeline autónomo CubeSat EdgeAI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CubeSat EdgeAI — Pipeline Autonomo")
        self.root.geometry("820x660")
        self.root.minsize(600, 500)
        self.root.configure(bg="#1e1e2e")

        self.input_folder = tk.StringVar(value="./Imagenes")
        self.running = False

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                        foreground="#cdd6f4", background="#1e1e2e")
        style.configure("Sub.TLabel", font=("Segoe UI", 10),
                        foreground="#a6adc8", background="#1e1e2e")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("Card.TFrame", background="#313244")
        style.configure("TLabel", foreground="#cdd6f4", background="#313244",
                        font=("Segoe UI", 10))
        style.configure("Start.TButton", font=("Segoe UI", 13, "bold"),
                        padding=12)
        style.configure("TButton", font=("Segoe UI", 10), padding=6)

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # ── Header ──
        ttk.Label(main, text="CubeSat EdgeAI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="Pipeline autonomo de microscopia — PC / Raspberry Pi 5",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        # ── Input folder ──
        folder_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(folder_frame, text="Carpeta de entrada:").pack(anchor="w")
        row = ttk.Frame(folder_frame, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(4, 0))

        self.folder_entry = ttk.Entry(row, textvariable=self.input_folder, font=("Consolas", 10))
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="Buscar...", command=self._browse_folder).pack(side=tk.RIGHT)

        # ── Config info ──
        info_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 8))

        self.mode_var = tk.StringVar(value="classic")
        ttk.Label(info_frame, text="Modo:").pack(side=tk.LEFT)
        for mode, label in [("classic", "OpenCV"), ("full", "IA (Cellpose)"), ("minimal", "Minimo")]:
            ttk.Radiobutton(info_frame, text=label, variable=self.mode_var, value=mode).pack(side=tk.LEFT, padx=8)

        self.method_var = tk.StringVar(value="opencv")
        ttk.Label(info_frame, text="   Segmentacion:").pack(side=tk.LEFT)
        for m, label in [("opencv", "OpenCV"), ("cellpose", "Cellpose"), ("onnx", "ONNX")]:
            ttk.Radiobutton(info_frame, text=label, variable=self.method_var, value=m).pack(side=tk.LEFT, padx=8)

        # ── START button ──
        self.start_btn = ttk.Button(
            main, text="START ANALYSIS", style="Start.TButton",
            command=self._start_pipeline
        )
        self.start_btn.pack(fill=tk.X, pady=(4, 8))

        # ── Progress ──
        self.progress = ttk.Progressbar(main, mode="indeterminate", length=400)
        self.progress.pack(fill=tk.X, pady=(0, 8))

        # ── Log ──
        log_frame = ttk.Frame(main, style="Card.TFrame", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(log_frame, text="Log del pipeline:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=16, font=("Consolas", 9),
            bg="#181825", fg="#a6e3a1", insertbackground="#a6e3a1",
            relief=tk.FLAT, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # ── Status bar ──
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(main, textvariable=self.status_var, style="Sub.TLabel").pack(
            anchor="w", pady=(6, 0)
        )

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de imagenes")
        if folder:
            self.input_folder.set(folder)

    def _log(self, msg: str):
        """Thread-safe log to text widget."""
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def _start_pipeline(self):
        if self.running:
            return

        folder = self.input_folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Carpeta no encontrada:\n{folder}")
            return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.progress.start(15)
        self.log_text.delete("1.0", tk.END)
        self.status_var.set("Ejecutando pipeline...")

        thread = threading.Thread(target=self._run_pipeline, args=(folder,), daemon=True)
        thread.start()

    def _run_pipeline(self, folder: str):
        try:
            controller = PipelineController(log_callback=self._log)

            # Aplicar modo y método seleccionados
            controller.cfg["mode"] = self.mode_var.get()
            controller.cfg["onion"]["method"] = self.method_var.get()

            result = controller.run(input_folder=folder)

            summary = result.get("summary", {})
            out_dir = result.get("output_dir", "")

            self._log("")
            self._log("=" * 50)
            if "cells" in summary:
                c = summary["cells"]
                self._log(f"CELULAS: {c['count']} detectadas")
                self._log(f"  Area media: {c['area_um2_mean']:.2f} um2")
                self._log(f"  Perimetro medio: {c['perimeter_um_mean']:.2f} um")
            if "fibers" in summary:
                fb = summary["fibers"]
                self._log(f"FIBRAS: {fb['count']} detectadas")
                self._log(f"  Longitud media: {fb['length_um_mean']:.2f} um")

            pipe = summary.get("pipeline", {})
            self._log(f"\nTiempo total: {pipe.get('elapsed_seconds', 0):.1f}s")
            self._log(f"Resultados: {out_dir}")
            self._log("=" * 50)

            self.root.after(0, self._finished, out_dir)

        except Exception as e:
            self._log(f"\nERROR FATAL: {e}")
            self.root.after(0, self._finished, None)

    def _finished(self, out_dir):
        self.running = False
        self.progress.stop()
        self.start_btn.configure(state="normal")

        if out_dir:
            self.status_var.set(f"Completado — {out_dir}")
            if messagebox.askyesno("Pipeline completado", "Abrir carpeta de resultados?"):
                os.startfile(out_dir) if os.name == "nt" else os.system(f"xdg-open '{out_dir}'")
        else:
            self.status_var.set("Error durante la ejecucion")

    def run(self):
        self.root.mainloop()
