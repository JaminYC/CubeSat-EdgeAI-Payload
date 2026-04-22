"""
GUI del pipeline autonomo — tkinter (ligero, compatible con RPi 5).
Organizado en pestanas: Pipeline | FPM | Modelos IA
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from .config import load_config
from .classifier import scan_folder
from .controller import PipelineController
from .fpm_reconstruction import reconstruct_fpm, load_scan_metadata
from .ai_enhance import get_available_models, run_ai_model, run_all_models


class PipelineGUI:
    """Ventana principal del pipeline autonomo CubeSat EdgeAI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CubeSat EdgeAI — Pipeline Autonomo")
        self.root.geometry("900x750")
        self.root.minsize(700, 600)
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
        # Notebook tab style
        style.configure("TNotebook", background="#1e1e2e")
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"),
                        padding=[14, 6])

        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # -- Header --
        ttk.Label(main, text="CubeSat EdgeAI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="Pipeline autonomo de microscopia -- PC / Raspberry Pi 5",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        # ── Notebook (tabs) ─────────────────────────────────────
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # Tab 1: Pipeline
        tab_pipeline = ttk.Frame(self.notebook, style="TFrame", padding=8)
        self.notebook.add(tab_pipeline, text="  Pipeline  ")
        self._build_tab_pipeline(tab_pipeline)

        # Tab 2: FPM
        tab_fpm = ttk.Frame(self.notebook, style="TFrame", padding=8)
        self.notebook.add(tab_fpm, text="  FPM  ")
        self._build_tab_fpm(tab_fpm)

        # Tab 3: Modelos IA
        tab_ai = ttk.Frame(self.notebook, style="TFrame", padding=8)
        self.notebook.add(tab_ai, text="  Modelos IA  ")
        self._build_tab_ai(tab_ai)

        # ── Log (compartido, abajo) ─────────────────────────────
        log_frame = ttk.Frame(main, style="Card.TFrame", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        ttk.Label(log_frame, text="Log:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, font=("Consolas", 9),
            bg="#181825", fg="#a6e3a1", insertbackground="#a6e3a1",
            relief=tk.FLAT, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # ── Status bar ──────────────────────────────────────────
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(main, textvariable=self.status_var, style="Sub.TLabel").pack(
            anchor="w", pady=(4, 0)
        )

        # Escanear al inicio
        self.root.after(300, self._scan_preview)

    # ══════════════════════════════════════════════════════════════
    #  TAB 1: Pipeline
    # ══════════════════════════════════════════════════════════════

    def _build_tab_pipeline(self, parent):
        # -- Input folder --
        folder_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(folder_frame, text="Carpeta de entrada:").pack(anchor="w")
        row = ttk.Frame(folder_frame, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(4, 0))

        self.folder_entry = ttk.Entry(row, textvariable=self.input_folder,
                                       font=("Consolas", 10))
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="Buscar...", command=self._browse_folder).pack(side=tk.RIGHT)

        hint = ttk.Frame(folder_frame, style="Card.TFrame")
        hint.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(hint, text="Estructura:  carpeta/ -> ruler/ , onion/ , fiber/  (o clasifica por nombre)",
                  style="Preview.TLabel").pack(anchor="w")

        # -- Preview panel --
        preview_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        preview_frame.pack(fill=tk.X, pady=(0, 8))

        prev_header = ttk.Frame(preview_frame, style="Card.TFrame")
        prev_header.pack(fill=tk.X)
        ttk.Label(prev_header, text="Imagenes detectadas:").pack(side=tk.LEFT)
        ttk.Button(prev_header, text="Escanear", command=self._scan_preview).pack(side=tk.RIGHT)

        self.preview_text = tk.Text(
            preview_frame, height=5, font=("Consolas", 9),
            bg="#181825", fg="#cdd6f4", relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.X, pady=(4, 0))
        self.preview_text.tag_configure("ruler", foreground="#f38ba8")
        self.preview_text.tag_configure("onion", foreground="#a6e3a1")
        self.preview_text.tag_configure("fiber", foreground="#89b4fa")
        self.preview_text.tag_configure("unknown", foreground="#6c7086")
        self.preview_text.tag_configure("header", foreground="#f9e2af",
                                         font=("Consolas", 9, "bold"))

        # -- Calibracion --
        cal_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
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

        # -- Config: mejora + segmentacion --
        info_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 8))

        # Enhancement (denoising) - obligatorio para condiciones espaciales
        self.enhance_var = tk.StringVar(value="n2v")
        ttk.Label(info_frame, text="Mejora (obligatoria):").pack(side=tk.LEFT)
        for val, label in [("n2v", "N2V"), ("care", "CARE")]:
            ttk.Radiobutton(info_frame, text=label, variable=self.enhance_var,
                            value=val).pack(side=tk.LEFT, padx=4)

        # Segmentation method
        self.method_var = tk.StringVar(value="opencv")
        ttk.Label(info_frame, text="   Segmentacion:").pack(side=tk.LEFT)
        for m, label in [("opencv", "OpenCV"), ("cellpose", "Cellpose"),
                          ("stardist", "StarDist")]:
            ttk.Radiobutton(info_frame, text=label, variable=self.method_var,
                            value=m).pack(side=tk.LEFT, padx=4)

        # -- Buttons --
        btn_row = ttk.Frame(parent, style="TFrame")
        btn_row.pack(fill=tk.X, pady=(4, 4))

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
        self.progress = ttk.Progressbar(parent, mode="indeterminate", length=400)
        self.progress.pack(fill=tk.X, pady=(4, 0))

    # ══════════════════════════════════════════════════════════════
    #  TAB 2: FPM
    # ══════════════════════════════════════════════════════════════

    def _build_tab_fpm(self, parent):
        fpm_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        fpm_frame.pack(fill=tk.X, pady=(0, 8))

        fpm_top = ttk.Frame(fpm_frame, style="Card.TFrame")
        fpm_top.pack(fill=tk.X)
        ttk.Label(fpm_top, text="Reconstruccion FPM:",
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.fpm_status = tk.StringVar(value="Sin reconstruir")
        ttk.Label(fpm_top, textvariable=self.fpm_status,
                  font=("Consolas", 9), foreground="#89b4fa",
                  background="#313244").pack(side=tk.LEFT, padx=(8, 0))

        # Folder
        fpm_row1 = ttk.Frame(fpm_frame, style="Card.TFrame")
        fpm_row1.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(fpm_row1, text="Carpeta scan:").pack(side=tk.LEFT)
        self.fpm_folder = tk.StringVar(value="")
        self.fpm_folder_entry = ttk.Entry(fpm_row1, textvariable=self.fpm_folder,
                                           font=("Consolas", 9), width=40)
        self.fpm_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Button(fpm_row1, text="Buscar...",
                   command=self._browse_fpm_folder).pack(side=tk.LEFT)

        # Method + params
        fpm_row2 = ttk.Frame(fpm_frame, style="Card.TFrame")
        fpm_row2.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(fpm_row2, text="Metodo:").pack(side=tk.LEFT)
        self.fpm_method = tk.StringVar(value="multiangle")
        ttk.Radiobutton(fpm_row2, text="Multi-angulo", variable=self.fpm_method,
                        value="multiangle").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(fpm_row2, text="Multi-frame", variable=self.fpm_method,
                        value="multiframe").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(fpm_row2, text="Fourier", variable=self.fpm_method,
                        value="fourier").pack(side=tk.LEFT, padx=4)

        ttk.Label(fpm_row2, text="  Upscale:").pack(side=tk.LEFT, padx=(8, 0))
        self.fpm_upscale = tk.IntVar(value=2)
        for val in [2, 3, 4]:
            ttk.Radiobutton(fpm_row2, text=f"x{val}", variable=self.fpm_upscale,
                            value=val).pack(side=tk.LEFT, padx=4)

        fpm_row2b = ttk.Frame(fpm_frame, style="Card.TFrame")
        fpm_row2b.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(fpm_row2b, text="Iters:").pack(side=tk.LEFT)
        self.fpm_iters = tk.IntVar(value=15)
        ttk.Spinbox(fpm_row2b, from_=5, to=50, increment=5,
                     textvariable=self.fpm_iters, width=4).pack(side=tk.LEFT, padx=4)

        ttk.Label(fpm_row2b, text="  NA:").pack(side=tk.LEFT, padx=(8, 0))
        self.fpm_na = tk.DoubleVar(value=0.10)
        ttk.Spinbox(fpm_row2b, from_=0.02, to=0.50, increment=0.02,
                     textvariable=self.fpm_na, width=5, format="%.2f").pack(side=tk.LEFT, padx=4)

        ttk.Label(fpm_row2b, text="  ROI:").pack(side=tk.LEFT, padx=(8, 0))
        self.fpm_roi = tk.IntVar(value=0)
        ttk.Spinbox(fpm_row2b, from_=0, to=4096, increment=128,
                     textvariable=self.fpm_roi, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Label(fpm_row2b, text="px (0=completo)").pack(side=tk.LEFT)

        self.fpm_align = tk.BooleanVar(value=False)
        ttk.Checkbutton(fpm_row2b, text="  Alinear (ECC)",
                        variable=self.fpm_align).pack(side=tk.LEFT, padx=(12, 0))

        # Progress + button
        fpm_row3 = ttk.Frame(fpm_frame, style="Card.TFrame")
        fpm_row3.pack(fill=tk.X, pady=(8, 0))

        self.fpm_progress = ttk.Progressbar(fpm_row3, mode="determinate", length=200)
        self.fpm_progress.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)
        self.fpm_progress_label = tk.StringVar(value="")
        ttk.Label(fpm_row3, textvariable=self.fpm_progress_label,
                  font=("Consolas", 8), foreground="#89b4fa",
                  background="#313244").pack(side=tk.LEFT, padx=(4, 4))

        self.fpm_btn = ttk.Button(fpm_row3, text="RECONSTRUIR",
                                   command=self._start_fpm, style="Start.TButton")
        self.fpm_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # Hint
        fpm_hint = ttk.Frame(fpm_frame, style="Card.TFrame")
        fpm_hint.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(fpm_hint,
                  text="Multi-angulo: lensless+OLED (recomendado)  |  Multi-frame: shifts reales  |  Fourier: con lente",
                  style="Preview.TLabel").pack(anchor="w")

    # ══════════════════════════════════════════════════════════════
    #  TAB 3: Modelos IA
    # ══════════════════════════════════════════════════════════════

    def _build_tab_ai(self, parent):
        available = get_available_models()

        # -- Image source --
        src_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        src_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(src_frame, text="Imagen de entrada:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        src_row = ttk.Frame(src_frame, style="Card.TFrame")
        src_row.pack(fill=tk.X, pady=(4, 0))
        self.ai_image_path = tk.StringVar(value="")
        ttk.Entry(src_row, textvariable=self.ai_image_path,
                  font=("Consolas", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(src_row, text="Buscar...",
                   command=self._browse_ai_image).pack(side=tk.RIGHT)

        # -- Model selection --
        model_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        model_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(model_frame, text="Seleccionar modelo:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))

        self.ai_model_var = tk.StringVar(value="cellpose")

        models_grid = ttk.Frame(model_frame, style="Card.TFrame")
        models_grid.pack(fill=tk.X)

        # Two columns of radio buttons
        col_left = ttk.Frame(models_grid, style="Card.TFrame")
        col_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        col_right = ttk.Frame(models_grid, style="Card.TFrame")
        col_right.pack(side=tk.LEFT, fill=tk.X, expand=True)

        seg_models = [
            ("cellpose", "Cellpose — segmentacion celular"),
            ("stardist", "StarDist — deteccion celular (rapido)"),
        ]
        denoise_models = [
            ("n2v", "N2V — denoising self-supervised"),
            ("care", "CARE — denoising/restauracion"),
        ]

        ttk.Label(col_left, text="Segmentacion:", foreground="#a6e3a1",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w")
        for mid, label in seg_models:
            state = "normal" if available.get(mid) else "disabled"
            tag = label if available.get(mid) else f"{label} [N/A]"
            ttk.Radiobutton(col_left, text=tag, variable=self.ai_model_var,
                            value=mid, state=state).pack(anchor="w", padx=(8, 0), pady=1)

        ttk.Label(col_right, text="Denoising:", foreground="#89b4fa",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w")
        for mid, label in denoise_models:
            state = "normal" if available.get(mid) else "disabled"
            tag = label if available.get(mid) else f"{label} [N/A]"
            ttk.Radiobutton(col_right, text=tag, variable=self.ai_model_var,
                            value=mid, state=state).pack(anchor="w", padx=(8, 0), pady=1)

        # -- Options --
        opts_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        opts_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(opts_frame, text="Opciones del modelo:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))

        opts_row = ttk.Frame(opts_frame, style="Card.TFrame")
        opts_row.pack(fill=tk.X)

        ttk.Label(opts_row, text="Cellpose:").pack(side=tk.LEFT)
        self.ai_cp_model = tk.StringVar(value="cyto3")
        ttk.Combobox(opts_row, textvariable=self.ai_cp_model, width=8,
                     values=["cyto3", "cyto2", "cyto", "nuclei"],
                     state="readonly").pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(opts_row, text="StarDist:").pack(side=tk.LEFT)
        self.ai_sd_model = tk.StringVar(value="2D_versatile_fluo")
        ttk.Combobox(opts_row, textvariable=self.ai_sd_model, width=16,
                     values=["2D_versatile_fluo", "2D_versatile_he",
                              "2D_paper_dsb2018"],
                     state="readonly").pack(side=tk.LEFT, padx=(4, 16))

        self.ai_n2v_train = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_row, text="N2V: entrenar en imagen",
                        variable=self.ai_n2v_train).pack(side=tk.LEFT)

        # -- Status + buttons --
        btn_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.ai_status = tk.StringVar(value="Listo")
        ttk.Label(btn_frame, textvariable=self.ai_status,
                  font=("Consolas", 9), foreground="#a6e3a1",
                  background="#313244").pack(anchor="w", pady=(0, 4))

        self.ai_progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=300)
        self.ai_progress.pack(fill=tk.X, pady=(0, 6))

        ai_btns = ttk.Frame(btn_frame, style="Card.TFrame")
        ai_btns.pack(fill=tk.X)

        self.ai_run_btn = ttk.Button(ai_btns, text="EJECUTAR MODELO",
                                      command=self._start_ai_model,
                                      style="Start.TButton")
        self.ai_run_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.ai_run_all_btn = ttk.Button(ai_btns, text="EJECUTAR TODOS",
                                          command=self._start_ai_all,
                                          style="Start.TButton")
        self.ai_run_all_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        # Hint
        ttk.Label(btn_frame,
                  text="Resultados se guardan en ai_results/ junto a la imagen  |  Target: RPi 5 (ONNX)",
                  style="Preview.TLabel").pack(anchor="w", pady=(6, 0))

    # ══════════════════════════════════════════════════════════════
    #  Callbacks — Pipeline tab
    # ══════════════════════════════════════════════════════════════

    def _manual_calibrate(self):
        folder = self.input_folder.get()
        initial_dir = folder
        if os.path.isdir(folder):
            ruler_dir = os.path.join(folder, "ruler")
            if os.path.isdir(ruler_dir):
                initial_dir = ruler_dir

        ruler_path = filedialog.askopenfilename(
            title="Seleccionar imagen para calibrar",
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
                self.root.after(0, lambda: self.cal_status.set("Calibracion cancelada"))
                self.root.after(0, lambda: self.status_var.set("Listo"))
                return
            avg_px = result["avg_distance_px"]
            n_pairs = result["num_pairs"]
            self.root.after(0, lambda: self._ask_real_distance(avg_px, n_pairs))

        threading.Thread(target=_run, daemon=True).start()

    def _ask_real_distance(self, avg_px, n_pairs):
        dialog = tk.Toplevel(self.root)
        dialog.title("Distancia real")
        dialog.geometry("420x220")
        dialog.configure(bg="#313244")
        dialog.transient(self.root)
        dialog.grab_set()

        info = f"Promedio medido: {avg_px:.2f} pixels ({n_pairs} medicion{'es' if n_pairs > 1 else ''})"
        ttk.Label(dialog, text=info, font=("Segoe UI", 11, "bold")).pack(pady=(16, 8))
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
                messagebox.showerror("Error", "Ingresa un numero valido", parent=dialog)

        ttk.Button(dialog, text="Aceptar", command=_accept).pack(pady=8)
        dialog.bind("<Return>", lambda e: _accept())

    def _enter_calibration(self):
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
                messagebox.showerror("Error", "Ingresa un numero valido", parent=dialog)

        ttk.Button(dialog, text="Aceptar", command=_accept).pack(pady=12)
        dialog.bind("<Return>", lambda e: _accept())

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de imagenes")
        if folder:
            self.input_folder.set(folder)
            self._scan_preview()

    def _scan_preview(self):
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
        folder = self.input_folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Carpeta no encontrada:\n{folder}")
            return
        classified = scan_folder(folder, self.cfg)
        total = sum(len(v) for v in classified.values())
        if total == 0:
            messagebox.showwarning("Sin imagenes", "No se encontraron imagenes en la carpeta.")
            return
        self.status_var.set("Abriendo visor... (ESC para cerrar)")

        def _run_viewer():
            from .viewer import run_viewer
            run_viewer(input_folder=folder)
            self.root.after(0, lambda: self.status_var.set("Visor cerrado"))

        threading.Thread(target=_run_viewer, daemon=True).start()

    def _start_pipeline(self):
        if self.running:
            return
        folder = self.input_folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Carpeta no encontrada:\n{folder}")
            return
        classified = scan_folder(folder, self.cfg)
        total = sum(len(v) for v in classified.values())
        if total == 0:
            messagebox.showwarning("Sin imagenes",
                                    "No se encontraron imagenes.\nCrea subcarpetas: ruler/ onion/ fiber/")
            return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.progress.start(15)
        self.log_text.delete("1.0", tk.END)
        self.status_var.set("Ejecutando pipeline...")

        threading.Thread(target=self._run_pipeline, args=(folder,), daemon=True).start()

    def _run_pipeline(self, folder: str):
        try:
            controller = PipelineController(log_callback=self._log)

            # AI enhancement (denoising before segmentation)
            controller.enhance_method = self.enhance_var.get()  # siempre activo (n2v o care)

            # Segmentation method
            seg_method = self.method_var.get()
            if seg_method in ("cellpose", "stardist"):
                controller.seg_ai_method = seg_method
                controller.cfg["mode"] = "full"
            else:
                controller.seg_ai_method = None
                controller.cfg["mode"] = "classic"
            controller.cfg["onion"]["method"] = seg_method

            if self.manual_um_per_pixel is not None:
                controller.um_per_pixel = self.manual_um_per_pixel
                controller.cal_info = {
                    "success": True, "method": "manual",
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
            if messagebox.askyesno("Pipeline completado", "Abrir carpeta de resultados?"):
                if os.name == "nt":
                    os.startfile(out_dir)
                else:
                    os.system(f"xdg-open '{out_dir}'")
        else:
            self.status_var.set("Error durante la ejecucion")

    # ══════════════════════════════════════════════════════════════
    #  Callbacks — FPM tab
    # ══════════════════════════════════════════════════════════════

    def _browse_fpm_folder(self):
        folder = filedialog.askdirectory(
            title="Seleccionar carpeta de scan FPM (con scan_metadata.json)"
        )
        if folder:
            self.fpm_folder.set(folder)
            meta_path = os.path.join(folder, "scan_metadata.json")
            if os.path.isfile(meta_path):
                try:
                    meta = load_scan_metadata(folder)
                    n_caps = len(meta.get("captures", []))
                    grid = meta.get("grid_size", [0, 0])
                    self.fpm_status.set(f"Scan detectado: {grid[0]}x{grid[1]} = {n_caps} imgs")
                except Exception as e:
                    self.fpm_status.set(f"Error leyendo metadata: {e}")
            else:
                self.fpm_status.set("WARN: no se encontro scan_metadata.json")

    def _start_fpm(self):
        folder = self.fpm_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Selecciona una carpeta de scan FPM valida")
            return
        meta_path = os.path.join(folder, "scan_metadata.json")
        if not os.path.isfile(meta_path):
            messagebox.showerror("Error",
                                  "No se encontro scan_metadata.json en la carpeta.")
            return

        self.fpm_btn.configure(state="disabled")
        self.progress.start(15)
        self.log_text.delete("1.0", tk.END)
        self.status_var.set("Reconstruyendo FPM...")
        self.fpm_status.set("Procesando...")

        threading.Thread(target=self._run_fpm, args=(folder,), daemon=True).start()

    def _run_fpm(self, folder: str):
        try:
            def fpm_log(msg):
                self.root.after(0, self._append_log, msg)

            def progress_cb(cur, total):
                pct = int(cur / total * 100)
                self.root.after(0, lambda c=cur, t=total, p=pct: [
                    self.fpm_status.set(f"Iter {c}/{t}"),
                    self.fpm_progress.configure(value=p),
                    self.fpm_progress_label.set(f"{p}%"),
                ])

            result = reconstruct_fpm(
                scan_folder=folder,
                upscale_factor=self.fpm_upscale.get(),
                max_iters=self.fpm_iters.get(),
                align=self.fpm_align.get(),
                roi_size=self.fpm_roi.get(),
                na_obj=self.fpm_na.get(),
                method=self.fpm_method.get(),
                logger=fpm_log,
                progress_callback=progress_cb,
            )

            um_hr = result["um_per_pixel_hr"]
            us = result["upscale_factor"]
            n = result["n_images"]

            self._log("")
            self._log("=" * 50)
            self._log(f"FPM completado: x{us} con {n} imagenes")
            self._log(f"  Resolucion HR: {um_hr:.4f} um/px")
            self._log("=" * 50)
            self.root.after(0, lambda: self._fpm_finished(result))

        except Exception as e:
            self._log(f"\nERROR FPM: {e}")
            import traceback
            self._log(traceback.format_exc())
            self.root.after(0, lambda: self._fpm_finished(None))

    def _fpm_finished(self, result):
        self.fpm_btn.configure(state="normal")
        self.progress.stop()
        if result:
            um_hr = result["um_per_pixel_hr"]
            us = result["upscale_factor"]
            self.fpm_status.set(f"OK x{us} -- {um_hr:.4f} um/px HR")
            self.status_var.set("Reconstruccion FPM completada")
            files = result.get("files", {})
            amp = files.get("amplitude", "")
            out_dir = os.path.dirname(amp) if amp else ""
            if messagebox.askyesno("FPM Completado",
                                    f"Reconstruccion exitosa (x{us}).\n"
                                    f"Escala HR: {um_hr:.4f} um/px\n\n"
                                    f"Abrir carpeta de resultados?"):
                if out_dir and os.name == "nt":
                    os.startfile(out_dir)
                elif out_dir:
                    os.system(f"xdg-open '{out_dir}'")
        else:
            self.fpm_status.set("Error en reconstruccion")
            self.status_var.set("Error durante reconstruccion FPM")

    # ══════════════════════════════════════════════════════════════
    #  Callbacks — AI tab
    # ══════════════════════════════════════════════════════════════

    def _browse_ai_image(self):
        path = filedialog.askopenfilename(
            title="Seleccionar imagen para procesamiento IA",
            filetypes=[
                ("Imagenes", "*.png *.jpg *.jpeg *.tiff *.tif *.bmp"),
                ("Todos", "*.*"),
            ]
        )
        if path:
            self.ai_image_path.set(path)

    def _start_ai_model(self):
        img_path = self.ai_image_path.get()
        if not img_path or not os.path.isfile(img_path):
            messagebox.showerror("Error", "Selecciona una imagen valida")
            return

        self.ai_run_btn.configure(state="disabled")
        self.ai_run_all_btn.configure(state="disabled")
        self.ai_progress.start(15)
        self.ai_status.set("Procesando...")
        self.log_text.delete("1.0", tk.END)

        model_name = self.ai_model_var.get()
        threading.Thread(target=self._run_ai_worker,
                         args=(img_path, model_name), daemon=True).start()

    def _start_ai_all(self):
        img_path = self.ai_image_path.get()
        if not img_path or not os.path.isfile(img_path):
            messagebox.showerror("Error", "Selecciona una imagen valida")
            return

        self.ai_run_btn.configure(state="disabled")
        self.ai_run_all_btn.configure(state="disabled")
        self.ai_progress.start(15)
        self.ai_status.set("Ejecutando todos...")
        self.log_text.delete("1.0", tk.END)

        threading.Thread(target=self._run_ai_all_worker,
                         args=(img_path,), daemon=True).start()

    def _run_ai_worker(self, img_path, model_name):
        try:
            import cv2 as _cv2
            image = _cv2.imread(img_path, _cv2.IMREAD_UNCHANGED)
            if image is None:
                self._log(f"ERROR: No se pudo leer {img_path}")
                self.root.after(0, self._ai_finished, None)
                return

            output_dir = os.path.join(os.path.dirname(img_path), "ai_results")
            kwargs = self._get_ai_kwargs(model_name)

            result = run_ai_model(
                image, model_name, output_dir=output_dir,
                logger=lambda msg: self.root.after(0, self._append_log, msg),
                **kwargs
            )
            self.root.after(0, self._ai_finished, result)

        except Exception as e:
            self._log(f"\nERROR AI: {e}")
            import traceback
            self._log(traceback.format_exc())
            self.root.after(0, self._ai_finished, None)

    def _run_ai_all_worker(self, img_path):
        try:
            import cv2 as _cv2
            import numpy as _np
            image = _cv2.imread(img_path, _cv2.IMREAD_UNCHANGED)
            if image is None:
                self._log(f"ERROR: No se pudo leer {img_path}")
                self.root.after(0, self._ai_finished, None)
                return

            if len(image.shape) == 3 and image.shape[2] == 4:
                image = _cv2.cvtColor(image, _cv2.COLOR_BGRA2BGR)
            gray = _cv2.cvtColor(image, _cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            output_dir = os.path.join(os.path.dirname(img_path), "ai_results")
            model_kwargs = {
                "cellpose": self._get_ai_kwargs("cellpose"),
                "stardist": self._get_ai_kwargs("stardist"),
                "n2v": self._get_ai_kwargs("n2v"),
            }

            results = run_all_models(
                image, output_dir,
                logger=lambda msg: self.root.after(0, self._append_log, msg),
                **model_kwargs
            )

            # ── Recolectar metricas para tabla comparativa ──
            comparison = {"segmentation": {}, "denoising": {}, "image_name": os.path.basename(img_path)}

            for name, res in results.items():
                if "error" in res:
                    continue

                if "n_cells" in res or "masks" in res or "labels" in res:
                    # Modelo de segmentacion
                    labels = res.get("masks", res.get("labels", None))
                    entry = {
                        "celulas": res.get("n_cells", 0),
                        "tiempo_s": round(res.get("elapsed", 0), 1),
                    }
                    if labels is not None:
                        unique = _np.unique(labels)
                        unique = unique[unique > 0]
                        if len(unique) > 0:
                            areas = []
                            circs = []
                            for lbl in unique:
                                mask = (labels == lbl).astype(_np.uint8)
                                area = _np.sum(mask)
                                areas.append(area)
                                contours, _ = _cv2.findContours(mask, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE)
                                if contours:
                                    perim = _cv2.arcLength(contours[0], True)
                                    if perim > 0 and area > 0:
                                        circs.append(4 * 3.14159 * area / (perim ** 2))
                            entry["area_media_px2"] = round(float(_np.mean(areas)), 1)
                            entry["area_std_px2"] = round(float(_np.std(areas)), 1)
                            entry["circ_media"] = round(float(_np.mean(circs)), 3) if circs else 0
                            entry["circ_std"] = round(float(_np.std(circs)), 3) if circs else 0
                    comparison["segmentation"][name] = entry

                elif "denoised" in res or "restored" in res:
                    # Modelo de denoising
                    denoised = res.get("denoised", res.get("restored", None))
                    entry = {"tiempo_s": round(res.get("elapsed", 0), 1)}
                    if denoised is not None:
                        den_gray = _cv2.cvtColor(denoised, _cv2.COLOR_BGR2GRAY) if len(denoised.shape) == 3 else denoised
                        ref = gray
                        # Ajustar tamanios si difieren
                        if den_gray.shape != ref.shape:
                            den_gray = _cv2.resize(den_gray, (ref.shape[1], ref.shape[0]))
                        # PSNR
                        mse = _np.mean((ref.astype(float) - den_gray.astype(float)) ** 2)
                        entry["psnr_db"] = round(float(10 * _np.log10(255.0**2 / mse)), 2) if mse > 0 else 999
                        # Contraste (std de intensidad)
                        c_orig = float(_np.std(ref.astype(float)))
                        c_den = float(_np.std(den_gray.astype(float)))
                        entry["contraste_orig"] = round(c_orig, 1)
                        entry["contraste_den"] = round(c_den, 1)
                        entry["contraste_cambio"] = f"{(c_den - c_orig) / c_orig * 100:+.1f}%"
                        # Nitidez (laplaciano)
                        s_orig = float(_np.mean(_np.abs(_cv2.Laplacian(ref, _cv2.CV_64F))))
                        s_den = float(_np.mean(_np.abs(_cv2.Laplacian(den_gray, _cv2.CV_64F))))
                        entry["nitidez_orig"] = round(s_orig, 1)
                        entry["nitidez_den"] = round(s_den, 1)
                        entry["nitidez_cambio"] = f"{(s_den - s_orig) / s_orig * 100:+.1f}%"
                    comparison["denoising"][name] = entry

            # ── Generar imagen comparativa side-by-side ──
            self._log("\nGenerando imagen comparativa...")
            try:
                panels = []
                titles = []
                h, w = gray.shape[:2]
                scale = min(400 / w, 300 / h)
                nw, nh = int(w * scale), int(h * scale)

                # Original
                orig_bgr = _cv2.cvtColor(gray, _cv2.COLOR_GRAY2BGR)
                panels.append(_cv2.resize(orig_bgr, (nw, nh)))
                titles.append("Original")

                # Segmentacion overlays
                for name, res in results.items():
                    labels = res.get("masks", res.get("labels", None))
                    if labels is not None:
                        overlay = res.get("overlay", None)
                        if overlay is not None:
                            if len(overlay.shape) == 3 and overlay.shape[2] == 4:
                                overlay = _cv2.cvtColor(overlay, _cv2.COLOR_BGRA2BGR)
                            panels.append(_cv2.resize(overlay, (nw, nh)))
                        else:
                            panels.append(_cv2.resize(orig_bgr, (nw, nh)))
                        n = res.get("n_cells", "?")
                        t = res.get("elapsed", 0)
                        titles.append(f"{name}: {n} cel, {t:.1f}s")

                # Denoising
                for name, res in results.items():
                    den = res.get("denoised", res.get("restored", None))
                    if den is not None:
                        if len(den.shape) == 2:
                            den = _cv2.cvtColor(den, _cv2.COLOR_GRAY2BGR)
                        panels.append(_cv2.resize(den, (nw, nh)))
                        titles.append(f"{name}: {res.get('elapsed', 0):.1f}s")

                if len(panels) > 1:
                    # Agregar titulo a cada panel
                    title_h = 30
                    labeled = []
                    for panel, title in zip(panels, titles):
                        lp = _np.zeros((nh + title_h, nw, 3), dtype=_np.uint8)
                        lp[:title_h, :] = (40, 40, 40)
                        _cv2.putText(lp, title, (8, 22), _cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                    (255, 255, 255), 1, _cv2.LINE_AA)
                        lp[title_h:, :] = panel
                        labeled.append(lp)

                    cols = min(3, len(labeled))
                    rows = (len(labeled) + cols - 1) // cols
                    ph = nh + title_h
                    while len(labeled) < rows * cols:
                        labeled.append(_np.zeros((ph, nw, 3), dtype=_np.uint8))

                    grid_rows = []
                    for r in range(rows):
                        grid_rows.append(_np.hstack(labeled[r * cols:(r + 1) * cols]))
                    grid = _np.vstack(grid_rows)

                    grid_path = os.path.join(output_dir, "comparacion_modelos.png")
                    _cv2.imwrite(grid_path, grid)
                    self._log(f"Imagen comparativa: {grid_path}")
            except Exception as e:
                self._log(f"Error generando imagen comparativa: {e}")

            # ── Imprimir tabla comparativa en log ──
            self._log(f"\n{'='*65}")
            self._log("TABLA COMPARATIVA DE SEGMENTACION")
            self._log(f"{'='*65}")
            self._log(f"{'Modelo':<12} {'Celulas':>8} {'Tiempo':>8} {'Area med':>10} {'Area std':>10} {'Circ med':>9} {'Circ std':>9}")
            self._log(f"{'-'*65}")
            for name, m in comparison["segmentation"].items():
                self._log(
                    f"{name:<12} {m.get('celulas','?'):>8} {m['tiempo_s']:>7.1f}s "
                    f"{m.get('area_media_px2','?'):>10} {m.get('area_std_px2','?'):>10} "
                    f"{m.get('circ_media','?'):>9} {m.get('circ_std','?'):>9}"
                )

            if comparison["denoising"]:
                self._log(f"\n{'='*65}")
                self._log("TABLA COMPARATIVA DE DENOISING")
                self._log(f"{'='*65}")
                self._log(f"{'Modelo':<8} {'Tiempo':>8} {'PSNR(dB)':>10} {'Contraste':>12} {'Nitidez':>12}")
                self._log(f"{'-'*65}")
                for name, m in comparison["denoising"].items():
                    self._log(
                        f"{name:<8} {m['tiempo_s']:>7.1f}s {m.get('psnr_db','?'):>10} "
                        f"{m.get('contraste_cambio','?'):>12} {m.get('nitidez_cambio','?'):>12}"
                    )
            self._log(f"{'='*65}")

            # Guardar tabla como JSON
            import json
            json_path = os.path.join(output_dir, "comparacion_modelos.json")
            json_data = {k: v for k, v in comparison.items() if k != "image_name"}
            json_data["imagen"] = comparison["image_name"]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            self._log(f"Datos: {json_path}")

            # Mostrar ventana con tabla
            self.root.after(0, self._show_comparison_window, comparison)
            self.root.after(0, self._ai_finished, results)

        except Exception as e:
            self._log(f"\nERROR AI: {e}")
            import traceback
            self._log(traceback.format_exc())
            self.root.after(0, self._ai_finished, None)

    def _get_ai_kwargs(self, model_name):
        if model_name == "cellpose":
            return {"model_type": self.ai_cp_model.get()}
        elif model_name == "stardist":
            return {"model_name": self.ai_sd_model.get()}
        elif model_name == "n2v":
            return {"train_on_image": self.ai_n2v_train.get()}
        return {}

    def _show_comparison_window(self, comparison):
        """Abre ventana con tabla comparativa de modelos."""
        win = tk.Toplevel(self.root)
        win.title("Comparacion de Modelos")
        win.geometry("750x500")
        win.configure(bg="#1e1e2e")

        ttk.Label(win, text=f"Comparacion: {comparison.get('image_name', '')}",
                  font=("Segoe UI", 14, "bold"), foreground="#cdd6f4",
                  background="#1e1e2e").pack(pady=(10, 5))

        # ── Tabla de segmentacion ──
        if comparison.get("segmentation"):
            seg_frame = ttk.LabelFrame(win, text="Segmentacion", padding=8)
            seg_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

            cols_seg = ("Modelo", "Celulas", "Tiempo (s)", "Area media (px2)",
                        "Area std (px2)", "Circ. media", "Circ. std")
            tree_seg = ttk.Treeview(seg_frame, columns=cols_seg, show="headings", height=4)
            for col in cols_seg:
                tree_seg.heading(col, text=col)
                w = 100 if "Modelo" in col else 90
                tree_seg.column(col, width=w, anchor="center")
            tree_seg.column("Modelo", anchor="w")

            for name, m in comparison["segmentation"].items():
                tree_seg.insert("", tk.END, values=(
                    name,
                    m.get("celulas", "?"),
                    m.get("tiempo_s", "?"),
                    m.get("area_media_px2", "--"),
                    m.get("area_std_px2", "--"),
                    m.get("circ_media", "--"),
                    m.get("circ_std", "--"),
                ))
            tree_seg.pack(fill=tk.X)

        # ── Tabla de denoising ──
        if comparison.get("denoising"):
            den_frame = ttk.LabelFrame(win, text="Denoising / Mejora", padding=8)
            den_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

            cols_den = ("Modelo", "Tiempo (s)", "PSNR (dB)", "Contraste", "Nitidez")
            tree_den = ttk.Treeview(den_frame, columns=cols_den, show="headings", height=4)
            for col in cols_den:
                tree_den.heading(col, text=col)
                tree_den.column(col, width=130, anchor="center")
            tree_den.column("Modelo", anchor="w")

            for name, m in comparison["denoising"].items():
                tree_den.insert("", tk.END, values=(
                    name,
                    m.get("tiempo_s", "?"),
                    m.get("psnr_db", "--"),
                    m.get("contraste_cambio", "--"),
                    m.get("nitidez_cambio", "--"),
                ))
            tree_den.pack(fill=tk.X)

        # ── Interpretacion ──
        interp_frame = ttk.LabelFrame(win, text="Interpretacion", padding=8)
        interp_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

        interp_text = tk.Text(interp_frame, height=8, font=("Consolas", 9),
                              bg="#181825", fg="#cdd6f4", relief=tk.FLAT, wrap=tk.WORD)
        interp_text.pack(fill=tk.X)

        lines = []
        seg = comparison.get("segmentation", {})
        den = comparison.get("denoising", {})

        if seg:
            by_cells = sorted(seg.items(), key=lambda x: x[1].get("celulas", 0), reverse=True)
            by_speed = sorted(seg.items(), key=lambda x: x[1].get("tiempo_s", 999))
            by_circ = sorted(seg.items(), key=lambda x: x[1].get("circ_media", 0), reverse=True)
            lines.append("SEGMENTACION:")
            lines.append(f"  Mayor deteccion: {by_cells[0][0]} ({by_cells[0][1].get('celulas',0)} celulas)")
            lines.append(f"  Mas rapido:      {by_speed[0][0]} ({by_speed[0][1].get('tiempo_s',0)}s)")
            lines.append(f"  Mayor regularidad: {by_circ[0][0]} (circ={by_circ[0][1].get('circ_media',0):.3f})")
            if len(by_speed) > 1:
                ratio = by_speed[-1][1].get("tiempo_s", 1) / max(by_speed[0][1].get("tiempo_s", 0.01), 0.01)
                lines.append(f"  {by_speed[0][0]} es {ratio:.0f}x mas rapido que {by_speed[-1][0]}")
            lines.append(f"  Para RPi 5: {by_speed[0][0]} es el candidato ideal (ONNX)")
            lines.append("")

        if den:
            lines.append("DENOISING:")
            for name, m in den.items():
                lines.append(f"  {name}: PSNR={m.get('psnr_db','?')}dB, "
                           f"contraste {m.get('contraste_cambio','?')}, "
                           f"nitidez {m.get('nitidez_cambio','?')}")
            lines.append("  N2V no necesita referencia limpia -> ideal para espacio")
            lines.append("  Real-ESRGAN: solo para visualizacion (puede inventar detalles)")

        interp_text.insert("1.0", "\n".join(lines))
        interp_text.configure(state=tk.DISABLED)

        # Boton cerrar
        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=8)

    def _ai_finished(self, result):
        self.ai_run_btn.configure(state="normal")
        self.ai_run_all_btn.configure(state="normal")
        self.ai_progress.stop()

        if result:
            self.ai_status.set("Completado")
            self.status_var.set("Procesamiento IA completado")

            out_dir = None
            if isinstance(result, dict):
                files = result.get("saved_files", {})
                if files:
                    out_dir = os.path.dirname(list(files.values())[0])
                else:
                    for res in result.values():
                        if isinstance(res, dict):
                            files = res.get("saved_files", {})
                            if files:
                                out_dir = os.path.dirname(list(files.values())[0])
                                break

            if out_dir and messagebox.askyesno("IA Completado", "Abrir carpeta de resultados?"):
                if os.name == "nt":
                    os.startfile(out_dir)
                else:
                    os.system(f"xdg-open '{out_dir}'")
        else:
            self.ai_status.set("Error")
            self.status_var.set("Error durante procesamiento IA")

    # ══════════════════════════════════════════════════════════════
    #  Shared
    # ══════════════════════════════════════════════════════════════

    def _log(self, msg: str):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def run(self):
        self.root.mainloop()
