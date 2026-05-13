"""Diagramas comparativos para el manual M13.

Compara FloripaSat, OreSat, AAUSAT, UPSat, NASA cFS y F' frente al
INTISAT. Genera 7 figuras:
  fig01_timeline.png      : timeline de misiones open-source
  fig02_matriz.png        : matriz comparativa (proyectos x dimensiones)
  fig03_floripasat.png    : arquitectura distribuida FloripaSat (4 modulos por SPI)
  fig04_oresat.png        : arquitectura cards / CANopen de OreSat
  fig05_cfs.png           : stack de NASA cFS (cFE + apps + OSAL + PSP)
  fig06_fprime.png        : workflow F' components -> FPP -> generated code
  fig07_recomendacion.png : que adopta INTISAT de cada uno
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "figuras" / "m13"
OUT.mkdir(parents=True, exist_ok=True)

C = {
    "intisat":   "#1A365D",
    "floripa":   "#2F855A",
    "oresat":    "#805AD5",
    "aausat":    "#C53030",
    "upsat":     "#319795",
    "cfs":       "#D69E2E",
    "fprime":    "#2C5282",
    "muted":     "#718096",
    "border":    "#2D3748",
    "text":      "#1A202C",
    "ok":        "#2F855A",
    "warn":      "#C58F00",
    "off":       "#CBD5E0",
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
          label_offset=(0, 0.12), fontsize=8, ls="-", lw=1.3):
    style = f"arc3,rad={rad}"
    a = FancyArrowPatch(
        p1, p2,
        arrowstyle="-|>", mutation_scale=12,
        connectionstyle=style, color=color, linewidth=lw, linestyle=ls,
    )
    ax.add_patch(a)
    if label:
        mx = (p1[0] + p2[0]) / 2 + label_offset[0]
        my = (p1[1] + p2[1]) / 2 + label_offset[1]
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
        ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - 0.35, title,
                ha="center", fontsize=14, weight="bold",
                color=title_color or C["intisat"])


def save(fig, name):
    out = OUT / name
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# ============================================================================
# Fig 1 -- Timeline de misiones open-source
# ============================================================================
def fig_timeline():
    fig, ax = plt.subplots(figsize=(14, 7))
    setup_ax(ax, (2010, 2027), (0, 8), "Timeline de CubeSats open-source de referencia")

    # eje horizontal
    ax.plot([2011, 2026.5], [3.5, 3.5], color="#444", linewidth=1.5)
    for y in range(2011, 2027):
        ax.plot([y, y], [3.45, 3.55], color="#444", linewidth=0.8)
        ax.text(y, 3.25, str(y), ha="center", fontsize=8, color="#666")

    # eventos: (year_month, label, color, y_offset, year_decimal)
    events = [
        (2013.15, "AAUSAT-3\nlanzamiento", C["aausat"],  5.5),
        (2016.32, "AAUSAT-4\nlanzamiento", C["aausat"],  6.5),
        (2017.30, "UPSat\nlanzamiento\n(primer CubeSat 100% open)", C["upsat"], 7.0),
        (2018.42, "MarCO-A/B (NASA, F')\nflyby Marte", C["fprime"], 5.5),
        (2019.96, "FloripaSat-1\nlanzamiento (1U)", C["floripa"], 6.5),
        (2021.30, "Ingenuity (NASA, F')\n1er vuelo motor en Marte", C["fprime"], 5.5),
        (2022.40, "OreSat0 (0.5U)\nlanzamiento", C["oresat"], 7.0),
        (2023.01, "GOLDS-UFSC /\nFloripaSat-2 (2U)", C["floripa"], 5.5),
        (2024.20, "OreSat0.5 (1U)\nlanzamiento", C["oresat"], 6.5),
        (2026.50, "INTISAT\n(en diseno)", C["intisat"], 1.5),
    ]
    for x, label, color, yo in events:
        ax.plot([x, x], [3.5, yo - 0.55 if yo > 3.5 else yo + 0.55],
                color=color, linewidth=1.2, linestyle="--")
        box(ax, (x, yo), label, fill=color, text="white", w=2.5, h=1.0,
            fontsize=8.5, weight="bold")

    # bandas verticales para frameworks
    ax.add_patch(Rectangle((2015, 0.5), 11.5, 0.4, facecolor="#FFFBE6",
                           edgecolor=C["cfs"], lw=0.8))
    ax.text(2020.5, 0.7, "NASA cFS open (2015): LRO, MMS, GPM, Lunar IceCube, Artemis",
            ha="center", fontsize=8.5, color=C["cfs"], weight="bold")

    ax.add_patch(Rectangle((2017, 0.05), 9.5, 0.4, facecolor="#EBF8FF",
                           edgecolor=C["fprime"], lw=0.8))
    ax.text(2021.75, 0.25, "NASA F' open (2017): MarCO, Ingenuity, ASTERIA, LCRD",
            ha="center", fontsize=8.5, color=C["fprime"], weight="bold")

    plt.tight_layout()
    return save(fig, "fig01_timeline.png")


# ============================================================================
# Fig 2 -- Matriz comparativa (proyectos x dimensiones)
# ============================================================================
def fig_matriz():
    # filas: proyectos. columnas: dimensiones.
    rows = [
        ("FloripaSat",       C["floripa"]),
        ("OreSat",           C["oresat"]),
        ("AAUSAT",           C["aausat"]),
        ("UPSat",            C["upsat"]),
        ("NASA cFS",         C["cfs"]),
        ("NASA F'",          C["fprime"]),
        ("INTISAT (target)", C["intisat"]),
    ]
    cols = ["Arquitectura", "OS / runtime", "Bus interno",
            "Lenguaje", "FSM", "Open?"]
    cells = [
        ["Distribuida\n4 modulos",  "FreeRTOS\nbare metal",  "SPI",     "C",      "FSM en C\n(plana)",    "Si"],
        ["Cards\nCANopen",          "Linux\n(Yocto)",         "CAN",     "Python", "StateMachine\nexplicita", "Si"],
        ["Monolitica",              "FreeRTOS",               "I2C",     "C",      "HSMM\n(jerarquica)",   "Parcial"],
        ["Monolitica",              "FreeRTOS",               "I2C",     "C",      "Implicita",            "Si"],
        ["Componentes\n+ pub/sub",  "VxWorks/RTEMS\nLinux",   "Software\nBus",   "C",      "Mode\nManager\napp",    "Si"],
        ["Componentes\n+ ports",    "Linux\nVxWorks/RTEMS",   "Ports\nFPP",  "C++",    "SMs\ngeneradas\ndesde FPP", "Si"],
        ["Monolitica\npayload-side", "Linux (RPi 5)",         "I2C\n(con OBC)", "Python", "STATE_*\nen daemon.py", "Si"],
    ]

    fig, ax = plt.subplots(figsize=(14, 8))
    setup_ax(ax, (0, 15), (0, 10), "Matriz comparativa: arquitecturas de CubeSat open-source")

    cw, ch = 2.0, 0.95
    x0, y0 = 2.0, 1.0  # esquina inferior

    # cabeceras de columna
    for j, col in enumerate(cols):
        ax.add_patch(Rectangle((x0 + j * cw, y0 + len(rows) * ch),
                               cw, ch, facecolor=C["intisat"], edgecolor="white"))
        ax.text(x0 + j * cw + cw / 2, y0 + len(rows) * ch + ch / 2,
                col, ha="center", va="center", color="white",
                fontsize=10, weight="bold")

    # filas
    for i, (name, color) in enumerate(rows):
        yi = y0 + (len(rows) - 1 - i) * ch
        # etiqueta de fila
        ax.add_patch(Rectangle((x0 - cw, yi), cw, ch,
                               facecolor=color, edgecolor="white", lw=1.2))
        ax.text(x0 - cw / 2, yi + ch / 2, name,
                ha="center", va="center", color="white",
                fontsize=10, weight="bold")
        # celdas
        for j, val in enumerate(cells[i]):
            x = x0 + j * cw
            highlight = (name == "INTISAT (target)")
            facec = "#FFFBE6" if highlight else ("#F7FAFC" if (i + j) % 2 == 0 else "white")
            ax.add_patch(Rectangle((x, yi), cw, ch,
                                   facecolor=facec, edgecolor="#cbd5e0", lw=0.8))
            ax.text(x + cw / 2, yi + ch / 2, val,
                    ha="center", va="center", fontsize=8.5,
                    weight="bold" if highlight else "normal",
                    color=C["text"])

    # nota inferior
    ax.text(7.5, 0.35,
            "INTISAT ya define payload-side; quedan abiertas las decisiones de OBC, bus inter-subsistema y framework",
            ha="center", fontsize=9, style="italic", color=C["muted"])

    plt.tight_layout()
    return save(fig, "fig02_matriz.png")


# ============================================================================
# Fig 3 -- Arquitectura distribuida FloripaSat
# ============================================================================
def fig_floripasat():
    fig, ax = plt.subplots(figsize=(13, 7.5))
    setup_ax(ax, (0, 14), (0, 9), "FloripaSat-1: 4 modulos independientes, bus SPI",
             title_color=C["floripa"])

    # 4 modulos en cruz, OBDH al centro
    box(ax, (7, 5.5), "OBDH\nMSP430 + FreeRTOS\n(coordinador)",
        fill=C["floripa"], text="white", w=3.0, h=1.3, fontsize=10)
    box(ax, (2.5, 5.5), "EPS\nMSP430 bare metal",
        fill="#48BB78", text="white", w=2.8, h=1.1, fontsize=10)
    box(ax, (11.5, 5.5), "Payload\n(VHF/UHF + experimentos)",
        fill="#48BB78", text="white", w=2.8, h=1.1, fontsize=10)
    box(ax, (7, 8.0), "TT&C - Beacon\nMSP430",
        fill="#48BB78", text="white", w=2.8, h=1.0, fontsize=10)
    box(ax, (7, 2.8), "TT&C - Telecomando\nMSP430",
        fill="#48BB78", text="white", w=2.8, h=1.0, fontsize=10)

    # flechas SPI bidireccionales
    for p in [(2.5, 5.5), (11.5, 5.5), (7, 8.0), (7, 2.8)]:
        ax.add_patch(FancyArrowPatch(
            (7, 5.5), p,
            arrowstyle="<->", mutation_scale=14,
            color="#444", linewidth=1.5,
        ))

    # etiqueta SPI
    ax.text(4.7, 5.85, "SPI", fontsize=10, weight="bold",
            color="#444", bbox=dict(boxstyle="round,pad=0.2",
                                    fc="white", ec="#888"))
    ax.text(9.3, 5.85, "SPI", fontsize=10, weight="bold",
            color="#444", bbox=dict(boxstyle="round,pad=0.2",
                                    fc="white", ec="#888"))
    ax.text(7.5, 6.7, "SPI", fontsize=10, weight="bold", color="#444",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888"))
    ax.text(7.5, 4.2, "SPI", fontsize=10, weight="bold", color="#444",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888"))

    # FSM por modulo en banda inferior
    ax.add_patch(Rectangle((0.5, 0.3), 13, 1.2,
                           facecolor="#F0FFF4", edgecolor=C["floripa"], lw=1.0))
    ax.text(7, 1.15, "Modos FSM en OBDH (FreeRTOS task): Survival -> Normal -> Hibernation -> Shutdown",
            ha="center", fontsize=10, weight="bold", color=C["floripa"])
    ax.text(7, 0.6,
            "Cada modulo tiene SU propio repo en GitHub. Documentacion HW/FW en LaTeX en el mismo repo. "
            "Comunicacion: paquetes NGHam.",
            ha="center", fontsize=9, color=C["text"])

    plt.tight_layout()
    return save(fig, "fig03_floripasat.png")


# ============================================================================
# Fig 4 -- Arquitectura cards / CANopen de OreSat
# ============================================================================
def fig_oresat():
    fig, ax = plt.subplots(figsize=(14, 8))
    setup_ax(ax, (0, 16), (0, 10), "OreSat: cards independientes sobre bus CAN (CANopen)",
             title_color=C["oresat"])

    # bus CAN horizontal
    ax.plot([1.5, 14.5], [5.0, 5.0], color="#444", linewidth=4)
    ax.text(8, 4.5, "CAN bus (CANopen, CiA 301)",
            ha="center", fontsize=11, weight="bold", color="#444")

    # 6 cards arriba y abajo del bus
    cards_top = [
        (2.5, "Solar\ncard"),
        (5.5, "Battery\ncard"),
        (8.5, "ADCS\ncard"),
        (11.5, "Star\nTracker"),
        (14.0, "CFC\n(camara)"),
    ]
    cards_bot = [
        (3.0, "C3 card\n(Linux + OLAF)\nLinux + Python\nCANopen master\nradio UHF"),
        (8.0, "DxWiFi\ncard"),
        (12.5, "RW\ncard\n(opcional)"),
    ]

    for x, label in cards_top:
        box(ax, (x, 7.5), label, fill=C["oresat"], text="white",
            w=1.8, h=1.3, fontsize=9)
        ax.add_patch(FancyArrowPatch(
            (x, 6.8), (x, 5.1),
            arrowstyle="<->", mutation_scale=10,
            color="#666", linewidth=1.1,
        ))

    for x, label in cards_bot:
        if "C3" in label:
            box(ax, (x, 2.5), label, fill=C["intisat"], text="white",
                w=2.5, h=2.0, fontsize=9)
            ax.add_patch(FancyArrowPatch(
                (x, 3.5), (x, 4.9),
                arrowstyle="<->", mutation_scale=10,
                color="#666", linewidth=1.4,
            ))
        else:
            box(ax, (x, 2.8), label, fill="#9F7AEA", text="white",
                w=1.8, h=1.2, fontsize=9)
            ax.add_patch(FancyArrowPatch(
                (x, 3.4), (x, 4.9),
                arrowstyle="<->", mutation_scale=10,
                color="#666", linewidth=1.1,
            ))

    # nota
    ax.add_patch(Rectangle((0.5, 0.3), 15, 0.9,
                           facecolor="#FAF5FF", edgecolor=C["oresat"], lw=1.0))
    ax.text(8, 0.95, "Cada card = STM32 + OD (Object Dictionary) CANopen estandar",
            ha="center", fontsize=10, weight="bold", color=C["oresat"])
    ax.text(8, 0.55,
            "C3 corre Linux + Python (OLAF). El resto de cards son STM32 bare metal. "
            "El C3 actua como master CANopen.",
            ha="center", fontsize=9, color=C["text"])

    plt.tight_layout()
    return save(fig, "fig04_oresat.png")


# ============================================================================
# Fig 5 -- Stack de NASA cFS
# ============================================================================
def fig_cfs():
    fig, ax = plt.subplots(figsize=(13, 8.5))
    setup_ax(ax, (0, 14), (0, 10), "NASA cFS: stack de capas + apps modulares",
             title_color=C["cfs"])

    # Capa hardware
    box(ax, (7, 0.8), "Hardware (procesador + I/O)",
        fill="#A0AEC0", text="white", w=12, h=0.9, fontsize=11)
    # Capa OS
    box(ax, (7, 1.9), "RTOS / OS  (VxWorks  |  RTEMS  |  Linux  |  FreeRTOS)",
        fill="#718096", text="white", w=12, h=0.9, fontsize=11)
    # PSP
    box(ax, (7, 3.0), "PSP  (Platform Support Package)",
        fill="#9F7AEA", text="white", w=12, h=0.9, fontsize=11)
    # OSAL
    box(ax, (7, 4.1), "OSAL  (OS Abstraction Layer)",
        fill="#805AD5", text="white", w=12, h=0.9, fontsize=11)
    # cFE
    box(ax, (7, 5.2), "cFE  (Core Flight Executive: ES, SB, EVS, TIME, TBL)",
        fill=C["cfs"], text="white", w=12, h=0.9, fontsize=11)

    # Apps modulares
    apps_y = 7.5
    apps = [
        ("HK\nHousekeeping",   "#2C5282"),
        ("SCH\nScheduler",     "#2C5282"),
        ("LC\nLimit Checker",  "#C53030"),
        ("SC\nStored Cmds",    "#2C5282"),
        ("DS\nData Storage",   "#319795"),
        ("CFDP\nFile transfer", "#319795"),
        ("HS\nHealth & Safety", "#C53030"),
        ("MM (custom)\nMode Manager",  C["intisat"]),
    ]
    for i, (label, c) in enumerate(apps):
        x = 1.0 + i * 1.625
        box(ax, (x, apps_y), label, fill=c, text="white",
            w=1.4, h=1.1, fontsize=8, weight="bold")
        # flecha hacia SB (en cFE)
        ax.add_patch(FancyArrowPatch(
            (x, apps_y - 0.55), (x, 5.65),
            arrowstyle="<->", mutation_scale=10,
            color="#666", linewidth=1.0,
        ))

    # leyenda
    ax.text(7, 9.05, "Apps modulares (intercambiables, comunican via Software Bus)",
            ha="center", fontsize=10, weight="bold", color=C["text"])

    plt.tight_layout()
    return save(fig, "fig05_cfs.png")


# ============================================================================
# Fig 6 -- F' workflow
# ============================================================================
def fig_fprime():
    fig, ax = plt.subplots(figsize=(14, 7.5))
    setup_ax(ax, (0, 15), (0, 9), "NASA F': FPP -> codigo generado -> componentes conectados",
             title_color=C["fprime"])

    # Source FPP
    box(ax, (2.0, 7.0), ".fpp\n(FPP DSL)\n- components\n- ports\n- state machines",
        fill="#EBF8FF", text=C["fprime"], w=2.6, h=1.8, fontsize=9, weight="normal")

    # Compiler
    box(ax, (5.5, 7.0), "fpp-to-cpp\n(compiler)",
        fill="#2C5282", text="white", w=2.4, h=1.2, fontsize=10)

    # Generated code
    box(ax, (9.0, 7.0), "C++ stubs\nserializacion\nlogica de SM",
        fill="#D69E2E", text="white", w=2.4, h=1.5, fontsize=9)

    # User code
    box(ax, (12.5, 7.0), "Logica de\nusuario (C++)",
        fill="#2F855A", text="white", w=2.4, h=1.2, fontsize=10)

    # Flechas del pipeline
    arrow(ax, (3.3, 7.0), (4.3, 7.0), None)
    arrow(ax, (6.7, 7.0), (7.8, 7.0), None)
    arrow(ax, (10.2, 7.0), (11.3, 7.0), None)

    # Topologia de componentes (abajo)
    y_comp = 3.5
    components = [
        (2.0, "Sensor\ncomponent"),
        (5.5, "Mode\nManager\n(state machine)"),
        (9.0, "Telemetry\ncomponent"),
        (12.5, "Comm\ncomponent"),
    ]
    for x, label in components:
        weight = "bold"
        if "Mode" in label:
            box(ax, (x, y_comp), label, fill=C["fprime"], text="white",
                w=2.4, h=1.5, fontsize=9.5)
        else:
            box(ax, (x, y_comp), label, fill="#319795", text="white",
                w=2.4, h=1.3, fontsize=10)

    # ports (lineas entre components)
    for i in range(3):
        x1 = components[i][0] + 1.2
        x2 = components[i + 1][0] - 1.2
        ax.add_patch(FancyArrowPatch(
            (x1, y_comp), (x2, y_comp),
            arrowstyle="<->", mutation_scale=12,
            color="#444", linewidth=1.3,
        ))
        ax.text((x1 + x2) / 2, y_comp + 0.4, "port",
                ha="center", fontsize=8, style="italic", color="#666")

    # banda inferior
    ax.add_patch(Rectangle((0.5, 0.3), 14, 1.4,
                           facecolor="#EBF8FF", edgecolor=C["fprime"], lw=1.0))
    ax.text(7.5, 1.4, "Misiones que usaron F':",
            ha="center", fontsize=10, weight="bold", color=C["fprime"])
    ax.text(7.5, 0.85,
            "MarCO-A/B (2018, 1ros CubeSats a Marte)  |  Ingenuity (2021-2024, 72 vuelos en Marte)  |  "
            "ASTERIA  |  LCRD  |  NEA Scout",
            ha="center", fontsize=9, color=C["text"])

    plt.tight_layout()
    return save(fig, "fig06_fprime.png")


# ============================================================================
# Fig 7 -- Recomendaciones: que adopta INTISAT de cada uno
# ============================================================================
def fig_recomendacion():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    setup_ax(ax, (0, 15), (0, 10), "Recomendaciones para INTISAT: que adoptar de cada referencia",
             title_color=C["intisat"])

    # INTISAT al centro
    box(ax, (7.5, 5.0), "INTISAT\n(target architecture)",
        fill=C["intisat"], text="white", w=3.5, h=1.4, fontsize=12, weight="bold")

    # Cards flotando alrededor con flechas entrando
    refs = [
        (1.5,  8.0, "De FloripaSat\n- Repo por subsistema\n- LaTeX doc en repo\n- FreeRTOS task por modulo", C["floripa"]),
        (7.5,  8.5, "De AAUSAT\n- Operations Concept doc\n- HSMM jerarquica\n- CSP como protocolo", C["aausat"]),
        (13.5, 8.0, "De OreSat\n- Python en OBC (no RTOS)\n- Object Dictionary explicito\n- Matriz modos x cards", C["oresat"]),
        (1.5,  2.0, "De UPSat\n- Github org publico\n- Wiki con decisiones\n- ECSS packet TM/TC", C["upsat"]),
        (7.5,  1.7, "De NASA cFS\n- Pub/sub Software Bus\n- App Mode Manager separada\n- App Limit Checker", C["cfs"]),
        (13.5, 2.0, "De NASA F'\n- Componentes con ports\n- FSM declarativa\n- Topologia separada del codigo", C["fprime"]),
    ]
    for x, y, label, color in refs:
        box(ax, (x, y), label, fill=color, text="white",
            w=2.9, h=1.7, fontsize=8.5, weight="normal")
        ax.add_patch(FancyArrowPatch(
            (x, y), (7.5 + (x - 7.5) * 0.15, 5.0 + (y - 5.0) * 0.15),
            arrowstyle="-|>", mutation_scale=14,
            color=color, linewidth=1.5,
        ))

    # nota inferior
    ax.text(7.5, 0.4,
            "Estrategia: tomar lo mejor de cada uno, pero NO copiar arquitectura completa. "
            "INTISAT empieza simple (Python + I2C) y modulariza segun aprende.",
            ha="center", fontsize=10, style="italic", color=C["intisat"],
            bbox=dict(boxstyle="round,pad=0.3", fc="#EBF8FF",
                      ec=C["intisat"], lw=1.2))

    plt.tight_layout()
    return save(fig, "fig07_recomendacion.png")


if __name__ == "__main__":
    for fn in (fig_timeline, fig_matriz, fig_floripasat, fig_oresat,
               fig_cfs, fig_fprime, fig_recomendacion):
        p = fn()
        print(f"OK -> {p.name}  ({p.stat().st_size // 1024} kB)")
