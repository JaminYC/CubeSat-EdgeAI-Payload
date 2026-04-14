"""
FPM Calibration and Measurement Tool
=====================================
Herramienta de calibración y medición dimensional para microscopía FPM
usando microesferas de poliestireno de 2 umm como patrón de referencia.

Autor: Sistema de calibración para FPM
Fecha: 2026-01-19

Uso:
    python fpm_calibration_tool.py <ruta_imagen>

Controles:
    c - Modo calibración (medir microesferas de 2 umm)
    m - Modo medición (medir estructuras desconocidas)
    r - Reset (limpiar medición actual)
    s - Guardar resultados en CSV
    q - Salir
"""

import cv2
import numpy as np
import csv
from datetime import datetime
import os
import sys
import time
from tkinter import Tk, filedialog, messagebox


class FPMCalibrationTool:
    """
    Herramienta de calibración y medición para imágenes FPM reconstruidas.
    """

    def __init__(self, image_path):
        """
        Inicializa la herramienta con una imagen FPM.

        Args:
            image_path: Ruta a la imagen reconstruida FPM
        """
        self.image_path = image_path
        self.original_image = cv2.imread(image_path)

        if self.original_image is None:
            raise ValueError(f"No se pudo cargar la imagen: {image_path}")

        self.display_image = self.original_image.copy()
        self.window_name = "FPM Calibration Tool"

        # Estado de la aplicación
        self.mode = None  # 'calibration' o 'measurement'
        self.points = []  # Puntos seleccionados por el usuario
        
        # Estado de zoom por región (legacy)
        self.zoom_mode = False
        self.zoom_rect_start = None
        self.zoom_rect_end = None
        self.zoom_rect_drawing = False

        # ROI (Region of Interest) para zoom eficiente a altos factores
        # Al activar ROI, update_display solo hace resize del recorte pequeño
        # en vez de la imagen entera — indispensable para zoom > x30.
        # Las coordenadas de calibración siguen siendo correctas porque
        # screen_to_image_coords suma el offset del ROI.
        self.roi_region = None        # (x1, y1, x2, y2) en coords imagen, o None
        self.roi_selecting = False    # True mientras el usuario arrastra el rect
        self.roi_start_img = None     # Coord imagen donde empezó el drag
        self.roi_preview_end = None   # Posición pantalla actual durante el drag

        # Datos de calibración
        self.calibration_data = []  # Lista de dict con mediciones
        
        # Parámetros del patrón de calibración
        self.calibration_pattern_type = 'line'  # 'sphere' o 'line'
        self.calibration_pattern_size_um = 1000.0  # Por defecto 1 mm = 1000 um

        # Parámetros físicos del sistema óptico (para escala automática)
        self.sensor_pixel_um = 1.47   # OV5647: 1.47 µm/px nativos
        self.upscale_factor  = 1.0    # factor Real-ESRGAN (1 = sin upscaling)
        # upscale_factor > 1 → um_per_pixel = sensor_pixel_um / upscale_factor

        # Datos de mediciones
        self.measurement_data = []  # Lista de dict con mediciones
        self.geometry_data = []  # Lista de mediciones geométricas

        # Escala calculada
        self.scale_um_per_pixel = None
        self.scale_std = None

        # Contador de mediciones
        self.calibration_count = 0
        self.measurement_count = 0
        self.geometry_count = 0

        # Submodo de geometría
        self.geometry_mode = None  # 'circle', 'rectangle', 'triangle', 'polygon'

        # Configuración de visualización
        self.circle_color = (0, 255, 0)  # Verde
        self.point_color = (0, 0, 255)   # Rojo
        self.text_color = (255, 255, 255)  # Blanco

        # Control de zoom
        self.zoom_level = 1.0
        self.zoom_min = 0.1
        self.zoom_max = 100.0
        self.zoom_step = 0.1

        # Offset para pan (desplazamiento)
        self.pan_offset = [0, 0]
        self.is_panning = False
        self.pan_start = None
        self.pan_step = 50  # Píxeles a mover con las flechas

        # Panel de información
        self.panel_height = 240  # Altura del panel superior

        # Caché de anotaciones: evita redibujar todo en cada frame de pan/zoom
        self._annotated_base = None   # Imagen con anotaciones permanentes cacheada
        self._annotations_dirty = True  # True = necesita reconstruir el cache

        # Throttle de display: limitar a 60fps durante pan con mouse
        self._last_display_time = 0.0
        self._display_interval = 1.0 / 60  # 60fps máximo

        # Factor de zoom multiplicativo (más natural que lineal)
        self.zoom_factor = 1.15  # ×1.15 por paso

        # Posición del cursor en coords de imagen (para previews en vivo)
        self._mouse_pos = None  # (img_x, img_y) o None si fuera de imagen

        # CLAHE: contraste realzado para ver microesferas pequeñas
        self.clahe_active = False
        self._clahe_image = None   # cacheada la primera vez que se activa

        # Candidatos HoughCircles: lista de (cx, cy, r) en coords imagen, o None
        self._candidates = None

        # ── Análisis de luminancia ─────────────────────────────────────────────
        # Mapa de falso color
        self.false_color_active = False   # toggle con 'f'
        self._false_color_image = None    # cache del colormap aplicado

        # Selección de ROI para histograma (independiente del ROI de zoom)
        self.lum_selecting = False        # arrastrando rectángulo
        self.lum_start_img = None         # punto inicio en coords imagen
        self.lum_preview_end = None       # punto final en pantalla (preview)
        self.lum_region = None            # (x1,y1,x2,y2) región confirmada

        # Perfil de intensidad (line scan)
        self.linescan_active = False      # esperando dos clicks para la línea
        self.linescan_points = []         # 0, 1 o 2 puntos en coords imagen

    def _raw_screen_to_image(self, screen_x, screen_y_adj):
        """
        Convierte coords de pantalla (ya descontado el panel) a coords de imagen,
        teniendo en cuenta el ROI activo si lo hay.
        Devuelve coordenadas FLOTANTES (sub-pixel) para máxima precisión.
        A zoom x60, cada pixel de pantalla = 1/60 px de imagen ≈ 0.017 px —
        redondear a int tiraría 98% de la resolución disponible.
        Solo se convierte a int al llamar funciones de dibujo cv2.
        """
        if self.roi_region is not None:
            rx1, ry1 = self.roi_region[0], self.roi_region[1]
            img_x = rx1 + (screen_x - self.pan_offset[0]) / self.zoom_level
            img_y = ry1 + (screen_y_adj - self.pan_offset[1]) / self.zoom_level
        else:
            img_x = (screen_x - self.pan_offset[0]) / self.zoom_level
            img_y = (screen_y_adj - self.pan_offset[1]) / self.zoom_level
        return img_x, img_y

    def mouse_callback(self, event, x, y, flags, param):
        """
        Callback para eventos del mouse.
        Cuando roi_selecting está activo, el botón izquierdo dibuja el rectángulo
        de selección en vez de registrar puntos de medición.
        """
        # ── Modo selección ROI luminancia ─────────────────────────────────────
        if self.lum_selecting:
            if event == cv2.EVENT_LBUTTONDOWN:
                adj_y = y - self.panel_height
                if adj_y >= 0:
                    self.lum_start_img = self._raw_screen_to_image(x, adj_y)
                    self.lum_preview_end = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE and self.lum_start_img is not None:
                self.lum_preview_end = (x, y)
                now = time.monotonic()
                if now - self._last_display_time >= self._display_interval:
                    self._last_display_time = now
                    self.update_display()
            elif event == cv2.EVENT_LBUTTONUP and self.lum_start_img is not None:
                adj_y = y - self.panel_height
                end_img = self._raw_screen_to_image(x, adj_y)
                sx2, sy2 = self.lum_start_img
                ex2, ey2 = end_img
                H2, W2 = self.original_image.shape[:2]
                sx2 = max(0, min(W2-1, sx2)); sy2 = max(0, min(H2-1, sy2))
                ex2 = max(0, min(W2-1, ex2)); ey2 = max(0, min(H2-1, ey2))
                x1l, x2l = min(sx2, ex2), max(sx2, ex2)
                y1l, y2l = min(sy2, ey2), max(sy2, ey2)
                self.lum_selecting = False
                self.lum_start_img = None
                self.lum_preview_end = None
                if x2l - x1l > 3 and y2l - y1l > 3:
                    self.lum_region = (x1l, y1l, x2l, y2l)
                    self.update_display()
                    self.show_luminance_histogram(self.lum_region)
                else:
                    self.update_display()
            return

        # ── Modo selección de ROI (tiene prioridad sobre mediciones) ──────────
        if self.roi_selecting:
            if event == cv2.EVENT_MOUSEWHEEL:
                # Permitir zoom mientras se elige el área
                if flags > 0:
                    self.zoom_level = min(self.zoom_max, self.zoom_level * self.zoom_factor)
                else:
                    self.zoom_level = max(self.zoom_min, self.zoom_level / self.zoom_factor)
                self.update_display()

            elif event == cv2.EVENT_LBUTTONDOWN:
                adj_y = y - self.panel_height
                if adj_y >= 0:
                    self.roi_start_img = self._raw_screen_to_image(x, adj_y)
                    self.roi_preview_end = (x, y)

            elif event == cv2.EVENT_MOUSEMOVE and self.roi_start_img is not None:
                self.roi_preview_end = (x, y)
                now = time.monotonic()
                if now - self._last_display_time >= self._display_interval:
                    self._last_display_time = now
                    self.update_display()

            elif event == cv2.EVENT_LBUTTONUP and self.roi_start_img is not None:
                adj_y = y - self.panel_height
                end_img = self._raw_screen_to_image(x, adj_y)
                sx, sy = self.roi_start_img
                ex, ey = end_img
                H, W = self.original_image.shape[:2]
                sx = max(0, min(W - 1, sx)); sy = max(0, min(H - 1, sy))
                ex = max(0, min(W - 1, ex)); ey = max(0, min(H - 1, ey))
                x1, x2 = min(sx, ex), max(sx, ex)
                y1, y2 = min(sy, ey), max(sy, ey)
                if x2 - x1 > 5 and y2 - y1 > 5:
                    self.roi_region = (x1, y1, x2, y2)
                    self.pan_offset = [0, 0]
                    self._annotations_dirty = True
                    # Auto-ajustar zoom para que el ROI llene el viewport
                    out_h, out_w = self.original_image.shape[:2]
                    fit_zoom = min(out_w / (x2 - x1), out_h / (y2 - y1))
                    self.zoom_level = max(1.0, min(self.zoom_max, fit_zoom))
                self.roi_selecting = False
                self.roi_start_img = None
                self.roi_preview_end = None
                self.update_display()
            return  # bloquear el resto del callback mientras se selecciona ROI

        # ── Eventos normales ───────────────────────────────────────────────────
        img_x, img_y = self.screen_to_image_coords(x, y)

        # Zoom con rueda del ratón (multiplicativo: más natural)
        if event == cv2.EVENT_MOUSEWHEEL:
            if flags > 0:  # Scroll up - acercar
                self.zoom_level = min(self.zoom_max, self.zoom_level * self.zoom_factor)
            else:  # Scroll down - alejar
                self.zoom_level = max(self.zoom_min, self.zoom_level / self.zoom_factor)
            self.update_display()

        # Pan con botón derecho
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.is_panning = True
            self.pan_start = (x, y)

        elif event == cv2.EVENT_RBUTTONUP:
            self.is_panning = False
            self.pan_start = None

        elif event == cv2.EVENT_MOUSEMOVE:
            # Pan con botón derecho
            if self.is_panning and self.pan_start is not None:
                dx = x - self.pan_start[0]
                dy = y - self.pan_start[1]
                self.pan_offset[0] += dx
                self.pan_offset[1] += dy
                self.pan_start = (x, y)

            # Actualizar posición del cursor para previews en vivo
            self._mouse_pos = (img_x, img_y) if img_x is not None else None

            # Redibujar si hay preview activo o panning (throttle 60fps)
            needs_update = (self.is_panning or
                            (self.points and self.mode in ('calibration', 'measurement', 'geometry')) or
                            (self.linescan_active and len(self.linescan_points) == 1))
            if needs_update:
                now = time.monotonic()
                if now - self._last_display_time >= self._display_interval:
                    self._last_display_time = now
                    self.update_display()

        # Doble click: zoom rápido centrado en ese punto (sin registrar punto)
        elif event == cv2.EVENT_LBUTTONDBLCLK:
            if img_x is not None and img_y is not None:
                # El primer click del doble ya añadió un punto — lo quitamos
                if self.points:
                    self.points.pop()
                # Zoom ×4 acumulativo centrado en el punto clicado
                self.zoom_level = min(self.zoom_max, self.zoom_level * 4.0)
                out_h, out_w = self.original_image.shape[:2]
                if self.roi_region is not None:
                    rx1, ry1 = self.roi_region[0], self.roi_region[1]
                    self.pan_offset[0] = out_w // 2 - int((img_x - rx1) * self.zoom_level)
                    self.pan_offset[1] = out_h // 2 - int((img_y - ry1) * self.zoom_level)
                else:
                    self.pan_offset[0] = out_w // 2 - int(img_x * self.zoom_level)
                    self.pan_offset[1] = out_h // 2 - int(img_y * self.zoom_level)
                self.update_display()
                print(f"\nZoom rapido: x{self.zoom_level:.1f} centrado en ({img_x:.1f}, {img_y:.1f})")

        # Click izquierdo: line scan (si está activo, tiene prioridad)
        elif event == cv2.EVENT_LBUTTONDOWN and self.linescan_active:
            if img_x is not None and img_y is not None:
                self.linescan_points.append((img_x, img_y))
                if len(self.linescan_points) == 2:
                    self.linescan_active = False
                    self.show_linescan(self.linescan_points[0], self.linescan_points[1])
                    self.linescan_points = []
                    self.update_display()
                else:
                    self.update_display()

        # Click izquierdo para mediciones
        elif event == cv2.EVENT_LBUTTONDOWN:
            if img_x is not None and img_y is not None:
                self.points.append((img_x, img_y))

                if self.mode == 'calibration':
                    self.handle_calibration_point(img_x, img_y)
                elif self.mode == 'measurement':
                    self.handle_measurement_point(img_x, img_y)
                elif self.mode == 'geometry':
                    self.handle_geometry_point(img_x, img_y)

    def screen_to_image_coords(self, screen_x, screen_y):
        """
        Convierte coordenadas de pantalla a coordenadas de imagen original.
        Si hay ROI activa, suma el offset del ROI para que las mediciones
        siempre referencien la imagen completa (calibración correcta).
        """
        screen_y_adjusted = screen_y - self.panel_height
        if screen_y_adjusted < 0:
            return None, None

        img_x, img_y = self._raw_screen_to_image(screen_x, screen_y_adjusted)

        # Verificar límites en imagen original
        if 0 <= img_x < self.original_image.shape[1] and 0 <= img_y < self.original_image.shape[0]:
            return img_x, img_y
        return None, None

    def image_to_screen_coords(self, img_x, img_y):
        """
        Convierte coordenadas de imagen original a coordenadas de pantalla.
        Si hay ROI activa, resta el offset del ROI antes de escalar.
        """
        if self.roi_region is not None:
            rx1, ry1 = self.roi_region[0], self.roi_region[1]
            screen_x = int((img_x - rx1) * self.zoom_level + self.pan_offset[0])
            screen_y = int((img_y - ry1) * self.zoom_level + self.pan_offset[1] + self.panel_height)
        else:
            screen_x = int(img_x * self.zoom_level + self.pan_offset[0])
            screen_y = int(img_y * self.zoom_level + self.pan_offset[1] + self.panel_height)
        return screen_x, screen_y

    def handle_calibration_point(self, x, y):
        """
        Maneja los clicks en modo calibración.
        """
        if len(self.points) == 1:
            # Primer click
            if self.calibration_pattern_type == 'sphere':
                print(f"  Centro marcado en: ({x}, {y})")
            else:
                print(f"  Punto de inicio marcado en: ({x}, {y})")

        elif len(self.points) == 2:
            # Segundo click
            p1 = self.points[0]
            p2 = self.points[1]

            if self.calibration_pattern_type == 'sphere':
                # Calcular radio y diámetro en píxeles (p1=centro, p2=borde)
                radius_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                diameter_px = 2 * radius_px
            else:
                # Calcular longitud de la línea en píxeles
                length_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                # Para compatibilidad con el resto del código y formato CSV, 
                # guardamos la longitud como diámetro y la mitad como radio
                diameter_px = length_px
                radius_px = length_px / 2.0

            # Calcular escala umm/pixel
            um_per_pixel = self.calibration_pattern_size_um / diameter_px

            # Guardar datos
            self.calibration_count += 1
            self.calibration_data.append({
                'id': self.calibration_count,
                'center_x': p1[0],
                'center_y': p1[1],
                'border_x': p2[0],
                'border_y': p2[1],
                'radius_px': radius_px,
                'diameter_px': diameter_px,
                'um_per_pixel': um_per_pixel
            })

            # Actualizar escala global
            self.update_scale()

            if self.calibration_pattern_type == 'sphere':
                print(f"  OK Microesfera #{self.calibration_count}: D={diameter_px:.2f}px -> {um_per_pixel:.4f}umm/px")
            else:
                print(f"  OK Patrón Lineal #{self.calibration_count}: L={diameter_px:.2f}px -> {um_per_pixel:.4f}umm/px")

            # Reset para siguiente medición
            self.points = []
            self._annotations_dirty = True  # Invalidar caché

            # Actualizar visualización
            self.update_display()

            # Mostrar estadísticas
            self.display_statistics()

    def handle_measurement_point(self, x, y):
        """
        Maneja los clicks en modo medición.
        """
        if self.scale_um_per_pixel is None:
            print("AVISO: Primero debes calibrar (presiona 'c' y mide microesferas)")
            self.points = []
            self.mode = None
            return

        if len(self.points) == 1:
            # Primer punto
            print(f"  Punto 1 marcado en: ({x}, {y})")
            self.update_display()

        elif len(self.points) == 2:
            # Segundo punto: calcular distancia
            p1 = self.points[0]
            p2 = self.points[1]

            # Distancia en píxeles
            distance_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

            # Convertir a micrómetros
            distance_um = distance_px * self.scale_um_per_pixel

            self.measurement_count += 1

            # Guardar datos de medición
            self.measurement_data.append({
                'id': self.measurement_count,
                'p1_x': p1[0],
                'p1_y': p1[1],
                'p2_x': p2[0],
                'p2_y': p2[1],
                'distance_px': distance_px,
                'distance_um': distance_um
            })

            print(f"OK Medicion #{self.measurement_count}:")
            print(f"  Distancia: {distance_px:.2f} px = {distance_um:.2f} um")

            # Reset para siguiente medición
            self.points = []
            self._annotations_dirty = True  # Invalidar caché
            self.update_display()

    def handle_geometry_point(self, x, y):
        """
        Maneja los clicks en modo geometría.
        """
        if self.scale_um_per_pixel is None:
            print("AVISO: Primero debes calibrar:")
            print("  - Presiona 'c' y mide microesferas, O")
            print("  - Presiona 'e' para introducir escala manualmente")
            self.points = []
            self.mode = None
            return

        # Actualizar visualización con puntos temporales
        self.update_display()

        # Círculo: 3 puntos en el borde
        if self.geometry_mode == 'circle':
            if len(self.points) == 3:
                self.measure_circle()

        # Rectángulo: 2 esquinas opuestas
        elif self.geometry_mode == 'rectangle':
            if len(self.points) == 2:
                self.measure_rectangle()

        # Triángulo: 3 vértices
        elif self.geometry_mode == 'triangle':
            if len(self.points) == 3:
                self.measure_triangle()

        # Polígono: presionar Enter para finalizar
        elif self.geometry_mode == 'polygon':
            # Se maneja con tecla Enter en el loop principal
            pass

    def measure_circle(self):
        """Mide un círculo a partir de 3 puntos en el borde."""
        p1, p2, p3 = self.points[0], self.points[1], self.points[2]

        # Calcular centro y radio usando geometría
        # Fórmula: centro del círculo que pasa por 3 puntos
        ax, ay = p1
        bx, by = p2
        cx, cy = p3

        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 0.001:
            print("ERROR: Los puntos son colineales, no forman un circulo")
            self.points = []
            return

        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d

        center_x, center_y = ux, uy
        radius_px = np.sqrt((ax - ux)**2 + (ay - uy)**2)
        diameter_px = 2 * radius_px

        # Convertir a micrómetros
        radius_um = radius_px * self.scale_um_per_pixel
        diameter_um = diameter_px * self.scale_um_per_pixel
        area_px = np.pi * radius_px**2
        area_um = area_px * (self.scale_um_per_pixel**2)

        self.geometry_count += 1
        self.geometry_data.append({
            'id': self.geometry_count,
            'type': 'circle',
            'center_x': center_x,
            'center_y': center_y,
            'radius_px': radius_px,
            'diameter_px': diameter_px,
            'radius_um': radius_um,
            'diameter_um': diameter_um,
            'area_um2': area_um,
            'points': self.points.copy()
        })

        print(f"OK Circulo #{self.geometry_count}:")
        print(f"  Radio: {radius_um:.2f} um ({radius_px:.1f} px)")
        print(f"  Diametro: {diameter_um:.2f} um ({diameter_px:.1f} px)")
        print(f"  Area: {area_um:.2f} um^2")

        self.points = []
        self._annotations_dirty = True
        self.update_display()

    def measure_rectangle(self):
        """Mide un rectángulo a partir de 2 esquinas opuestas."""
        p1, p2 = self.points[0], self.points[1]

        width_px = abs(p2[0] - p1[0])
        height_px = abs(p2[1] - p1[1])
        area_px = width_px * height_px
        perimeter_px = 2 * (width_px + height_px)

        # Convertir a micrómetros
        width_um = width_px * self.scale_um_per_pixel
        height_um = height_px * self.scale_um_per_pixel
        area_um = area_px * (self.scale_um_per_pixel**2)
        perimeter_um = perimeter_px * self.scale_um_per_pixel

        self.geometry_count += 1
        self.geometry_data.append({
            'id': self.geometry_count,
            'type': 'rectangle',
            'width_px': width_px,
            'height_px': height_px,
            'width_um': width_um,
            'height_um': height_um,
            'area_um2': area_um,
            'perimeter_um': perimeter_um,
            'points': self.points.copy()
        })

        print(f"OK Rectangulo #{self.geometry_count}:")
        print(f"  Ancho: {width_um:.2f} um ({width_px:.1f} px)")
        print(f"  Alto: {height_um:.2f} um ({height_px:.1f} px)")
        print(f"  Area: {area_um:.2f} um^2")
        print(f"  Perimetro: {perimeter_um:.2f} um")

        self.points = []
        self._annotations_dirty = True
        self.update_display()

    def measure_triangle(self):
        """Mide un triángulo a partir de 3 vértices."""
        p1, p2, p3 = self.points[0], self.points[1], self.points[2]

        # Calcular lados
        side1_px = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        side2_px = np.sqrt((p3[0]-p2[0])**2 + (p3[1]-p2[1])**2)
        side3_px = np.sqrt((p1[0]-p3[0])**2 + (p1[1]-p3[1])**2)

        # Área usando fórmula de Herón
        s_px = (side1_px + side2_px + side3_px) / 2
        area_px = np.sqrt(s_px * (s_px - side1_px) * (s_px - side2_px) * (s_px - side3_px))
        perimeter_px = side1_px + side2_px + side3_px

        # Convertir a micrómetros
        side1_um = side1_px * self.scale_um_per_pixel
        side2_um = side2_px * self.scale_um_per_pixel
        side3_um = side3_px * self.scale_um_per_pixel
        area_um = area_px * (self.scale_um_per_pixel**2)
        perimeter_um = perimeter_px * self.scale_um_per_pixel

        self.geometry_count += 1
        self.geometry_data.append({
            'id': self.geometry_count,
            'type': 'triangle',
            'side1_um': side1_um,
            'side2_um': side2_um,
            'side3_um': side3_um,
            'area_um2': area_um,
            'perimeter_um': perimeter_um,
            'points': self.points.copy()
        })

        print(f"OK Triangulo #{self.geometry_count}:")
        print(f"  Lados: {side1_um:.2f}, {side2_um:.2f}, {side3_um:.2f} um")
        print(f"  Area: {area_um:.2f} um^2")
        print(f"  Perimetro: {perimeter_um:.2f} um")

        self.points = []
        self._annotations_dirty = True
        self.update_display()

    def measure_polygon(self):
        """Mide un polígono a partir de N vértices."""
        if len(self.points) < 3:
            print("ERROR: Se necesitan al menos 3 puntos para un poligono")
            return

        # Calcular perímetro
        perimeter_px = 0
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]
            perimeter_px += np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

        # Calcular área usando fórmula del área de polígono (Shoelace formula)
        area_px = 0
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]
            area_px += p1[0] * p2[1] - p2[0] * p1[1]
        area_px = abs(area_px) / 2

        # Convertir a micrómetros
        perimeter_um = perimeter_px * self.scale_um_per_pixel
        area_um = area_px * (self.scale_um_per_pixel**2)

        self.geometry_count += 1
        self.geometry_data.append({
            'id': self.geometry_count,
            'type': 'polygon',
            'num_sides': len(self.points),
            'area_um2': area_um,
            'perimeter_um': perimeter_um,
            'points': self.points.copy()
        })

        print(f"OK Poligono #{self.geometry_count}:")
        print(f"  Lados: {len(self.points)}")
        print(f"  Area: {area_um:.2f} um^2")
        print(f"  Perimetro: {perimeter_um:.2f} um")

        self.points = []
        self._annotations_dirty = True
        self.update_display()

    def update_scale(self):
        """
        Actualiza la escala global usando la mediana de todas las calibraciones.
        """
        if len(self.calibration_data) > 0:
            scales = [d['um_per_pixel'] for d in self.calibration_data]
            self.scale_um_per_pixel = np.median(scales)
            self.scale_std = np.std(scales)

    def display_statistics(self):
        """
        Muestra estadísticas de calibración en consola.
        """
        if len(self.calibration_data) == 0:
            return

        print("\n" + "="*60)
        print("ESTADÍSTICAS DE CALIBRACIÓN")
        print("="*60)
        print(f"Número de microesferas medidas: {len(self.calibration_data)}")
        print(f"Escala (mediana): {self.scale_um_per_pixel:.4f} umm/pixel")
        print(f"Desviación estándar: {self.scale_std:.4f} umm/pixel")
        print(f"Coeficiente de variación: {(self.scale_std/self.scale_um_per_pixel*100):.2f}%")
        print("="*60 + "\n")

    def save_results(self):
        """
        Guarda los resultados de calibración en un archivo CSV.
        """
        if len(self.calibration_data) == 0:
            print("AVISO: No hay datos de calibración para guardar")
            return

        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fpm_calibration_{timestamp}.csv"

        # Guardar CSV
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['id', 'center_x', 'center_y', 'border_x', 'border_y',
                         'radius_px', 'diameter_px', 'um_per_pixel']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for data in self.calibration_data:
                writer.writerow(data)

        # Guardar resumen
        summary_file = f"fpm_calibration_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("FPM CALIBRATION SUMMARY\n")
            f.write("="*60 + "\n\n")
            f.write(f"Imagen analizada: {self.image_path}\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Número de mediciones: {len(self.calibration_data)}\n")
            f.write(f"Dimensión de patrón de referencia: {self.calibration_pattern_size_um} umm (Tipo: {self.calibration_pattern_type})\n\n")
            f.write(f"ESCALA CALCULADA:\n")
            f.write(f"  Mediana: {self.scale_um_per_pixel:.4f} umm/pixel\n")
            f.write(f"  Desv. estándar: {self.scale_std:.4f} umm/pixel\n")
            f.write(f"  Coef. variación: {(self.scale_std/self.scale_um_per_pixel*100):.2f}%\n\n")

            f.write("MEDICIONES INDIVIDUALES:\n")
            for data in self.calibration_data:
                f.write(f"  #{data['id']}: {data['diameter_px']:.2f} px -> {data['um_per_pixel']:.4f} umm/px\n")

        print(f"OK Resultados guardados:")
        print(f"  - {filename}")
        print(f"  - {summary_file}")

    def _rebuild_annotation_layer(self):
        """
        Reconstruye la capa base con todas las anotaciones PERMANENTES.
        Solo se llama cuando _annotations_dirty == True.
        Si CLAHE está activo usa la imagen de contraste realzado como fondo.
        """
        if self.false_color_active and self._false_color_image is not None:
            source = self._false_color_image
        elif self.clahe_active and self._clahe_image is not None:
            source = self._clahe_image
        else:
            source = self.original_image
        base_img = source.copy()

        # Calibraciones guardadas — renderizado mejorado para imágenes de microscopía
        for data in self.calibration_data:
            center = (int(round(data['center_x'])), int(round(data['center_y'])))
            radius = int(round(data['radius_px']))

            # 1) Relleno semi-transparente (overlay amarillo-naranja suave)
            overlay = base_img.copy()
            cv2.circle(overlay, center, radius, (0, 180, 255), -1)
            cv2.addWeighted(overlay, 0.12, base_img, 0.88, 0, base_img)

            # 2) Halo oscuro exterior (contrasta con cualquier fondo)
            cv2.circle(base_img, center, radius, (0, 0, 0), 5)

            # 3) Círculo de color encima del halo
            cv2.circle(base_img, center, radius, (0, 230, 255), 2)

            # 4) Crosshair en el centro (más visible que solo un puntito)
            cs = max(8, radius // 4)  # tamaño de la cruz proporcional al radio
            cv2.line(base_img, (center[0] - cs, center[1]), (center[0] + cs, center[1]), (0, 0, 0), 3)
            cv2.line(base_img, (center[0], center[1] - cs), (center[0], center[1] + cs), (0, 0, 0), 3)
            cv2.line(base_img, (center[0] - cs, center[1]), (center[0] + cs, center[1]), (0, 230, 255), 1)
            cv2.line(base_img, (center[0], center[1] - cs), (center[0], center[1] + cs), (0, 230, 255), 1)

            # 5) Etiqueta con sombra para legibilidad
            label = f"#{data['id']}"
            tx, ty = center[0] - 18, center[1] - radius - 10
            cv2.putText(base_img, label, (tx + 2, ty + 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)   # sombra
            cv2.putText(base_img, label, (tx, ty),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 230, 255), 2)  # texto

        # Mediciones guardadas
        for data in self.measurement_data:
            p1 = (int(round(data['p1_x'])), int(round(data['p1_y'])))
            p2 = (int(round(data['p2_x'])), int(round(data['p2_y'])))
            cv2.line(base_img, p1, p2, (255, 0, 255), 3)
            cv2.circle(base_img, p1, 5, self.point_color, -1)
            cv2.circle(base_img, p2, 5, self.point_color, -1)
            mid_point = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            text = f"M{data['id']}: {data['distance_um']:.2f}um ({data['distance_px']:.1f}px)"
            cv2.putText(base_img, text, (mid_point[0] + 10, mid_point[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)

        # Geometrías guardadas
        for data in self.geometry_data:
            if data['type'] == 'circle':
                center = (int(data['center_x']), int(data['center_y']))
                radius = int(data['radius_px'])
                cv2.circle(base_img, center, radius, (0, 255, 255), 2)
                cv2.circle(base_img, center, 5, self.point_color, -1)
                text = f"C{data['id']}: R={data['radius_um']:.1f}um A={data['area_um2']:.1f}um2"
                cv2.putText(base_img, text, (center[0] + 10, center[1] - radius - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            elif data['type'] == 'rectangle':
                pts = np.array(data['points'], np.int32)
                x_min, x_max = min(pts[:, 0]), max(pts[:, 0])
                y_min, y_max = min(pts[:, 1]), max(pts[:, 1])
                cv2.rectangle(base_img, (x_min, y_min), (x_max, y_max), (255, 255, 0), 2)
                text = f"R{data['id']}: {data['width_um']:.1f}x{data['height_um']:.1f}um A={data['area_um2']:.1f}um2"
                cv2.putText(base_img, text, (x_min, y_min - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            elif data['type'] in ['triangle', 'polygon']:
                pts = np.array(data['points'], np.int32).reshape((-1, 1, 2))
                cv2.polylines(base_img, [pts], True, (255, 128, 0), 2)
                for pt in data['points']:
                    cv2.circle(base_img, pt, 5, self.point_color, -1)
                centroid_x = int(np.mean([p[0] for p in data['points']]))
                centroid_y = int(np.mean([p[1] for p in data['points']]))
                if data['type'] == 'triangle':
                    text = f"T{data['id']}: A={data['area_um2']:.1f}um2"
                else:
                    text = f"P{data['id']}: {data['num_sides']} lados A={data['area_um2']:.1f}um2"
                cv2.putText(base_img, text, (centroid_x + 10, centroid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 128, 0), 2)

        self._annotated_base = base_img

    def _draw_temp_points(self, img):
        """
        Fase 1 — dibuja en coordenadas de IMAGEN los elementos que deben
        escalar con el zoom porque representan distancias reales:
          · círculo rubber-band de calibración
          · línea viva de medición / línea definitiva
          · polilínea de geometría
        Los elementos decorativos de tamaño fijo (crosshair, etiquetas,
        marcadores de punto) se dibujan en _draw_screen_overlays().
        Las coords en self.points son flotantes (sub-pixel); se convierten
        a int solo para las llamadas cv2.
        """
        mp = self._mouse_pos
        # Convierte tupla float a int para cv2
        ip = lambda p: (int(p[0]), int(p[1]))

        for i, point in enumerate(self.points):

            if self.mode == 'calibration' and i == 0:
                # Círculo rubber-band: su radio ES la distancia medida → escala con zoom
                if mp is not None:
                    r = int(np.hypot(mp[0] - point[0], mp[1] - point[1]))
                    if r > 0:
                        cv2.circle(img, ip(point), r, (0, 0, 0), 4)
                        cv2.circle(img, ip(point), r, (0, 230, 255), 2)

            elif self.mode == 'measurement' and i == 0:
                if len(self.points) == 2:
                    cv2.line(img, ip(self.points[0]), ip(self.points[1]), self.circle_color, 3)
                elif mp is not None:
                    cv2.line(img, ip(point), ip(mp), (0, 0, 0), 4)
                    cv2.line(img, ip(point), ip(mp), self.circle_color, 2)

            elif self.mode == 'geometry' and len(self.points) > 1:
                pts = np.array(self.points, np.int32).reshape((-1, 1, 2))
                cv2.polylines(img, [pts], False, (0, 200, 200), 2)

    def _draw_screen_overlays(self, display_img):
        """
        Fase 2 — dibuja elementos decorativos directamente en coordenadas de
        PANTALLA, sobre display_image, con tamaño FIJO en píxeles de pantalla.
        Así no se amplifican con el zoom: a x60 el crosshair sigue siendo
        ~15px, no 900px.
        """
        if not self.points:
            return

        mp = self._mouse_pos
        CROSS = 15   # brazos del crosshair en píxeles de pantalla
        DOT   = 6    # radio de marcador de punto en píxeles de pantalla

        for i, point in enumerate(self.points):
            sx, sy = self.image_to_screen_coords(point[0], point[1])

            # ── Calibración ────────────────────────────────────────────────
            if self.mode == 'calibration' and i == 0:
                # Crosshair de tamaño fijo en el centro marcado
                cv2.line(display_img, (sx-CROSS, sy), (sx+CROSS, sy), (0, 0, 0), 3)
                cv2.line(display_img, (sx, sy-CROSS), (sx, sy+CROSS), (0, 0, 0), 3)
                cv2.line(display_img, (sx-CROSS, sy), (sx+CROSS, sy), (0, 230, 255), 1)
                cv2.line(display_img, (sx, sy-CROSS), (sx, sy+CROSS), (0, 230, 255), 1)
                cv2.putText(display_img, "Centro", (sx+17, sy-17),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 3)
                cv2.putText(display_img, "Centro", (sx+15, sy-15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.75, self.text_color, 2)
                # Etiqueta de diámetro junto al cursor (en pantalla)
                if mp is not None:
                    mx_s, my_s = self.image_to_screen_coords(mp[0], mp[1])
                    r_img = np.hypot(mp[0] - point[0], mp[1] - point[1])
                    d_px = 2 * r_img
                    if self.scale_um_per_pixel:
                        lbl = f"D = {d_px * self.scale_um_per_pixel:.3f} um  ({d_px:.0f} px)"
                    else:
                        lbl = f"r = {r_img:.0f} px   D = {d_px:.0f} px"
                    cv2.putText(display_img, lbl, (mx_s+17, my_s-17),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 3)
                    cv2.putText(display_img, lbl, (mx_s+15, my_s-15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 230, 255), 2)

            # ── Medición ───────────────────────────────────────────────────
            elif self.mode == 'measurement':
                cv2.circle(display_img, (sx, sy), DOT, self.point_color, -1)
                if i == 0 and len(self.points) == 1 and mp is not None:
                    mx_s, my_s = self.image_to_screen_coords(mp[0], mp[1])
                    d_px = np.hypot(mp[0] - point[0], mp[1] - point[1])
                    if self.scale_um_per_pixel:
                        lbl = f"{d_px * self.scale_um_per_pixel:.3f} um  ({d_px:.1f} px)"
                    else:
                        lbl = f"{d_px:.1f} px"
                    cv2.putText(display_img, lbl, (mx_s+12, my_s-12),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 3)
                    cv2.putText(display_img, lbl, (mx_s+10, my_s-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)

            # ── Geometría ──────────────────────────────────────────────────
            elif self.mode == 'geometry':
                cv2.circle(display_img, (sx, sy), DOT, (0, 255, 255), -1)
                cv2.putText(display_img, str(i+1), (sx+10, sy-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    def _build_panel(self, width):
        """Construye el panel de información superior con estado contextual."""
        panel = np.full((self.panel_height, width, 3), 40, dtype=np.uint8)

        # --- Fila 1: título | escala | zoom ---
        cv2.putText(panel, "FPM CALIBRATION TOOL", (20, 32),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        zoom_text = f"Zoom: {self.zoom_level:.2f}x"
        cv2.putText(panel, zoom_text, (width - 175, 32),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 220, 0), 2)

        if self.scale_um_per_pixel:
            if len(self.calibration_data) > 0:
                scale_text = f"Escala: {self.scale_um_per_pixel:.4f} um/px  (n={len(self.calibration_data)})"
            else:
                scale_text = f"Escala: {self.scale_um_per_pixel:.4f} um/px  [MANUAL]"
            cv2.putText(panel, scale_text, (width - 490, 32),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 210, 255), 2)

        # --- Fila 2: medición ---
        k_flag = f" [{self.sensor_pixel_um}um x{self.upscale_factor}]" if self.upscale_factor != 1.0 else ""
        cv2.putText(panel,
            f"[c]Calibrar  [e]Escala  [k]Sensor{k_flag}  [m]Medir  [g]Geometria  [r]Reset  [s]Guardar  [q]Salir",
            (20, 63), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (210, 210, 210), 1)

        # --- Fila 3: navegación y visualización ---
        clahe_flag = "*" if self.clahe_active else ""
        fc_flag    = "*" if self.false_color_active else ""
        hough_flag = f"({len(self._candidates)})" if self._candidates else ""
        lum_flag   = "(sel)" if self.lum_selecting else ("(roi)" if self.lum_region else "")
        ls_flag    = f"({len(self.linescan_points)}/2)" if self.linescan_active else ""
        cv2.putText(panel,
            f"[+/-/Rueda]Zoom  [BtnDer]Pan  [v]ROI  [n]CLAHE{clahe_flag}  [f]FalsoColor{fc_flag}"
            f"  [i]Histograma{lum_flag}  [p]LineScan{ls_flag}  [h]Hough{hough_flag}  DblClick=Zoom",
            (20, 93), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (210, 210, 210), 1)

        # --- Fila 4: estado contextual del modo activo ---
        y_mode = 130
        if self.mode == 'calibration':
            hints = ["  -> Click en el CENTRO de la microesfera",
                     "  -> Click en el BORDE de la microesfera"]
            hint = hints[len(self.points)] if len(self.points) < 2 else ""
            mode_text = f"MODO: CALIBRACION   esferas={len(self.calibration_data)}{hint}"
            cv2.putText(panel, mode_text, (20, y_mode),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 255, 80), 2)
        elif self.mode == 'measurement':
            hints = ["  -> Click en punto 1", "  -> Click en punto 2"]
            hint = hints[len(self.points)] if len(self.points) < 2 else ""
            mode_text = f"MODO: MEDICION   mediciones={len(self.measurement_data)}{hint}"
            cv2.putText(panel, mode_text, (20, y_mode),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 255, 80), 2)
        elif self.mode == 'geometry':
            if self.geometry_mode:
                reqs = {'circle': 3, 'rectangle': 2, 'triangle': 3, 'polygon': None}
                req = reqs.get(self.geometry_mode)
                if req:
                    prog = f"  ({len(self.points)}/{req} puntos)"
                else:
                    prog = f"  ({len(self.points)} puntos — Enter para finalizar)"
                mode_text = f"MODO: GEOMETRIA - {self.geometry_mode.upper()}{prog}"
            else:
                mode_text = "MODO: GEOMETRIA   -> Selecciona: [1]Circulo [2]Rectangulo [3]Triangulo [4]Poligono"
            cv2.putText(panel, mode_text, (20, y_mode),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 255, 80), 2)
        else:
            cv2.putText(panel, "Sin modo activo  ->  Presiona una tecla para comenzar",
                       (20, y_mode), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (130, 130, 130), 1)

        # --- Fila 5: estado ROI / luminancia ---
        y_roi = 168
        if self.roi_selecting:
            cv2.putText(panel, "ROI: clic + arrastra para seleccionar  |  v=cancelar",
                       (20, y_roi), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 128), 2)
        elif self.roi_region is not None:
            rx1, ry1, rx2, ry2 = self.roi_region
            roi_text = (f"ROI activa: {rx2-rx1}x{ry2-ry1}px  ({rx1},{ry1})-({rx2},{ry2})"
                        f"  |  v=nueva ROI  |  Esc=borrar")
            cv2.putText(panel, roi_text, (20, y_roi),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 128), 2)

        # --- Fila 6: estado lum / linescan activos ---
        y_lum = 200
        if self.lum_selecting:
            cv2.putText(panel, "HISTOGRAMA: arrastra rectangulo en la imagen  |  [i]=cancelar",
                       (20, y_lum), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 180, 0), 2)
        elif self.linescan_active:
            pts_txt = "click PUNTO 1" if len(self.linescan_points) == 0 else "click PUNTO 2"
            cv2.putText(panel, f"LINE SCAN: {pts_txt} en la imagen  |  [p]=cancelar",
                       (20, y_lum), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 200, 255), 2)

        # --- Fila 7: resumen de conteos ---
        y_sum = self.panel_height - 14
        summary = (f"Calibraciones: {len(self.calibration_data)}   "
                   f"Mediciones: {len(self.measurement_data)}   "
                   f"Geometrias: {len(self.geometry_data)}")
        cv2.putText(panel, summary, (20, y_sum),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)

        # Línea separadora inferior del panel
        cv2.line(panel, (0, self.panel_height - 1), (width, self.panel_height - 1), (70, 70, 70), 2)

        return panel

    def update_display(self):
        """
        Actualiza la visualización con zoom, anotaciones y panel de información.

        Optimización ROI: si hay una región de interés activa, recortamos
        _annotated_base a ese rectángulo ANTES de escalar.  A zoom x60 sobre
        una imagen 1000x1000, sin ROI hay que crear una imagen 60000x60000;
        con un ROI de 100x100 solo se crea una de 6000x6000 — 100× más rápido.
        Las coordenadas de calibración no se alteran porque screen_to_image_coords
        y image_to_screen_coords compensan el offset del ROI.
        """
        # Reconstruir capa de anotaciones solo si cambió algo permanente
        if self._annotated_base is None or self._annotations_dirty:
            self._rebuild_annotation_layer()
            self._annotations_dirty = False

        # Si hay puntos temporales, dibujarlos sobre una copia; si no, usar directo el caché
        if self.points:
            base_img = self._annotated_base.copy()
            self._draw_temp_points(base_img)
        else:
            base_img = self._annotated_base

        # ── ROI: recortar ANTES de escalar ────────────────────────────────────
        if self.roi_region is not None:
            rx1, ry1, rx2, ry2 = self.roi_region
            H, W = base_img.shape[:2]
            rx1 = int(max(0, rx1)); ry1 = int(max(0, ry1))
            rx2 = int(min(W, rx2)); ry2 = int(min(H, ry2))
            if rx2 > rx1 and ry2 > ry1:
                base_img = base_img[ry1:ry2, rx1:rx2]

        # Aplicar zoom (ahora sobre la imagen recortada, mucho más pequeña)
        h, w = base_img.shape[:2]
        new_w = max(1, int(w * self.zoom_level))
        new_h = max(1, int(h * self.zoom_level))
        if self.zoom_level != 1.0:
            interp = cv2.INTER_NEAREST if self.zoom_level > 4.0 else cv2.INTER_LINEAR
            zoomed_img = cv2.resize(base_img, (new_w, new_h), interpolation=interp)
        else:
            zoomed_img = base_img

        # Región visible (viewport del tamaño de la imagen original)
        output_h, output_w = self.original_image.shape[:2]
        visible_region = np.full((output_h, output_w, 3), 20, dtype=np.uint8)

        src_x = max(0, -self.pan_offset[0])
        src_y = max(0, -self.pan_offset[1])
        src_x_end = min(new_w, src_x + output_w)
        src_y_end = min(new_h, src_y + output_h)
        dst_x = max(0, self.pan_offset[0])
        dst_y = max(0, self.pan_offset[1])
        dst_x_end = dst_x + (src_x_end - src_x)
        dst_y_end = dst_y + (src_y_end - src_y)

        if src_x < new_w and src_y < new_h and dst_x < output_w and dst_y < output_h:
            visible_region[dst_y:dst_y_end, dst_x:dst_x_end] = zoomed_img[src_y:src_y_end, src_x:src_x_end]

        # Panel de información contextual
        panel = self._build_panel(visible_region.shape[1])

        # Combinar panel + imagen
        self.display_image = np.vstack([panel, visible_region])

        # Fase 2: elementos decorativos en coordenadas de pantalla (tamaño fijo)
        if self.points:
            self._draw_screen_overlays(self.display_image)

        # ── Overlay ROI de luminancia (rectángulo en curso o confirmado) ─────
        if self.lum_selecting and self.lum_start_img is not None and self.lum_preview_end is not None:
            s_sx, s_sy = self.image_to_screen_coords(self.lum_start_img[0], self.lum_start_img[1])
            ex, ey = self.lum_preview_end
            cv2.rectangle(self.display_image, (s_sx, s_sy), (ex, ey), (0, 0, 0), 3)
            cv2.rectangle(self.display_image, (s_sx, s_sy), (ex, ey), (255, 180, 0), 2)
        elif self.lum_region is not None:
            lx1, ly1, lx2, ly2 = self.lum_region
            s1x, s1y = self.image_to_screen_coords(lx1, ly1)
            s2x, s2y = self.image_to_screen_coords(lx2, ly2)
            cv2.rectangle(self.display_image, (s1x, s1y), (s2x, s2y), (0, 0, 0), 3)
            cv2.rectangle(self.display_image, (s1x, s1y), (s2x, s2y), (255, 180, 0), 2)
            cv2.putText(self.display_image, "HIST", (s1x + 4, s1y + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 180, 0), 1)

        # ── Overlay line scan (línea definida o en construcción) ─────────────
        mp = self._mouse_pos
        if self.linescan_active:
            if len(self.linescan_points) == 1 and mp is not None:
                sp1x, sp1y = self.image_to_screen_coords(*self.linescan_points[0])
                mpx, mpy = self.image_to_screen_coords(mp[0], mp[1])
                cv2.line(self.display_image, (sp1x, sp1y), (mpx, mpy), (0, 0, 0), 3)
                cv2.line(self.display_image, (sp1x, sp1y), (mpx, mpy), (0, 200, 255), 2)
                cv2.circle(self.display_image, (sp1x, sp1y), 5, (0, 200, 255), -1)
                d_px = np.hypot(mp[0] - self.linescan_points[0][0],
                                mp[1] - self.linescan_points[0][1])
                lbl = (f"{d_px*self.scale_um_per_pixel:.2f}µm ({d_px:.1f}px)"
                       if self.scale_um_per_pixel else f"{d_px:.1f}px")
                cv2.putText(self.display_image, lbl, (mpx+10, mpy-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3)
                cv2.putText(self.display_image, lbl, (mpx+8, mpy-12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)

        # Candidatos HoughCircles (encima de anotaciones, bajo el rectángulo ROI)
        if self._candidates:
            out_h, out_w = self.original_image.shape[:2]
            for cx, cy, cr in self._candidates:
                sx, sy = self.image_to_screen_coords(cx, cy)
                sr = max(1, int(cr * self.zoom_level))
                # Descartar si está completamente fuera de la pantalla
                if sx + sr < 0 or sx - sr > out_w or sy + sr < self.panel_height or sy - sr > out_h + self.panel_height:
                    continue
                cv2.circle(self.display_image, (sx, sy), sr, (0, 0, 0), 3)
                cv2.circle(self.display_image, (sx, sy), sr, (0, 255, 255), 1)
                cv2.circle(self.display_image, (sx, sy), 3, (0, 255, 255), -1)

        # Dibujar rectángulo de selección ROI en curso (encima de todo)
        if self.roi_selecting and self.roi_start_img is not None and self.roi_preview_end is not None:
            s_sx, s_sy = self.image_to_screen_coords(self.roi_start_img[0], self.roi_start_img[1])
            ex, ey = self.roi_preview_end
            cv2.rectangle(self.display_image, (s_sx, s_sy), (ex, ey), (0, 0, 0), 3)
            cv2.rectangle(self.display_image, (s_sx, s_sy), (ex, ey), (0, 255, 128), 2)

    # ══════════════════════════════════════════════════════════════════════════
    #  ANÁLISIS DE LUMINANCIA
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _fig_to_cv2(fig):
        """
        Renderiza una figura matplotlib a imagen BGR para cv2.imshow.
        Usa backend Agg (sin Tkinter) para evitar conflictos de GIL con OpenCV.
        """
        import matplotlib
        matplotlib.use('Agg')
        fig.canvas.draw()
        buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        w, h = fig.canvas.get_width_height()
        img_rgba = buf.reshape(h, w, 4)
        import matplotlib.pyplot as plt
        plt.close(fig)
        return cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)

    def show_luminance_histogram(self, region=None):
        """
        Muestra histograma de luminancia/intensidad con matplotlib.
        region: (x1,y1,x2,y2) en coords imagen. None = imagen completa.
        Muestra:
          · Histograma RGB superpuesto + canal Y (luminancia)
          · Estadísticas: media, mediana, std, min/max, P5-P95, SNR, contraste
          · Curva acumulada (CDF) normalizada
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.gridspec as gridspec
        except ImportError:
            print("\nERROR: matplotlib no está instalado. Ejecuta: pip install matplotlib")
            return

        img = self.original_image
        label = "Imagen completa"
        if region is not None:
            x1, y1, x2, y2 = [int(round(v)) for v in region]
            H, W = img.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            if x2 <= x1 or y2 <= y1:
                print("\nRegión inválida para histograma")
                return
            img = img[y1:y2, x1:x2]
            label = f"ROI ({x2-x1}×{y2-y1} px) @ ({x1},{y1})"

        # Luminancia Y (perceptual)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        b, g, r = cv2.split(img.astype(np.float32))

        def _stats(ch):
            flat = ch.flatten()
            return {
                'mean':   float(np.mean(flat)),
                'median': float(np.median(flat)),
                'std':    float(np.std(flat)),
                'min':    float(np.min(flat)),
                'max':    float(np.max(flat)),
                'p5':     float(np.percentile(flat, 5)),
                'p95':    float(np.percentile(flat, 95)),
            }

        st_y = _stats(gray)
        st_r = _stats(r)
        st_g = _stats(g)
        st_b = _stats(b)

        snr  = st_y['mean'] / st_y['std'] if st_y['std'] > 0 else float('inf')
        cont = (st_y['max'] - st_y['min']) / (st_y['max'] + st_y['min'] + 1e-6)
        dyn  = st_y['p95'] - st_y['p5']   # rango dinámico efectivo (P5-P95)

        fig = plt.figure(figsize=(13, 7), facecolor='#1e1e1e')
        fig.suptitle(f"Análisis de luminancia — {label}", color='white', fontsize=12)

        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.32)
        ax_hist  = fig.add_subplot(gs[0, :])   # histograma ancho
        ax_cdf   = fig.add_subplot(gs[1, 0])   # CDF acumulada
        ax_stats = fig.add_subplot(gs[1, 1])   # tabla estadísticas

        for ax in (ax_hist, ax_cdf, ax_stats):
            ax.set_facecolor('#2b2b2b')
            for sp in ax.spines.values():
                sp.set_color('#555')
            ax.tick_params(colors='#ccc', labelsize=8)
            ax.xaxis.label.set_color('#ccc')
            ax.yaxis.label.set_color('#ccc')
            ax.title.set_color('#ddd')

        bins = 256
        # Histogramas
        for ch, col, lbl in [(gray, 'white', 'Y lum'), (r, '#ff5555', 'R'),
                              (g, '#55ff55', 'G'), (b, '#5599ff', 'B')]:
            hist, edges = np.histogram(ch.flatten(), bins=bins, range=(0, 255))
            cx = (edges[:-1] + edges[1:]) / 2
            alpha = 0.85 if lbl == 'Y lum' else 0.45
            lw    = 2.0   if lbl == 'Y lum' else 1.0
            ax_hist.plot(cx, hist, color=col, alpha=alpha, linewidth=lw, label=lbl)

        ax_hist.axvline(st_y['mean'],   color='yellow',  ls='--', lw=1.2, label=f"Media {st_y['mean']:.1f}")
        ax_hist.axvline(st_y['median'], color='orange',  ls=':',  lw=1.2, label=f"Mediana {st_y['median']:.1f}")
        ax_hist.axvline(st_y['p5'],     color='#aaa',    ls=':',  lw=0.8, label=f"P5={st_y['p5']:.0f}")
        ax_hist.axvline(st_y['p95'],    color='#aaa',    ls=':',  lw=0.8, label=f"P95={st_y['p95']:.0f}")
        ax_hist.set_xlim(0, 255)
        ax_hist.set_xlabel("Intensidad (0-255)")
        ax_hist.set_ylabel("Frecuencia")
        ax_hist.set_title("Histograma de intensidad")
        ax_hist.legend(fontsize=7.5, labelcolor='white',
                       facecolor='#333', edgecolor='#555', ncol=4)

        # CDF
        hist_y, _ = np.histogram(gray.flatten(), bins=bins, range=(0, 255))
        cdf = np.cumsum(hist_y).astype(float)
        cdf /= cdf[-1]
        cx  = np.linspace(0, 255, bins)
        ax_cdf.plot(cx, cdf, color='white', linewidth=1.5)
        ax_cdf.fill_between(cx, cdf, alpha=0.15, color='white')
        ax_cdf.axvline(st_y['p5'],  color='#aaa', ls=':', lw=0.8)
        ax_cdf.axvline(st_y['p95'], color='#aaa', ls=':', lw=0.8)
        ax_cdf.set_xlim(0, 255); ax_cdf.set_ylim(0, 1)
        ax_cdf.set_xlabel("Intensidad"); ax_cdf.set_ylabel("CDF")
        ax_cdf.set_title("Distribución acumulada (CDF)")

        # Tabla estadísticas
        ax_stats.axis('off')
        rows = [
            ("", "Y lum", "R", "G", "B"),
            ("Media",    f"{st_y['mean']:.1f}",   f"{st_r['mean']:.1f}",
                         f"{st_g['mean']:.1f}",   f"{st_b['mean']:.1f}"),
            ("Mediana",  f"{st_y['median']:.1f}", f"{st_r['median']:.1f}",
                         f"{st_g['median']:.1f}", f"{st_b['median']:.1f}"),
            ("Std",      f"{st_y['std']:.1f}",    f"{st_r['std']:.1f}",
                         f"{st_g['std']:.1f}",    f"{st_b['std']:.1f}"),
            ("Min",      f"{st_y['min']:.0f}",    f"{st_r['min']:.0f}",
                         f"{st_g['min']:.0f}",    f"{st_b['min']:.0f}"),
            ("Max",      f"{st_y['max']:.0f}",    f"{st_r['max']:.0f}",
                         f"{st_g['max']:.0f}",    f"{st_b['max']:.0f}"),
            ("P5",       f"{st_y['p5']:.0f}",     f"{st_r['p5']:.0f}",
                         f"{st_g['p5']:.0f}",     f"{st_b['p5']:.0f}"),
            ("P95",      f"{st_y['p95']:.0f}",    f"{st_r['p95']:.0f}",
                         f"{st_g['p95']:.0f}",    f"{st_b['p95']:.0f}"),
            ("SNR",      f"{snr:.2f}",  "—", "—", "—"),
            ("Contraste",f"{cont:.3f}", "—", "—", "—"),
            ("D.Dinámica",f"{dyn:.0f}","—", "—", "—"),
        ]
        col_colors = [['#2b2b2b']*5] + [
            ['#1e1e1e' if i%2==0 else '#272727']*5 for i in range(len(rows)-1)
        ]
        tbl = ax_stats.table(
            cellText=[list(r) for r in rows],
            cellLoc='center', loc='center',
            cellColours=col_colors
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        for (_, ci), cell in tbl.get_celld().items():
            cell.set_edgecolor('#444')
            cell.set_text_props(color='white' if ci > 0 else '#aaa')
        ax_stats.set_title("Estadísticas por canal")

        print(f"\n--- Luminancia {label} ---")
        print(f"  Y  media={st_y['mean']:.1f}  std={st_y['std']:.1f}  "
              f"SNR={snr:.2f}  contraste={cont:.3f}  D.Din={dyn:.0f}")
        print(f"  R  media={st_r['mean']:.1f}  G={st_g['mean']:.1f}  B={st_b['mean']:.1f}")

        cv_img = self._fig_to_cv2(fig)
        cv2.imshow("Histograma de luminancia", cv_img)

    def show_linescan(self, p1, p2):
        """
        Muestra el perfil de intensidad a lo largo de la línea p1→p2.
        p1, p2: coordenadas flotantes en imagen original.
        Extrae pixels con interpolación bilineal a lo largo de la línea.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            print("\nERROR: matplotlib no instalado")
            return

        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])
        length_px = np.hypot(x2 - x1, y2 - y1)
        if length_px < 1:
            print("\nLínea demasiado corta"); return

        n_samples = max(2, int(length_px * 2))  # sobremuestreo x2
        xs = np.linspace(x1, x2, n_samples)
        ys = np.linspace(y1, y2, n_samples)

        img_f = self.original_image.astype(np.float32)
        H, W = img_f.shape[:2]

        # Interpolación bilineal manual (evita dependencia de scipy)
        xi = np.clip(xs, 0, W - 1.001)
        yi = np.clip(ys, 0, H - 1.001)
        x0, y0 = xi.astype(int), yi.astype(int)
        x1i, y1i = np.minimum(x0 + 1, W - 1), np.minimum(y0 + 1, H - 1)
        fx, fy = xi - x0, yi - y0

        def _interp_ch(ch):
            return (ch[y0, x0]*(1-fx)*(1-fy) + ch[y0, x1i]*fx*(1-fy) +
                    ch[y1i, x0]*(1-fx)*fy    + ch[y1i, x1i]*fx*fy)

        b_ch = _interp_ch(img_f[:, :, 0])
        g_ch = _interp_ch(img_f[:, :, 1])
        r_ch = _interp_ch(img_f[:, :, 2])
        y_ch = 0.299*r_ch + 0.587*g_ch + 0.114*b_ch  # luminancia

        # Eje X en µm si hay escala
        if self.scale_um_per_pixel:
            step = length_px / (n_samples - 1) * self.scale_um_per_pixel
            xaxis = np.arange(n_samples) * step
            xlabel = "Distancia (µm)"
        else:
            xaxis = np.linspace(0, length_px, n_samples)
            xlabel = "Distancia (px)"

        fig, axes = plt.subplots(2, 1, figsize=(10, 6), facecolor='#1e1e1e',
                                 gridspec_kw={'height_ratios': [1, 2]})
        fig.suptitle(f"Perfil de intensidad  |  longitud={length_px:.1f}px"
                     + (f" = {length_px*self.scale_um_per_pixel:.2f}µm" if self.scale_um_per_pixel else ""),
                     color='white', fontsize=11)

        # Miniatura con la línea marcada
        ax_img = axes[0]
        ax_img.set_facecolor('#2b2b2b')
        margin = 40
        lx1 = max(0, int(min(x1, x2)) - margin)
        ly1 = max(0, int(min(y1, y2)) - margin)
        lx2 = min(W, int(max(x1, x2)) + margin)
        ly2 = min(H, int(max(y1, y2)) + margin)
        thumb = cv2.cvtColor(self.original_image[ly1:ly2, lx1:lx2], cv2.COLOR_BGR2RGB)
        ax_img.imshow(thumb, aspect='auto', cmap=None)
        ax_img.plot([x1-lx1, x2-lx1], [y1-ly1, y2-ly1],
                    color='yellow', linewidth=1.5, marker='o', markersize=4)
        ax_img.set_title("Región analizada", color='#ccc', fontsize=8)
        ax_img.axis('off')

        # Perfil
        ax_p = axes[1]
        ax_p.set_facecolor('#2b2b2b')
        for sp in ax_p.spines.values(): sp.set_color('#555')
        ax_p.tick_params(colors='#ccc', labelsize=8)
        ax_p.plot(xaxis, y_ch, color='white',    lw=1.8, label='Y (lum)')
        ax_p.plot(xaxis, r_ch, color='#ff5555',  lw=1.0, alpha=0.7, label='R')
        ax_p.plot(xaxis, g_ch, color='#55ff55',  lw=1.0, alpha=0.7, label='G')
        ax_p.plot(xaxis, b_ch, color='#5599ff',  lw=1.0, alpha=0.7, label='B')
        ax_p.axhline(np.mean(y_ch), color='yellow', ls='--', lw=1.0,
                     label=f"Media Y={np.mean(y_ch):.1f}")
        ax_p.set_xlabel(xlabel, color='#ccc')
        ax_p.set_ylabel("Intensidad (0-255)", color='#ccc')
        ax_p.set_title("Perfil de intensidad a lo largo de la línea", color='#ddd')
        ax_p.legend(fontsize=8, labelcolor='white', facecolor='#333', edgecolor='#555')
        ax_p.set_ylim(0, 260)

        plt.tight_layout()
        cv_img = self._fig_to_cv2(fig)
        cv2.imshow("Perfil de intensidad", cv_img)

        print(f"\n--- Line scan ({x1:.1f},{y1:.1f}) -> ({x2:.1f},{y2:.1f}) ---")
        print(f"  Longitud: {length_px:.1f} px" +
              (f" = {length_px*self.scale_um_per_pixel:.2f} µm" if self.scale_um_per_pixel else ""))
        print(f"  Y  media={np.mean(y_ch):.1f}  min={np.min(y_ch):.1f}  max={np.max(y_ch):.1f}")

    def _run_hough_detection(self):
        """
        Detecta automáticamente candidatos circulares del tamaño de las microesferas
        usando HoughCircles con CLAHE previo para mejor contraste.
        Almacena los candidatos en self._candidates como lista de (cx, cy, r).
        """
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        # CLAHE mejora la detección en imágenes de microscopía de bajo contraste
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Rango de radios esperado según escala calibrada
        if self.scale_um_per_pixel and self.scale_um_per_pixel > 0:
            if self.calibration_pattern_type == 'sphere':
                expected_r = (self.calibration_pattern_size_um / 2.0) / self.scale_um_per_pixel
            else:
                expected_r = (2.0 / 2.0) / self.scale_um_per_pixel
            min_r = max(1, int(expected_r * 0.5))
            max_r = max(min_r + 2, int(expected_r * 2.5))
        else:
            min_r, max_r = 1, 20  # búsqueda amplia si no hay escala

        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1,
            minDist=max(3, min_r * 2),
            param1=50, param2=12,
            minRadius=min_r, maxRadius=max_r
        )

        if circles is not None:
            self._candidates = [(float(c[0]), float(c[1]), float(c[2]))
                                 for c in circles[0]]
            print(f"\nHough: {len(self._candidates)} candidatos (radio {min_r}-{max_r} px)")
            print("  Candidatos en amarillo — entra en modo [c] y haz click en el centro")
        else:
            self._candidates = []
            print(f"\nHough: ningún candidato encontrado (radio {min_r}-{max_r} px)")
            print("  Prueba [n] para activar contraste CLAHE y volver a intentarlo")

    def set_calibration_pattern(self):
        """
        Diálogo para seleccionar el patrón de calibración (línea o esfera) y su tamaño.
        """
        from tkinter import simpledialog

        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        ans = simpledialog.askstring(
            "Patrón de Calibración",
            "Selecciona el patrón:\n"
            "1. Regleta 1 mm (1000 um)\n"
            "2. Regleta 0.3 mm (300 um)\n"
            "3. Regleta 0.076 mm (76 um)\n"
            "4. Microesfera (2 um)\n"
            "5. Otro valor lineal...",
            initialvalue="1"
        )

        if ans == '1':
            self.calibration_pattern_type = 'line'
            self.calibration_pattern_size_um = 1000.0
        elif ans == '2':
            self.calibration_pattern_type = 'line'
            self.calibration_pattern_size_um = 300.0
        elif ans == '3':
            self.calibration_pattern_type = 'line'
            self.calibration_pattern_size_um = 76.0
        elif ans == '4':
            self.calibration_pattern_type = 'sphere'
            self.calibration_pattern_size_um = 2.0
        elif ans == '5':
            custom = simpledialog.askfloat("Tamaño Personalizado", "Longitud en micrómetros (um):", minvalue=0.01)
            if custom is not None:
                self.calibration_pattern_type = 'line'
                self.calibration_pattern_size_um = custom
            else:
                root.destroy()
                print("\nCancelado - Patrón sin cambios")
                return
        else:
            root.destroy()
            print("\nCancelado - Patrón sin cambios")
            return

        root.destroy()
        print(f"\nOK Patrón establecido: {self.calibration_pattern_type} -> {self.calibration_pattern_size_um} um")

    def set_manual_scale(self):
        """
        Permite al usuario introducir manualmente la escala um/pixel.
        Útil cuando no hay microesferas en la imagen pero se conoce la escala.
        """
        from tkinter import simpledialog

        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Pedir escala al usuario
        scale = simpledialog.askfloat(
            "Escala Manual",
            "Introduce la escala en um/pixel:\n(Ejemplo: 0.0298)",
            minvalue=0.0001,
            maxvalue=10.0
        )

        root.destroy()

        if scale is not None:
            self.scale_um_per_pixel = scale
            self.scale_std = 0.0  # Sin desviación porque es un valor único
            print(f"\nOK Escala manual establecida: {scale:.4f} um/pixel")
            print("Ahora puedes usar el modo medicion (presiona 'm')")
            self.update_display()
        else:
            print("\nCancelado - No se establecio escala")

    def set_sensor_params(self):
        """
        Diálogo para introducir los parámetros físicos del sistema:
          - Tamaño de pixel del sensor (µm)
          - Factor de upscaling (Real-ESRGAN u otro)
        Calcula automáticamente um/pixel = sensor_px / upscale y lo aplica
        como escala, permitiendo usar [h] con el radio exacto esperado.
        """
        from tkinter import simpledialog

        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        px_um = simpledialog.askfloat(
            "Parámetros del sensor",
            f"Tamaño de pixel del sensor (µm):\n"
            f"  OV5647 = 1.47  |  IMX477 = 1.55  |  IMX219 = 1.12\n"
            f"Valor actual: {self.sensor_pixel_um}",
            initialvalue=self.sensor_pixel_um,
            minvalue=0.1, maxvalue=50.0
        )
        if px_um is None:
            root.destroy()
            print("\nCancelado")
            return

        factor = simpledialog.askfloat(
            "Factor de upscaling",
            f"Factor de super-resolución aplicado a la imagen:\n"
            f"  Sin upscaling = 1   |   Real-ESRGAN x2 = 2   |   x4 = 4\n"
            f"Valor actual: {self.upscale_factor}",
            initialvalue=self.upscale_factor,
            minvalue=0.25, maxvalue=32.0
        )
        root.destroy()

        if factor is None:
            print("\nCancelado")
            return

        self.sensor_pixel_um = px_um
        self.upscale_factor  = factor
        scale = px_um / factor
        self.scale_um_per_pixel = scale
        self.scale_std = 0.0

        print(f"\nOK Parámetros del sensor:")
        print(f"  Sensor pixel : {px_um} µm/px (nativo)")
        print(f"  Upscale      : x{factor}")
        print(f"  -> Escala efectiva: {scale:.4f} µm/px en imagen upscalada")
        if self.calibration_pattern_type == 'sphere':
            expected_r = (self.calibration_pattern_size_um / 2.0) / scale
            print(f"  -> Microesfera de {self.calibration_pattern_size_um}µm ≈ {expected_r*2:.1f} px diámetro en esta imagen")
        else:
            expected_l = self.calibration_pattern_size_um / scale
            print(f"  -> Regleta de {self.calibration_pattern_size_um}µm ≈ {expected_l:.1f} px de longitud en esta imagen")
        print("  Usa [h] para buscar candidatos (esferas), o [m] para medir")
        self.update_display()

    def reset_current_measurement(self):
        """
        Limpia la medición actual y restaura la imagen.
        """
        self.points = []
        self.update_display()


    def run(self):
        """
        Ejecuta el loop principal de la aplicación.
        """
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print("\n" + "="*60)
        print("FPM CALIBRATION TOOL")
        print("="*60)
        print(f"Imagen cargada: {self.image_path}")
        print(f"Dimensiones: {self.original_image.shape[1]}x{self.original_image.shape[0]} px")
        print("\nControles:")
        print("  c - Modo calibracion")
        print("  p - Configurar patron de calibracion (regleta, microesfera, etc.)")
        print("  e - Establecer escala manualmente (si no hay patron)")
        print("  m - Modo medicion (medir estructuras desconocidas)")
        print("  g - Modo geometría (medir círculos, rectángulos, triángulos, polígonos)")
        print("      1=Círculo, 2=Rectángulo, 3=Triángulo, 4=Polígono")
        print("      Enter=Finalizar polígono")
        print("  +/- - Zoom in/out")
        print("  Rueda del raton - Zoom")
        print("  Flechas (arriba/abajo/izq/der) - Desplazar imagen (pan)")
        print("  Boton derecho + arrastrar - Desplazar imagen (pan)")
        print("  k - Escala desde sensor + upscale (ej: OV5647 1.47µm × x4 ESRGAN)")
        print("  n - Contraste CLAHE (realza estructuras pequeñas, toggle)")
        print("  f - Falso color INFERNO (visualizar gradientes de luminancia, toggle)")
        print("  i - Histograma de luminancia: arrastra ROI -> histograma RGB+Y+stats")
        print("      Shift+i -> histograma de imagen completa sin selección")
        print("  p - Perfil de intensidad (line scan): 2 clicks -> curva de intensidad")
        print("  h - Buscar microesferas automáticamente (HoughCircles)")
        print("      -> marca candidatos en cyan; entra en [c] y confirma")
        print("  Doble click - Zoom x4 centrado en ese punto")
        print("  v - Seleccionar ROI (zoom eficiente >x30; Esc para borrar)")
        print("      -> clic + arrastra el rect; el zoom se auto-ajusta al soltar")
        print("      -> las mediciones siempre referencian la imagen original")
        print("  r - Reset (limpiar medicion actual)")
        print("  s - Guardar resultados en CSV")
        print("  q - Salir")
        print("="*60 + "\n")

        # Dibujar imagen inicial
        self.update_display()

        while True:
            cv2.imshow(self.window_name, self.display_image)
            key = cv2.waitKeyEx(30)  # 30ms timeout para captura confiable de teclas

            if key == ord('c'):
                # Modo calibración
                self.mode = 'calibration'
                self.points = []
                self.update_display()
                print("\n-> MODO CALIBRACION activado")
                if self.calibration_pattern_type == 'sphere':
                    print("  1. Click en el CENTRO de una microesfera")
                    print("  2. Click en el BORDE de la misma microesfera")
                else:
                    print("  1. Click en el PUNTO INICIAL de la línea patron")
                    print("  2. Click en el PUNTO FINAL de la línea patron")

            elif key == ord('p'):
                # Configurar patron
                self.set_calibration_pattern()

            elif key == ord('e'):
                # Establecer escala manualmente
                self.set_manual_scale()

            elif key == ord('k'):
                # Escala desde parámetros físicos del sensor + upscale
                self.set_sensor_params()

            elif key == ord('m'):
                # Modo medición
                if self.scale_um_per_pixel is None:
                    print("\nAVISO: Primero debes calibrar:")
                    print("  - Presiona 'c' y mide microesferas, O")
                    print("  - Presiona 'e' para introducir escala manualmente")
                else:
                    self.mode = 'measurement'
                    self.points = []
                    self.update_display()
                    print("\n-> MODO MEDICIÓN activado")
                    print("  1. Click en el primer punto")
                    print("  2. Click en el segundo punto")

            elif key == ord('g'):
                # Modo geometría
                if self.scale_um_per_pixel is None:
                    print("\nAVISO: Primero debes calibrar:")
                    print("  - Presiona 'c' y mide microesferas, O")
                    print("  - Presiona 'e' para introducir escala manualmente")
                else:
                    self.mode = 'geometry'
                    self.geometry_mode = None
                    self.points = []
                    self.update_display()
                    print("\n-> MODO GEOMETRÍA activado")
                    print("Selecciona el tipo de figura:")
                    print("  1 - Círculo (3 puntos en el perímetro)")
                    print("  2 - Rectángulo (2 esquinas opuestas)")
                    print("  3 - Triángulo (3 vértices)")
                    print("  4 - Polígono (N vértices, presiona Enter para finalizar)")
                    print("Presiona el número de la figura que deseas medir...")

            elif key == ord('1'):
                if self.mode == 'geometry':
                    # Círculo
                    self.geometry_mode = 'circle'
                    self.points = []
                    self.update_display()
                    print("\n-> CÍRCULO seleccionado")
                    print("  Haz click en 3 puntos del perímetro del círculo")

            elif key == ord('2'):
                if self.mode == 'geometry':
                    # Rectángulo
                    self.geometry_mode = 'rectangle'
                    self.points = []
                    self.update_display()
                    print("\n-> RECTÁNGULO seleccionado")
                    print("  1. Click en una esquina")
                    print("  2. Click en la esquina opuesta")

            elif key == ord('3'):
                if self.mode == 'geometry':
                    # Triángulo
                    self.geometry_mode = 'triangle'
                    self.points = []
                    self.update_display()
                    print("\n-> TRIÁNGULO seleccionado")
                    print("  Haz click en los 3 vértices del triángulo")

            elif key == ord('4'):
                if self.mode == 'geometry':
                    # Polígono
                    self.geometry_mode = 'polygon'
                    self.points = []
                    self.update_display()
                    print("\n-> POLÍGONO seleccionado")
                    print("  Haz click en cada vértice del polígono")
                    print("  Presiona Enter cuando termines")

            elif key == 13 and self.mode == 'geometry' and self.geometry_mode == 'polygon':
                # Enter - finalizar polígono
                if len(self.points) >= 3:
                    self.measure_polygon()
                    self.points = []
                    self.update_display()
                else:
                    print("\nAVISO: Necesitas al menos 3 puntos para un polígono")

            elif key == ord('+') or key == ord('='):
                # Zoom in (multiplicativo)
                self.zoom_level = min(self.zoom_max, self.zoom_level * self.zoom_factor)
                self.update_display()
                print(f"Zoom: {self.zoom_level:.2f}x")

            elif key == ord('-') or key == ord('_'):
                # Zoom out (multiplicativo)
                self.zoom_level = max(self.zoom_min, self.zoom_level / self.zoom_factor)
                self.update_display()
                print(f"Zoom: {self.zoom_level:.2f}x")

            # Paneo con teclas de flecha (códigos para Windows)
            elif key == 2490368:  # Flecha arriba
                self.pan_offset[1] += self.pan_step
                self.update_display()

            elif key == 2621440:  # Flecha abajo
                self.pan_offset[1] -= self.pan_step
                self.update_display()

            elif key == 2424832:  # Flecha izquierda
                self.pan_offset[0] += self.pan_step
                self.update_display()

            elif key == 2555904:  # Flecha derecha
                self.pan_offset[0] -= self.pan_step
                self.update_display()

            elif key == ord('i'):
                # Histograma de luminancia — ROI o imagen completa
                if self.lum_selecting:
                    self.lum_selecting = False
                    self.lum_start_img = None
                    self.lum_preview_end = None
                    self.update_display()
                    print("\nHistograma: selección cancelada")
                else:
                    self.lum_selecting = True
                    self.lum_start_img = None
                    self.lum_preview_end = None
                    self.update_display()
                    print("\nHistograma: arrastra un rectángulo para seleccionar ROI")
                    print("  (o pulsa [i] de nuevo sin arrastrar para imagen completa)")

            elif key == ord('I'):
                # Histograma imagen completa (Shift+i)
                self.show_luminance_histogram(None)

            elif key == ord('p'):
                # Perfil de intensidad (line scan) — 2 clicks
                if self.linescan_active:
                    self.linescan_active = False
                    self.linescan_points = []
                    self.update_display()
                    print("\nLine scan: cancelado")
                else:
                    self.linescan_active = True
                    self.linescan_points = []
                    self.update_display()
                    print("\nLine scan: click en PUNTO 1 de la línea")

            elif key == ord('f'):
                # Toggle mapa de falso color
                self.false_color_active = not self.false_color_active
                if self.false_color_active and self._false_color_image is None:
                    gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
                    colored = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)
                    self._false_color_image = colored
                    print("\nFalso color: mapa INFERNO generado")
                self._annotations_dirty = True
                self.update_display()
                print(f"Falso color: {'ACTIVO' if self.false_color_active else 'desactivado'}")

            elif key == ord('n'):
                # Toggle contraste CLAHE
                self.clahe_active = not self.clahe_active
                if self.clahe_active and self._clahe_image is None:
                    gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    self._clahe_image = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
                    print("\nCLAHE: imagen de contraste realzado generada")
                self._annotations_dirty = True
                self.update_display()
                print(f"Contraste CLAHE: {'ACTIVO' if self.clahe_active else 'desactivado'}")

            elif key == ord('h'):
                # Detección automática HoughCircles
                print("\nBuscando microesferas con HoughCircles...")
                self._run_hough_detection()
                self.update_display()

            elif key == ord('v'):
                # ROI: alternar selección / limpiar
                if self.roi_selecting:
                    # Cancelar selección en curso
                    self.roi_selecting = False
                    self.roi_start_img = None
                    self.roi_preview_end = None
                    self.update_display()
                    print("\nROI: selección cancelada")
                elif self.roi_region is not None:
                    # Ya hay ROI activa → empezar nueva selección
                    self.roi_selecting = True
                    self.roi_start_img = None
                    self.roi_preview_end = None
                    self.update_display()
                    print("\nROI: clic + arrastra para seleccionar nueva región")
                else:
                    # Sin ROI → entrar en modo selección
                    self.roi_selecting = True
                    self.roi_start_img = None
                    self.roi_preview_end = None
                    self.update_display()
                    print("\nROI: clic + arrastra para seleccionar región de interés")
                    print("  (el zoom se auto-ajusta al soltar; las mediciones siguen")
                    print("   referenciando la imagen original — calibración correcta)")

            elif key == 27:  # Escape
                # Cancelar selección en curso, o borrar ROI activa
                if self.roi_selecting:
                    self.roi_selecting = False
                    self.roi_start_img = None
                    self.roi_preview_end = None
                    self.update_display()
                    print("\nROI: selección cancelada")
                elif self.roi_region is not None:
                    self.roi_region = None
                    self.pan_offset = [0, 0]
                    self.zoom_level = 1.0
                    self._annotations_dirty = True
                    self.update_display()
                    print("\nROI: eliminada — vista completa restaurada")

            elif key == ord('r'):
                # Reset
                self.reset_current_measurement()
                self.mode = None
                print("\nRESET: Medición actual limpiada")

            elif key == ord('s'):
                # Guardar
                self.save_results()

            elif key == ord('q'):
                # Salir
                print("\n¡Hasta luego!")
                break

        cv2.destroyAllWindows()

        # Mostrar resumen final
        if len(self.calibration_data) > 0:
            self.display_statistics()


def select_image_file():
    """
    Abre un diálogo para seleccionar un archivo de imagen.
    Soporta PNG, JPG, JPEG, TIFF, TIF, BMP
    """
    root = Tk()
    root.withdraw()  # Ocultar ventana principal
    root.attributes('-topmost', True)  # Traer al frente

    print("\n" + "="*60)
    print("SELECCIÓN DE IMAGEN")
    print("="*60)
    print("Abriendo diálogo de selección de archivo...")

    file_types = [
        ("Imágenes soportadas", "*.png *.jpg *.jpeg *.tiff *.tif *.bmp"),
        ("TIFF", "*.tiff *.tif"),
        ("PNG", "*.png"),
        ("JPEG", "*.jpg *.jpeg"),
        ("BMP", "*.bmp"),
        ("Todos los archivos", "*.*")
    ]

    image_path = filedialog.askopenfilename(
        title="Selecciona una imagen FPM reconstruida",
        filetypes=file_types
    )

    root.destroy()

    if not image_path:
        print("No se seleccionó ninguna imagen. Saliendo...")
        return None

    print(f"OK Imagen seleccionada: {image_path}")
    return image_path


def main():
    """
    Función principal.
    """
    print("\n" + "="*60)
    print("FPM CALIBRATION TOOL - Inicializando")
    print("="*60)

    # Determinar la ruta de la imagen
    if len(sys.argv) < 2:
        # Modo GUI: seleccionar imagen con diálogo
        print("Modo: Selección de imagen con interfaz gráfica")
        image_path = select_image_file()

        if image_path is None:
            sys.exit(0)
    else:
        # Modo línea de comandos: usar argumento
        print("Modo: Línea de comandos")
        image_path = sys.argv[1]

    # Verificar que el archivo existe
    if not os.path.exists(image_path):
        error_msg = f"Error: No se encuentra el archivo {image_path}"
        print(error_msg)

        # Intentar mostrar mensaje con GUI si tkinter está disponible
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Error", error_msg)
            root.destroy()
        except:
            pass

        sys.exit(1)

    # Verificar extensión de archivo
    valid_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp']
    file_ext = os.path.splitext(image_path)[1].lower()

    if file_ext not in valid_extensions:
        warning_msg = f"Advertencia: Extensión '{file_ext}' no común. Intentando cargar de todos modos..."
        print(warning_msg)

    # Ejecutar herramienta
    try:
        print(f"\nCargando imagen: {image_path}")
        tool = FPMCalibrationTool(image_path)
        tool.run()
    except Exception as e:
        error_msg = f"Error al ejecutar la herramienta: {e}"
        print(error_msg)

        # Intentar mostrar mensaje con GUI
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Error", error_msg)
            root.destroy()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
