"""Genera los 4 diagramas del manual M11 como PNG con matplotlib.

Reemplazo de los TikZ que se rompieron con `right=of`/`below=of`. Aca
las coordenadas son explicitas y verificables.
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)

# Paleta consistente
COLOR = {
    "solar":   "#FFF3B0",
    "battery": "#FFE08A",
    "rail":    "#CFE8FF",
    "protect": "#FFC9C9",
    "measure": "#D7F0CC",
    "cm5":     "#BFD7F7",
    "carrier": "#E0F5D8",
    "conn":    "#FFE9A6",
    "shifter": "#D9D9D9",
    "obc":     "#FFE0B3",
}


def box(ax, x, y, w, h, label, fill="#EEE", fontsize=10, weight="normal"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2, edgecolor="#222", facecolor=fill,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, label,
            ha="center", va="center", fontsize=fontsize, weight=weight)


def arrow(ax, x1, y1, x2, y2, label=None, color="#222"):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=14,
        linewidth=1.4, color=color,
    )
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, label,
                ha="center", va="bottom", fontsize=8, style="italic")


# =========================================================================
# Fig 1 — Sandwich CM5 + carrier (vista lateral)
# =========================================================================
def fig_sandwich():
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.set_xlim(-2.5, 9)
    ax.set_ylim(-1.5, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # CM5
    box(ax, 0, 2.4, 6, 0.9, "Compute Module 5  (55 x 40 mm)",
        fill=COLOR["cm5"], fontsize=11, weight="bold")

    # Mezzanines (vista de canto)
    box(ax, 0.3, 2.0, 2.5, 0.35, "DF40C-100DS  J1", fill=COLOR["shifter"], fontsize=8)
    box(ax, 3.2, 2.0, 2.5, 0.35, "DF40C-100DS  J2", fill=COLOR["shifter"], fontsize=8)

    # Carrier
    box(ax, -1, 0.4, 8, 1.5, "Carrier board  (~90 x 90 mm)",
        fill=COLOR["carrier"], fontsize=11, weight="bold")

    # Conectores carrier (en la parte de abajo)
    for x, w, txt in [(0.0, 1.2, "PC-104 H1"),
                      (1.5, 1.2, "PC-104 H2"),
                      (3.0, 1.0, "FFC CSI-2"),
                      (4.3, 0.8, "SPI OLED"),
                      (5.3, 0.8, "Debug")]:
        box(ax, x, -0.05, w, 0.45, txt, fill=COLOR["conn"], fontsize=8)

    # Cota stack height
    ax.annotate("", xy=(-1.6, 2.4), xytext=(-1.6, 1.9),
                arrowprops=dict(arrowstyle="<->", color="#444"))
    ax.text(-1.95, 2.15, "1.5 mm\nstack", ha="center", va="center",
            fontsize=9, rotation=90)

    # Titulo
    ax.text(3, 4.15, "Sandwich CM5 + carrier (vista lateral)",
            ha="center", fontsize=12, weight="bold")

    plt.tight_layout()
    out = OUT / "fig01_sandwich.png"
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# =========================================================================
# Fig 2 — Cadena completa de energia (7 etapas)
# =========================================================================
def fig_energia():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")

    BW, BH = 2.2, 0.85  # box width/height homogeneos

    # Fila superior: fuente
    stages_top = [
        (0.3, 5.5, "1. Paneles\nsolares", COLOR["solar"]),
        (3.0, 5.5, "2. MPPT\n(EPS)",      COLOR["solar"]),
        (5.7, 5.5, "3. Bateria\nLi-ion",   COLOR["battery"]),
        (8.4, 5.5, "4. Rail\n5V_PAYLOAD",  COLOR["rail"]),
    ]
    for x, y, t, c in stages_top:
        box(ax, x, y, BW, BH, t, fill=c, fontsize=10)

    # Flechas fila superior (->)
    for i in range(len(stages_top) - 1):
        x1 = stages_top[i][0] + BW
        x2 = stages_top[i + 1][0]
        y = stages_top[i][1] + BH / 2
        arrow(ax, x1 + 0.05, y, x2 - 0.05, y)

    # Flecha bajando del rail al carrier
    rail_x = stages_top[3][0] + BW / 2
    ax.add_patch(FancyArrowPatch(
        (rail_x, stages_top[3][1]),
        (rail_x, 4.2),
        arrowstyle="-|>", mutation_scale=16, color="#222", linewidth=1.6,
    ))
    ax.text(rail_x + 0.15, 4.7, "carrier", fontsize=9, style="italic")

    # Banda separadora: "borde del carrier"
    ax.plot([0.1, 12.9], [4.05, 4.05], "--", color="#888", linewidth=0.8)
    ax.text(0.15, 4.15, "carrier (tu PCB) -->", fontsize=8, color="#666")

    # Fila inferior: proteccion + medicion + CM5
    stages_bot = [
        (8.4, 3.0, "5a. Fusible\nPTC", COLOR["protect"]),
        (5.7, 3.0, "5b. Diodo\nSchottky", COLOR["protect"]),
        (3.0, 3.0, "5c. LDO\n5V / 6A",   COLOR["protect"]),
        (0.3, 3.0, "6. INA219\n(monitor)", COLOR["measure"]),
    ]
    for x, y, t, c in stages_bot:
        box(ax, x, y, BW, BH, t, fill=c, fontsize=10)

    # Flechas fila inferior (<-)
    for i in range(len(stages_bot) - 1):
        x1 = stages_bot[i][0]
        x2 = stages_bot[i + 1][0] + BW
        y = stages_bot[i][1] + BH / 2
        arrow(ax, x1 - 0.05, y, x2 + 0.05, y)

    # Conexion rail -> primer proteccion (fusible) - bajada
    ax.add_patch(FancyArrowPatch(
        (rail_x, 4.2 - 0.0),
        (stages_bot[0][0] + BW / 2, stages_bot[0][1] + BH),
        arrowstyle="-|>", mutation_scale=14, color="#222", linewidth=1.4,
    ))

    # Bajada del INA219 al CM5 (fila final)
    cm5_y = 1.4
    box(ax, 0.3, cm5_y, BW, BH, "7. CM5 5V_IN", fill=COLOR["cm5"], fontsize=10, weight="bold")
    box(ax, 3.0, cm5_y, BW, BH, "PMIC interna\nCM5", fill=COLOR["cm5"], fontsize=10)
    box(ax, 5.7, cm5_y, BW, BH, "Nucleos\nBCM2712", fill=COLOR["cm5"], fontsize=10)

    ax.add_patch(FancyArrowPatch(
        (stages_bot[3][0] + BW / 2, stages_bot[3][1]),
        (0.3 + BW / 2, cm5_y + BH),
        arrowstyle="-|>", mutation_scale=14, color="#222", linewidth=1.4,
    ))
    arrow(ax, 0.3 + BW + 0.05, cm5_y + BH / 2, 3.0 - 0.05, cm5_y + BH / 2)
    arrow(ax, 3.0 + BW + 0.05, cm5_y + BH / 2, 5.7 - 0.05, cm5_y + BH / 2)

    # Banda CM5
    ax.plot([0.1, 12.9], [2.5, 2.5], "--", color="#888", linewidth=0.8)
    ax.text(0.15, 2.6, "CM5 (modulo) -->", fontsize=8, color="#666")

    # Titulo
    ax.text(6.5, 6.7, "Camino de la energia: paneles -> CM5 (7 etapas)",
            ha="center", fontsize=13, weight="bold")

    plt.tight_layout()
    out = OUT / "fig02_energia.png"
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# =========================================================================
# Fig 3 — I2C CM5 <-> TXS0108E <-> OBC
# =========================================================================
def fig_i2c():
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.set_aspect("equal")
    ax.axis("off")

    BW, BH = 3.0, 1.0
    y = 2.0

    box(ax, 0.3, y, BW, BH, "CM5\nGPIO2 / GPIO3\n@ 3.3 V",
        fill=COLOR["cm5"], fontsize=10, weight="bold")
    box(ax, 4.5, y, BW, BH, "TXS0108E\nlevel shifter",
        fill=COLOR["shifter"], fontsize=10, weight="bold")
    box(ax, 8.7, y, BW, BH, "OBC\nSDA2 / SCL2\n@ 3.3 V o 5 V",
        fill=COLOR["obc"], fontsize=10, weight="bold")

    # Lineas dobles SDA/SCL
    for dy, lab in [(0.25, "SDA"), (-0.25, "SCL")]:
        ax.add_patch(FancyArrowPatch(
            (0.3 + BW, y + BH / 2 + dy),
            (4.5, y + BH / 2 + dy),
            arrowstyle="<->", mutation_scale=12, color="#222", linewidth=1.2,
        ))
        ax.add_patch(FancyArrowPatch(
            (4.5 + BW, y + BH / 2 + dy),
            (8.7, y + BH / 2 + dy),
            arrowstyle="<->", mutation_scale=12, color="#222", linewidth=1.2,
        ))
    ax.text((0.3 + BW + 4.5) / 2 + BW / 2 - BW / 2, y + BH / 2 + 0.55, "SDA, SCL",
            ha="center", fontsize=9, style="italic")
    # mejor: etiqueta clara en el centro de cada par
    ax.text(0.3 + BW + (4.5 - 0.3 - BW) / 2, y + BH / 2 + 0.55,
            "SDA, SCL", ha="center", fontsize=9, style="italic")
    ax.text(4.5 + BW + (8.7 - 4.5 - BW) / 2, y + BH / 2 + 0.55,
            "SDA, SCL", ha="center", fontsize=9, style="italic")

    # Pull-ups
    ax.text(0.3 + BW + (4.5 - 0.3 - BW) / 2, y - 0.25,
            "pull-up 4.7 k a 3.3 V", ha="center", fontsize=8, color="#444")
    ax.text(4.5 + BW + (8.7 - 4.5 - BW) / 2, y - 0.25,
            "pull-up 4.7 k a Vbus_OBC", ha="center", fontsize=8, color="#444")

    # Titulo
    ax.text(6, 3.6, "Bus I2C CM5 <-> OBC (con shifter bidireccional)",
            ha="center", fontsize=12, weight="bold")

    plt.tight_layout()
    out = OUT / "fig03_i2c.png"
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# =========================================================================
# Fig 4 — INA219 con shunt (high-side)
# =========================================================================
def fig_ina219():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5)
    ax.set_aspect("equal")
    ax.axis("off")

    BW, BH = 2.4, 0.9
    y_rail = 3.5

    # Linea de potencia
    box(ax, 0.3, y_rail, BW, BH, "5 V desde\nLTM4631",
        fill=COLOR["rail"], fontsize=10, weight="bold")
    box(ax, 4.0, y_rail, BW, BH, "Shunt\n0.1 ohm  1 %",
        fill=COLOR["protect"], fontsize=10, weight="bold")
    box(ax, 7.7, y_rail, BW, BH, "5 V al CM5\n(VIN+, VIN-)",
        fill=COLOR["cm5"], fontsize=10, weight="bold")

    # Flechas linea de potencia
    arrow(ax, 0.3 + BW + 0.05, y_rail + BH / 2, 4.0 - 0.05, y_rail + BH / 2)
    arrow(ax, 4.0 + BW + 0.05, y_rail + BH / 2, 7.7 - 0.05, y_rail + BH / 2)

    # INA219 abajo del shunt
    ina_x, ina_y = 4.0, 1.5
    box(ax, ina_x, ina_y, BW, BH, "INA219\nI2C 0x40",
        fill=COLOR["measure"], fontsize=10, weight="bold")

    # Sensing: dos lineas punteadas desde extremos del shunt al INA
    ax.plot([4.0 + 0.1, ina_x + 0.3],
            [y_rail, ina_y + BH],
            "--", color="#a00", linewidth=1.2)
    ax.plot([4.0 + BW - 0.1, ina_x + BW - 0.3],
            [y_rail, ina_y + BH],
            "--", color="#a00", linewidth=1.2)
    ax.text(4.0 + BW / 2, (y_rail + ina_y + BH) / 2 + 0.05,
            "VIN+   VIN-", ha="center", fontsize=8, color="#a00",
            style="italic")

    # SDA/SCL del INA al CM5
    ax.add_patch(FancyArrowPatch(
        (ina_x + BW / 2, ina_y),
        (ina_x + BW / 2, 0.5),
        arrowstyle="-|>", mutation_scale=14, color="#222", linewidth=1.4,
    ))
    ax.text(ina_x + BW / 2 + 0.15, 0.85,
            "SDA, SCL  ->  CM5 (I2C bus interno)",
            fontsize=9, style="italic")

    # Titulo
    ax.text(5.5, 4.7, "Monitor INA219 sobre el rail 5 V del CM5 (high-side)",
            ha="center", fontsize=12, weight="bold")

    plt.tight_layout()
    out = OUT / "fig04_ina219.png"
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


if __name__ == "__main__":
    for fn in (fig_sandwich, fig_energia, fig_i2c, fig_ina219):
        p = fn()
        print(f"OK -> {p.name}  ({p.stat().st_size // 1024} kB)")
