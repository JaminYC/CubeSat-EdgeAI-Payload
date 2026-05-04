"""
Generador de patrones de iluminacion para OLED SSD1351 (128x128 RGB).

Cada patron define como ilumina la muestra → modalidad de microscopia distinta.

Uso:
    python tools/aperture_patterns.py --gallery
        Muestra todos los patrones lado a lado.

    python tools/aperture_patterns.py --pattern bf --save out/bf.png
    python tools/aperture_patterns.py --pattern df --inner 30 --outer 55 --save out/df.png
    python tools/aperture_patterns.py --pattern dpc --direction left --save out/dpc_L.png
    python tools/aperture_patterns.py --pattern fpm --grid 5 --idx 12 --save out/fpm_12.png
    python tools/aperture_patterns.py --pattern stripe --orientation h --period 8 --save out/stripe_h.png
    python tools/aperture_patterns.py --pattern square --side 40 --save out/square.png
    python tools/aperture_patterns.py --pattern point --x 64 --y 32 --save out/point.png

    # Generar tanda FPM 5x5 (25 patrones para tu pipeline)
    python tools/aperture_patterns.py --batch fpm5 --outdir out/fpm5/

    # Informacion optica de un patron (NA, angulo)
    python tools/aperture_patterns.py --pattern df --inner 40 --outer 60 --info
"""

import argparse
import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# ── Geometria del setup (de tu config.yaml) ──────────────────────────
OLED_SIZE = 128
DOT_PITCH_MM = 0.17
OLED_DISTANCE_MM = 15.0


# ── Generadores de patrones ──────────────────────────────────────────

def pattern_bf(size=OLED_SIZE, radius=None) -> np.ndarray:
    """Bright field: disco central. radius=None → todo el OLED encendido."""
    img = np.zeros((size, size), dtype=np.uint8)
    cy, cx = size // 2, size // 2
    yy, xx = np.indices((size, size))
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    r = radius if radius is not None else size // 2
    img[r2 <= r * r] = 255
    return img


def pattern_df(size=OLED_SIZE, inner=30, outer=55) -> np.ndarray:
    """Dark field: anillo. Solo angulos oblicuos."""
    img = np.zeros((size, size), dtype=np.uint8)
    cy, cx = size // 2, size // 2
    yy, xx = np.indices((size, size))
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    img[(r2 >= inner * inner) & (r2 <= outer * outer)] = 255
    return img


def pattern_dpc(size=OLED_SIZE, radius=None, direction="left") -> np.ndarray:
    """
    Differential Phase Contrast: medio disco.
    direction in {left, right, top, bottom}.
    Capturas DPC se restan: I_L - I_R revela gradiente de fase horizontal.
    """
    img = np.zeros((size, size), dtype=np.uint8)
    cy, cx = size // 2, size // 2
    yy, xx = np.indices((size, size))
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    r = radius if radius is not None else size // 2 - 5
    disc = r2 <= r * r

    if direction == "left":
        half = xx < cx
    elif direction == "right":
        half = xx >= cx
    elif direction == "top":
        half = yy < cy
    elif direction == "bottom":
        half = yy >= cy
    else:
        raise ValueError(f"direction debe ser left/right/top/bottom, no {direction}")
    img[disc & half] = 255
    return img


def pattern_fpm(size=OLED_SIZE, grid=5, idx=None, ix=None, iy=None) -> np.ndarray:
    """
    FPM: un solo LED encendido en posicion (ix, iy) de una grilla NxN.
    idx puede pasarse en lugar de (ix, iy): idx = iy * grid + ix.
    Patron usado por tu cubesat/capture.py.
    """
    img = np.zeros((size, size), dtype=np.uint8)
    if idx is not None:
        ix = idx % grid
        iy = idx // grid
    if ix is None or iy is None:
        ix = grid // 2
        iy = grid // 2
    # Posiciones equiespaciadas en el OLED
    step = size // (grid + 1)
    px = (ix + 1) * step
    py = (iy + 1) * step
    # Encender un cuadradito 3x3 (1 pixel solo no se ve bien)
    spot = 2
    img[max(0, py - spot):py + spot + 1, max(0, px - spot):px + spot + 1] = 255
    return img


def pattern_stripe(size=OLED_SIZE, orientation="h", period=8, phase=0) -> np.ndarray:
    """
    Patron de rayas (Structured Illumination Microscopy).
    orientation: h (horizontales), v (verticales), d (diagonales).
    period: pixeles entre rayas.
    phase: 0..period-1, desplazamiento.
    """
    img = np.zeros((size, size), dtype=np.uint8)
    yy, xx = np.indices((size, size))
    if orientation == "h":
        coord = yy
    elif orientation == "v":
        coord = xx
    elif orientation == "d":
        coord = (xx + yy) // 2
    else:
        raise ValueError(f"orientation debe ser h/v/d, no {orientation}")
    img[(coord + phase) % period < period // 2] = 255
    return img


def pattern_square(size=OLED_SIZE, side=40) -> np.ndarray:
    """Cuadrado central. Util para tests de calibracion."""
    img = np.zeros((size, size), dtype=np.uint8)
    cy, cx = size // 2, size // 2
    h = side // 2
    img[cy - h:cy + h, cx - h:cx + h] = 255
    return img


def pattern_point(size=OLED_SIZE, x=None, y=None, spot=2) -> np.ndarray:
    """Un solo punto en (x, y). Util para barridos arbitrarios."""
    img = np.zeros((size, size), dtype=np.uint8)
    if x is None:
        x = size // 2
    if y is None:
        y = size // 2
    img[max(0, y - spot):y + spot + 1, max(0, x - spot):x + spot + 1] = 255
    return img


def pattern_quadrant(size=OLED_SIZE, quad="tl") -> np.ndarray:
    """Cuadrante: tl=top-left, tr=top-right, bl, br. Una variante de DPC."""
    img = np.zeros((size, size), dtype=np.uint8)
    h = size // 2
    if quad == "tl": img[:h, :h] = 255
    elif quad == "tr": img[:h, h:] = 255
    elif quad == "bl": img[h:, :h] = 255
    elif quad == "br": img[h:, h:] = 255
    else: raise ValueError(f"quad debe ser tl/tr/bl/br, no {quad}")
    return img


def pattern_cross(size=OLED_SIZE, thickness=8) -> np.ndarray:
    """Cruz: una linea horizontal + una vertical."""
    img = np.zeros((size, size), dtype=np.uint8)
    c = size // 2
    t = thickness // 2
    img[c - t:c + t + 1, :] = 255
    img[:, c - t:c + t + 1] = 255
    return img


# ── Calculo de parametros opticos ────────────────────────────────────

def optical_info(pattern: np.ndarray) -> dict:
    """
    Calcula angulo max y NA equivalente del patron.
    Asume distancia OLED-sensor de OLED_DISTANCE_MM.
    """
    size = pattern.shape[0]
    cy, cx = size // 2, size // 2
    # Pixeles encendidos
    on = pattern > 0
    if not on.any():
        return {"n_lit": 0}
    yy, xx = np.indices(pattern.shape)
    dx = (xx[on] - cx) * DOT_PITCH_MM
    dy = (yy[on] - cy) * DOT_PITCH_MM
    r = np.sqrt(dx ** 2 + dy ** 2)
    theta = np.arctan2(r, OLED_DISTANCE_MM)  # rad
    return {
        "n_lit":         int(on.sum()),
        "fill_factor":   float(on.mean()),
        "r_min_mm":      float(r.min()),
        "r_max_mm":      float(r.max()),
        "r_mean_mm":     float(r.mean()),
        "theta_min_deg": float(np.degrees(theta.min())),
        "theta_max_deg": float(np.degrees(theta.max())),
        "NA_min":        float(np.sin(theta.min())),
        "NA_max":        float(np.sin(theta.max())),
        "NA_mean":       float(np.sin(theta.mean())),
    }


def print_info(name: str, pattern: np.ndarray):
    info = optical_info(pattern)
    print(f"\n=== {name} ===")
    if info["n_lit"] == 0:
        print("  Sin pixeles encendidos.")
        return
    print(f"  Pixeles encendidos: {info['n_lit']} / {pattern.size}  ({100*info['fill_factor']:.1f}%)")
    print(f"  Distancia al centro OLED: {info['r_min_mm']:.2f} - {info['r_max_mm']:.2f} mm  (media {info['r_mean_mm']:.2f})")
    print(f"  Angulo de incidencia:     {info['theta_min_deg']:.1f}° - {info['theta_max_deg']:.1f}°")
    print(f"  NA equivalente:           {info['NA_min']:.3f} - {info['NA_max']:.3f}  (media {info['NA_mean']:.3f})")
    # Resolucion teorica (Abbe) para luz visible 550 nm
    if info["NA_max"] > 0:
        d_abbe_um = 0.55 / (2 * info["NA_max"])
        print(f"  Resolucion (Abbe, 550nm): {d_abbe_um*1000:.0f} nm = {d_abbe_um:.2f} um")


# ── Galeria comparativa ──────────────────────────────────────────────

def make_gallery(out_path: str = None):
    patterns = {
        "Bright Field": pattern_bf(radius=55),
        "Dark Field": pattern_df(inner=35, outer=55),
        "DPC left": pattern_dpc(direction="left"),
        "DPC right": pattern_dpc(direction="right"),
        "DPC top": pattern_dpc(direction="top"),
        "DPC bottom": pattern_dpc(direction="bottom"),
        "FPM (1,1) de 5x5": pattern_fpm(grid=5, ix=1, iy=1),
        "FPM (2,2) centro": pattern_fpm(grid=5, ix=2, iy=2),
        "FPM (4,4) esquina": pattern_fpm(grid=5, ix=4, iy=4),
        "Stripe horizontal": pattern_stripe(orientation="h", period=8),
        "Stripe vertical": pattern_stripe(orientation="v", period=8),
        "Stripe diagonal": pattern_stripe(orientation="d", period=8),
        "Square central": pattern_square(side=40),
        "Cross": pattern_cross(thickness=6),
        "Quadrant TL": pattern_quadrant("tl"),
        "Point off-axis": pattern_point(x=96, y=32),
    }
    n = len(patterns)
    cols = 4
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 3.5 * rows),
                              facecolor="white")
    axes = axes.flatten()
    for i, (name, p) in enumerate(patterns.items()):
        ax = axes[i]
        ax.imshow(p, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        info = optical_info(p)
        if info["n_lit"] > 0:
            sub = (f"NA = {info['NA_min']:.2f}-{info['NA_max']:.2f}   "
                   f"theta_max = {info['theta_max_deg']:.0f}°")
        else:
            sub = ""
        ax.set_title(name, fontsize=10, fontweight="bold")
        ax.set_xlabel(sub, fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
        # Cruz central como referencia
        c = OLED_SIZE // 2
        ax.axhline(c, color="cyan", linewidth=0.4, alpha=0.5)
        ax.axvline(c, color="cyan", linewidth=0.4, alpha=0.5)
    for j in range(i + 1, len(axes)):
        axes[j].axis("off")
    fig.suptitle(
        f"Patrones de iluminacion para OLED 128x128  "
        f"(distancia {OLED_DISTANCE_MM} mm, dot pitch {DOT_PITCH_MM} mm)",
        fontsize=12, fontweight="bold"
    )
    plt.tight_layout()
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        plt.savefig(out_path, dpi=130, bbox_inches="tight")
        print(f"  Galeria guardada: {out_path}")
    plt.show()


# ── Batches utiles ───────────────────────────────────────────────────

def batch_fpm(grid: int, outdir: str):
    """Genera grid x grid patrones FPM para barrido completo."""
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for iy in range(grid):
        for ix in range(grid):
            p = pattern_fpm(grid=grid, ix=ix, iy=iy)
            path = os.path.join(outdir, f"fpm_{iy:02d}_{ix:02d}.png")
            Image.fromarray(p).save(path)
            n += 1
    print(f"  {n} patrones FPM guardados en {outdir}/")


def batch_dpc(outdir: str):
    """4 patrones DPC (L, R, T, B) — para reconstruir fase."""
    os.makedirs(outdir, exist_ok=True)
    for d in ("left", "right", "top", "bottom"):
        p = pattern_dpc(direction=d)
        Image.fromarray(p).save(os.path.join(outdir, f"dpc_{d}.png"))
    print(f"  4 patrones DPC guardados en {outdir}/")


def batch_sim(outdir: str, period: int = 8, n_phases: int = 3):
    """Set SIM: 3 orientaciones x N fases por orientacion."""
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for orient in ("h", "v", "d"):
        for ph in range(n_phases):
            p = pattern_stripe(orientation=orient, period=period,
                               phase=int(ph * period / n_phases))
            Image.fromarray(p).save(
                os.path.join(outdir, f"sim_{orient}_p{ph}.png")
            )
            n += 1
    print(f"  {n} patrones SIM guardados en {outdir}/")


# ── Main / CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pattern", choices=[
        "bf", "df", "dpc", "fpm", "stripe", "square", "point", "cross", "quadrant"
    ], help="tipo de patron")
    parser.add_argument("--save", help="ruta PNG donde guardar")
    parser.add_argument("--gallery", action="store_true",
                        help="mostrar todos los patrones lado a lado")
    parser.add_argument("--info", action="store_true",
                        help="imprimir info optica (NA, angulo)")
    parser.add_argument("--batch", choices=["fpm5", "fpm9", "dpc", "sim"],
                        help="generar set completo")
    parser.add_argument("--outdir", default="out/", help="directorio de salida para batch")
    # Params especificos
    parser.add_argument("--radius", type=int, help="radio (BF, DPC)")
    parser.add_argument("--inner", type=int, default=30, help="radio interno DF")
    parser.add_argument("--outer", type=int, default=55, help="radio externo DF")
    parser.add_argument("--direction", default="left",
                        choices=["left", "right", "top", "bottom"])
    parser.add_argument("--grid", type=int, default=5, help="grilla FPM NxN")
    parser.add_argument("--idx", type=int, help="indice plano FPM")
    parser.add_argument("--ix", type=int, help="columna FPM")
    parser.add_argument("--iy", type=int, help="fila FPM")
    parser.add_argument("--orientation", default="h", choices=["h", "v", "d"])
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--phase", type=int, default=0)
    parser.add_argument("--side", type=int, default=40, help="lado del cuadrado")
    parser.add_argument("--thickness", type=int, default=8, help="grosor cruz")
    parser.add_argument("--x", type=int, help="x del punto")
    parser.add_argument("--y", type=int, help="y del punto")
    parser.add_argument("--quad", default="tl", choices=["tl", "tr", "bl", "br"])

    args = parser.parse_args()

    # Modo galeria
    if args.gallery:
        make_gallery(args.save)
        return

    # Modo batch
    if args.batch:
        os.makedirs(args.outdir, exist_ok=True)
        if args.batch == "fpm5":
            batch_fpm(5, args.outdir)
        elif args.batch == "fpm9":
            batch_fpm(9, args.outdir)
        elif args.batch == "dpc":
            batch_dpc(args.outdir)
        elif args.batch == "sim":
            batch_sim(args.outdir)
        return

    # Modo single
    if not args.pattern:
        parser.print_help()
        return

    if args.pattern == "bf":
        p = pattern_bf(radius=args.radius)
    elif args.pattern == "df":
        p = pattern_df(inner=args.inner, outer=args.outer)
    elif args.pattern == "dpc":
        p = pattern_dpc(radius=args.radius, direction=args.direction)
    elif args.pattern == "fpm":
        p = pattern_fpm(grid=args.grid, idx=args.idx, ix=args.ix, iy=args.iy)
    elif args.pattern == "stripe":
        p = pattern_stripe(orientation=args.orientation,
                           period=args.period, phase=args.phase)
    elif args.pattern == "square":
        p = pattern_square(side=args.side)
    elif args.pattern == "point":
        p = pattern_point(x=args.x, y=args.y)
    elif args.pattern == "cross":
        p = pattern_cross(thickness=args.thickness)
    elif args.pattern == "quadrant":
        p = pattern_quadrant(quad=args.quad)

    if args.info:
        print_info(args.pattern, p)

    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        Image.fromarray(p).save(args.save)
        print(f"  Guardado: {args.save}  ({p.shape[1]}x{p.shape[0]} uint8)")
    elif not args.info:
        # Preview
        plt.figure(figsize=(5, 5), facecolor="white")
        plt.imshow(p, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        plt.title(f"{args.pattern}")
        plt.axis("off")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
