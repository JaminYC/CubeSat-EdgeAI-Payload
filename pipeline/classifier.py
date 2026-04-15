"""
Clasificador de tipo de imagen.

Prioridad de clasificación:
  1. Por subcarpeta: ruler/, onion/, fiber/
  2. Por nombre de archivo: keywords configurables
  3. Fallback: "unknown"
"""

import os


# Nombres de subcarpeta reconocidos para cada tipo
_FOLDER_ALIASES = {
    "ruler":  {"ruler", "regla", "calibration", "calibracion", "scale"},
    "onion":  {"onion", "cebolla", "cells", "celulas", "epidermis", "skin", "piel"},
    "fiber":  {"fiber", "fibra", "cotton", "algodon", "thread", "hilo"},
}


def _classify_by_folder(filepath: str) -> str:
    """Clasifica por nombre de la carpeta padre."""
    parent = os.path.basename(os.path.dirname(filepath)).lower()
    for img_type, aliases in _FOLDER_ALIASES.items():
        if parent in aliases:
            return img_type
    return None


def _classify_by_name(filepath: str, cfg: dict) -> str:
    """Clasifica por keywords en el nombre del archivo."""
    name = os.path.basename(filepath).lower()
    cl = cfg["classifier"]

    for kw in cl["ruler_keywords"]:
        if kw in name:
            return "ruler"
    for kw in cl["onion_keywords"]:
        if kw in name:
            return "onion"
    for kw in cl["fiber_keywords"]:
        if kw in name:
            return "fiber"
    return None


def classify_image(filepath: str, cfg: dict) -> str:
    """
    Clasifica una imagen como 'ruler', 'onion', 'fiber' o 'unknown'.
    Prioridad: subcarpeta > nombre de archivo > unknown.
    """
    return (
        _classify_by_folder(filepath)
        or _classify_by_name(filepath, cfg)
        or "unknown"
    )


def _collect_images(folder: str, extensions: set) -> list:
    """Recolecta imágenes recursivamente (1 nivel de subcarpetas)."""
    images = []

    for entry in sorted(os.listdir(folder)):
        full = os.path.join(folder, entry)

        if os.path.isfile(full):
            ext = os.path.splitext(entry)[1].lower()
            if ext in extensions:
                images.append(full)

        elif os.path.isdir(full):
            # Solo 1 nivel de profundidad
            for fname in sorted(os.listdir(full)):
                fpath = os.path.join(full, fname)
                if os.path.isfile(fpath):
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in extensions:
                        images.append(fpath)

    return images


def scan_folder(folder: str, cfg: dict) -> dict:
    """
    Escanea una carpeta (y subcarpetas 1 nivel) y clasifica imágenes.

    Estructura esperada:
        carpeta/
        ├── ruler/        ← calibración
        │   └── regla.png
        ├── onion/        ← cebolla
        │   └── muestra.tiff
        ├── fiber/        ← fibra (opcional)
        │   └── algodon.png
        └── otra_imagen.png  ← clasifica por nombre o unknown

    Retorna: {"ruler": [...], "onion": [...], "fiber": [...], "unknown": [...]}
    """
    extensions = set(cfg["classifier"]["extensions"])
    result = {"ruler": [], "onion": [], "fiber": [], "unknown": []}

    images = _collect_images(folder, extensions)
    for fpath in images:
        img_type = classify_image(fpath, cfg)
        result[img_type].append(fpath)

    return result
