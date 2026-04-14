#!/usr/bin/env python3
# INTISAT — Fourier Ptychography GUI (fpm-py v2 API) con progreso y logs

import os, glob, threading, traceback
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
import numpy as np
import cv2
from PIL import Image, ImageTk

# ===== fpm-py v2 API =====
FPM_IMPORT_ERR = None
try:
    import fpm_py as fpm   # v2: expose ImageCapture, ImageSeries, reconstruct
    HAVE_FPM = True
except Exception as e:
    HAVE_FPM = False
    FPM_IMPORT_ERR = str(e)

# ===== utilidades imagen =====
def read_gray01(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"No se pudo leer: {path}")
    return img.astype(np.float32)/255.0

def to_u8(img01: np.ndarray) -> np.ndarray:
    return np.clip(img01*255.0, 0, 255).astype(np.uint8)

def stretch(img01: np.ndarray, p1=2, p2=98) -> np.ndarray:
    lo, hi = np.percentile(img01, [p1, p2])
    return np.clip((img01 - lo)/(hi - lo + 1e-9), 0, 1)

def ecc_align(ref01: np.ndarray, mov01: np.ndarray,
              warp_mode=cv2.MOTION_AFFINE, iters=80, eps=1e-5) -> np.ndarray:
    ref = (ref01*255).astype(np.uint8)
    mov = (mov01*255).astype(np.uint8)
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp = np.eye(3,3, dtype=np.float32)
    else:
        warp = np.eye(2,3, dtype=np.float32)
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iters, eps)
        _, warp = cv2.findTransformECC(ref, mov, warp, warp_mode, criteria, None, 5)
        if warp_mode == cv2.MOTION_HOMOGRAPHY:
            aligned = cv2.warpPerspective(mov01, warp, (ref.shape[1], ref.shape[0]),
                                          flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP,
                                          borderMode=cv2.BORDER_REFLECT)
        else:
            aligned = cv2.warpAffine(mov01, warp, (ref.shape[1], ref.shape[0]),
                                     flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP,
                                     borderMode=cv2.BORDER_REFLECT)
        return aligned
    except cv2.error:
        return mov01

# ===== k-vectores sintéticos =====
def make_k_vectors_synthetic(n_imgs: int, na_illum: float, wavelength_m: float):
    """
    Genera un grid cuadrado de k-vectores en el plano, acotado por NA_illum.
    fpm-py espera 'k_vector' por captura (par 2D). Usamos aproximación:
      kx = (2π/λ) * sx,  ky = (2π/λ) * sy,  con sqrt(sx^2+sy^2) <= NA_illum
    """
    if n_imgs <= 1 or na_illum <= 0.0:
        return [(0.0, 0.0)] * n_imgs

    k0 = 2.0 * np.pi / wavelength_m
    g = int(np.ceil(np.sqrt(n_imgs)))
    cx = np.linspace(-na_illum, na_illum, g)
    cy = np.linspace(-na_illum, na_illum, g)
    pairs = []
    for yy in cy:
        for xx in cx:
            if np.sqrt(xx*xx + yy*yy) <= na_illum + 1e-9:
                pairs.append((k0*xx, k0*yy))
    # recorta/replica para tener exactamente n_imgs
    if len(pairs) >= n_imgs:
        return pairs[:n_imgs]
    else:
        # si faltan, completa con (0,0)
        return pairs + [(0.0, 0.0)] * (n_imgs - len(pairs))

# ===== núcleo FPM con progreso =====
def run_fpm_folder(folder: str,
                   lam_nm: float, px_um: float,
                   magnification: float, na_illum: float,
                   iters: int, do_align: bool,
                   kv_mode: str,      # "zero" | "grid"
                   logger, set_total, set_progress, set_phase):
    if not HAVE_FPM:
        raise RuntimeError(f"fpm-py no disponible: {FPM_IMPORT_ERR or 'import error'}")

    paths = sorted(glob.glob(os.path.join(folder, "*.tif*")) +
                   glob.glob(os.path.join(folder, "*.png")) +
                   glob.glob(os.path.join(folder, "*.jpg")))
    if not paths:
        raise RuntimeError("No se encontraron imágenes .tiff/.tif/.png/.jpg en la carpeta seleccionada.")

    set_total(len(paths))
    logger(f"📂 Carpeta: {folder}")
    logger(f"🖼️  Encontradas: {len(paths)} imágenes")

    imgs = []
    ref01 = None
    for i, p in enumerate(paths, start=1):
        im = read_gray01(p)
        im = (im - im.min())/(im.max() - im.min() + 1e-9)  # normalize
        if ref01 is None:
            ref01 = im.copy()
        if do_align:
            im = ecc_align(ref01, im, cv2.MOTION_AFFINE, iters=80)
        imgs.append(im)
        set_progress(i)
        logger(f"  • [{i}/{len(paths)}] {os.path.basename(p)}")

    lam_m = lam_nm * 1e-9
    px_um = float(px_um)
    px_m  = px_um * 1e-6
    mag   = float(magnification)

    # Construcción de ImageSeries (fpm-py v2)
    captures = []
    if kv_mode == "grid":
        kvs = make_k_vectors_synthetic(len(imgs), na_illum=float(na_illum), wavelength_m=lam_m)
    else:
        kvs = [(0.0, 0.0)] * len(imgs)  # zero-k

    for im, kv in zip(imgs, kvs):
        cap = fpm.ImageCapture(image=im, k_vector=kv)
        captures.append(cap)

    series = fpm.ImageSeries(
        captures=captures,
        magnification=mag,
        pixel_size=px_um  # micras según docs
    )

    logger(f"⚙️  Parámetros: λ={lam_nm:.1f} nm | pixel={px_um:.3f} µm | mag={mag:.2f} | NA_illum={na_illum:.2f} | iters={iters} | k_mode={kv_mode}")

    # Reconstrucción (sin callback -> barra indeterminada)
    set_phase(True)
    logger("🧮 Reconstruyendo con fpm.reconstruct(series)…")
    out = fpm.reconstruct(series,
                          iteration_terminator=lambda inputs: fpm.iter_ceil(inputs, max_iter=int(iters)))
    set_phase(False)

    # 'out' puede traer amplitud, fase o imagen; asumimos intensidad normalizada
    if hasattr(out, "image"):
        rec = out.image
    else:
        rec = np.asarray(out, dtype=np.float32)

    rec = stretch(rec, 2, 98)
    logger("✅ Reconstrucción finalizada.")
    return imgs[0], rec

# ===== GUI =====
class FPMGuiV2:
    def __init__(self, root):
        self.root = root
        root.title("INTISAT • Fourier Ptychography (fpm-py v2) — Progreso y logs")

        # Estado
        self.folder = tk.StringVar()
        self.lambda_nm = tk.DoubleVar(value=530.0)
        self.pixel_um = tk.DoubleVar(value=1.12)
        self.magnification = tk.DoubleVar(value=4.0)  # ajusta según tu setup
        self.na_illum = tk.DoubleVar(value=0.50)      # control del grid sintético
        self.iters = tk.IntVar(value=50)
        self.do_align = tk.BooleanVar(value=True)
        self.kmode = tk.StringVar(value="grid")       # "grid" o "zero"

        # Top
        top = ttk.Frame(root, padding=8); top.pack(fill="x")
        ttk.Button(top, text="Elegir carpeta…", command=self.pick_folder).pack(side="left")
        ttk.Entry(top, textvariable=self.folder, width=65).pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(top, text="Reconstruir (FPM)", command=self.run_clicked).pack(side="right")

        # Controles
        ctr = ttk.Frame(root, padding=8); ctr.pack(fill="x")
        self._spin(ctr, "λ (nm):", self.lambda_nm, 200, 800, 1.0)
        self._spin(ctr, "pixel (µm):", self.pixel_um, 0.5, 10.0, 0.01)
        self._spin(ctr, "Magnif.:", self.magnification, 1.0, 20.0, 0.5)
        self._spin(ctr, "NA illum:", self.na_illum, 0.05, 0.95, 0.05)
        self._spin(ctr, "Iters:", self.iters, 10, 300, 5)
        ttk.Checkbutton(ctr, text="Alinear (ECC)", variable=self.do_align).pack(side="left", padx=(10, 0))
        ttk.Label(ctr, text="k-vector:").pack(side="left", padx=(16,2))
        ttk.Combobox(ctr, values=["grid","zero"], textvariable=self.kmode, width=6, state="readonly").pack(side="left")

        # Progreso
        prog = ttk.Frame(root, padding=8); prog.pack(fill="x")
        self.pb_load = ttk.Progressbar(prog, mode="determinate", length=420, maximum=100)
        self.pb_load.pack(side="left", padx=(0, 10))
        self.pb_phase = ttk.Progressbar(prog, mode="indeterminate", length=220)
        self.pb_phase.pack(side="left", padx=(0, 10))
        self.count_label = ttk.Label(prog, text="0 / 0"); self.count_label.pack(side="left")

        # Logs
        logs = ttk.LabelFrame(root, text="Logs", padding=6); logs.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.txt = tk.Text(logs, height=10, wrap="word"); self.txt.pack(fill="both", expand=True)
        self.txt.configure(state="disabled")

        # Paneles
        pan = ttk.Frame(root, padding=8); pan.pack(fill="both", expand=True)
        self.lbl_in  = self._panel(pan, "Muestra (1ra imagen)")
        self.lbl_out = self._panel(pan, "Reconstrucción FPM")

        self.sample01 = None
        self.recon01  = None

        # Estado
        self.status = ttk.Label(root, text="Listo."); self.status.pack(fill="x", padx=8, pady=(0,8))

        if not HAVE_FPM:
            messagebox.showwarning("fpm-py", f"No se pudo importar fpm-py.\n{FPM_IMPORT_ERR or ''}\n\n"
                                             "Asegúrate de instalarlo en este venv:\n"
                                             "  pip install fpm-py\n"
                                             "y que torch esté disponible (CPU):\n"
                                             "  pip install --extra-index-url https://download.pytorch.org/whl/cpu torch")

    # ---- helpers GUI ----
    def _spin(self, parent, text, var, mn, mx, step):
        ttk.Label(parent, text=text).pack(side="left")
        sp = ttk.Spinbox(parent, from_=mn, to=mx, increment=step, textvariable=var, width=8)
        sp.pack(side="left", padx=(2, 12))

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
        else:   self.pb_phase.stop()
        self.root.update_idletasks()

    def _show_img(self, widget: tk.Label, img01: np.ndarray):
        h, w = img01.shape
        maxw = 560
        sc = min(1.0, maxw/float(w))
        vis = cv2.resize(to_u8(img01), (int(w*sc), int(h*sc)), interpolation=cv2.INTER_AREA) if sc != 1.0 else to_u8(img01)
        ph = ImageTk.PhotoImage(Image.fromarray(vis).convert("L"))
        widget.img_ref = ph
        widget.configure(image=ph)

    # ---- acciones ----
    def pick_folder(self):
        d = filedialog.askdirectory(title="Selecciona carpeta (p.ej. data/rawfourier)",
                                    initialdir=os.path.join(os.getcwd(), "..", "data"))
        if d: self.folder.set(d)

    def run_clicked(self):
        if not HAVE_FPM:
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
            self._log(f"🚀 Inicio en: {self.folder.get()}")
            sample01, rec01 = run_fpm_folder(
                folder=self.folder.get(),
                lam_nm=self.lambda_nm.get(),
                px_um=self.pixel_um.get(),
                magnification=self.magnification.get(),
                na_illum=self.na_illum.get(),
                iters=self.iters.get(),
                do_align=self.do_align.get(),
                kv_mode=self.kmode.get(),
                logger=self._log,
                set_total=self._set_total,
                set_progress=self._set_progress,
                set_phase=self._set_phase
            )
            self.sample01, self.recon01 = sample01, rec01
            self.root.after(0, lambda: self._show_img(self.lbl_in,  self.sample01))
            self.root.after(0, lambda: self._show_img(self.lbl_out, self.recon01))
            out = os.path.join(self.folder.get(), "fpm_reconstruction.png")
            cv2.imwrite(out, to_u8(self.recon01))
            self._log(f"💾 Guardado: {out}")
            self.status.configure(text="Listo. (ajusta parámetros y reintenta si deseas)")
        except Exception as e:
            tb = traceback.format_exc()
            self._log(f"❌ Error: {e}")
            self._log(tb)
            self.status.configure(text="Error en reconstrucción.")
            messagebox.showerror("Error", f"{e}\n\n{tb}")

def main():
    root = tk.Tk()
    app = FPMGuiV2(root)
    root.geometry("1280x820")
    root.mainloop()

if __name__ == "__main__":
    main()
