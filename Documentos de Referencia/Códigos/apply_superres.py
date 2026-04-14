#!/usr/bin/env python3
# apply_superres.py — aplica SR x2/x4 a los PNG de fresnel.
# Si Real-ESRGAN está instalado, lo usa; si no, cae a bicúbica.

import os, glob, argparse
import cv2
from PIL import Image

try:
    from realesrgan import RealESRGAN
    HAVE_REALESRGAN = True
except Exception:
    HAVE_REALESRGAN = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DIR = os.path.join(BASE_DIR, "..", "data", "processed", "fresnel")
OUT_DIR  = os.path.join(BASE_DIR, "..", "data", "processed", "superres")
os.makedirs(OUT_DIR, exist_ok=True)

def bicubic_sr(img_bgr, scale=2):
    h, w = img_bgr.shape[:2]
    return cv2.resize(img_bgr, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=2, choices=[2,4], help="Factor SR")
    ap.add_argument("--glob", type=str, default="*_FRESNEL_*.png", help="Patrón de entrada")
    args = ap.parse_args()

    if HAVE_REALESRGAN:
        print("🧠 Real-ESRGAN detectado. Usando modelo preentrenado.")
        # Nota: Ajusta el nombre del modelo si tienes otro
        model_name = "x4plus" if args.scale==4 else "x2plus"
        try:
            model = RealESRGAN(model_name, device="cuda")
        except Exception as e:
            print(f"[WARN] No se pudo cargar Real-ESRGAN ({e}). Usaré bicúbica.")
            HAVE_REALESRGAN_local = False
        else:
            HAVE_REALESRGAN_local = True
    else:
        print("ℹ️ Real-ESRGAN no disponible. Usaré bicúbica.")
        HAVE_REALESRGAN_local = False

    files = sorted(glob.glob(os.path.join(PROC_DIR, args.glob)))
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {os.path.basename(f)}")
        if HAVE_REALESRGAN_local:
            im = Image.open(f).convert("RGB")
            sr  = model.predict(im)
            out = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(f))[0] + f"_SRx{args.scale}.png")
            sr.save(out)
        else:
            img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            sr  = bicubic_sr(img, scale=args.scale)
            out = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(f))[0] + f"_SRx{args.scale}_bicubic.png")
            cv2.imwrite(out, sr)

    print(f"✅ SR listo en: {OUT_DIR}")

if __name__ == "__main__":
    main()
