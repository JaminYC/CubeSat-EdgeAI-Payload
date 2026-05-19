"""Figuras para el manual M15: topologias de red en CubeSats.

Genera 12 figuras matplotlib en Documentos de Referencia/figuras/m15/.

Cubre:
 - modelo OSI adaptado
 - comparacion de buses fisicos
 - 5 topologias clasicas
 - una por mision (FloripaSat, OreSat, AAUSAT, UPSat, NASA cFS, NASA F')
 - matriz comparativa
 - propuesta INTISAT
 - flujo de control en el tiempo
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, RegularPolygon
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "figuras" / "m15"
OUT.mkdir(parents=True, exist_ok=True)

C = {
    "intisat":  "#1A365D",
    "floripa":  "#2F855A",
    "oresat":   "#805AD5",
    "aausat":   "#C53030",
    "upsat":    "#319795",
    "cfs":      "#D69E2E",
    "fprime":   "#2C5282",
    "muted":    "#718096",
    "border":   "#2D3748",
    "text":     "#1A202C",
    "ok":       "#2F855A",
    "warn":     "#C58F00",
    "bus":      "#4A5568",
    "bg":       "#F8F9FA",
}


def box(ax, xy, label, fill="#EEE", w=2.4, h=1.0, fontsize=10,
        text="#1A202C", weight="bold"):
    x, y = xy
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.18",
        linewidth=1.4, edgecolor=C["border"], facecolor=fill,
    )
    ax.add_patch(p)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=fontsize, color=text, weight=weight)


def arrow(ax, p1, p2, label=None, rad=0.0, color="#2D3748",
          fontsize=8, ls="-", lw=1.3, style="-|>"):
    s = f"arc3,rad={rad}"
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=12,
                        connectionstyle=s, color=color, linewidth=lw, linestyle=ls)
    ax.add_patch(a)
    if label:
        mx = (p1[0] + p2[0]) / 2
        my = (p1[1] + p2[1]) / 2 + 0.15
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=fontsize, style="italic", color=C["text"],
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="#cbd5e0", lw=0.5, alpha=0.95))


def setup_ax(ax, xlim, ylim, title=None, title_color=None):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - 0.4, title,
                ha="center", fontsize=14, weight="bold",
                color=title_color or C["intisat"])


def save(fig, name):
    out = OUT / name
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# ============================================================================
# Fig 1 -- Capas OSI adaptado a CubeSat
# ============================================================================
def fig_capas():
    fig, ax = plt.subplots(figsize=(13, 9))
    setup_ax(ax, (0, 14), (0, 11),
             "Modelo de capas de red adaptado a CubeSats")

    layers = [
        # (y, name, examples, color)
        (9.0, "L7  Aplicacion",   "Comandos TC/TM (ECSS, CCSDS), housekeeping, FSM, payload",
         "#1A365D"),
        (7.7, "L6  Presentacion", "Serializacion: TLV, JSON, protobuf, structs C",
         "#2C5282"),
        (6.4, "L5  Sesion",       "Estados de conexion, autenticacion, retries",
         "#2E86C1"),
        (5.1, "L4  Transporte",   "CSP (Cubesat Space Protocol), UDP, CFDP",
         "#7D3C98"),
        (3.8, "L3  Red",          "Direccionamiento de nodo, routing (CSP nodes, CANopen NMT)",
         "#9B59B6"),
        (2.5, "L2  Enlace",       "Frames, ACK, CRC, MAC: I2C/SPI/CAN/AX.25",
         "#D69E2E"),
        (1.2, "L1  Fisico",       "Senal electrica: 3.3V/5V, baudrate, hilos, RS-422/485",
         "#C53030"),
    ]

    for y, name, ex, color in layers:
        ax.add_patch(Rectangle((0.5, y - 0.55), 13, 1.0,
                               facecolor=color, edgecolor=C["border"],
                               linewidth=1.5, alpha=0.95))
        ax.text(1.0, y, name, fontsize=12, color="white", weight="bold",
                va="center")
        ax.text(4.5, y, ex, fontsize=9.5, color="white", va="center",
                style="italic")

    # Lineas de flecha lateral
    ax.annotate("", xy=(13.7, 9.5), xytext=(13.7, 0.7),
                arrowprops=dict(arrowstyle="<->", color="#444", lw=1.5))
    ax.text(13.85, 5.1, "encapsulacion\n(L7 a L1)", fontsize=9,
            color="#444", rotation=90, va="center")

    # Nota inferior
    ax.text(7, 0.2,
            "En CubeSats simples (UPSat, FloripaSat) solo se implementan L1, L2 y L7. "
            "Misiones con CSP (AAUSAT, GomSpace) suben hasta L4.",
            ha="center", fontsize=10, style="italic", color=C["muted"])

    plt.tight_layout()
    return save(fig, "fig01_capas_osi.png")


# ============================================================================
# Fig 2 -- Comparacion de buses fisicos
# ============================================================================
def fig_buses():
    buses = [
        # (name, hilos, vel_max_Mbps, topologia_tipica, robustez, costo, complejidad, color)
        ("I2C",        2,   0.4,  "multi-drop",    2, 1, 1, "#2F855A"),
        ("SPI",        4,  50.0,  "estrella (CS)", 1, 1, 2, "#319795"),
        ("UART/RS-232", 2,  0.115, "punto a punto", 1, 1, 1, "#9B59B6"),
        ("RS-485",     2,  10.0,  "multi-drop",    4, 2, 2, "#D69E2E"),
        ("CAN / CANopen", 2,  1.0,  "multi-master",  5, 2, 3, "#805AD5"),
        ("Ethernet (Mbps)", 4, 100.0, "switched",     3, 4, 5, "#2C5282"),
        ("SpaceWire",  4, 200.0,  "switched",      5, 5, 5, "#1A365D"),
    ]

    fig, ax = plt.subplots(figsize=(14, 8))
    setup_ax(ax, (0, 15), (0, 11),
             "Buses fisicos disponibles en CubeSats: comparacion")

    # Header
    cols = ["Bus", "Hilos", "Vel max", "Topologia", "Robustez",
            "Costo", "Complej.", "Tipico en"]
    col_w = [1.8, 0.9, 1.2, 1.7, 1.4, 1.0, 1.2, 4.5]
    x0 = 0.6
    y_header = 9.7
    x_cur = x0
    ax.add_patch(Rectangle((x0, y_header - 0.4), sum(col_w),
                           0.7, facecolor=C["intisat"], edgecolor="white"))
    for col, w in zip(cols, col_w):
        ax.text(x_cur + w / 2, y_header - 0.05, col, ha="center",
                va="center", color="white", fontsize=10, weight="bold")
        x_cur += w

    # Rows
    extra_info = ["UPSat, AAUSAT, INTISAT", "FloripaSat", "telcomandos legados",
                  "EnduroSat, GomSpace", "OreSat", "misiones grandes (no CubeSat)",
                  "ESA missions (PROBA)"]
    for i, (b, info) in enumerate(zip(buses, extra_info)):
        y = y_header - 0.85 - i * 0.95
        ax.add_patch(Rectangle((x0, y - 0.4), sum(col_w), 0.85,
                               facecolor="#F8F9FA" if i % 2 == 0 else "white",
                               edgecolor="#cbd5e0", linewidth=0.5))
        # marcador color a la izq
        ax.add_patch(Rectangle((x0, y - 0.4), 0.08, 0.85,
                               facecolor=b[7], edgecolor="none"))
        vals = [b[0], str(b[1]), f"{b[2]:.1f} Mbps", b[3]]
        x_cur = x0
        for val, w in zip(vals, col_w[:4]):
            ax.text(x_cur + w / 2, y, val, ha="center", va="center",
                    fontsize=10, weight="bold" if w == col_w[0] else "normal")
            x_cur += w
        # Bars (robustez, costo, complejidad) - ahora simples puntos
        for level, w in zip([b[4], b[5], b[6]], col_w[4:7]):
            ax.text(x_cur + w / 2, y, "*" * level, ha="center", va="center",
                    fontsize=11, color=b[7], weight="bold", family="monospace")
            x_cur += w
        # info
        ax.text(x_cur + col_w[7] / 2, y, info, ha="center", va="center",
                fontsize=9.5, style="italic", color=C["muted"])

    # Leyenda
    ax.text(7.5, 0.5,
            "Robustez / Costo / Complejidad: cada * = 1 punto en escala 1-5",
            ha="center", fontsize=9, color=C["muted"], style="italic")

    plt.tight_layout()
    return save(fig, "fig02_buses_comparados.png")


# ============================================================================
# Fig 3 -- 5 topologias clasicas
# ============================================================================
def fig_topologias():
    fig, axs = plt.subplots(1, 5, figsize=(20, 5.5))

    titles = [
        "Estrella (Star)",
        "Bus / Multidrop",
        "Anillo (Ring)",
        "Malla (Mesh)",
        "Distribuida\n(Pub/Sub logico)"
    ]
    descs = [
        "Hub central, todos conectan al OBC",
        "Todos comparten un mismo bus fisico",
        "Cada nodo conectado a 2 vecinos",
        "Cada nodo conectado a multiples",
        "Sin jefe, eventos via Software Bus"
    ]
    examples = [
        "FloripaSat, AAUSAT, UPSat",
        "OreSat (CAN), CANopen",
        "Raro en CubeSats",
        "Raro en CubeSats",
        "NASA cFS, ROS2"
    ]

    colors = ["#2F855A", "#805AD5", "#D69E2E", "#C53030", "#2C5282"]

    # Topologia 1: Estrella
    ax = axs[0]
    setup_ax(ax, (-3.5, 3.5), (-3.5, 3.5), titles[0], colors[0])
    box(ax, (0, 0), "OBC", fill=colors[0], text="white", w=1.4, h=1.0, fontsize=11)
    for ang in [0, 72, 144, 216, 288]:
        x = 2.3 * np.cos(np.radians(ang + 90))
        y = 2.3 * np.sin(np.radians(ang + 90))
        box(ax, (x, y), "sub", fill="#EEE", text=C["text"], w=1.0, h=0.7, fontsize=9)
        arrow(ax, (0, 0), (x * 0.7, y * 0.7), color="#444", lw=1.1, style="<->")

    # Topologia 2: Bus
    ax = axs[1]
    setup_ax(ax, (-3.5, 3.5), (-3.5, 3.5), titles[1], colors[1])
    ax.plot([-3, 3], [0, 0], color=C["border"], linewidth=3)
    for x in [-2.5, -1.0, 0.5, 2.0]:
        ax.plot([x, x], [0, 1.3], color=C["border"], linewidth=1.2)
        box(ax, (x, 1.7), "sub", fill=colors[1], text="white", w=1.0, h=0.7, fontsize=9)
    box(ax, (3, -0.8), "OBC", fill="white", text=C["text"], w=1.0, h=0.7, fontsize=9)
    ax.plot([3, 3], [0, -0.4], color=C["border"], linewidth=1.2)

    # Topologia 3: Anillo
    ax = axs[2]
    setup_ax(ax, (-3.5, 3.5), (-3.5, 3.5), titles[2], colors[2])
    for i in range(6):
        ang1 = i * 60 + 90
        ang2 = (i + 1) * 60 + 90
        x1, y1 = 2.5 * np.cos(np.radians(ang1)), 2.5 * np.sin(np.radians(ang1))
        x2, y2 = 2.5 * np.cos(np.radians(ang2)), 2.5 * np.sin(np.radians(ang2))
        ax.plot([x1, x2], [y1, y2], color=C["border"], linewidth=1.5)
    for i in range(6):
        ang = i * 60 + 90
        x = 2.5 * np.cos(np.radians(ang))
        y = 2.5 * np.sin(np.radians(ang))
        lbl = "OBC" if i == 0 else "sub"
        clr = colors[2] if i == 0 else "white"
        tc = "white" if i == 0 else C["text"]
        box(ax, (x, y), lbl, fill=clr, text=tc, w=0.9, h=0.6, fontsize=9)

    # Topologia 4: Malla
    ax = axs[3]
    setup_ax(ax, (-3.5, 3.5), (-3.5, 3.5), titles[3], colors[3])
    pts = []
    for ang in [0, 72, 144, 216, 288]:
        a = ang + 90
        pts.append((2.4 * np.cos(np.radians(a)), 2.4 * np.sin(np.radians(a))))
    # all pairs
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                    color="#cbd5e0", linewidth=0.8)
    for i, (x, y) in enumerate(pts):
        lbl = "OBC" if i == 0 else "sub"
        clr = colors[3] if i == 0 else "white"
        tc = "white" if i == 0 else C["text"]
        box(ax, (x, y), lbl, fill=clr, text=tc, w=0.9, h=0.6, fontsize=9)

    # Topologia 5: Distribuida (pub/sub)
    ax = axs[4]
    setup_ax(ax, (-3.5, 3.5), (-3.5, 3.5), titles[4], colors[4])
    # bus logico horizontal grueso
    ax.plot([-3, 3], [0, 0], color=colors[4], linewidth=6, alpha=0.5)
    ax.text(0, -0.4, "Software Bus (logico)", ha="center", fontsize=9,
            color=colors[4], weight="bold", style="italic")
    for x in [-2.3, -0.8, 0.8, 2.3]:
        ax.plot([x, x], [0, 1.2], color=colors[4], linewidth=1.2)
        box(ax, (x, 1.6), "app", fill=colors[4], text="white",
            w=0.9, h=0.6, fontsize=9)
    for x in [-1.5, 1.5]:
        ax.plot([x, x], [0, -1.2], color=colors[4], linewidth=1.2)
        box(ax, (x, -1.6), "app", fill="white", text=C["text"],
            w=0.9, h=0.6, fontsize=9)

    # Descripciones debajo
    for i in range(5):
        axs[i].text(0, -3.7, descs[i], ha="center", fontsize=10,
                    weight="bold", color=colors[i])
        axs[i].text(0, -4.3, examples[i], ha="center", fontsize=9,
                    style="italic", color=C["muted"])

    plt.suptitle("Las 5 topologias clasicas y donde aparecen en CubeSats",
                 fontsize=15, weight="bold", color=C["intisat"], y=1.02)
    plt.tight_layout()
    return save(fig, "fig03_topologias_clasicas.png")


# ============================================================================
# Fig 4 -- FloripaSat (estrella SPI)
# ============================================================================
def fig_floripasat():
    fig, ax = plt.subplots(figsize=(13, 8))
    setup_ax(ax, (0, 14), (0, 9),
             "FloripaSat-1: topologia ESTRELLA con bus SPI (4 modulos)",
             title_color=C["floripa"])

    # OBDH central
    box(ax, (7, 4.8), "OBDH\nMSP430 + FreeRTOS\nSPI MASTER",
        fill=C["floripa"], text="white", w=3.0, h=1.5, fontsize=10)

    # 4 esclavos en cruz
    perif = [
        ((2.5, 4.8), "EPS\nMSP430\nSPI slave"),
        ((11.5, 4.8), "Payload\nMSP430\nSPI slave"),
        ((7, 7.5), "TT&C Beacon\nMSP430\nSPI slave"),
        ((7, 2.0), "TT&C TC\nMSP430\nSPI slave"),
    ]
    for pos, lbl in perif:
        box(ax, pos, lbl, fill="#48BB78", text="white",
            w=2.6, h=1.3, fontsize=9.5)

    # Lineas SPI 4-hilos (CS por slave)
    for pos in [p[0] for p in perif]:
        ax.plot([7, pos[0]], [4.8, pos[1]],
                color=C["floripa"], linewidth=2.0)
        ax.text((7 + pos[0]) / 2, (4.8 + pos[1]) / 2 + 0.25,
                "SPI\n(CS+CLK+MOSI+MISO)",
                ha="center", fontsize=7.5, color=C["floripa"],
                style="italic",
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="#cbd5e0", lw=0.5))

    # Banda inferior con caracteristicas
    ax.add_patch(Rectangle((0.5, 0.2), 13, 0.85,
                           facecolor="#F0FFF4", edgecolor=C["floripa"],
                           linewidth=1.2))
    ax.text(7, 0.85,
            "Caracteristicas: SPI a 1 MHz, full-duplex, 1 CS por slave -> "
            "no broadcast, OBDH es punto unico de fallo",
            ha="center", fontsize=10, color=C["floripa"], weight="bold")
    ax.text(7, 0.45,
            "Ventaja: simplicidad de protocolo.  Desventaja: 4 CS lines + "
            "OBDH siempre activo. Hot swap imposible.",
            ha="center", fontsize=9, color=C["text"], style="italic")

    plt.tight_layout()
    return save(fig, "fig04_floripasat.png")


# ============================================================================
# Fig 5 -- OreSat (bus CAN)
# ============================================================================
def fig_oresat():
    fig, ax = plt.subplots(figsize=(14, 8))
    setup_ax(ax, (0, 16), (0, 9),
             "OreSat: topologia BUS multidrop con CAN + CANopen (CiA 301)",
             title_color=C["oresat"])

    # Bus CAN horizontal
    ax.plot([1, 15], [4.5, 4.5], color=C["oresat"], linewidth=5)
    ax.text(8, 4.05, "CAN bus diferencial (CAN_H + CAN_L)",
            ha="center", fontsize=10, weight="bold", color=C["oresat"])
    # terminadores
    for x in [1.0, 15.0]:
        ax.add_patch(Circle((x, 4.5), 0.15, facecolor=C["oresat"],
                            edgecolor="white", linewidth=2))
        ax.text(x, 3.7, "120 ohm", fontsize=8, ha="center",
                color=C["oresat"])

    # cards arriba y abajo
    cards_top = [
        (2.5, "C3 card\nLinux + OLAF\nCANopen master"),
        (5.5, "Battery\ncard\nSTM32 NMT"),
        (8.5, "Solar\ncard\nSTM32 NMT"),
        (11.5, "ADCS\ncard\nSTM32 NMT"),
        (14.0, "CFC\n(camara)\nSTM32 NMT"),
    ]
    for x, lbl in cards_top:
        box(ax, (x, 6.8), lbl, fill=C["oresat"], text="white",
            w=1.8, h=1.4, fontsize=8.5)
        ax.plot([x, x], [4.5, 6.1], color=C["oresat"], linewidth=1.5)

    cards_bot = [
        (4.0, "DxWiFi\ncard"),
        (7.0, "Star\nTracker"),
        (10.0, "GPS\ncard"),
        (13.0, "RW\n(opcional)"),
    ]
    for x, lbl in cards_bot:
        box(ax, (x, 2.4), lbl, fill="#9F7AEA", text="white",
            w=1.7, h=1.0, fontsize=9)
        ax.plot([x, x], [4.5, 2.9], color=C["oresat"], linewidth=1.5)

    # Nota inferior
    ax.add_patch(Rectangle((0.5, 0.3), 15, 0.85,
                           facecolor="#FAF5FF", edgecolor=C["oresat"],
                           linewidth=1.2))
    ax.text(8, 0.95,
            "CANopen NMT: cada card en {Init, Pre-Op, Operational, Stopped}. "
            "Mensajes priorizados por arbitraje en CAN-ID",
            ha="center", fontsize=10, color=C["oresat"], weight="bold")
    ax.text(8, 0.55,
            "Hot swap posible: una card puede caerse sin afectar el resto. "
            "C3 actua de master logico (no fisico).",
            ha="center", fontsize=9, color=C["text"], style="italic")

    plt.tight_layout()
    return save(fig, "fig05_oresat.png")


# ============================================================================
# Fig 6 -- AAUSAT (estrella I2C + CSP overlay)
# ============================================================================
def fig_aausat():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    setup_ax(ax, (0, 15), (0, 9.5),
             "AAUSAT: estrella I2C fisica + CSP (Cubesat Space Protocol) logico",
             title_color=C["aausat"])

    # OBC central
    box(ax, (7.5, 5.0), "OBC\nMSP430\nFreeRTOS\nCSP node 1",
        fill=C["aausat"], text="white", w=2.8, h=1.6, fontsize=10)

    perif = [
        ((2.5, 5.0),  "EPS\nCSP node 2"),
        ((12.5, 5.0), "ADCS\nCSP node 3"),
        ((7.5, 8.0),  "AIS RX\n(payload)\nCSP node 4"),
        ((7.5, 2.0),  "Radio UHF\nCSP node 5"),
    ]
    for pos, lbl in perif:
        box(ax, pos, lbl, fill="#FED7D7", text=C["text"],
            w=2.4, h=1.2, fontsize=9.5)

    # I2C fisico (lineas grises)
    for pos in [p[0] for p in perif]:
        ax.plot([7.5, pos[0]], [5.0, pos[1]],
                color="#A0AEC0", linewidth=1.5, linestyle="--")

    # Capa CSP overlay (banda translucida)
    ax.add_patch(Rectangle((0.5, 0.2), 14, 1.4,
                           facecolor="#FFF5F5",
                           edgecolor=C["aausat"], linewidth=1.5))
    ax.text(7.5, 1.3, "CAPA LOGICA: CSP (transport, 5 bit address + 6 bit port)",
            ha="center", fontsize=11, color=C["aausat"], weight="bold")
    ax.text(7.5, 0.85,
            "CAPA FISICA: I2C 100 kHz (dashed) -- pero CSP es agnostico, podria correr "
            "sobre CAN, UART o radio sin cambiar el codigo de aplicacion.",
            ha="center", fontsize=9, color=C["text"])
    ax.text(7.5, 0.45,
            "Ventaja: la misma app de tierra puede hablar con cualquier nodo via "
            "ruteo CSP. Encriptacion HMAC opcional.",
            ha="center", fontsize=9, color=C["text"], style="italic")

    plt.tight_layout()
    return save(fig, "fig06_aausat.png")


# ============================================================================
# Fig 7 -- UPSat (monolitica I2C simple)
# ============================================================================
def fig_upsat():
    fig, ax = plt.subplots(figsize=(13, 7))
    setup_ax(ax, (0, 13), (0, 8),
             "UPSat: ESTRELLA simple sobre I2C (sin capa de red)",
             title_color=C["upsat"])

    # OBC central
    box(ax, (6.5, 4.0), "OBC\nSTM32 + FreeRTOS\nI2C MASTER",
        fill=C["upsat"], text="white", w=3.0, h=1.5, fontsize=11)

    perif = [
        ((2.0, 4.0), "EPS"),
        ((11.0, 4.0), "INMS\n(payload)"),
        ((6.5, 6.5), "Radio\nUHF"),
        ((6.5, 1.7), "ADCS"),
    ]
    for pos, lbl in perif:
        box(ax, pos, lbl, fill="#B2DFDB", text=C["text"],
            w=2.0, h=1.1, fontsize=10)
        ax.plot([6.5, pos[0]], [4.0, pos[1]],
                color=C["upsat"], linewidth=2.0)
        ax.text((6.5 + pos[0]) / 2, (4.0 + pos[1]) / 2 + 0.15,
                "I2C", fontsize=9, color=C["upsat"], ha="center",
                weight="bold",
                bbox=dict(boxstyle="round,pad=0.12", fc="white",
                          ec="#cbd5e0", lw=0.5))

    # Nota
    ax.add_patch(Rectangle((0.5, 0.2), 12, 0.8,
                           facecolor="#E0F2F1", edgecolor=C["upsat"],
                           linewidth=1.2))
    ax.text(6.5, 0.85,
            "Sin CSP, sin CANopen: comandos directos en bytes via I2C 100 kHz",
            ha="center", fontsize=10, color=C["upsat"], weight="bold")
    ax.text(6.5, 0.45,
            "Es lo MAS simple posible. Codigo de aplicacion habla I2C raw. "
            "Suficiente para 4-5 subsistemas y vuelo de demostracion.",
            ha="center", fontsize=9, color=C["text"], style="italic")

    plt.tight_layout()
    return save(fig, "fig07_upsat.png")


# ============================================================================
# Fig 8 -- NASA cFS Software Bus (pub/sub)
# ============================================================================
def fig_cfs():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    setup_ax(ax, (0, 15), (0, 9),
             "NASA cFS: Software Bus pub/sub (topologia LOGICA distribuida)",
             title_color=C["cfs"])

    # Software Bus horizontal grueso
    ax.add_patch(Rectangle((1, 4.0), 13, 0.7,
                           facecolor=C["cfs"], edgecolor=C["border"],
                           linewidth=2))
    ax.text(7.5, 4.35, "Software Bus (cFE)",
            ha="center", fontsize=14, color="white", weight="bold")
    ax.text(7.5, 3.7,
            "publicacion/suscripcion por Message ID (MID)",
            ha="center", fontsize=10, color=C["cfs"], style="italic")

    # Apps publicadoras (arriba)
    pubs = [
        (2.5, "HK\napp\nMID 0x0001"),
        (5.5, "SCH\napp"),
        (8.5, "LC\napp\nMID 0x0002"),
        (11.5, "MM\n(Mode Mgr)\nMID 0x0003"),
    ]
    for x, lbl in pubs:
        box(ax, (x, 6.5), lbl, fill="#2C5282", text="white",
            w=1.8, h=1.4, fontsize=9)
        # flecha hacia abajo (publica)
        ax.add_patch(FancyArrowPatch((x, 5.8), (x, 4.75),
                                     arrowstyle="-|>", mutation_scale=14,
                                     color="#2C5282", linewidth=1.5))

    # Apps suscriptoras (abajo)
    subs = [
        (3.5, "DS\n(data store)\nsub: 0x0001"),
        (7.5, "CFDP\n(downlink)"),
        (11.5, "HS\n(health/safety)\nsub: 0x0002, 0x0003"),
    ]
    for x, lbl in subs:
        box(ax, (x, 1.7), lbl, fill="#C53030", text="white",
            w=2.0, h=1.4, fontsize=9)
        ax.add_patch(FancyArrowPatch((x, 3.95), (x, 2.4),
                                     arrowstyle="-|>", mutation_scale=14,
                                     color="#C53030", linewidth=1.5))

    plt.tight_layout()
    return save(fig, "fig08_cfs.png")


# ============================================================================
# Fig 9 -- F' Ports tipados
# ============================================================================
def fig_fprime():
    fig, ax = plt.subplots(figsize=(14, 7))
    setup_ax(ax, (0, 15), (0, 8),
             "NASA F': topologia COMPILE-TIME con ports tipados (no runtime)",
             title_color=C["fprime"])

    components = [
        (2.0, "GPS\ncomponent"),
        (5.5, "Mode Manager\n(state machine)"),
        (9.0, "Telemetry\ncomponent"),
        (12.5, "Comm\n(downlink)"),
    ]
    for x, lbl in components:
        clr = C["fprime"] if "Mode" in lbl else "#319795"
        box(ax, (x, 4.5), lbl, fill=clr, text="white",
            w=2.6, h=1.5, fontsize=10)

    # ports tipados (lineas entre components)
    for i in range(3):
        x1 = components[i][0] + 1.3
        x2 = components[i + 1][0] - 1.3
        ax.add_patch(FancyArrowPatch((x1, 4.5), (x2, 4.5),
                                     arrowstyle="<->", mutation_scale=14,
                                     color="#444", linewidth=2))
        ax.text((x1 + x2) / 2, 5.1, "typed port",
                ha="center", fontsize=9, style="italic", color="#666")
        # tipo concreto bajo el port
        types = ["Tlm.Gps", "Cmd.Mode", "Tlm.Pkt"]
        ax.text((x1 + x2) / 2, 3.9, types[i],
                ha="center", fontsize=9, color="#666", family="monospace")

    # Nota top
    ax.add_patch(Rectangle((0.5, 6.7), 14, 0.7,
                           facecolor="#EBF8FF", edgecolor=C["fprime"],
                           linewidth=1.2))
    ax.text(7.5, 7.05,
            "Topologia descrita en FPP, compilada por fpp-to-cpp -> "
            "verificacion estatica de tipos en build time",
            ha="center", fontsize=11, color=C["fprime"], weight="bold")

    # Nota inferior
    ax.add_patch(Rectangle((0.5, 0.4), 14, 1.6,
                           facecolor="#F8FAFC", edgecolor="#666",
                           linewidth=1))
    ax.text(7.5, 1.55,
            "Ventaja vs cFS pub/sub: errores de tipo de mensaje se detectan al COMPILAR, no en orbita.",
            ha="center", fontsize=10, color=C["text"], weight="bold")
    ax.text(7.5, 1.05,
            "Desventaja: agregar un nuevo subscriber requiere recompilar todo. Menos flexible en runtime.",
            ha="center", fontsize=9, color=C["text"], style="italic")
    ax.text(7.5, 0.65,
            "Misiones: MarCO (2018), Ingenuity (2021-2024, 72 vuelos en Marte), ASTERIA, LCRD",
            ha="center", fontsize=9, color=C["fprime"], style="italic")

    plt.tight_layout()
    return save(fig, "fig09_fprime.png")


# ============================================================================
# Fig 10 -- Matriz comparativa
# ============================================================================
def fig_matriz():
    rows = [
        ("FloripaSat",       C["floripa"]),
        ("OreSat",           C["oresat"]),
        ("AAUSAT",           C["aausat"]),
        ("UPSat",            C["upsat"]),
        ("NASA cFS",         C["cfs"]),
        ("NASA F'",          C["fprime"]),
        ("INTISAT (target)", C["intisat"]),
    ]
    cols = ["Topologia", "Bus fisico", "Capa red", "Control",
            "Hot swap?", "Falla aislada?"]
    cells = [
        ["Estrella",        "SPI",          "(ninguna)",   "Centralizado",
         "No",  "Parcial"],
        ["Bus multidrop",   "CAN 1 Mbps",   "CANopen",     "Centralizado",
         "Si",  "Si"],
        ["Estrella",        "I2C",          "CSP",         "Centralizado",
         "No",  "Si (CSP)"],
        ["Estrella",        "I2C",          "(ninguna)",   "Centralizado",
         "No",  "No"],
        ["Pub/Sub logico",  "depende",      "SB (cFE)",    "Distribuido",
         "Si",  "Si"],
        ["Ports tipados",   "depende",      "FPP",         "Compile-time",
         "No",  "Si"],
        ["Estrella",        "I2C 400 kHz",  "(CSP opcional)", "Centralizado",
         "Limitado", "Parcial"],
    ]

    fig, ax = plt.subplots(figsize=(15, 8))
    setup_ax(ax, (0, 16), (0, 10),
             "Matriz comparativa de topologias y control")

    cw, ch = 2.1, 0.95
    x0, y0 = 2.0, 1.0

    # Cabeceras col
    for j, col in enumerate(cols):
        ax.add_patch(Rectangle((x0 + j * cw, y0 + len(rows) * ch),
                               cw, ch, facecolor=C["intisat"],
                               edgecolor="white"))
        ax.text(x0 + j * cw + cw / 2, y0 + len(rows) * ch + ch / 2,
                col, ha="center", va="center", color="white",
                fontsize=10, weight="bold")

    # Filas
    for i, (name, color) in enumerate(rows):
        yi = y0 + (len(rows) - 1 - i) * ch
        ax.add_patch(Rectangle((x0 - cw, yi), cw, ch,
                               facecolor=color, edgecolor="white", lw=1.2))
        ax.text(x0 - cw / 2, yi + ch / 2, name,
                ha="center", va="center", color="white",
                fontsize=10, weight="bold")
        for j, val in enumerate(cells[i]):
            x = x0 + j * cw
            highlight = (name == "INTISAT (target)")
            facec = "#FFFBE6" if highlight else ("#F7FAFC" if (i + j) % 2 == 0 else "white")
            ax.add_patch(Rectangle((x, yi), cw, ch,
                                   facecolor=facec, edgecolor="#cbd5e0",
                                   lw=0.8))
            ax.text(x + cw / 2, yi + ch / 2, val,
                    ha="center", va="center", fontsize=9,
                    weight="bold" if highlight else "normal",
                    color=C["text"])

    # nota
    ax.text(8, 0.4,
            "INTISAT replica el patron mas simple (estrella + I2C) pero deja la puerta abierta a CSP en v2.",
            ha="center", fontsize=9, style="italic", color=C["muted"])

    plt.tight_layout()
    return save(fig, "fig10_matriz.png")


# ============================================================================
# Fig 11 -- Propuesta INTISAT
# ============================================================================
def fig_intisat():
    fig, ax = plt.subplots(figsize=(13, 8.5))
    setup_ax(ax, (0, 14), (0, 9),
             "Topologia propuesta para INTISAT (1U): estrella I2C centrada en CM5",
             title_color=C["intisat"])

    # CM5 central (mas grande)
    box(ax, (7, 5), "Raspberry Pi CM5\n(OBC + payload)\nLinux + Python\nI2C MASTER",
        fill=C["intisat"], text="white", w=3.4, h=1.8, fontsize=11)

    # subsistemas alrededor
    perif = [
        ((2.0, 5),  "EPS\nMSP430\nADC + MPPT",   "#2F855A"),
        ((12.0, 5), "Radio UHF\n+ S band",        "#C53030"),
        ((7, 8.0),  "ADCS\nmagnetorquers",        "#7D3C98"),
        ((7, 2.0),  "Sensores T degC\n(housekeep)", "#319795"),
    ]
    for pos, lbl, color in perif:
        box(ax, pos, lbl, fill=color, text="white",
            w=2.4, h=1.2, fontsize=10)
        ax.plot([7, pos[0]], [5, pos[1]],
                color=C["intisat"], linewidth=2.0)
        midx = (7 + pos[0]) / 2
        midy = (5 + pos[1]) / 2
        ax.text(midx, midy + 0.25,
                "I2C 400 kHz",
                ha="center", fontsize=8.5, color=C["intisat"],
                weight="bold", style="italic",
                bbox=dict(boxstyle="round,pad=0.12", fc="white",
                          ec="#cbd5e0", lw=0.5))

    # Banda inferior con caracteristicas
    ax.add_patch(Rectangle((0.5, 0.2), 13, 0.85,
                           facecolor="#EBF8FF", edgecolor=C["intisat"],
                           linewidth=1.2))
    ax.text(7, 0.85,
            "Direcciones I2C: EPS=0x10, ADCS=0x20, Radio=0x30, Sensores=0x48..0x4F",
            ha="center", fontsize=10, color=C["intisat"], weight="bold")
    ax.text(7, 0.45,
            "Capa logica: telecomandos ECSS-E-ST-70-41 simplificados, paquetes binarios con CRC16",
            ha="center", fontsize=9, color=C["text"], style="italic")

    plt.tight_layout()
    return save(fig, "fig11_intisat.png")


# ============================================================================
# Fig 12 -- Flujo de control en el tiempo
# ============================================================================
def fig_flujo_control():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(7, 8.5, "Flujo temporal de un telecomando: tierra -> EPS",
            ha="center", fontsize=14, weight="bold", color=C["intisat"])

    # Carriles horizontales (lanes)
    lanes = [
        (7.0, "Tierra (estacion)",  "#34495E"),
        (5.7, "Radio UHF",          "#9B59B6"),
        (4.4, "OBC (CM5)",          C["intisat"]),
        (3.1, "Bus I2C",            "#A0AEC0"),
        (1.8, "Subsistema EPS",     "#2F855A"),
    ]
    for y, name, color in lanes:
        ax.plot([1.5, 13], [y, y], color=color, linewidth=2, alpha=0.4)
        ax.text(1.4, y, name, ha="right", va="center", fontsize=10,
                weight="bold", color=color)

    # Eventos (x, y, label, color)
    events = [
        (2.0, 7.0, "Comando\nTC", "#34495E"),
        (3.5, 5.7, "Decodifica\nAX.25", "#9B59B6"),
        (5.0, 4.4, "Valida +\nrutea", C["intisat"]),
        (6.5, 3.1, "Escribe\nI2C", "#A0AEC0"),
        (8.0, 1.8, "Ejecuta\ncomando", "#2F855A"),
        (9.5, 3.1, "Respuesta\nI2C", "#A0AEC0"),
        (11.0, 4.4, "Telemetria\nasync", C["intisat"]),
        (12.5, 5.7, "Modula\nbeacon", "#9B59B6"),
    ]
    for x, y, lbl, color in events:
        box(ax, (x, y), lbl, fill=color, text="white", w=1.0, h=0.6,
            fontsize=8.5)

    # Flechas entre eventos
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)]
    for i, j in edges:
        x1, y1 = events[i][0], events[i][1]
        x2, y2 = events[j][0], events[j][1]
        ax.add_patch(FancyArrowPatch((x1 + 0.5, y1), (x2 - 0.5, y2),
                                     arrowstyle="-|>", mutation_scale=12,
                                     color="#444", linewidth=1.3,
                                     connectionstyle="arc3,rad=0"))

    # Tiempo total
    ax.text(7, 0.5,
            "Tiempo total tipico: ~50-200 ms para TC simple. Telemetria asincrona via beacon.",
            ha="center", fontsize=11, style="italic", color=C["intisat"],
            bbox=dict(boxstyle="round,pad=0.3", fc="#EBF8FF",
                      ec=C["intisat"], lw=1))

    plt.tight_layout()
    return save(fig, "fig12_flujo_control.png")


if __name__ == "__main__":
    for fn in (fig_capas, fig_buses, fig_topologias, fig_floripasat,
               fig_oresat, fig_aausat, fig_upsat, fig_cfs, fig_fprime,
               fig_matriz, fig_intisat, fig_flujo_control):
        p = fn()
        print(f"OK -> {p.name}  ({p.stat().st_size // 1024} kB)")
