#!/usr/bin/env python3
# Barrido de EXPOSICIÓN (útil con OLED SSD1306 1-bit) con vista en vivo.

import os, time, json, argparse
from datetime import datetime
import numpy as np
import cv2

from picamera2 import Picamera2

# ---- OLED opcional (SSD1306) ----
def init_oled(addr_hex):
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import Image
        serial = i2c(port=1, address=addr_hex)
        dev = ssd1306(serial)
        # Blanco total
        img = Image.new("1", (dev.width, dev.height), 1)
        dev.display(img)
        return dev
    except Exception as e:
        print(f"[OLED] No disponible ({e}). Seguimos sin OLED…")
        return None

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
    ap.add_argument("--use_oled", type=int, default=1, help="1=blanco fijo en OLED 0x3C")
    ap.add_argument("--i2c_addr", default="0x3C")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    # lista de exposiciones en microsegundos (ajústala a tu setup de 2 cm)
    ap.add_argument("--expos", default="2000,4000,6000,8000,12000,16000,20000,26000,32000,40000")
    ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--tag", default="screen_2cm")
    args = ap.parse_args()

    # Rutas
    base_dir = os.path.dirname(__file__)
    raw_dir  = os.path.join(base_dir, "..", "data", "raw")
    meta_dir = os.path.join(base_dir, "..", "data", "metadata")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)

    # OLED (blanco fijo)
    dev = init_oled(int(args.i2c_addr, 16)) if args.use_oled else None

    # Cámara
    cam = Picamera2()
    cfg = cam.create_preview_configuration(main={"format":"XRGB8888","size":(args.width,args.height)})
    cam.configure(cfg)
    cam.start()
    cam.set_controls({"AeEnable": False, "AwbEnable": False, "AnalogueGain": args.gain})

    cv2.namedWindow("Exposure sweep", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Exposure sweep", 640, 480)

    expos = [int(x) for x in args.expos.split(",")]

    print("Controles: n = siguiente exposición, q = salir")
    for exp_us in expos:
        cam.set_controls({"ExposureTime": exp_us})
        time.sleep(0.25)

        frame = cam.capture_array()
        bgr = frame[..., :3][:, :, ::-1].copy()
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        met = stats(gray)

        overlay = bgr.copy()
        txt1 = f"Exp:{exp_us/1000:.1f} ms  G:{args.gain:.1f}x"
        txt2 = f"Mean:{met['mean']:.1f}  Sat:{met['pct_sat_255']:.2f}%  Blk:{met['pct_black_0']:.2f}%"
        cv2.putText(overlay, txt1, (18,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        cv2.putText(overlay, txt2, (18,80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.imshow("Exposure sweep", overlay)

        print(f"exp={exp_us:5d} us → mean={met['mean']:.1f}, sat%={met['pct_sat_255']:.2f}, blk%={met['pct_black_0']:.2f}")

        # Guardar
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"ism_{ts}_exp{exp_us//1000}ms_gain{args.gain:.1f}x_{args.tag}"
        cv2.imwrite(os.path.join(raw_dir,  f"{base}.tiff"), bgr)
        with open(os.path.join(meta_dir, f"{base}.json"), "w") as f:
            json.dump({"exposure_us": exp_us, "gain": args.gain, **met}, f, indent=2)

        k = cv2.waitKey(0) & 0xFF
        if k == ord("q"):
            break
        # cualquier otra tecla: pasa al siguiente exp

    cam.close()
    cv2.destroyAllWindows()
    print("Barrido de exposición terminado ✅")

if __name__ == "__main__":
    main()
