#!/usr/bin/env python3
# gui_reconstruct.py — GUI para cargar .tiff, reconstruir Fresnel y aplicar super-resolución

import os, sys, math
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import numpy as np
import cv2
from PIL import Image, ImageTk

# --- SR opcional: Real-ESRGAN ---
HAVE_REALESRGAN = False
try:
    from realesrgan import RealESRGAN   # pip install realesrgan  (opcional)
    HAVE_REALESRGAN = True
except Exception:
    HAVE_REALESRGAN = False

# ---------- Utilidades de imagen ----------
def read_gray01(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"No se pudo leer: {path}")
    return (img.astype(np.float32) / 255.0, img.shape)

def to_u8_img(arr01):
    arr = np.clip(arr01 * 255.0, 0, 255).astype(np.uint8)
    return arr

def to_pil(arr01):
    return Image.fromarray(to_u8_img(arr01))

def stretch_robust(img, lo=1, hi=99):
    a, b = np.percentile(img, [lo, hi])
    out = (img - a) / (b - a + 1e-9)
    return np.clip(out, 0, 1)

def bicubic_sr(img01, scale=2):
    im = to_u8_img(img01)
    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    h, w = im.shape[:2]
    sr = cv2.resize(im, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
    # devolver en escala [0..1] gris
    sr_gray = cv2.cvtColor(sr, cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    return sr_gray

# ---------- Fresnel (espectro angular) ----------
def fresnel_reconstruct_amp(I01, z_m, lam_m, px_m):
    """
    I01: intensidad [0..1]
    z_m: distancia (m)
    lam_m: longitud de onda (m)
    px_m: pitch de pixel (m)
    return: |U| normalizado [0..1]
    """
    U0 = np.sqrt(np.clip(I01, 0, 1))
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
    return stretch_robust(mag, 2, 98)

# ---------- GUI ----------
class ReconGUI:
    def __init__(self, root):
        self.root = root
        root.title("INTISAT • Reconstrucción Fresnel + Super-resolución")

        # Parámetros
        self.file_path = tk.StringVar()
        self.lambda_nm = tk.DoubleVar(value=530.0)  # OLED verde
        self.z_mm      = tk.DoubleVar(value=3.0)
        self.px_um     = tk.DoubleVar(value=1.12)   # OV5647 ~1.12 µm
        self.sr_scale  = tk.IntVar(value=2)
        self.use_realesrgan = tk.BooleanVar(value=HAVE_REALESRGAN)

        # Barra superior
        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Abrir TIFF…", command=self.open_file).pack(side="left")
        ttk.Entry(top, textvariable=self.file_path, width=60).pack(side="left", padx=6, fill="x", expand=True)

        # Controles
        controls = ttk.Frame(root, padding=8)
        controls.pack(fill="x")
        self._add_spin(controls, "λ (nm):", self.lambda_nm, 200, 800, 1.0)
        self._add_spin(controls, "z (mm):", self.z_mm, 0.5, 10.0, 0.1)
        self._add_spin(controls, "pixel (µm):", self.px_um, 0.5, 5.0, 0.01)
        ttk.Label(controls, text="SR escala:").pack(side="left", padx=(12,2))
        ttk.Combobox(controls, values=[2,4], textvariable=self.sr_scale, width=4, state="readonly").pack(side="left")
        ttk.Checkbutton(controls, text="Real-ESRGAN", variable=self.use_realesrgan,
                        state="normal" if HAVE_REALESRGAN else "disabled").pack(side="left", padx=8)
        ttk.Button(controls, text="Reconstruir", command=self.run_all).pack(side="right")

        # Lienzos de imágenes
        canv = ttk.Frame(root, padding=8)
        canv.pack(fill="both", expand=True)
        self.canvas_raw     = self._make_panel(canv, "Original")
        self.canvas_fresnel = self._make_panel(canv, "Fresnel")
        self.canvas_sr      = self._make_panel(canv, "Super-resolución")

        # estados
        self.img_raw = None
        self.img_fresnel = None
        self.img_sr = None

    def _add_spin(self, parent, label, var, mn, mx, step):
        ttk.Label(parent, text=label).pack(side="left")
        sp = ttk.Spinbox(parent, from_=mn, to=mx, increment=step, textvariable=var, width=8)
        sp.pack(side="left", padx=(2,12))

    def _make_panel(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        frame.pack(side="left", fill="both", expand=True, padx=4)
        canvas = tk.Label(frame, bg="#202020")
        canvas.pack(fill="both", expand=True)
        return canvas

    def open_file(self):
        f = filedialog.askopenfilename(title="Selecciona imagen TIFF",
                                       filetypes=[("TIFF","*.tif *.tiff"),("PNG","*.png"),("Todos","*.*")],
                                       initialdir=os.path.join(os.getcwd(), "..", "data", "raw"))
        if f:
            self.file_path.set(f)

    def run_all(self):
        try:
            if not self.file_path.get():
                raise RuntimeError("Selecciona un archivo primero.")

            lam = self.lambda_nm.get()*1e-9
            z   = self.z_mm.get()*1e-3
            px  = self.px_um.get()*1e-6

            # 1) Cargar
            raw01, _ = read_gray01(self.file_path.get())
            self.img_raw = raw01
            self._show_img(self.canvas_raw, raw01)

            # 2) Fresnel
            fres01 = fresnel_reconstruct_amp(raw01, z, lam, px)
            self.img_fresnel = fres01
            self._show_img(self.canvas_fresnel, fres01)

            # 3) Super-res
            if self.use_realesrgan.get() and HAVE_REALESRGAN:
                try:
                    scale = self.sr_scale.get()
                    model_name = "x4plus" if scale==4 else "x2plus"
                    model = RealESRGAN(model_name, device="cuda")
                    pil_in = to_pil(fres01).convert("RGB")
                    pil_out = model.predict(pil_in)
                    sr_gray = cv2.cvtColor(np.array(pil_out), cv2.COLOR_RGB2GRAY).astype(np.float32)/255.0
                    self.img_sr = sr_gray
                except Exception as e:
                    messagebox.showwarning("Real-ESRGAN", f"No se pudo usar Real-ESRGAN ({e}). Uso bicúbica.")
                    self.img_sr = bicubic_sr(fres01, scale=self.sr_scale.get())
            else:
                self.img_sr = bicubic_sr(fres01, scale=self.sr_scale.get())

            self._show_img(self.canvas_sr, self.img_sr)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _show_img(self, canvas: tk.Label, img01):
        # Redimensionar a ancho razonable manteniendo aspecto
        h, w = img01.shape
        maxw = 540  # ajusta para tu pantalla
        scale = min(1.0, maxw / w)
        if scale != 1.0:
            img_res = cv2.resize(to_u8_img(img01), (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        else:
            img_res = to_u8_img(img01)
        # pasar a PhotoImage
        im = Image.fromarray(img_res)
        im = im.convert("L")
        photo = ImageTk.PhotoImage(im)
        canvas.img_ref = photo  # evita GC
        canvas.configure(image=photo)

def main():
    root = tk.Tk()
    ReconGUI(root)
    root.geometry("1720x720")  # ajusta a tu monitor
    root.mainloop()

if __name__ == "__main__":
    main()
