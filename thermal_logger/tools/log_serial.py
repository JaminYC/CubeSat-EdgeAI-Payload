#!/usr/bin/env python3
"""
log_serial.py — Lector serial para ESP32 Thermal Logger
Gráfica en TIEMPO REAL + comandos desde la terminal.

Uso:
    python log_serial.py --port COM4
    python log_serial.py --port COM4 --output perfil.csv

Comandos disponibles mientras corre:
    MODE FILTER   activa línea EMA en la gráfica
    MODE RAW      solo temperatura cruda
    RATE 1000     cambia periodo a 1000 ms
    OFFSET -2.5   aplica offset de calibración
    STOP / START  pausa y reanuda el logging
    RESET         reinicia el tiempo

Dependencias:
    pip install pyserial matplotlib
"""

import argparse
import csv
import sys
import time
import threading
import queue
from datetime import datetime

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ─── Argumentos ──────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="ESP32 Thermal Logger — gráfica en tiempo real")
    p.add_argument("--port",   required=True,        help="Puerto COM (ej. COM4)")
    p.add_argument("--baud",   default=115200, type=int)
    default_name = f"perfil_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    p.add_argument("--output", default=default_name, help="Archivo CSV de salida")
    p.add_argument("--window", default=300,   type=int, help="Segundos visibles (default 300)")
    p.add_argument("--reflow", action="store_true",    help="Mostrar zonas de referencia Kester Sn63Pb37")
    return p.parse_args()

# ─── Estado compartido ────────────────────────────────────
data_queue  = queue.Queue()    # datos del serial → gráfica
cmd_queue   = queue.Queue()    # comandos del usuario → serial
clear_event = threading.Event() # señal para limpiar datos al cambiar modo
t_data     = []
temp_data  = []
filt_data  = []
has_filter = False
t_offset   = [None]   # primer timestamp recibido → normaliza a t=0
stop_event = threading.Event()
ser_ref    = [None]           # referencia compartida al objeto serial

COMMANDS = """\
──────────────────────────────────────────
  Comandos disponibles:
    MODE FILTER   → activa filtro EMA en gráfica
    MODE RAW      → solo temperatura cruda
    RATE <ms>     → periodo (ej: RATE 1000)
    OFFSET <C>    → calibración (ej: OFFSET -2.5)
    STOP          → pausa logging
    START         → reanuda logging
    RESET         → reinicia tiempo base
──────────────────────────────────────────"""

# ─── Hilo: leer stdin y encolar comandos ─────────────────
def stdin_reader():
    print(COMMANDS)
    while not stop_event.is_set():
        try:
            line = sys.stdin.readline()
            if line:
                cmd = line.strip()
                if cmd:
                    cmd_queue.put(cmd)
        except Exception:
            break

# ─── Hilo: serial (lectura + escritura de comandos) ──────
def serial_worker(port, baud, output):
    global has_filter

    print(f"Conectando a {port} @ {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except serial.SerialException as e:
        print(f"ERROR al abrir puerto: {e}")
        stop_event.set()
        return

    ser_ref[0] = ser
    time.sleep(2)
    ser.flushInput()
    ser.write(b"START\n")
    print(f"Guardando en: {output}\n")

    headers = None

    with open(output, "w", newline="") as f:
        writer = None
        while not stop_event.is_set():
            # ── Enviar comandos del usuario ──
            while not cmd_queue.empty():
                cmd = cmd_queue.get_nowait()
                ser.write((cmd + "\n").encode())
                print(f"  → Enviado: {cmd}")
                # Si cambia a MODE FILTER/RAW, resetear cabecera
                if "MODE" in cmd.upper():
                    # Forzar nueva cabecera CSV: STOP → START
                    ser.write(b"STOP\n")
                    time.sleep(0.1)
                    ser.write(b"START\n")
                    headers = None
                    has_filter = False
                    clear_event.set()   # avisar a la gráfica que limpie datos

            # ── Leer datos ──
            try:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                if line.startswith("#"):
                    print(f"  {line}")
                    continue

                # Detectar cabecera CSV
                if headers is None:
                    if "t_ms" not in line:
                        continue
                    headers = line.split(",")
                    has_filter = (len(headers) == 3)
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    print(f"  Cabecera: {headers}")
                    continue

                parts = line.split(",")
                if len(parts) == len(headers):
                    writer.writerow(parts)
                    f.flush()
                    data_queue.put(parts)

            except Exception:
                if not stop_event.is_set():
                    time.sleep(0.1)

    try:
        ser.write(b"STOP\n")
        ser.close()
    except Exception:
        pass
    print("Puerto serial cerrado.")

# ─── Perfil de referencia Kester Sn63Pb37 ────────────────
def draw_reflow_reference(ax):
    """Dibuja zonas y líneas del perfil Kester sobre el eje dado."""
    # Zonas de tiempo (segundos)
    zones = [
        (0,   90,  "#fab387", "Pre-heating\n(0-90 s)"),
        (90,  180, "#f9e2af", "Soaking\n(90-180 s)"),
        (180, 240, "#f38ba8", "Reflow\n(180-240 s)"),
        (240, 300, "#89b4fa", "Cooling"),
    ]
    for t0, t1, color, label in zones:
        ax.axvspan(t0, t1, alpha=0.08, color=color, zorder=0)
        if label != "Cooling":
            ax.text((t0+t1)/2, 8, label, ha="center", va="bottom",
                    fontsize=7.5, color=color, alpha=0.9)

    # Líneas horizontales de temperatura clave
    hlines = [
        (150, "#f9e2af", "150°C soak start"),
        (183, "#fab387", "183°C liquidus"),
        (217, "#f38ba8", "217°C peak min"),
        (225, "#f38ba8", "225°C peak max"),
    ]
    for temp, color, label in hlines:
        ax.axhline(temp, color=color, linewidth=0.8, linestyle="--", alpha=0.6, zorder=1)
        ax.text(302, temp, label, va="center", fontsize=7, color=color, alpha=0.85)

    # Líneas verticales de zona
    for t in [90, 180, 240]:
        ax.axvline(t, color="#6c7086", linewidth=0.8, linestyle=":", alpha=0.7)

    ax.set_xlim(0, 310)
    ax.set_ylim(0, 250)

# ─── Gráfica en tiempo real ───────────────────────────────
def make_animation(window_s, output, show_reflow=False):
    BG = "#1e1e2e"

    if show_reflow:
        fig, (ax_ref, ax_zoom) = plt.subplots(
            2, 1, figsize=(13, 8),
            gridspec_kw={"height_ratios": [2, 1], "hspace": 0.35}
        )
    else:
        fig, ax_zoom = plt.subplots(figsize=(13, 5))
        ax_ref = None

    fig.patch.set_facecolor(BG)

    def _style(ax, title_txt):
        ax.set_facecolor(BG)
        ax.set_xlabel("Tiempo (s)", color="#cdd6f4")
        ax.set_ylabel("Temperatura (°C)", color="#cdd6f4")
        ax.tick_params(colors="#cdd6f4")
        for spine in ax.spines.values():
            spine.set_edgecolor("#45475a")
        ax.grid(True, alpha=0.2, color="#45475a")
        ax.set_title(title_txt, color="#cdd6f4", fontsize=9, pad=6)

    # ── Panel superior: referencia Kester ──
    if ax_ref is not None:
        _style(ax_ref, "Referencia Kester Sn63Pb37 — perfil completo")
        draw_reflow_reference(ax_ref)
        ref_raw,  = ax_ref.plot([], [], color="#f38ba8", linewidth=1.8, label="temp_C")
        ref_filt, = ax_ref.plot([], [], color="#a6e3a1", linewidth=1.8,
                                linestyle="-", label="EMA filtrada", visible=False)
        ax_ref.legend(facecolor="#313244", labelcolor="#cdd6f4", fontsize=8)
    else:
        ref_raw = ref_filt = None

    # ── Panel inferior: zoom dinámico ──
    _style(ax_zoom, "Zoom — últimos datos (autoescala)")
    zoom_raw,  = ax_zoom.plot([], [], color="#f38ba8", linewidth=1.8, label="temp_C")
    zoom_filt, = ax_zoom.plot([], [], color="#a6e3a1", linewidth=1.8,
                              linestyle="-", label="EMA filtrada", visible=False)
    ax_zoom.legend(facecolor="#313244", labelcolor="#cdd6f4", fontsize=8)

    sup_title = fig.suptitle("Esperando datos...", color="#cdd6f4", fontsize=11, y=0.98)

    def update(_frame):
        if clear_event.is_set():
            t_data.clear(); temp_data.clear(); filt_data.clear()
            t_offset[0] = None
            for line in [ref_raw, ref_filt, zoom_raw, zoom_filt]:
                if line is not None:
                    line.set_data([], [])
            clear_event.clear()

        while not data_queue.empty():
            parts = data_queue.get_nowait()
            try:
                raw_ms = int(parts[0])
                if t_offset[0] is None:
                    t_offset[0] = raw_ms
                t_s  = (raw_ms - t_offset[0]) / 1000.0
                if parts[1] == "NaN":
                    continue
                t_data.append(t_s)
                temp_data.append(float(parts[1]))
                if has_filter and len(parts) == 3 and parts[2] != "NaN":
                    filt_data.append(float(parts[2]))
            except (ValueError, IndexError):
                continue

        if not t_data:
            return [zoom_raw, zoom_filt] + ([ref_raw, ref_filt] if ax_ref else [])

        all_t   = t_data
        all_tmp = temp_data
        all_flt = filt_data if (has_filter and len(filt_data) == len(t_data)) else []

        # ── Panel referencia: todos los datos ──
        if ax_ref is not None:
            ref_raw.set_data(all_t, all_tmp)
            x_max = max(310, t_data[-1] + 10)
            ax_ref.set_xlim(0, x_max)
            ax_ref.set_ylim(0, 250)
            if all_flt:
                ref_filt.set_data(all_t, all_flt)
                ref_filt.set_visible(True)
            else:
                ref_filt.set_visible(False)

        # ── Panel zoom: ventana deslizante + autoescala ──
        t_max   = t_data[-1]
        t_min_w = max(0.0, t_max - window_s)
        idx     = [i for i, t in enumerate(t_data) if t >= t_min_w]
        vis_t   = [t_data[i]    for i in idx]
        vis_tmp = [temp_data[i] for i in idx]
        vis_flt = [filt_data[i] for i in idx] if all_flt else []

        zoom_raw.set_data(vis_t, vis_tmp)
        ax_zoom.set_xlim(t_min_w, t_min_w + window_s)
        vals = vis_tmp + vis_flt
        if vals:
            ax_zoom.set_ylim(min(vals) - 3, max(vals) + 3)

        if vis_flt:
            zoom_filt.set_data(vis_t, vis_flt)
            zoom_filt.set_visible(True)
        else:
            zoom_filt.set_visible(False)

        sup_title.set_text(
            f"Perfil térmico  |  {temp_data[-1]:.1f} °C  |  "
            f"t = {t_data[-1]:.0f} s  |  {datetime.now().strftime('%H:%M:%S')}"
        )
        return [zoom_raw, zoom_filt] + ([ref_raw, ref_filt] if ax_ref else [])

    def on_close(_event):
        stop_event.set()
        try:
            fig.savefig(output.replace(".csv", ".png"), dpi=150,
                        facecolor=fig.get_facecolor())
            print(f"Gráfico guardado: {output.replace('.csv', '.png')}")
        except Exception:
            pass

    fig.canvas.mpl_connect("close_event", on_close)
    ani = animation.FuncAnimation(fig, update, interval=500,
                                  blit=False, cache_frame_data=False)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
    return ani

# ─── Main ─────────────────────────────────────────────────
def main():
    args = parse_args()

    # Hilo serial
    t_serial = threading.Thread(
        target=serial_worker,
        args=(args.port, args.baud, args.output),
        daemon=True
    )
    t_serial.start()

    # Hilo stdin (comandos del usuario)
    t_stdin = threading.Thread(target=stdin_reader, daemon=True)
    t_stdin.start()

    # Gráfica en hilo principal
    make_animation(args.window, args.output, show_reflow=args.reflow)

    stop_event.set()
    t_serial.join(timeout=3)
    print("Listo.")

if __name__ == "__main__":
    main()
