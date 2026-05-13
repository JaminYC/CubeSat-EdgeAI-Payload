"""Genera los diagramas de maquinas de estado del INTISAT como PNG.

Reemplaza el render de Mermaid del HTML por figuras matplotlib con
posicionamiento explicito, colores semanticos y tipografia limpia.

Estilo:
  - Estados como cajas redondeadas con color segun rol
  - Transiciones como flechas curvas con etiqueta
  - Estados terminales como circulos negros (UML)
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "figuras" / "m12"
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Paleta semantica (alineada con HTML)
# ============================================================================
C = {
    "mision":   "#1A365D",  # azul oscuro INTISAT
    "nominal":  "#2C5282",  # azul info
    "active":   "#319795",  # cyan activo
    "safe":     "#718096",  # gris seguro
    "fault":    "#C53030",  # rojo anomalia
    "boot":     "#805AD5",  # violeta init
    "ok":       "#2F855A",  # verde ok
    "warn":     "#C58F00",  # ambar
    "subsys":   "#E8F0FE",  # bg subsistema
    "border":   "#2D3748",
    "text":     "#1A202C",
    "muted":    "#718096",
    "bg":       "#FCFDFF",
}


def state_box(ax, xy, label, fill="#E8F0FE", text="#1A202C",
              w=2.4, h=1.0, fontsize=10, weight="bold"):
    x, y = xy
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.18",
        linewidth=1.4, edgecolor=C["border"], facecolor=fill,
    )
    ax.add_patch(p)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=fontsize, color=text, weight=weight)


def terminal(ax, xy, kind="start", r=0.16):
    """Estado terminal UML: circulo negro (start) o circulo en circulo (end)."""
    x, y = xy
    if kind == "start":
        ax.add_patch(Circle((x, y), r, facecolor="#111", edgecolor="#111"))
    else:  # end
        ax.add_patch(Circle((x, y), r * 1.3, facecolor="none", edgecolor="#111", linewidth=1.4))
        ax.add_patch(Circle((x, y), r * 0.65, facecolor="#111", edgecolor="#111"))


def arrow(ax, p1, p2, label=None, rad=0.0, color="#2D3748",
          label_offset=(0, 0.12), fontsize=8, ls="-", lw=1.3):
    x1, y1 = p1
    x2, y2 = p2
    style = f"arc3,rad={rad}"
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=12,
        connectionstyle=style, color=color, linewidth=lw, linestyle=ls,
    )
    ax.add_patch(a)
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        # bbox blanca para legibilidad cuando cruza una flecha
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=fontsize, style="italic", color=C["text"],
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="#cbd5e0", lw=0.5, alpha=0.95))


def setup_ax(ax, xlim, ylim, title=None):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - 0.35, title,
                ha="center", fontsize=14, weight="bold", color=C["mision"])


def save(fig, name):
    out = OUT / name
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# ============================================================================
# Fig 01 — Jerarquia 3 niveles
# ============================================================================
def fig_jerarquia():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    setup_ax(ax, (0, 16), (0, 10), "Jerarquia FSM del INTISAT: 3 niveles")

    # Bandas guia (fondo)
    for y, c, h in [(8.2, "#EDF2F7", 1.4), (5.0, "#EDF2F7", 1.8), (1.8, "#EDF2F7", 1.7)]:
        ax.add_patch(Rectangle((1.6, y - h / 2), 14.2, h,
                               facecolor=c, edgecolor="none", zorder=-2))

    # Etiquetas de nivel (en el margen izquierdo, fuera del area de cajas)
    ax.text(0.85, 8.2, "Nivel 1\nMISION", ha="center", va="center",
            fontsize=11, weight="bold", color=C["mision"])
    ax.text(0.85, 5.0, "Nivel 2\nSUBSISTEMAS", ha="center", va="center",
            fontsize=11, weight="bold", color=C["active"])
    ax.text(0.85, 1.8, "Nivel 3\nCOMPONENTES", ha="center", va="center",
            fontsize=11, weight="bold", color=C["muted"])

    # Separador vertical entre etiquetas y cajas
    ax.plot([1.6, 1.6], [0.5, 9.2], color="#cbd5e0", lw=1.0)

    # Nivel 1 -- Mision (centrado en area de cajas: x in [1.6, 15.8] => mid=8.7)
    state_box(ax, (8.7, 8.2), "MISION\nLAUNCH / NOMINAL / COMMS_PASS / SAFE",
              fill=C["mision"], text="white", w=8.0, h=1.2, fontsize=11.5)

    # Nivel 2 -- 5 subsistemas, espaciados uniformemente
    sub_xs = [2.8, 5.7, 8.7, 11.7, 14.6]
    sub_data = [
        ("OBC",     "BOOT / NOMINAL\nSAFE_HOLD / FAULT"),
        ("EPS",     "CHARGING\nDISCHARGING\nBATTERY_LOW"),
        ("ADCS",    "DETUMBLE / SUN_PT\nNADIR / SAFE"),
        ("COMMS",   "IDLE / BEACON\nRX / TX"),
        ("PAYLOAD", "IDLE / CAPTURING\nPROC / DOWNLINK"),
    ]
    for x, (name, st) in zip(sub_xs, sub_data):
        state_box(ax, (x, 5.0), f"{name}\n{st}", fill=C["active"], text="white",
                  w=2.7, h=1.6, fontsize=9)
        arrow(ax, (8.7, 7.6), (x, 5.85), color="#4a5568", lw=1.0, label=None)

    # Nivel 3 -- componentes (OBC y PAYLOAD)
    state_box(ax, (2.8, 1.8), "watchdog\nmemoria health\nbus I2C health",
              fill="#A0AEC0", text="white", w=2.7, h=1.5, fontsize=9, weight="normal")
    state_box(ax, (14.6, 1.8), "OV5647 sensor\nOLED SSD1351\nINA219",
              fill="#A0AEC0", text="white", w=2.7, h=1.5, fontsize=9, weight="normal")
    arrow(ax, (2.8, 4.2), (2.8, 2.6), color="#a0aec0", lw=1.0)
    arrow(ax, (14.6, 4.2), (14.6, 2.6), color="#a0aec0", lw=1.0)

    # Anotacion "regla de oro"
    ax.text(8.7, 0.4,
            "Regla: la FSM de Mision NO controla detalles, solo dice 'estamos en X'. "
            "Cada subsistema interpreta ese X en su contexto local.",
            ha="center", fontsize=9.5, style="italic", color=C["mision"],
            bbox=dict(boxstyle="round,pad=0.3", fc="#FFFBEB",
                      ec=C["warn"], lw=1.2))

    plt.tight_layout()
    return save(fig, "fig01_jerarquia.png")


# ============================================================================
# Fig 02 — FSM de MISION
# ============================================================================
def fig_mision():
    fig, ax = plt.subplots(figsize=(15, 10))
    setup_ax(ax, (0, 18), (0, 12), "FSM de MISION (nivel 1): 8 modos operacionales")

    # Layout: linea horizontal de "arranque" arriba, NOMINAL grande al centro,
    # SAFE/EOL abajo, COMMS/ECLIPSE/PAYLOAD a los lados
    pos = {
        "LAUNCH":        (1.8, 10.0),
        "DETUMBLE":      (5.0, 10.0),
        "COMMISSIONING": (8.5, 10.0),
        "PAYLOAD_OP":    (3.5, 6.5),
        "NOMINAL":       (9.0, 6.5),
        "COMMS_PASS":    (14.5, 6.5),
        "ECLIPSE":       (15.0, 9.5),
        "SAFE":          (9.0, 3.0),
        "EOL":           (15.5, 2.5),
    }
    colors = {
        "LAUNCH":        C["boot"],
        "DETUMBLE":      C["warn"],
        "COMMISSIONING": C["warn"],
        "NOMINAL":       C["nominal"],
        "PAYLOAD_OP":    C["active"],
        "COMMS_PASS":    C["active"],
        "ECLIPSE":       C["muted"],
        "SAFE":          C["safe"],
        "EOL":           "#4a5568",
    }
    box_w = {"NOMINAL": 2.6}
    for name, (x, y) in pos.items():
        w = box_w.get(name, 2.4)
        state_box(ax, (x, y), name, fill=colors[name], text="white",
                  w=w, h=0.95, fontsize=11)

    # Terminales
    terminal(ax, (0.55, 10.0), "start")
    terminal(ax, (17.3, 2.5), "end")

    def tr(a, b, label, rad=0.0, off=(0, 0.22), fs=8.5, color="#2D3748"):
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        arrow(ax, (x1, y1), (x2, y2), label, rad=rad, label_offset=off,
              fontsize=fs, color=color)

    arrow(ax, (0.7, 10.0), pos["LAUNCH"], "separation", label_offset=(0, 0.22))

    # Fila superior: arranque secuencial
    tr("LAUNCH", "DETUMBLE", "deployer eject")
    tr("DETUMBLE", "COMMISSIONING", "rates<1°/s")
    tr("COMMISSIONING", "NOMINAL", "subsys OK", rad=-0.25, off=(0.6, -0.3))

    # NOMINAL <-> PAYLOAD_OP
    tr("NOMINAL", "PAYLOAD_OP", "CMD_START_PAYLOAD", rad=-0.22, off=(0, 0.35))
    tr("PAYLOAD_OP", "NOMINAL", "scan done", rad=-0.22, off=(0, -0.35))

    # NOMINAL <-> COMMS_PASS
    tr("NOMINAL", "COMMS_PASS", "ground LOS", rad=-0.22, off=(0, 0.35))
    tr("COMMS_PASS", "NOMINAL", "pass done", rad=-0.22, off=(0, -0.35))

    # NOMINAL <-> ECLIPSE (curvada arriba)
    tr("NOMINAL", "ECLIPSE", "sun<thresh", rad=0.3, off=(0.7, 0.3))
    tr("ECLIPSE", "NOMINAL", "sun>thresh", rad=0.3, off=(-0.7, -0.2))

    # NOMINAL -> SAFE / SAFE -> NOMINAL
    tr("NOMINAL", "SAFE", "anomaly /\nlow voltage", rad=0.2, off=(0.7, 0))
    tr("SAFE", "NOMINAL", "CMD_RESUME", rad=0.2, off=(-0.8, 0))

    # PAYLOAD_OP -> SAFE / COMMS_PASS -> SAFE
    tr("PAYLOAD_OP", "SAFE", "critical fault", rad=-0.25, off=(-0.6, 0.1))
    tr("COMMS_PASS", "SAFE", "critical fault", rad=0.25, off=(0.7, 0.1))

    # NOMINAL -> EOL
    tr("NOMINAL", "EOL", "alt<200km", rad=-0.4, off=(0.8, -0.6))
    arrow(ax, pos["EOL"], (17.15, 2.5), "reentry", label_offset=(0, 0.22))

    # Leyenda en banda inferior (separada del grafo)
    ax.add_patch(Rectangle((0.5, 0.4), 17, 0.9,
                           facecolor="#F7FAFC", edgecolor="#CBD5E0", lw=0.8))
    items = [
        ("Init/transitorio", C["boot"]),
        ("Estabilizacion",   C["warn"]),
        ("Default (NOMINAL)", C["nominal"]),
        ("Activo",           C["active"]),
        ("Eclipse",          C["muted"]),
        ("Safe",             C["safe"]),
        ("EOL",              "#4a5568"),
    ]
    for i, (label, color) in enumerate(items):
        x = 1.0 + i * 2.45
        ax.add_patch(Rectangle((x, 0.75), 0.35, 0.25,
                               facecolor=color, edgecolor=color))
        ax.text(x + 0.45, 0.87, label, va="center", fontsize=9)

    plt.tight_layout()
    return save(fig, "fig02_mision.png")


# ============================================================================
# Fig 03 — FSM del OBC
# ============================================================================
def fig_obc():
    fig, ax = plt.subplots(figsize=(13, 8))
    setup_ax(ax, (0, 14), (0, 9), "FSM del OBC (On-Board Computer)")

    pos = {
        "BOOT":        (2.0, 6.8),
        "NOMINAL":     (7.0, 6.8),
        "MAINTENANCE": (12.0, 6.8),
        "FAULT":       (4.0, 3.0),
        "SAFE_HOLD":   (10.0, 3.0),
    }
    colors = {
        "BOOT":        C["boot"],
        "NOMINAL":     C["nominal"],
        "MAINTENANCE": C["active"],
        "FAULT":       C["fault"],
        "SAFE_HOLD":   C["safe"],
    }
    for n, p in pos.items():
        state_box(ax, p, n, fill=colors[n], text="white", w=2.6, h=1.0, fontsize=11)

    terminal(ax, (0.55, 6.8), "start")
    arrow(ax, (0.7, 6.8), pos["BOOT"], None)

    arrow(ax, pos["BOOT"], pos["NOMINAL"], "init OK", label_offset=(0, 0.25))
    arrow(ax, pos["BOOT"], pos["FAULT"], "init fail", rad=-0.25, label_offset=(-0.6, 0.3))
    arrow(ax, pos["NOMINAL"], pos["MAINTENANCE"], "eclipse window", rad=-0.2, label_offset=(0, 0.3))
    arrow(ax, pos["MAINTENANCE"], pos["NOMINAL"], "tasks done", rad=-0.2, label_offset=(0, -0.3))
    arrow(ax, pos["NOMINAL"], pos["FAULT"], "watchdog / SEU", rad=0.25, label_offset=(-0.9, -0.3))
    arrow(ax, pos["FAULT"], pos["NOMINAL"], "auto-reboot OK", rad=0.25, label_offset=(0.9, -0.3))
    arrow(ax, pos["NOMINAL"], pos["SAFE_HOLD"], "CMD_SAFE_OBC", rad=-0.25, label_offset=(0.9, -0.3))
    arrow(ax, pos["SAFE_HOLD"], pos["NOMINAL"], "CMD_RESUME", rad=-0.25, label_offset=(-0.9, 0.3))
    arrow(ax, pos["FAULT"], pos["SAFE_HOLD"], "3 reboots failed", label_offset=(0, 0.25))

    # Tabla de consumo (banda inferior separada)
    ax.add_patch(Rectangle((0.5, 0.5), 13, 1.0,
                           facecolor="#F7FAFC", edgecolor="#CBD5E0", lw=0.8))
    ax.text(7, 1.25, "Consumo tipico por estado",
            ha="center", fontsize=10, weight="bold", color=C["mision"])
    ax.text(7, 0.8,
            "BOOT ~3 W    |    NOMINAL ~1.5 W    |    MAINTENANCE ~2 W    |    "
            "SAFE_HOLD ~1 W    |    FAULT varia",
            ha="center", fontsize=10, color=C["text"])

    plt.tight_layout()
    return save(fig, "fig03_obc.png")


# ============================================================================
# Fig 04 — FSM del EPS
# ============================================================================
def fig_eps():
    fig, ax = plt.subplots(figsize=(14, 9))
    setup_ax(ax, (0, 15), (0, 10), "FSM del EPS (Electric Power System)")

    # Layout: BOOT a la izquierda, columna central con niveles de SoC,
    # CHARGING/DISCHARGING a la derecha, FAULT abajo
    pos = {
        "BOOT":              (1.5, 8.5),
        "BATTERY_NOMINAL":   (6.5, 8.5),
        "CHARGING":          (11.5, 9.2),
        "DISCHARGING":       (11.5, 7.0),
        "BATTERY_LOW":       (6.5, 5.0),
        "BATTERY_CRITICAL":  (6.5, 2.0),
        "FAULT":             (12.0, 2.0),
    }
    colors = {
        "BOOT":             C["boot"],
        "BATTERY_NOMINAL":  C["ok"],
        "CHARGING":         C["nominal"],
        "DISCHARGING":      C["warn"],
        "BATTERY_LOW":      "#D69E2E",
        "BATTERY_CRITICAL": C["fault"],
        "FAULT":            "#742A2A",
    }
    for n, p in pos.items():
        state_box(ax, p, n, fill=colors[n], text="white", w=2.8, h=0.95, fontsize=11)

    terminal(ax, (0.4, 8.5), "start")
    terminal(ax, (14.0, 2.0), "end")
    arrow(ax, (0.55, 8.5), pos["BOOT"], None)
    arrow(ax, pos["FAULT"], (13.85, 2.0), "BMS shutdown", label_offset=(0, 0.25))

    # BOOT -> tres destinos segun SoC
    arrow(ax, pos["BOOT"], pos["BATTERY_NOMINAL"], "SoC>70%", label_offset=(0, 0.25))
    arrow(ax, pos["BOOT"], pos["BATTERY_LOW"], "30-70%", rad=-0.2, label_offset=(0.4, 0))
    arrow(ax, pos["BOOT"], pos["BATTERY_CRITICAL"], "SoC<30%", rad=-0.4, label_offset=(-1.5, -0.6))

    # NOMINAL <-> CHARGING / DISCHARGING
    arrow(ax, pos["BATTERY_NOMINAL"], pos["CHARGING"], "sun & SoC<100%", rad=-0.2, label_offset=(0, 0.35))
    arrow(ax, pos["CHARGING"], pos["BATTERY_NOMINAL"], "SoC>90%", rad=-0.2, label_offset=(0, -0.3))
    arrow(ax, pos["BATTERY_NOMINAL"], pos["DISCHARGING"], "eclipse", rad=0.2, label_offset=(0, 0.3))
    arrow(ax, pos["DISCHARGING"], pos["BATTERY_LOW"], "SoC<70%", rad=0.2, label_offset=(0.8, 0))

    # LOW <-> NOMINAL (recarga)
    arrow(ax, pos["BATTERY_LOW"], pos["BATTERY_NOMINAL"], "SoC>80%", rad=-0.3, label_offset=(-0.9, 0))

    # LOW <-> CRITICAL
    arrow(ax, pos["BATTERY_LOW"], pos["BATTERY_CRITICAL"], "SoC<30%", label_offset=(0.5, 0))
    arrow(ax, pos["BATTERY_CRITICAL"], pos["BATTERY_LOW"], "SoC>40%", rad=-0.3, label_offset=(-0.8, 0))

    # CRITICAL -> FAULT
    arrow(ax, pos["BATTERY_CRITICAL"], pos["FAULT"], "SoC<10%", label_offset=(0, 0.25))

    # Nota crítica en banda inferior
    ax.add_patch(Rectangle((0.5, 0.3), 14, 0.85,
                           facecolor="#FFF5F5", edgecolor=C["fault"], lw=1.2))
    ax.text(7.5, 0.72,
            "CRITICO: BATTERY_CRITICAL fuerza al bus completo a SAFE — apaga payload/ADCS y mantiene solo OBC + COMMS minimo",
            ha="center", fontsize=10, style="italic", color=C["fault"], weight="bold")

    plt.tight_layout()
    return save(fig, "fig04_eps.png")


# ============================================================================
# Fig 05 — FSM del ADCS
# ============================================================================
def fig_adcs():
    fig, ax = plt.subplots(figsize=(15, 9.5))
    setup_ax(ax, (0, 16), (0, 11), "FSM del ADCS (Attitude Determination & Control)")

    # Layout: fila superior = secuencia inicial (OFF->DETUMBLE->SUN_ACQ->SUN_PT)
    # fila central = SUN_PT es el hub central; NADIR/TARGET a los lados; INERTIAL_HOLD para eclipse
    # SAFE abajo
    pos = {
        "OFF":              (1.5, 9.0),
        "DETUMBLE":         (5.0, 9.0),
        "SUN_ACQUISITION":  (8.5, 9.0),
        "SUN_POINTING":     (12.5, 9.0),
        "INERTIAL_HOLD":    (12.5, 5.5),
        "NADIR_POINTING":   (8.5, 5.5),
        "TARGET_POINTING":  (4.5, 5.5),
        "SAFE":             (8.5, 2.0),
    }
    colors = {
        "OFF":             C["safe"],
        "DETUMBLE":        C["warn"],
        "SUN_ACQUISITION": C["boot"],
        "SUN_POINTING":    C["ok"],
        "NADIR_POINTING":  C["active"],
        "TARGET_POINTING": C["active"],
        "INERTIAL_HOLD":   C["muted"],
        "SAFE":            C["fault"],
    }
    for n, p in pos.items():
        state_box(ax, p, n, fill=colors[n], text="white", w=2.8, h=0.95, fontsize=10.5)

    terminal(ax, (0.4, 9.0), "start")
    arrow(ax, (0.55, 9.0), pos["OFF"], None)

    # Secuencia inicial
    arrow(ax, pos["OFF"], pos["DETUMBLE"], "post-deploy", label_offset=(0, 0.25))
    arrow(ax, pos["DETUMBLE"], pos["SUN_ACQUISITION"], "rates<1°/s", label_offset=(0, 0.25))
    arrow(ax, pos["SUN_ACQUISITION"], pos["SUN_POINTING"], "sun vector OK", label_offset=(0, 0.25))

    # SUN_POINTING hub (vertical hacia abajo)
    arrow(ax, pos["SUN_POINTING"], pos["INERTIAL_HOLD"], "eclipse start", rad=0.2, label_offset=(0.9, 0))
    arrow(ax, pos["INERTIAL_HOLD"], pos["SUN_POINTING"], "eclipse end", rad=0.2, label_offset=(-0.9, 0))

    # SUN_PT <-> NADIR
    arrow(ax, pos["SUN_POINTING"], pos["NADIR_POINTING"], "CMD nadir", rad=-0.2, label_offset=(0, 0.3))
    arrow(ax, pos["NADIR_POINTING"], pos["SUN_POINTING"], "CMD sun", rad=-0.2, label_offset=(0, -0.3))

    # SUN_PT <-> TARGET (curva mas larga)
    arrow(ax, pos["SUN_POINTING"], pos["TARGET_POINTING"], "CMD target\n(lat, lon)",
          rad=0.3, label_offset=(-1.0, 0.5))
    arrow(ax, pos["TARGET_POINTING"], pos["SUN_POINTING"], "target done",
          rad=0.3, label_offset=(1.0, -0.5))

    # gyro faults -> SAFE
    arrow(ax, pos["SUN_POINTING"], pos["SAFE"], "gyro fault", rad=-0.35, label_offset=(1.2, -0.7))
    arrow(ax, pos["NADIR_POINTING"], pos["SAFE"], "gyro fault", rad=0.0, label_offset=(0.6, 0))
    arrow(ax, pos["TARGET_POINTING"], pos["SAFE"], "gyro fault", rad=-0.25, label_offset=(0.6, -0.4))

    # SAFE -> DETUMBLE (recovery)
    arrow(ax, pos["SAFE"], pos["DETUMBLE"], "CMD_RESUME", rad=-0.4, label_offset=(-1.8, 1.5))

    # Banda inferior con nota
    ax.add_patch(Rectangle((0.5, 0.3), 15, 0.85,
                           facecolor="#F7FAFC", edgecolor="#CBD5E0", lw=0.8))
    ax.text(8, 0.72,
            "DETUMBLE: post-deploy estabiliza rates con magnetorquers (algoritmo B-dot).   "
            "SUN_POINTING es el modo 'default' por seguridad termica/energetica.",
            ha="center", fontsize=10, style="italic", color=C["text"])

    plt.tight_layout()
    return save(fig, "fig05_adcs.png")


# ============================================================================
# Fig 06 — FSM del COMMS
# ============================================================================
def fig_comms():
    fig, ax = plt.subplots(figsize=(14, 9))
    setup_ax(ax, (0, 15), (0, 10), "FSM de COMMS (Comunicaciones UHF / S-Band)")

    # IDLE en el centro; BEACON/TX arriba, RX/TX_ACK abajo, COMMAND_PROC al fondo, FAULT al costado
    pos = {
        "IDLE":               (7.5, 6.0),
        "BEACON":             (2.5, 8.5),
        "TX":                 (12.5, 8.5),
        "RX":                 (2.5, 3.5),
        "TX_ACK":             (12.5, 3.5),
        "COMMAND_PROCESSING": (7.5, 1.8),
        "FAULT":              (13.5, 6.0),
    }
    colors = {
        "IDLE":               C["nominal"],
        "BEACON":             C["active"],
        "RX":                 C["ok"],
        "COMMAND_PROCESSING": C["boot"],
        "TX_ACK":             C["active"],
        "TX":                 C["active"],
        "FAULT":              C["fault"],
    }
    for n, p in pos.items():
        state_box(ax, p, n, fill=colors[n], text="white", w=2.8, h=0.95, fontsize=10.5)

    terminal(ax, (0.55, 6.0), "start")
    arrow(ax, (0.7, 6.0), pos["IDLE"], None)

    # IDLE <-> BEACON
    arrow(ax, pos["IDLE"], pos["BEACON"], "timer 30 s", rad=-0.2, label_offset=(-0.7, 0.3))
    arrow(ax, pos["BEACON"], pos["IDLE"], "beacon sent", rad=-0.2, label_offset=(0.7, -0.2))

    # IDLE <-> TX
    arrow(ax, pos["IDLE"], pos["TX"], "CMD_DOWNLINK", rad=0.2, label_offset=(0.8, 0.3))
    arrow(ax, pos["TX"], pos["IDLE"], "queue empty", rad=0.2, label_offset=(-0.8, -0.2))

    # IDLE -> RX, RX -> COMMAND_PROC -> TX_ACK -> IDLE
    arrow(ax, pos["IDLE"], pos["RX"], "carrier detected", rad=0.25, label_offset=(-1.0, 0))
    arrow(ax, pos["RX"], pos["COMMAND_PROCESSING"], "valid frame", rad=-0.2, label_offset=(0, -0.3))
    arrow(ax, pos["COMMAND_PROCESSING"], pos["RX"], "invalid (drop)",
          rad=-0.2, label_offset=(0, 0.3), ls="--", color=C["muted"])
    arrow(ax, pos["COMMAND_PROCESSING"], pos["TX_ACK"], "cmd OK", rad=-0.2, label_offset=(0, -0.3))
    arrow(ax, pos["TX_ACK"], pos["IDLE"], "ack sent", rad=-0.25, label_offset=(0.9, 0))

    # IDLE <-> FAULT
    arrow(ax, pos["IDLE"], pos["FAULT"], "T>85°C", rad=-0.2, label_offset=(0, 0.3))
    arrow(ax, pos["FAULT"], pos["IDLE"], "T normal", rad=-0.2, label_offset=(0, -0.3))

    # Banda inferior
    ax.add_patch(Rectangle((0.5, 0.3), 14, 0.85,
                           facecolor="#F7FAFC", edgecolor="#CBD5E0", lw=0.8))
    ax.text(7.5, 0.72,
            "BEACON: AX.25 cada 30 s con telemetria basica (SoC, modo, temp).   "
            "TX usa S-Band si esta presente, fallback UHF.",
            ha="center", fontsize=10, style="italic", color=C["text"])

    plt.tight_layout()
    return save(fig, "fig06_comms.png")


# ============================================================================
# Fig 07 — FSM del PAYLOAD
# ============================================================================
def fig_payload():
    fig, ax = plt.subplots(figsize=(16, 10))
    setup_ax(ax, (0, 17), (0, 11), "FSM del PAYLOAD (microscopia FPM — INTISAT)")

    # Layout: fila superior = pipeline feliz (BOOT->IDLE->CAPTURING->PROCESSING->EXPORTING)
    # fila media = DOWNLINK; lateral = OTA, SAFE_MODE; fondo = ERROR
    pos = {
        "BOOT":       (1.5, 9.0),
        "IDLE":       (5.5, 9.0),
        "CAPTURING":  (9.5, 9.0),
        "PROCESSING": (13.5, 9.0),
        "EXPORTING":  (13.5, 6.0),
        "DOWNLINK":   (9.5, 6.0),
        "SAFE_MODE":  (1.5, 6.0),
        "OTA":        (5.5, 6.0),
        "ERROR":      (9.5, 2.0),
    }
    colors = {
        "BOOT":       C["boot"],
        "IDLE":       C["nominal"],
        "CAPTURING":  C["active"],
        "PROCESSING": "#9F7AEA",
        "EXPORTING":  "#319795",
        "DOWNLINK":   C["ok"],
        "OTA":        C["warn"],
        "SAFE_MODE":  C["safe"],
        "ERROR":      C["fault"],
    }
    for n, p in pos.items():
        state_box(ax, p, n, fill=colors[n], text="white", w=2.8, h=0.95, fontsize=11)

    terminal(ax, (0.4, 9.0), "start")
    arrow(ax, (0.55, 9.0), pos["BOOT"], None)

    # camino feliz (verde)
    happy = "#2F855A"
    arrow(ax, pos["BOOT"], pos["IDLE"], "services up", label_offset=(0, 0.25))
    arrow(ax, pos["IDLE"], pos["CAPTURING"], "CMD_START_CAPTURE",
          label_offset=(0, 0.25), color=happy)
    arrow(ax, pos["CAPTURING"], pos["PROCESSING"], "25 frames OK",
          label_offset=(0, 0.25), color=happy)
    arrow(ax, pos["PROCESSING"], pos["EXPORTING"], "IA OK",
          rad=-0.0, label_offset=(0.5, 0), color=happy)
    arrow(ax, pos["EXPORTING"], pos["DOWNLINK"], "files written",
          label_offset=(0, 0.25), color=happy)
    arrow(ax, pos["DOWNLINK"], pos["IDLE"], "tx complete",
          rad=-0.3, label_offset=(0.5, 1.0), color=happy)

    # SAFE_MODE
    arrow(ax, pos["IDLE"], pos["SAFE_MODE"], "CMD_SAFE", rad=0.2, label_offset=(0.5, 0.3))
    arrow(ax, pos["SAFE_MODE"], pos["IDLE"], "CMD_RESUME", rad=0.2, label_offset=(-0.5, -0.3))

    # OTA
    arrow(ax, pos["IDLE"], pos["OTA"], "CMD_OTA_COMMIT", rad=-0.2, label_offset=(0.9, 0))
    arrow(ax, pos["OTA"], pos["IDLE"], "checkout OK", rad=-0.2, label_offset=(-0.9, 0))
    arrow(ax, pos["OTA"], pos["ERROR"], "rollback", rad=-0.3, label_offset=(-0.7, 0.5),
          color="#742a2a")

    # caminos de error (rojos, diagonal hacia ERROR central)
    err_c = "#742a2a"
    arrow(ax, pos["CAPTURING"], pos["ERROR"], "sensor fail",
          rad=0.3, label_offset=(0.9, 1.0), color=err_c)
    arrow(ax, pos["PROCESSING"], pos["ERROR"], "IA fail",
          rad=0.3, label_offset=(1.0, 0.5), color=err_c)
    arrow(ax, pos["EXPORTING"], pos["ERROR"], "disk full",
          rad=-0.3, label_offset=(1.0, 0), color=err_c)
    arrow(ax, pos["ERROR"], pos["IDLE"], "CMD_RESUME",
          rad=-0.4, label_offset=(-2.0, 1.5))

    # Banda inferior con codigo real
    ax.add_patch(Rectangle((0.5, 0.3), 16, 0.9,
                           facecolor="#F0FFF4", edgecolor=happy, lw=1.0))
    ax.text(8.5, 0.95, "PAYLOAD ya esta implementado en el INTISAT (no es propuesta)",
            ha="center", fontsize=10.5, weight="bold", color=happy)
    ax.text(8.5, 0.55,
            "Codigo: cubesat/commands.py:STATE_*    Watchdog: systemd cubesat-pipeline.service    "
            "OTA: rollback automatico    Flujo verde = camino feliz",
            ha="center", fontsize=9.5, color=C["text"])

    plt.tight_layout()
    return save(fig, "fig07_payload.png")


# ============================================================================
# Fig 08 — Matriz modos x subsistemas (heatmap visual)
# ============================================================================
def fig_matriz():
    modes = ["LAUNCH", "DETUMBLE", "COMMISSIONING", "NOMINAL",
             "PAYLOAD_OP", "COMMS_PASS", "ECLIPSE", "SAFE", "EOL"]
    subs = ["OBC", "EPS", "ADCS", "COMMS", "PAYLOAD"]

    # rol: 0=off/idle, 1=normal, 2=activo, 3=safe/fault
    role = {
        ("LAUNCH",        "OBC"): ("BOOT", 1),
        ("LAUNCH",        "EPS"): ("NOMINAL", 1),
        ("LAUNCH",        "ADCS"): ("OFF", 0),
        ("LAUNCH",        "COMMS"): ("IDLE", 0),
        ("LAUNCH",        "PAYLOAD"): ("OFF", 0),

        ("DETUMBLE",      "OBC"): ("NOMINAL", 1),
        ("DETUMBLE",      "EPS"): ("DISCHARG", 1),
        ("DETUMBLE",      "ADCS"): ("DETUMBLE", 2),
        ("DETUMBLE",      "COMMS"): ("BEACON", 2),
        ("DETUMBLE",      "PAYLOAD"): ("OFF", 0),

        ("COMMISSIONING", "OBC"): ("NOMINAL", 1),
        ("COMMISSIONING", "EPS"): ("CHARGING", 1),
        ("COMMISSIONING", "ADCS"): ("SUN_PT", 2),
        ("COMMISSIONING", "COMMS"): ("BEACON", 2),
        ("COMMISSIONING", "PAYLOAD"): ("OFF", 0),

        ("NOMINAL",       "OBC"): ("NOMINAL", 1),
        ("NOMINAL",       "EPS"): ("CHARGING", 1),
        ("NOMINAL",       "ADCS"): ("SUN_PT", 1),
        ("NOMINAL",       "COMMS"): ("IDLE", 0),
        ("NOMINAL",       "PAYLOAD"): ("IDLE", 0),

        ("PAYLOAD_OP",    "OBC"): ("NOMINAL", 1),
        ("PAYLOAD_OP",    "EPS"): ("DISCHARG", 1),
        ("PAYLOAD_OP",    "ADCS"): ("NADIR_PT", 2),
        ("PAYLOAD_OP",    "COMMS"): ("IDLE", 0),
        ("PAYLOAD_OP",    "PAYLOAD"): ("CAPTURE", 2),

        ("COMMS_PASS",    "OBC"): ("NOMINAL", 1),
        ("COMMS_PASS",    "EPS"): ("DISCHARG", 1),
        ("COMMS_PASS",    "ADCS"): ("TARGET", 2),
        ("COMMS_PASS",    "COMMS"): ("TX/RX", 2),
        ("COMMS_PASS",    "PAYLOAD"): ("DOWNLNK", 1),

        ("ECLIPSE",       "OBC"): ("MAINT", 1),
        ("ECLIPSE",       "EPS"): ("DISCHARG", 1),
        ("ECLIPSE",       "ADCS"): ("INERTIAL", 1),
        ("ECLIPSE",       "COMMS"): ("IDLE", 0),
        ("ECLIPSE",       "PAYLOAD"): ("IDLE", 0),

        ("SAFE",          "OBC"): ("SAFE_HLD", 3),
        ("SAFE",          "EPS"): ("CRITICAL", 3),
        ("SAFE",          "ADCS"): ("DETUMBLE", 3),
        ("SAFE",          "COMMS"): ("BEACON", 3),
        ("SAFE",          "PAYLOAD"): ("SAFE", 3),

        ("EOL",           "OBC"): ("NOMINAL", 1),
        ("EOL",           "EPS"): ("DISCHARG", 1),
        ("EOL",           "ADCS"): ("OFF", 0),
        ("EOL",           "COMMS"): ("BEACON", 2),
        ("EOL",           "PAYLOAD"): ("OFF", 0),
    }
    role_color = {0: "#E2E8F0", 1: "#BFE3C8", 2: "#9DD7D6", 3: "#FBB6B6"}
    role_text = {0: "#4a5568", 1: "#1a1a1a", 2: "#1a1a1a", 3: "#742A2A"}

    fig, ax = plt.subplots(figsize=(12, 7.5))
    setup_ax(ax, (0, 12), (0, 9.5), None)

    cell_w, cell_h = 1.7, 0.78
    x0, y0 = 2.0, 1.0  # esquina inferior izquierda de la matriz

    # cabeceras
    for j, s in enumerate(subs):
        ax.add_patch(Rectangle((x0 + j * cell_w, y0 + len(modes) * cell_h),
                               cell_w, cell_h, facecolor=C["mision"], edgecolor="white"))
        ax.text(x0 + j * cell_w + cell_w / 2, y0 + len(modes) * cell_h + cell_h / 2,
                s, ha="center", va="center", color="white", fontsize=11, weight="bold")

    for i, m in enumerate(modes):
        yi = y0 + (len(modes) - 1 - i) * cell_h
        ax.add_patch(Rectangle((x0 - cell_w * 1.05, yi),
                               cell_w * 1.05, cell_h, facecolor="#F6F8FA", edgecolor="#cbd5e0"))
        ax.text(x0 - cell_w * 1.05 / 2, yi + cell_h / 2, m,
                ha="center", va="center", fontsize=10, weight="bold", color=C["mision"])
        for j, s in enumerate(subs):
            state, r = role[(m, s)]
            x = x0 + j * cell_w
            ax.add_patch(Rectangle((x, yi), cell_w, cell_h,
                                   facecolor=role_color[r], edgecolor="white", linewidth=1.5))
            ax.text(x + cell_w / 2, yi + cell_h / 2, state,
                    ha="center", va="center", fontsize=9, color=role_text[r],
                    weight="bold" if r >= 2 else "normal")

    # titulo
    ax.text(6, 9.0, "Matriz modos x subsistemas (rosetta)",
            ha="center", fontsize=14, weight="bold", color=C["mision"])

    # leyenda
    leg_items = [("OFF/IDLE", role_color[0]),
                 ("Normal", role_color[1]),
                 ("Activo", role_color[2]),
                 ("Safe/Fault", role_color[3])]
    for k, (lab, col) in enumerate(leg_items):
        x = 1.5 + k * 2.5
        ax.add_patch(Rectangle((x, 0.2), 0.4, 0.3, facecolor=col, edgecolor="#888"))
        ax.text(x + 0.55, 0.35, lab, va="center", fontsize=9.5)

    plt.tight_layout()
    return save(fig, "fig08_matriz.png")


if __name__ == "__main__":
    figs = [
        fig_jerarquia, fig_mision, fig_obc, fig_eps,
        fig_adcs, fig_comms, fig_payload, fig_matriz,
    ]
    for fn in figs:
        p = fn()
        print(f"OK -> {p.name}  ({p.stat().st_size // 1024} kB)")
