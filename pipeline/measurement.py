"""
Medición dimensional: convierte resultados de segmentación
de pixels a unidades reales (µm, mm).
"""

import cv2
import numpy as np


def measure_cells(seg_result: dict, um_per_pixel: float) -> list:
    """
    Calcula métricas reales para cada célula segmentada.
    Retorna lista de dicts con métricas por célula.
    """
    cells = []
    contours = seg_result.get("contours", [])

    for i, cnt in enumerate(contours):
        area_px = cv2.contourArea(cnt)
        perimeter_px = cv2.arcLength(cnt, closed=True)

        # Escala: area escala al cuadrado, perimetro lineal
        area_um2 = area_px * (um_per_pixel ** 2)
        perimeter_um = perimeter_px * um_per_pixel

        # Circularidad: 4π × area / perimeter²
        circularity = 0.0
        if perimeter_px > 0:
            circularity = (4 * np.pi * area_px) / (perimeter_px ** 2)

        # Aspect ratio del bounding rect rotado
        aspect_ratio = 1.0
        if len(cnt) >= 5:
            _, (w, h), _ = cv2.fitEllipse(cnt)
            if min(w, h) > 0:
                aspect_ratio = max(w, h) / min(w, h)

        # Solidez: area / convex hull area
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        solidity = area_px / hull_area if hull_area > 0 else 0

        # Centroide
        M = cv2.moments(cnt)
        cx = int(M["m10"] / M["m00"]) if M["m00"] > 0 else 0
        cy = int(M["m01"] / M["m00"]) if M["m00"] > 0 else 0

        cells.append({
            "id": i + 1,
            "centroid_x": cx,
            "centroid_y": cy,
            "area_px": round(area_px, 1),
            "area_um2": round(area_um2, 2),
            "perimeter_px": round(perimeter_px, 1),
            "perimeter_um": round(perimeter_um, 2),
            "circularity": round(circularity, 4),
            "aspect_ratio": round(aspect_ratio, 3),
            "solidity": round(solidity, 4),
        })

    return cells


def measure_fibers(fiber_result: dict, um_per_pixel: float) -> list:
    """
    Convierte mediciones de fibras de pixels a µm.
    """
    fibers = []
    for i, line in enumerate(fiber_result.get("lines", [])):
        fibers.append({
            "id": i + 1,
            "x1": line["x1"],
            "y1": line["y1"],
            "x2": line["x2"],
            "y2": line["y2"],
            "length_px": round(line["length_px"], 1),
            "length_um": round(line["length_px"] * um_per_pixel, 2),
            "angle_deg": round(line["angle_deg"], 2),
        })
    return fibers


def compute_summary(cells: list = None, fibers: list = None) -> dict:
    """Genera resumen estadístico."""
    summary = {}

    if cells:
        areas = [c["area_um2"] for c in cells]
        perimeters = [c["perimeter_um"] for c in cells]
        circularities = [c["circularity"] for c in cells]
        summary["cells"] = {
            "count": len(cells),
            "area_um2_mean": round(float(np.mean(areas)), 2),
            "area_um2_std": round(float(np.std(areas)), 2),
            "area_um2_min": round(float(np.min(areas)), 2),
            "area_um2_max": round(float(np.max(areas)), 2),
            "perimeter_um_mean": round(float(np.mean(perimeters)), 2),
            "circularity_mean": round(float(np.mean(circularities)), 4),
        }

    if fibers:
        lengths = [f["length_um"] for f in fibers]
        summary["fibers"] = {
            "count": len(fibers),
            "length_um_mean": round(float(np.mean(lengths)), 2),
            "length_um_std": round(float(np.std(lengths)), 2),
            "length_um_min": round(float(np.min(lengths)), 2),
            "length_um_max": round(float(np.max(lengths)), 2),
        }

    return summary
