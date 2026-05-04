"""
Profiler energetico del payload CubeSat.

Mide corriente y voltaje del rail 5V_PAYLOAD via INA219 mientras
la RPi ejecuta las distintas fases del pipeline (idle, capture, IA, downlink).

Uso (en la RPi):
    sudo pip install adafruit-circuitpython-ina219
    python tools/power_profiler.py --duration 120 --output power_log.csv

Salida:
    power_log.csv  con columnas: timestamp, voltage_V, current_mA, power_W, phase
    power_log.png  grafico con la traza temporal y energia acumulada por fase
"""

import argparse
import time
import csv
import sys
from pathlib import Path

# El sensor INA219 se inicializa en la RPi; en el dev box solo simulamos.
def init_sensor():
    try:
        import board
        import busio
        from adafruit_ina219 import INA219
        i2c = busio.I2C(board.SCL, board.SDA)
        ina = INA219(i2c)
        return ina
    except Exception as e:
        print(f"[WARN] INA219 no disponible ({e}). Modo simulacion.")
        return None


def read_sample(sensor):
    """Devuelve (voltage_V, current_mA, power_W)."""
    if sensor is None:
        # Modo simulacion: devuelve un valor sintetico para testing
        import random
        v = 5.0 + random.uniform(-0.05, 0.05)
        i = random.uniform(600, 1200)   # mA
        return v, i, v * i / 1000.0
    v = sensor.bus_voltage + sensor.shunt_voltage
    i = sensor.current  # mA
    return v, i, v * i / 1000.0


def profile(duration: float, output: str, phase_marker: str = None):
    sensor = init_sensor()
    samples = []
    t0 = time.perf_counter()
    print(f"[INFO] Sampling por {duration} s a 10 Hz...")
    while time.perf_counter() - t0 < duration:
        v, i, p = read_sample(sensor)
        ts = time.perf_counter() - t0
        samples.append((ts, v, i, p, phase_marker or "unknown"))
        time.sleep(0.1)

    # Guardar CSV
    with open(output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "voltage_V", "current_mA", "power_W", "phase"])
        for s in samples:
            w.writerow([f"{s[0]:.3f}", f"{s[1]:.3f}",
                          f"{s[2]:.1f}", f"{s[3]:.3f}", s[4]])
    # Resumen
    powers = [s[3] for s in samples]
    avg = sum(powers) / len(powers)
    pico = max(powers)
    energy = sum(powers) * 0.1  # J (suma * dt)
    print(f"[OK] Muestras: {len(samples)}")
    print(f"     Potencia media: {avg:.2f} W")
    print(f"     Potencia pico:  {pico:.2f} W")
    print(f"     Energia total:  {energy:.1f} J ({energy/3600:.4f} Wh)")
    print(f"     CSV guardado:   {output}")
    return samples


def plot(csv_path: str, png_path: str):
    """Grafica el log de power."""
    import matplotlib.pyplot as plt
    times, voltages, currents, powers = [], [], [], []
    with open(csv_path) as f:
        next(f)  # header
        for row in csv.reader(f):
            times.append(float(row[0]))
            voltages.append(float(row[1]))
            currents.append(float(row[2]))
            powers.append(float(row[3]))

    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                                facecolor="white")
    axes[0].plot(times, powers, color="#C53030", lw=1.4)
    axes[0].set_ylabel("Potencia (W)", fontweight="bold")
    axes[0].grid(alpha=0.3)
    axes[0].set_title(f"Profile energetico — media {sum(powers)/len(powers):.2f} W",
                        fontweight="bold")

    axes[1].plot(times, currents, color="#2C5282", lw=1.4)
    axes[1].set_ylabel("Corriente (mA)", fontweight="bold")
    axes[1].set_xlabel("Tiempo (s)")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(png_path, dpi=140)
    print(f"[OK] Grafico guardado: {png_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=60,
                     help="duracion del muestreo (s)")
    ap.add_argument("--output", default="power_log.csv")
    ap.add_argument("--phase", default="full_cycle",
                     help="etiqueta de fase: idle/capture/processing/downlink")
    ap.add_argument("--plot", action="store_true",
                     help="generar grafico al terminar")
    args = ap.parse_args()

    profile(args.duration, args.output, args.phase)
    if args.plot:
        plot(args.output, args.output.replace(".csv", ".png"))
