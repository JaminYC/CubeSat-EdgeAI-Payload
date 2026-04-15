"""
Detección y segmentación de fibras (algodón, hilos).
Usa Canny + HoughLinesP + skeletonization.
"""

import cv2
import numpy as np


def detect_fibers(img_gray: np.ndarray, cfg: dict) -> dict:
    """
    Detecta fibras usando Canny + HoughLinesP.
    Retorna dict con líneas, máscara, métricas.
    """
    params = cfg["fiber"]

    # 1. Blur suave
    blurred = cv2.GaussianBlur(img_gray, (5, 5), 1)

    # 2. Canny
    edges = cv2.Canny(blurred, params["canny_low"], params["canny_high"])

    # 3. Dilatación leve para conectar segmentos
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    # 4. HoughLinesP
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=params["hough_threshold"],
        minLineLength=params["hough_min_length"],
        maxLineGap=params["hough_max_gap"],
    )

    if lines is None:
        return {
            "lines": [],
            "mask": np.zeros_like(img_gray),
            "num_fibers": 0,
            "method": "hough",
        }

    # 5. Filtrar líneas muy cortas
    min_len = params["min_fiber_length_px"]
    filtered = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length >= min_len:
            filtered.append({
                "x1": int(x1), "y1": int(y1),
                "x2": int(x2), "y2": int(y2),
                "length_px": float(length),
                "angle_deg": float(np.degrees(np.arctan2(y2 - y1, x2 - x1))),
            })

    # 6. Máscara de fibras
    mask = np.zeros_like(img_gray)
    for f in filtered:
        cv2.line(mask, (f["x1"], f["y1"]), (f["x2"], f["y2"]), 255, 2)

    return {
        "lines": filtered,
        "mask": mask,
        "num_fibers": len(filtered),
        "method": "hough",
    }
