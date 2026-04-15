"""
Segmentación de células de piel de cebolla.

Soporta 3 backends (graceful degradation):
  1. "opencv"   — baseline clásico (siempre disponible)
  2. "cellpose" — modelo preentrenado o fine-tuned (requiere cellpose)
  3. "onnx"     — modelo exportado para RPi (requiere onnxruntime)
"""

import cv2
import numpy as np
from skimage import measure


# ─── Backend OpenCV (Fase 1 — siempre disponible) ─────────────────────────


def segment_opencv(img_gray: np.ndarray, cfg: dict, mask: np.ndarray = None) -> dict:
    """
    Segmentación clásica: Canny + morfología + watershed.
    Retorna dict con labels, contours, num_cells.
    """
    params = cfg["onion"]["opencv"]

    # 1. Blur
    blurred = cv2.GaussianBlur(
        img_gray, (params["blur_kernel"], params["blur_kernel"]), 0
    )

    # 2. Canny para bordes
    edges = cv2.Canny(blurred, 30, 100)

    # 3. Cierre morfológico para conectar bordes rotos
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (params["morph_kernel"], params["morph_kernel"])
    )
    closed = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE, kernel, iterations=params["morph_iterations"]
    )

    # 4. Llenar regiones cerradas
    # Invertir: bordes blancos → fondo blanco, células negras
    inverted = cv2.bitwise_not(closed)

    # 5. Encontrar contornos
    contours_raw, _ = cv2.findContours(
        inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # 6. Filtrar por área
    min_area = params["min_cell_area_px"]
    max_area = params["max_cell_area_px"]
    contours = [c for c in contours_raw if min_area < cv2.contourArea(c) < max_area]

    # 7. Crear label map
    labels = np.zeros(img_gray.shape, dtype=np.int32)
    for i, c in enumerate(contours, start=1):
        cv2.drawContours(labels, [c], -1, i, cv2.FILLED)

    # Aplicar máscara de viñeteo si existe
    if mask is not None:
        labels[mask == 0] = 0

    return {
        "labels": labels,
        "contours": contours,
        "num_cells": len(contours),
        "method": "opencv",
    }


# ─── Backend Cellpose (Fase 2-3) ──────────────────────────────────────────


def segment_cellpose(img_gray: np.ndarray, cfg: dict) -> dict:
    """
    Segmentación con Cellpose (cyto3 o fine-tuned).
    Requiere: pip install cellpose
    """
    try:
        from cellpose import models
    except ImportError:
        print("[WARN] Cellpose no instalado — fallback a OpenCV")
        return segment_opencv(img_gray, cfg)

    params = cfg["onion"]["cellpose"]
    model = models.Cellpose(model_type=params["model_type"], gpu=cfg["hardware"]["use_gpu"])

    masks, flows, styles, diams = model.eval(
        img_gray,
        diameter=params["diameter"],
        flow_threshold=params["flow_threshold"],
        cellprob_threshold=params["cellprob_threshold"],
        channels=[0, 0],
    )

    # Extraer contornos de las masks
    contours = []
    for region in measure.regionprops(masks):
        # Crear contorno desde la máscara de cada célula
        cell_mask = (masks == region.label).astype(np.uint8)
        cnts, _ = cv2.findContours(cell_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            contours.append(cnts[0])

    return {
        "labels": masks,
        "contours": contours,
        "num_cells": masks.max(),
        "method": "cellpose",
        "diameter_detected": float(diams),
    }


# ─── Backend ONNX (Fase 4 — RPi deploy) ──────────────────────────────────


def segment_onnx(img_gray: np.ndarray, cfg: dict) -> dict:
    """
    Inferencia con modelo ONNX exportado.
    Requiere: pip install onnxruntime
    """
    try:
        import onnxruntime as ort
    except ImportError:
        print("[WARN] onnxruntime no instalado — fallback a OpenCV")
        return segment_opencv(img_gray, cfg)

    model_path = cfg["onion"]["onnx"]["model_path"]
    try:
        session = ort.InferenceSession(model_path)
    except Exception as e:
        print(f"[WARN] No se pudo cargar ONNX model: {e} — fallback a OpenCV")
        return segment_opencv(img_gray, cfg)

    # Preparar input (normalizar, agregar batch dim)
    img_input = img_gray.astype(np.float32) / 255.0
    img_input = np.expand_dims(np.expand_dims(img_input, 0), 0)

    input_name = session.get_inputs()[0].name
    result = session.run(None, {input_name: img_input})
    masks = result[0].squeeze().astype(np.int32)

    contours = []
    for region in measure.regionprops(masks):
        cell_mask = (masks == region.label).astype(np.uint8)
        cnts, _ = cv2.findContours(cell_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            contours.append(cnts[0])

    return {
        "labels": masks,
        "contours": contours,
        "num_cells": masks.max(),
        "method": "onnx",
    }


# ─── Dispatcher ───────────────────────────────────────────────────────────


def segment_onion(img_gray: np.ndarray, cfg: dict, mask: np.ndarray = None) -> dict:
    """Ejecuta la segmentación según el método configurado, con fallback."""
    method = cfg["onion"]["method"]

    if method == "cellpose":
        return segment_cellpose(img_gray, cfg)
    elif method == "onnx":
        return segment_onnx(img_gray, cfg)
    else:
        return segment_opencv(img_gray, cfg, mask)
