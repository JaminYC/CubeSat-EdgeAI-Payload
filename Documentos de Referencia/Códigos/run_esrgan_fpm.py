#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# INTISAT — ESRGAN (SRVGG) por tiles en CPU + salida GRAYSCALE
# Evita OOM en Raspberry Pi procesando la imagen en ventanas con solape.

import os, math, cv2, torch, numpy as np

# ====== RUTAS ======
INPUT_PATH  = "/home/sat/intisat/payloads/image_sensor_microscopy_system/data/rawfourier2/fpm_reconstruction.png"
OUTPUT_PATH = "/home/sat/intisat/payloads/image_sensor_microscopy_system/data/rawfourier2/fpm_sr_gray_x4.png"
MODEL_PATH  = "/home/sat/intisat/payloads/image_sensor_microscopy_system/software/analysis/models/RealESRGAN_x4plus_anime_6B.pth"

# ====== PARÁMETROS ======
SCALE = 2              # 4 ó 2 (si andas muy justo de RAM, pon 2)
TILE  = 80            # tamaño de ventana en el plano de entrada (128/160/192)
OVERLAP = 8           # solape entre tiles (8–32). Más solape = menos costura, más cómputo
PAD_BORD = OVERLAP//2  # padding reflect para bordes

assert os.path.exists(INPUT_PATH), f"No existe la imagen: {INPUT_PATH}"
assert os.path.exists(MODEL_PATH), f"No existe el modelo: {MODEL_PATH}"

print("🧠 Cargando modelo (SRVGG)…")
from realesrgan.archs.srvgg_arch import SRVGGNetCompact

# Modelo SRVGG compacto (compatible con many Real-ESRGAN weights)
model = SRVGGNetCompact(
    num_in_ch=3, num_out_ch=3,
    num_feat=64, num_conv=32,
    upscale=SCALE, act_type='prelu'
)
ckpt = torch.load(MODEL_PATH, map_location="cpu")
state = ckpt.get("params_ema", ckpt)
missing, unexpected = model.load_state_dict(state, strict=False)
model.eval()
print("✅ Modelo listo. Faltones:", len(missing), "No esperados:", len(unexpected))

# ====== CARGA IMAGEN (GRIS) ======
img = cv2.imread(INPUT_PATH, cv2.IMREAD_GRAYSCALE)
if img is None:
    raise RuntimeError(f"No se pudo abrir {INPUT_PATH}")
H, W = img.shape
print(f"📐 Tamaño entrada: {W}×{H}")

# ====== SALIDAS ACUMULADAS (FLOAT32) ======
outH, outW = H * SCALE, W * SCALE
acc = np.zeros((outH, outW, 3), dtype=np.float32)   # acumulador de píxeles
wgt = np.zeros((outH, outW, 1), dtype=np.float32)   # pesos para blending

step = TILE - OVERLAP
if step <= 0:
    raise ValueError("TILE debe ser > OVERLAP. Ajusta parámetros.")

# Ventana de suavizado (coseno) para el blending en región central del tile
def cosine_window(h, w):
    wy = np.hanning(h)
    wx = np.hanning(w)
    win = np.outer(wy, wx).astype(np.float32)
    win = (win - win.min()) / (win.max() - win.min() + 1e-12)
    return win

# Para cada tile en la imagen
tiles_y = math.ceil((H - OVERLAP) / step)
tiles_x = math.ceil((W - OVERLAP) / step)
print(f"🧩 Tiles: {tiles_x} × {tiles_y} (TILE={TILE}, OVERLAP={OVERLAP}, STEP={step})")

win_in = cosine_window(TILE, TILE)  # ventana de entrada
win_in = np.expand_dims(win_in, axis=2)  # (TILE, TILE, 1)

for y0 in range(0, H, step):
    for x0 in range(0, W, step):
        y1 = min(y0 + TILE, H)
        x1 = min(x0 + TILE, W)
        tile = img[y0:y1, x0:x1]

        # Si el tile es más pequeño en bordes, lo adaptamos al tamaño TILE con padding reflect
        ph_top = PAD_BORD if y0 > 0 else 0
        ph_bot = PAD_BORD if y1 < H else 0
        pw_left = PAD_BORD if x0 > 0 else 0
        pw_right = PAD_BORD if x1 < W else 0

        # Para cumplir exactamente TILE en el core, hacemos pad adicional si el bloque es menor
        pad_h_extra = max(0, TILE - tile.shape[0])
        pad_w_extra = max(0, TILE - tile.shape[1])
        ph_bot += pad_h_extra
        pw_right += pad_w_extra

        tile_pad = cv2.copyMakeBorder(tile, ph_top, ph_bot, pw_left, pw_right, borderType=cv2.BORDER_REFLECT)
        # recorta/garantiza al menos TILE+pad si se fuera por rounding raro
        tile_pad = tile_pad[:max(TILE + ph_top + ph_bot, tile_pad.shape[0]),
                            :max(TILE + pw_left + pw_right, tile_pad.shape[1])]

        # Selecciona la región central (TILE×TILE) dentro de tile_pad para inferencia sin bordes duros
        cy0 = ph_top
        cx0 = pw_left
        core = tile_pad[cy0:cy0+TILE, cx0:cx0+TILE]

        # A RGB y tensor
        core_rgb = cv2.cvtColor(core, cv2.COLOR_GRAY2RGB)
        core_t  = torch.from_numpy(core_rgb.transpose(2,0,1)).float().unsqueeze(0) / 255.0

        with torch.no_grad():
            out_t = model(core_t).clamp(0,1)  # (1,3,TILE*SCALE,TILE*SCALE)

        out_np = (out_t.squeeze(0).permute(1,2,0).cpu().numpy())  # float32 [0..1]

        # Región de salida correspondiente (escalada)
        oy0 = y0 * SCALE
        ox0 = x0 * SCALE
        oy1 = oy0 + TILE * SCALE
        ox1 = ox0 + TILE * SCALE

        # Si estamos en el borde final, recortar para no salirnos
        oy1 = min(oy1, outH)
        ox1 = min(ox1, outW)
        out_core = out_np[:oy1-oy0, :ox1-ox0, :]

        # Ventana de blending (escalada)
        win = cv2.resize(win_in.squeeze(), (out_core.shape[1], out_core.shape[0]),
                        interpolation=cv2.INTER_CUBIC).astype(np.float32)
        if win.ndim == 2:  # asegúrate de que sea (h,w,1)
            win = win[..., None]
    # Acumula con pesos
        acc[oy0:oy1, ox0:ox1, :] += out_core * win
        wgt[oy0:oy1, ox0:ox1, :] += win

# Evitar división por cero
wgt[wgt == 0] = 1.0
out_rgb = (acc / wgt).clip(0.0, 1.0)

# A GRAYSCALE para microscopía
out_gray = cv2.cvtColor((out_rgb * 255.0).astype(np.uint8), cv2.COLOR_RGB2GRAY)
cv2.imwrite(OUTPUT_PATH, out_gray)
print(f"✅ SR por tiles completada → {OUTPUT_PATH}")
print(f"📐 Tamaño salida: {out_gray.shape[1]}×{out_gray.shape[0]}  (scale x{SCALE})")
