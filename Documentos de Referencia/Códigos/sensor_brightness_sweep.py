#!/usr/bin/env python3
# sensor_brightness_sweep.py
# Barrido de brillo de pantalla (OLED SSD1306) vs respuesta del sensor (OV5647).
# Genera TIFF + JSON por punto y un CSV con métricas agregadas.

import os, csv, time, json, argparse, glob
from datetime import datetime
import numpy as np
import cv2

from picamera2 import Picamera2

# OLED opcional (SSD1306 I2C 0x3C)
def init_oled(addr_hex):
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        serial = i2c(port=1, address=addr_hex)
        dev = ssd1306(serial)  # auto size
        return dev
    except Exception as e:
        print(f"[OLED] No disponible ({e}). Continuando sin OLED…")
        return None

def oled_full_white(device, contrast=255):
    if device is None:
        return
    from PIL import Image
    device.contrast(contrast)     # 0..255
    img = Image.new("1", (device.width, device.height), 1)  # todo blanco
    device.display(img)

def oled_off(device):
    if device is None:
        return
    from PIL import Image
    device.contrast(0)
    img = Image.new("1", (device.width, device.height), 0)  # todo negro
    device.display(img)

def stats(img_gray):
    h = cv2.calcHist([img_gray],[0],None,[256],[0,256]).ravel()
    total = img_gray.size
    sat_pct = 100.0 * h[-1] / total
    blk_pct = 100.0 * h[0]  / total
    return {
        "min": int(img_gray.min()),
        "max": int(img_gray.max()),
        "mean": float(img_gray.mean()),
        "std":  float(img_gray.std()),
        "pct_sat_255": float(sat_pct),
        "pct_black_0": float(blk_pct),
    }

def main():
    ap = argparse.ArgumentParser(description="Barrido brillo (OLED) vs respuesta del sensor")
    ap.add_argument("--use_oled", type=int, default=1, help="1=usar OLED SSD1306 (I2C 0x3C), 0=sin OLED")
    ap.add_argument("--i2c_addr", default="0x3C", help="0x3C u 0x3D")
    ap.add_argument("--levels", default="0,32,64,96,128,160,192,224,255", help="niveles de brillo (0..255)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--exposure_us", type=int, default=12000)
    ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--settle_s", type=float, default=0.25, help="tiempo de estabilización antes de capturar")
    ap.add_argument("--tag", default="screen_2cm")
    args = ap.parse_args()

    # Rutas
    base_dir = os.path.dirname(__file__)
    raw_dir  = os.path.join(base_dir, "..", "data", "raw")
    meta_dir = os.path.join(base_dir, "..", "data", "metadata")
    proc_dir = os.path.join(base_dir, "..", "data", "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)
    os.makedirs(proc_dir, exist_ok=True)

    # OLED
    device = None
    if args.use_oled == 1:
        device = init_oled(int(args.i2c_addr, 16))
        if device:
            print(f"[OLED] Detectado: {device.width}x{device.height} @ {args.i2c_addr}")
        else:
            print("[OLED] No disponible. Ejecutando sin OLED…")

    # Cámara
    cam = Picamera2()
    cfg = cam.create_still_configuration(main={"format": "XRGB8888", "size": (args.width, args.height)})
    cam.configure(cfg)
    cam.start()
    # Bloquear en manual para caracterizar
    cam.set_controls({"AeEnable": False, "AwbEnable": False,
                      "ExposureTime": args.exposure_us, "AnalogueGain": args.gain})

    levels = [int(x) for x in args.levels.split(",")]

    # CSV
    ts0 = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(proc_dir, f"brightness_sweep_{ts0}_{args.tag}.csv")
    with open(csv_path, "w", newline="") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=[
            "timestamp","brightness","img_path","min","max","mean","std","pct_sat_255","pct_black_0",
            "exposure_us","gain","width","height","tag"
        ])
        writer.writeheader()

        for b in levels:
            if device:
                oled_full_white(device, contrast=b)
            time.sleep(args.settle_s)

            frame = cam.capture_array()
            bgr = frame[..., :3][:, :, ::-1].copy()
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

            met = stats(gray)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"ism_{ts}_exp{args.exposure_us//1000}ms_gain{args.gain:.1f}x_{args.tag}_b{b}"
            img_path  = os.path.join(raw_dir,  f"{base}.tiff")
            meta_path = os.path.join(meta_dir, f"{base}.json")

            cv2.imwrite(img_path, bgr)

            meta = {
                "timestamp": ts,
                "tag": args.tag,
                "brightness_level": b,
                "camera": {
                    "width": args.width, "height": args.height,
                    "exposure_us": args.exposure_us, "gain": args.gain,
                    "AeEnable": False, "AwbEnable": False
                },
                "metrics": met
            }
            with open(meta_path, "w") as fj:
                json.dump(meta, fj, indent=2)

            row = {"timestamp": ts, "brightness": b, "img_path": img_path,
                   "exposure_us": args.exposure_us, "gain": args.gain,
                   "width": args.width, "height": args.height, "tag": args.tag}
            row.update(met)
            writer.writerow(row)

            print(f"b={b:3d} → mean={met['mean']:.1f}, max={met['max']}, sat%={met['pct_sat_255']:.2f}")

    if device:
        oled_off(device)
    cam.close()
    print(f"\nCSV listo: {csv_path}")
    print("Listo ✅")
if __name__ == "__main__":
    main()
