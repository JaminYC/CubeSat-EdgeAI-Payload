"""
AI Enhancement module for CubeSat EdgeAI pipeline.

Wraps multiple pre-trained microscopy AI models:
  - Cellpose: cell segmentation (cyto3, nuclei)
  - CARE (CSBDeep): denoising / restoration
  - Noise2Void (N2V): self-supervised denoising (no clean targets needed)
  - StarDist: star-convex polygon cell detection

All models use pre-trained weights. Designed for graceful degradation:
if a package is not installed, that model is simply unavailable.

RPi 5 target: models can be exported to ONNX for ARM64 inference.
"""

import os
import time
import numpy as np
import cv2
from datetime import datetime

# Suppress TF/oneDNN warnings
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


# ── Availability flags ──────────────────────────────────────────────

_HAS_CELLPOSE = False
_HAS_CARE = False
_HAS_N2V = False
_HAS_STARDIST = False

try:
    from cellpose import models as cp_models
    _HAS_CELLPOSE = True
except (ImportError, RuntimeError):
    pass

try:
    import tensorflow as _tf
    _HAS_CARE = True   # CARE implemented with raw TF/Keras
    _HAS_N2V = True    # N2V implemented with raw TF/Keras
except (ImportError, RuntimeError):
    pass

try:
    from stardist.models import StarDist2D
    _HAS_STARDIST = True
except (ImportError, RuntimeError):
    pass


def get_available_models():
    """Return dict of model_name -> bool (available)."""
    return {
        "cellpose": _HAS_CELLPOSE,
        "care": _HAS_CARE,
        "n2v": _HAS_N2V,
        "stardist": _HAS_STARDIST,
    }


def _safe_imwrite(path, img):
    """Write image handling Windows paths with spaces/unicode."""
    success = cv2.imwrite(path, img)
    if not success:
        ext = os.path.splitext(path)[1]
        ok, buf = cv2.imencode(ext, img)
        if ok:
            with open(path, "wb") as f:
                f.write(buf.tobytes())


# ── Cellpose ────────────────────────────────────────────────────────

def run_cellpose(image, model_type="cyto3", diameter=None,
                 flow_threshold=0.4, cellprob_threshold=0.0, logger=None):
    """
    Run Cellpose segmentation on a single image.

    Args:
        image: numpy array (grayscale or RGB)
        model_type: "cyto3", "cyto2", "nuclei", etc.
        diameter: cell diameter in pixels (None = auto-detect)
        channels: [cytoplasm_channel, nucleus_channel] e.g. [0,0] for grayscale
        flow_threshold: flow error threshold
        cellprob_threshold: cell probability threshold
        logger: logging function

    Returns:
        dict with masks, flows, overlay, n_cells, diameters
    """
    log = logger or print

    if not _HAS_CELLPOSE:
        raise RuntimeError("Cellpose no instalado. pip install cellpose")

    log(f"[Cellpose] Modelo: {model_type}, diameter: {diameter or 'auto'}")

    # cellpose 4.x: model_type is ignored, use CellposeModel directly
    model = cp_models.Cellpose(model_type=model_type, gpu=False)

    if image.ndim == 2:
        channels = [0, 0]
    else:
        channels = [0, 0]

    t0 = time.time()
    masks, flows, styles, diams = model.eval(
        image,
        diameter=diameter,
        channels=channels,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
    )
    elapsed = time.time() - t0

    n_cells = masks.max()
    log(f"[Cellpose] {n_cells} celulas detectadas en {elapsed:.1f}s")
    log(f"[Cellpose] Diametro: {diams:.1f} px")

    # Create colored overlay
    overlay = _masks_to_overlay(image, masks)

    return {
        "masks": masks,
        "flows": flows,
        "overlay": overlay,
        "n_cells": int(n_cells),
        "diameter": float(diams),
        "elapsed": elapsed,
        "model": model_type,
    }


# ── CARE (CSBDeep) ──────────────────────────────────────────────────

def run_care(image, n_epochs=15, logger=None, **kwargs):
    """
    CARE-style denoising: trains a small U-Net to map noisy->clean
    using synthetic noise augmentation on the input image itself.

    Unlike N2V (blind-spot), CARE uses paired training with synthetic noise,
    which typically produces sharper results.

    Args:
        image: numpy array (grayscale or color)
        n_epochs: training epochs
        logger: logging function

    Returns:
        dict with restored image, elapsed time
    """
    log = logger or print

    log(f"[CARE] Denoising supervisado (noise2clean, {n_epochs} epochs)...")

    if image.ndim == 3:
        if image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    img_float = gray.astype(np.float32) / 255.0 if gray.max() > 1.0 else gray.astype(np.float32)

    t0 = time.time()

    # Crop if too large
    h, w = img_float.shape
    max_dim = 1024
    if h > max_dim or w > max_dim:
        cy, cx = h // 2, w // 2
        hh, ww = min(h, max_dim) // 2, min(w, max_dim) // 2
        img_crop = img_float[cy - hh:cy + hh, cx - ww:cx + ww]
        log(f"[CARE] Recortado para training: {img_float.shape} -> {img_crop.shape}")
    else:
        img_crop = img_float

    import tensorflow as tf

    # Generate paired training data: add synthetic noise -> original as target
    patch_size = 64
    n_patches = 400

    ph, pw = img_crop.shape
    X_noisy = []
    Y_clean = []

    noise_level = np.std(img_crop) * 0.3  # 30% of image std as noise

    for _ in range(n_patches):
        y = np.random.randint(0, ph - patch_size)
        x = np.random.randint(0, pw - patch_size)
        clean = img_crop[y:y + patch_size, x:x + patch_size].copy()
        noisy = clean + np.random.normal(0, noise_level, clean.shape).astype(np.float32)
        noisy = np.clip(noisy, 0, 1)
        X_noisy.append(noisy)
        Y_clean.append(clean)

    X_noisy = np.array(X_noisy)[..., np.newaxis]
    Y_clean = np.array(Y_clean)[..., np.newaxis]

    # Same U-Net architecture as N2V
    inp = tf.keras.Input(shape=(None, None, 1))
    c1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(inp)
    c1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(c1)
    p1 = tf.keras.layers.MaxPooling2D(2)(c1)
    c2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(p1)
    c2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(c2)
    p2 = tf.keras.layers.MaxPooling2D(2)(c2)
    b = tf.keras.layers.Conv2D(128, 3, padding='same', activation='relu')(p2)
    b = tf.keras.layers.Conv2D(128, 3, padding='same', activation='relu')(b)
    u2 = tf.keras.layers.UpSampling2D(2)(b)
    u2 = tf.keras.layers.Concatenate()([u2, c2])
    d2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(u2)
    d2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(d2)
    u1 = tf.keras.layers.UpSampling2D(2)(d2)
    u1 = tf.keras.layers.Concatenate()([u1, c1])
    d1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(u1)
    d1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(d1)
    out = tf.keras.layers.Conv2D(1, 1, padding='same', activation='sigmoid')(d1)

    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss='mse')

    log(f"[CARE] Red: {model.count_params()} parametros")
    log(f"[CARE] Entrenando noisy->clean con {len(X_noisy)} patches...")

    model.fit(X_noisy, Y_clean, epochs=n_epochs, batch_size=16,
              validation_split=0.1, verbose=0)

    log(f"[CARE] Entrenamiento completado")

    # Predict on full image
    pad_h = (32 - h % 32) % 32
    pad_w = (32 - w % 32) % 32
    padded = np.pad(img_float, ((0, pad_h), (0, pad_w)), mode='reflect')
    inp_arr = padded[np.newaxis, ..., np.newaxis]

    restored_pad = model.predict(inp_arr, verbose=0)[0, :h, :w, 0]
    restored_u8 = np.clip(restored_pad * 255, 0, 255).astype(np.uint8)

    elapsed = time.time() - t0
    log(f"[CARE] Restauracion completada en {elapsed:.1f}s")

    return {
        "restored": restored_u8,
        "elapsed": elapsed,
        "model": "care_noise2clean",
    }


# ── Noise2Void ──────────────────────────────────────────────────────

def run_n2v(image, n_epochs=20, train_on_image=True, logger=None, **kwargs):
    """
    Noise2Void-style self-supervised denoising.

    Uses a lightweight blind-spot CNN approach compatible with current
    TF/Keras versions. Trains on the noisy image itself — no clean
    reference needed.

    Args:
        image: numpy array (grayscale or color)
        n_epochs: training epochs
        train_on_image: always True for N2V (trains on input image)
        logger: logging function

    Returns:
        dict with denoised image, elapsed time
    """
    log = logger or print

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    img_float = gray.astype(np.float32) / 255.0 if gray.max() > 1.0 else gray.astype(np.float32)

    log(f"[N2V] Denoising self-supervised ({n_epochs} epochs)...")
    log(f"[N2V] (No requiere imagenes limpias de referencia)")

    t0 = time.time()

    # Crop if too large for training
    h, w = img_float.shape
    max_dim = 1024
    if h > max_dim or w > max_dim:
        cy, cx = h // 2, w // 2
        hh, ww = min(h, max_dim) // 2, min(w, max_dim) // 2
        img_crop = img_float[cy - hh:cy + hh, cx - ww:cx + ww]
        log(f"[N2V] Recortado para training: {img_float.shape} -> {img_crop.shape}")
    else:
        img_crop = img_float

    # Build lightweight blind-spot denoising network with raw Keras
    import tensorflow as tf

    # Generate training patches with blind-spot masking
    patch_size = 64
    n_patches = 400
    perc_pix = 0.02  # % of pixels to mask per patch

    ph, pw = img_crop.shape
    X_train = []
    Y_train = []

    for _ in range(n_patches):
        y = np.random.randint(0, ph - patch_size)
        x = np.random.randint(0, pw - patch_size)
        patch = img_crop[y:y + patch_size, x:x + patch_size].copy()

        # Create blind-spot: mask random pixels and set target
        target = patch.copy()
        n_mask = max(1, int(patch_size * patch_size * perc_pix))
        mask_y = np.random.randint(0, patch_size, n_mask)
        mask_x = np.random.randint(0, patch_size, n_mask)

        # Replace masked pixels with random neighbor value
        for my, mx in zip(mask_y, mask_x):
            dy, dx = np.random.choice([-1, 0, 1], 2)
            ny, nx = np.clip(my + dy, 0, patch_size - 1), np.clip(mx + dx, 0, patch_size - 1)
            patch[my, mx] = patch[ny, nx]

        X_train.append(patch)
        Y_train.append(target)

    X_train = np.array(X_train)[..., np.newaxis]
    Y_train = np.array(Y_train)[..., np.newaxis]

    # Simple U-Net-like architecture
    inp = tf.keras.Input(shape=(None, None, 1))
    # Encoder
    c1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(inp)
    c1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(c1)
    p1 = tf.keras.layers.MaxPooling2D(2)(c1)
    c2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(p1)
    c2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(c2)
    p2 = tf.keras.layers.MaxPooling2D(2)(c2)
    # Bottleneck
    b = tf.keras.layers.Conv2D(128, 3, padding='same', activation='relu')(p2)
    b = tf.keras.layers.Conv2D(128, 3, padding='same', activation='relu')(b)
    # Decoder
    u2 = tf.keras.layers.UpSampling2D(2)(b)
    u2 = tf.keras.layers.Concatenate()([u2, c2])
    d2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(u2)
    d2 = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(d2)
    u1 = tf.keras.layers.UpSampling2D(2)(d2)
    u1 = tf.keras.layers.Concatenate()([u1, c1])
    d1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(u1)
    d1 = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(d1)
    out = tf.keras.layers.Conv2D(1, 1, padding='same', activation='sigmoid')(d1)

    model = tf.keras.Model(inp, out)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss='mse')

    log(f"[N2V] Red: {model.count_params()} parametros")
    log(f"[N2V] Entrenando con {len(X_train)} patches...")

    model.fit(X_train, Y_train, epochs=n_epochs, batch_size=16,
              validation_split=0.1, verbose=0,
              callbacks=[tf.keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5)])

    log(f"[N2V] Entrenamiento completado")

    # Predict on full image (tile if needed)
    pad_h = (32 - h % 32) % 32
    pad_w = (32 - w % 32) % 32
    padded = np.pad(img_float, ((0, pad_h), (0, pad_w)), mode='reflect')
    inp_arr = padded[np.newaxis, ..., np.newaxis]

    denoised_pad = model.predict(inp_arr, verbose=0)[0, :h, :w, 0]
    denoised_u8 = np.clip(denoised_pad * 255, 0, 255).astype(np.uint8)

    elapsed = time.time() - t0
    log(f"[N2V] Denoising completado en {elapsed:.1f}s")

    return {
        "denoised": denoised_u8,
        "elapsed": elapsed,
        "model": "n2v_blindspot",
        "trained_on_image": True,
    }


# ── StarDist ────────────────────────────────────────────────────────

def run_stardist(image, model_name="2D_versatile_fluo", logger=None):
    """
    Run StarDist star-convex polygon cell detection.

    Available pre-trained models:
        - "2D_versatile_fluo": fluorescence microscopy
        - "2D_versatile_he": H&E histology
        - "2D_paper_dsb2018": Data Science Bowl 2018

    Args:
        image: numpy array (grayscale or RGB)
        model_name: pre-trained model name
        logger: logging function

    Returns:
        dict with labels, details (coord, points, prob), overlay, n_cells
    """
    log = logger or print

    if not _HAS_STARDIST:
        raise RuntimeError("StarDist no instalado. pip install stardist")

    log(f"[StarDist] Modelo: {model_name}")

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Normalize
    img_norm = gray.astype(np.float32)
    if img_norm.max() > 1.0:
        img_norm = img_norm / 255.0

    t0 = time.time()

    # Fix Windows symlink issue: patch pathlib.symlink_to with shutil.copytree
    import pathlib
    _orig_symlink = pathlib.Path.symlink_to
    def _copy_fallback(self_path, target, target_is_directory=False):
        try:
            _orig_symlink(self_path, target, target_is_directory)
        except OSError:
            import shutil
            src = self_path.parent / target
            if src.is_dir():
                if self_path.exists():
                    shutil.rmtree(self_path)
                shutil.copytree(str(src), str(self_path))
            else:
                shutil.copy2(str(src), str(self_path))
    pathlib.Path.symlink_to = _copy_fallback

    model = StarDist2D.from_pretrained(model_name)
    pathlib.Path.symlink_to = _orig_symlink  # restore
    labels, details = model.predict_instances(img_norm)
    elapsed = time.time() - t0

    n_cells = labels.max()
    log(f"[StarDist] {n_cells} celulas detectadas en {elapsed:.1f}s")

    # Create overlay
    overlay = _masks_to_overlay(image, labels)

    return {
        "labels": labels,
        "details": details,
        "overlay": overlay,
        "n_cells": int(n_cells),
        "elapsed": elapsed,
        "model": model_name,
    }


# ── Utilities ───────────────────────────────────────────────────────

def _masks_to_overlay(image, masks, alpha=0.4):
    """Create a colored overlay from segmentation masks."""
    # Ensure 3-channel BGR
    if image.ndim == 2:
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        base = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        base = image.copy()

    if masks.max() == 0:
        return base

    overlay = base.copy()
    n = masks.max()

    # Generate distinct colors using colormap (faster than per-cell loop)
    color_lut = np.zeros((n + 1, 3), dtype=np.uint8)
    for i in range(1, n + 1):
        hue = int(i * 180 / n) % 180
        color_hsv = np.array([[[hue, 200, 230]]], dtype=np.uint8)
        color_lut[i] = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0, 0]

    # Apply colors via LUT (vectorized)
    mask_bool = masks > 0
    overlay[mask_bool] = color_lut[masks[mask_bool]]

    result = cv2.addWeighted(base, 1 - alpha, overlay, alpha, 0)

    # Draw contours
    for i in range(1, min(n + 1, 500)):
        mask_i = (masks == i).astype(np.uint8)
        contours, _ = cv2.findContours(mask_i, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(result, contours, -1, (255, 255, 255), 1)

    return result


def run_ai_model(image, model_name, output_dir=None, logger=None, **kwargs):
    """
    Unified entry point: run any available AI model on an image.

    Args:
        image: numpy array (grayscale or BGR)
        model_name: "cellpose", "care", "n2v", "stardist"
        output_dir: directory to save results (optional)
        logger: logging function
        **kwargs: model-specific parameters

    Returns:
        dict with model results and saved file paths
    """
    log = logger or print
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    log(f"\n{'='*50}")
    log(f"AI Model: {model_name.upper()}")
    log(f"{'='*50}")

    if model_name == "cellpose":
        result = run_cellpose(image, logger=log, **kwargs)
    elif model_name == "care":
        result = run_care(image, logger=log, **kwargs)
    elif model_name == "n2v":
        result = run_n2v(image, logger=log, **kwargs)
    elif model_name == "stardist":
        result = run_stardist(image, logger=log, **kwargs)
    else:
        raise ValueError(f"Modelo desconocido: {model_name}")

    # Save results if output_dir specified
    saved_files = {}
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        prefix = f"ai_{model_name}_{ts}"

        if model_name in ("cellpose", "stardist"):
            # Save overlay
            overlay_path = os.path.join(output_dir, f"{prefix}_overlay.png")
            _safe_imwrite(overlay_path, result["overlay"])
            saved_files["overlay"] = overlay_path

            # Save masks
            masks_key = "masks" if "masks" in result else "labels"
            masks = result[masks_key]
            mask_path = os.path.join(output_dir, f"{prefix}_masks.png")
            # Normalize masks for visibility
            if masks.max() > 0:
                mask_vis = (masks.astype(np.float32) / masks.max() * 255).astype(np.uint8)
                mask_colored = cv2.applyColorMap(mask_vis, cv2.COLORMAP_JET)
                mask_colored[masks == 0] = 0
                _safe_imwrite(mask_path, mask_colored)
            else:
                _safe_imwrite(mask_path, np.zeros_like(image))
            saved_files["masks"] = mask_path

        elif model_name == "care":
            restored_path = os.path.join(output_dir, f"{prefix}_restored.png")
            _safe_imwrite(restored_path, result["restored"])
            saved_files["restored"] = restored_path

        elif model_name == "n2v":
            denoised_path = os.path.join(output_dir, f"{prefix}_denoised.png")
            _safe_imwrite(denoised_path, result["denoised"])
            saved_files["denoised"] = denoised_path

        log(f"[{model_name.upper()}] Archivos guardados:")
        for k, v in saved_files.items():
            log(f"  {k}: {os.path.basename(v)}")

    result["saved_files"] = saved_files
    return result


def run_all_models(image, output_dir, logger=None, **kwargs):
    """
    Run all available AI models on an image and save results.

    Args:
        image: numpy array
        output_dir: where to save results
        logger: logging function

    Returns:
        dict of model_name -> result dict
    """
    log = logger or print
    available = get_available_models()
    results = {}

    for model_name, is_available in available.items():
        if not is_available:
            log(f"[SKIP] {model_name}: no instalado")
            continue

        try:
            model_kwargs = kwargs.get(model_name, {})
            result = run_ai_model(
                image, model_name, output_dir=output_dir,
                logger=log, **model_kwargs
            )
            results[model_name] = result
        except Exception as e:
            log(f"[ERROR] {model_name}: {e}")
            results[model_name] = {"error": str(e)}

    return results
