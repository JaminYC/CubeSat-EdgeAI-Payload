#!/usr/bin/env python3
# process_batch_fresnel.py — Reconstrucción Fresnel en lote + métricas de foco + CSV
# Recorre data/raw/*.tiff, aplica propagación (espectro angular) para varios z,
# guarda PNGs en data/processed/fresnel y un CSV con métricas por imagen y z.

import os, glob, json, argparse, csv
import numpy as np
import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
RAW_DIR  = os.path.join(DATA_DIR, "raw")
META_DIR = os.path.join(DATA_DIR, "metadata")
OUT_DIR  = os.path.join(DATA_DIR, "processed", "fresnel")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- Utilidades ----------
def load_gray_01(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    return (img.astype(np.float32) / 255.0, img.shape)

def save_png01(path, arr01):
    arr = np.clip(arr01 * 255.0, 0, 255).astype(np.uint8)
    cv2.imwrite(path, arr)

def variance_of_laplacian(im01):
    return cv2.Laplacian((im01*255).astype(np.uint8), cv2.CV_64F).var()

def tenengrad(im01):  # Sobel-based focus measure
    gx = cv2.Sobel((im01*255).astype(np.uint8), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel((im01*255).astype(np.uint8), cv2.CV_32F, 0, 1, ksize=3)
    g2 = gx*gx + gy*gy
    return float(np.mean(g2))

def rms_contrast(im01):
    return float(im01.std())

def fresnel_reconstruct_amp(I01, z, wavelength, px):
    """
    Reconstrucción por espectro angular. Usa amplitud = sqrt(I).
    I01: imagen [0..1] (intensidad)
    z: distancia (m)
    wavelength: lambda (m)
    px: pitch de pixel (m)
    Return: magnitud |U| normalizada [0..1]
    """
    U0 = np.sqrt(np.clip(I01, 0.0, 1.0))

    Ny, Nx = U0.shape
    fx = np.fft.fftfreq(Nx, d=px)
    fy = np.fft.fftfreq(Ny, d=px)
    FX, FY = np.meshgrid(fx, fy)

    k = 2*np.pi / wavelength
    # Filtro de paso: evitar sqrt de negativos por altas frecuencias (apodización suave)
    arg = 1.0 - (wavelength*FX)**2 - (wavelength*FY)**2
    arg = np.clip(arg, 0.0, None)
    H = np.exp(1j * k * z * np.sqrt(arg))

    U1 = np.fft.ifft2(np.fft.fft2(U0) * H)
    mag = np.abs(U1)
    # Normalización robusta (percentiles para evitar saturación)
    lo, hi = np.percentile(mag, [1, 99])
    mag01 = np.clip((mag - lo) / (hi - lo + 1e-9), 0, 1)
    return mag01

def read_meta_if_exists(raw_path):
    base = os.path.splitext(os.path.basename(raw_path))[0]
    meta_path = os.path.join(META_DIR, base + ".json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            return json.load(f)
    return {}

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Batch Fresnel reconstruction + focus metrics")
    ap.add_argument("--lambda_nm", type=float, default=530.0, help="Longitud de onda (nm), p.ej. 530 para OLED verde")
    ap.add_argument("--px_um", type=float, default=1.12, help="Tamaño de pixel (μm), OV5647≈1.12")
    ap.add_argument("--z_mm", type=str, default="2.0,3.0,4.0",
                    help="Lista de planos z en mm, ej: 1.0,2.0,3.5")
    ap.add_argument("--glob", type=str, default="*.tiff", help="Patrón de archivos en data/raw")
    ap.add_argument("--limit", type=int, default=0, help="Procesar solo N archivos (0 = todos)")
    args = ap.parse_args()

    wavelength = args.lambda_nm * 1e-9
    px = args.px_um * 1e-6
    z_list = [float(z)*1e-3 for z in args.z_mm.split(",")]

    raw_list = sorted(glob.glob(os.path.join(RAW_DIR, args.glob)))
    if args.limit > 0:
        raw_list = raw_list[:args.limit]

    csv_path = os.path.join(OUT_DIR, "fresnel_metrics.csv")
    with open(csv_path, "w", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow([
            "raw_file","z_mm","lambda_nm","px_um","lap_var","tenengrad","rms_contrast","out_png"
        ])

        for i, raw_path in enumerate(raw_list, 1):
            print(f"[{i}/{len(raw_list)}] {os.path.basename(raw_path)}")
            I01, shape = load_gray_01(raw_path)
            meta = read_meta_if_exists(raw_path)

            for z in z_list:
                recon01 = fresnel_reconstruct_amp(I01, z, wavelength, px)

                # métricas
                m_lap  = variance_of_laplacian(recon01)
                m_tng  = tenengrad(recon01)
                m_rms  = rms_contrast(recon01)

                # guardar
                base = os.path.splitext(os.path.basename(raw_path))[0]
                out_name = f"{base}_FRESNEL_z{int(round(z*1e3))}mm_lambda{int(args.lambda_nm)}nm.png"
                out_path = os.path.join(OUT_DIR, out_name)
                save_png01(out_path, recon01)

                writer.writerow([
                    os.path.basename(raw_path), f"{z*1e3:.3f}", f"{args.lambda_nm:.1f}", f"{args.px_um:.2f}",
                    f"{m_lap:.4f}", f"{m_tng:.4f}", f"{m_rms:.6f}", out_name
                ])

    print(f"✅ Listo. PNGs en: {OUT_DIR}")
    print(f"✅ Métricas en:   {csv_path}")

if __name__ == "__main__":
    main()
