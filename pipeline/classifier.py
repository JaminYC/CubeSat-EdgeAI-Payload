"""
Clasificador de tipo de imagen por nombre de archivo.
MVP: usa keywords en el nombre. Futuro: clasificador visual ligero.
"""

import os


def classify_image(filepath: str, cfg: dict) -> str:
    """
    Clasifica una imagen como 'ruler', 'onion', 'fiber' o 'unknown'.
    Busca keywords en el nombre del archivo (case-insensitive).
    """
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
    return "unknown"


def scan_folder(folder: str, cfg: dict) -> dict:
    """
    Escanea una carpeta y clasifica todas las imágenes.
    Retorna: {"ruler": [...], "onion": [...], "fiber": [...], "unknown": [...]}
    """
    extensions = set(cfg["classifier"]["extensions"])
    result = {"ruler": [], "onion": [], "fiber": [], "unknown": []}

    for fname in sorted(os.listdir(folder)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in extensions:
            continue
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        img_type = classify_image(fpath, cfg)
        result[img_type].append(fpath)

    return result
