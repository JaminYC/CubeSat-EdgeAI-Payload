"""
Genera la imagen de tareas por hacer del item 9 (Microscopia)
lista para insertar en un slide.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT_PATH = "out/tareas_microscopia.png"

# Datos: (clave, titulo, progreso 0-100, descripcion corta)
tareas = [
    ("a", "9.1 Tiempo de captura",            0,
     "Instrumentar capture.py con timestamps; medir 25 angulos en banco.",
     "Estimado: 5–10 s/scan."),
    ("b", "9.2 Analisis energetico",          20,
     "Medir consumo con INA219 en RPi + OLED + sensor; tabla idle/activo/pico.",
     "Estimado: ~5.5 W medio, 9 W pico."),
    ("c", "9.3 Canales de respaldo OBC↔RPi",  30,
     "I2C_2 ya implementado como primario; agregar CAN_1 como backup.",
     "Requiere transceiver MCP2515 + can_slave.py."),
    ("d", "9.4 CAD ensamblaje en estructura", 40,
     "Mascaras y housings disenados; falta frame, slot intercambiable y anclaje PC-104.",
     "Estimado: 1–2 dias en Inventor."),
    ("e", "9.5 Reset OBC → RPi",              30,
     "Soft reset por I2C ya implementado (CMD_REBOOT).",
     "Falta hard reset via power cycling del rail 5V_PAYLOAD por el EPS."),
]

# Colores
COLOR_TITLE = "#1A365D"
COLOR_ACCENT = "#C58F00"
COLOR_DONE = "#2F855A"
COLOR_PARTIAL = "#C58F00"
COLOR_TODO = "#C53030"
COLOR_BG = "#FFFFFF"
COLOR_BG_ROW = "#F7FAFC"

def status_color(progress):
    if progress >= 70:  return COLOR_DONE
    if progress >= 30:  return COLOR_PARTIAL
    return COLOR_TODO

def status_label(progress):
    if progress >= 70:  return "HECHO"
    if progress >= 30:  return "PARCIAL"
    return "PENDIENTE"


fig, ax = plt.subplots(figsize=(14, 8.5), facecolor=COLOR_BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_axis_off()

# Header
ax.add_patch(Rectangle((0, 92), 100, 8, facecolor=COLOR_TITLE,
                          edgecolor="none"))
ax.text(50, 96, "9. MICROSCOPIA — Tareas por hacer",
         ha="center", va="center",
         fontsize=18, fontweight="bold", color="white")

# Filas
y_top = 88
row_h = 14
gap = 1
y = y_top

for i, (key, titulo, prog, desc, extra) in enumerate(tareas):
    bg = COLOR_BG_ROW if i % 2 == 0 else COLOR_BG
    ax.add_patch(Rectangle((0, y - row_h), 100, row_h,
                              facecolor=bg, edgecolor="none"))

    # Letra inciso (circulo a la izquierda)
    color = status_color(prog)
    ax.add_patch(mpatches.Circle((4, y - row_h/2), 2.4, facecolor=color,
                                    edgecolor="white", linewidth=1.5))
    ax.text(4, y - row_h/2, key,
             ha="center", va="center",
             fontsize=18, fontweight="bold", color="white")

    # Titulo
    ax.text(8, y - 3.5, titulo,
             ha="left", va="center",
             fontsize=14, fontweight="bold", color=COLOR_TITLE)

    # Descripcion + accion
    ax.text(8, y - 7, desc,
             ha="left", va="center",
             fontsize=11, color="#2D3748")
    ax.text(8, y - 10.2, extra,
             ha="left", va="center",
             fontsize=10, color="#718096", style="italic")

    # Barra de progreso
    bar_x, bar_w = 70, 22
    bar_y = y - 6.5
    bar_h = 1.6
    # Fondo de la barra
    ax.add_patch(Rectangle((bar_x, bar_y), bar_w, bar_h,
                              facecolor="#E2E8F0", edgecolor="none"))
    # Progreso
    ax.add_patch(Rectangle((bar_x, bar_y), bar_w * prog / 100, bar_h,
                              facecolor=color, edgecolor="none"))
    # Etiqueta % y estado
    ax.text(bar_x + bar_w / 2, bar_y + 3.5, f"{prog}%",
             ha="center", va="bottom",
             fontsize=11, fontweight="bold", color=color)
    ax.text(bar_x + bar_w / 2, bar_y - 1.5, status_label(prog),
             ha="center", va="top",
             fontsize=9, fontweight="bold", color=color)

    y -= row_h + gap

# Pie con leyenda
ax.add_patch(Rectangle((0, 0), 100, 4, facecolor="#EDF2F7",
                          edgecolor="none"))
legend_x = 5
ax.add_patch(mpatches.Circle((legend_x + 1, 2), 1.0,
                                facecolor=COLOR_TODO, edgecolor="white"))
ax.text(legend_x + 3, 2, "Pendiente (<30%)",
         ha="left", va="center", fontsize=10, color="#2D3748")
ax.add_patch(mpatches.Circle((legend_x + 22, 2), 1.0,
                                facecolor=COLOR_PARTIAL, edgecolor="white"))
ax.text(legend_x + 24, 2, "Parcial (30–70%)",
         ha="left", va="center", fontsize=10, color="#2D3748")
ax.add_patch(mpatches.Circle((legend_x + 43, 2), 1.0,
                                facecolor=COLOR_DONE, edgecolor="white"))
ax.text(legend_x + 45, 2, "Hecho (>70%)",
         ha="left", va="center", fontsize=10, color="#2D3748")
ax.text(95, 2, "INTISAT — Payload de microscopia FPM",
         ha="right", va="center", fontsize=10, color="#718096", style="italic")

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=180, bbox_inches="tight", facecolor=COLOR_BG)
print(f"  Slide guardado: {OUT_PATH}")
