"""
Tuner interactivo para segmentacion de cebolla en grayscale.

Uso:
    python tools/tune_onion.py <imagen.png>

Atajos:
    s   guarda parametros a tools/onion_params.yaml
    r   reset a defaults
    1-4 cicla entre vistas (preproc / walls / dist / overlay)
    g   toggle grilla de stats
    q   salir

Trackbars:
    CLAHE clip          contraste local (1..10)
    Tophat ksize        realce de paredes oscuras (3..81 impar)
    Frangi sigma_max    grosor maximo de pared a detectar
    Wall thresh         umbral binario sobre el realce
    Marker min_dist     separacion minima entre seeds de watershed
    Min area px         filtro inferior
    Max area px         filtro superior
    AR max x10          aspect ratio max (× 10, asi 50 = 5.0)

Mantenelo abierto, mira los stats en la barra inferior — los rangos sanos:
    N celulas: 30-200 en un FOV tipico
    area_med: 8000-40000 um² (con 2.66 um/px)
    circ_med: 0.35-0.75
    AR_med:   2.0-5.0
"""

import cv2
import numpy as np
import sys
import os
import yaml
from pathlib import Path
from skimage.filters import frangi
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from scipy import ndimage as ndi


WINDOW = "Onion Tuner — q salir | s guardar | 1-4 vistas | g stats"
PARAMS_FILE = Path(__file__).parent / "onion_params.yaml"
UM_PER_PIXEL_DEFAULT = 2.66


# ─── Defaults ────────────────────────────────────────────────────────

DEFAULTS = {
    "clahe_clip":   30,    # /10 → 3.0
    "tophat_ksize": 25,    # impar
    "frangi_smax":  8,
    "wall_thresh":  60,
    "marker_dist":  20,
    "min_area":     500,
    "max_area":     30000,
    "ar_max_x10":   60,    # /10 → 6.0
}


# ─── Trackbar callbacks (todo recalcula en update()) ────────────────

_state = {"changed": True, "view": 4, "show_stats": True}

def _bump(_=None):
    _state["changed"] = True


# ─── Pipeline (todo grayscale) ──────────────────────────────────────

def preprocess(gray, clahe_clip):
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip / 10.0, tileGridSize=(8, 8))
    return clahe.apply(g)


def detect_walls(pp, tophat_ksize, frangi_smax):
    """Realza paredes oscuras → mapa donde valor alto = pared."""
    k = max(3, tophat_ksize | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    blackhat = cv2.morphologyEx(pp, cv2.MORPH_BLACKHAT, kernel)

    # Frangi para realzar lineas (paredes son ridges 1D)
    img_f = pp.astype(np.float32) / 255.0
    sigmas = np.linspace(1, max(2, frangi_smax), 4)
    vesselness = frangi(img_f, sigmas=sigmas, black_ridges=True)
    vesselness = (vesselness / (vesselness.max() + 1e-9) * 255).astype(np.uint8)

    walls = cv2.addWeighted(blackhat, 0.5, vesselness, 0.5, 0)
    return walls


def segment(walls, gray_pp, wall_thresh, marker_dist, min_area, max_area, ar_max):
    """Wall map → walls binarias → watershed → label map."""
    # 1. Binarizar paredes
    _, wall_bin = cv2.threshold(walls, wall_thresh, 255, cv2.THRESH_BINARY)
    wall_bin = cv2.morphologyEx(
        wall_bin, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )

    # 2. Interior = NO pared
    cells_bin = cv2.bitwise_not(wall_bin)
    cells_bin = cv2.morphologyEx(
        cells_bin, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=1,
    )

    # 3. Distance transform
    dist = cv2.distanceTransform(cells_bin, cv2.DIST_L2, 5)

    # 4. Seeds (peak local max separados por marker_dist)
    coords = peak_local_max(
        dist, min_distance=max(3, marker_dist),
        labels=cells_bin > 0,
    )
    if len(coords) == 0:
        return np.zeros_like(gray_pp, dtype=np.int32), wall_bin

    markers = np.zeros(dist.shape, dtype=np.int32)
    markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
    markers = ndi.label(markers > 0)[0]

    # 5. Watershed sobre -dist (los seeds son maximos)
    labels = watershed(-dist, markers, mask=(cells_bin > 0))

    # 6. Filtrar por area + AR
    out = np.zeros_like(labels)
    keep = 0
    for lid in range(1, labels.max() + 1):
        m = (labels == lid).astype(np.uint8)
        a = int(m.sum())
        if not (min_area <= a <= max_area):
            continue
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = cnts[0]
        if len(c) >= 5:
            _, (w, h), _ = cv2.fitEllipse(c)
            if min(w, h) > 0 and max(w, h) / min(w, h) > ar_max:
                continue
        keep += 1
        out[labels == lid] = keep

    return out, wall_bin


# ─── Stats por celula ────────────────────────────────────────────────

def compute_stats(labels, um_per_px):
    n = labels.max()
    if n == 0:
        return {"n": 0}
    areas, circs, ars = [], [], []
    for lid in range(1, n + 1):
        m = (labels == lid).astype(np.uint8)
        a = int(m.sum())
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = cnts[0]
        peri = cv2.arcLength(c, True)
        circ = (4 * np.pi * a) / (peri * peri) if peri > 0 else 0
        ar = 1.0
        if len(c) >= 5:
            _, (w, h), _ = cv2.fitEllipse(c)
            if min(w, h) > 0:
                ar = max(w, h) / min(w, h)
        areas.append(a * um_per_px ** 2)
        circs.append(circ)
        ars.append(ar)
    return {
        "n": n,
        "area_med":  np.median(areas),
        "area_mean": np.mean(areas),
        "circ_med":  np.median(circs),
        "ar_med":    np.median(ars),
        "coverage":  100.0 * (labels > 0).sum() / labels.size,
    }


# ─── Render ──────────────────────────────────────────────────────────

def render_view(view_id, gray, pp, walls, wall_bin, labels, stats):
    """view_id: 1=preproc 2=walls 3=wall_bin 4=overlay segmentacion."""
    if view_id == 1:
        out = cv2.cvtColor(pp, cv2.COLOR_GRAY2BGR)
        title = "PREPROC (CLAHE)"
    elif view_id == 2:
        out = cv2.applyColorMap(walls, cv2.COLORMAP_INFERNO)
        title = "WALL ENHANCEMENT (blackhat + frangi)"
    elif view_id == 3:
        out = cv2.cvtColor(wall_bin, cv2.COLOR_GRAY2BGR)
        title = "WALLS BINARIZADAS"
    else:
        base = cv2.cvtColor(pp, cv2.COLOR_GRAY2BGR)
        if labels.max() > 0:
            n = int(labels.max())
            color_lut = np.zeros((n + 1, 3), dtype=np.uint8)
            for i in range(1, n + 1):
                hue = int(i * 180 / max(1, n)) % 180
                hsv = np.array([[[hue, 200, 230]]], dtype=np.uint8)
                color_lut[i] = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
            mask_bool = labels > 0
            colored = base.copy()
            colored[mask_bool] = color_lut[labels[mask_bool]]
            out = cv2.addWeighted(base, 0.55, colored, 0.45, 0)
            for lid in range(1, min(n + 1, 800)):
                m = (labels == lid).astype(np.uint8)
                cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(out, cs, -1, (255, 255, 255), 1)
        else:
            out = base
        title = f"SEGMENTACION  N={stats['n']}"
    cv2.putText(out, title, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, (255, 255, 0), 2, cv2.LINE_AA)
    return out


def render_stats_bar(stats, w, sane):
    bar = np.zeros((110, w, 3), dtype=np.uint8) + 30
    if stats["n"] == 0:
        cv2.putText(bar, "Sin celulas detectadas — bajar wall_thresh o subir clahe_clip",
                    (12, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        return bar
    line1 = (f"N = {stats['n']:3d}     "
             f"area_med = {stats['area_med']/1000:.1f} k um²     "
             f"area_mean = {stats['area_mean']/1000:.1f} k     "
             f"circ_med = {stats['circ_med']:.2f}     "
             f"AR_med = {stats['ar_med']:.2f}     "
             f"cobertura = {stats['coverage']:.0f}%")
    cv2.putText(bar, line1, (12, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.62, (240, 240, 240), 1, cv2.LINE_AA)

    flags = []
    flags.append(("area_med", "OK" if 8000 <= stats["area_med"] <= 40000 else "FUERA",
                  (60, 220, 60) if 8000 <= stats["area_med"] <= 40000 else (60, 60, 220)))
    flags.append(("circ_med", "OK" if 0.35 <= stats["circ_med"] <= 0.75 else "FUERA",
                  (60, 220, 60) if 0.35 <= stats["circ_med"] <= 0.75 else (60, 60, 220)))
    flags.append(("AR_med", "OK" if 2.0 <= stats["ar_med"] <= 5.0 else "FUERA",
                  (60, 220, 60) if 2.0 <= stats["ar_med"] <= 5.0 else (60, 60, 220)))
    flags.append(("cobertura", "OK" if 60 <= stats["coverage"] <= 90 else "FUERA",
                  (60, 220, 60) if 60 <= stats["coverage"] <= 90 else (60, 60, 220)))

    x = 12
    cv2.putText(bar, "Sanity:", (x, 78), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (180, 180, 180), 1, cv2.LINE_AA)
    x += 75
    for name, val, color in flags:
        txt = f"{name}={val}"
        cv2.putText(bar, txt, (x, 78), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, color, 1, cv2.LINE_AA)
        x += 12 * len(txt) + 10
    return bar


# ─── Main loop ───────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python tools/tune_onion.py <imagen>")
        # Buscar una de prueba
        defaults = [
            "Imagenes/Variados/MicroscopiaPruebaCLAHE.png",
            "Imagenes/Variados/Prueba.jpg",
            "Imagenes/Variados/Prueba2.png",
        ]
        for d in defaults:
            if os.path.exists(d):
                print(f"   Usando default: {d}")
                img_path = d
                break
        else:
            return
    else:
        img_path = sys.argv[1]

    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"No pude cargar {img_path}")
        return

    # Resize para mantener responsivo (max 1400 px)
    H, W = img.shape
    max_dim = 1400
    if max(H, W) > max_dim:
        scale = max_dim / max(H, W)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        print(f"  Imagen redimensionada {W}×{H} → {img.shape[1]}×{img.shape[0]} (escala {scale:.2f})")

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, min(1600, img.shape[1]), min(1000, img.shape[0] + 280))

    cv2.createTrackbar("CLAHE clip x10",  WINDOW, DEFAULTS["clahe_clip"],   100, _bump)
    cv2.createTrackbar("Tophat ksize",    WINDOW, DEFAULTS["tophat_ksize"],  81, _bump)
    cv2.createTrackbar("Frangi smax",     WINDOW, DEFAULTS["frangi_smax"],   30, _bump)
    cv2.createTrackbar("Wall thresh",     WINDOW, DEFAULTS["wall_thresh"],  255, _bump)
    cv2.createTrackbar("Marker dist",     WINDOW, DEFAULTS["marker_dist"],   80, _bump)
    cv2.createTrackbar("Min area px",     WINDOW, DEFAULTS["min_area"],   10000, _bump)
    cv2.createTrackbar("Max area px",     WINDOW, DEFAULTS["max_area"],  100000, _bump)
    cv2.createTrackbar("AR max x10",      WINDOW, DEFAULTS["ar_max_x10"],  150, _bump)

    pp = walls = wall_bin = labels = None
    stats = {"n": 0}

    print("\nTeclas: 1/2/3/4 vistas | s guardar params | r reset | g stats | q salir\n")

    while True:
        if _state["changed"]:
            params = {
                "clahe_clip":   max(1, cv2.getTrackbarPos("CLAHE clip x10", WINDOW)),
                "tophat_ksize": max(3, cv2.getTrackbarPos("Tophat ksize", WINDOW)),
                "frangi_smax":  max(2, cv2.getTrackbarPos("Frangi smax", WINDOW)),
                "wall_thresh":  cv2.getTrackbarPos("Wall thresh", WINDOW),
                "marker_dist":  max(3, cv2.getTrackbarPos("Marker dist", WINDOW)),
                "min_area":     cv2.getTrackbarPos("Min area px", WINDOW),
                "max_area":     max(100, cv2.getTrackbarPos("Max area px", WINDOW)),
                "ar_max_x10":   max(10, cv2.getTrackbarPos("AR max x10", WINDOW)),
            }
            pp = preprocess(img, params["clahe_clip"])
            walls = detect_walls(pp, params["tophat_ksize"], params["frangi_smax"])
            labels, wall_bin = segment(
                walls, pp,
                params["wall_thresh"], params["marker_dist"],
                params["min_area"], params["max_area"],
                params["ar_max_x10"] / 10.0,
            )
            stats = compute_stats(labels, UM_PER_PIXEL_DEFAULT)
            _state["changed"] = False
            _state["last_params"] = params

        view = render_view(_state["view"], img, pp, walls, wall_bin, labels, stats)
        if _state["show_stats"]:
            bar = render_stats_bar(stats, view.shape[1], None)
            view = np.vstack([view, bar])
        cv2.imshow(WINDOW, view)

        k = cv2.waitKey(30) & 0xFF
        if k == ord("q") or k == 27:
            break
        elif k == ord("s"):
            with open(PARAMS_FILE, "w") as f:
                yaml.safe_dump({
                    "image": str(img_path),
                    "params": _state["last_params"],
                    "stats":  {k: float(v) for k, v in stats.items()},
                }, f, default_flow_style=False)
            print(f"  Guardado: {PARAMS_FILE}")
        elif k == ord("r"):
            for name, val in [
                ("CLAHE clip x10", DEFAULTS["clahe_clip"]),
                ("Tophat ksize",   DEFAULTS["tophat_ksize"]),
                ("Frangi smax",    DEFAULTS["frangi_smax"]),
                ("Wall thresh",    DEFAULTS["wall_thresh"]),
                ("Marker dist",    DEFAULTS["marker_dist"]),
                ("Min area px",    DEFAULTS["min_area"]),
                ("Max area px",    DEFAULTS["max_area"]),
                ("AR max x10",     DEFAULTS["ar_max_x10"]),
            ]:
                cv2.setTrackbarPos(name, WINDOW, val)
            _bump()
        elif k in (ord("1"), ord("2"), ord("3"), ord("4")):
            _state["view"] = int(chr(k))
        elif k == ord("g"):
            _state["show_stats"] = not _state["show_stats"]

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
