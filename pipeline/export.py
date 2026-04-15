"""
Exportación de resultados: overlays, máscaras, CSV, JSON, resumen.
"""

import os
import csv
import json
import cv2
import numpy as np


def draw_overlay(img_color: np.ndarray, seg_result: dict, cfg: dict) -> np.ndarray:
    """Dibuja contornos y labels sobre la imagen original."""
    overlay = img_color.copy()
    alpha = cfg["export"]["overlay_alpha"]

    contours = seg_result.get("contours", [])
    num = len(contours)

    # Generar colores únicos
    colors = []
    for i in range(num):
        hue = int(180 * i / max(num, 1))
        c = np.array([[[hue, 200, 230]]], dtype=np.uint8)
        rgb = cv2.cvtColor(c, cv2.COLOR_HSV2BGR)[0][0]
        colors.append((int(rgb[0]), int(rgb[1]), int(rgb[2])))

    # Dibujar relleno semitransparente
    fill = overlay.copy()
    for i, cnt in enumerate(contours):
        cv2.drawContours(fill, [cnt], -1, colors[i % len(colors)], cv2.FILLED)
    cv2.addWeighted(fill, alpha, overlay, 1 - alpha, 0, overlay)

    # Dibujar bordes
    for i, cnt in enumerate(contours):
        cv2.drawContours(overlay, [cnt], -1, colors[i % len(colors)], 1)

    return overlay


def draw_fiber_overlay(img_color: np.ndarray, fiber_result: dict) -> np.ndarray:
    """Dibuja líneas de fibras sobre la imagen."""
    overlay = img_color.copy()
    for line in fiber_result.get("lines", []):
        cv2.line(
            overlay,
            (line["x1"], line["y1"]),
            (line["x2"], line["y2"]),
            (0, 255, 0),
            2,
        )
    return overlay


def save_mask(labels: np.ndarray, filepath: str):
    """Guarda label map como imagen (16-bit para muchas instancias)."""
    if labels.max() > 255:
        cv2.imwrite(filepath, labels.astype(np.uint16))
    else:
        cv2.imwrite(filepath, labels.astype(np.uint8))


def save_csv(measurements: list, filepath: str):
    """Guarda mediciones en CSV."""
    if not measurements:
        return
    keys = measurements[0].keys()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(measurements)


def save_json(data: dict, filepath: str):
    """Guarda datos en JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def save_summary_txt(summary: dict, cal_info: dict, filepath: str):
    """Genera resumen legible en texto plano."""
    lines = []
    lines.append("=" * 50)
    lines.append("  CUBESAT EDGEAI — REPORTE DE ANALISIS")
    lines.append("=" * 50)
    lines.append("")

    # Calibración
    lines.append(f"Calibracion: {cal_info.get('message', 'N/A')}")
    lines.append(f"  Escala: {cal_info.get('um_per_pixel', 0):.4f} um/pixel")
    lines.append("")

    # Células
    if "cells" in summary:
        c = summary["cells"]
        lines.append(f"CELULAS DETECTADAS: {c['count']}")
        lines.append(f"  Area media:       {c['area_um2_mean']:.2f} um2")
        lines.append(f"  Area std:         {c['area_um2_std']:.2f} um2")
        lines.append(f"  Perimetro medio:  {c['perimeter_um_mean']:.2f} um")
        lines.append(f"  Circularidad:     {c['circularity_mean']:.4f}")
        lines.append("")

    # Fibras
    if "fibers" in summary:
        fb = summary["fibers"]
        lines.append(f"FIBRAS DETECTADAS: {fb['count']}")
        lines.append(f"  Longitud media:   {fb['length_um_mean']:.2f} um")
        lines.append(f"  Longitud std:     {fb['length_um_std']:.2f} um")
        lines.append("")

    lines.append("=" * 50)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_results(
    output_dir: str,
    image_name: str,
    img_color: np.ndarray,
    seg_result: dict = None,
    fiber_result: dict = None,
    cell_measurements: list = None,
    fiber_measurements: list = None,
    summary: dict = None,
    cal_info: dict = None,
    cfg: dict = None,
):
    """Exporta todos los resultados de una imagen."""
    base = os.path.splitext(image_name)[0]
    exp = cfg["export"] if cfg else {}

    # Overlay
    if exp.get("save_overlays", True):
        if seg_result and seg_result.get("contours"):
            ov = draw_overlay(img_color, seg_result, cfg)
            cv2.imwrite(os.path.join(output_dir, f"{base}_overlay.png"), ov)
        if fiber_result and fiber_result.get("lines"):
            ov = draw_fiber_overlay(img_color, fiber_result)
            cv2.imwrite(os.path.join(output_dir, f"{base}_fibers_overlay.png"), ov)

    # Masks
    if exp.get("save_masks", True) and seg_result is not None:
        labels = seg_result.get("labels")
        if labels is not None:
            save_mask(labels, os.path.join(output_dir, f"{base}_mask.png"))

    # CSV
    if exp.get("save_csv", True):
        if cell_measurements:
            save_csv(cell_measurements, os.path.join(output_dir, f"{base}_cells.csv"))
        if fiber_measurements:
            save_csv(
                fiber_measurements, os.path.join(output_dir, f"{base}_fibers.csv")
            )

    # JSON
    if exp.get("save_json", True) and summary:
        save_json(
            {"calibration": cal_info, "summary": summary},
            os.path.join(output_dir, f"{base}_results.json"),
        )

    # Summary txt
    if exp.get("save_summary", True) and summary and cal_info:
        save_summary_txt(
            summary, cal_info, os.path.join(output_dir, f"{base}_summary.txt")
        )
