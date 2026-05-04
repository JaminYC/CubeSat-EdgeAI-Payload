"""
Genera la tabla comparativa de los tres modos de ensamblaje como imagen PNG
lista para usar en presentaciones.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.table import Table

OUT_PATH = "out/modes_comparison_table.png"

# Datos de la tabla
header = ["Criterio", "A) Contact imaging", "B) Mascara + spacer", "C) Contact + mascara arriba"]

rows = [
    ["Distancia muestra-sensor (z)",       "0.5 mm",                   "5.0 mm",                    "0.5 mm"],
    ["Nitidez geometrica",                  "MAXIMA",                   "Media",                     "MAXIMA"],
    ["Luz al sensor",                       "MAXIMA",                   "Reducida",                  "Controlada"],
    ["Filtrado angular",                    "Sin filtrado",             "Si (coleccion)",            "Si (iluminacion)"],
    ["Sample toca sensor",                  "SI (riesgo)",              "NO (toca mascara)",         "SI (cover glass)"],
    ["Versatilidad optica",                 "Baja",                     "Media",                     "ALTA (DPC, DF, oblique)"],
    ["Complejidad mecanica",                "Trivial",                  "Media",                     "Alta (2 pisos)"],
    ["Calibracion eje optico",              "No requerida",             "Critica",                   "Muy critica"],
    ["Caso de uso ideal",                   "FPM (single-LED)",         "Muestras secas",            "Biologico general"],
]

# Colores por criterio (verde=ventaja, rojo=desventaja, gris=neutral)
def cell_color(criterion, value):
    """Devuelve el color de fondo segun si es ventaja/desventaja para ese criterio."""
    pos = {
        "MAXIMA": "#c6f6d5",      # verde fuerte
        "ALTA":   "#c6f6d5",
        "Si": "#fef5e7",           # neutro/positivo
        "Si (coleccion)":  "#bee3f8",
        "Si (iluminacion)": "#bee3f8",
        "Media":  "#fef5e7",
        "Reducida": "#fed7d7",     # rojo
        "Controlada": "#bee3f8",   # azul (info)
        "Sin filtrado": "#fed7d7",
        "SI (riesgo)":  "#fed7d7",
        "NO (toca mascara)": "#fef5e7",
        "SI (cover glass)":  "#fef5e7",
        "Baja":  "#fed7d7",
        "ALTA (DPC, DF, oblique)": "#c6f6d5",
        "Trivial": "#c6f6d5",
        "Alta (2 pisos)": "#fed7d7",
        "No requerida": "#c6f6d5",
        "Critica": "#fef5e7",
        "Muy critica": "#fed7d7",
    }
    return pos.get(value, "#ffffff")


fig, ax = plt.subplots(figsize=(14, 7), facecolor="white")
ax.set_axis_off()

# Crear tabla
n_rows = len(rows) + 1   # + header
n_cols = len(header)
col_widths = [0.28, 0.24, 0.24, 0.24]
row_height = 1.0 / n_rows

table = Table(ax, bbox=[0, 0, 1, 1])

# Header
for j, txt in enumerate(header):
    cell = table.add_cell(0, j, col_widths[j], row_height,
                            text=txt, loc="center",
                            facecolor="#1A365D")
    cell.get_text().set_color("white")
    cell.get_text().set_fontweight("bold")
    cell.get_text().set_fontsize(11)
    cell.set_edgecolor("white")
    cell.set_linewidth(2)

# Rows
for i, row in enumerate(rows, start=1):
    for j, txt in enumerate(row):
        if j == 0:
            # Columna criterio (gris claro, bold)
            color = "#edf2f7"
            cell = table.add_cell(i, j, col_widths[j], row_height,
                                    text=txt, loc="left",
                                    facecolor=color)
            cell.get_text().set_fontweight("bold")
            cell.get_text().set_fontsize(10)
            cell.PAD = 0.04
        else:
            color = cell_color(row[0], txt)
            cell = table.add_cell(i, j, col_widths[j], row_height,
                                    text=txt, loc="center",
                                    facecolor=color)
            cell.get_text().set_fontsize(10)
        cell.set_edgecolor("white")
        cell.set_linewidth(1.5)

ax.add_table(table)

# Titulo
fig.suptitle("Tres modos de ensamblaje lensless con OV5647 — comparativa",
              fontsize=14, fontweight="bold", color="#1A365D", y=0.97)

# Leyenda
legend_handles = [
    mpatches.Patch(color="#c6f6d5", label="Ventaja"),
    mpatches.Patch(color="#fef5e7", label="Neutral / Aceptable"),
    mpatches.Patch(color="#bee3f8", label="Funcionalidad activa"),
    mpatches.Patch(color="#fed7d7", label="Desventaja / Limitacion"),
]
fig.legend(handles=legend_handles, loc="lower center", ncol=4,
            frameon=False, fontsize=10, bbox_to_anchor=(0.5, -0.02))

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(OUT_PATH, dpi=180, bbox_inches="tight", facecolor="white")
print(f"  Tabla guardada: {OUT_PATH}")
