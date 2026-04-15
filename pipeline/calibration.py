"""
Calibración: convierte pixels a unidades reales (µm o mm).
Soporta:
  - Detección de marcas de regla (HoughLines)
  - Microesferas de diámetro conocido (contornos circulares)
  - Fallback a valor por defecto
"""

import cv2
import numpy as np


def calibrate_from_ruler(img_gray: np.ndarray, cfg: dict) -> dict:
    """
    Detecta líneas verticales repetidas en imagen de regla.
    Calcula spacing promedio en pixels → convierte a µm/pixel.
    """
    cal = cfg["calibration"]
    spacing_mm = cal["ruler_spacing_mm"]

    # Preprocesar
    blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Detectar líneas verticales
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=img_gray.shape[0] // 4,
        maxLineGap=20,
    )

    if lines is None or len(lines) < 2:
        return _fallback(cfg, "No se detectaron suficientes lineas en la regla")

    # Extraer posiciones X de las líneas verticales (ángulo ~90°)
    x_positions = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle > 70:  # casi vertical
            x_positions.append((x1 + x2) / 2)

    if len(x_positions) < 2:
        return _fallback(cfg, "No se encontraron lineas verticales")

    x_positions = sorted(set(int(round(x)) for x in x_positions))

    # Calcular spacings entre líneas consecutivas
    spacings = []
    for i in range(1, len(x_positions)):
        s = x_positions[i] - x_positions[i - 1]
        if s > 5:  # filtrar duplicados muy cercanos
            spacings.append(s)

    if not spacings:
        return _fallback(cfg, "No se pudieron calcular espaciados")

    avg_spacing_px = float(np.median(spacings))
    um_per_pixel = (spacing_mm * 1000) / avg_spacing_px

    return {
        "success": True,
        "method": "ruler",
        "um_per_pixel": um_per_pixel,
        "mm_per_pixel": um_per_pixel / 1000,
        "avg_spacing_px": avg_spacing_px,
        "num_lines": len(x_positions),
        "num_spacings": len(spacings),
        "message": f"Calibrado: {um_per_pixel:.4f} um/px ({len(spacings)} intervalos)",
    }


def calibrate_from_microspheres(img_gray: np.ndarray, cfg: dict) -> dict:
    """
    Detecta microesferas circulares y calcula escala.
    Usa HoughCircles para encontrar esferas de diámetro conocido.
    """
    cal = cfg["calibration"]
    sphere_diam_um = cal["microsphere_diameter_um"]

    blurred = cv2.GaussianBlur(img_gray, (9, 9), 2)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=20,
        param1=50,
        param2=30,
        minRadius=5,
        maxRadius=100,
    )

    if circles is None or len(circles[0]) < 1:
        return _fallback(cfg, "No se detectaron microesferas")

    radii = circles[0][:, 2]
    avg_radius_px = float(np.median(radii))
    avg_diameter_px = avg_radius_px * 2
    um_per_pixel = sphere_diam_um / avg_diameter_px

    return {
        "success": True,
        "method": "microspheres",
        "um_per_pixel": um_per_pixel,
        "mm_per_pixel": um_per_pixel / 1000,
        "avg_diameter_px": avg_diameter_px,
        "num_spheres": len(radii),
        "message": f"Calibrado: {um_per_pixel:.4f} um/px ({len(radii)} esferas)",
    }


def calibrate(img_gray: np.ndarray, cfg: dict) -> dict:
    """Ejecuta calibración según el método configurado."""
    method = cfg["calibration"]["method"]
    if method == "ruler":
        return calibrate_from_ruler(img_gray, cfg)
    elif method == "microspheres":
        return calibrate_from_microspheres(img_gray, cfg)
    else:
        return _fallback(cfg, f"Metodo desconocido: {method}")


def _fallback(cfg: dict, reason: str) -> dict:
    """Retorna calibración por defecto."""
    default = cfg["calibration"]["default_um_per_pixel"]
    return {
        "success": False,
        "method": "default",
        "um_per_pixel": default,
        "mm_per_pixel": default / 1000,
        "message": f"Fallback ({default} um/px): {reason}",
    }
