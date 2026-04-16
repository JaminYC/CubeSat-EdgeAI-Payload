"""
Genera diagramas del pipeline como imagenes PNG de alta calidad.
Dos versiones: resumida y detallada.

Uso:
    python generate_pipeline_diagram.py
"""

import numpy as np
import cv2
import os


# ══════════════════════════════════════════════════════════════
# Utilidades de dibujo
# ══════════════════════════════════════════════════════════════

def draw_rounded_rect(img, pt1, pt2, color, radius=15, thickness=-1, border_color=None, border_thick=2):
    """Rectangulo con esquinas redondeadas."""
    x1, y1 = pt1
    x2, y2 = pt2
    r = min(radius, (x2 - x1) // 4, (y2 - y1) // 4)

    # Fondo
    if thickness == -1:
        # Cuerpo central
        cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1)
        # Esquinas
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, -1)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, -1)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, -1)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, -1)

    # Borde
    if border_color is not None:
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, border_color, border_thick)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, border_color, border_thick)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, border_color, border_thick)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, border_color, border_thick)
        cv2.line(img, (x1 + r, y1), (x2 - r, y1), border_color, border_thick)
        cv2.line(img, (x1 + r, y2), (x2 - r, y2), border_color, border_thick)
        cv2.line(img, (x1, y1 + r), (x1, y2 - r), border_color, border_thick)
        cv2.line(img, (x2, y1 + r), (x2, y2 - r), border_color, border_thick)


def put_text_centered(img, text, center_x, y, font_scale=0.55, color=(255, 255, 255),
                      thickness=1, font=cv2.FONT_HERSHEY_SIMPLEX):
    """Texto centrado horizontalmente."""
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = center_x - tw // 2
    cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)


def put_multiline_centered(img, lines, center_x, start_y, line_height=22,
                           font_scale=0.50, color=(255, 255, 255), thickness=1):
    """Multiples lineas centradas."""
    for i, line in enumerate(lines):
        put_text_centered(img, line, center_x, start_y + i * line_height,
                         font_scale, color, thickness)


def draw_arrow(img, pt1, pt2, color=(180, 180, 180), thickness=2, tip_length=0.03):
    """Flecha entre dos puntos."""
    cv2.arrowedLine(img, pt1, pt2, color, thickness, tipLength=tip_length, line_type=cv2.LINE_AA)


def draw_arrow_down(img, x, y1, y2, color=(180, 180, 180)):
    """Flecha vertical hacia abajo."""
    draw_arrow(img, (x, y1), (x, y2), color)


def draw_arrow_right(img, x1, x2, y, color=(180, 180, 180)):
    """Flecha horizontal hacia derecha."""
    draw_arrow(img, (x1, y), (x2, y), color, tip_length=0.04)


# ══════════════════════════════════════════════════════════════
# Colores (BGR)
# ══════════════════════════════════════════════════════════════

BG = (30, 30, 30)            # Fondo oscuro
COL_START = (80, 180, 80)    # Verde
COL_LOAD = (140, 120, 60)    # Azul oscuro
COL_CLASS = (160, 130, 50)   # Azul
COL_CAL = (50, 150, 180)     # Amarillo/dorado
COL_ENHANCE = (160, 100, 50) # Azul medio
COL_SEG = (50, 100, 170)     # Naranja/rojo
COL_MEAS = (130, 70, 130)    # Purpura
COL_EXPORT = (80, 140, 80)   # Verde
COL_ARROW = (160, 160, 160)
COL_TEXT = (240, 240, 240)
COL_SUBTEXT = (180, 180, 180)
COL_BORDER = (100, 100, 100)


# ══════════════════════════════════════════════════════════════
# Version RESUMIDA
# ══════════════════════════════════════════════════════════════

def generate_simple():
    """Diagrama resumido del pipeline."""
    W, H = 1200, 830
    img = np.full((H, W, 3), BG, dtype=np.uint8)

    # Titulo
    put_text_centered(img, "Pipeline de Microscopia - CubeSat EdgeAI", W // 2, 40,
                     font_scale=0.9, color=COL_TEXT, thickness=2)
    put_text_centered(img, "Vision general", W // 2, 65,
                     font_scale=0.5, color=COL_SUBTEXT)

    # Nodos del pipeline (flujo vertical)
    cx = W // 2
    box_w = 550
    box_h = 65

    # Nodo 1: Carga
    nodes_main = [
        ("1. Carga y Clasificacion", "Detecta tipo: regla, cebolla, fibra", COL_LOAD, 100),
        ("2. Calibracion", "Regla o manual -> um/pixel", COL_CAL, 195),
    ]

    for title, subtitle, color, y in nodes_main:
        draw_rounded_rect(img, (cx - box_w//2, y), (cx + box_w//2, y + box_h), color,
                         radius=12, border_color=COL_BORDER, border_thick=1)
        put_text_centered(img, title, cx, y + 28, 0.6, COL_TEXT, 1)
        put_text_centered(img, subtitle, cx, y + 50, 0.45, COL_SUBTEXT)

    # Flecha 1->2
    draw_arrow_down(img, cx, 165 + 3, 195 - 3, COL_ARROW)

    # Flecha 2->3
    draw_arrow_down(img, cx, 260 + 3, 295 - 3, COL_ARROW)

    # Nodo 3: Mejora de imagen (OBLIGATORIO, mas grande)
    y_enh = 298
    enh_h = 155
    draw_rounded_rect(img, (cx - box_w//2, y_enh), (cx + box_w//2, y_enh + enh_h),
                     COL_ENHANCE, radius=12, border_color=(200, 140, 60), border_thick=2)
    put_text_centered(img, "3. Mejora de Imagen por IA (OBLIGATORIA)", cx, y_enh + 22,
                     0.58, COL_TEXT, 1)
    put_text_centered(img, "En el espacio: ruido del sensor, radiacion, optica lensless", cx, y_enh + 44,
                     0.40, (200, 180, 140))
    # Sub-items
    items_enh = [
        "Denoising: N2V (self-supervised) / CARE (noise2clean)",
        "Super-res real: FPM multi-angulo (lensless + OLED)",
        "Super-res visual: Real-ESRGAN x4 (solo para reportes,",
        "    no para medicion -- puede inventar detalles falsos)",
    ]
    for i, line in enumerate(items_enh):
        put_text_centered(img, line, cx, y_enh + 66 + i * 20, 0.42, COL_SUBTEXT)

    # Flecha 3->4
    draw_arrow_down(img, cx, y_enh + enh_h + 3, y_enh + enh_h + 30, COL_ARROW)

    # Nodos 4-6
    nodes_bottom = [
        ("4. Segmentacion", "Cellpose / StarDist / OpenCV", COL_SEG, y_enh + enh_h + 33),
        ("5. Medicion", "Area, perimetro, circularidad, grosor", COL_MEAS, y_enh + enh_h + 128),
        ("6. Exportacion", "JSON + CSV + imagenes + reporte", COL_EXPORT, y_enh + enh_h + 223),
    ]

    for title, subtitle, color, y in nodes_bottom:
        draw_rounded_rect(img, (cx - box_w//2, y), (cx + box_w//2, y + box_h), color,
                         radius=12, border_color=COL_BORDER, border_thick=1)
        put_text_centered(img, title, cx, y + 28, 0.6, COL_TEXT, 1)
        put_text_centered(img, subtitle, cx, y + 50, 0.45, COL_SUBTEXT)

    # Flechas entre nodos bottom
    for i in range(len(nodes_bottom) - 1):
        y_from = nodes_bottom[i][3] + box_h
        y_to = nodes_bottom[i + 1][3]
        draw_arrow_down(img, cx, y_from + 3, y_to - 3, COL_ARROW)

    # Nota lateral: graceful degradation
    seg_y = nodes_bottom[0][3]
    note_x = cx + box_w // 2 + 20
    cv2.rectangle(img, (note_x, seg_y), (note_x + 280, seg_y + 65), (40, 40, 60), -1)
    cv2.rectangle(img, (note_x, seg_y), (note_x + 280, seg_y + 65), (100, 80, 80), 1)
    put_text_centered(img, "Graceful Degradation", note_x + 140, seg_y + 25,
                     font_scale=0.5, color=(150, 150, 255))
    put_text_centered(img, "Si IA falla -> OpenCV automatico", note_x + 140, seg_y + 48,
                     font_scale=0.42, color=COL_SUBTEXT)
    cv2.line(img, (cx + box_w // 2, seg_y + 32), (note_x, seg_y + 32), (100, 80, 80), 1, cv2.LINE_AA)

    # Nota lateral: calibracion aplica a medicion
    note2_x = cx - box_w // 2 - 230
    meas_y = nodes_bottom[1][3]
    cv2.rectangle(img, (note2_x, 195), (note2_x + 200, 245), (40, 60, 60), -1)
    cv2.rectangle(img, (note2_x, 195), (note2_x + 200, 245), (80, 120, 100), 1)
    put_text_centered(img, "um/pixel se aplica", note2_x + 100, 215,
                     font_scale=0.42, color=COL_SUBTEXT)
    put_text_centered(img, "a todas las mediciones", note2_x + 100, 233,
                     font_scale=0.42, color=COL_SUBTEXT)
    y_cal = 227
    y_meas = meas_y + 32
    x_line = note2_x + 200
    cv2.line(img, (x_line, y_cal), (x_line, y_meas), (80, 120, 100), 1, cv2.LINE_AA)
    cv2.arrowedLine(img, (x_line, y_meas), (cx - box_w // 2, y_meas),
                    (80, 120, 100), 1, tipLength=0.05, line_type=cv2.LINE_AA)

    # Footer
    put_text_centered(img, "CubeSat EdgeAI Payload - Abril 2026", W // 2, H - 25,
                     font_scale=0.4, color=(100, 100, 100))

    return img


# ══════════════════════════════════════════════════════════════
# Version DETALLADA
# ══════════════════════════════════════════════════════════════

def generate_detailed():
    """Diagrama detallado del pipeline — replica exacta del mermaid del README."""
    W, H = 2400, 2100
    img = np.full((H, W, 3), BG, dtype=np.uint8)

    # Titulo
    put_text_centered(img, "Pipeline de Microscopia - Arquitectura Detallada", W // 2, 45,
                     font_scale=1.1, color=COL_TEXT, thickness=2)
    put_text_centered(img, "CubeSat EdgeAI Payload", W // 2, 75,
                     font_scale=0.6, color=COL_SUBTEXT)

    cx = W // 2

    # ── ETAPA 1: CARGA ──
    bw, bh = 500, 65
    y = 105
    draw_rounded_rect(img, (cx - bw//2, y), (cx + bw//2, y + bh), COL_LOAD,
                     border_color=COL_BORDER)
    put_text_centered(img, "Carga de imagenes", cx, y + 25, 0.65, COL_TEXT, 1)
    put_text_centered(img, "Lee todos los archivos de imagen de la carpeta seleccionada",
                     cx, y + 48, 0.42, COL_SUBTEXT)

    draw_arrow_down(img, cx, y + bh + 3, y + bh + 32, COL_ARROW)

    # ── ETAPA 2: CLASIFICACION ──
    y = 205
    draw_rounded_rect(img, (cx - bw//2, y), (cx + bw//2, y + 80), COL_CLASS,
                     border_color=COL_BORDER)
    put_text_centered(img, "Clasificacion automatica", cx, y + 25, 0.65, COL_TEXT, 1)
    put_multiline_centered(img, [
        "Analiza histogramas, bordes y patrones",
        "para determinar el tipo de cada imagen",
    ], cx, y + 48, 16, 0.40, COL_SUBTEXT)

    # ── Ramificacion en 4 ──
    y_branch_top = y + 80 + 5
    branch_y = 355
    col_x = [280, 780, 1380, 1980]  # 4 columnas: regla, cebolla, fibra, desconocida
    bw2 = 420

    cv2.line(img, (cx, y_branch_top), (cx, y_branch_top + 18), COL_ARROW, 2, cv2.LINE_AA)
    cv2.line(img, (col_x[0], y_branch_top + 18), (col_x[3], y_branch_top + 18), COL_ARROW, 2, cv2.LINE_AA)
    for x in col_x:
        draw_arrow_down(img, x, y_branch_top + 18, branch_y - 3, COL_ARROW)

    # ── Col 0: REGLA ──
    bh2 = 60
    draw_rounded_rect(img, (col_x[0] - bw2//2, branch_y), (col_x[0] + bw2//2, branch_y + bh2),
                     COL_CAL, border_color=COL_BORDER)
    put_text_centered(img, "Imagen de regla", col_x[0], branch_y + 22, 0.55, COL_TEXT, 1)
    put_text_centered(img, "Contiene marcas de escala conocidas para calibrar",
                     col_x[0], branch_y + 44, 0.38, COL_SUBTEXT)

    draw_arrow_down(img, col_x[0], branch_y + bh2 + 3, branch_y + bh2 + 38, COL_ARROW)

    y_cal = branch_y + bh2 + 41
    cal_h = 90
    draw_rounded_rect(img, (col_x[0] - bw2//2, y_cal), (col_x[0] + bw2//2, y_cal + cal_h),
                     COL_CAL, border_color=COL_BORDER)
    put_multiline_centered(img, [
        "Calibracion",
        "Detecta lineas de la regla con",
        "Transformada de Hough y calcula",
        "la relacion micrometros por pixel",
    ], col_x[0], y_cal + 20, 18, 0.42, COL_TEXT)

    y_scale = y_cal + cal_h + 40
    draw_arrow_down(img, col_x[0], y_cal + cal_h + 3, y_scale - 25, COL_ARROW)
    cv2.circle(img, (col_x[0], y_scale), 35, COL_CAL, -1)
    cv2.circle(img, (col_x[0], y_scale), 35, COL_BORDER, 2)
    put_multiline_centered(img, [
        "Factor de",
        "escala",
        "um/pixel",
    ], col_x[0], y_scale - 12, 14, 0.35, COL_TEXT)

    # ── Col 1: CEBOLLA ──
    draw_rounded_rect(img, (col_x[1] - bw2//2, branch_y), (col_x[1] + bw2//2, branch_y + bh2),
                     COL_SEG, border_color=COL_BORDER)
    put_text_centered(img, "Piel de cebolla", col_x[1], branch_y + 22, 0.55, COL_TEXT, 1)
    put_text_centered(img, "Tejido epidermal con celulas rectangulares visibles",
                     col_x[1], branch_y + 44, 0.38, COL_SUBTEXT)

    # Mejora IA cebolla (OBLIGATORIA)
    draw_arrow_down(img, col_x[1], branch_y + bh2 + 3, branch_y + bh2 + 38, COL_ARROW)
    y_enh = branch_y + bh2 + 41
    enh_h = 260
    draw_rounded_rect(img, (col_x[1] - bw2//2, y_enh), (col_x[1] + bw2//2, y_enh + enh_h),
                     COL_ENHANCE, border_color=(200, 140, 60), border_thick=3)
    put_multiline_centered(img, [
        "Mejora de imagen por IA",
        "Etapa obligatoria: en el espacio las",
        "imagenes llegan con ruido del sensor,",
        "radiacion y optica limitada (lensless)",
        "",
        "Denoising:",
        "N2V - self-supervised, no necesita",
        "imagen limpia de referencia",
        "CARE - noise2clean con ruido sintetico",
        "",
        "Super-resolucion:",
        "Real-ESRGAN - upscaling x4 con red",
        "generativa adversarial (RRDBNet)",
        "FPM - reconstruccion multi-angulo,",
        "aumenta resolucion real desde",
        "multiples capturas lensless+OLED",
    ], col_x[1], y_enh + 18, 15, 0.38, COL_TEXT)

    # Segmentacion cebolla
    draw_arrow_down(img, col_x[1], y_enh + enh_h + 3, y_enh + enh_h + 38, COL_ARROW)
    y_seg = y_enh + enh_h + 41
    seg_h = 195
    draw_rounded_rect(img, (col_x[1] - bw2//2, y_seg), (col_x[1] + bw2//2, y_seg + seg_h),
                     COL_SEG, border_color=COL_BORDER)
    put_multiline_centered(img, [
        "Segmentacion celular",
        "",
        "Cellpose cyto3: predice campos de flujo",
        "vectorial que apuntan al centro de cada",
        "celula y agrupa pixeles que convergen",
        "al mismo centro para formar mascaras",
        "",
        "StarDist: predice distancias radiales",
        "desde cada pixel al borde del objeto en",
        "multiples direcciones y reconstruye",
        "poligonos convexos como contorno celular",
        "",
        "OpenCV: umbral adaptativo + watershed",
        "con marcadores morfologicos como fallback",
    ], col_x[1], y_seg + 16, 13, 0.37, COL_TEXT)

    # Medicion cebolla
    draw_arrow_down(img, col_x[1], y_seg + seg_h + 3, y_seg + seg_h + 38, COL_ARROW)
    y_meas = y_seg + seg_h + 41
    meas_h = 80
    draw_rounded_rect(img, (col_x[1] - bw2//2, y_meas), (col_x[1] + bw2//2, y_meas + meas_h),
                     COL_MEAS, border_color=COL_BORDER)
    put_multiline_centered(img, [
        "Medicion celular",
        "Area en um2, perimetro en um,",
        "circularidad, conteo total,",
        "estadisticas por imagen",
    ], col_x[1], y_meas + 18, 16, 0.40, COL_TEXT)

    # ── Col 2: FIBRA ──
    draw_rounded_rect(img, (col_x[2] - bw2//2, branch_y), (col_x[2] + bw2//2, branch_y + bh2),
                     (50, 120, 140), border_color=COL_BORDER)
    put_text_centered(img, "Fibra de algodon", col_x[2], branch_y + 22, 0.55, COL_TEXT, 1)
    put_text_centered(img, "Estructuras filamentosas alargadas y delgadas",
                     col_x[2], branch_y + 44, 0.38, COL_SUBTEXT)

    # Mejora IA fibra (OBLIGATORIA)
    draw_arrow_down(img, col_x[2], branch_y + bh2 + 3, branch_y + bh2 + 38, COL_ARROW)
    y_enh_f = branch_y + bh2 + 41
    enh_f_h = 110
    draw_rounded_rect(img, (col_x[2] - bw2//2, y_enh_f), (col_x[2] + bw2//2, y_enh_f + enh_f_h),
                     COL_ENHANCE, border_color=(200, 140, 60), border_thick=3)
    put_multiline_centered(img, [
        "Mejora de imagen por IA",
        "Denoising obligatorio para fibras:",
        "N2V o CARE para reducir ruido",
        "antes de detectar bordes finos",
    ], col_x[2], y_enh_f + 22, 20, 0.42, COL_TEXT)

    # Deteccion de fibras
    draw_arrow_down(img, col_x[2], y_enh_f + enh_f_h + 3, y_enh_f + enh_f_h + 38, COL_ARROW)
    y_seg_f = y_enh_f + enh_f_h + 41
    seg_f_h = 110
    draw_rounded_rect(img, (col_x[2] - bw2//2, y_seg_f), (col_x[2] + bw2//2, y_seg_f + seg_f_h),
                     (50, 120, 140), border_color=COL_BORDER)
    put_multiline_centered(img, [
        "Deteccion de fibras",
        "",
        "Canny para bordes + Hough para",
        "lineas + esqueletizacion para",
        "extraer el eje central de cada fibra",
    ], col_x[2], y_seg_f + 18, 18, 0.40, COL_TEXT)

    # Medicion fibra
    draw_arrow_down(img, col_x[2], y_seg_f + seg_f_h + 3, y_seg_f + seg_f_h + 38, COL_ARROW)
    y_meas_f = y_seg_f + seg_f_h + 41
    draw_rounded_rect(img, (col_x[2] - bw2//2, y_meas_f), (col_x[2] + bw2//2, y_meas_f + meas_h),
                     COL_MEAS, border_color=COL_BORDER)
    put_multiline_centered(img, [
        "Medicion de fibras",
        "Grosor promedio en um,",
        "longitud en um, numero de",
        "cruces entre fibras",
    ], col_x[2], y_meas_f + 18, 16, 0.40, COL_TEXT)

    # ── Col 3: DESCONOCIDA ──
    draw_rounded_rect(img, (col_x[3] - bw2//2, branch_y), (col_x[3] + bw2//2, branch_y + bh2),
                     (80, 80, 80), border_color=COL_BORDER)
    put_text_centered(img, "Imagen no reconocida", col_x[3], branch_y + 22, 0.55, COL_TEXT, 1)
    put_text_centered(img, "No coincide con ningun patron",
                     col_x[3], branch_y + 44, 0.38, COL_SUBTEXT)

    # Flecha de desconocida hacia mejora cebolla
    unk_arrow_y = branch_y + bh2 + 15
    cv2.line(img, (col_x[3], branch_y + bh2 + 3), (col_x[3], unk_arrow_y), COL_ARROW, 2, cv2.LINE_AA)
    cv2.arrowedLine(img, (col_x[3], unk_arrow_y), (col_x[1] + bw2//2 + 3, unk_arrow_y),
                    COL_ARROW, 2, tipLength=0.015, line_type=cv2.LINE_AA)
    # Linea baja hasta la mejora cebolla
    cv2.line(img, (col_x[1] + bw2//2 + 3, unk_arrow_y), (col_x[1] + bw2//2 + 3, y_enh + 30),
             COL_ARROW, 2, cv2.LINE_AA)
    cv2.arrowedLine(img, (col_x[1] + bw2//2 + 3, y_enh + 30), (col_x[1] + bw2//2, y_enh + 30),
                    COL_ARROW, 2, tipLength=0.15, line_type=cv2.LINE_AA)
    put_text_centered(img, "Se procesa como cebolla", (col_x[1] + col_x[3]) // 2, unk_arrow_y - 8,
                     0.35, (150, 150, 150))

    # ── Lineas de calibracion a mediciones ──
    scale_x = col_x[0]
    scale_y_bottom = y_scale + 35
    # Vertical larga
    cv2.line(img, (scale_x, scale_y_bottom), (scale_x, y_meas_f + 40),
             (50, 150, 180), 2, cv2.LINE_AA)
    # Hacia medicion cebolla
    cv2.arrowedLine(img, (scale_x, y_meas + 40), (col_x[1] - bw2//2, y_meas + 40),
                    (50, 150, 180), 2, tipLength=0.015, line_type=cv2.LINE_AA)
    put_text_centered(img, "um/px", (scale_x + col_x[1] - bw2//2) // 2, y_meas + 33,
                     0.38, (50, 150, 180))
    # Hacia medicion fibra
    cv2.arrowedLine(img, (scale_x, y_meas_f + 40), (col_x[2] - bw2//2, y_meas_f + 40),
                    (50, 150, 180), 2, tipLength=0.01, line_type=cv2.LINE_AA)

    # ── CONVERGENCIA: Agregacion ──
    y_agg = max(y_meas + meas_h, y_meas_f + meas_h) + 55
    cv2.line(img, (col_x[1], y_meas + meas_h + 3), (col_x[1], y_agg - 3), COL_ARROW, 2, cv2.LINE_AA)
    cv2.line(img, (col_x[2], y_meas_f + meas_h + 3), (col_x[2], y_agg - 3), COL_ARROW, 2, cv2.LINE_AA)
    cv2.line(img, (col_x[1], y_agg), (col_x[2], y_agg), COL_ARROW, 2, cv2.LINE_AA)
    mid_x = (col_x[1] + col_x[2]) // 2
    draw_arrow_down(img, mid_x, y_agg, y_agg + 33, COL_ARROW)

    y_agg_box = y_agg + 36
    bw_agg = 550
    agg_h = 70
    draw_rounded_rect(img, (mid_x - bw_agg//2, y_agg_box), (mid_x + bw_agg//2, y_agg_box + agg_h),
                     (80, 100, 60), border_color=COL_BORDER)
    put_text_centered(img, "Agregacion de resultados", mid_x, y_agg_box + 25, 0.6, COL_TEXT, 1)
    put_text_centered(img, "Combina mediciones de todas las imagenes del lote",
                     mid_x, y_agg_box + 48, 0.42, COL_SUBTEXT)
    put_text_centered(img, "en un resumen estadistico global",
                     mid_x, y_agg_box + 64, 0.42, COL_SUBTEXT)

    # ── EXPORTACION ──
    draw_arrow_down(img, mid_x, y_agg_box + agg_h + 3, y_agg_box + agg_h + 33, COL_ARROW)
    y_exp = y_agg_box + agg_h + 36

    exp_w = 340
    exp_h = 85
    exp_gap = 40
    exp_x_start = mid_x - (3 * exp_w + 2 * exp_gap) // 2

    cv2.line(img, (mid_x, y_exp - 3), (mid_x, y_exp + 12), COL_ARROW, 2, cv2.LINE_AA)
    cv2.line(img, (exp_x_start + exp_w//2, y_exp + 12),
             (exp_x_start + 2*(exp_w + exp_gap) + exp_w//2, y_exp + 12), COL_ARROW, 2, cv2.LINE_AA)

    exports = [
        ("Imagenes procesadas",
         "Overlays con contornos coloreados",
         "sobre la imagen original",
         "Mascaras de segmentacion"),
        ("Datos estructurados",
         "CSV con mediciones por celula/fibra",
         "JSON con metadata completa",
         "incluyendo calibracion y config"),
        ("Reporte de texto",
         "Resumen legible con promedios,",
         "desviaciones, conteos totales",
         "y parametros del pipeline"),
    ]
    for i, (title, l1, l2, l3) in enumerate(exports):
        ex = exp_x_start + i * (exp_w + exp_gap)
        ey = y_exp + 18
        draw_arrow_down(img, ex + exp_w//2, y_exp + 12, ey - 2, COL_ARROW)
        draw_rounded_rect(img, (ex, ey), (ex + exp_w, ey + exp_h), COL_EXPORT,
                         border_color=COL_BORDER)
        put_text_centered(img, title, ex + exp_w//2, ey + 20, 0.48, COL_TEXT, 1)
        put_text_centered(img, l1, ex + exp_w//2, ey + 40, 0.37, COL_SUBTEXT)
        put_text_centered(img, l2, ex + exp_w//2, ey + 56, 0.37, COL_SUBTEXT)
        put_text_centered(img, l3, ex + exp_w//2, ey + 72, 0.37, COL_SUBTEXT)

    # Footer
    put_text_centered(img, "CubeSat EdgeAI Payload - Abril 2026", W // 2, H - 25,
                     font_scale=0.45, color=(100, 100, 100))

    return img


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main():
    out_dir = os.path.join(os.path.dirname(__file__), "Documentos de Referencia")
    os.makedirs(out_dir, exist_ok=True)

    # Version resumida
    print("Generando diagrama resumido...")
    simple = generate_simple()
    path_simple = os.path.join(out_dir, "pipeline_resumido.png")
    cv2.imwrite(path_simple, simple)
    print(f"  -> {path_simple}")

    # Version detallada
    print("Generando diagrama detallado...")
    detailed = generate_detailed()
    path_detail = os.path.join(out_dir, "pipeline_detallado.png")
    cv2.imwrite(path_detail, detailed)
    print(f"  -> {path_detail}")

    print("Listo.")


if __name__ == "__main__":
    main()
