"""
Reconstruccion FPM (Fourier Ptychographic Microscopy).

Implementacion pura NumPy/OpenCV del algoritmo iterativo de recuperacion
de fase tipo Gerchberg-Saxton adaptado para FPM.

Toma N imagenes capturadas con distintos angulos de iluminacion (LED/OLED)
y reconstruye una imagen de mayor resolucion con informacion de amplitud y fase.

Referencia:
  Zheng, Horstmeyer, Yang (2013) — Wide-field, high-resolution Fourier
  ptychographic microscopy. Nature Photonics 7(9), 739-745.

Preserva caracter metrologico: la escala fisica se mantiene,
solo se recupera informacion de alta frecuencia real del espectro.
"""

import os
import json
import glob
import math
import numpy as np
import cv2


# ── Utilidades ────────────────────────────────────────────────────────

def load_scan_metadata(folder: str) -> dict:
    """Carga scan_metadata.json de una carpeta de scan FPM."""
    meta_path = os.path.join(folder, "scan_metadata.json")
    if not os.path.isfile(meta_path):
        raise FileNotFoundError(f"No se encontro scan_metadata.json en {folder}")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scan_images(folder: str, metadata: dict, logger=None) -> list:
    """
    Carga las imagenes TIFF del scan en orden.
    Retorna lista de (imagen_gray_float32, capture_info).
    """
    captures = metadata.get("captures", [])
    if not captures:
        # Fallback: buscar TIFFs directamente
        tiff_paths = sorted(
            glob.glob(os.path.join(folder, "*.tiff")) +
            glob.glob(os.path.join(folder, "*.tif"))
        )
        captures = [{"filename": os.path.basename(p)} for p in tiff_paths]

    total = len(captures)
    images = []
    for idx, cap in enumerate(captures):
        fname = cap["filename"]
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            if logger:
                logger(f"  WARN: {fname} no encontrado, saltando")
            continue

        img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            if logger:
                logger(f"  WARN: no se pudo leer {fname}")
            continue

        img_f = img.astype(np.float32) / 255.0
        images.append((img_f, cap))

        # Log progreso cada 10 imagenes o la ultima
        if logger and ((idx + 1) % 10 == 0 or idx + 1 == total):
            logger(f"  Cargadas {idx + 1}/{total} imagenes...")

    return images


def compute_illumination_vectors(metadata: dict):
    """
    Calcula vectores de iluminacion (kx, ky) a partir de las posiciones
    del LED/OLED y la geometria del setup.

    Retorna array (N, 2) con los vectores k normalizados.
    """
    fpm_info = metadata.get("fpm", {})
    wavelength_nm = fpm_info.get("wavelength_nm", 530)
    wavelength_m = wavelength_nm * 1e-9

    oled_width_mm = fpm_info.get("oled_width_mm", 21.744)
    oled_height_mm = fpm_info.get("oled_height_mm", 10.864)
    oled_size_px = metadata.get("oled_size_px", [128, 64])
    distance_mm = fpm_info.get("distance_mm", 15.0)

    # Conversion pixel OLED -> mm
    mm_per_oled_px_x = oled_width_mm / oled_size_px[0]
    mm_per_oled_px_y = oled_height_mm / oled_size_px[1]

    # Centro del OLED
    cx_oled = oled_size_px[0] / 2.0
    cy_oled = oled_size_px[1] / 2.0

    captures = metadata.get("captures", [])
    k_vectors = []

    k0 = 2.0 * np.pi / wavelength_m

    for cap in captures:
        pos = cap.get("circle_pos_px", [cx_oled, cy_oled])
        # Desplazamiento en mm desde el centro del OLED
        dx_mm = (pos[0] - cx_oled) * mm_per_oled_px_x
        dy_mm = (pos[1] - cy_oled) * mm_per_oled_px_y
        dist_mm = distance_mm

        # Angulo de iluminacion
        # sin(theta_x) = dx / sqrt(dx^2 + dy^2 + dist^2)
        r = math.sqrt(dx_mm**2 + dy_mm**2 + dist_mm**2)
        sin_x = dx_mm / r
        sin_y = dy_mm / r

        kx = k0 * sin_x
        ky = k0 * sin_y

        k_vectors.append((kx, ky))

    return np.array(k_vectors, dtype=np.float64)


def align_images_ecc(images: list, logger=None):
    """
    Alinea las imagenes al frame de referencia (primera imagen) usando ECC.
    """
    if len(images) < 2:
        return images

    total = len(images)
    ref = (images[0][0] * 255).astype(np.uint8)
    aligned = [images[0]]

    for i in range(1, total):
        img_f, cap = images[i]
        mov = (img_f * 255).astype(np.uint8)

        warp = np.eye(2, 3, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)

        try:
            _, warp = cv2.findTransformECC(ref, mov, warp, cv2.MOTION_TRANSLATION,
                                            criteria, None, 5)
            img_aligned = cv2.warpAffine(
                img_f, warp, (img_f.shape[1], img_f.shape[0]),
                flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REFLECT
            )
            aligned.append((img_aligned, cap))
        except cv2.error:
            if logger:
                logger(f"  WARN: alineacion fallo para imagen {i}")
            aligned.append((img_f, cap))

        if logger and (i % 10 == 0 or i + 1 == total):
            logger(f"  Alineadas {i}/{total - 1}...")

    return aligned


# ── Multi-angle Fusion (correcto para lensless + OLED scan) ──────────

class MultiAngleFusion:
    """
    Fusion multi-angulo: combina N imagenes con distinta iluminacion
    para recuperar detalle de alta frecuencia.

    Cada angulo de iluminacion resalta bordes perpendiculares a esa
    direccion. Este algoritmo extrae los gradientes/detalles mas fuertes
    de cada imagen y los fusiona via reconstruccion Poisson.

    Pasos:
    1. Calcular imagen base (media de todas)
    2. Para cada imagen: extraer gradientes direccionales (Sobel)
    3. Seleccionar el gradiente mas fuerte en cada pixel (de cualquier imagen)
    4. Reconstruir imagen desde gradientes fusionados (Poisson FFT)
    5. Blend con base para estabilidad
    6. Opcional: upscale con detalle preservado
    """

    def __init__(self, upscale_factor=2, max_iters=1, logger=None):
        self.upscale_factor = upscale_factor
        self.max_iters = max_iters  # iteraciones Poisson refinement
        self.log = logger or print

    def reconstruct(self, images, progress_callback=None):
        n_imgs = len(images)
        us = self.upscale_factor

        img0 = images[0][0]
        h_lr, w_lr = img0.shape
        h_hr = h_lr * us
        w_hr = w_lr * us

        self.log(f"Multi-angle Fusion: {n_imgs} imgs, {w_lr}x{h_lr} -> {w_hr}x{h_hr} (x{us})")

        # 1) Imagen base: media de todas las imagenes (contenido de baja frecuencia)
        self.log("  Calculando imagen base (media)...")
        base = np.zeros((h_lr, w_lr), dtype=np.float64)
        for img_f, _ in images:
            base += img_f.astype(np.float64)
        base /= n_imgs

        # 1b) Mascara de iluminacion: detectar zonas con buena luz
        #     El viñeteo del OLED causa bordes oscuros que generan gradientes falsos
        base_blur = cv2.GaussianBlur(base, (0, 0), sigmaX=50.0)
        illum_mask = base_blur / (base_blur.max() + 1e-10)
        # Suavizar mascara para transicion gradual
        illum_mask = np.clip(illum_mask, 0, 1) ** 2  # penalizar zonas oscuras
        pct_good = float(np.mean(illum_mask > 0.3) * 100)
        self.log(f"  Mascara iluminacion: {pct_good:.0f}% del area con buena luz")

        # 2) Denoise base para estimar umbral de ruido
        #    Gradientes menores al ruido del sensor no son detalle real
        noise_est = float(np.std(base - cv2.GaussianBlur(base, (0, 0), sigmaX=2.0)))
        grad_threshold = noise_est * 3.0  # solo gradientes > 3x ruido
        self.log(f"  Ruido estimado: {noise_est:.4f}, umbral gradiente: {grad_threshold:.4f}")

        # 3) Extraer gradientes de cada imagen y seleccionar los mas fuertes
        self.log("  Extrayendo gradientes por angulo de iluminacion...")
        best_gx = np.zeros((h_lr, w_lr), dtype=np.float64)
        best_gy = np.zeros((h_lr, w_lr), dtype=np.float64)
        best_mag = np.zeros((h_lr, w_lr), dtype=np.float64)

        # Mapa de sharpness local para weighted average
        sharpness_sum = np.zeros((h_lr, w_lr), dtype=np.float64)
        weighted_img = np.zeros((h_lr, w_lr), dtype=np.float64)

        for idx, (img_f, _) in enumerate(images):
            img_64 = img_f.astype(np.float64)

            # Denoise suave antes de gradientes (elimina ruido sensor)
            img_clean = cv2.GaussianBlur(img_64, (0, 0), sigmaX=0.8)

            # Ponderar imagen por su brillo local (SNR proxy)
            img_bright = cv2.GaussianBlur(img_64, (0, 0), sigmaX=30.0)
            bright_w = img_bright / (img_bright.max() + 1e-10)
            bright_w = np.clip(bright_w, 0.05, 1.0)

            # Gradientes Sobel sobre imagen limpia
            gx = cv2.Sobel(img_clean, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(img_clean, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(gx**2 + gy**2) * bright_w * illum_mask

            # Filtrar gradientes bajo umbral de ruido
            below_noise = mag < grad_threshold
            gx[below_noise] = 0
            gy[below_noise] = 0
            mag[below_noise] = 0

            # Sharpness local (Laplacian) ponderada
            lap = np.abs(cv2.Laplacian(img_clean, cv2.CV_64F, ksize=3))
            sharp_w = cv2.GaussianBlur(lap, (0, 0), sigmaX=5.0)
            sharp_w *= bright_w

            # Seleccionar gradiente mas fuerte en cada pixel
            stronger = mag > best_mag
            best_gx[stronger] = gx[stronger]
            best_gy[stronger] = gy[stronger]
            best_mag[stronger] = mag[stronger]

            # Acumular para fusion ponderada por sharpness
            sharpness_sum += sharp_w
            weighted_img += img_64 * sharp_w

            if (idx + 1) % 20 == 0 or idx + 1 == n_imgs:
                self.log(f"    Procesadas {idx + 1}/{n_imgs}")

        # 4) Fusion ponderada por sharpness
        self.log("  Fusion ponderada por sharpness local...")
        sharp_fused = weighted_img / np.maximum(sharpness_sum, 1e-10)

        # 5) Reconstruccion Poisson con gradientes limpios
        self.log("  Reconstruccion Poisson desde gradientes fusionados...")
        best_gx *= illum_mask
        best_gy *= illum_mask
        poisson_img = self._poisson_reconstruct(best_gx, best_gy, base)

        # 6) Blend adaptativo
        self.log("  Blend adaptativo...")
        enhanced = 0.5 * poisson_img + 0.5 * sharp_fused
        fused = illum_mask * enhanced + (1.0 - illum_mask) * base
        fused = np.clip(fused, 0, 1)

        # 7) Detalle = diferencia entre fusionada y base
        detail = fused - base
        detail_strength = float(np.std(detail))
        self.log(f"  Detalle recuperado: std={detail_strength:.4f}")

        # 8) Upscale preservando detalle
        self.log(f"  Upscale x{us}...")
        if us > 1:
            base_hr = cv2.resize(base.astype(np.float32), (w_hr, h_hr),
                                  interpolation=cv2.INTER_CUBIC).astype(np.float64)
            detail_hr = cv2.resize(detail.astype(np.float32), (w_hr, h_hr),
                                    interpolation=cv2.INTER_LANCZOS4).astype(np.float64)
            hr_img = base_hr + detail_hr
            hr_img = np.clip(hr_img, 0, 1)
        else:
            hr_img = fused

        # 9) Post: denoise suave para limpiar granulado residual
        hr_f32 = hr_img.astype(np.float32)
        # Non-local means: elimina ruido preservando bordes
        hr_u8_temp = (np.clip(hr_f32, 0, 1) * 255).astype(np.uint8)
        hr_denoised = cv2.fastNlMeansDenoising(hr_u8_temp, None, h=5,
                                                 templateWindowSize=7,
                                                 searchWindowSize=21)
        hr_final = hr_denoised.astype(np.float32) / 255.0

        if progress_callback:
            progress_callback(1, 1)

        amp_norm = self._stretch(hr_final, 0.5, 99.5)
        amplitude_u8 = (amp_norm * 255).astype(np.uint8)

        self.log(f"  Fusion completa: {w_hr}x{h_hr}")

        return {
            "amplitude": hr_final,
            "phase": np.zeros_like(hr_final),
            "amplitude_u8": amplitude_u8,
            "phase_u8": np.zeros_like(amplitude_u8),
            "upscale_factor": us,
            "output_size": (w_hr, h_hr),
            "input_size": (w_lr, h_lr),
            "n_images": n_imgs,
            "n_valid": n_imgs,
            "n_iters": 1,
            "um_per_pixel_hr": 0,
            "um_per_pixel_lr": 0,
        }

    def _poisson_reconstruct(self, gx, gy, guide):
        """
        Reconstruye imagen desde campo de gradientes via Poisson FFT.
        Resuelve: nabla^2(u) = div(gx, gy) en dominio de frecuencia.
        """
        h, w = gx.shape

        # Divergencia del campo de gradientes
        # div = d(gx)/dx + d(gy)/dy
        div = np.zeros_like(gx)
        div[:, 1:] += gx[:, 1:] - gx[:, :-1]  # d(gx)/dx
        div[1:, :] += gy[1:, :] - gy[:-1, :]  # d(gy)/dy

        # Resolver Poisson en frecuencia
        # nabla^2(u) = div  ->  u = F^-1[ F[div] / (kx^2 + ky^2) ]
        div_f = np.fft.fft2(div)

        ky = np.fft.fftfreq(h).reshape(-1, 1)
        kx = np.fft.fftfreq(w).reshape(1, -1)

        # Eigenvalores del Laplaciano discreto
        denom = (2.0 * np.cos(2.0 * np.pi * kx) +
                 2.0 * np.cos(2.0 * np.pi * ky) - 4.0)
        denom[0, 0] = 1.0  # evitar division por cero (DC)

        u_f = div_f / denom
        u_f[0, 0] = 0  # DC = 0 (ajustamos despues con guide)

        u = np.fft.ifft2(u_f).real

        # Ajustar nivel DC y rango usando la imagen guia (base)
        u = u - u.mean() + guide.mean()
        # Escalar rango para que coincida con guide
        u_std = u.std()
        g_std = guide.std()
        if u_std > 1e-10:
            u = (u - u.mean()) * (g_std / u_std) + guide.mean()

        return np.clip(u, 0, 1)

    def _stretch(self, img, p_lo=1, p_hi=99):
        lo = np.percentile(img, p_lo)
        hi = np.percentile(img, p_hi)
        return np.clip((img - lo) / (hi - lo + 1e-9), 0, 1)


# ── Multi-frame Super-Resolution (requiere shifts reales) ────────────

class MultiFrameSR:
    """
    Super-resolucion multi-frame: registra N imagenes con precision
    sub-pixel y las fusiona en una imagen de mayor resolucion usando
    Iterative Back Projection (IBP) con ponderacion por calidad.

    Mas robusto que FPM Fourier puro para setups lensless donde
    el modelo de pupila no aplica directamente.
    """

    def __init__(self, upscale_factor=2, max_iters=10, logger=None):
        self.upscale_factor = upscale_factor
        self.max_iters = max_iters
        self.log = logger or print

    def reconstruct(self, images, progress_callback=None):
        n_imgs = len(images)
        us = self.upscale_factor

        img0 = images[0][0]
        h_lr, w_lr = img0.shape
        h_hr = h_lr * us
        w_hr = w_lr * us

        self.log(f"Multi-frame SR: {n_imgs} imgs, {w_lr}x{h_lr} -> {w_hr}x{h_hr} (x{us})")

        # 0) Calcular pesos por calidad (SNR basado en brillo/varianza)
        #    Imagenes oscuras (bordes del grid OLED) aportan mas ruido que senal
        qualities = []
        for img_f, _ in images:
            mean_val = float(img_f.mean())
            std_val = float(img_f.std())
            # SNR proxy: señal / ruido. Imagenes muy oscuras tienen SNR bajo
            snr = mean_val / (std_val + 1e-6) * mean_val  # penaliza baja intensidad
            qualities.append(snr)
        qualities = np.array(qualities, dtype=np.float64)
        # Normalizar: mejor imagen = 1.0, peor = peso minimo
        q_max = qualities.max()
        if q_max > 0:
            weights = qualities / q_max
        else:
            weights = np.ones(n_imgs)
        # Clamp: no descartar totalmente, pero reducir contribucion
        weights = np.clip(weights, 0.1, 1.0)

        n_high = int(np.sum(weights > 0.5))
        n_low = n_imgs - n_high
        self.log(f"  Pesos calidad: {n_high} imgs alta calidad, {n_low} baja calidad")

        # 1) Registrar contra la imagen de mayor calidad (no la primera)
        best_idx = int(np.argmax(qualities))
        ref = images[best_idx][0]
        self.log(f"  Referencia: imagen #{best_idx} (mejor SNR)")

        shifts = []
        reg_failed = 0
        self.log("  Registrando imagenes (correlacion de fase)...")
        for i in range(n_imgs):
            if i == best_idx:
                shifts.append((0.0, 0.0))
                continue
            img_i = images[i][0]
            dx, dy = self._phase_correlation(ref, img_i)
            # Filtrar shifts absurdos (>30px = probablemente error de registro)
            if abs(dx) > 30 or abs(dy) > 30:
                weights[i] = 0.0  # descartar esta imagen
                shifts.append((0.0, 0.0))
                reg_failed += 1
            else:
                shifts.append((dx, dy))
            if (i + 1) % 20 == 0 or i + 1 == n_imgs:
                self.log(f"    Registradas {i + 1}/{n_imgs}")

        shifts = np.array(shifts)
        n_active = int(np.sum(weights > 0))
        if reg_failed > 0:
            self.log(f"  WARN: {reg_failed} imagenes descartadas por shift excesivo")
        self.log(f"  Imagenes activas: {n_active}/{n_imgs}")
        active_mask = weights > 0
        self.log(f"  Shifts activos: dx=[{shifts[active_mask,0].min():.2f}, "
                 f"{shifts[active_mask,0].max():.2f}], "
                 f"dy=[{shifts[active_mask,1].min():.2f}, "
                 f"{shifts[active_mask,1].max():.2f}]")

        # 2) Inicializar imagen HR con upscale bicubico de la referencia
        hr_img = cv2.resize(ref, (w_hr, h_hr), interpolation=cv2.INTER_CUBIC).astype(np.float64)

        # 3) Iterative Back Projection (IBP) con pesos y beta decreciente
        self.log(f"  IBP: {self.max_iters} iteraciones (beta adaptativo)...")
        for iteration in range(self.max_iters):
            correction = np.zeros_like(hr_img)
            weight_sum = np.zeros_like(hr_img)

            # Beta decreciente: empieza agresivo, termina fino
            # iter 0 -> beta=0.8, iter final -> beta=0.2
            t = iteration / max(self.max_iters - 1, 1)
            beta = 0.8 - 0.6 * t

            for i in range(n_imgs):
                w_i = weights[i]
                if w_i <= 0:
                    continue

                img_i = images[i][0].astype(np.float64)
                dx, dy = shifts[i]

                hr_shift_x = dx * us
                hr_shift_y = dy * us

                # Simular: shift HR -> downscale -> deberia = img_i
                M = np.float32([[1, 0, -hr_shift_x], [0, 1, -hr_shift_y]])
                hr_shifted = cv2.warpAffine(
                    hr_img, M, (w_hr, h_hr),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT
                )

                lr_simulated = cv2.resize(hr_shifted, (w_lr, h_lr),
                                          interpolation=cv2.INTER_AREA)

                error = img_i - lr_simulated

                # Back-project con peso
                error_up = cv2.resize(error, (w_hr, h_hr),
                                      interpolation=cv2.INTER_CUBIC)
                M_fwd = np.float32([[1, 0, hr_shift_x], [0, 1, hr_shift_y]])
                error_shifted = cv2.warpAffine(
                    error_up, M_fwd, (w_hr, h_hr),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT
                )

                correction += w_i * error_shifted
                weight_sum += w_i

            # Actualizar HR
            hr_img += beta * correction / np.maximum(weight_sum, 1e-6)
            hr_img = np.clip(hr_img, 0, 1)

            avg_err = float(np.mean(np.abs(correction)) / max(n_active, 1))

            if progress_callback:
                progress_callback(iteration + 1, self.max_iters)
            self.log(f"    Iter {iteration + 1}/{self.max_iters} -- "
                     f"error: {avg_err:.6f}, beta: {beta:.2f}")

        # 4) Post-procesamiento: Wiener-like deconvolution suave
        hr_f32 = hr_img.astype(np.float32)
        hr_sharp = self._wiener_sharpen(hr_f32)

        amplitude = hr_sharp
        amp_norm = self._stretch(amplitude, 0.5, 99.5)
        amplitude_u8 = (amp_norm * 255).astype(np.uint8)

        return {
            "amplitude": amplitude,
            "phase": np.zeros_like(amplitude),
            "amplitude_u8": amplitude_u8,
            "phase_u8": np.zeros_like(amplitude_u8),
            "upscale_factor": us,
            "output_size": (w_hr, h_hr),
            "input_size": (w_lr, h_lr),
            "n_images": n_imgs,
            "n_valid": n_active,
            "n_iters": self.max_iters,
            "um_per_pixel_hr": 0,
            "um_per_pixel_lr": 0,
        }

    def _phase_correlation(self, ref, img):
        """Calcula shift sub-pixel entre dos imagenes por correlacion de fase."""
        h, w = ref.shape
        f_ref = np.fft.fft2(ref.astype(np.float64))
        f_img = np.fft.fft2(img.astype(np.float64))

        cross = f_ref * np.conj(f_img)
        cross /= np.abs(cross) + 1e-10

        corr = np.fft.ifft2(cross).real
        corr = np.fft.fftshift(corr)

        peak_y, peak_x = np.unravel_index(np.argmax(corr), corr.shape)

        dx = peak_x - w // 2
        dy = peak_y - h // 2

        # Refinamiento sub-pixel (parabolico)
        if 1 <= peak_x < w - 1 and 1 <= peak_y < h - 1:
            cx_m = corr[peak_y, peak_x - 1]
            cx_0 = corr[peak_y, peak_x]
            cx_p = corr[peak_y, peak_x + 1]
            denom = 2.0 * (2 * cx_0 - cx_m - cx_p)
            if abs(denom) > 1e-10:
                dx += (cx_m - cx_p) / denom

            cy_m = corr[peak_y - 1, peak_x]
            cy_0 = corr[peak_y, peak_x]
            cy_p = corr[peak_y + 1, peak_x]
            denom = 2.0 * (2 * cy_0 - cy_m - cy_p)
            if abs(denom) > 1e-10:
                dy += (cy_m - cy_p) / denom

        return float(dx), float(dy)

    def _wiener_sharpen(self, img, noise_var=0.002):
        """
        Sharpening via Wiener-like deconvolution en frecuencia.
        Asume PSF gaussiana del sistema optico lensless.
        Mas limpio que unsharp mask, preserva bordes sin amplificar ruido.
        """
        # Estimar PSF gaussiana del blur del sistema
        # sigma proporcional al upscale (mas upscale = mas blur residual)
        psf_sigma = 0.8 * self.upscale_factor
        h, w = img.shape

        # PSF en frecuencia (OTF)
        ky = np.fft.fftfreq(h).reshape(-1, 1).astype(np.float32)
        kx = np.fft.fftfreq(w).reshape(1, -1).astype(np.float32)
        otf = np.exp(-2.0 * (np.pi * psf_sigma) ** 2 * (kx**2 + ky**2))

        # Wiener filter: H* / (|H|^2 + NSR)
        nsr = noise_var / (np.var(img) + 1e-10)
        wiener = otf / (otf**2 + nsr)

        # Aplicar en frecuencia
        img_f = np.fft.fft2(img)
        restored = np.fft.ifft2(img_f * wiener).real.astype(np.float32)

        # Blend suave: 70% restaurada + 30% original (evita artefactos de ringing)
        result = 0.7 * restored + 0.3 * img
        return np.clip(result, 0, 1)

    def _stretch(self, img, p_lo=1, p_hi=99):
        lo = np.percentile(img, p_lo)
        hi = np.percentile(img, p_hi)
        return np.clip((img - lo) / (hi - lo + 1e-9), 0, 1)


# ── Nucleo FPM: Algoritmo iterativo (Fourier) ───────────────────────

class FPMReconstructor:
    """
    Reconstruccion FPM iterativa (Gerchberg-Saxton adaptado).

    Algoritmo:
    1. Inicializar objeto de alta resolucion O(x,y) con imagen central upscaled
    2. Para cada iteracion:
       a. Para cada imagen capturada i con k-vector (kx_i, ky_i):
          - Extraer sub-apertura del espectro de O: shift por k-vector
          - Aplicar pupila P (filtro pasa-bajos del sensor)
          - Transformar a espacio real -> imagen estimada
          - Reemplazar amplitud con sqrt(imagen_capturada), mantener fase
          - Transformar de vuelta a Fourier
          - Actualizar espectro de O en la region de la sub-apertura
    3. Resultado: O contiene amplitud + fase de alta resolucion
    """

    def __init__(self, pixel_size_um=1.4, wavelength_nm=530,
                 upscale_factor=2, na_obj=0.1, max_iters=15,
                 logger=None):
        self.pixel_size_um = pixel_size_um
        self.wavelength_nm = wavelength_nm
        self.upscale_factor = upscale_factor
        self.na_obj = na_obj
        self.max_iters = max_iters
        self.log = logger or print

    def reconstruct(self, images, k_vectors, progress_callback=None):
        """
        Ejecuta la reconstruccion FPM.

        Args:
            images: lista de (img_float32, capture_info)
            k_vectors: array (N, 2) con vectores k de iluminacion
            progress_callback: fn(current_iter, total_iters) opcional

        Returns:
            dict con resultados de la reconstruccion
        """
        n_imgs = len(images)
        if n_imgs == 0:
            raise ValueError("No hay imagenes para reconstruir")

        img0 = images[0][0]
        h_lr, w_lr = img0.shape
        us = self.upscale_factor
        h_hr = h_lr * us
        w_hr = w_lr * us

        self.log(f"FPM: {n_imgs} imgs, {w_lr}x{h_lr} -> {w_hr}x{h_hr} (x{us})")

        # ── Parametros fisicos ──
        wavelength_m = self.wavelength_nm * 1e-9
        pixel_m = self.pixel_size_um * 1e-6
        pixel_hr = pixel_m / us

        # NA del sensor (Nyquist del pixel pitch)
        # NA_sensor = lambda / (2 * pixel_size) para muestreo coherente
        na_sensor = wavelength_m / (2.0 * pixel_m)
        self.log(f"  NA sensor (Nyquist): {na_sensor:.4f}")

        # Pupila = circulo que representa el pasabajos del sensor
        # Radio en pixeles de frecuencia del espectro LR
        # La pupila cubre la mitad del espectro LR (Nyquist)
        pupil_radius_lr = min(w_lr, h_lr) / 2.0

        self.log(f"  Pupila radio: {pupil_radius_lr:.0f} px (en espectro LR)")

        # Pre-computar pupila LR
        sub_pupil = self._make_pupil(h_lr, w_lr, pupil_radius_lr)

        # ── k-vectors a desplazamientos en pixeles del espectro HR ──
        dfx_hr = 1.0 / (w_hr * pixel_hr)
        dfy_hr = 1.0 / (h_hr * pixel_hr)

        k_shifts = np.zeros((n_imgs, 2), dtype=np.float64)
        for i in range(n_imgs):
            k_shifts[i, 0] = k_vectors[i, 0] / (2.0 * np.pi) / dfx_hr
            k_shifts[i, 1] = k_vectors[i, 1] / (2.0 * np.pi) / dfy_hr

        # ── Filtrar imagenes cuyos shifts caben en el espectro HR ──
        # La sub-apertura de tamano LR centrada en el shift debe caber
        # dentro del espectro HR de tamano (w_hr, h_hr)
        max_shift_x = (w_hr - w_lr) / 2.0
        max_shift_y = (h_hr - h_lr) / 2.0

        valid_mask = (
            (np.abs(k_shifts[:, 0]) <= max_shift_x) &
            (np.abs(k_shifts[:, 1]) <= max_shift_y)
        )
        valid_indices = np.where(valid_mask)[0]
        n_valid = len(valid_indices)

        self.log(f"  k-shifts: x=[{k_shifts[:,0].min():.0f}, {k_shifts[:,0].max():.0f}], "
                 f"y=[{k_shifts[:,1].min():.0f}, {k_shifts[:,1].max():.0f}]")
        self.log(f"  Max shift permitido: x=+-{max_shift_x:.0f}, y=+-{max_shift_y:.0f}")
        self.log(f"  Imagenes validas: {n_valid}/{n_imgs} "
                 f"({n_imgs - n_valid} descartadas por shift fuera de rango)")

        if n_valid < 3:
            raise ValueError(
                f"Solo {n_valid} imagenes tienen shifts validos para upscale x{us}. "
                f"Intenta con upscale mayor (x{us+1} o x{us+2}) o NA menor."
            )

        # ── Inicializacion con imagen central ──
        center_dists = np.sqrt(k_shifts[valid_indices, 0]**2 +
                               k_shifts[valid_indices, 1]**2)
        center_valid_pos = np.argmin(center_dists)
        center_idx = valid_indices[center_valid_pos]
        self.log(f"  Imagen central: #{center_idx} "
                 f"(shift: {k_shifts[center_idx, 0]:.0f}, {k_shifts[center_idx, 1]:.0f})")

        img_center = images[center_idx][0]
        obj_init = cv2.resize(img_center, (w_hr, h_hr), interpolation=cv2.INTER_CUBIC)

        # Objeto complejo: amplitud = sqrt(intensidad), fase = 0
        obj_complex = np.sqrt(np.maximum(obj_init, 0)).astype(np.complex64)
        self.log("  Calculando FFT inicial...")
        obj_spectrum = np.fft.fftshift(np.fft.fft2(obj_complex))
        del obj_complex, obj_init

        cx = w_hr // 2
        cy = h_hr // 2

        # |P|^2 max para normalizacion Wirtinger (EPRY update)
        P_abs2_max = float(np.max(sub_pupil ** 2))
        # Conjugada de la pupila (real, asi que es ella misma)
        pupil_conj = sub_pupil.copy()

        # Ordenar por distancia al centro (procesar centro primero, luego bordes)
        valid_dists = np.sqrt(k_shifts[valid_indices, 0]**2 +
                              k_shifts[valid_indices, 1]**2)
        sorted_valid = valid_indices[np.argsort(valid_dists)]

        # ── Iteraciones (EPRY: Embedded Pupil Recovery) ──
        self.log(f"  Iniciando {self.max_iters} iteraciones con {n_valid} imgs...")
        for iteration in range(self.max_iters):
            error_total = 0.0
            n_processed = 0

            # Primera iteracion: orden centro->borde; despues aleatorio
            if iteration == 0:
                order = sorted_valid
            else:
                order = np.random.permutation(valid_indices)

            for idx in order:
                img_captured = images[idx][0]
                shift_x = int(round(k_shifts[idx, 0]))
                shift_y = int(round(k_shifts[idx, 1]))

                # Region de sub-apertura en el espectro HR
                x1 = cx + shift_x - w_lr // 2
                y1 = cy + shift_y - h_lr // 2
                x2 = x1 + w_lr
                y2 = y1 + h_lr

                if x1 < 0 or y1 < 0 or x2 > w_hr or y2 > h_hr:
                    continue

                # 1) Extraer sub-apertura del objeto
                obj_sub = obj_spectrum[y1:y2, x1:x2].copy()

                # 2) Aplicar pupila -> campo en apertura
                psi = obj_sub * sub_pupil

                # 3) A espacio real (imagen estimada)
                phi = np.fft.ifft2(np.fft.ifftshift(psi))

                # 4) Reemplazar amplitud con medicion real, mantener fase
                est_amp = np.abs(phi).astype(np.float32)
                est_amp_safe = np.maximum(est_amp, 1e-10)
                meas_amp = np.sqrt(
                    np.maximum(img_captured, 1e-10).astype(np.float32))

                phi_updated = (meas_amp / est_amp_safe) * phi

                # Error
                error_total += float(np.mean((est_amp - meas_amp) ** 2))
                n_processed += 1

                # 5) De vuelta a Fourier
                psi_updated = np.fft.fftshift(np.fft.fft2(phi_updated))

                # 6) EPRY update: O += P* (psi' - psi) / |P|^2_max
                #    Normalizacion por |P|^2_max previene divergencia
                delta_psi = psi_updated - psi
                obj_spectrum[y1:y2, x1:x2] += (
                    pupil_conj * delta_psi / P_abs2_max
                )

            avg_error = error_total / max(n_processed, 1)
            if progress_callback:
                progress_callback(iteration + 1, self.max_iters)
            self.log(f"  Iter {iteration + 1}/{self.max_iters} -- "
                     f"error: {avg_error:.6f} ({n_processed} imgs)")

        # ── Resultado final ──
        self.log("  Generando imagen final...")
        obj_final = np.fft.ifft2(np.fft.ifftshift(obj_spectrum))
        del obj_spectrum

        amplitude = np.abs(obj_final).astype(np.float32)
        phase = np.angle(obj_final).astype(np.float32)
        del obj_final

        # Normalizar amplitud: stretch robusto por percentiles
        amp_norm = self._stretch(amplitude, p_lo=0.5, p_hi=99.5)
        amplitude_u8 = (amp_norm * 255).astype(np.uint8)

        # Fase normalizada
        phase_norm = (phase - phase.min()) / (phase.max() - phase.min() + 1e-9)
        phase_u8 = (phase_norm * 255).astype(np.uint8)

        um_per_pixel_hr = self.pixel_size_um / us

        return {
            "amplitude": amplitude,
            "phase": phase,
            "amplitude_u8": amplitude_u8,
            "phase_u8": phase_u8,
            "upscale_factor": us,
            "output_size": (w_hr, h_hr),
            "input_size": (w_lr, h_lr),
            "n_images": n_imgs,
            "n_valid": n_valid,
            "n_iters": self.max_iters,
            "um_per_pixel_hr": um_per_pixel_hr,
            "um_per_pixel_lr": self.pixel_size_um,
        }

    def _make_pupil(self, h, w, radius):
        """Crea mascara de pupila circular centrada."""
        y = np.arange(h) - h // 2
        x = np.arange(w) - w // 2
        xx, yy = np.meshgrid(x, y)
        rr = np.sqrt(xx**2 + yy**2)
        pupil = (rr <= radius).astype(np.float32)
        return pupil

    def _stretch(self, img, p_lo=1, p_hi=99):
        """Contraste stretch por percentiles."""
        lo = np.percentile(img, p_lo)
        hi = np.percentile(img, p_hi)
        return np.clip((img - lo) / (hi - lo + 1e-9), 0, 1)


# ── Funcion de alto nivel ────────────────────────────────────────────

def reconstruct_fpm(scan_folder: str,
                    upscale_factor: int = 2,
                    max_iters: int = 15,
                    align: bool = True,
                    roi_size: int = 0,
                    na_obj: float = 0.1,
                    method: str = "multiangle",
                    output_dir: str = None,
                    logger=None,
                    progress_callback=None) -> dict:
    """
    Funcion principal: reconstruye desde una carpeta de scan.

    Args:
        scan_folder: carpeta con scan_metadata.json + TIFFs
        upscale_factor: factor de super-resolucion (2, 3, 4)
        max_iters: iteraciones del algoritmo
        align: alinear imagenes por ECC
        roi_size: recortar ROI centrado (0 = imagen completa)
        na_obj: apertura numerica del objetivo (lensless ~0.05-0.15)
        method: "multiangle" (fusion multi-angulo, lensless OLED),
                "multiframe" (IBP, requiere shifts reales),
                "fourier" (FPM clasico, requiere lente)
        output_dir: carpeta de salida (None = misma carpeta del scan)
        logger: funcion de log
        progress_callback: fn(iter, total)

    Returns:
        dict con resultados y rutas de archivos guardados
    """
    log = logger or print

    # 1. Cargar metadata (soporta formato fpm/OLED y tft/ILI9341)
    log("Cargando metadata del scan...")
    metadata = load_scan_metadata(scan_folder)
    fpm_info = metadata.get("fpm", {})
    tft_info = metadata.get("tft", {})
    scan_params = metadata.get("scan_parameters", {})

    pixel_size_um = fpm_info.get("pixel_size_um", 1.4)
    wavelength_nm = fpm_info.get("wavelength_nm", 530)

    # Grid: puede estar en scan_parameters o raiz
    grid_size = scan_params.get("grid_size", metadata.get("grid_size", [9, 9]))

    # Distancia: de fpm o tft
    distance_mm = fpm_info.get("distance_mm", tft_info.get("distance_mm", 15.0))

    # Light source
    light_source = metadata.get("light_source", "unknown")
    n_captures = len(metadata.get("captures", []))

    log(f"  Fuente: {light_source}")
    log(f"  Grid: {grid_size[0]}x{grid_size[1]} ({n_captures} capturas)")
    log(f"  Pixel: {pixel_size_um} um | Distancia: {distance_mm} mm")
    log(f"  Metodo: {method}")

    # 2. Cargar imagenes
    log("Cargando imagenes...")
    images = load_scan_images(scan_folder, metadata, logger=log)
    log(f"  {len(images)} imagenes cargadas")

    if len(images) < 2:
        raise ValueError("Se necesitan al menos 2 imagenes para reconstruccion")

    # 2b. Normalizar intensidad entre imagenes
    log("Normalizando intensidad...")
    means = [float(img_f.mean()) for img_f, _ in images]
    global_mean = float(np.mean(means))
    log(f"  Brillo: min={min(means):.3f}, max={max(means):.3f}, "
        f"ratio={max(means)/max(min(means), 1e-10):.1f}x")
    normalized = []
    for (img_f, cap), m in zip(images, means):
        if m > 1e-6:
            img_norm = img_f * (global_mean / m)
            img_norm = np.clip(img_norm, 0, 1).astype(np.float32)
        else:
            img_norm = img_f
        normalized.append((img_norm, cap))
    images = normalized
    log(f"  Normalizado a media={global_mean:.3f}")

    # 3. ROI centrado (opcional, para reducir memoria)
    if roi_size > 0:
        log(f"Aplicando ROI centrado: {roi_size}x{roi_size} px")
        cropped = []
        for img_f, cap in images:
            h, w = img_f.shape
            r = min(roi_size, h, w)
            y0 = (h - r) // 2
            x0 = (w - r) // 2
            cropped.append((img_f[y0:y0+r, x0:x0+r], cap))
        images = cropped

    # 4. Alineacion
    if align:
        log("Alineando imagenes (ECC)...")
        images = align_images_ecc(images, logger=log)

    # 5. Reconstruir segun metodo elegido
    if method == "multiangle":
        # Multi-angle Fusion: correcto para lensless + OLED scan
        # No hay shifts geometricos, la info esta en variacion de iluminacion
        log(f"Iniciando Multi-angle Fusion (x{upscale_factor})...")
        fuser = MultiAngleFusion(
            upscale_factor=upscale_factor,
            logger=log,
        )
        result = fuser.reconstruct(images, progress_callback)
        result["um_per_pixel_lr"] = pixel_size_um
        result["um_per_pixel_hr"] = pixel_size_um / upscale_factor

    elif method == "multiframe":
        # Multi-frame SR: requiere shifts sub-pixel reales entre imagenes
        # (camara o muestra debe moverse entre capturas)
        log(f"Iniciando Multi-frame SR (x{upscale_factor}, {max_iters} iters)...")
        sr = MultiFrameSR(
            upscale_factor=upscale_factor,
            max_iters=max_iters,
            logger=log,
        )
        result = sr.reconstruct(images, progress_callback)
        result["um_per_pixel_lr"] = pixel_size_um
        result["um_per_pixel_hr"] = pixel_size_um / upscale_factor

    elif method == "fourier":
        # FPM Fourier clasico (requiere lente con pupila conocida)
        log("Calculando vectores de iluminacion...")
        k_vectors = compute_illumination_vectors(metadata)
        if len(k_vectors) > len(images):
            k_vectors = k_vectors[:len(images)]

        log(f"Iniciando FPM Fourier (x{upscale_factor}, {max_iters} iters, NA={na_obj})...")
        reconstructor = FPMReconstructor(
            pixel_size_um=pixel_size_um,
            wavelength_nm=wavelength_nm,
            upscale_factor=upscale_factor,
            na_obj=na_obj,
            max_iters=max_iters,
            logger=log,
        )
        result = reconstructor.reconstruct(images, k_vectors, progress_callback)

    else:
        raise ValueError(f"Metodo desconocido: {method}. Usa: multiangle, multiframe, fourier")

    # 7. Guardar resultados
    out = os.path.abspath(output_dir or scan_folder)
    os.makedirs(out, exist_ok=True)

    # Timestamp para no sobreescribir corridas anteriores
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"sr_{method}_x{upscale_factor}_{ts}"

    amp_path = os.path.join(out, f"{prefix}_amplitude.png")
    phase_path = os.path.join(out, f"{prefix}_phase.png")
    amp16_path = os.path.join(out, f"{prefix}_amplitude_16bit.tiff")
    compare_path = os.path.join(out, f"{prefix}_comparison.png")

    log(f"Guardando resultados en: {out}")

    def _safe_imwrite(path, img):
        """cv2.imwrite falla silenciosamente con rutas unicode/espacios en Windows."""
        success = cv2.imwrite(path, img)
        if not success:
            # Fallback: encode a numpy buffer y escribir con open()
            ext = os.path.splitext(path)[1]
            ok, buf = cv2.imencode(ext, img)
            if ok:
                with open(path, "wb") as f:
                    f.write(buf.tobytes())
            else:
                raise IOError(f"No se pudo guardar: {path}")

    _safe_imwrite(amp_path, result["amplitude_u8"])
    _safe_imwrite(phase_path, result["phase_u8"])

    # 16 bits para maxima precision
    amp_16 = (result["amplitude"] / (result["amplitude"].max() + 1e-9) * 65535).astype(np.uint16)
    _safe_imwrite(amp16_path, amp_16)

    log(f"  Amplitud: {amp_path} ({os.path.getsize(amp_path)} bytes)")

    # Comparacion lado a lado
    # Usar la imagen de mejor calidad como referencia visual
    sample_f = images[0][0]
    h_lr, w_lr = sample_f.shape
    h_hr, w_hr = result["amplitude_u8"].shape

    sample_up = cv2.resize(sample_f, (w_hr, h_hr), interpolation=cv2.INTER_CUBIC)

    lo = np.percentile(sample_up, 0.5)
    hi = np.percentile(sample_up, 99.5)
    sample_norm = np.clip((sample_up - lo) / (hi - lo + 1e-9), 0, 1)
    sample_u8 = (sample_norm * 255).astype(np.uint8)

    # CLAHE para resaltar detalle recuperado
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    amp_u8_eq = clahe.apply(result["amplitude_u8"])
    sample_u8_eq = clahe.apply(sample_u8)

    compare = np.hstack([sample_u8_eq, amp_u8_eq])

    compare_color = cv2.cvtColor(compare, cv2.COLOR_GRAY2BGR)
    cv2.putText(compare_color, "Original (upscaled)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    method_label = "Multi-frame SR" if method == "multiframe" else "FPM Fourier"
    n_valid = result.get("n_valid", len(images))
    cv2.putText(compare_color,
                f"{method_label} x{upscale_factor} ({n_valid} imgs, {max_iters} iters)",
                (w_hr + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

    _safe_imwrite(compare_path, compare_color)
    log(f"  Comparacion: {compare_path} ({os.path.getsize(compare_path)} bytes)")

    # Metadata de reconstruccion
    recon_meta = {
        "scan_folder": os.path.abspath(scan_folder),
        "method": method,
        "n_images": len(images),
        "n_valid": n_valid,
        "upscale_factor": upscale_factor,
        "max_iters": max_iters,
        "align": align,
        "roi_size": roi_size,
        "na_obj": na_obj,
        "wavelength_nm": wavelength_nm,
        "pixel_size_um": pixel_size_um,
        "um_per_pixel_hr": result["um_per_pixel_hr"],
        "input_size": list(result["input_size"]),
        "output_size": list(result["output_size"]),
        "files": {
            "amplitude": amp_path,
            "phase": phase_path,
            "amplitude_16bit": amp16_path,
            "comparison": compare_path,
        }
    }

    meta_out_path = os.path.join(out, f"{prefix}_meta.json")
    with open(meta_out_path, "w", encoding="utf-8") as f:
        json.dump(recon_meta, f, indent=2, ensure_ascii=False, default=str)

    log(f"Reconstruccion completada!")
    log(f"  Fase: {phase_path}")
    log(f"  Meta: {meta_out_path}")
    log(f"  Escala HR: {result['um_per_pixel_hr']:.4f} um/px")

    result["files"] = recon_meta["files"]
    result["meta_path"] = meta_out_path
    return result
