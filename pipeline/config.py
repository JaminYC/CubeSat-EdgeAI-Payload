"""
Carga y gestión de configuración del pipeline.
"""

import os
import yaml


_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.yaml"
)


def load_config(path: str = None) -> dict:
    """Carga config.yaml y devuelve dict."""
    path = path or _DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def get_output_dir(cfg: dict) -> str:
    """Crea y devuelve la carpeta de salida."""
    out = cfg["paths"]["output_folder"]
    os.makedirs(out, exist_ok=True)
    return out
