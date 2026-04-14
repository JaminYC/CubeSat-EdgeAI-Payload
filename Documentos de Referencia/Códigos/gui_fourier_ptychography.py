#!/usr/bin/env python3
# gui_fourier_ptychography.py — INTISAT
# Selecciona carpeta con imágenes (p.ej. data/rawfourier/), reconstruye (FPM o Fresnel-multiframe) y aplica SR.

import os, glob, sys, math, traceback
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import numpy as np
import cv2
from PIL import Image, ImageTk

# ====== Opcionales ======
HAVE_FPM = False
try:
    # pip install fpm-py
    from fpm_py import FPM
    HAVE_FPM = True
except Exception:
    HAVE_FPM = False

HAVE_REALESRGAN = False
try:
    # pip install realesrgan
    from realesrgan import RealESRGAN
    HAVE_REALESRGAN = True
except Exception:
    HAVE_REALESRGAN = False

# ====== Utilidades de imagen ======
def read_gray01(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None: raise RuntimeError(f"No se pudo leer: {path}")
    return img.astype(np.float32)/255.0

def to_u8(img01):
    return np.clip(img01*255.0, 0, 255).astype(np.uint8)

def stretch(img01, p_lo=2, p_hi=98):
    lo, hi = np.percentile(img01, [p_lo, p_hi])
    return np.clip((img01 - lo)/(hi-lo + 1e-9), 0, 1)

def bicubic_sr(img01, scale=2):
    im = to_u8(img01)
    h,w = im.shape[:2]
    return cv2.resize(im, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC).astype(np.uint8)

def fresnel_reconstruct_amp(I01, z_m, lam_m, px_m):
    U0 = np.sqrt(np.clip(I01,0,1))
    Ny, Nx = U0.shape
    fx = np.fft.fftfreq(Nx, d=px_m)
    fy = np.fft.fftfreq(Ny, d=px_m)
    FX, FY = np.meshgrid(fx, fy)
    k = 2*np.pi/lam_m
    arg = 1.0 - (lam_m*FX)**2 - (lam_m*FY)**2
    arg = np.clip(arg, 0.0, None)
    H = np.exp(1j * k * z_m * np.sqrt(arg))
    U1 = np.fft.ifft2(np.fft.fft2(U0) * H)
    mag = np.abs(U1)
    return stretch(mag, 2, 98)

def ecc_align(ref01, mov01, warp_mode=cv2.MOTION_AFFINE, iters=100, eps=1e-5):
    # Alinea 'mov01' a 'ref01' con ECC, retorna imagen alineada
    ref = (ref01*255).astype(np.uint8)
    mov = (mov01*255).astype(np.uint8)
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp = np.eye(3,3, dtype=np.float32)
    else:
        warp = np.eye(2,3, dtype=np.float32)
    try:
        cc, warp = cv2.findTransformECC(ref, mov, warp, warp_mode,
                                        (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT, iters, eps),
                                        None, 5)
        if warp_mode == cv2.MOTION_HOMOGRAPHY:
            aligned = cv2.warpPerspective(mov01, warp, (ref.shape[1], ref.shape[0]),
                                          flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        else:
            aligned = cv2.warpAffine(mov01, warp, (ref.shape[1], ref.shape[0]),
                                     flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        return aligned
    except cv2.error:
        # Si falla, devuelve original
        return mov01

# ====== Reconstrucciones ======
def reconstruct_folder(folder, lam_nm, z_mm, px_um, do_align=True,
                       use_fpm=True, fpm_iters=50):
    paths = sorted(glob.glob(os.path.join(folder, "*.tif*")) + glob.glob(os.path.join(folder, "*.png")))
    if not paths:
        raise RuntimeError("No se encontraron imágenes .tiff/.tif/.png en la carpeta seleccionada.")
    # Muestra (primera)
    sample01 = read_gray01(paths[0])

    lam = lam_nm*1e-9
    z   = z_mm*1e-3
    px  = px_um*1e-6

    if use_fpm and HAVE_FPM:
        # Preprocesamiento: lee, normaliza y (opcional) alinea
        imgs = []
        ref01 = sample01
        for p in paths:
            im = read_gray01(p)
            im = (im - im.min())/(im.max()-im.min() + 1e-9)
            if do_align:
                im = ecc_align(ref01, im, cv2.MOTION_AFFINE, iters=80)
            imgs.append(im)
        # Parámetros FPM básicos (ajústalos a tu geometría real si la conoces)
        # NOTA: Si no sabes NA_obj/NA_illum, estos son placeholders razonables para empezar
        NA_obj   = 0.08
        NA_illum = 0.50
        fpm = FPM(images=imgs, wavelength=lam, px_size=px,
                  NA_obj=NA_obj, NA_illum=NA_illum)
        rec = fpm.reconstruct(iterations=int(fpm_iters))  # devuelve float [0..1] o normalizable
        rec = stretch(rec, 2, 98)
        return sample01, rec
    else:
        # Fallback: Fresnel multi-frame (alinear, reconstruir cada frame y promediar)
        ref01 = sample01
        acc = None
        n = 0
        for p in paths:
            im = read_gray01(p)
            im = (im - im.min())/(im.max()-im.min() + 1e-9)
            if do_align:
                im = ecc_align(ref01, im, cv2.MOTION_AFFINE, iters=60)
            rec = fresnel_reconstruct_amp(im, z, lam, px)
            if acc is None:
                acc = rec
            else:
                acc = acc + rec
            n += 1
        rec = acc / max(n,1)
        rec = stretch(rec, 2, 98)
        return sample01, rec

def apply_sr(img01, scale=2, use_realesrgan=False):
    if use_realesrgan and HAVE_REALESRGAN:
        try:
            model_name = "x4plus" if scale==4 else "x2plus"
            model = RealESRGAN(model_name, device="cuda")
            pil_in = Image.fromarray(to_u8(img01)).convert("RGB")
            pil_out = model.predict(pil_in)
            out = cv2.cvtColor(np.array(pil_out), cv2.COLOR_RGB2GRAY)
            return out
        except Exception:
            # Fallback a bicúbica si falla GPU o modelo
            return bicubic_sr(img01, scale=scale)
    else:
        return bicubic_sr(img01, scale=scale)

# ====== GUI ======
class FPGUI:
    def __init__(self, root):
        self.root = root
        root.title("INTISAT • Fourier Ptychography GUI")

        # Vars
        self.folder = tk.StringVar()
        self.lambda_nm = tk.DoubleVar(value=530.0)
        self.z_mm      = tk.DoubleVar(value=3.0)
        self.px_um     = tk.DoubleVar(value=1.12)
        self.fpm_iters = tk.IntVar(value=50)
        self.sr_scale  = tk.IntVar(value=2)
        self.do_align  = tk.BooleanVar(value=True)
        self.use_fpm   = tk.BooleanVar(value=HAVE_FPM)
        self.use_srgan = tk.BooleanVar(value=HAVE_REALESRGAN)

        # Top
        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Elegir carpeta…", command=self.pick_folder).pack(side="left")
        ttk.Entry(top, textvariable=self.folder, width=70).pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(top, text="Reconstruir", command=self.run_pipeline).pack(side="right")

        # Controls
        ctr = ttk.Frame(root, padding=8)
        ctr.pack(fill="x")
        self._spin(ctr, "λ (nm):", self.lambda_nm, 200, 800, 1.0)
        self._spin(ctr, "z (mm):", self.z_mm, 0.2, 10.0, 0.1)
        self._spin(ctr, "pixel (µm):", self.px_um, 0.5, 10.0, 0.01)
        self._spin(ctr, "FP iters:", self.fpm_iters, 10, 200, 5)
        ttk.Label(ctr, text="SR escala:").pack(side="left", padx=(10,2))
        ttk.Combobox(ctr, values=[2,4], textvariable=self.sr_scale, width=4, state="readonly").pack(side="left")
        ttk.Checkbutton(ctr, text="Alinear", variable=self.do_align).pack(side="left", padx=8)
        ttk.Checkbutton(ctr, text="Usar FPM", variable=self.use_fpm,
                        state="normal" if HAVE_FPM else "disabled").pack(side="left", padx=8)
        ttk.Checkbutton(ctr, text="Real-ESRGAN", variable=self.use_srgan,
                        state="normal" if HAVE_REALESRGAN else "disabled").pack(side="left", padx=8)
        ttk.Button(ctr, text="Guardar salida", command=self.save_outputs).pack(side="right")

        # Panels
        pan = ttk.Frame(root, padding=8)
        pan.pack(fill="both", expand=True)
        self.lbl_raw     = self._panel(pan, "Original (muestra)")
        self.lbl_recon   = self._panel(pan, "Reconstrucción (FPM/Fresnel MF)")
        self.lbl_sr      = self._panel(pan, "Super-resolución")

        # Buffers
        self.sample01 = None
        self.recon01  = None
        self.sr_img   = None

        # Info
        self.status = tk.StringVar(value="Listo.")
        ttk.Label(root, textvariable=self.status, anchor="w").pack(fill="x", padx=8, pady=(0,8))

    def _spin(self, parent, text, var, mn, mx, step):
        ttk.Label(parent, text=text).pack(side="left")
        sp = ttk.Spinbox(parent, from_=mn, to=mx, increment=step, textvariable=var, width=8)
        sp.pack(side="left", padx=(2,10))

    def _panel(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        frame.pack(side="left", fill="both", expand=True, padx=4)
        lbl = tk.Label(frame, bg="#202020")
        lbl.pack(fill="both", expand=True)
        return lbl

    def pick_folder(self):
        d = filedialog.askdirectory(title="Selecciona carpeta con imágenes",
                                    initialdir=os.path.join(os.getcwd(), "..", "data"))
        if d:
            self.folder.set(d)

    def show_img(self, widget: tk.Label, img01):
        h, w = img01.shape
        maxw = 540
        scale = min(1.0, maxw/float(w))
        if scale != 1.0:
            vis = cv2.resize(to_u8(img01), (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        else:
            vis = to_u8(img01)
        im = Image.fromarray(vis).convert("L")
        ph = ImageTk.PhotoImage(im)
        widget.img_ref = ph
        widget.configure(image=ph)

    def run_pipeline(self):
        try:
            if not self.folder.get():
                raise RuntimeError("Selecciona primero la carpeta (p.ej. data/rawfourier).")
            self.status.set("Procesando… (puede tardar)")
            self.root.update_idletasks()

            sample01, recon01 = reconstruct_folder(
                self.folder.get(),
                lam_nm=self.lambda_nm.get(),
                z_mm=self.z_mm.get(),
                px_um=self.px_um.get(),
                do_align=self.do_align.get(),
                use_fpm=self.use_fpm.get(),
                fpm_iters=self.fpm_iters.get()
            )
            self.sample01 = sample01
            self.recon01  = recon01
            self.show_img(self.lbl_raw, sample01)
            self.show_img(self.lbl_recon, recon01)

            # SR
            self.sr_img = apply_sr(recon01, scale=self.sr_scale.get(), use_realesrgan=self.use_srgan.get())
            self.show_img(self.lbl_sr, (self.sr_img.astype(np.float32)/255.0))
            self.status.set("Hecho. Ajusta parámetros y vuelve a 'Reconstruir' si deseas.")
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("Error", f"{e}\n\n{tb}")
            self.status.set("Error. Revisa parámetros o imágenes.")

    def save_outputs(self):
        try:
            if self.recon01 is None:
                raise RuntimeError("Aún no hay reconstrucción. Pulsa 'Reconstruir' primero.")
            out_dir = filedialog.askdirectory(title="Carpeta de salida", initialdir=self.folder.get())
            if not out_dir: return
            # Guarda sample, recon y SR
            cv2.imwrite(os.path.join(out_dir, "sample.png"), to_u8(self.sample01))
            cv2.imwrite(os.path.join(out_dir, "reconstruction.png"), to_u8(self.recon01))
            if self.sr_img is not None:
                cv2.imwrite(os.path.join(out_dir, f"reconstruction_SR_x{self.sr_scale.get()}.png"), self.sr_img)
            # Log simple
            with open(os.path.join(out_dir, "recon_log.txt"), "w") as f:
                f.write(f"lambda_nm={self.lambda_nm.get()}\n")
                f.write(f"z_mm={self.z_mm.get()}\n")
                f.write(f"pixel_um={self.px_um.get()}\n")
                f.write(f"use_fpm={self.use_fpm.get()} (HAVE_FPM={HAVE_FPM})\n")
                f.write(f"fpm_iters={self.fpm_iters.get()}\n")
                f.write(f"align={self.do_align.get()}\n")
                f.write(f"sr_scale={self.sr_scale.get()} use_srgan={self.use_srgan.get()} (HAVE_REALESRGAN={HAVE_REALESRGAN})\n")
            messagebox.showinfo("Guardado", f"Archivos exportados en:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

def main():
    root = tk.Tk()
    gui = FPGUI(root)
    root.geometry("1720x760")
    root.mainloop()

if __name__ == "__main__":
    main()
