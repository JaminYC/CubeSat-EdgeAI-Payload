#!/usr/bin/env python3
# exposure_sweep_fino.py — Barrido fino 5–15 ms (paso 1 ms) con preview y gráficos.
# Genera: imágenes TIFF + JSON, CSV y un plot PNG (mean vs exposición).

import os, time, json, csv, argparse
from datetime import datetime
import numpy as np
import cv2
import matplotlib.pyplot as plt
from picamera2 import Picamera2

# ---------- OLED opcional (SSD1306) ----------
def init_oled(addr_hex):
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import Image
        serial = i2c(port=1, address=addr_hex)
        dev = ssd1306(serial)
        # Blanco fijo
        img = Image.new("1", (dev.width, dev.height), 1)
        dev.display(img)
        return dev
    except Exception as e:
        print(f"[OLED] No disponible ({e}). Seguimos sin OLED…")
        return None

# --------------- utilidades -------------------
def stats(gray):
    total = gray.size
    return {
        "min": int(gray.min()),
        "max": int(gray.max()),
        "mean": float(gray.mean()),
        "std":  float(gray.std()),
        "pct_sat_255": 100.0 * np.sum(gray == 255) / total,
        "pct_black_0": 100.0 * np.sum(gray == 0)  / total,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--use_oled", type=int, default=1, help="1=OLED blanco (0x3C)")
    ap.add_argument("--i2c_addr", default="0x3C")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--tobj", type=float, default=150.0, help="objetivo mean (0–255)")
    ap.add_argument("--tag", default="screen_2cm_fino")
    # rango fino 5–15 ms (1 ms paso)
    ap.add_argument("--exp_ms_start", type=int, default=5)
    ap.add_argument("--exp_ms_end",   type=int, default=15)
    args = ap.parse_args()

    # rutas
    base_dir = os.path.dirname(__file__)
    raw_dir  = os.path.join(base_dir, "..", "data", "raw")
    meta_dir = os.path.join(base_dir, "..", "data", "metadata")
    proc_dir = os.path.join(base_dir, "..", "data", "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)
    os.makedirs(proc_dir, exist_ok=True)

    # OLED blanco (opcional)
    _ = init_oled(int(args.i2c_addr, 16)) if args.use_oled else None

    # cámara
    cam = Picamera2()
    cfg = cam.create_preview_configuration(main={"format":"XRGB8888","size":(args.width,args.height)})
    cam.configure(cfg)
    cam.start()
    cam.set_controls({"AeEnable": False, "AwbEnable": False, "AnalogueGain": args.gain})

    cv2.namedWindow("Exposure sweep fino", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Exposure sweep fino", 640, 480)

    expos_ms = list(range(args.exp_ms_start, args.exp_ms_end + 1, 1))
    rows = []

    print("Controles: n = siguiente | q = salir")
    for ms in expos_ms:
        exp_us = int(ms * 1000)
        cam.set_controls({"ExposureTime": exp_us})
        time.sleep(0.25)

        frame = cam.capture_array()
        bgr = frame[..., :3][:, :, ::-1].copy()
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        met = stats(gray)

        # overlay
        overlay = bgr.copy()
        cv2.putText(overlay, f"Exp:{ms} ms  G:{args.gain:.1f}x",
                    (18,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        cv2.putText(overlay, f"Mean:{met['mean']:.1f}  Sat:{met['pct_sat_255']:.2f}%  Blk:{met['pct_black_0']:.2f}%",
                    (18,80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.imshow("Exposure sweep fino", overlay)

        # guardar
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"ism_{ts}_exp{ms}ms_gain{args.gain:.1f}x_{args.tag}"
        cv2.imwrite(os.path.join(raw_dir,  f"{base}.tiff"), bgr)
        with open(os.path.join(meta_dir, f"{base}.json"), "w") as f:
            json.dump({"exposure_us": exp_us, "gain": args.gain, **met}, f, indent=2)

        rows.append({"exp_ms": ms, **met})

        print(f"exp={ms:2d} ms → mean={met['mean']:.1f}  sat={met['pct_sat_255']:.2f}%  blk={met['pct_black_0']:.2f}%")

        k = cv2.waitKey(0) & 0xFF
        if k == ord('q'):
            break
        # cualquier otra tecla avanza

    cam.close()
    cv2.destroyAllWindows()

    # CSV
    tsall = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(proc_dir, f"exposure_sweep_fino_{tsall}_{args.tag}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["exp_ms","min","max","mean","std","pct_sat_255","pct_black_0"])
        writer.writeheader(); writer.writerows(rows)

    # Plot
    xs = [r["exp_ms"] for r in rows]
    ys = [r["mean"]   for r in rows]
    sat = [r["pct_sat_255"] > 0.5 for r in rows]  # marcamos sat >= 0.5%

    plt.figure(figsize=(6,4.5))
    ok_x  = [x for x,s in zip(xs, sat) if not s]
    ok_y  = [y for y,s in zip(ys, sat) if not s]
    sat_x = [x for x,s in zip(xs, sat) if s]
    sat_y = [y for y,s in zip(ys, sat) if s]
    plt.scatter(ok_x, ok_y, label="OK")
    if sat_x:
        plt.scatter(sat_x, sat_y, marker='x', label="Saturado")
    plt.axhline(args.tobj, linestyle="--", label=f"objetivo≈{int(args.tobj)}")
    plt.title("Mean vs exposición (ms)")
    plt.xlabel("Exposición (ms)")
    plt.ylabel("Mean (0..255)")
    plt.legend()
    plot_path = os.path.join(proc_dir, f"exposure_sweep_fino_{tsall}_{args.tag}.png")
    plt.tight_layout(); plt.savefig(plot_path, dpi=150)
    print(f"\nCSV:  {csv_path}\nPlot: {plot_path}\nListo ✅")

if __name__ == "__main__":
    main()
