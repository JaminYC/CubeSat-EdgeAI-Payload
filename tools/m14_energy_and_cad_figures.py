"""Figuras para el manual M14: analisis energetico + CAD conceptual
del payload de microscopia FPM del INTISAT.

Salidas en Documentos de Referencia/figuras/m14/:
  fig01_potencia_estado.png   : barras de potencia por estado del payload
  fig02_duty_cycle.png        : duty cycle por estado en una orbita LEO
  fig03_energia_orbita.png    : energia consumida (Wh) por estado/orbita
  fig04_timeline_orbita.png   : timeline de 90 min con potencia instantanea
  fig05_balance_energetico.png: balance generacion vs consumo (orbital)
  fig06_cad_vista_superior.png: vista top del payload en 1U/2U
  fig07_cad_vista_lateral.png : vista side con stack de PCBs
  fig08_cad_vista_explotada.png: vista explotada de componentes
  fig09_diagrama_conexiones.png: conexiones electrico-datos
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch, Polygon, Circle, Wedge

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "figuras" / "m14"
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATOS DEL PRESUPUESTO ENERGETICO
# ============================================================================
# Estados del payload (M12/M13/M-drawio) con su potencia tipica y duracion
# por orbita LEO de 90 min (5400 s).
#
# Las cifras son estimaciones conservadoras basadas en datasheets de los
# componentes propuestos. Refinar tras integracion real.

ESTADOS = [
    # (nombre, potencia_W, dur_seg_orbita, color, descripcion_breve)
    ("OFF",     0.00, 1800, "#95A5A6", "Payload apagado (eclipse)"),
    ("BOOT",    4.50,   60, "#F39C12", "Arranque CM5 + drivers"),
    ("CAL",     5.20,  120, "#9B59B6", "Calibracion optica"),
    ("IDLE",    3.00, 1500, "#27AE60", "Espera en zona solar"),
    ("WARMUP",  6.00,   30, "#16A085", "Estabilizacion termica"),
    ("CAPT",    8.50,  180, "#229954", "Captura FPM (49 imagenes)"),
    ("PROC",    8.20,  240, "#1E8449", "FPM + Real-ESRGAN"),
    ("STORE",   3.20,   30, "#52BE80", "Compresion + disco"),
    ("DLPREP",  5.00,   60, "#5DADE2", "Banda S init + paquetes"),
    ("DL",     12.80,  240, "#2874A6", "Downlink banda S activo"),
    ("LP",      0.55,  840, "#E74C3C", "Bajo consumo (suspend)"),
    ("ERR",     3.50,  300, "#C0392B", "Estado de error / retry"),
]

# Componentes individuales con potencia, duty cycle y energia por orbita.
# duty_cycle es la fraccion del tiempo en que el componente esta activo en
# una orbita tipica de 90 min.
COMPONENTES = [
    # (nombre, P_max_W, P_idle_W, duty_cycle, fuente_datasheet, comentario)
    ("Raspberry Pi CM5",          5.0, 0.5,  0.65, "RPi Foundation",  "OBC payload, Linux + Python"),
    ("Camara CMOS (Sony IMX477)", 1.2, 0.05, 0.10, "Sony IMX477 DS",  "12MP, modo RAW para FPM"),
    ("Array LED 8x8 (multiplex)", 4.0, 0.0,  0.06, "Cree XPE2/CREE",  "Solo 1 LED ON por captura"),
    ("Driver LEDs (STM32G4)",     0.4, 0.05, 0.10, "ST DS",           "Multiplexa + PWM corriente"),
    ("Transceptor banda S",      10.0, 1.5,  0.05, "EnduroSat XBand", "Solo TX en zona ventana"),
    ("eMMC 32GB",                 0.3, 0.1,  0.20, "Samsung eMMC",    "Buffer captura + downlink"),
    ("Sensores temperatura",      0.05,0.05, 1.0,  "TI TMP117",       "Siempre on (housekeeping)"),
    ("Heater termico (opcional)", 2.0, 0.0,  0.10, "PI ceramic",      "Solo si TEMP_CMOS<-10C"),
    ("Conversor 5V/3.3V (LDO)",   0.5, 0.1,  1.0,  "TI TPS7A",        "Siempre on (alim. CM5/perif)"),
]


def setup_ax(ax, xlim, ylim, title=None, title_color=None):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - 0.4, title,
                ha="center", fontsize=14, weight="bold",
                color=title_color or "#1A365D")


def save(fig, name):
    out = OUT / name
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


# ============================================================================
# Fig 1 -- Potencia instantanea por estado del payload
# ============================================================================
def fig_potencia_estado():
    fig, ax = plt.subplots(figsize=(13, 6))
    names = [e[0] for e in ESTADOS]
    powers = [e[1] for e in ESTADOS]
    colors = [e[3] for e in ESTADOS]

    bars = ax.bar(names, powers, color=colors, edgecolor="#2D3748", linewidth=1.2)
    ax.set_ylabel("Potencia instantanea (W)", fontsize=12, weight="bold")
    ax.set_xlabel("Estado del payload", fontsize=12, weight="bold")
    ax.set_title("Potencia instantanea por estado del payload (microscopia FPM)",
                 fontsize=14, weight="bold", color="#1A365D", pad=15)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Etiquetas sobre las barras
    for bar, p in zip(bars, powers):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                f"{p:.2f} W", ha="center", fontsize=9, weight="bold")

    # Lineas de referencia
    ax.axhline(y=5.0, color="#27AE60", linestyle=":", linewidth=1.2, alpha=0.6)
    ax.text(11.4, 5.1, "5 W = consumo OBC tipico", fontsize=9,
            color="#27AE60", ha="right")
    ax.axhline(y=10.0, color="#C0392B", linestyle=":", linewidth=1.2, alpha=0.6)
    ax.text(11.4, 10.1, "10 W = limite presupuesto EPS 1U", fontsize=9,
            color="#C0392B", ha="right")

    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    return save(fig, "fig01_potencia_estado.png")


# ============================================================================
# Fig 2 -- Duty cycle por estado (% de tiempo en orbita)
# ============================================================================
def fig_duty_cycle():
    fig, ax = plt.subplots(figsize=(11, 7))
    names = [e[0] for e in ESTADOS]
    durs = [e[2] for e in ESTADOS]
    colors = [e[3] for e in ESTADOS]
    total = sum(durs)
    pcts = [100 * d / total for d in durs]

    wedges, texts, autotexts = ax.pie(
        durs, labels=names, colors=colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.78,
        wedgeprops=dict(edgecolor="white", linewidth=2),
        textprops=dict(fontsize=10, weight="bold")
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(9)

    ax.set_title("Distribucion del tiempo (duty cycle) por estado en una orbita LEO (90 min)",
                 fontsize=14, weight="bold", color="#1A365D", pad=20)

    # Anotaciones de duracion en segundos a la derecha
    legend_lines = [f"{n:<8s}: {d:>4d} s  ({p:>4.1f} %)"
                    for n, d, p in zip(names, durs, pcts)]
    ax.text(1.45, 0.1, "\n".join(legend_lines),
            fontfamily="monospace", fontsize=9,
            verticalalignment="center", transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", fc="#F8F9FA",
                      ec="#566573", lw=1))

    plt.tight_layout()
    return save(fig, "fig02_duty_cycle.png")


# ============================================================================
# Fig 3 -- Energia consumida por estado (Wh por orbita)
# ============================================================================
def fig_energia_orbita():
    fig, ax = plt.subplots(figsize=(13, 6))
    names = [e[0] for e in ESTADOS]
    energies = [e[1] * e[2] / 3600 for e in ESTADOS]  # Wh = W * h
    colors = [e[3] for e in ESTADOS]
    total_wh = sum(energies)

    bars = ax.bar(names, energies, color=colors, edgecolor="#2D3748", linewidth=1.2)
    ax.set_ylabel("Energia por orbita (Wh)", fontsize=12, weight="bold")
    ax.set_xlabel("Estado del payload", fontsize=12, weight="bold")
    ax.set_title(f"Energia consumida por estado en una orbita LEO de 90 min  "
                 f"(total payload: {total_wh:.2f} Wh/orbita)",
                 fontsize=13, weight="bold", color="#1A365D", pad=15)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    for bar, e in zip(bars, energies):
        if e > 0.01:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{e:.3f}", ha="center", fontsize=9, weight="bold")

    # Linea de capacidad bateria 1U
    ax.axhline(y=1.0, color="#566573", linestyle="--", linewidth=1, alpha=0.5)
    ax.text(11.4, 1.02, "1 Wh = ~2.5% bateria 1U (40Wh)", fontsize=8,
            color="#566573", ha="right")

    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    return save(fig, "fig03_energia_orbita.png")


# ============================================================================
# Fig 4 -- Timeline de una orbita (90 min) con potencia instantanea
# ============================================================================
def fig_timeline_orbita():
    fig, ax = plt.subplots(figsize=(14, 6))

    # Construir la secuencia temporal de estados a lo largo de 90 min.
    # Asumimos una orbita con: 30 min eclipse + 60 min iluminado.
    # Durante el iluminado el payload cumple su ciclo nominal.
    sequence = [
        # (estado, duracion_s)
        ("OFF",    1800),   # eclipse: payload off
        ("BOOT",     60),
        ("CAL",     120),
        ("IDLE",    300),
        ("WARMUP",   30),
        ("CAPT",    180),
        ("PROC",    240),
        ("STORE",    30),
        ("IDLE",    300),
        ("DLPREP",   60),
        ("DL",      240),
        ("IDLE",    300),
        ("LP",      840),   # apaga al perder zona solar
        ("ERR",     300),   # bloque ilustrativo (recovery)
        ("IDLE",    600),
    ]
    # Mapa nombre -> (potencia, color)
    state_info = {e[0]: (e[1], e[3]) for e in ESTADOS}

    t = 0
    for name, dur in sequence:
        p, color = state_info[name]
        ax.add_patch(Rectangle((t / 60, 0), dur / 60, p,
                               facecolor=color, edgecolor="#2D3748", linewidth=0.6))
        if dur > 120:
            ax.text(t / 60 + dur / 120, p / 2 if p > 1 else 0.4,
                    name, ha="center", va="center",
                    fontsize=9, color="white" if p > 2 else "#1A202C",
                    weight="bold")
        t += dur

    ax.set_xlim(0, t / 60)
    ax.set_ylim(0, 15)
    ax.set_xlabel("Tiempo en la orbita (minutos)", fontsize=12, weight="bold")
    ax.set_ylabel("Potencia instantanea (W)", fontsize=12, weight="bold")
    ax.set_title("Perfil temporal del consumo del payload durante una orbita LEO",
                 fontsize=14, weight="bold", color="#1A365D", pad=15)
    ax.grid(axis="both", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Marcar fases de la orbita
    ax.axvline(x=30, color="#F39C12", linestyle="-", linewidth=2, alpha=0.5)
    ax.text(15, 14, "ECLIPSE", ha="center", fontsize=11,
            weight="bold", color="#566573",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FEF9E7", ec="#F39C12"))
    ax.text(60, 14, "ILUMINADO (zona solar)", ha="center", fontsize=11,
            weight="bold", color="#1E8449",
            bbox=dict(boxstyle="round,pad=0.3", fc="#E8F8F5", ec="#27AE60"))

    plt.tight_layout()
    return save(fig, "fig04_timeline_orbita.png")


# ============================================================================
# Fig 5 -- Balance energetico orbital (generacion vs consumo)
# ============================================================================
def fig_balance_energetico():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # --- Panel izquierdo: barras comparativas ---
    categorias = ["Generacion\n(paneles solares)",
                  "Consumo OBC\n+ EPS + UHF",
                  "Consumo payload\n(microscopia FPM)",
                  "Margen disponible"]
    # Valores en Wh por orbita (estimaciones para 1U con paneles 1U + extendidos)
    # Paneles 1U solo: ~3.5W * 0.7h iluminada = ~2.45 Wh
    # Paneles desplegados (4 alas): ~10W * 0.7h = ~7 Wh -> usamos 6.5 Wh
    generacion = 6.5
    consumo_bus = 2.2  # OBC nominal + EPS + UHF housekeeping
    consumo_pl = sum(e[1] * e[2] / 3600 for e in ESTADOS)
    margen = generacion - consumo_bus - consumo_pl
    valores = [generacion, consumo_bus, consumo_pl, margen]
    colors_bal = ["#27AE60", "#5DADE2", "#9B59B6",
                  "#229954" if margen > 0 else "#C0392B"]

    bars = ax1.bar(categorias, valores, color=colors_bal,
                   edgecolor="#2D3748", linewidth=1.2)
    ax1.set_ylabel("Energia (Wh por orbita)", fontsize=11, weight="bold")
    ax1.set_title("Balance energetico orbital", fontsize=13,
                  weight="bold", color="#1A365D")
    ax1.grid(axis="y", alpha=0.3, linestyle="--")
    ax1.set_axisbelow(True)
    ax1.axhline(y=0, color="black", linewidth=0.8)

    for bar, v in zip(bars, valores):
        ax1.text(bar.get_x() + bar.get_width() / 2,
                 v + (0.15 if v >= 0 else -0.3),
                 f"{v:+.2f} Wh", ha="center", fontsize=10, weight="bold",
                 color="#1A202C")

    # --- Panel derecho: capacidad bateria y estado SOC ---
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis("off")
    ax2.set_title("Reserva de bateria", fontsize=13, weight="bold",
                  color="#1A365D")

    # Caja: capacidad nominal
    bat_cap = 40  # Wh nominal CubeSat 1U con 2x 18650
    soc_target = 60  # %  - mantener SOC >= 60% por margen DOD
    usable = bat_cap * (1 - soc_target / 100)

    info = (
        f"$\\bf{{Capacidad\\ nominal}}$: {bat_cap} Wh\n"
        f"  (2 x 18650 a 3.7V, 2x serie + 1p)\n\n"
        f"$\\bf{{DOD\\ maximo\\ recomendado}}$: 40%\n"
        f"  -> energia utilizable {usable:.0f} Wh\n\n"
        f"$\\bf{{Margen\\ por\\ orbita}}$: {margen:+.2f} Wh\n"
        f"  -> {'superavit' if margen > 0 else 'DEFICIT (revisar diseno)'}\n\n"
        f"$\\bf{{Eclipses\\ consecutivos\\ soportados}}$: "
        f"{int(usable / (consumo_bus + consumo_pl)) if (consumo_bus + consumo_pl) > 0 else 0}\n"
        f"  (sin recarga, con duty cycle full)\n\n"
        f"$\\bf{{Recomendacion}}$:\n"
        f"  - mantener payload OFF en eclipse\n"
        f"  - duty cycle de captura cada 2 orbitas\n"
        f"  - downlink solo sobre estacion (~10 min)"
    )
    ax2.text(0.3, 9.7, info, fontsize=10, va="top",
             bbox=dict(boxstyle="round,pad=0.6", fc="#F8F9FA",
                       ec="#566573", lw=1.2),
             family="DejaVu Sans")

    plt.suptitle("Balance energetico y reserva de bateria del INTISAT",
                 fontsize=15, weight="bold", color="#1A365D", y=1.02)
    plt.tight_layout()
    return save(fig, "fig05_balance_energetico.png")


# ============================================================================
# Fig 6 -- Vista superior (top) del payload en estructura 1U/2U
# ============================================================================
def fig_cad_vista_superior():
    fig, ax = plt.subplots(figsize=(11, 11))
    ax.set_xlim(-10, 110)
    ax.set_ylim(-10, 120)
    ax.set_aspect("equal")
    ax.axis("off")

    # Estructura 1U (100x100 mm interior)
    ax.add_patch(Rectangle((0, 0), 100, 100, fill=False,
                           edgecolor="#2D3748", linewidth=3))
    ax.add_patch(Rectangle((-1, -1), 102, 102, fill=False,
                           edgecolor="#2D3748", linewidth=1, linestyle="--"))
    ax.text(50, 105, "Vista superior - Payload de microscopia en 1U (cara +Z)",
            ha="center", fontsize=13, weight="bold", color="#1A365D")
    ax.text(50, -7, "100 mm", ha="center", fontsize=10, weight="bold")
    ax.text(-6, 50, "100 mm", ha="center", fontsize=10, weight="bold",
            rotation=90)

    # Componentes (vistos desde arriba)
    # Cada uno: (x, y, w, h, color, label)
    componentes_top = [
        (5, 5, 90, 25, "#3498DB", "Carrier CM5 + radio banda S\n(PCB 90x90 mm)"),
        (15, 35, 70, 35, "#9B59B6", "Array LED 8x8\n(70x70 mm)"),
        (40, 75, 20, 20, "#E67E22", "Camara CMOS + objetivo\n(IMX477, 25x25 mm)"),
        (5, 75, 25, 20, "#27AE60", "Driver LEDs\n(STM32G4)"),
        (70, 75, 25, 20, "#C0392B", "Heater termico\n(opcional)"),
    ]
    for x, y, w, h, c, lbl in componentes_top:
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.5,rounding_size=2",
                                    facecolor=c, edgecolor="#2D3748",
                                    linewidth=1.5, alpha=0.85))
        ax.text(x + w / 2, y + h / 2, lbl, ha="center", va="center",
                fontsize=9, color="white", weight="bold")

    # Indicadores de muestra biologica y eje optico
    ax.plot(50, 80, marker="*", markersize=20, color="gold",
            markeredgecolor="#1A202C", zorder=5)
    ax.annotate("muestra (en\nportamuestras)", xy=(50, 80), xytext=(50, 100),
                fontsize=9, ha="center", color="#1A202C",
                arrowprops=dict(arrowstyle="->", color="#1A202C"))

    # Ejes de orientacion
    ax.annotate("", xy=(108, 0), xytext=(108, 20),
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=2))
    ax.text(112, 10, "+Y", fontsize=11, weight="bold", color="#C0392B")
    ax.annotate("", xy=(108, 0), xytext=(88, 0),
                arrowprops=dict(arrowstyle="->", color="#27AE60", lw=2))
    ax.text(100, -5, "+X", fontsize=11, weight="bold", color="#27AE60")

    # Cota leyenda
    leyenda = (
        "Volumen 1U: 100x100x113.5 mm (CDS 13.4)\n"
        "Masa maxima 1U: 1.33 kg (estandar CDS)\n"
        "Eje optico: paralelo a +Z (sale de la pagina)"
    )
    ax.text(50, -15, leyenda, ha="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", fc="#FEF9E7", ec="#F39C12"))

    plt.tight_layout()
    return save(fig, "fig06_cad_vista_superior.png")


# ============================================================================
# Fig 7 -- Vista lateral con stack de PCBs y modulo optico
# ============================================================================
def fig_cad_vista_lateral():
    fig, ax = plt.subplots(figsize=(8, 12))
    ax.set_xlim(-10, 110)
    ax.set_ylim(-10, 130)
    ax.set_aspect("equal")
    ax.axis("off")

    # Estructura exterior 1U
    ax.add_patch(Rectangle((0, 0), 100, 113.5, fill=False,
                           edgecolor="#2D3748", linewidth=3))
    ax.text(50, 120, "Vista lateral - stack del payload (corte X-Z)",
            ha="center", fontsize=13, weight="bold", color="#1A365D")
    ax.text(-6, 56, "113.5 mm", ha="center", fontsize=10, weight="bold",
            rotation=90)
    ax.text(50, -7, "100 mm", ha="center", fontsize=10, weight="bold")

    # Stack vertical (de abajo hacia arriba)
    # (z_inicio, altura, color, label)
    stack = [
        (2,   12, "#5DADE2", "EPS + 2x 18650"),
        (14,   8, "#9B59B6", "Pi 5 carrier + CM5"),
        (22,   8, "#3498DB", "PCB Radio banda S"),
        (30,   5, "#27AE60", "Driver LEDs (STM32G4)"),
        (35,   8, "#E74C3C", "Array LED 8x8 (PCB con LEDs)"),
        (50,  35, "#F39C12", "Modulo optico (objetivo + tubo)"),
        (90,   3, "#7D6608", "Portamuestras + ventana"),
        (95,   8, "#2C3E50", "Camara CMOS + lente colectora"),
    ]
    for z, h, c, lbl in stack:
        ax.add_patch(Rectangle((10, z), 80, h, facecolor=c,
                               edgecolor="#2D3748", linewidth=1.5, alpha=0.85))
        ax.text(50, z + h / 2, lbl, ha="center", va="center",
                fontsize=9.5, color="white", weight="bold")
        # Cota de altura a la derecha
        ax.annotate("", xy=(95, z), xytext=(95, z + h),
                    arrowprops=dict(arrowstyle="<->", color="#566573", lw=0.8))
        ax.text(98, z + h / 2, f"{h} mm", fontsize=8, color="#566573",
                va="center")

    # Indicadores ejes opticos
    ax.annotate("", xy=(50, 50), xytext=(50, 95),
                arrowprops=dict(arrowstyle="->", color="gold", lw=2,
                                connectionstyle="arc3,rad=0"))
    ax.text(75, 75, "eje\noptico\n+Z", fontsize=10, weight="bold",
            color="#7D6608")

    # Leyenda inferior
    leyenda = (
        "ESTIMACION DE STACK - revisar tras integracion real\n"
        "Espacios entre PCBs: ~2 mm (no mostrado)\n"
        "Sin contar standoffs, cableado interno ni baffles"
    )
    ax.text(50, -7, leyenda, ha="center", fontsize=8.5, style="italic",
            color="#566573")

    plt.tight_layout()
    return save(fig, "fig07_cad_vista_lateral.png")


# ============================================================================
# Fig 8 -- Vista explotada de componentes
# ============================================================================
def fig_cad_vista_explotada():
    fig, ax = plt.subplots(figsize=(13, 10))
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 22)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Vista explotada del ensamblaje del payload de microscopia",
                 fontsize=14, weight="bold", color="#1A365D", pad=15)

    # Componentes en stack vertical separados (de abajo hacia arriba)
    componentes_exp = [
        # (cx, cy, w, h, color, label_principal, label_subtitulo)
        (15,  2.5, 14, 1.5, "#5DADE2", "EPS + bateria",        "PCB 90x90 mm + 2x 18650"),
        (15,  4.5, 14, 1.2, "#9B59B6", "Carrier CM5",           "Pi 5 carrier + CM5 module"),
        (15,  6.2, 14, 1.0, "#3498DB", "Radio banda S",         "EnduroSat XBand 10W"),
        (15,  7.5, 14, 0.8, "#27AE60", "Driver LEDs",           "STM32G4 + multiplexador"),
        (15,  8.7, 14, 1.0, "#E74C3C", "Array LED 8x8",         "PCB con 64 LEDs (FPM)"),
        (15, 10.5, 14, 0.6, "#7D6608", "Portamuestras",         "ventana de vidrio + sample"),
        (15, 11.5, 14, 0.8, "#F39C12", "Objetivo + tubo",       "lente colectora f=4mm"),
        (15, 13.0, 14, 1.0, "#2C3E50", "Camara CMOS",           "Sony IMX477 (12 MP RAW)"),
        (15, 14.7, 14, 0.6, "#566573", "Conector FFC + cable",  "CSI-2 hacia CM5"),
        (15, 16.0, 14, 1.5, "#34495E", "Tapa superior (+Z)",    "estructura 1U + baffle"),
    ]
    for cx, cy, w, h, c, lbl, sub in componentes_exp:
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                    boxstyle="round,pad=0.05,rounding_size=0.2",
                                    facecolor=c, edgecolor="#2D3748",
                                    linewidth=1.2, alpha=0.9))
        ax.text(cx, cy, lbl, ha="center", va="center",
                fontsize=10, color="white", weight="bold")
        ax.text(cx + w / 2 + 0.3, cy, sub, ha="left", va="center",
                fontsize=8.5, color="#1A202C", style="italic")

    # Lineas verticales conectando (eje de ensamblaje)
    for cx, cy, w, h, *_ in componentes_exp[:-1]:
        ax.plot([cx - 5, cx - 5], [cy + h / 2 + 0.05, cy + 1.5 - h / 2 - 0.05],
                color="#95A5A6", linewidth=0.8, linestyle="--", zorder=0)

    # Etiquetas laterales
    ax.text(2, 17.5, "Tapa\nsuperior",
            fontsize=11, weight="bold", color="#34495E", ha="center")
    ax.text(2, 2.5, "Base / EPS",
            fontsize=11, weight="bold", color="#5DADE2", ha="center")

    # Flecha de orden de ensamblaje
    ax.annotate("", xy=(3, 16), xytext=(3, 3),
                arrowprops=dict(arrowstyle="->", color="#27AE60", lw=2.5))
    ax.text(0.5, 9, "Orden de\nensamblaje\n(bottom-up)",
            fontsize=10, weight="bold", color="#27AE60", ha="center")

    plt.tight_layout()
    return save(fig, "fig08_cad_vista_explotada.png")


# ============================================================================
# Fig 9 -- Diagrama de conexiones (HW logico)
# ============================================================================
def fig_diagrama_conexiones():
    fig, ax = plt.subplots(figsize=(14, 9))
    setup_ax(ax, (0, 16), (0, 10), "Conexiones electricas y de datos del payload")

    # CM5 central
    ax.add_patch(FancyBboxPatch((6.5, 4), 3, 2.0,
                                boxstyle="round,pad=0.1,rounding_size=0.3",
                                facecolor="#1A365D", edgecolor="#0F2342",
                                linewidth=2))
    ax.text(8, 5, "Raspberry Pi CM5\n(payload OBC)", ha="center", va="center",
            fontsize=11, color="white", weight="bold")

    # Componentes alrededor
    perif = [
        # (x, y, w, h, color, label, bus)
        (1.5, 7.0, 2.5, 1.0, "#E67E22", "Camara CMOS\n(IMX477)",        "MIPI CSI-2"),
        (1.5, 4.5, 2.5, 1.0, "#9B59B6", "Driver LEDs\n(STM32G4)",        "I2C + GPIO"),
        (1.5, 2.0, 2.5, 1.0, "#5DADE2", "EPS\n(ADC + control)",         "I2C + GPIO"),
        (12,  7.0, 2.5, 1.0, "#27AE60", "Radio banda S",                "UART o SPI"),
        (12,  4.5, 2.5, 1.0, "#7D6608", "eMMC 32GB",                    "eMMC (interno)"),
        (12,  2.0, 2.5, 1.0, "#C0392B", "Sensores T degC\n(TMP117 x N)", "I2C"),
        (6.5, 0.5, 3.0, 1.0, "#34495E", "Conector OBC principal\n(via header)", "UART + GPIO"),
    ]
    for x, y, w, h, c, lbl, bus in perif:
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.08,rounding_size=0.2",
                                    facecolor=c, edgecolor="#2D3748",
                                    linewidth=1.2, alpha=0.9))
        ax.text(x + w / 2, y + h / 2 + 0.1, lbl,
                ha="center", va="center", fontsize=9,
                color="white", weight="bold")
        ax.text(x + w / 2, y + h / 2 - 0.35, bus,
                ha="center", va="center", fontsize=7.5,
                color="white", style="italic")

    # Flechas (CM5 <-> perif)
    cm5_center = (8, 5)
    for x, y, w, h, _, _, _ in perif:
        if x < 6:
            # izquierda
            start = (x + w, y + h / 2)
            end = (cm5_center[0] - 1.5, cm5_center[1] +
                   (y + h / 2 - cm5_center[1]) * 0.2)
        elif x > 9.5:
            start = (x, y + h / 2)
            end = (cm5_center[0] + 1.5, cm5_center[1] +
                   (y + h / 2 - cm5_center[1]) * 0.2)
        else:
            start = (x + w / 2, y + h)
            end = (cm5_center[0], cm5_center[1] - 1.0)
        ax.add_patch(FancyArrowPatch(start, end,
                                     arrowstyle="<->", mutation_scale=12,
                                     color="#566573", linewidth=1.3))

    # Leyenda de alimentacion
    pwr_text = (
        "Lineas de alimentacion:\n"
        "  EPS -> 5V regulado -> CM5\n"
        "  EPS -> 3.3V LDO -> camara, LEDs, sensores\n"
        "  EPS -> 5V conmutado -> radio banda S (solo TX)\n"
        "  EPS -> 5V LDO -> heater termico (opcional)"
    )
    ax.text(0.3, 0.4, pwr_text, fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="#FEF9E7",
                      ec="#F39C12", lw=1), family="DejaVu Sans")

    plt.tight_layout()
    return save(fig, "fig09_diagrama_conexiones.png")


if __name__ == "__main__":
    # Solo figuras energeticas; las CAD se reemplazaron por drawios
    # (Timeline_Orbital_Payload_INTISAT.drawio y
    #  Maquina_Estados_Payload_Energetico_INTISAT.drawio).
    # Las funciones CAD (fig_cad_*) quedan disponibles si se necesitan.
    for fn in (fig_potencia_estado, fig_duty_cycle, fig_energia_orbita,
               fig_timeline_orbita, fig_balance_energetico):
        p = fn()
        print(f"OK -> {p.name}  ({p.stat().st_size // 1024} kB)")
