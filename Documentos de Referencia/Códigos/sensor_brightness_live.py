
#!/usr/bin/env python3
# sensor_brightness_live.py
# Barrido de brillo o exposición con visualización en vivo.

import os, time, json, csv, argparse
import numpy as np
import cv2
from datetime import datetime
from picamera2 import Picamera2

# --- OLED opcional (SSD1306 I2C 0x3C) ---
def init_oled(addr_hex):
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        serial = i2c(port=1, address=addr_hex)
        dev = ssd1306(serial)
        return dev
    except Exception as e:
        print(f"[OLED] No disponible ({e})")
        return None

def oled_full_white(device, contrast=255):
    if device is None:
        return
    from PIL import Image
    device.contrast(contrast)
    img = Image.new("1", (device.width, device.height), 1)
    device.display(img)

def oled_off(device):
    if device is None:
        return
    from PIL import Image
    img = Image.new("1", (device.width, device.height), 0)
    device.display(img)

def stats(gray):
    total = gray.size
    return {
        "min": int(gray.min()),
        "max": int(gray.max()),
        "mean": float(gray.mean()),
        "std":  float(gray.std()),
        "pct_sat_255": 100.0 * np.sum(gray == 255) / total,
        "pct_black_0": 100.0 * np.sum(gray == 0) / total,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--use_oled", type=int, default=1)
    ap.add_argument("--i2c_addr", default="0x3C")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--exposure_us", type=int, default=12000)
    ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--levels", default="0,32,64,96,128,160,192,224,255")
    ap.add_argument("--tag", default="live_2cm")
    args = ap.parse_args()

    # Rutas
    base_dir = os.path.dirname(__file__)
    raw_dir  = os.path.join(base_dir, "..", "data", "raw")
    meta_dir = os.path.join(base_dir, "..", "data", "metadata")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)

    # OLED opcional
    device = init_oled(int(args.i2c_addr, 16)) if args.use_oled else None
    if device:
        print(f"[OLED] Detectado {device.width}x{device.height}")
    else:
        print("[OLED] Desactivado")

    # Cámara
    cam = Picamera2()
    cfg = cam.create_preview_configuration(main={"format":"XRGB8888","size":(args.width,args.height)})
    cam.configure(cfg)
    cam.start()
    cam.set_controls({"AeEnable": False, "AwbEnable": False,
                      "ExposureTime": args.exposure_us, "AnalogueGain": args.gain})

    levels = [int(x) for x in args.levels.split(",")]
    print("Controles: q = salir, n = siguiente nivel")

    cv2.namedWindow("Microscopía Live", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Microscopía Live", 640, 480)

    for b in levels:
        if device:
            oled_full_white(device, contrast=b)
        time.sleep(0.3)

        frame = cam.capture_array()
        bgr = frame[..., :3][:, :, ::-1]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        met = stats(gray)

        overlay = bgr.copy()
        cv2.putText(overlay, f"Brillo:{b} Exp:{args.exposure_us/1000:.1f}ms G:{args.gain:.1f}x",
                    (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        cv2.putText(overlay, f"Mean:{met['mean']:.1f} Sat:{met['pct_sat_255']:.2f}% Blk:{met['pct_black_0']:.2f}%",
                    (20,80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.imshow("Microscopía Live", overlay)
        print(f"b={b:3d} → mean={met['mean']:.1f} sat={met['pct_sat_255']:.2f}% blk={met['pct_black_0']:.2f}%")

        # Guardar TIFF + JSON
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"ism_{ts}_b{b}_exp{args.exposure_us//1000}ms"
        cv2.imwrite(os.path.join(raw_dir, f"{base}.tiff"), bgr)
        with open(os.path.join(meta_dir, f"{base}.json"), "w") as f:
            json.dump(met, f, indent=2)

        # Espera tecla
        k = cv2.waitKey(0) & 0xFF
        if k == ord("q"):
            break

    if device:
        oled_off(device)
    cam.close()
    cv2.destroyAllWindows()
    print("Barrido terminado ✅")

if __name__ == "__main__":
    main()
