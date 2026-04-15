"""
Exportacion de resultados: overlays anotados, mascaras, CSV, JSON, resumen.
"""

import os
import csv
import json
import cv2
import numpy as np


def _generate_colors(n):
    """Genera n colores distintos usando HSV."""
    colors = []
    for i in range(max(n, 1)):
        hue = int(180 * i / max(n, 1))
        c = np.array([[[hue, 190, 230]]], dtype=np.uint8)
        bgr = cv2.cvtColor(c, cv2.COLOR_HSV2BGR)[0][0]
        colors.append((int(bgr[0]), int(bgr[1]), int(bgr[2])))
    return colors


def draw_overlay(img_color, seg_result, cfg):
    """
    Overlay detallado: celulas sombreadas, bordes gruesos, numeradas.
    Panel superior con conteo.
    """
    overlay = img_color.copy()
    contours = seg_result.get("contours", [])
    num = len(contours)
    h, w = overlay.shape[:2]

    if num == 0:
        return _add_info_bar(overlay, "Sin celulas detectadas", 0)

    colors = _generate_colors(num)
    alpha = cfg.get("export", {}).get("overlay_alpha", 0.4)

    # 1. Relleno semitransparente
    fill = overlay.copy()
    for i, cnt in enumerate(contours):
        cv2.drawContours(fill, [cnt], -1, colors[i % num], cv2.FILLED)
    cv2.addWeighted(fill, alpha, overlay, 1 - alpha, 0, overlay)

    # 2. Bordes gruesos
    border_thick = max(1, int(min(h, w) / 500))
    for i, cnt in enumerate(contours):
        cv2.drawContours(overlay, [cnt], -1, colors[i % num], border_thick)

    # 3. Numeros en el centroide de cada celula
    font_scale = max(0.3, min(h, w) / 2500)
    font_thick = max(1, int(min(h, w) / 1000))
    for i, cnt in enumerate(contours):
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        label = str(i + 1)

        # Fondo para legibilidad
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                       font_scale, font_thick)
        cv2.rectangle(overlay, (cx - 2, cy - th - 3), (cx + tw + 2, cy + 3),
                      (0, 0, 0), cv2.FILLED)
        cv2.putText(overlay, label, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)

    return _add_info_bar(overlay, "Celulas detectadas", num)


def draw_mask_colored(img_gray, seg_result):
    """Mascara coloreada: fondo oscuro, cada celula en color unico."""
    labels = seg_result.get("labels")
    if labels is None:
        return cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    base = (cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR) * 0.25).astype(np.uint8)
    num = labels.max()
    colors = _generate_colors(num)

    for i in range(1, num + 1):
        mask = (labels == i)
        base[mask] = colors[(i - 1) % len(colors)]

    return _add_info_bar(base, "Mascara de segmentacion", num)


def draw_side_by_side(img_color, overlay, mask_colored):
    """Imagen comparativa: original | overlay | mascara lado a lado."""
    h, w = img_color.shape[:2]

    # Escalar todas a mismo tamano
    target_w = min(w, 600)
    scale = target_w / w
    target_h = int(h * scale)

    imgs = []
    for img in [img_color, overlay, mask_colored]:
        # Quitar info bar si tiene (detectar por diferencia de alto)
        if img.shape[0] > h:
            img = img[img.shape[0] - h:, :]
        resized = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)
        imgs.append(resized)

    # Labels
    labels = ["ORIGINAL", "OVERLAY", "MASCARA"]
    for i, (img, lbl) in enumerate(zip(imgs, labels)):
        cv2.putText(img, lbl, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 255, 255), 2, cv2.LINE_AA)

    combined = np.hstack(imgs)

    # Barra superior
    bar_h = 40
    bar = np.zeros((bar_h, combined.shape[1], 3), dtype=np.uint8)
    bar[:] = (35, 35, 35)
    cv2.putText(bar, "CubeSat EdgeAI -- Comparacion de resultados",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 220, 200), 1,
                cv2.LINE_AA)

    return np.vstack([bar, combined])


def draw_fiber_overlay(img_color, fiber_result):
    """Overlay de fibras con lineas coloreadas y numeradas."""
    overlay = img_color.copy()
    lines = fiber_result.get("lines", [])
    num = len(lines)

    if num == 0:
        return _add_info_bar(overlay, "Sin fibras detectadas", 0)

    for i, line in enumerate(lines):
        pt1 = (line["x1"], line["y1"])
        pt2 = (line["x2"], line["y2"])
        cv2.line(overlay, pt1, pt2, (0, 255, 0), 2)
        mid_x = (line["x1"] + line["x2"]) // 2
        mid_y = (line["y1"] + line["y2"]) // 2
        cv2.putText(overlay, str(i + 1), (mid_x, mid_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1,
                    cv2.LINE_AA)

    return _add_info_bar(overlay, "Fibras detectadas", num)


def _add_info_bar(img, title, count):
    """Agrega barra superior con info."""
    h, w = img.shape[:2]
    bar_h = 45
    bar = np.zeros((bar_h, w, 3), dtype=np.uint8)
    bar[:] = (35, 35, 35)

    text = f"CubeSat EdgeAI  |  {title}: {count}"
    cv2.putText(bar, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (150, 230, 150), 1, cv2.LINE_AA)

    return np.vstack([bar, img])


def save_mask(labels, filepath):
    """Guarda label map como imagen."""
    if labels.max() > 255:
        cv2.imwrite(filepath, labels.astype(np.uint16))
    else:
        cv2.imwrite(filepath, labels.astype(np.uint8))


def save_csv(measurements, filepath):
    """Guarda mediciones en CSV."""
    if not measurements:
        return
    keys = measurements[0].keys()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(measurements)


def save_json(data, filepath):
    """Guarda datos en JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def save_summary_txt(summary, cal_info, filepath):
    """Genera resumen legible en texto plano."""
    lines = []
    lines.append("=" * 50)
    lines.append("  CUBESAT EDGEAI -- REPORTE DE ANALISIS")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Calibracion: {cal_info.get('message', 'N/A')}")
    lines.append(f"  Escala: {cal_info.get('um_per_pixel', 0):.4f} um/pixel")
    lines.append("")

    if "cells" in summary:
        c = summary["cells"]
        lines.append(f"CELULAS DETECTADAS: {c['count']}")
        lines.append(f"  Area media:       {c['area_um2_mean']:.2f} um2")
        lines.append(f"  Area std:         {c['area_um2_std']:.2f} um2")
        lines.append(f"  Perimetro medio:  {c['perimeter_um_mean']:.2f} um")
        lines.append(f"  Circularidad:     {c['circularity_mean']:.4f}")
        lines.append("")

    if "fibers" in summary:
        fb = summary["fibers"]
        lines.append(f"FIBRAS DETECTADAS: {fb['count']}")
        lines.append(f"  Longitud media:   {fb['length_um_mean']:.2f} um")
        lines.append(f"  Longitud std:     {fb['length_um_std']:.2f} um")
        lines.append("")

    lines.append("=" * 50)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_results(
    output_dir,
    image_name,
    img_color,
    img_gray=None,
    seg_result=None,
    fiber_result=None,
    cell_measurements=None,
    fiber_measurements=None,
    summary=None,
    cal_info=None,
    cfg=None,
):
    """Exporta todos los resultados de una imagen."""
    base = os.path.splitext(image_name)[0]
    exp = cfg.get("export", {}) if cfg else {}

    overlay_path = None

    # Overlays anotados
    if exp.get("save_overlays", True):
        if seg_result and seg_result.get("contours"):
            ov = draw_overlay(img_color, seg_result, cfg)
            overlay_path = os.path.join(output_dir, f"{base}_overlay.png")
            cv2.imwrite(overlay_path, ov)

            # Mascara coloreada
            if img_gray is not None:
                mask_col = draw_mask_colored(img_gray, seg_result)
                cv2.imwrite(os.path.join(output_dir, f"{base}_mask_color.png"), mask_col)

                # Comparacion lado a lado
                # Quitar barra del overlay para el side-by-side
                compare = draw_side_by_side(img_color, ov, mask_col)
                cv2.imwrite(os.path.join(output_dir, f"{base}_comparacion.png"), compare)

        if fiber_result and fiber_result.get("lines"):
            ov = draw_fiber_overlay(img_color, fiber_result)
            overlay_path = os.path.join(output_dir, f"{base}_fibers_overlay.png")
            cv2.imwrite(overlay_path, ov)

    # Masks raw
    if exp.get("save_masks", True) and seg_result is not None:
        labels = seg_result.get("labels")
        if labels is not None:
            save_mask(labels, os.path.join(output_dir, f"{base}_mask.png"))

    # CSV
    if exp.get("save_csv", True):
        if cell_measurements:
            save_csv(cell_measurements, os.path.join(output_dir, f"{base}_cells.csv"))
        if fiber_measurements:
            save_csv(fiber_measurements, os.path.join(output_dir, f"{base}_fibers.csv"))

    # JSON
    if exp.get("save_json", True) and summary:
        save_json(
            {"calibration": cal_info, "summary": summary},
            os.path.join(output_dir, f"{base}_results.json"),
        )

    # Summary txt
    if exp.get("save_summary", True) and summary and cal_info:
        save_summary_txt(
            summary, cal_info, os.path.join(output_dir, f"{base}_summary.txt")
        )

    return overlay_path
