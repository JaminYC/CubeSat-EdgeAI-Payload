import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
from skimage import measure, color
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def remove_vignette(img):
    _, mask = cv2.threshold(img, 10, 255, cv2.THRESH_BINARY)
    median_val = int(np.median(img[mask > 0])) if mask.any() else 128
    img_out = img.copy()
    img_out[mask == 0] = median_val
    return img_out, mask

def run_pipeline(img_gray, params, roi=None):
    um_per_pixel = params["um_per_pixel"] * (2 if params["resize_half"] else 1)
    img = img_gray.copy()

    if params["resize_half"]:
        img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

    # Aplicar ROI si existe (en coordenadas de la imagen posiblemente reducida)
    roi_mask_global = None
    if roi is not None:
        x1, y1, x2, y2 = roi
        h, w = img.shape
        x1c, y1c = max(0, x1), max(0, y1)
        x2c, y2c = min(w, x2), min(h, y2)
        if x2c > x1c and y2c > y1c:
            img = img[y1c:y2c, x1c:x2c]
            um_per_pixel = um_per_pixel  # calibración igual (solo recortamos)

    img_clean, mask_valid = remove_vignette(img)

    clahe = cv2.createCLAHE(
        clipLimit=params["clahe_clip"],
        tileGridSize=(max(2, params["clahe_tile"]), max(2, params["clahe_tile"]))
    )
    enhanced = clahe.apply(img_clean)

    d = params["bilateral_d"]
    if d % 2 == 0: d += 1
    blurred = cv2.bilateralFilter(enhanced, d=d,
                                   sigmaColor=params["bilateral_sc"],
                                   sigmaSpace=params["bilateral_ss"])

    v = np.median(blurred)
    sigma = params["canny_sigma"]
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edges = cv2.Canny(blurred, lower, upper)

    k = params["morph_close_k"]
    if k % 2 == 0: k += 1
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_close,
                               iterations=params["morph_close_iter"])

    foreground = cv2.bitwise_not(closed)
    kernel_open = np.ones((3, 3), np.uint8)
    opening = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel_open, iterations=2)

    dist = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
    thr = params["dist_thresh"] * dist.max() if dist.max() > 0 else 1
    _, sure_fg = cv2.threshold(dist, thr, 255, 0)
    sure_fg = np.uint8(sure_fg)
    sure_bg = cv2.dilate(opening, kernel_open, iterations=3)
    unknown = cv2.subtract(sure_bg, sure_fg)

    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0
    markers[mask_valid == 0] = 1

    img_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    markers_ws = cv2.watershed(img_bgr, markers.copy())
    labeled = np.where(markers_ws > 1, markers_ws, 0).astype(np.int32)
    labeled[mask_valid == 0] = 0

    overlay = color.label2rgb(labeled, image=enhanced, bg_label=0, alpha=0.45)

    props = measure.regionprops(labeled)
    resultados = []
    for p in props:
        if p.area < params["min_area_px"]:
            continue
        resultados.append({
            "ID":           p.label,
            "Area_um2":     round(p.area * (um_per_pixel ** 2), 1),
            "Largo_um":     round(p.axis_major_length * um_per_pixel, 1),
            "Ancho_um":     round(p.axis_minor_length * um_per_pixel, 1),
            "Redondez":     round((4 * np.pi * p.area / p.perimeter**2) if p.perimeter > 0 else 0, 3),
        })
    return enhanced, edges, opening, overlay, labeled.max(), pd.DataFrame(resultados)


# ─────────────────────────────────────────────────────────────────────────────
class CellAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔬 Cell Metrology Analyzer — OV5647")
        self.root.configure(bg="#1e1e2e")
        self.root.state("zoomed")

        self.img_gray   = None
        self.img_path   = tk.StringVar(value="")
        self._after_id  = None
        self.df_result  = None
        self.current_path = ""

        # ROI state
        self._roi_mode  = False
        self._roi       = None   # (x1,y1,x2,y2) en coord de imagen (post-resize si aplica)
        self._roi_rect  = None   # Rectangle patch en ax[0,0]
        self._press     = None

        self._build_ui()

    # ── Helpers UI ─────────────────────────────────────────────────────────
    def _lbl(self, parent, text, **kw):
        return tk.Label(parent, text=text, bg="#1e1e2e", fg="#cdd6f4",
                        font=("Consolas", 9), **kw)

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg="#313244", pady=6)
        top.pack(fill="x", side="top")

        def btn(parent, txt, cmd, bg="#89b4fa"):
            return tk.Button(parent, text=txt, command=cmd,
                             bg=bg, fg="#1e1e2e", font=("Consolas", 10, "bold"),
                             relief="flat", padx=12, pady=4)

        btn(top, "📂 Abrir Imagen", self._open_image).pack(side="left", padx=8)
        tk.Label(top, textvariable=self.img_path,
                 bg="#313244", fg="#a6e3a1", font=("Consolas", 9)).pack(side="left", padx=6)

        btn(top, "💾 Guardar CSV", self._save_csv, "#a6e3a1").pack(side="right", padx=8)
        btn(top, "🔄 Recalcular",  self._recalculate, "#fab387").pack(side="right", padx=4)
        self.roi_btn = btn(top, "📐 Seleccionar ROI", self._toggle_roi_mode, "#cba6f7")
        self.roi_btn.pack(side="right", padx=4)
        btn(top, "✖ Limpiar ROI", self._clear_roi, "#f38ba8").pack(side="right", padx=2)

        # ── Layout ───────────────────────────────────────────────────────
        main = tk.Frame(self.root, bg="#1e1e2e")
        main.pack(fill="both", expand=True)

        # Sliders (izquierda)
        left = tk.Frame(main, bg="#181825", width=270)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Plots (derecha)
        right = tk.Frame(main, bg="#1e1e2e")
        right.pack(side="left", fill="both", expand=True)

        # ── Matplotlib ───────────────────────────────────────────────────
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 7))
        self.fig.patch.set_facecolor("#1e1e2e")
        plt.tight_layout(pad=2)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Conectar eventos de mouse para ROI
        self.canvas.mpl_connect("button_press_event",   self._on_press)
        self.canvas.mpl_connect("motion_notify_event",  self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_release)

        # ── Status bar ───────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Carga una imagen para comenzar...")
        self.count_var  = tk.StringVar(value="Células: —")
        sb = tk.Frame(right, bg="#313244")
        sb.pack(fill="x")
        tk.Label(sb, textvariable=self.status_var, bg="#313244", fg="#cdd6f4",
                 font=("Consolas", 9), anchor="w").pack(side="left", padx=8)
        tk.Label(sb, textvariable=self.count_var, bg="#313244", fg="#a6e3a1",
                 font=("Consolas", 10, "bold"), anchor="e").pack(side="right", padx=8)

        # ── ROI info label ───────────────────────────────────────────────
        self.roi_info_var = tk.StringVar(value="ROI: completa imagen")
        tk.Label(sb, textvariable=self.roi_info_var, bg="#313244", fg="#cba6f7",
                 font=("Consolas", 9)).pack(side="right", padx=12)

        # ── Sliders panel ────────────────────────────────────────────────
        outer = tk.Canvas(left, bg="#181825", highlightthickness=0)
        vsb   = ttk.Scrollbar(left, orient="vertical", command=outer.yview)
        sf    = tk.Frame(outer, bg="#181825")
        sf.bind("<Configure>", lambda e: outer.configure(scrollregion=outer.bbox("all")))
        outer.create_window((0, 0), window=sf, anchor="nw")
        outer.configure(yscrollcommand=vsb.set)
        outer.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        # scroll con rueda
        outer.bind_all("<MouseWheel>", lambda e: outer.yview_scroll(-1*(e.delta//120), "units"))

        self.sliders = {}
        S = self._slider  # shorthand

        self._section(sf, "⚙  IMAGEN")
        self._check(sf, "resize_half", "Reducir 50% (más rápido)", True)
        S(sf, "um_per_pixel", "µm / pixel", 0.01, 10.0, 1.4, 0.01)

        self._section(sf, "🎨  CLAHE")
        S(sf, "clahe_clip", "Clip Limit",   0.10, 10.0, 3.0, 0.01)
        S(sf, "clahe_tile", "Tile Size",    2,    32,   8,   1,  integer=True)

        self._section(sf, "〰  FILTRO BILATERAL")
        S(sf, "bilateral_d",  "Diámetro d",    3, 21,  9,  2, integer=True)
        S(sf, "bilateral_sc", "Sigma Color",   1, 200, 75,  1)
        S(sf, "bilateral_ss", "Sigma Space",   1, 200, 75,  1)

        self._section(sf, "🔲  CANNY (Bordes)")
        S(sf, "canny_sigma", "Sigma (sensibilidad)", 0.01, 1.5, 0.33, 0.01)

        self._section(sf, "🔷  MORFOLOGÍA (Cierre)")
        S(sf, "morph_close_k",    "Kernel Size",  3, 25, 7, 2, integer=True)
        S(sf, "morph_close_iter", "Iteraciones",  1, 10, 2, 1, integer=True)

        self._section(sf, "💧  WATERSHED")
        S(sf, "dist_thresh", "Dist. Threshold",  0.01, 0.99, 0.30, 0.01)
        S(sf, "min_area_px", "Área mín. (px)",    5,  1000,  50,   5, integer=True)

        self._draw_placeholder()

    # ── Slider helpers ─────────────────────────────────────────────────────
    def _section(self, parent, title):
        f = tk.Frame(parent, bg="#313244")
        f.pack(fill="x", pady=(8, 1), padx=4)
        tk.Label(f, text=title, bg="#313244", fg="#89b4fa",
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=6, pady=2)

    def _check(self, parent, key, label, default):
        var = tk.BooleanVar(value=default)
        self.sliders[key] = var
        f = tk.Frame(parent, bg="#181825")
        f.pack(fill="x", padx=10, pady=2)
        tk.Checkbutton(f, text=label, variable=var, bg="#181825", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#181825",
                       font=("Consolas", 9), command=self._on_change).pack(anchor="w")

    def _slider(self, parent, key, label, from_, to, init, res, integer=False):
        f = tk.Frame(parent, bg="#181825")
        f.pack(fill="x", padx=10, pady=2)
        hdr = tk.Frame(f, bg="#181825")
        hdr.pack(fill="x")
        self._lbl(hdr, label).pack(side="left")
        val_lbl = self._lbl(hdr, f"{init}")
        val_lbl.pack(side="right")

        var = tk.DoubleVar(value=init)
        self.sliders[key] = var

        def on_slide(v, vl=val_lbl, vr=var, intg=integer):
            val = int(float(v)) if intg else round(float(v), 3)
            vr.set(val)
            vl.config(text=str(val))
            self._schedule()

        tk.Scale(f, from_=from_, to=to, resolution=res, orient="horizontal",
                 variable=var, bg="#181825", fg="#cdd6f4", troughcolor="#313244",
                 activebackground="#89b4fa", highlightthickness=0,
                 showvalue=False, command=on_slide).pack(fill="x")

    def _schedule(self):
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(350, self._recalculate)

    def _on_change(self):
        self._schedule()

    # ── ROI selection ──────────────────────────────────────────────────────
    def _toggle_roi_mode(self):
        self._roi_mode = not self._roi_mode
        if self._roi_mode:
            self.roi_btn.config(bg="#f38ba8", text="📐 Modo ROI ACTIVO")
            self.status_var.set("🖱  Haz clic y arrastra sobre el PANEL 1 (CLAHE) para definir la región")
        else:
            self.roi_btn.config(bg="#cba6f7", text="📐 Seleccionar ROI")
            self.status_var.set("Modo ROI desactivado")

    def _clear_roi(self):
        self._roi = None
        if self._roi_rect is not None:
            try:
                self._roi_rect.remove()
            except Exception:
                pass
            self._roi_rect = None
            self.canvas.draw_idle()
        self.roi_info_var.set("ROI: completa imagen")
        self._roi_mode = False
        self.roi_btn.config(bg="#cba6f7", text="📐 Seleccionar ROI")
        self._recalculate()

    def _ax_to_img_coords(self, event):
        """Transforma coordenadas del evento a píxeles de imagen en ax[0,0]."""
        ax = self.axes[0, 0]
        if event.inaxes != ax:
            return None
        # event.xdata / ydata están en coordenadas de imagen (matplotlib las mapea directo)
        return int(event.xdata), int(event.ydata)

    def _on_press(self, event):
        if not self._roi_mode or self.img_gray is None:
            return
        coords = self._ax_to_img_coords(event)
        if coords is None:
            return
        self._press = coords
        # Borrar rect anterior
        if self._roi_rect is not None:
            try:
                self._roi_rect.remove()
            except Exception:
                pass
            self._roi_rect = None

    def _on_motion(self, event):
        if not self._roi_mode or self._press is None:
            return
        coords = self._ax_to_img_coords(event)
        if coords is None:
            return
        x1, y1 = self._press
        x2, y2 = coords
        ax = self.axes[0, 0]
        if self._roi_rect is not None:
            try:
                self._roi_rect.remove()
            except Exception:
                pass
        self._roi_rect = ax.add_patch(
            Rectangle((min(x1, x2), min(y1, y2)),
                       abs(x2 - x1), abs(y2 - y1),
                       linewidth=2, edgecolor="#f38ba8",
                       facecolor="#f38ba8", alpha=0.15)
        )
        self.canvas.draw_idle()

    def _on_release(self, event):
        if not self._roi_mode or self._press is None:
            return
        coords = self._ax_to_img_coords(event)
        if coords is None:
            self._press = None
            return
        x1, y1 = self._press
        x2, y2 = coords
        self._press = None

        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.status_var.set("⚠  ROI muy pequeña, inténtalo de nuevo")
            return

        # Las coords vienen en espacio de la imagen mostrada (ya reducida si resize_half=True)
        self._roi = (min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2))
        w_roi = abs(x2 - x1)
        h_roi = abs(y2 - y1)

        um = self.sliders["um_per_pixel"].get() * (2 if self.sliders["resize_half"].get() else 1)
        self.roi_info_var.set(
            f"ROI: {int(w_roi)}×{int(h_roi)} px  →  {w_roi*um:.0f}×{h_roi*um:.0f} µm"
        )
        self._roi_mode = False
        self.roi_btn.config(bg="#cba6f7", text="📐 Seleccionar ROI")
        self.status_var.set(f"✅ ROI fijada: {int(w_roi)}×{int(h_roi)} px")
        self._recalculate()

    # ── Get params ─────────────────────────────────────────────────────────
    def _get_params(self):
        p = {}
        for k, v in self.sliders.items():
            p[k] = v.get()
        for ki in ["clahe_tile", "bilateral_d", "morph_close_k", "morph_close_iter", "min_area_px"]:
            p[ki] = int(p[ki])
        return p

    # ── Open / Recalculate ─────────────────────────────────────────────────
    def _open_image(self):
        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp"), ("Todos", "*.*")]
        )
        if not path:
            return
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            messagebox.showerror("Error", f"No se pudo abrir: {path}")
            return
        self.img_gray     = img
        self.current_path = path
        self._roi         = None
        self._roi_rect    = None
        self.img_path.set(os.path.basename(path))
        self.roi_info_var.set("ROI: completa imagen")
        self.status_var.set(f"Imagen: {img.shape[1]}×{img.shape[0]} px")
        self._recalculate()

    def _recalculate(self):
        if self.img_gray is None:
            return
        self.status_var.set("⏳ Procesando...")
        self.root.update_idletasks()
        try:
            params = self._get_params()
            enhanced, edges, opening, overlay, n, df = run_pipeline(
                self.img_gray, params, roi=self._roi
            )
            self.df_result = df
            self._update_plots(enhanced, edges, opening, overlay, n, df)
            self.count_var.set(f"🔬 Células válidas: {len(df)}")
            if len(df) > 0:
                self.status_var.set(
                    f"✅ {n} regiones | {len(df)} válidas | "
                    f"Área media: {df['Area_um2'].mean():.0f} µm²  | "
                    f"Largo medio: {df['Largo_um'].mean():.1f} µm"
                )
            else:
                self.status_var.set(f"✅ {n} regiones detectadas | 0 válidas con los filtros actuales")
        except Exception as e:
            self.status_var.set(f"❌ Error: {e}")

    def _update_plots(self, enhanced, edges, opening, overlay, n, df):
        for ax in self.axes.flat:
            ax.clear()
            ax.set_facecolor("#1e1e2e")

        self.axes[0, 0].imshow(enhanced, cmap="gray")
        self.axes[0, 0].set_title("1. CLAHE  ← Arrastra aquí para ROI", color="#cba6f7", fontsize=9)
        self.axes[0, 0].axis("off")

        # Redibujar el rect de ROI si existe
        if self._roi is not None:
            x1, y1, x2, y2 = self._roi
            self._roi_rect = self.axes[0, 0].add_patch(
                Rectangle((x1, y1), x2-x1, y2-y1,
                           linewidth=2, edgecolor="#f38ba8",
                           facecolor="#f38ba8", alpha=0.15)
            )

        self.axes[0, 1].imshow(edges, cmap="gray")
        self.axes[0, 1].set_title("2. Bordes Canny", color="#cdd6f4", fontsize=9)
        self.axes[0, 1].axis("off")

        self.axes[1, 0].imshow(opening, cmap="gray")
        self.axes[1, 0].set_title("3. Foreground (Cierre Morf.)", color="#cdd6f4", fontsize=9)
        self.axes[1, 0].axis("off")

        self.axes[1, 1].imshow(overlay)
        self.axes[1, 1].set_title(
            f"4. Watershed — {n} regiones | {len(df)} válidas",
            color="#a6e3a1", fontsize=9
        )
        self.axes[1, 1].axis("off")

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    def _draw_placeholder(self):
        for ax in self.axes.flat:
            ax.set_facecolor("#313244")
            ax.text(0.5, 0.5, "Carga una imagen\npara comenzar",
                    ha="center", va="center", color="#585b70",
                    fontsize=13, transform=ax.transAxes)
            ax.axis("off")
        self.canvas.draw()

    def _save_csv(self):
        if self.df_result is None or len(self.df_result) == 0:
            messagebox.showwarning("Sin datos", "Procesa una imagen primero.")
            return
        base = os.path.splitext(os.path.basename(self.current_path))[0] if self.current_path else "resultado"
        roi_suffix = "_ROI" if self._roi else ""
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"metrologia_{base}{roi_suffix}.csv"
        )
        if path:
            self.df_result.to_csv(path, index=False)
            messagebox.showinfo("✅ Guardado", f"CSV guardado en:\n{path}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    CellAnalyzerApp(root)
    root.mainloop()
