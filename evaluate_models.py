"""
Evaluacion comparativa de modelos de segmentacion y denoising.
Corre Cellpose, StarDist, OpenCV, N2V y CARE sobre las mismas imagenes
y genera tablas comparativas, overlays side-by-side e IoU cruzado.

Uso:
    python evaluate_models.py
    python evaluate_models.py --images "ruta1.jpg" "ruta2.tiff"
"""

import os
import sys
import time
import argparse
import json
import csv
import traceback
import numpy as np
import cv2
from datetime import datetime

# ── Suprimir warnings de TF ──
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

# ── Imports del pipeline ──
sys.path.insert(0, os.path.dirname(__file__))
from pipeline.ai_enhance import (
    run_cellpose, run_stardist, run_n2v, run_care,
    get_available_models, _HAS_CELLPOSE, _HAS_STARDIST,
    _HAS_N2V, _HAS_CARE
)
from pipeline.preprocess import preprocess
from pipeline.segmentation_onion import segment_onion
from pipeline.config import load_config


def log(msg):
    print(f"[EVAL] {msg}")


# ══════════════════════════════════════════════════════════════
# Metricas
# ══════════════════════════════════════════════════════════════

def count_cells(labels):
    """Cuenta celulas unicas en mapa de labels (0 = fondo)."""
    unique = np.unique(labels)
    return len(unique[unique > 0])


def area_stats(labels, um_per_pixel=1.0):
    """Estadisticas de area por celula."""
    unique = np.unique(labels)
    unique = unique[unique > 0]
    if len(unique) == 0:
        return {"count": 0, "mean": 0, "std": 0, "median": 0, "min": 0, "max": 0}
    areas = []
    for lbl in unique:
        area_px = np.sum(labels == lbl)
        areas.append(area_px * um_per_pixel ** 2)
    areas = np.array(areas)
    return {
        "count": len(areas),
        "mean": float(np.mean(areas)),
        "std": float(np.std(areas)),
        "median": float(np.median(areas)),
        "min": float(np.min(areas)),
        "max": float(np.max(areas)),
    }


def perimeter_stats(labels, um_per_pixel=1.0):
    """Estadisticas de perimetro por celula."""
    unique = np.unique(labels)
    unique = unique[unique > 0]
    if len(unique) == 0:
        return {"mean": 0, "std": 0, "median": 0}
    perimeters = []
    for lbl in unique:
        mask = (labels == lbl).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            p = cv2.arcLength(contours[0], True) * um_per_pixel
            perimeters.append(p)
    if not perimeters:
        return {"mean": 0, "std": 0, "median": 0}
    perimeters = np.array(perimeters)
    return {
        "mean": float(np.mean(perimeters)),
        "std": float(np.std(perimeters)),
        "median": float(np.median(perimeters)),
    }


def circularity_stats(labels):
    """Estadisticas de circularidad por celula."""
    unique = np.unique(labels)
    unique = unique[unique > 0]
    if len(unique) == 0:
        return {"mean": 0, "std": 0, "median": 0}
    circs = []
    for lbl in unique:
        mask = (labels == lbl).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            area = cv2.contourArea(contours[0])
            perim = cv2.arcLength(contours[0], True)
            if perim > 0 and area > 0:
                c = 4 * np.pi * area / (perim ** 2)
                circs.append(c)
    if not circs:
        return {"mean": 0, "std": 0, "median": 0}
    circs = np.array(circs)
    return {
        "mean": float(np.mean(circs)),
        "std": float(np.std(circs)),
        "median": float(np.median(circs)),
    }


def iou_between_masks(labels_a, labels_b):
    """
    IoU cruzado entre dos mapas de labels.
    Para cada celula en A, encuentra la celula en B con mayor overlap.
    Retorna: IoU promedio, matched pairs, unmatched en A, unmatched en B.
    """
    ids_a = np.unique(labels_a)
    ids_a = ids_a[ids_a > 0]
    ids_b = np.unique(labels_b)
    ids_b = ids_b[ids_b > 0]

    if len(ids_a) == 0 or len(ids_b) == 0:
        return {"mean_iou": 0, "matched": 0, "unmatched_a": len(ids_a),
                "unmatched_b": len(ids_b), "ious": []}

    matched_b = set()
    ious = []
    unmatched_a = 0

    for a_id in ids_a:
        mask_a = (labels_a == a_id)
        # Encontrar labels de B que intersectan con esta celula de A
        overlapping_b = np.unique(labels_b[mask_a])
        overlapping_b = overlapping_b[overlapping_b > 0]

        best_iou = 0
        best_b = None
        for b_id in overlapping_b:
            mask_b = (labels_b == b_id)
            intersection = np.sum(mask_a & mask_b)
            union = np.sum(mask_a | mask_b)
            if union > 0:
                iou = intersection / union
                if iou > best_iou:
                    best_iou = iou
                    best_b = b_id

        if best_iou > 0.3:  # umbral minimo para considerar match
            ious.append(best_iou)
            if best_b is not None:
                matched_b.add(best_b)
        else:
            unmatched_a += 1

    unmatched_b = len(ids_b) - len(matched_b)

    return {
        "mean_iou": float(np.mean(ious)) if ious else 0,
        "matched": len(ious),
        "unmatched_a": unmatched_a,
        "unmatched_b": unmatched_b,
        "ious": [float(x) for x in ious],
    }


def psnr(original, denoised):
    """Peak Signal-to-Noise Ratio."""
    mse = np.mean((original.astype(float) - denoised.astype(float)) ** 2)
    if mse == 0:
        return float("inf")
    return float(10 * np.log10(255.0 ** 2 / mse))


def ssim_simple(img1, img2, window_size=7):
    """SSIM simplificado (sin dependencia extra)."""
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)

    kernel = cv2.getGaussianKernel(window_size, 1.5)
    window = np.outer(kernel, kernel.transpose())

    mu1 = cv2.filter2D(img1, -1, window)
    mu2 = cv2.filter2D(img2, -1, window)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.filter2D(img1 ** 2, -1, window) - mu1_sq
    sigma2_sq = cv2.filter2D(img2 ** 2, -1, window) - mu2_sq
    sigma12 = cv2.filter2D(img1 * img2, -1, window) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

    return float(np.mean(ssim_map))


# ══════════════════════════════════════════════════════════════
# Ejecucion de modelos
# ══════════════════════════════════════════════════════════════

def run_opencv_segmentation(img_gray, cfg):
    """Corre segmentacion OpenCV y retorna labels."""
    img_pp, mask = preprocess(img_gray, cfg)
    seg = segment_onion(img_pp, cfg, mask)
    return seg.get("labels", np.zeros_like(img_gray, dtype=np.int32))


def run_all_segmentation(img_gray, cfg):
    """Corre todos los modelos de segmentacion disponibles."""
    results = {}
    img_pp, mask = preprocess(img_gray, cfg)

    # OpenCV
    log("  Corriendo OpenCV...")
    t0 = time.time()
    try:
        seg_cv = segment_onion(img_pp, cfg, mask)
        t_cv = time.time() - t0
        results["OpenCV"] = {
            "labels": seg_cv.get("labels", np.zeros_like(img_gray, dtype=np.int32)),
            "time": t_cv,
            "num_cells": seg_cv.get("num_cells", 0),
            "overlay": seg_cv.get("overlay", None),
            "success": True,
        }
        log(f"  OpenCV: {seg_cv.get('num_cells', 0)} celulas en {t_cv:.1f}s")
    except Exception as e:
        log(f"  OpenCV FALLO: {e}")
        results["OpenCV"] = {"success": False, "error": str(e), "time": 0}

    # Cellpose
    if _HAS_CELLPOSE:
        log("  Corriendo Cellpose cyto3...")
        t0 = time.time()
        try:
            cp = run_cellpose(img_pp, model_type="cyto3", logger=lambda m: log(f"    {m}"))
            t_cp = time.time() - t0
            results["Cellpose"] = {
                "labels": cp["masks"],
                "time": t_cp,
                "num_cells": cp["n_cells"],
                "overlay": cp["overlay"],
                "diameter": cp.get("diameter", None),
                "success": True,
            }
            log(f"  Cellpose: {cp['n_cells']} celulas en {t_cp:.1f}s")
        except Exception as e:
            log(f"  Cellpose FALLO: {e}")
            traceback.print_exc()
            results["Cellpose"] = {"success": False, "error": str(e), "time": 0}
    else:
        log("  Cellpose NO DISPONIBLE")
        results["Cellpose"] = {"success": False, "error": "not installed", "time": 0}

    # StarDist
    if _HAS_STARDIST:
        log("  Corriendo StarDist...")
        t0 = time.time()
        try:
            sd = run_stardist(img_pp, logger=lambda m: log(f"    {m}"))
            t_sd = time.time() - t0
            results["StarDist"] = {
                "labels": sd["labels"],
                "time": t_sd,
                "num_cells": sd["n_cells"],
                "overlay": sd["overlay"],
                "success": True,
            }
            log(f"  StarDist: {sd['n_cells']} celulas en {t_sd:.1f}s")
        except Exception as e:
            log(f"  StarDist FALLO: {e}")
            traceback.print_exc()
            results["StarDist"] = {"success": False, "error": str(e), "time": 0}
    else:
        log("  StarDist NO DISPONIBLE")
        results["StarDist"] = {"success": False, "error": "not installed", "time": 0}

    return results


def run_all_denoising(img_gray):
    """Corre todos los modelos de denoising disponibles."""
    results = {}

    # N2V
    if _HAS_N2V:
        log("  Corriendo N2V (10 epochs)...")
        t0 = time.time()
        try:
            n2v = run_n2v(img_gray, n_epochs=10, logger=lambda m: log(f"    {m}"))
            t_n2v = time.time() - t0
            results["N2V"] = {
                "denoised": n2v["denoised"],
                "time": t_n2v,
                "success": True,
            }
            log(f"  N2V completado en {t_n2v:.1f}s")
        except Exception as e:
            log(f"  N2V FALLO: {e}")
            traceback.print_exc()
            results["N2V"] = {"success": False, "error": str(e), "time": 0}
    else:
        log("  N2V NO DISPONIBLE (TensorFlow)")
        results["N2V"] = {"success": False, "error": "TF not installed", "time": 0}

    # CARE
    if _HAS_CARE:
        log("  Corriendo CARE (10 epochs)...")
        t0 = time.time()
        try:
            care = run_care(img_gray, n_epochs=10, logger=lambda m: log(f"    {m}"))
            t_care = time.time() - t0
            results["CARE"] = {
                "denoised": care["restored"],
                "time": t_care,
                "success": True,
            }
            log(f"  CARE completado en {t_care:.1f}s")
        except Exception as e:
            log(f"  CARE FALLO: {e}")
            traceback.print_exc()
            results["CARE"] = {"success": False, "error": str(e), "time": 0}
    else:
        log("  CARE NO DISPONIBLE (TensorFlow)")
        results["CARE"] = {"success": False, "error": "TF not installed", "time": 0}

    return results


# ══════════════════════════════════════════════════════════════
# Generacion de imagenes comparativas
# ══════════════════════════════════════════════════════════════

def labels_to_color(labels, img_base=None):
    """Convierte mapa de labels a imagen coloreada con overlay."""
    if img_base is not None:
        if len(img_base.shape) == 2:
            base = cv2.cvtColor(img_base, cv2.COLOR_GRAY2BGR)
        else:
            base = img_base.copy()
    else:
        base = np.zeros((*labels.shape[:2], 3), dtype=np.uint8)

    unique = np.unique(labels)
    unique = unique[unique > 0]

    np.random.seed(42)
    colors = np.random.randint(60, 255, size=(len(unique) + 1, 3), dtype=np.uint8)

    overlay = base.copy()
    for i, lbl in enumerate(unique):
        mask = (labels == lbl).astype(np.uint8)
        color = tuple(int(c) for c in colors[i])
        # Rellenar celula con transparencia
        colored = np.full_like(overlay, color, dtype=np.uint8)
        overlay = np.where(mask[:, :, np.newaxis] > 0,
                          cv2.addWeighted(overlay, 0.5, colored, 0.5, 0),
                          overlay)
        # Dibujar contorno
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, color, 1)

    return overlay


def make_comparison_grid(img_gray, seg_results, denoise_results, image_name):
    """Genera imagen grid comparativa."""
    # Determinar tamanio base
    h, w = img_gray.shape[:2]
    # Escalar para que cada panel tenga max 500px de ancho
    scale = min(500 / w, 400 / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    panels = []
    titles = []

    # Panel 1: Original
    orig_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    panels.append(cv2.resize(orig_bgr, (new_w, new_h)))
    titles.append("Original")

    # Paneles de segmentacion
    for name in ["OpenCV", "Cellpose", "StarDist"]:
        if name in seg_results and seg_results[name].get("success"):
            r = seg_results[name]
            overlay = labels_to_color(r["labels"], img_gray)
            panel = cv2.resize(overlay, (new_w, new_h))
            n = r.get("num_cells", "?")
            t = r.get("time", 0)
            titles.append(f"{name}: {n} cel, {t:.1f}s")
            panels.append(panel)

    # Paneles de denoising
    for name in ["N2V", "CARE"]:
        if name in denoise_results and denoise_results[name].get("success"):
            r = denoise_results[name]
            den = r["denoised"]
            if len(den.shape) == 2:
                den_bgr = cv2.cvtColor(den, cv2.COLOR_GRAY2BGR)
            else:
                den_bgr = den
            panel = cv2.resize(den_bgr, (new_w, new_h))
            t = r.get("time", 0)
            titles.append(f"{name}: {t:.1f}s")
            panels.append(panel)

    if not panels:
        return None

    # Organizar en grid 2x3 o 3x2
    n_panels = len(panels)
    cols = min(3, n_panels)
    rows = (n_panels + cols - 1) // cols

    # Agregar titulo a cada panel
    title_h = 35
    labeled_panels = []
    for panel, title in zip(panels, titles):
        lp = np.zeros((new_h + title_h, new_w, 3), dtype=np.uint8)
        lp[:title_h, :] = (40, 40, 40)
        cv2.putText(lp, title, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 1, cv2.LINE_AA)
        lp[title_h:, :] = panel
        labeled_panels.append(lp)

    # Rellenar con paneles vacios si necesario
    panel_h = new_h + title_h
    while len(labeled_panels) < rows * cols:
        labeled_panels.append(np.zeros((panel_h, new_w, 3), dtype=np.uint8))

    # Armar grid
    grid_rows = []
    for r in range(rows):
        row_panels = labeled_panels[r * cols: (r + 1) * cols]
        grid_rows.append(np.hstack(row_panels))
    grid = np.vstack(grid_rows)

    # Titulo superior
    header_h = 45
    header = np.zeros((header_h, grid.shape[1], 3), dtype=np.uint8)
    header[:] = (60, 60, 60)
    cv2.putText(header, f"Comparacion de Modelos: {image_name}",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    return np.vstack([header, grid])


def make_iou_heatmap(iou_matrix, model_names, out_path):
    """Genera heatmap de IoU cruzado entre modelos."""
    n = len(model_names)
    cell_size = 120
    margin = 150
    img_w = margin + n * cell_size
    img_h = margin + n * cell_size

    img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 255

    # Headers
    for i, name in enumerate(model_names):
        x = margin + i * cell_size + cell_size // 2
        cv2.putText(img, name, (x - 30, margin - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        y = margin + i * cell_size + cell_size // 2
        cv2.putText(img, name, (10, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    # Celdas
    for i in range(n):
        for j in range(n):
            x1 = margin + j * cell_size
            y1 = margin + i * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size

            val = iou_matrix[i][j]
            # Color: rojo (0) -> amarillo (0.5) -> verde (1.0)
            if val >= 0.5:
                g = 255
                r = int(255 * (1 - (val - 0.5) * 2))
            else:
                r = 255
                g = int(255 * val * 2)
            color = (0, g, r)  # BGR

            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (100, 100, 100), 1)

            # Texto
            text = f"{val:.2f}" if val > 0 else "N/A"
            txt_color = (0, 0, 0) if val > 0.3 else (255, 255, 255)
            cv2.putText(img, text, (x1 + 30, y1 + cell_size // 2 + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, txt_color, 1, cv2.LINE_AA)

    # Titulo
    cv2.putText(img, "IoU cruzado entre modelos", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

    cv2.imwrite(out_path, img)
    return out_path


# ══════════════════════════════════════════════════════════════
# Evaluacion principal
# ══════════════════════════════════════════════════════════════

def evaluate_image(image_path, output_dir, cfg):
    """Evaluacion completa de una imagen."""
    image_name = os.path.basename(image_path)
    log(f"\n{'='*60}")
    log(f"EVALUANDO: {image_name}")
    log(f"{'='*60}")

    # Cargar imagen
    img_color = cv2.imread(image_path)
    if img_color is None:
        log(f"ERROR: No se pudo cargar {image_path}")
        return None

    if len(img_color.shape) == 3 and img_color.shape[2] == 4:
        img_color = cv2.cvtColor(img_color, cv2.COLOR_BGRA2BGR)

    img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    h, w = img_gray.shape
    log(f"  Tamanio: {w}x{h}, dtype: {img_gray.dtype}")

    # Crear subcarpeta
    img_dir = os.path.join(output_dir, os.path.splitext(image_name)[0])
    os.makedirs(img_dir, exist_ok=True)

    # ── 1. Segmentacion ──
    log("\n-- SEGMENTACION --")
    seg_results = run_all_segmentation(img_gray, cfg)

    # ── 2. Denoising ──
    log("\n-- DENOISING --")
    denoise_results = run_all_denoising(img_gray)

    # ── 3. Segmentacion post-denoising ──
    log("\n-- SEGMENTACION POST-DENOISING --")
    for dn_name in ["N2V", "CARE"]:
        if dn_name in denoise_results and denoise_results[dn_name].get("success"):
            denoised = denoise_results[dn_name]["denoised"]
            log(f"  Segmentando imagen denoised con {dn_name} + OpenCV...")
            t0 = time.time()
            try:
                img_pp, mask = preprocess(denoised, cfg)
                seg = segment_onion(img_pp, cfg, mask)
                t_seg = time.time() - t0
                combo_name = f"{dn_name}+OpenCV"
                seg_results[combo_name] = {
                    "labels": seg.get("labels", np.zeros_like(img_gray, dtype=np.int32)),
                    "time": denoise_results[dn_name]["time"] + t_seg,
                    "num_cells": seg.get("num_cells", 0),
                    "success": True,
                }
                log(f"  {combo_name}: {seg.get('num_cells', 0)} celulas "
                    f"({denoise_results[dn_name]['time']:.1f}s denoise + {t_seg:.1f}s seg)")
            except Exception as e:
                log(f"  {dn_name}+OpenCV FALLO: {e}")

    # ── 4. Metricas por modelo ──
    log("\n-- METRICAS --")
    all_metrics = {}

    for name, res in seg_results.items():
        if not res.get("success"):
            continue
        labels = res["labels"]
        areas = area_stats(labels)
        perims = perimeter_stats(labels)
        circs = circularity_stats(labels)

        metrics = {
            "modelo": name,
            "celulas": areas["count"],
            "tiempo_s": round(res.get("time", 0), 2),
            "area_media_px2": round(areas["mean"], 1),
            "area_std_px2": round(areas["std"], 1),
            "area_mediana_px2": round(areas["median"], 1),
            "area_min_px2": round(areas["min"], 1),
            "area_max_px2": round(areas["max"], 1),
            "perimetro_medio_px": round(perims["mean"], 1),
            "perimetro_std_px": round(perims["std"], 1),
            "circularidad_media": round(circs["mean"], 3),
            "circularidad_std": round(circs["std"], 3),
            "circularidad_mediana": round(circs["median"], 3),
        }
        all_metrics[name] = metrics
        log(f"  {name}: {metrics['celulas']} cel, area={metrics['area_media_px2']}px2, "
            f"circ={metrics['circularidad_media']}, t={metrics['tiempo_s']}s")

    # Metricas de denoising
    denoise_metrics = {}
    for dn_name, res in denoise_results.items():
        if not res.get("success"):
            continue
        denoised = res["denoised"]
        p = psnr(img_gray, denoised)
        s = ssim_simple(img_gray, denoised)
        # Contraste: std de intensidad (mayor = mas contraste)
        contrast_orig = float(np.std(img_gray.astype(float)))
        contrast_den = float(np.std(denoised.astype(float)))
        # Sharpness: media del laplaciano (mayor = mas nitido)
        sharp_orig = float(np.mean(np.abs(cv2.Laplacian(img_gray, cv2.CV_64F))))
        sharp_den = float(np.mean(np.abs(cv2.Laplacian(denoised, cv2.CV_64F))))

        denoise_metrics[dn_name] = {
            "modelo": dn_name,
            "tiempo_s": round(res["time"], 2),
            "psnr_db": round(p, 2),
            "ssim": round(s, 4),
            "contraste_original": round(contrast_orig, 2),
            "contraste_denoised": round(contrast_den, 2),
            "cambio_contraste_pct": round((contrast_den - contrast_orig) / contrast_orig * 100, 1),
            "nitidez_original": round(sharp_orig, 2),
            "nitidez_denoised": round(sharp_den, 2),
            "cambio_nitidez_pct": round((sharp_den - sharp_orig) / sharp_orig * 100, 1),
        }
        log(f"  {dn_name}: PSNR={p:.2f}dB, SSIM={s:.4f}, "
            f"contraste {denoise_metrics[dn_name]['cambio_contraste_pct']:+.1f}%, "
            f"nitidez {denoise_metrics[dn_name]['cambio_nitidez_pct']:+.1f}%")

    # ── 5. IoU cruzado ──
    log("\n-- IoU CRUZADO --")
    seg_names = [n for n in seg_results if seg_results[n].get("success")]
    n_seg = len(seg_names)
    iou_matrix = np.zeros((n_seg, n_seg))
    iou_details = {}

    for i, name_a in enumerate(seg_names):
        for j, name_b in enumerate(seg_names):
            if i == j:
                iou_matrix[i][j] = 1.0
            elif j > i:
                log(f"  {name_a} vs {name_b}...")
                iou_res = iou_between_masks(
                    seg_results[name_a]["labels"],
                    seg_results[name_b]["labels"]
                )
                iou_matrix[i][j] = iou_res["mean_iou"]
                iou_matrix[j][i] = iou_res["mean_iou"]
                key = f"{name_a}_vs_{name_b}"
                iou_details[key] = iou_res
                log(f"    IoU={iou_res['mean_iou']:.3f}, "
                    f"matched={iou_res['matched']}, "
                    f"solo_{name_a}={iou_res['unmatched_a']}, "
                    f"solo_{name_b}={iou_res['unmatched_b']}")

    # ── 6. Guardar overlays ──
    log("\n-- GUARDANDO RESULTADOS --")

    # Overlays individuales
    for name, res in seg_results.items():
        if not res.get("success"):
            continue
        overlay = labels_to_color(res["labels"], img_gray)
        path = os.path.join(img_dir, f"seg_{name.replace('+', '_')}.png")
        cv2.imwrite(path, overlay)

    # Imagenes denoised
    for dn_name, res in denoise_results.items():
        if not res.get("success"):
            continue
        path = os.path.join(img_dir, f"denoise_{dn_name}.png")
        cv2.imwrite(path, res["denoised"])

    # Grid comparativa
    grid = make_comparison_grid(img_gray, seg_results, denoise_results, image_name)
    if grid is not None:
        cv2.imwrite(os.path.join(img_dir, "comparacion_grid.png"), grid)

    # Heatmap IoU
    if n_seg >= 2:
        make_iou_heatmap(iou_matrix.tolist(), seg_names,
                         os.path.join(img_dir, "iou_heatmap.png"))

    # ── 7. Tablas en texto ──
    report_lines = []
    report_lines.append(f"EVALUACION: {image_name}")
    report_lines.append(f"Tamanio: {w}x{h}")
    report_lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # Tabla de segmentacion
    report_lines.append("=" * 100)
    report_lines.append("TABLA COMPARATIVA DE SEGMENTACION")
    report_lines.append("=" * 100)
    header = f"{'Modelo':<15} {'Celulas':>8} {'Tiempo':>8} {'Area media':>12} {'Area std':>10} {'Perim medio':>12} {'Circ media':>11} {'Circ std':>9}"
    report_lines.append(header)
    report_lines.append("-" * 100)
    for name in seg_names:
        if name in all_metrics:
            m = all_metrics[name]
            line = (f"{m['modelo']:<15} {m['celulas']:>8} {m['tiempo_s']:>7.1f}s "
                    f"{m['area_media_px2']:>11.1f} {m['area_std_px2']:>10.1f} "
                    f"{m['perimetro_medio_px']:>12.1f} {m['circularidad_media']:>11.3f} "
                    f"{m['circularidad_std']:>9.3f}")
            report_lines.append(line)
    report_lines.append("")

    # Tabla de denoising
    if denoise_metrics:
        report_lines.append("=" * 100)
        report_lines.append("TABLA COMPARATIVA DE DENOISING")
        report_lines.append("=" * 100)
        header = f"{'Modelo':<10} {'Tiempo':>8} {'PSNR(dB)':>10} {'SSIM':>8} {'Contraste%':>12} {'Nitidez%':>10}"
        report_lines.append(header)
        report_lines.append("-" * 100)
        for name, dm in denoise_metrics.items():
            line = (f"{dm['modelo']:<10} {dm['tiempo_s']:>7.1f}s {dm['psnr_db']:>10.2f} "
                    f"{dm['ssim']:>8.4f} {dm['cambio_contraste_pct']:>+11.1f}% "
                    f"{dm['cambio_nitidez_pct']:>+9.1f}%")
            report_lines.append(line)
        report_lines.append("")

    # Tabla IoU cruzado
    if n_seg >= 2:
        report_lines.append("=" * 100)
        report_lines.append("MATRIZ IoU CRUZADO (umbral match > 0.3)")
        report_lines.append("=" * 100)
        # Header
        header = f"{'':15}" + "".join(f"{n:>15}" for n in seg_names)
        report_lines.append(header)
        report_lines.append("-" * (15 + 15 * n_seg))
        for i, name in enumerate(seg_names):
            row = f"{name:<15}" + "".join(f"{iou_matrix[i][j]:>15.3f}" for j in range(n_seg))
            report_lines.append(row)
        report_lines.append("")

        # Detalle de IoU
        report_lines.append("DETALLE IoU:")
        for key, detail in iou_details.items():
            names = key.split("_vs_")
            report_lines.append(f"  {names[0]} vs {names[1]}:")
            report_lines.append(f"    IoU promedio:    {detail['mean_iou']:.3f}")
            report_lines.append(f"    Celulas matched: {detail['matched']}")
            report_lines.append(f"    Solo en {names[0]}: {detail['unmatched_a']}")
            report_lines.append(f"    Solo en {names[1]}: {detail['unmatched_b']}")
            if detail['ious']:
                report_lines.append(f"    IoU min:         {min(detail['ious']):.3f}")
                report_lines.append(f"    IoU max:         {max(detail['ious']):.3f}")
                # Distribucion de IoU
                ious_arr = np.array(detail['ious'])
                bins = [0.3, 0.5, 0.7, 0.9, 1.01]
                labels_bins = ["0.3-0.5", "0.5-0.7", "0.7-0.9", "0.9-1.0"]
                report_lines.append(f"    Distribucion IoU:")
                for k in range(len(bins) - 1):
                    count = np.sum((ious_arr >= bins[k]) & (ious_arr < bins[k + 1]))
                    pct = count / len(ious_arr) * 100
                    bar = "#" * int(pct / 2)
                    report_lines.append(f"      {labels_bins[k]}: {count:3d} ({pct:5.1f}%) {bar}")

    report_text = "\n".join(report_lines)
    log(f"\n{report_text}")

    # Guardar reporte
    with open(os.path.join(img_dir, "evaluacion.txt"), "w", encoding="utf-8") as f:
        f.write(report_text)

    # Guardar JSON
    json_data = {
        "image": image_name,
        "size": f"{w}x{h}",
        "segmentation": all_metrics,
        "denoising": denoise_metrics,
        "iou_cross": {k: {kk: vv for kk, vv in v.items() if kk != "ious"}
                      for k, v in iou_details.items()},
        "iou_matrix": {seg_names[i]: {seg_names[j]: round(iou_matrix[i][j], 4)
                                       for j in range(n_seg)}
                       for i in range(n_seg)},
    }
    with open(os.path.join(img_dir, "evaluacion.json"), "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # CSV de metricas
    if all_metrics:
        csv_path = os.path.join(img_dir, "metricas_segmentacion.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(list(all_metrics.values())[0].keys()))
            writer.writeheader()
            for m in all_metrics.values():
                writer.writerow(m)

    return json_data


def generate_global_report(all_results, output_dir):
    """Genera reporte global comparando resultados de todas las imagenes."""
    log(f"\n{'='*60}")
    log("REPORTE GLOBAL")
    log(f"{'='*60}")

    report = []
    report.append("REPORTE GLOBAL DE EVALUACION")
    report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Imagenes evaluadas: {len(all_results)}")
    report.append("")

    # Agregar metricas por modelo a traves de todas las imagenes
    model_agg = {}
    for result in all_results:
        if result is None:
            continue
        for name, metrics in result.get("segmentation", {}).items():
            if name not in model_agg:
                model_agg[name] = {"celulas": [], "tiempos": [], "areas": [], "circs": []}
            model_agg[name]["celulas"].append(metrics["celulas"])
            model_agg[name]["tiempos"].append(metrics["tiempo_s"])
            model_agg[name]["areas"].append(metrics["area_media_px2"])
            model_agg[name]["circs"].append(metrics["circularidad_media"])

    report.append("=" * 90)
    report.append("RESUMEN POR MODELO (promedio sobre todas las imagenes)")
    report.append("=" * 90)
    report.append(f"{'Modelo':<15} {'Celulas (prom)':>14} {'Tiempo (prom)':>14} {'Area (prom)':>12} {'Circ (prom)':>12}")
    report.append("-" * 90)
    for name, agg in model_agg.items():
        report.append(
            f"{name:<15} "
            f"{np.mean(agg['celulas']):>14.1f} "
            f"{np.mean(agg['tiempos']):>13.1f}s "
            f"{np.mean(agg['areas']):>12.1f} "
            f"{np.mean(agg['circs']):>12.3f}"
        )
    report.append("")

    # Ranking
    report.append("RANKING POR CRITERIO:")
    report.append("")

    # Mas celulas detectadas
    by_cells = sorted(model_agg.items(), key=lambda x: np.mean(x[1]["celulas"]), reverse=True)
    report.append("  Mayor deteccion (celulas promedio):")
    for i, (name, agg) in enumerate(by_cells):
        report.append(f"    {i+1}. {name}: {np.mean(agg['celulas']):.0f}")

    # Mas rapido
    by_speed = sorted(model_agg.items(), key=lambda x: np.mean(x[1]["tiempos"]))
    report.append("  Mas rapido:")
    for i, (name, agg) in enumerate(by_speed):
        report.append(f"    {i+1}. {name}: {np.mean(agg['tiempos']):.1f}s")

    # Mayor circularidad (celdas mas regulares)
    by_circ = sorted(model_agg.items(), key=lambda x: np.mean(x[1]["circs"]), reverse=True)
    report.append("  Mayor circularidad media (formas mas regulares):")
    for i, (name, agg) in enumerate(by_circ):
        report.append(f"    {i+1}. {name}: {np.mean(agg['circs']):.3f}")

    report_text = "\n".join(report)
    log(f"\n{report_text}")

    with open(os.path.join(output_dir, "reporte_global.txt"), "w", encoding="utf-8") as f:
        f.write(report_text)

    # JSON global
    with open(os.path.join(output_dir, "reporte_global.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)


def main():
    parser = argparse.ArgumentParser(description="Evaluacion comparativa de modelos IA")
    parser.add_argument("--images", nargs="+", default=None,
                        help="Rutas a imagenes a evaluar")
    parser.add_argument("--output", type=str, default=None,
                        help="Carpeta de salida")
    args = parser.parse_args()

    # Imagenes por defecto
    if args.images:
        image_paths = args.images
    else:
        base = os.path.dirname(__file__)
        image_paths = [
            os.path.join(base, "Imagenes", "imagenes de internet", "piel de cebolla ejemplo1.jpg"),
            os.path.join(base, "Imagenes", "Prueba 05-12-2025", "img_00_04_cx113_cy145.tiff"),
        ]
        # Filtrar solo las que existen
        image_paths = [p for p in image_paths if os.path.exists(p)]

    if not image_paths:
        log("ERROR: No se encontraron imagenes para evaluar")
        return

    # Output dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output or os.path.join(
        os.path.dirname(__file__), "Resultados", f"evaluacion_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    log(f"Imagenes a evaluar: {len(image_paths)}")
    for p in image_paths:
        log(f"  - {p}")
    log(f"Salida: {output_dir}")

    # Modelos disponibles
    available = get_available_models()
    log(f"\nModelos disponibles:")
    for name, avail in available.items():
        log(f"  {name}: {'SI' if avail else 'NO'}")

    # Config
    cfg = load_config()

    # Evaluar cada imagen
    all_results = []
    for img_path in image_paths:
        result = evaluate_image(img_path, output_dir, cfg)
        all_results.append(result)

    # Reporte global
    valid_results = [r for r in all_results if r is not None]
    if valid_results:
        generate_global_report(valid_results, output_dir)

    log(f"\nEvaluacion completa. Resultados en: {output_dir}")


if __name__ == "__main__":
    main()
