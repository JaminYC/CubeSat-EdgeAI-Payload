#!/usr/bin/env python3
# INTISAT — Fourier Ptychography GUI (ROI + MemSafe)
# Escenario: muestra sobre el sensor, iluminación con poca variación.
# - Recorte ROI centrado para subir la súper-res sin OOM
# - Parámetros expuestos: base_scale, pad, ROI, downsample, NA, magnif
# - API dual fpm-py (nueva y clásica)
#
# Requisitos: numpy, opencv-python, Pillow, torch, fpm-py

import os, glob, threading, traceback, importlib, math
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
import numpy as np
import cv2
from PIL import Image, ImageTk

import torch
import fpm_py as fpm

# ===================== Detección API fpm-py =====================
FPM_IMPORT_ERR = None
HAS_NEW_API = False
HAS_OLD_API = hasattr(fpm, "FPM")

try:
    structs_mod = importlib.import_module("fpm_py.core.structs")
    ImageCapture = getattr(structs_mod, "ImageCapture")
    ImageSeries = getattr(structs_mod, "ImageSeries")
    AcquisitionSettings = getattr(structs_mod, "AcquisitionSettings")
    HAS_NEW_API = True
except Exception as e:
    FPM_IMPORT_ERR = str(e)

# ===================== Utilidades =====================
def read_gray01(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"No se pudo leer: {path}")
    return img.astype(np.float32) / 255.0

def to_u8(img01: np.ndarray) -> np.ndarray:
    return np.clip(img01 * 255.0, 0, 255).astype(np.uint8)

def stretch(img01: np.ndarray, p_lo=2, p_hi=98) -> np.ndarray:
    lo, hi = np.percentile(img01, [p_lo, p_hi])
    return np.clip((img01 - lo) / (hi - lo + 1e-9), 0, 1)

def ecc_align(ref01: np.ndarray, mov01: np.ndarray,
              warp_mode=cv2.MOTION_AFFINE, iters=80, eps=1e-5) -> np.ndarray:
    """Alinea mov01 a ref01 por ECC; si falla, devuelve mov01."""
    ref = (ref01 * 255).astype(np.uint8)
    mov = (mov01 * 255).astype(np.uint8)
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp = np.eye(3,3, dtype=np.float32)
    else:
        warp = np.eye(2,3, dtype=np.float32)
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iters, eps)
        _, warp = cv2.findTransformECC(ref, mov, warp, warp_mode, criteria, None, 5)
        if warp_mode == cv2.MOTION_HOMOGRAPHY:
            aligned = cv2.warpPerspective(
                mov01, warp, (ref.shape[1], ref.shape[0]),
                flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REFLECT
            )
        else:
            aligned = cv2.warpAffine(
                mov01, warp, (ref.shape[1], ref.shape[0]),
                flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REFLECT
            )
        return aligned
    except cv2.error:
        return mov01

# ===================== k-vectores =====================
def make_k_vectors_synthetic(n_imgs: int, na_illum: float, wavelength_m: float):
    """ (kx, ky) en rad/m (sin escalar por pixel efectivo). """
    if n_imgs <= 1 or na_illum <= 0.0:
        return [(0.0, 0.0)] * n_imgs
    k0 = 2.0 * np.pi / wavelength_m
    g = int(np.ceil(np.sqrt(n_imgs)))
    cx = np.linspace(-na_illum, na_illum, g)
    cy = np.linspace(-na_illum, na_illum, g)
    pairs = []
    for yy in cy:
        for xx in cx:
            if np.hypot(xx, yy) <= na_illum + 1e-9:
                pairs.append((k0*xx, k0*yy))
    return (pairs[:n_imgs] if len(pairs) >= n_imgs
            else pairs + [(0.0, 0.0)] * (n_imgs - len(pairs)))

# ===================== ImageSeries (API nueva) =====================
def build_image_series_v2(imgs01, kvs_scaled, lam_m, px_m, magnification):
    if len(imgs01) == 0:
        raise RuntimeError("No hay imágenes para construir ImageSeries.")
    H, W = imgs01[0].shape
    eff_px = px_m / float(magnification)            # pixel efectivo (plano objeto)
    du = lam_m / (W * eff_px + 1e-12)

    capts = []
    for im01, (kx_s, ky_s) in zip(imgs01, kvs_scaled):
        im_t = torch.from_numpy(im01.astype(np.float32))  # (H, W)
        kv_t = torch.tensor([kx_s, ky_s], dtype=torch.float32)
        capts.append(ImageCapture(image=im_t, k_vector=kv_t))

    device = torch.device("cpu")
    if hasattr(fpm, "best_device"):
        try: device = fpm.best_device()
        except Exception: pass

    settings = AcquisitionSettings(
        du=float(du),
        wavelength=float(lam_m),
        pixel_size=float(px_m)  # tamaño de pixel del sensor
    )
    series = ImageSeries(captures=capts, settings=settings, device=device)
    return series, du

# ===================== Tamaño de salida =====================
def compute_safe_output_size(img_shape, du, kvs_scaled, base_scale=3, pad=256):
    """ tamaño de salida (H_out, W_out) con margen según desplazamiento |k|/du. """
    H, W = img_shape
    max_shift_x = max(abs(kx) / (du + 1e-12) for kx, _ in kvs_scaled) if kvs_scaled else 0.0
    max_shift_y = max(abs(ky) / (du + 1e-12) for _, ky in kvs_scaled) if kvs_scaled else 0.0
    margin_x = int(math.ceil(max_shift_x)) + int(pad)
    margin_y = int(math.ceil(max_shift_y)) + int(pad)

    W_out_min = base_scale * W
    H_out_min = base_scale * H
    W_out = max(W_out_min, W + 2 * margin_x)
    H_out = max(H_out_min, H + 2 * margin_y)
    if W_out % 2 == 1: W_out += 1
    if H_out % 2 == 1: H_out += 1
    return (H_out, W_out)

def estimate_bytes(h, w, complex_buffers=3, real_buffers=3, dtype_bytes=4):
    """
    Estimación gruesa de memoria: múltiples buffers complejos/real (float32).
    """
    pix = h * w
    return pix * ((complex_buffers * 2) + real_buffers) * dtype_bytes

# ===================== Núcleo reconstrucción =====================
def reconstruct_dual_api(folder: str,
                         lam_nm: float, px_um: float,
                         iters: int, do_align: bool,
                         kmode: str, na_illum: float,
                         magnification: float,
                         roi_size: int, downsample: int,
                         base_scale: int, pad_px: int,
                         logger, set_total, set_progress, set_phase):
    if not (HAS_NEW_API or HAS_OLD_API):
        raise RuntimeError(f"fpm-py no disponible: {FPM_IMPORT_ERR or 'No import'}")

    # 1) listar archivos
    paths = sorted(glob.glob(os.path.join(folder, "*.tif*")) +
                   glob.glob(os.path.join(folder, "*.png")) +
                   glob.glob(os.path.join(folder, "*.jpg")))
    if not paths:
        raise RuntimeError("No se encontraron imágenes .tiff/.tif/.png/.jpg en la carpeta seleccionada.")
    set_total(len(paths))
    logger(f"📂 Carpeta: {folder}")
    logger(f"🖼️  Encontradas: {len(paths)} imágenes")

    # 2) cargar/normalizar + ROI + downsample + alineación
    imgs = []
    ref01 = None
    for i, p in enumerate(paths, start=1):
        im = read_gray01(p)
        im = (im - im.min()) / (im.max() - im.min() + 1e-9)

        # ROI centrado (si aplica)
        if roi_size > 0:
            H, W = im.shape
            r = min(roi_size, H, W)
            y0 = (H - r) // 2
            x0 = (W - r) // 2
            im = im[y0:y0+r, x0:x0+r]

        # Downsample 2x opcional
        if downsample == 2:
            im = cv2.resize(im, (im.shape[1]//2, im.shape[0]//2), interpolation=cv2.INTER_AREA)

        if ref01 is None:
            ref01 = im.copy()
        if do_align and len(paths) > 1:
            im = ecc_align(ref01, im, cv2.MOTION_AFFINE, iters=80)
        imgs.append(im)
        set_progress(i)
        logger(f"  • [{i}/{len(paths)}] {os.path.basename(p)}")

    sample01 = imgs[0]
    H, W = sample01.shape
    lam_m = lam_nm * 1e-9
    px_m  = px_um * 1e-6

    logger("⚙️  Parámetros: "
           f"λ={lam_nm:.1f} nm | pixel={px_um:.3f} µm | iters={iters} | align={do_align} | "
           f"ROI={H}x{W} | ds×{downsample} | base×{base_scale} | pad={pad_px}")

    set_phase(True)
    # 3) API nueva
    if HAS_NEW_API:
        logger(f"🧮 API nueva: ImageSeries (magnif={magnification:.2f}, NA_illum={na_illum:.2f}, k_mode={kmode})")

        if kmode == "grid":
            kvs = make_k_vectors_synthetic(len(imgs), na_illum=float(na_illum), wavelength_m=lam_m)
        else:
            kvs = [(0.0, 0.0)] * len(imgs)

        eff_px = px_m / float(magnification)   # pixel efectivo [m] en plano objeto
        kvs_scaled = [(kx * eff_px, ky * eff_px) for (kx, ky) in kvs]

        series, du = build_image_series_v2(
            imgs01=imgs, kvs_scaled=kvs_scaled,
            lam_m=lam_m, px_m=px_m, magnification=float(magnification)
        )

        H_out, W_out = compute_safe_output_size(
            img_shape=(H, W), du=du, kvs_scaled=kvs_scaled,
            base_scale=base_scale, pad=pad_px
        )

        # Estimar memoria y avisar
        est = estimate_bytes(H_out, W_out)
        if est > 2_000_000_000:  # ~2 GB
            logger(f"⚠️ Estimación RAM ~{est/1e9:.2f} GB. Considera bajar base_scale, ROI o usar ds×2.")
        logger(f"📏 Salida: {H_out}×{W_out} (du={du:.4e})")

        try:
            out = fpm.reconstruct(series, output_image_size=(H_out, W_out), max_iters=int(iters))
        except TypeError:
            terminator = None
            if hasattr(fpm, "iter_ceil"):
                terminator = lambda inp: fpm.iter_ceil(inp, max_iter=int(iters))
            out = fpm.reconstruct(series,
                                  output_image_size=(H_out, W_out),
                                  max_iters=int(iters) if terminator is None else None,
                                  iteration_terminator=terminator)

        if hasattr(out, "image"):
            rec_t = out.image
            if torch.is_tensor(rec_t):
                rec = rec_t.detach().cpu().abs().numpy()
            else:
                rec = np.asarray(rec_t)
        elif torch.is_tensor(out):
            rec = out.detach().cpu().abs().numpy()
        else:
            arr = np.asarray(out, dtype=np.float32)
            rec = np.abs(arr) if np.iscomplexobj(arr) else arr

    # 4) API clásica (fallback)
    else:
        logger(f"🧮 API clásica: FPM(NA_obj=0.08, NA_illum={na_illum:.2f})")
        solver = fpm.FPM(images=imgs, wavelength=lam_m, px_size=px_m, NA_obj=0.08, NA_illum=float(na_illum))
        rec = solver.reconstruct(iterations=int(iters))

    set_phase(False)

    rec = stretch(rec, 2, 98)
    logger("✅ Reconstrucción finalizada.")
    return sample01, rec, paths

# ===================== GUI =====================
class FPMRoiGUI:
    def __init__(self, root):
        self.root = root
        root.title("INTISAT • FPM (ROI + MemSafe)")

        # estado/control — defaults seguros para tu caso
        self.folder = tk.StringVar()
        self.lambda_nm = tk.DoubleVar(value=530.0)
        self.pixel_um = tk.DoubleVar(value=1.12)
        self.iters = tk.IntVar(value=60)
        self.do_align = tk.BooleanVar(value=True)

        self.kmode = tk.StringVar(value="grid")   # grid | zero
        self.na_illum = tk.DoubleVar(value=0.30)  # poca variación angular realista al inicio
        self.magnification = tk.DoubleVar(value=4.0)

        self.roi = tk.IntVar(value=1024)          # ROI centrado (0=sin recorte)
        self.downsample = tk.IntVar(value=1)      # 1 o 2
        self.base_scale = tk.IntVar(value=3)      # subir a 4 si hay RAM
        self.pad_px = tk.IntVar(value=256)

        # top
        top = ttk.Frame(root, padding=8); top.pack(fill="x")
        ttk.Button(top, text="Elegir carpeta…", command=self.pick_folder).pack(side="left")
        ttk.Entry(top, textvariable=self.folder, width=65).pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(top, text="Reconstruir (FPM)", command=self.run_clicked).pack(side="right")

        # controles básicos
        ctr = ttk.Frame(root, padding=8); ctr.pack(fill="x")
        self._spin(ctr, "λ (nm):", self.lambda_nm, 200, 800, 1.0)
        self._spin(ctr, "pixel (µm):", self.pixel_um, 0.5, 10.0, 0.01)
        self._spin(ctr, "iters:", self.iters, 10, 300, 5)
        ttk.Checkbutton(ctr, text="Alinear (ECC)", variable=self.do_align).pack(side="left", padx=(10,0))

        # avanzados
        adv = ttk.Frame(root, padding=8); adv.pack(fill="x")
        self._spin(adv, "Magnif.:", self.magnification, 1.0, 20.0, 0.5)
        self._spin(adv, "NA illum.:", self.na_illum, 0.05, 0.95, 0.05)
        ttk.Label(adv, text="k-vector:").pack(side="left", padx=(12,2))
        ttk.Combobox(adv, values=["grid","zero"], textvariable=self.kmode,
                     width=6, state="readonly").pack(side="left")

        mem = ttk.Frame(root, padding=8); mem.pack(fill="x")
        self._spin(mem, "ROI (px, 0=full):", self.roi, 0, 4096, 64)
        self._spin(mem, "Downsample ×:", self.downsample, 1, 2, 1)
        self._spin(mem, "base_scale ×:", self.base_scale, 1, 5, 1)
        self._spin(mem, "pad (px):", self.pad_px, 0, 1024, 32)

        # progreso
        prog = ttk.Frame(root, padding=8); prog.pack(fill="x")
        self.pb_load = ttk.Progressbar(prog, mode="determinate", length=420, maximum=100)
        self.pb_load.pack(side="left", padx=(0,10))
        self.pb_phase = ttk.Progressbar(prog, mode="indeterminate", length=220)
        self.pb_phase.pack(side="left", padx=(0,10))
        self.count_label = ttk.Label(prog, text="0 / 0"); self.count_label.pack(side="left")

        # logs
        logs = ttk.LabelFrame(root, text="Logs", padding=6); logs.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.txt = tk.Text(logs, height=10, wrap="word"); self.txt.pack(fill="both", expand=True)
        self.txt.configure(state="disabled")

        # paneles
        pan = ttk.Frame(root, padding=8); pan.pack(fill="both", expand=True)
        self.lbl_in  = self._panel(pan, "Muestra (1ra imagen/ROI)")
        self.lbl_out = self._panel(pan, "Reconstrucción FPM")

        self.sample01 = None
        self.recon01  = None
        self.last_paths = []

        api_label = "nueva" if HAS_NEW_API else ("clásica" if HAS_OLD_API else "no disponible")
        self.status = ttk.Label(root, text=f"Listo. fpm-py API detectada: {api_label}")
        self.status.pack(fill="x", padx=8, pady=(0,8))
        if not (HAS_NEW_API or HAS_OLD_API):
            messagebox.showwarning("fpm-py",
                                   f"No se pudo importar fpm-py.\n{FPM_IMPORT_ERR or ''}\n\n"
                                   "Instala/ajusta el paquete en este venv.")

    # helpers GUI
    def _spin(self, parent, text, var, mn, mx, step):
        ttk.Label(parent, text=text).pack(side="left")
        sp = ttk.Spinbox(parent, from_=mn, to=mx, increment=step, textvariable=var, width=10)
        sp.pack(side="left", padx=(2,12))

    def _panel(self, parent, title):
        fr = ttk.LabelFrame(parent, text=title, padding=6)
        fr.pack(side="left", fill="both", expand=True, padx=4)
        lbl = tk.Label(fr, bg="#202020"); lbl.pack(fill="both", expand=True)
        return lbl

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt.configure(state="normal")
        self.txt.insert("end", f"[{ts}] {msg}\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _set_total(self, total: int):
        self._total = max(1, total)
        self.pb_load.configure(maximum=self._total)
        self.pb_load["value"] = 0
        self.count_label.configure(text=f"0 / {self._total}")
        self.root.update_idletasks()

    def _set_progress(self, cur: int):
        self.pb_load["value"] = cur
        self.count_label.configure(text=f"{cur} / {self._total}")
        self.root.update_idletasks()

    def _set_phase(self, on: bool):
        if on: self.pb_phase.start(60)
        else:  self.pb_phase.stop()
        self.root.update_idletasks()

    def _show_img(self, widget: tk.Label, img01: np.ndarray):
        h, w = img01.shape
        maxw = 560
        sc = min(1.0, maxw / float(w))
        vis = cv2.resize(to_u8(img01), (int(w*sc), int(h*sc)), interpolation=cv2.INTER_AREA) if sc != 1.0 else to_u8(img01)
        ph = ImageTk.PhotoImage(Image.fromarray(vis).convert("L"))
        widget.img_ref = ph
        widget.configure(image=ph)

    # acciones
    def pick_folder(self):
        d = filedialog.askdirectory(
            title="Selecciona carpeta (p.ej. data/rawfourierX)",
            initialdir=os.path.join(os.getcwd(), "..", "data")
        )
        if d: self.folder.set(d)

    def run_clicked(self):
        if not (HAS_NEW_API or HAS_OLD_API):
            messagebox.showerror("FPM", f"No se puede ejecutar: fpm-py no disponible.\n{FPM_IMPORT_ERR or ''}")
            return
        if not self.folder.get():
            messagebox.showwarning("Carpeta", "Selecciona primero la carpeta de imágenes.")
            return
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    def _worker(self):
        try:
            self.status.configure(text="Procesando…")
            self._log(f"🚀 Inicio en: {self.folder.get()} (API {'nueva' if HAS_NEW_API else 'clásica'})")
            sample01, rec01, paths = reconstruct_dual_api(
                folder=self.folder.get(),
                lam_nm=self.lambda_nm.get(),
                px_um=self.pixel_um.get(),
                iters=self.iters.get(),
                do_align=self.do_align.get(),
                kmode=self.kmode.get(),
                na_illum=self.na_illum.get(),
                magnification=self.magnification.get(),
                roi_size=self.roi.get(),
                downsample=self.downsample.get(),
                base_scale=self.base_scale.get(),
                pad_px=self.pad_px.get(),
                logger=self._log,
                set_total=self._set_total,
                set_progress=self._set_progress,
                set_phase=self._set_phase
            )
            self.sample01, self.recon01, self.last_paths = sample01, rec01, paths
            self.root.after(0, lambda: self._show_img(self.lbl_in,  self.sample01))
            self.root.after(0, lambda: self._show_img(self.lbl_out, self.recon01))

            out_png = os.path.join(self.folder.get(), "fpm_reconstruction.png")
            cv2.imwrite(out_png, to_u8(self.recon01))

            log_path = os.path.join(self.folder.get(), "recon_log.txt")
            with open(log_path, "w") as f:
                f.write(f"datetime={datetime.now().isoformat()}\n")
                f.write(f"api={'new' if HAS_NEW_API else 'old'}\n")
                f.write(f"folder={self.folder.get()}\n")
                f.write(f"lambda_nm={self.lambda_nm.get()}\n")
                f.write(f"pixel_um={self.pixel_um.get()}\n")
                f.write(f"iters={self.iters.get()}\n")
                f.write(f"align={self.do_align.get()}\n")
                f.write(f"kmode={self.kmode.get()}\n")
                f.write(f"na_illum={self.na_illum.get()}\n")
                f.write(f"magnification={self.magnification.get()}\n")
                f.write(f"roi={self.roi.get()}\n")
                f.write(f"downsample={self.downsample.get()}\n")
                f.write(f"base_scale={self.base_scale.get()}\n")
                f.write(f"pad_px={self.pad_px.get()}\n")
                f.write("files=\n")
                for p in self.last_paths:
                    f.write(f"  - {p}\n")

            self._log(f"💾 Guardado: {out_png}")
            self._log(f"🧾 Log: {log_path}")
            self.status.configure(text="Listo. (ajusta parámetros y reconstruye de nuevo si deseas)")
        except Exception as e:
            tb = traceback.format_exc()
            self._log(f"❌ Error: {e}")
            self._log(tb)
            self.status.configure(text="Error en reconstrucción.")
            messagebox.showerror("Error", f"{e}\n\n{tb}")

def main():
    root = tk.Tk()
    app = FPMRoiGUI(root)
    root.geometry("1280x820")
    root.mainloop()

if __name__ == "__main__":
    main()
