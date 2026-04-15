"""
GUI del pipeline autonomo — tkinter (ligero, compatible con RPi 5).
Un boton -> pipeline completo -> resultados.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from .config import load_config
from .classifier import scan_folder
from .controller import PipelineController


class PipelineGUI:
    """Ventana principal del pipeline autonomo CubeSat EdgeAI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CubeSat EdgeAI — Pipeline Autonomo")
        self.root.geometry("860x720")
        self.root.minsize(650, 560)
        self.root.configure(bg="#1e1e2e")

        self.input_folder = tk.StringVar(value="./Imagenes")
        self.running = False
        self.cfg = load_config()

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
        style.configure("Preview.TLabel", foreground="#bac2de", background="#313244",
                        font=("Consolas", 9))
        style.configure("Cat.TLabel", foreground="#f9e2af", background="#313244",
                        font=("Segoe UI", 10, "bold"))

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # -- Header --
        ttk.Label(main, text="CubeSat EdgeAI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="Pipeline autonomo de microscopia -- PC / Raspberry Pi 5",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        # -- Input folder --
        folder_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(folder_frame, text="Carpeta de entrada:").pack(anchor="w")
        row = ttk.Frame(folder_frame, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(4, 0))

        self.folder_entry = ttk.Entry(row, textvariable=self.input_folder,
                                       font=("Consolas", 10))
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="Buscar...", command=self._browse_folder).pack(side=tk.RIGHT)

        # Hint de estructura
        hint = ttk.Frame(folder_frame, style="Card.TFrame")
        hint.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(hint, text="Estructura esperada:  carpeta/ -> ruler/ , onion/ , fiber/",
                  style="Preview.TLabel").pack(anchor="w")
        ttk.Label(hint, text="(tambien clasifica por nombre si no hay subcarpetas)",
                  style="Preview.TLabel").pack(anchor="w")

        # -- Preview panel: imagenes detectadas --
        preview_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        preview_frame.pack(fill=tk.X, pady=(0, 8))

        prev_header = ttk.Frame(preview_frame, style="Card.TFrame")
        prev_header.pack(fill=tk.X)
        ttk.Label(prev_header, text="Imagenes detectadas:").pack(side=tk.LEFT)
        ttk.Button(prev_header, text="Escanear", command=self._scan_preview).pack(side=tk.RIGHT)

        self.preview_text = tk.Text(
            preview_frame, height=6, font=("Consolas", 9),
            bg="#181825", fg="#cdd6f4", relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.X, pady=(4, 0))
        # Tags de color para cada categoria
        self.preview_text.tag_configure("ruler", foreground="#f38ba8")
        self.preview_text.tag_configure("onion", foreground="#a6e3a1")
        self.preview_text.tag_configure("fiber", foreground="#89b4fa")
        self.preview_text.tag_configure("unknown", foreground="#6c7086")
        self.preview_text.tag_configure("header", foreground="#f9e2af",
                                         font=("Consolas", 9, "bold"))

        # -- Calibracion manual --
        cal_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        cal_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(cal_frame, text="Calibracion:").pack(side=tk.LEFT)
        self.cal_status = tk.StringVar(value="Sin calibrar")
        ttk.Label(cal_frame, textvariable=self.cal_status,
                  font=("Consolas", 9), foreground="#f9e2af",
                  background="#313244").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Button(cal_frame, text="Calibrar con regla",
                   command=self._manual_calibrate).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(cal_frame, text="Ingresar um/px",
                   command=self._enter_calibration).pack(side=tk.RIGHT)

        self.manual_um_per_pixel = None

        # -- Config: modo y metodo --
        info_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 8))

        self.mode_var = tk.StringVar(value="classic")
        ttk.Label(info_frame, text="Modo:").pack(side=tk.LEFT)
        for mode, label in [("classic", "OpenCV"), ("full", "IA (Cellpose)"),
                             ("minimal", "Minimo")]:
            ttk.Radiobutton(info_frame, text=label, variable=self.mode_var,
                            value=mode).pack(side=tk.LEFT, padx=8)

        self.method_var = tk.StringVar(value="opencv")
        ttk.Label(info_frame, text="   Segmentacion:").pack(side=tk.LEFT)
        for m, label in [("opencv", "OpenCV"), ("cellpose", "Cellpose"),
                          ("onnx", "ONNX")]:
            ttk.Radiobutton(info_frame, text=label, variable=self.method_var,
                            value=m).pack(side=tk.LEFT, padx=8)

        # -- Buttons row --
        btn_row = ttk.Frame(main, style="TFrame")
        btn_row.pack(fill=tk.X, pady=(4, 8))

        self.start_btn = ttk.Button(
            btn_row, text="START ANALYSIS", style="Start.TButton",
            command=self._start_pipeline
        )
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.view_btn = ttk.Button(
            btn_row, text="VER RESULTADOS", style="Start.TButton",
            command=self._open_viewer
        )
        self.view_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        # -- Progress --
        self.progress = ttk.Progressbar(main, mode="indeterminate", length=400)
        self.progress.pack(fill=tk.X, pady=(0, 8))

        # -- Log --
        log_frame = ttk.Frame(main, style="Card.TFrame", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(log_frame, text="Log del pipeline:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, font=("Consolas", 9),
            bg="#181825", fg="#a6e3a1", insertbackground="#a6e3a1",
            relief=tk.FLAT, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # -- Status bar --
        self.status_var = tk.StringVar(value="Listo — selecciona carpeta y pulsa Escanear")
        ttk.Label(main, textvariable=self.status_var, style="Sub.TLabel").pack(
            anchor="w", pady=(6, 0)
        )

        # Escanear al inicio
        self.root.after(300, self._scan_preview)

    def _manual_calibrate(self):
        """Siempre deja al usuario escoger la imagen para calibrar."""
        # Directorio inicial: carpeta ruler/ si existe, sino la carpeta de entrada
        folder = self.input_folder.get()
        initial_dir = folder
        if os.path.isdir(folder):
            ruler_dir = os.path.join(folder, "ruler")
            if os.path.isdir(ruler_dir):
                initial_dir = ruler_dir

        ruler_path = filedialog.askopenfilename(
            title="Seleccionar imagen para calibrar (regla, regleta, referencia)",
            initialdir=initial_dir,
            filetypes=[
                ("Imagenes", "*.png *.jpg *.jpeg *.tiff *.tif *.bmp"),
                ("Todos", "*.*"),
            ]
        )

        if not ruler_path:
            return

        self.status_var.set("Calibrando... marca pares de puntos, ENTER para confirmar")

        def _run():
            from .manual_calibration import ManualCalibrator
            cal = ManualCalibrator()
            result = cal.calibrate(ruler_path)

            if not result["success"]:
                self.root.after(0, lambda: self.cal_status.set(
                    "Calibracion cancelada"))
                self.root.after(0, lambda: self.status_var.set("Listo"))
                return

            avg_px = result["avg_distance_px"]
            n_pairs = result["num_pairs"]

            # Pedir distancia real en GUI
            self.root.after(0, lambda: self._ask_real_distance(avg_px, n_pairs))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _ask_real_distance(self, avg_px, n_pairs):
        """Dialogo para ingresar la distancia real."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Distancia real")
        dialog.geometry("420x220")
        dialog.configure(bg="#313244")
        dialog.transient(self.root)
        dialog.grab_set()

        info = f"Promedio medido: {avg_px:.2f} pixels ({n_pairs} medicion{'es' if n_pairs > 1 else ''})"
        ttk.Label(dialog, text=info,
                  font=("Segoe UI", 11, "bold")).pack(pady=(16, 8))
        ttk.Label(dialog, text="Ingresa la distancia real entre los puntos:").pack()

        entry_frame = ttk.Frame(dialog)
        entry_frame.pack(pady=8)

        val_var = tk.StringVar(value="1.0")
        val_entry = ttk.Entry(entry_frame, textvariable=val_var, width=10,
                               font=("Consolas", 12))
        val_entry.pack(side=tk.LEFT, padx=4)
        val_entry.focus_set()
        val_entry.select_range(0, tk.END)

        unit_var = tk.StringVar(value="mm")
        for u in ["mm", "um"]:
            ttk.Radiobutton(entry_frame, text=u, variable=unit_var,
                            value=u).pack(side=tk.LEFT, padx=6)

        def _accept():
            try:
                value = float(val_var.get().replace(",", "."))
                unit = unit_var.get()
                value_um = value * 1000 if unit == "mm" else value
                um_px = value_um / avg_px

                self.manual_um_per_pixel = um_px
                self.cal_status.set(f"{um_px:.4f} um/px  ({value} {unit} = {avg_px:.1f} px, {n_pairs} med.)")
                self.status_var.set(f"Calibrado: {um_px:.4f} um/pixel")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Ingresa un numero valido",
                                      parent=dialog)

        ttk.Button(dialog, text="Aceptar", command=_accept).pack(pady=8)
        dialog.bind("<Return>", lambda e: _accept())

    def _enter_calibration(self):
        """Dialogo para ingresar um/pixel directamente."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ingresar calibracion")
        dialog.geometry("350x160")
        dialog.configure(bg="#313244")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Ingresa el valor de escala:",
                  font=("Segoe UI", 11)).pack(pady=(16, 8))

        entry_frame = ttk.Frame(dialog)
        entry_frame.pack(pady=4)

        val_var = tk.StringVar(value="0.5")
        val_entry = ttk.Entry(entry_frame, textvariable=val_var, width=12,
                               font=("Consolas", 12))
        val_entry.pack(side=tk.LEFT, padx=4)
        val_entry.focus_set()
        val_entry.select_range(0, tk.END)
        ttk.Label(entry_frame, text="um/pixel").pack(side=tk.LEFT)

        def _accept():
            try:
                um_px = float(val_var.get().replace(",", "."))
                self.manual_um_per_pixel = um_px
                self.cal_status.set(f"{um_px:.4f} um/px  (ingresado manual)")
                self.status_var.set(f"Calibrado: {um_px:.4f} um/pixel")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Ingresa un numero valido",
                                      parent=dialog)

        ttk.Button(dialog, text="Aceptar", command=_accept).pack(pady=12)
        dialog.bind("<Return>", lambda e: _accept())

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de imagenes")
        if folder:
            self.input_folder.set(folder)
            self._scan_preview()

    def _scan_preview(self):
        """Escanea la carpeta y muestra preview de imagenes clasificadas."""
        folder = self.input_folder.get()
        if not os.path.isdir(folder):
            self._set_preview("Carpeta no encontrada: " + folder)
            return

        classified = scan_folder(folder, self.cfg)

        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)

        total = sum(len(v) for v in classified.values())

        categories = [
            ("ruler", "CALIBRACION (ruler/)", classified["ruler"]),
            ("onion", "CEBOLLA (onion/)", classified["onion"]),
            ("fiber", "FIBRA (fiber/)", classified["fiber"]),
            ("unknown", "SIN CLASIFICAR", classified["unknown"]),
        ]

        for tag, title, files in categories:
            if files:
                self.preview_text.insert(tk.END, f"  {title}: {len(files)}\n", "header")
                for f in files:
                    name = os.path.basename(f)
                    parent = os.path.basename(os.path.dirname(f))
                    display = f"    {parent}/{name}\n" if parent != os.path.basename(folder) else f"    {name}\n"
                    self.preview_text.insert(tk.END, display, tag)

        if total == 0:
            self.preview_text.insert(tk.END, "  No se encontraron imagenes.\n", "unknown")
            self.preview_text.insert(tk.END, "  Crea subcarpetas: ruler/ onion/ fiber/\n", "unknown")

        self.preview_text.configure(state=tk.DISABLED)
        self.status_var.set(f"Escaneado: {total} imagenes encontradas")

    def _set_preview(self, text: str):
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", text)
        self.preview_text.configure(state=tk.DISABLED)

    def _open_viewer(self):
        """Abre el visor interactivo de OpenCV en un hilo separado."""
        folder = self.input_folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Carpeta no encontrada:\n{folder}")
            return

        classified = scan_folder(folder, self.cfg)
        total = sum(len(v) for v in classified.values())
        if total == 0:
            messagebox.showwarning("Sin imagenes",
                                    "No se encontraron imagenes en la carpeta.")
            return

        self.status_var.set("Abriendo visor... (ESC para cerrar)")

        def _run_viewer():
            from .viewer import run_viewer
            run_viewer(input_folder=folder)
            self.root.after(0, lambda: self.status_var.set("Visor cerrado"))

        thread = threading.Thread(target=_run_viewer, daemon=True)
        thread.start()

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

        # Verificar que hay imagenes
        classified = scan_folder(folder, self.cfg)
        total = sum(len(v) for v in classified.values())
        if total == 0:
            messagebox.showwarning(
                "Sin imagenes",
                "No se encontraron imagenes en la carpeta.\n\n"
                "Crea subcarpetas: ruler/ onion/ fiber/\n"
                "y coloca las imagenes dentro."
            )
            return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.progress.start(15)
        self.log_text.delete("1.0", tk.END)
        self.status_var.set("Ejecutando pipeline...")

        thread = threading.Thread(target=self._run_pipeline, args=(folder,),
                                  daemon=True)
        thread.start()

    def _run_pipeline(self, folder: str):
        try:
            controller = PipelineController(log_callback=self._log)

            # Aplicar modo y metodo seleccionados
            controller.cfg["mode"] = self.mode_var.get()
            controller.cfg["onion"]["method"] = self.method_var.get()

            # Aplicar calibracion manual si existe
            if self.manual_um_per_pixel is not None:
                controller.um_per_pixel = self.manual_um_per_pixel
                controller.cal_info = {
                    "success": True,
                    "method": "manual",
                    "um_per_pixel": self.manual_um_per_pixel,
                    "mm_per_pixel": self.manual_um_per_pixel / 1000,
                    "message": f"Calibracion manual: {self.manual_um_per_pixel:.4f} um/px",
                }

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
            self.status_var.set(f"Completado -- {out_dir}")
            if messagebox.askyesno("Pipeline completado",
                                    "Abrir carpeta de resultados?"):
                if os.name == "nt":
                    os.startfile(out_dir)
                else:
                    os.system(f"xdg-open '{out_dir}'")
        else:
            self.status_var.set("Error durante la ejecucion")

    def run(self):
        self.root.mainloop()
