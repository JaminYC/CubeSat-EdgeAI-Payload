"""
Visor interactivo de resultados de segmentacion.
Muestra original vs overlay con celulas numeradas.

Controles:
  A / D  o  <- / ->  : imagen anterior / siguiente
  TAB                 : alternar original / overlay / mascara
  +  /  -            : zoom in / out
  R                   : resetear vista
  S                   : guardar captura actual
  ESC / Q             : cerrar
"""

import os
import cv2
import numpy as np
from .preprocess import load_image, preprocess
from .segmentation_onion import segment_onion
from .segmentation_fiber import detect_fibers
from .measurement import measure_cells, measure_fibers
from .classifier import scan_folder, classify_image
from .config import load_config


def _build_cell_overlay(img_color, seg_result, measurements):
    """Crea overlay detallado con celulas numeradas y sombreadas."""
    overlay = img_color.copy()
    contours = seg_result.get("contours", [])
    num = len(contours)
    h, w = overlay.shape[:2]

    # Generar colores unicos (HSV -> BGR)
    colors = []
    for i in range(max(num, 1)):
        hue = int(180 * i / max(num, 1))
        c = np.array([[[hue, 180, 220]]], dtype=np.uint8)
        rgb = cv2.cvtColor(c, cv2.COLOR_HSV2BGR)[0][0]
        colors.append((int(rgb[0]), int(rgb[1]), int(rgb[2])))

    # Capa de relleno semitransparente
    fill_layer = overlay.copy()
    for i, cnt in enumerate(contours):
        color = colors[i % len(colors)]
        cv2.drawContours(fill_layer, [cnt], -1, color, cv2.FILLED)
    cv2.addWeighted(fill_layer, 0.35, overlay, 0.65, 0, overlay)

    # Bordes gruesos
    for i, cnt in enumerate(contours):
        color = colors[i % len(colors)]
        cv2.drawContours(overlay, [cnt], -1, color, 2)

    # Numeros y centroides
    font_scale = max(0.3, min(h, w) / 2000)
    thickness = max(1, int(min(h, w) / 800))

    for m in measurements:
        cx, cy = m["centroid_x"], m["centroid_y"]
        cell_id = str(m["id"])

        # Fondo negro para legibilidad
        (tw, th), _ = cv2.getTextSize(cell_id, cv2.FONT_HERSHEY_SIMPLEX,
                                       font_scale, thickness)
        cv2.rectangle(overlay, (cx - 2, cy - th - 4), (cx + tw + 2, cy + 4),
                      (0, 0, 0), cv2.FILLED)
        cv2.putText(overlay, cell_id, (cx, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255),
                    thickness, cv2.LINE_AA)

    return overlay


def _build_mask_view(img_gray, seg_result):
    """Crea vista de mascara coloreada sobre fondo oscuro."""
    labels = seg_result.get("labels")
    if labels is None:
        return cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    # Fondo oscuro
    base = (cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR) * 0.3).astype(np.uint8)

    num = labels.max()
    for i in range(1, num + 1):
        hue = int(180 * i / max(num, 1))
        color_hsv = np.array([[[hue, 200, 255]]], dtype=np.uint8)
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
        mask = (labels == i)
        base[mask] = color_bgr

    return base


def _build_fiber_overlay(img_color, fiber_result, measurements):
    """Overlay de fibras con lineas numeradas."""
    overlay = img_color.copy()
    for m in measurements:
        pt1 = (m["x1"], m["y1"])
        pt2 = (m["x2"], m["y2"])
        cv2.line(overlay, pt1, pt2, (0, 255, 0), 2)
        mid_x = (m["x1"] + m["x2"]) // 2
        mid_y = (m["y1"] + m["y2"]) // 2
        cv2.putText(overlay, str(m["id"]), (mid_x, mid_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1,
                    cv2.LINE_AA)
    return overlay


def _draw_info_panel(img, image_name, view_name, num_detected, img_type,
                      current_idx, total_imgs):
    """Dibuja panel de informacion en la parte superior."""
    h, w = img.shape[:2]
    panel_h = 50
    panel = np.zeros((panel_h, w, 3), dtype=np.uint8)
    panel[:] = (40, 40, 40)

    font = cv2.FONT_HERSHEY_SIMPLEX
    # Linea 1: nombre de imagen y navegacion
    text1 = f"[{current_idx + 1}/{total_imgs}] {image_name}  |  Tipo: {img_type}"
    cv2.putText(panel, text1, (10, 18), font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    # Linea 2: vista actual y conteo
    text2 = f"Vista: {view_name}  |  Detectados: {num_detected}  |  "
    text2 += "A/D: cambiar img  |  TAB: cambiar vista  |  ESC: salir"
    cv2.putText(panel, text2, (10, 38), font, 0.4, (150, 220, 150), 1, cv2.LINE_AA)

    # Concatenar panel + imagen
    result = np.vstack([panel, img])
    return result


def run_viewer(input_folder: str = None, config_path: str = None,
               um_per_pixel: float = 0.5):
    """
    Visor interactivo: procesa y muestra cada imagen con overlay.
    """
    cfg = load_config(config_path)
    folder = input_folder or cfg["paths"]["input_folder"]
    classified = scan_folder(folder, cfg)

    # Juntar todas las imagenes en orden: ruler, onion, fiber, unknown
    all_images = []
    for img_type in ["ruler", "onion", "fiber", "unknown"]:
        for fpath in classified[img_type]:
            all_images.append((fpath, img_type))

    if not all_images:
        print("No se encontraron imagenes.")
        return

    print(f"Visor: {len(all_images)} imagenes encontradas")
    print("Controles: A/D=navegar  TAB=cambiar vista  +/-=zoom  ESC=salir")

    current_idx = 0
    view_mode = 0  # 0=original, 1=overlay, 2=mascara
    view_names = ["ORIGINAL", "OVERLAY (celulas)", "MASCARA"]
    zoom = 1.0
    cache = {}

    window_name = "CubeSat EdgeAI - Visor de Resultados"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1024, 700)

    while True:
        fpath, img_type = all_images[current_idx]
        fname = os.path.basename(fpath)

        # Procesar si no esta en cache
        if current_idx not in cache:
            img_color, img_gray = load_image(fpath)
            img_pp, mask = preprocess(img_gray, cfg)

            views = [img_color.copy()]  # [0] original
            num_detected = 0

            if img_type in ("onion", "unknown", "ruler"):
                seg = segment_onion(img_pp, cfg, mask)
                cells = measure_cells(seg, um_per_pixel)
                num_detected = seg["num_cells"]
                views.append(_build_cell_overlay(img_color, seg, cells))
                views.append(_build_mask_view(img_gray, seg))
            elif img_type == "fiber":
                fiber_res = detect_fibers(img_pp, cfg)
                fibers = measure_fibers(fiber_res, um_per_pixel)
                num_detected = fiber_res["num_fibers"]
                views.append(_build_fiber_overlay(img_color, fiber_res, fibers))
                # No hay mascara de labels para fibras, usar overlay como 3ra vista
                views.append(views[1].copy())

            cache[current_idx] = (views, num_detected)

        views, num_detected = cache[current_idx]
        view_idx = view_mode % len(views)
        display = views[view_idx].copy()

        # Zoom
        if zoom != 1.0:
            h, w = display.shape[:2]
            new_w = int(w * zoom)
            new_h = int(h * zoom)
            if new_w > 0 and new_h > 0:
                display = cv2.resize(display, (new_w, new_h),
                                      interpolation=cv2.INTER_LINEAR)

        # Info panel
        vname = view_names[view_idx] if view_idx < len(view_names) else "VISTA"
        display = _draw_info_panel(display, fname, vname, num_detected,
                                    img_type, current_idx, len(all_images))

        cv2.imshow(window_name, display)
        key = cv2.waitKey(0) & 0xFF

        if key == 27 or key == ord("q"):  # ESC or Q
            break
        elif key == ord("d") or key == 83 or key == 3:  # D or Right arrow
            current_idx = (current_idx + 1) % len(all_images)
            view_mode = 1  # mostrar overlay por defecto
        elif key == ord("a") or key == 81 or key == 2:  # A or Left arrow
            current_idx = (current_idx - 1) % len(all_images)
            view_mode = 1
        elif key == 9:  # TAB
            view_mode = (view_mode + 1) % 3
        elif key == ord("+") or key == ord("="):
            zoom = min(zoom * 1.25, 5.0)
        elif key == ord("-"):
            zoom = max(zoom / 1.25, 0.2)
        elif key == ord("r"):
            zoom = 1.0
        elif key == ord("s"):
            save_path = f"captura_{fname}"
            cv2.imwrite(save_path, display)
            print(f"Guardado: {save_path}")

    cv2.destroyAllWindows()
