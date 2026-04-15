"""
Preprocesamiento de imágenes de microscopía.
Diseñado para ser ligero (OpenCV puro) y funcionar en RPi 5.
"""

import cv2
import numpy as np


def load_image(filepath: str) -> tuple:
    """
    Carga imagen en color y grayscale.
    Retorna (img_color_bgr, img_gray).
    """
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"No se pudo cargar: {filepath}")

    # Si es 16-bit, normalizar a 8-bit
    if img.dtype == np.uint16:
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    if len(img.shape) == 2:
        gray = img
        color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        color = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    else:
        color = img
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return color, gray


def remove_vignette(img_gray: np.ndarray) -> tuple:
    """
    Detecta y corrige la zona negra de viñeteo del microscopio.
    Retorna (imagen_corregida, mascara_valida).
    """
    _, mask = cv2.threshold(img_gray, 10, 255, cv2.THRESH_BINARY)
    valid_pixels = img_gray[mask > 0]
    if valid_pixels.size == 0:
        return img_gray, mask
    median_val = int(np.median(valid_pixels))
    corrected = img_gray.copy()
    corrected[mask == 0] = median_val
    return corrected, mask


def apply_clahe(img_gray: np.ndarray, cfg: dict) -> np.ndarray:
    """Aplica CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    pre = cfg["preprocess"]
    clip = pre["clahe_clip_limit"]
    grid = pre["clahe_grid_size"]
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    return clahe.apply(img_gray)


def denoise(img_gray: np.ndarray, cfg: dict) -> np.ndarray:
    """Reducción de ruido preservando bordes."""
    strength = cfg["preprocess"]["denoise_strength"]
    return cv2.fastNlMeansDenoising(img_gray, None, h=strength)


def preprocess(img_gray: np.ndarray, cfg: dict) -> tuple:
    """
    Pipeline completo de preprocesamiento.
    Retorna (imagen_preprocesada, mascara_valida).
    """
    pre = cfg["preprocess"]
    mask = np.ones(img_gray.shape, dtype=np.uint8) * 255

    if pre["correct_vignette"]:
        img_gray, mask = remove_vignette(img_gray)

    if pre["apply_clahe"]:
        img_gray = apply_clahe(img_gray, cfg)

    if pre["denoise"]:
        img_gray = denoise(img_gray, cfg)

    return img_gray, mask
