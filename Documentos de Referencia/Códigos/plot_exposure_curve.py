#!/usr/bin/env python3
# Lee el CSV más reciente en data/processed y grafica mean vs exposure_us.
# Marca puntos saturados (pct_sat_255>0) en otro estilo.

import os, glob, csv
import numpy as np
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
PROC_DIR = os.path.join(BASE, "..", "data", "processed")

def latest_csv():
    files = sorted(glob.glob(os.path.join(PROC_DIR, "measurements_*.csv")))
    if not files:
        raise FileNotFoundError("No hay measurements_*.csv en data/processed. Corre compile_measurements.py primero.")
    return files[-1]

def main():
    path = latest_csv()
    xs_exp, ys_mean, sat_flags = [], [], []
    with open(path, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                exp = float(row.get("exposure_us") or 0.0)
                mean = float(row.get("mean") or 0.0)
                sat = float(row.get("pct_sat_255") or 0.0) > 0.0
                if exp > 0:
                    xs_exp.append(exp/1000.0)  # a ms
                    ys_mean.append(mean)
                    sat_flags.append(sat)
            except:
                pass

    if not xs_exp:
        print("No hay filas con exposure_us válido en:", path)
        return

    xs = np.array(xs_exp)
    ys = np.array(ys_mean)
    sat = np.array(sat_flags)

    plt.figure()
    plt.title("Mean vs exposición (ms)")
    plt.xlabel("Exposición (ms)")
    plt.ylabel("Mean (0..255)")

    # no saturados
    plt.scatter(xs[~sat], ys[~sat], label="OK", marker="o")
    # saturados
    if np.any(sat):
        plt.scatter(xs[sat], ys[sat], label="Saturado", marker="x")

    # línea objetivo (ej. mean ~ 150)
    plt.axhline(150, linestyle="--", label="objetivo≈150")
    plt.legend()
    out_png = os.path.join(PROC_DIR, "exposure_curve.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    print("Guardado:", out_png)

    # sugerencia de exposición (la más cercana a 150 sin saturar)
    idx_ok = np.where(~sat)[0]
    if len(idx_ok):
        dif = np.abs(ys[idx_ok] - 150)
        best = idx_ok[np.argmin(dif)]
        print(f"Sugerencia: ~{xs[best]:.1f} ms (mean={ys[best]:.1f})")
    else:
        print("Todas saturan; baja exposición o brillo.")

if __name__ == "__main__":
    main()
