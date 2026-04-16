"""
Controlador del pipeline autónomo.
Orquesta: clasificacion -> calibracion -> mejora IA -> segmentacion -> medicion -> exportacion.
"""

import os
import time
from datetime import datetime

from .config import load_config, get_output_dir
from .classifier import scan_folder
from .calibration import calibrate
from .preprocess import load_image, preprocess
from .segmentation_onion import segment_onion
from .segmentation_fiber import detect_fibers
from .measurement import measure_cells, measure_fibers, compute_summary
from .export import export_results, save_json, save_summary_txt
from .ai_enhance import run_n2v, run_cellpose, run_stardist, get_available_models


class PipelineController:
    """
    Controlador principal del pipeline autónomo.
    Un botón -> flujo completo -> resultados exportados.
    """

    def __init__(self, config_path: str = None, log_callback=None):
        self.cfg = load_config(config_path)
        self.log = log_callback or print
        self.cal_info = None
        self.um_per_pixel = self.cfg["calibration"]["default_um_per_pixel"]
        self.results = []
        # AI enhancement/segmentation options (set from GUI or config)
        self.enhance_method = None   # None, "n2v", "care"
        self.seg_ai_method = None    # None, "cellpose", "stardist" (overrides onion.method)

    def run(self, input_folder: str = None) -> dict:
        """
        Ejecuta el pipeline completo sobre una carpeta de imágenes.
        Retorna dict con resumen global.
        """
        folder = input_folder or self.cfg["paths"]["input_folder"]
        output_dir = get_output_dir(self.cfg)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)

        self.log(f"Pipeline iniciado — {timestamp}")
        self.log(f"Entrada: {folder}")
        self.log(f"Salida:  {run_dir}")
        t_start = time.time()

        # ── 1. Clasificar imágenes ──
        self.log("Escaneando y clasificando imagenes...")
        classified = scan_folder(folder, self.cfg)
        for img_type, files in classified.items():
            if files:
                self.log(f"  {img_type}: {len(files)} imagen(es)")

        # ── 2. Calibracion ──
        self.log("Calibrando...")
        if self.cal_info and self.cal_info.get("method") == "manual":
            # Calibracion manual ya fue seteada desde la GUI
            self.log(f"  {self.cal_info['message']}")
        elif classified["ruler"]:
            ruler_path = classified["ruler"][0]
            self.log(f"  Usando regla: {os.path.basename(ruler_path)}")
            _, ruler_gray = load_image(ruler_path)
            self.cal_info = calibrate(ruler_gray, self.cfg)
            self.um_per_pixel = self.cal_info["um_per_pixel"]
            self.log(f"  {self.cal_info['message']}")
        else:
            self.cal_info = {
                "success": False,
                "method": "default",
                "um_per_pixel": self.um_per_pixel,
                "message": f"Sin imagen de regla — usando default {self.um_per_pixel} um/px",
            }
            self.log(f"  {self.cal_info['message']}")

        # ── 3. Procesar imágenes de cebolla ──
        all_cell_data = []
        for fpath in classified["onion"]:
            fname = os.path.basename(fpath)
            self.log(f"Procesando cebolla: {fname}")
            try:
                result = self._process_onion(fpath, run_dir)
                all_cell_data.extend(result.get("cells", []))
                self.log(f"  -> {result.get('num_cells', 0)} celulas detectadas")
            except Exception as e:
                self.log(f"  ERROR: {e}")

        # ── 4. Procesar imágenes de fibras ──
        all_fiber_data = []
        for fpath in classified["fiber"]:
            fname = os.path.basename(fpath)
            self.log(f"Procesando fibra: {fname}")
            try:
                result = self._process_fiber(fpath, run_dir)
                all_fiber_data.extend(result.get("fibers", []))
                self.log(f"  -> {result.get('num_fibers', 0)} fibras detectadas")
            except Exception as e:
                self.log(f"  ERROR: {e}")

        # ── 5. Imágenes sin clasificar ──
        for fpath in classified["unknown"]:
            fname = os.path.basename(fpath)
            self.log(f"Sin clasificar: {fname} — intentando como cebolla")
            try:
                result = self._process_onion(fpath, run_dir)
                all_cell_data.extend(result.get("cells", []))
                self.log(f"  -> {result.get('num_cells', 0)} celulas detectadas")
            except Exception as e:
                self.log(f"  ERROR: {e}")

        # ── 6. Resumen global ──
        global_summary = compute_summary(
            cells=all_cell_data if all_cell_data else None,
            fibers=all_fiber_data if all_fiber_data else None,
        )

        elapsed = time.time() - t_start
        global_summary["pipeline"] = {
            "total_images": sum(len(v) for v in classified.values()),
            "onion_images": len(classified["onion"]),
            "fiber_images": len(classified["fiber"]),
            "ruler_images": len(classified["ruler"]),
            "unknown_images": len(classified["unknown"]),
            "elapsed_seconds": round(elapsed, 2),
            "mode": self.cfg["mode"],
        }

        # Guardar resumen global
        save_json(
            {"calibration": self.cal_info, "summary": global_summary},
            os.path.join(run_dir, "global_results.json"),
        )
        save_summary_txt(
            global_summary, self.cal_info, os.path.join(run_dir, "global_summary.txt")
        )

        self.log(f"Pipeline completado en {elapsed:.1f}s")
        self.log(f"Resultados en: {run_dir}")

        return {
            "output_dir": run_dir,
            "summary": global_summary,
            "calibration": self.cal_info,
        }

    def _process_onion(self, fpath: str, output_dir: str) -> dict:
        """Procesa una imagen de cebolla:
        preproceso -> [mejora IA] -> segmentacion [IA o OpenCV] -> medicion -> export.
        """
        import cv2
        img_color, img_gray = load_image(fpath)

        # ── Paso 2b: Mejora de imagen con IA (opcional) ──
        if self.enhance_method == "n2v":
            self.log("  [IA] Aplicando N2V denoising...")
            try:
                n2v_result = run_n2v(img_gray, n_epochs=10, logger=self.log)
                img_gray = n2v_result["denoised"]
                self.log(f"  [IA] N2V completado en {n2v_result['elapsed']:.1f}s")
            except Exception as e:
                self.log(f"  [IA] N2V fallo: {e} — continuando sin mejora")
        elif self.enhance_method == "care":
            from .ai_enhance import run_care
            self.log("  [IA] Aplicando CARE denoising...")
            try:
                care_result = run_care(img_gray, n_epochs=10, logger=self.log)
                img_gray = care_result["restored"]
                self.log(f"  [IA] CARE completado en {care_result['elapsed']:.1f}s")
            except Exception as e:
                self.log(f"  [IA] CARE fallo: {e} — continuando sin mejora")

        img_pp, mask = preprocess(img_gray, self.cfg)

        # ── Paso 3: Segmentacion (IA o OpenCV) ──
        if self.seg_ai_method == "cellpose":
            self.log("  [IA] Segmentando con Cellpose...")
            try:
                cp_result = run_cellpose(img_pp, model_type="cyto3", logger=self.log)
                seg = {
                    "labels": cp_result["masks"],
                    "num_cells": cp_result["n_cells"],
                    "method": "cellpose",
                    "overlay": cp_result["overlay"],
                }
                self.log(f"  [IA] Cellpose: {cp_result['n_cells']} celulas")
            except Exception as e:
                self.log(f"  [IA] Cellpose fallo: {e} — fallback a OpenCV")
                seg = segment_onion(img_pp, self.cfg, mask)
        elif self.seg_ai_method == "stardist":
            self.log("  [IA] Segmentando con StarDist...")
            try:
                sd_result = run_stardist(img_pp, logger=self.log)
                seg = {
                    "labels": sd_result["labels"],
                    "num_cells": sd_result["n_cells"],
                    "method": "stardist",
                    "overlay": sd_result["overlay"],
                }
                self.log(f"  [IA] StarDist: {sd_result['n_cells']} celulas")
            except Exception as e:
                self.log(f"  [IA] StarDist fallo: {e} — fallback a OpenCV")
                seg = segment_onion(img_pp, self.cfg, mask)
        else:
            seg = segment_onion(img_pp, self.cfg, mask)

        # ── Paso 4: Medicion ──
        cells = measure_cells(seg, self.um_per_pixel)
        summary = compute_summary(cells=cells)

        # ── Paso 5: Exportacion ──
        # Save AI overlay if available
        if "overlay" in seg:
            ai_overlay_path = os.path.join(
                output_dir,
                f"{os.path.splitext(os.path.basename(fpath))[0]}_ai_overlay.png"
            )
            cv2.imwrite(ai_overlay_path, seg["overlay"])

        export_results(
            output_dir=output_dir,
            image_name=os.path.basename(fpath),
            img_color=img_color,
            img_gray=img_gray,
            seg_result=seg,
            cell_measurements=cells,
            summary=summary,
            cal_info=self.cal_info,
            cfg=self.cfg,
        )

        return {"cells": cells, "num_cells": seg["num_cells"]}

    def _process_fiber(self, fpath: str, output_dir: str) -> dict:
        """Procesa una imagen de fibra: preproceso -> detección -> medición -> export."""
        img_color, img_gray = load_image(fpath)
        img_pp, _ = preprocess(img_gray, self.cfg)

        fiber_res = detect_fibers(img_pp, self.cfg)
        fibers = measure_fibers(fiber_res, self.um_per_pixel)
        summary = compute_summary(fibers=fibers)

        export_results(
            output_dir=output_dir,
            image_name=os.path.basename(fpath),
            img_color=img_color,
            fiber_result=fiber_res,
            fiber_measurements=fibers,
            summary=summary,
            cal_info=self.cal_info,
            cfg=self.cfg,
        )

        return {"fibers": fibers, "num_fibers": fiber_res["num_fibers"]}
