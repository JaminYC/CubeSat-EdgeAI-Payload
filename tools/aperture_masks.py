"""
Generador de mascaras opticas FISICAS para microscopia lensless con OV5647.

A diferencia de tools/aperture_patterns.py (que genera patrones para mostrar
en el OLED), este script genera **placas con huecos** para fabricar:
  - Por laser cut en aluminio / acrilico negro (0.3 - 0.5 mm)
  - Por foto-etching en acero inoxidable (alta precision)
  - Por impresion 1:1 en papel + recorte / aguja
  - Por taladro manual sobre tape negro

Cada mascara se monta entre la muestra y el sensor, separada una distancia
controlada por un spacer (vidrio, plastico negro, anillo impreso 3D).

Uso:
    # Galeria de todas las formas
    python tools/aperture_masks.py --gallery

    # Una mascara especifica → SVG escalado en mm + PNG preview
    python tools/aperture_masks.py --shape circle --diameter 1.0 --save out/pinhole_1mm.svg
    python tools/aperture_masks.py --shape square --side 1.5 --save out/square_1.5mm.svg
    python tools/aperture_masks.py --shape slit --width 0.1 --length 4.0 --save out/slit_100um.svg
    python tools/aperture_masks.py --shape array --pinhole 0.2 --pitch 1.0 --grid 5 --save out/honey.svg

    # Calcular parametros opticos para tu setup
    python tools/aperture_masks.py --shape circle --diameter 1.0 --info --h 1.5

Convenciones:
    - Plate exterior: cuadrado de 25x25 mm (encaja en el modulo OV5647 v1.3).
    - Apertura(s) centradas.
    - SVG en unidades mm (fillset Inkscape / LibreCAD / RDWorks compatible).
    - PNG preview a 200 DPI con dimensiones marcadas.
"""

import argparse
import os
import math

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

# Geometria por defecto del modulo OV5647 v1.3
PLATE_SIZE_MM = 25.0          # mascara exterior 25x25 mm
SENSOR_W_MM = 3.6288          # area activa horizontal
SENSOR_H_MM = 2.7216          # area activa vertical
PIXEL_PITCH_UM = 1.4
DEFAULT_H_MM = 1.5            # distancia mascara-sensor (spacer)


# ── Generadores SVG ───────────────────────────────────────────────────

def svg_header(plate=PLATE_SIZE_MM):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{plate}mm" height="{plate}mm"
     viewBox="0 0 {plate} {plate}" stroke-width="0.05" stroke="black" fill="none">
'''


def svg_footer():
    return "</svg>\n"


def svg_plate_outline(plate=PLATE_SIZE_MM):
    """Contorno cuadrado de la placa + cruz de centrado para alineacion."""
    s = ""
    s += f'<rect x="0" y="0" width="{plate}" height="{plate}" stroke="red"/>\n'
    # Cruz de centrado en las esquinas para alineacion mecanica
    for cx, cy in [(2, 2), (plate - 2, 2), (2, plate - 2), (plate - 2, plate - 2)]:
        s += f'<line x1="{cx-0.5}" y1="{cy}" x2="{cx+0.5}" y2="{cy}" stroke="red"/>\n'
        s += f'<line x1="{cx}" y1="{cy-0.5}" x2="{cx}" y2="{cy+0.5}" stroke="red"/>\n'
    return s


def shape_circle(diameter_mm: float, plate=PLATE_SIZE_MM) -> str:
    """Pinhole circular centrado."""
    cx = cy = plate / 2
    r = diameter_mm / 2
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="black"/>\n'


def shape_square(side_mm: float, plate=PLATE_SIZE_MM) -> str:
    """Apertura cuadrada centrada."""
    cx = cy = plate / 2
    s = side_mm
    return f'<rect x="{cx-s/2}" y="{cy-s/2}" width="{s}" height="{s}" stroke="black"/>\n'


def shape_slit(width_mm: float, length_mm: float, plate=PLATE_SIZE_MM,
                orientation="h") -> str:
    """Rendija lineal centrada. orientation: h (horizontal) o v (vertical)."""
    cx = cy = plate / 2
    if orientation == "h":
        w, h = length_mm, width_mm
    else:
        w, h = width_mm, length_mm
    return f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" stroke="black"/>\n'


def shape_array(pinhole_mm: float, pitch_mm: float, grid: int = 5,
                 plate=PLATE_SIZE_MM) -> str:
    """Arreglo NxN de pinholes circulares (collimator honeycomb-like)."""
    cx = cy = plate / 2
    r = pinhole_mm / 2
    s = ""
    half = (grid - 1) / 2
    for iy in range(grid):
        for ix in range(grid):
            x = cx + (ix - half) * pitch_mm
            y = cy + (iy - half) * pitch_mm
            s += f'<circle cx="{x}" cy="{y}" r="{r}" stroke="black"/>\n'
    return s


def shape_cross(width_mm: float, length_mm: float, plate=PLATE_SIZE_MM) -> str:
    """Cruz: dos rendijas perpendiculares."""
    return (shape_slit(width_mm, length_mm, plate, "h") +
            shape_slit(width_mm, length_mm, plate, "v"))


def shape_annulus(d_outer_mm: float, d_inner_mm: float,
                   plate=PLATE_SIZE_MM) -> str:
    """Anillo: pinhole + obstruccion central. Para dark-field reverso."""
    cx = cy = plate / 2
    s = f'<circle cx="{cx}" cy="{cy}" r="{d_outer_mm/2}" stroke="black"/>\n'
    s += f'<circle cx="{cx}" cy="{cy}" r="{d_inner_mm/2}" stroke="black"/>\n'
    return s


# ── Calculo optico ───────────────────────────────────────────────────

def optical_params(shape_size_mm: float, h_mm: float, lambda_nm: float = 550):
    """
    Calcula NA, angulo, FOV equivalente, resolucion de Abbe, transmitancia.
    shape_size_mm: dimension caracteristica (diametro pinhole, ancho slit, etc).
    """
    half = shape_size_mm / 2
    theta = math.atan(half / h_mm)  # rad
    NA = math.sin(theta)
    abbe_um = (lambda_nm / 1000) / (2 * NA) if NA > 0 else float("inf")
    # Area de la apertura (asumiendo circular)
    area_pinhole = math.pi * half ** 2
    # Hipotesis: area que veria el sensor sin mascara dentro del FOV
    area_full = math.pi * (h_mm * math.tan(math.radians(45))) ** 2
    transmittance = area_pinhole / area_full if area_full > 0 else 0
    return {
        "NA":             NA,
        "theta_deg":      math.degrees(theta),
        "abbe_um":        abbe_um,
        "transmittance":  transmittance,
    }


def print_info(shape_name, params: dict, optical: dict):
    print(f"\n=== Mascara: {shape_name} ===")
    for k, v in params.items():
        print(f"  {k:20s} = {v}")
    print(f"  Para distancia mascara-sensor h = {params.get('h_mm', DEFAULT_H_MM):.2f} mm:")
    print(f"  NA aceptacion        = {optical['NA']:.3f}")
    print(f"  Angulo aceptacion    = +/- {optical['theta_deg']:.1f}°")
    print(f"  Resol. Abbe (550nm)  = {optical['abbe_um']:.2f} um  ({optical['abbe_um']*1000:.0f} nm)")
    print(f"  Transmitancia rel.   = {optical['transmittance']*100:.2f} %")


# ── Visualizacion (galeria) ──────────────────────────────────────────

def draw_mask(ax, draw_fn, title, params_text=""):
    """Dibuja una mascara con la placa, su corte de contorno, y dimensiones."""
    plate = PLATE_SIZE_MM
    ax.set_xlim(-1, plate + 1)
    ax.set_ylim(-1, plate + 1)
    ax.set_aspect("equal")
    # Placa exterior
    ax.add_patch(Rectangle((0, 0), plate, plate, edgecolor="red",
                            facecolor="#222222", linewidth=1.0))
    # Apertura(s)
    draw_fn(ax)
    # Sensor activo proyectado en el centro
    cx = cy = plate / 2
    ax.add_patch(Rectangle(
        (cx - SENSOR_W_MM / 2, cy - SENSOR_H_MM / 2),
        SENSOR_W_MM, SENSOR_H_MM,
        edgecolor="cyan", facecolor="none", linewidth=0.8, linestyle="--"
    ))
    ax.set_title(title, fontsize=10, fontweight="bold")
    if params_text:
        ax.text(plate / 2, -0.5, params_text, ha="center", va="top",
                fontsize=8, family="monospace")
    ax.set_xticks([])
    ax.set_yticks([])
    # Escalas
    for tick in [5, 10, 15, 20]:
        ax.plot([tick, tick], [-0.3, 0], "k-", linewidth=0.5)


def make_gallery(out_path: str = None, h_mm: float = DEFAULT_H_MM):
    fig, axes = plt.subplots(2, 4, figsize=(16, 8.5), facecolor="white")
    axes = axes.flatten()
    plate = PLATE_SIZE_MM

    # 1. Pinhole circular 1 mm
    d = 1.0
    op = optical_params(d, h_mm)
    draw_mask(axes[0],
              lambda ax: ax.add_patch(Circle((plate/2, plate/2), d/2,
                                              edgecolor="lime", facecolor="white", linewidth=1.5)),
              "Pinhole circular Ø1.0 mm",
              f"NA={op['NA']:.2f}  θ={op['theta_deg']:.0f}°  Abbe={op['abbe_um']:.1f}μm")

    # 2. Pinhole circular 0.5 mm (mas estricto)
    d = 0.5
    op = optical_params(d, h_mm)
    draw_mask(axes[1],
              lambda ax: ax.add_patch(Circle((plate/2, plate/2), d/2,
                                              edgecolor="lime", facecolor="white", linewidth=1.5)),
              "Pinhole circular Ø0.5 mm",
              f"NA={op['NA']:.2f}  θ={op['theta_deg']:.0f}°  Abbe={op['abbe_um']:.1f}μm")

    # 3. Apertura cuadrada 1.5 mm
    s = 1.5
    op = optical_params(s, h_mm)
    draw_mask(axes[2],
              lambda ax: ax.add_patch(Rectangle((plate/2-s/2, plate/2-s/2), s, s,
                                                  edgecolor="lime", facecolor="white", linewidth=1.5)),
              "Apertura cuadrada 1.5 mm",
              f"NA={op['NA']:.2f}  θ={op['theta_deg']:.0f}°  area={s*s:.2f}mm²")

    # 4. Slit horizontal 0.1 x 4 mm
    w, l = 0.1, 4.0
    op = optical_params(w, h_mm)
    draw_mask(axes[3],
              lambda ax: ax.add_patch(Rectangle((plate/2-l/2, plate/2-w/2), l, w,
                                                  edgecolor="lime", facecolor="white", linewidth=1.5)),
              f"Rendija (slit) {w*1000:.0f}μm × {l:.1f}mm",
              f"NA_eje_corto={op['NA']:.2f}  θ={op['theta_deg']:.0f}°  line-scan")

    # 5. Slit vertical
    draw_mask(axes[4],
              lambda ax: ax.add_patch(Rectangle((plate/2-w/2, plate/2-l/2), w, l,
                                                  edgecolor="lime", facecolor="white", linewidth=1.5)),
              f"Rendija vertical {w*1000:.0f}μm × {l:.1f}mm",
              f"perpendicular a la anterior")

    # 6. Cruz (slit H + V)
    draw_mask(axes[5],
              lambda ax: (
                  ax.add_patch(Rectangle((plate/2-l/2, plate/2-w/2), l, w,
                                          edgecolor="lime", facecolor="white", linewidth=1.5)),
                  ax.add_patch(Rectangle((plate/2-w/2, plate/2-l/2), w, l,
                                          edgecolor="lime", facecolor="white", linewidth=1.5))
              ),
              f"Cruz: slits H + V cruzados",
              f"detecta gradientes en X e Y")

    # 7. Honeycomb 5x5 pinholes 0.2mm pitch 1mm
    ph, pitch, grid = 0.2, 1.0, 5
    def draw_array(ax):
        half = (grid - 1) / 2
        for iy in range(grid):
            for ix in range(grid):
                x = plate/2 + (ix - half) * pitch
                y = plate/2 + (iy - half) * pitch
                ax.add_patch(Circle((x, y), ph/2, edgecolor="lime",
                                     facecolor="white", linewidth=1.0))
    op = optical_params(ph, h_mm)
    draw_mask(axes[6], draw_array,
              f"Honeycomb 5×5 (Ø{ph*1000:.0f}μm @ {pitch:.1f}mm)",
              f"NA c/pinhole={op['NA']:.2f}  collimator paralelo")

    # 8. Anillo (annulus) — dark field reverso
    d_out, d_in = 2.0, 1.5
    def draw_ann(ax):
        ax.add_patch(Circle((plate/2, plate/2), d_out/2, edgecolor="lime",
                              facecolor="white", linewidth=1.5))
        ax.add_patch(Circle((plate/2, plate/2), d_in/2, edgecolor="black",
                              facecolor="black", linewidth=1.5))
    op_o = optical_params(d_out, h_mm)
    op_i = optical_params(d_in, h_mm)
    draw_mask(axes[7], draw_ann,
              f"Anillo Ø{d_out:.1f}/{d_in:.1f} mm",
              f"NA={op_i['NA']:.2f}-{op_o['NA']:.2f}  dark-field/oblique")

    fig.suptitle(
        f"Mascaras opticas para OV5647 lensless  "
        f"(distancia mascara-sensor h = {h_mm} mm)\n"
        f"Placa 25×25 mm.  Cyan punteado = area activa del sensor (3.6×2.7 mm).  "
        f"Verde = apertura (zona transparente).",
        fontsize=11, fontweight="bold"
    )
    plt.tight_layout()
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        plt.savefig(out_path, dpi=180, bbox_inches="tight")
        print(f"  Galeria guardada: {out_path}")
    plt.show()


# ── Diagrama de ensamblaje (cross-section) ──────────────────────────

def _label_arrow(ax, x_target, y_target, x_label, y_label, text,
                  color="black", fontsize=9, ha="left", va="center",
                  bbox_color="white"):
    """Etiqueta con flecha leader desde el target a la posicion del label."""
    ax.annotate(text, xy=(x_target, y_target), xytext=(x_label, y_label),
                fontsize=fontsize, color=color, ha=ha, va=va,
                arrowprops=dict(arrowstyle="-", color="gray",
                                  lw=0.7, connectionstyle="arc3,rad=0"),
                bbox=dict(boxstyle="round,pad=0.25", facecolor=bbox_color,
                          edgecolor="gray", linewidth=0.5))


def _draw_sensor_stack(ax, sensor_y=0, sensor_w=8, label_externally=False,
                         label_x_left=None):
    """Dibuja PCB + cover glass del OV5647.
    Si label_externally=True, las etiquetas van afuera con flechas."""
    sensor_h = 1.0
    cover_glass_h = 0.4
    # PCB
    ax.add_patch(Rectangle((0, sensor_y), sensor_w, sensor_h,
                            facecolor="#2c5282", edgecolor="black"))
    if not label_externally:
        ax.text(sensor_w/2, sensor_y + sensor_h/2, "PCB OV5647",
                 ha="center", va="center", color="white", fontsize=9)
    # Cover glass
    ax.add_patch(Rectangle((1.5, sensor_y + sensor_h), sensor_w - 3, cover_glass_h,
                            facecolor="#bee3f8", edgecolor="black", alpha=0.7))
    if not label_externally:
        ax.text(sensor_w/2, sensor_y + sensor_h + cover_glass_h/2,
                 "cover glass 0.4 mm", ha="center", va="center", fontsize=7)
    # Linea del plano de pixeles activos
    px_y = sensor_y + sensor_h - 0.05
    ax.plot([1.5, sensor_w-1.5], [px_y, px_y], "r-", lw=1.5, alpha=0.85)
    if not label_externally:
        ax.text(sensor_w-1.4, px_y, " plano de pixeles",
                 ha="left", va="center", fontsize=6, color="red")
    else:
        # Etiquetas externas con flechas
        if label_x_left is None:
            label_x_left = -2.5
        # PCB
        _label_arrow(ax, x_target=sensor_w/2, y_target=sensor_y + sensor_h/2,
                      x_label=label_x_left, y_label=sensor_y + sensor_h/2,
                      text="PCB OV5647", fontsize=9, ha="left",
                      bbox_color="#2c5282")
        # Cover glass
        _label_arrow(ax, x_target=sensor_w/2, y_target=sensor_y + sensor_h + cover_glass_h/2,
                      x_label=label_x_left, y_label=sensor_y + sensor_h + cover_glass_h/2 + 0.6,
                      text="cover glass\n0.4 mm", fontsize=8, ha="left")
        # Plano de pixeles
        _label_arrow(ax, x_target=sensor_w*0.25, y_target=px_y,
                      x_label=label_x_left, y_label=px_y - 0.5,
                      text="plano de\npixeles activos", fontsize=8,
                      color="red", ha="left")
    return sensor_y + sensor_h + cover_glass_h, sensor_h, cover_glass_h


def _draw_oled_rays(ax, x_center, y_top, n=7, x_spread=2.5, color="#d69e2e"):
    """Rayos amarillos venidos desde arriba simulando la iluminacion del OLED."""
    light_y = y_top + 1.5
    for x_off in np.linspace(-x_spread, x_spread, n):
        ax.annotate("", xy=(x_center + x_off * 0.4, y_top),
                     xytext=(x_center + x_off, light_y),
                     arrowprops=dict(arrowstyle="->", color=color, lw=0.7))
    ax.text(x_center, light_y + 0.05, "↓ luz desde OLED ↓",
             ha="center", fontsize=9, color=color)
    return light_y


def _draw_dim_arrow(ax, x, y0, y1, label, side="right"):
    """Flecha vertical de cota con etiqueta al costado."""
    ax.annotate("", xy=(x, y0), xytext=(x, y1),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1))
    yc = (y0 + y1) / 2
    if side == "right":
        ax.text(x + 0.2, yc, label, ha="left", va="center", fontsize=8)
    else:
        ax.text(x - 0.2, yc, label, ha="right", va="center", fontsize=8)


def _draw_panel_A(ax, sensor_w=10):
    """Contact imaging: muestra encima del cover glass, sin mascara.
    Usa etiquetas EXTERNAS con flechas para que no se superpongan."""
    label_x = -3.0
    cover_top, sensor_h, cg_h = _draw_sensor_stack(
        ax, sensor_y=0, sensor_w=sensor_w,
        label_externally=True, label_x_left=label_x
    )
    # Muestra
    sample_h = 0.5
    sample_y = cover_top + 0.05
    ax.add_patch(Rectangle((sensor_w/2 - 2.5, sample_y), 5.0, sample_h,
                            facecolor="#fbd38d", edgecolor="black", alpha=0.85))
    _label_arrow(ax, x_target=sensor_w/2 - 2.5, y_target=sample_y + sample_h/2,
                  x_label=label_x, y_label=sample_y + sample_h/2,
                  text="muestra\n(en contacto)", fontsize=9,
                  bbox_color="#fbd38d")
    # Rayos OLED
    light_y = _draw_oled_rays(ax, sensor_w/2, sample_y + sample_h + 0.3,
                                x_spread=3.0, n=9)
    # Cono de blur (un punto P del sample → muchos pixels)
    sample_pt_x = sensor_w / 2
    sample_pt_y = sample_y + sample_h / 3
    pixel_y = cover_top - 0.05
    alpha = math.degrees(math.atan(3.0 / 1.5))
    blur_x_half = (sample_pt_y - pixel_y) * math.tan(math.radians(alpha))
    ax.fill([sample_pt_x - blur_x_half, sample_pt_x + blur_x_half, sample_pt_x],
             [pixel_y, pixel_y, sample_pt_y], color="red", alpha=0.18)
    ax.plot([sample_pt_x, sample_pt_x - blur_x_half],
             [sample_pt_y, pixel_y], "r--", lw=0.8)
    ax.plot([sample_pt_x, sample_pt_x + blur_x_half],
             [sample_pt_y, pixel_y], "r--", lw=0.8)
    ax.plot([sample_pt_x - blur_x_half, sample_pt_x + blur_x_half],
             [pixel_y, pixel_y], "r-", lw=2.5)
    ax.plot(sample_pt_x, sample_pt_y, "ko", markersize=6)
    # Etiqueta del punto P y del blur (a la derecha, no debajo)
    _label_arrow(ax, x_target=sample_pt_x, y_target=sample_pt_y,
                  x_label=sensor_w + 0.3, y_label=sample_pt_y + 0.3,
                  text="punto P\nde la muestra", fontsize=8, ha="left")
    _label_arrow(ax, x_target=sample_pt_x + blur_x_half, y_target=pixel_y,
                  x_label=sensor_w + 0.3, y_label=pixel_y - 0.4,
                  text=f"blur en sensor\n≈ {blur_x_half*2*100:.0f} μm",
                  fontsize=8, color="red", ha="left",
                  bbox_color="#fed7d7")
    # Cota de z
    _draw_dim_arrow(ax, sensor_w + 0.5, pixel_y, sample_y,
                    "z ≈ 0.5 mm\n(cover + epoxy)", side="right")
    ax.set_xlim(label_x - 1, sensor_w + 4.5)
    ax.set_ylim(-0.6, light_y + 0.8)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("A) Contact imaging\nmuestra ↔ cover glass directo",
                  fontsize=11, fontweight="bold", pad=10)


def _draw_panel_B(ax, sensor_w=10, h_mm=DEFAULT_H_MM):
    """Lensless: muestra encima de la mascara, mascara separada por spacer."""
    cover_top, _, _ = _draw_sensor_stack(ax, sensor_y=0, sensor_w=sensor_w)
    # Spacer
    spacer_h = h_mm
    spacer_y = cover_top + 0.05
    ax.add_patch(Rectangle((1, spacer_y), 1.5, spacer_h,
                            facecolor="#cbd5e0", edgecolor="black"))
    ax.add_patch(Rectangle((sensor_w - 2.5, spacer_y), 1.5, spacer_h,
                            facecolor="#cbd5e0", edgecolor="black"))
    ax.text(1.75, spacer_y + spacer_h/2, f"spacer\nh={h_mm}mm",
             ha="center", va="center", fontsize=8, rotation=90)
    # Mascara
    mask_h = 0.4
    mask_y = spacer_y + spacer_h + 0.05
    ax.add_patch(Rectangle((0.5, mask_y), sensor_w - 1, mask_h,
                            facecolor="#1a202c", edgecolor="black", hatch="///"))
    ax.text(sensor_w/2, mask_y + mask_h/2 + 0.4, "MASCARA",
             ha="center", va="bottom", color="white", fontsize=10, fontweight="bold")
    # Apertura
    aperture_d = 1.0
    ax.add_patch(Rectangle((sensor_w/2 - aperture_d/2, mask_y),
                             aperture_d, mask_h,
                             facecolor="white", edgecolor="black"))
    ax.text(sensor_w/2, mask_y - 0.45, "apertura (D)",
             ha="center", fontsize=9)
    # Muestra encima de la mascara
    sample_h = 0.5
    sample_y = mask_y + mask_h + 0.15
    ax.add_patch(Rectangle((sensor_w/2 - 2.0, sample_y), 4.0, sample_h,
                            facecolor="#fbd38d", edgecolor="black", alpha=0.85))
    ax.text(sensor_w/2, sample_y + sample_h/2, "muestra",
             ha="center", va="center", fontsize=10, fontweight="bold")
    light_y = _draw_oled_rays(ax, sensor_w/2, sample_y + sample_h + 0.3,
                                x_spread=3.0, n=9)
    # Cono de luz: del aperture al plano de pixeles
    aperture_x = sensor_w / 2
    aperture_y = mask_y
    pixel_y = cover_top - 0.05
    NA_geom = aperture_d / (2 * spacer_h)
    blur_at_pixel = aperture_d / 2
    ax.fill([aperture_x - aperture_d/2, aperture_x + aperture_d/2,
              aperture_x + blur_at_pixel, aperture_x - blur_at_pixel],
             [aperture_y, aperture_y, pixel_y, pixel_y],
             color="green", alpha=0.18)
    ax.plot([aperture_x - aperture_d/2, aperture_x - blur_at_pixel],
             [aperture_y, pixel_y], "g--", lw=0.8)
    ax.plot([aperture_x + aperture_d/2, aperture_x + blur_at_pixel],
             [aperture_y, pixel_y], "g--", lw=0.8)
    ax.text(aperture_x + 2.2, (aperture_y + pixel_y)/2,
             f"NA = D/(2h)\n   ≈ {NA_geom:.2f}",
             ha="left", va="center", fontsize=9, color="green", fontweight="bold")
    # Cota z total
    _draw_dim_arrow(ax, sensor_w + 0.7, pixel_y, sample_y,
                    f"z ≈ {h_mm + 0.45:.1f} mm\n(spacer + cover)", side="right")
    ax.set_xlim(-1, sensor_w + 4)
    ax.set_ylim(-0.6, light_y + 0.8)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("B) Lensless con mascara + spacer\nmuestra encima de la mascara",
                  fontsize=11, fontweight="bold", pad=10)


def _draw_panel_C(ax, sensor_w=10, h_illum_mm=4.0):
    """Hibrido: muestra contact + mascara arriba para controlar iluminacion."""
    cover_top, _, _ = _draw_sensor_stack(ax, sensor_y=0, sensor_w=sensor_w)
    # Muestra en contacto (como A)
    sample_h = 0.5
    sample_y = cover_top + 0.05
    ax.add_patch(Rectangle((sensor_w/2 - 2.5, sample_y), 5.0, sample_h,
                            facecolor="#fbd38d", edgecolor="black", alpha=0.85))
    ax.text(sensor_w/2, sample_y + sample_h/2, "muestra (en contacto)",
             ha="center", va="center", fontsize=10, fontweight="bold")
    # Spacer (mas alto, separa muestra de mascara superior)
    spacer_y = sample_y + sample_h + 0.1
    ax.add_patch(Rectangle((1, spacer_y), 1.5, h_illum_mm,
                            facecolor="#cbd5e0", edgecolor="black"))
    ax.add_patch(Rectangle((sensor_w - 2.5, spacer_y), 1.5, h_illum_mm,
                            facecolor="#cbd5e0", edgecolor="black"))
    ax.text(1.75, spacer_y + h_illum_mm/2,
             f"spacer\nh₂={h_illum_mm}mm",
             ha="center", va="center", fontsize=8, rotation=90)
    # Mascara arriba (entre muestra y OLED)
    mask_h = 0.4
    mask_y = spacer_y + h_illum_mm + 0.1
    ax.add_patch(Rectangle((0.5, mask_y), sensor_w - 1, mask_h,
                            facecolor="#1a202c", edgecolor="black", hatch="///"))
    ax.text(sensor_w/2, mask_y + mask_h/2 + 0.4, "MASCARA (arriba)",
             ha="center", va="bottom", color="white", fontsize=10, fontweight="bold")
    # Apertura
    aperture_d = 1.5
    ax.add_patch(Rectangle((sensor_w/2 - aperture_d/2, mask_y),
                             aperture_d, mask_h,
                             facecolor="white", edgecolor="black"))
    ax.text(sensor_w/2, mask_y - 0.45, "apertura (D)",
             ha="center", fontsize=9)
    # Rayos OLED — solo los que pasan por la apertura
    light_y = mask_y + mask_h + 1.5
    for x_off in np.linspace(-3, 3, 11):
        ax.annotate("", xy=(sensor_w/2 + x_off * 0.3, mask_y + mask_h),
                     xytext=(sensor_w/2 + x_off, light_y),
                     arrowprops=dict(arrowstyle="->", color="#d69e2e", lw=0.6, alpha=0.4))
    ax.text(sensor_w/2, light_y + 0.05, "↓ luz desde OLED ↓",
             ha="center", fontsize=9, color="#d69e2e")
    # Cono que pasa la apertura → ilumina la muestra
    aperture_x = sensor_w / 2
    aperture_y = mask_y
    sample_top_y = sample_y + sample_h
    NA_illum = aperture_d / (2 * h_illum_mm)
    spread_at_sample = aperture_d / 2 + h_illum_mm * (aperture_d / 2 / h_illum_mm)
    ax.fill([aperture_x - aperture_d/2, aperture_x + aperture_d/2,
              aperture_x + spread_at_sample, aperture_x - spread_at_sample],
             [aperture_y, aperture_y, sample_top_y, sample_top_y],
             color="purple", alpha=0.15)
    ax.plot([aperture_x - aperture_d/2, aperture_x - spread_at_sample],
             [aperture_y, sample_top_y], "--", color="purple", lw=0.8)
    ax.plot([aperture_x + aperture_d/2, aperture_x + spread_at_sample],
             [aperture_y, sample_top_y], "--", color="purple", lw=0.8)
    ax.text(aperture_x + 2.3, (aperture_y + sample_top_y)/2,
             f"NA_iluminacion\n= D/(2h₂)\n≈ {NA_illum:.2f}",
             ha="left", va="center", fontsize=9,
             color="purple", fontweight="bold")
    # Cota z al sensor (sigue chico)
    pixel_y = cover_top - 0.05
    _draw_dim_arrow(ax, sensor_w + 0.7, pixel_y, sample_y,
                    "z ≈ 0.5 mm\n(igual que A!)", side="right")
    ax.set_xlim(-1, sensor_w + 4)
    ax.set_ylim(-0.6, light_y + 0.8)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("C) Contact + mascara arriba\nfiltra angulo de iluminacion",
                  fontsize=11, fontweight="bold", pad=10)


def _add_pros_cons(tax, title, color_bg, color_edge, lines):
    """Agrega caja de pros/cons en un axis dedicado."""
    tax.axis("off")
    text = title + "\n" + "\n".join(lines)
    tax.text(0.5, 0.5, text, transform=tax.transAxes,
             ha="center", va="center", fontsize=9.5,
             bbox=dict(boxstyle="round,pad=0.6", facecolor=color_bg,
                       edgecolor=color_edge, linewidth=1.5))


def make_assembly_diagram(out_path: str = None, h_mm: float = DEFAULT_H_MM):
    """Diagrama comparativo de TRES modos de ensamblaje del lensless."""
    fig = plt.figure(figsize=(22, 9), facecolor="white")
    gs = fig.add_gridspec(2, 3, height_ratios=[5, 1.2], hspace=0.08, wspace=0.15)

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    tax_a = fig.add_subplot(gs[1, 0])
    tax_b = fig.add_subplot(gs[1, 1])
    tax_c = fig.add_subplot(gs[1, 2])

    _draw_panel_A(ax_a)
    _draw_panel_B(ax_b, h_mm=h_mm)
    _draw_panel_C(ax_c)

    _add_pros_cons(tax_a,
        "MODO A — CONTACT IMAGING",
        "#fef5e7", "#d69e2e",
        ["✓ maxima luz al sensor",
         "✓ z minimo → blur minimo",
         "✗ sin filtrado angular",
         "✗ contamina el sensor",
         "✗ resol ≈ pixel pitch (1.4 μm) si OLED es puntual",
         "→ mejor con FPM (un LED a la vez)"])

    _add_pros_cons(tax_b,
        "MODO B — LENSLESS CON MASCARA + SPACER",
        "#e6fffa", "#319795",
        ["✓ filtrado angular controlado",
         "✓ NA elegida por diseño",
         "✓ sample NO toca el sensor",
         "✗ pierde luz (transmittance baja)",
         "✗ z mayor → blur geometrico > pixel pitch",
         "→ ideal para muestras secas (cebolla, fibras)"])

    _add_pros_cons(tax_c,
        "MODO C — CONTACT + MASCARA DE ILUMINACION",
        "#faf5ff", "#805ad5",
        ["✓ z minimo → maxima nitidez (igual que A)",
         "✓ angulo de iluminacion controlado por mascara",
         "✓ permite DPC, dark field, Köhler simplificado",
         "✗ sample en contacto con sensor",
         "✗ mascara mas grande (esta lejos: h₂ = 4 mm)",
         "→ el mejor compromiso para celulas vivas"])

    fig.suptitle(
        "Tres modos de ensamblaje lensless con OV5647 (vista lateral)",
        fontsize=14, fontweight="bold", y=0.99
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    if out_path:
        plt.savefig(out_path, dpi=160, bbox_inches="tight")
        print(f"  Diagrama de ensamblaje guardado: {out_path}")
    plt.show()


# ── Generadores OpenSCAD para spacer / holder ─────────────────────────

def generate_holder_scad(h_mm: float = DEFAULT_H_MM,
                          plate_mm: float = PLATE_SIZE_MM,
                          aperture_diameter_mm: float = 1.0) -> str:
    """
    Spacer/holder 3D printable que mantiene la mascara a distancia h del sensor.
    Salida: codigo OpenSCAD listo para abrir y exportar a STL.
    """
    return f'''// CubeSat OV5647 — Spacer + holder de mascara lensless
// Genera STL: Abrir en OpenSCAD → F6 → Export STL
// Imprimir en PLA / PETG NEGRO mate (importante: opaco a luz visible)

$fn = 80;

plate         = {plate_mm};            // mascara 25x25 mm
spacer_h      = {h_mm};            // distancia mascara-sensor
mask_thickness = 0.5;
wall          = 1.5;            // grosor pared spacer
sensor_pcb_w  = 25;             // modulo OV5647
sensor_pcb_h  = 24;
sensor_window_w = 6;            // hueco para que pase la luz
aperture_d    = {aperture_diameter_mm};   // diametro de apertura demo

// Spacer: anillo cuadrado vacio
module spacer() {{
    difference() {{
        cube([plate, plate, spacer_h]);
        translate([wall, wall, -0.1])
            cube([plate - 2*wall, plate - 2*wall, spacer_h + 0.2]);
    }}
}}

// Mascara plana con apertura circular (cambiar segun forma)
module mask_circle() {{
    difference() {{
        cube([plate, plate, mask_thickness]);
        translate([plate/2, plate/2, -0.1])
            cylinder(d=aperture_d, h=mask_thickness + 0.2);
    }}
}}

// Mascara con apertura cuadrada
module mask_square(side=1.5) {{
    difference() {{
        cube([plate, plate, mask_thickness]);
        translate([(plate-side)/2, (plate-side)/2, -0.1])
            cube([side, side, mask_thickness + 0.2]);
    }}
}}

// Mascara con rendija (slit)
module mask_slit(width=0.1, length=4) {{
    difference() {{
        cube([plate, plate, mask_thickness]);
        translate([(plate-length)/2, (plate-width)/2, -0.1])
            cube([length, width, mask_thickness + 0.2]);
    }}
}}

// Mascara con arreglo de pinholes
module mask_array(pinhole=0.2, pitch=1.0, grid=5) {{
    difference() {{
        cube([plate, plate, mask_thickness]);
        for (iy = [0:grid-1])
          for (ix = [0:grid-1])
            translate([plate/2 + (ix - (grid-1)/2)*pitch,
                        plate/2 + (iy - (grid-1)/2)*pitch, -0.1])
              cylinder(d=pinhole, h=mask_thickness + 0.2);
    }}
}}

// ─── Render ─────────────────────────────────────────────────
// Descomenta UNA de estas para generar la STL deseada:

spacer();
// translate([plate + 5, 0, 0]) mask_circle();
// translate([2*(plate + 5), 0, 0]) mask_square(side=1.5);
// translate([3*(plate + 5), 0, 0]) mask_slit(width=0.1, length=4);
// translate([0, plate + 5, 0]) mask_array(pinhole=0.2, pitch=1.0, grid=5);
'''


# ── Main / CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--shape", choices=["circle", "square", "slit", "array",
                                              "cross", "annulus"],
                        help="forma de la apertura")
    parser.add_argument("--save", help="ruta del archivo SVG (o PNG si gallery/diagram)")
    parser.add_argument("--gallery", action="store_true",
                        help="mostrar todas las mascaras tipicas")
    parser.add_argument("--diagram", action="store_true",
                        help="diagrama de ensamblaje (vista lateral)")
    parser.add_argument("--scad", action="store_true",
                        help="generar archivo OpenSCAD para imprimir 3D")
    parser.add_argument("--info", action="store_true",
                        help="imprimir parametros opticos")
    parser.add_argument("--h", "--distance", dest="h_mm", type=float,
                        default=DEFAULT_H_MM, help="distancia mascara-sensor (mm)")
    # Parametros por forma
    parser.add_argument("--diameter", type=float, default=1.0,
                        help="diametro circle (mm)")
    parser.add_argument("--side", type=float, default=1.5,
                        help="lado square (mm)")
    parser.add_argument("--width", type=float, default=0.1,
                        help="ancho slit (mm)")
    parser.add_argument("--length", type=float, default=4.0,
                        help="largo slit (mm)")
    parser.add_argument("--orientation", default="h", choices=["h", "v"])
    parser.add_argument("--pinhole", type=float, default=0.2,
                        help="diametro de cada pinhole en array (mm)")
    parser.add_argument("--pitch", type=float, default=1.0,
                        help="separacion entre pinholes en array (mm)")
    parser.add_argument("--grid", type=int, default=5)
    parser.add_argument("--d-outer", dest="d_outer", type=float, default=2.0)
    parser.add_argument("--d-inner", dest="d_inner", type=float, default=1.5)

    args = parser.parse_args()

    if args.gallery:
        out = args.save or "out/aperture_masks_gallery.png"
        make_gallery(out, args.h_mm)
        return

    if args.diagram:
        out = args.save or "out/aperture_masks_assembly.png"
        make_assembly_diagram(out, args.h_mm)
        return

    if args.scad:
        scad = generate_holder_scad(h_mm=args.h_mm,
                                    aperture_diameter_mm=args.diameter)
        out = args.save or "out/holder.scad"
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(scad)
        print(f"  OpenSCAD guardado: {out}")
        print(f"  Abri en OpenSCAD, descomenta la mascara que quieras y exporta STL.")
        return

    if not args.shape:
        parser.print_help()
        return

    # Generar SVG segun forma
    svg = svg_header() + svg_plate_outline()
    params = {"shape": args.shape, "h_mm": args.h_mm}

    if args.shape == "circle":
        svg += shape_circle(args.diameter)
        params["diameter_mm"] = args.diameter
        op = optical_params(args.diameter, args.h_mm)
    elif args.shape == "square":
        svg += shape_square(args.side)
        params["side_mm"] = args.side
        op = optical_params(args.side, args.h_mm)
    elif args.shape == "slit":
        svg += shape_slit(args.width, args.length, orientation=args.orientation)
        params["width_mm"] = args.width
        params["length_mm"] = args.length
        op = optical_params(args.width, args.h_mm)
    elif args.shape == "array":
        svg += shape_array(args.pinhole, args.pitch, args.grid)
        params["pinhole_mm"] = args.pinhole
        params["pitch_mm"] = args.pitch
        params["grid"] = args.grid
        op = optical_params(args.pinhole, args.h_mm)
    elif args.shape == "cross":
        svg += shape_cross(args.width, args.length)
        params["width_mm"] = args.width
        params["length_mm"] = args.length
        op = optical_params(args.width, args.h_mm)
    elif args.shape == "annulus":
        svg += shape_annulus(args.d_outer, args.d_inner)
        params["d_outer_mm"] = args.d_outer
        params["d_inner_mm"] = args.d_inner
        op = optical_params(args.d_outer, args.h_mm)

    svg += svg_footer()

    if args.info:
        print_info(args.shape, params, op)

    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  SVG guardado: {args.save}  ({PLATE_SIZE_MM} × {PLATE_SIZE_MM} mm)")
        print(f"  Abrir en Inkscape / LibreCAD para verificar dimensiones.")
        print(f"  Para laser cut: la linea ROJA es el contorno exterior, NEGRA = aperturas.")


if __name__ == "__main__":
    main()
