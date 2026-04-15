"""
Calibracion manual con zoom real, pan, y multiples mediciones promediadas.

Controles:
  Clic izq        : marcar punto (pares: A1-B1, A2-B2, ...)
  Rueda mouse     : zoom in/out centrado en cursor
  Clic der + drag : pan (mover imagen)
  Z               : deshacer ultimo punto
  R               : resetear todo
  Enter           : confirmar (minimo 1 par de puntos)
  ESC             : cancelar
"""

import cv2
import numpy as np
from .preprocess import load_image


class ManualCalibrator:

    def __init__(self):
        self.points = []          # lista de (x, y) en coords de imagen
        self.img = None
        self.zoom = 1.0
        self.offset_x = 0.0       # pan offset en pixels de imagen
        self.offset_y = 0.0
        self.dragging = False
        self.drag_start = None
        self.window_name = "Calibracion Manual"
        self.win_w = 1100
        self.win_h = 750

    def calibrate(self, image_path: str) -> dict:
        """
        Abre imagen para marcar pares de puntos.
        Retorna dict con distancias en pixels.
        """
        img_color, _ = load_image(image_path)
        self.img = img_color
        self.points = []
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.win_w, self.win_h)
        cv2.setMouseCallback(self.window_name, self._on_mouse)

        self._redraw()

        while True:
            key = cv2.waitKey(30) & 0xFF

            if key == 27:  # ESC
                cv2.destroyAllWindows()
                return {"success": False, "message": "Calibracion cancelada"}

            elif key == ord("r"):
                self.points = []
                self._redraw()

            elif key == ord("z"):
                if self.points:
                    self.points.pop()
                    self._redraw()

            elif key == 13:  # Enter
                if len(self.points) >= 2:
                    break

        cv2.destroyAllWindows()

        # Calcular distancias de cada par
        pairs = []
        for i in range(0, len(self.points) - 1, 2):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            dist = np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
            pairs.append({
                "point1": p1,
                "point2": p2,
                "distance_px": round(float(dist), 2),
            })

        distances = [p["distance_px"] for p in pairs]
        avg_dist = float(np.mean(distances))
        std_dist = float(np.std(distances)) if len(distances) > 1 else 0.0

        return {
            "success": True,
            "pairs": pairs,
            "num_pairs": len(pairs),
            "avg_distance_px": round(avg_dist, 2),
            "std_distance_px": round(std_dist, 2),
            "distances_px": [round(d, 2) for d in distances],
        }

    # ── Mouse ──────────────────────────────────────────────────────────

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and not self.dragging:
            # Convertir coords de ventana a coords de imagen
            img_x, img_y = self._screen_to_image(x, y)
            h, w = self.img.shape[:2]
            if 0 <= img_x < w and 0 <= img_y < h:
                self.points.append((img_x, img_y))
                self._redraw()

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.dragging = True
            self.drag_start = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            self.offset_x -= dx / self.zoom
            self.offset_y -= dy / self.zoom
            self.drag_start = (x, y)
            self._redraw()

        elif event == cv2.EVENT_RBUTTONUP:
            self.dragging = False

        elif event == cv2.EVENT_MOUSEWHEEL:
            # Zoom centrado en cursor
            img_x, img_y = self._screen_to_image(x, y)

            if flags > 0:
                new_zoom = min(self.zoom * 1.2, 20.0)
            else:
                new_zoom = max(self.zoom / 1.2, 0.1)

            # Ajustar offset para centrar zoom en cursor
            self.offset_x = img_x - (x / new_zoom)
            self.offset_y = img_y - (y / new_zoom)
            self.zoom = new_zoom
            self._redraw()

    def _screen_to_image(self, sx, sy):
        """Convierte coordenadas de ventana a coordenadas de imagen."""
        img_x = int(sx / self.zoom + self.offset_x)
        img_y = int(sy / self.zoom + self.offset_y)
        return img_x, img_y

    def _image_to_screen(self, ix, iy):
        """Convierte coordenadas de imagen a coordenadas de ventana."""
        sx = int((ix - self.offset_x) * self.zoom)
        sy = int((iy - self.offset_y) * self.zoom)
        return sx, sy

    # ── Dibujo ─────────────────────────────────────────────────────────

    def _redraw(self):
        h, w = self.img.shape[:2]

        # Region visible de la imagen
        view_w = int(self.win_w / self.zoom)
        view_h = int(self.win_h / self.zoom)

        # Clamp offset
        self.offset_x = max(0, min(self.offset_x, w - view_w))
        self.offset_y = max(0, min(self.offset_y, h - view_h))

        # Extraer ROI
        x1 = int(self.offset_x)
        y1 = int(self.offset_y)
        x2 = min(x1 + view_w, w)
        y2 = min(y1 + view_h, h)

        roi = self.img[y1:y2, x1:x2].copy()

        if roi.size == 0:
            return

        # Dibujar puntos y lineas sobre el ROI
        pair_colors = [
            (0, 0, 255), (0, 255, 0), (255, 100, 0), (0, 200, 255),
            (255, 0, 255), (100, 255, 100), (255, 200, 0), (0, 100, 255),
        ]

        for i, pt in enumerate(self.points):
            pair_idx = i // 2
            color = pair_colors[pair_idx % len(pair_colors)]
            # Posicion relativa al ROI
            px = pt[0] - x1
            py = pt[1] - y1

            # Crosshair en vez de solo circulo
            size = max(4, int(8 / self.zoom))
            arm = max(8, int(20 / self.zoom))
            thick = max(1, int(2 / self.zoom))
            cv2.circle(roi, (px, py), size, color, thick)
            cv2.line(roi, (px - arm, py), (px + arm, py), color, max(1, thick - 1))
            cv2.line(roi, (px, py - arm), (px, py + arm), color, max(1, thick - 1))

            # Label
            point_in_pair = "A" if i % 2 == 0 else "B"
            label = f"{pair_idx + 1}{point_in_pair}"
            font_s = max(0.35, 0.6 / self.zoom)
            cv2.putText(roi, label, (px + arm + 2, py - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, font_s, color,
                        max(1, int(1.5 / self.zoom)), cv2.LINE_AA)

        # Lineas entre pares + distancia
        for i in range(0, len(self.points) - 1, 2):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            pair_idx = i // 2
            color = pair_colors[pair_idx % len(pair_colors)]

            s1 = (p1[0] - x1, p1[1] - y1)
            s2 = (p2[0] - x1, p2[1] - y1)
            thick = max(1, int(2 / self.zoom))
            cv2.line(roi, s1, s2, (0, 255, 255), thick)

            dist = np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
            mid = ((s1[0] + s2[0]) // 2, (s1[1] + s2[1]) // 2)
            font_s = max(0.35, 0.55 / self.zoom)
            cv2.putText(roi, f"{dist:.1f}px", (mid[0] + 5, mid[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, font_s, (0, 255, 255),
                        max(1, int(2 / self.zoom)), cv2.LINE_AA)

        # Si hay punto suelto (sin par), dibujar linea punteada al cursor
        # (no implementado por complejidad, solo indicar que falta 1 punto)

        # Resize ROI al tamano de ventana
        display = cv2.resize(roi, (self.win_w, self.win_h),
                              interpolation=cv2.INTER_LINEAR)

        # Info bar
        bar_h = 60
        bar = np.zeros((bar_h, self.win_w, 3), dtype=np.uint8)
        bar[:] = (35, 35, 35)

        # Linea 1: instruccion
        incomplete = len(self.points) % 2 == 1
        if len(self.points) == 0:
            msg = "Clic izq: punto A del par 1"
        elif incomplete:
            pair_num = len(self.points) // 2 + 1
            msg = f"Clic izq: punto B del par {pair_num}"
        else:
            num_p = len(self.points) // 2
            msg = f"{num_p} par(es) medidos  |  Clic: agregar mas  |  ENTER: confirmar"

        cv2.putText(bar, msg, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (150, 230, 150), 1, cv2.LINE_AA)

        # Linea 2: controles y zoom
        ctrl = f"Rueda: zoom ({self.zoom:.1f}x)  |  Clic der+drag: pan  |  Z: deshacer  |  R: reset  |  ESC: cancelar"
        cv2.putText(bar, ctrl, (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (150, 150, 150), 1, cv2.LINE_AA)

        # Distancias a la derecha
        if len(self.points) >= 2:
            dists = []
            for j in range(0, len(self.points) - 1, 2):
                p1, p2 = self.points[j], self.points[j + 1]
                d = np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
                dists.append(d)
            avg = np.mean(dists)
            dist_txt = f"Promedio: {avg:.1f}px ({len(dists)} med.)"
            cv2.putText(bar, dist_txt, (self.win_w - 350, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
                        cv2.LINE_AA)

        final = np.vstack([bar, display])
        cv2.imshow(self.window_name, final)


def run_manual_calibration(image_path: str) -> dict:
    """
    Ejecuta calibracion manual completa (CLI).
    Retorna dict con um_per_pixel calculado.
    """
    cal = ManualCalibrator()
    result = cal.calibrate(image_path)

    if not result["success"]:
        return result

    avg_px = result["avg_distance_px"]
    n = result["num_pairs"]
    print(f"\n{n} medicion(es), promedio: {avg_px:.2f} pixels")
    if n > 1:
        print(f"  Distancias: {result['distances_px']}")
        print(f"  Std: {result['std_distance_px']:.2f} px")

    print("\nIngresa la distancia real entre los puntos.")
    print("Ejemplos: '1 mm', '0.079 mm', '100 um', '2 um'")

    while True:
        try:
            raw = input("\nDistancia real: ").strip().lower()
            if not raw:
                continue

            parts = raw.replace(",", ".").split()
            value = float(parts[0])

            unit = "um"
            if len(parts) > 1:
                unit = parts[1].strip()

            if unit in ("mm", "milimetros", "milimetro"):
                value_um = value * 1000
            elif unit in ("um", "micrometros", "micrometro", "micras"):
                value_um = value
            elif unit in ("cm", "centimetros"):
                value_um = value * 10000
            else:
                print(f"Unidad '{unit}' no reconocida. Usa: mm, um, cm")
                continue

            um_per_pixel = value_um / avg_px

            print(f"\nResultado:")
            print(f"  {value} {unit} = {avg_px:.2f} pixels (promedio de {n})")
            print(f"  Escala: {um_per_pixel:.6f} um/pixel")

            return {
                "success": True,
                "method": "manual",
                "um_per_pixel": um_per_pixel,
                "mm_per_pixel": um_per_pixel / 1000,
                "distance_px": avg_px,
                "distance_real_um": value_um,
                "num_measurements": n,
                "message": f"Calibrado manual: {um_per_pixel:.4f} um/px ({n} med., {value} {unit} = {avg_px:.1f} px)",
            }

        except (ValueError, IndexError):
            print("Formato invalido. Ejemplo: '1 mm' o '100 um'")
