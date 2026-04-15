"""
Calibracion manual: el usuario marca dos puntos sobre una imagen de referencia
(regla, regleta, microesferas) e indica la distancia real entre ellos.
El sistema calcula um/pixel.
"""

import cv2
import numpy as np
from .preprocess import load_image


class ManualCalibrator:
    """
    Abre una ventana OpenCV donde el usuario:
      1. Hace clic en punto A
      2. Hace clic en punto B
      3. Ingresa distancia real (en um o mm)
      4. El sistema calcula um/pixel

    Controles:
      Clic izq  : marcar punto
      R         : resetear puntos
      Enter     : confirmar (cuando hay 2 puntos)
      ESC       : cancelar
      +/-       : zoom
    """

    def __init__(self):
        self.points = []
        self.img = None
        self.display = None
        self.zoom = 1.0
        self.window_name = "Calibracion Manual - Marca 2 puntos"

    def calibrate(self, image_path: str) -> dict:
        """
        Abre imagen y permite marcar 2 puntos.
        Retorna dict con distancia en pixels y espera input de distancia real.
        """
        img_color, _ = load_image(image_path)
        self.img = img_color
        self.points = []

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1024, 700)
        cv2.setMouseCallback(self.window_name, self._on_mouse)

        self._redraw()

        while True:
            key = cv2.waitKey(30) & 0xFF

            if key == 27:  # ESC
                cv2.destroyWindow(self.window_name)
                return {"success": False, "message": "Calibracion cancelada"}

            elif key == ord("r"):  # Reset
                self.points = []
                self._redraw()

            elif key == ord("+") or key == ord("="):
                self.zoom = min(self.zoom * 1.25, 5.0)
                self._redraw()

            elif key == ord("-"):
                self.zoom = max(self.zoom / 1.25, 0.2)
                self._redraw()

            elif key == 13 and len(self.points) == 2:  # Enter
                break

        cv2.destroyWindow(self.window_name)

        # Calcular distancia en pixels
        p1, p2 = self.points
        dist_px = np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

        return {
            "success": True,
            "point1": p1,
            "point2": p2,
            "distance_px": round(float(dist_px), 2),
        }

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Convertir coordenadas de display a imagen real
            real_x = int(x / self.zoom)
            real_y = int(y / self.zoom)

            if len(self.points) < 2:
                self.points.append((real_x, real_y))
                self._redraw()

    def _redraw(self):
        h, w = self.img.shape[:2]
        display = self.img.copy()

        # Dibujar puntos
        for i, pt in enumerate(self.points):
            color = (0, 0, 255) if i == 0 else (0, 255, 0)
            cv2.circle(display, pt, 6, color, 2)
            cv2.circle(display, pt, 2, color, -1)
            label = f"P{i + 1} ({pt[0]}, {pt[1]})"
            cv2.putText(display, label, (pt[0] + 10, pt[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # Dibujar linea entre puntos
        if len(self.points) == 2:
            p1, p2 = self.points
            cv2.line(display, p1, p2, (0, 255, 255), 2)
            dist_px = np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            cv2.putText(display, f"{dist_px:.1f} px", (mid[0] + 10, mid[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2,
                        cv2.LINE_AA)

        # Info bar
        bar_h = 55
        bar = np.zeros((bar_h, w, 3), dtype=np.uint8)
        bar[:] = (35, 35, 35)

        if len(self.points) == 0:
            msg = "Haz CLIC en el punto A de la regla"
        elif len(self.points) == 1:
            msg = "Haz CLIC en el punto B de la regla"
        else:
            msg = "ENTER = confirmar  |  R = resetear  |  ESC = cancelar"

        cv2.putText(bar, msg, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (150, 230, 150), 1, cv2.LINE_AA)
        cv2.putText(bar, f"Puntos: {len(self.points)}/2  |  +/- = zoom  |  R = reset",
                    (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1,
                    cv2.LINE_AA)

        display = np.vstack([bar, display])

        # Zoom
        if self.zoom != 1.0:
            new_w = int(display.shape[1] * self.zoom)
            new_h = int(display.shape[0] * self.zoom)
            if new_w > 0 and new_h > 0:
                display = cv2.resize(display, (new_w, new_h))

        cv2.imshow(self.window_name, display)


def run_manual_calibration(image_path: str) -> dict:
    """
    Ejecuta calibracion manual completa.
    Retorna dict con um_per_pixel calculado.
    """
    cal = ManualCalibrator()
    result = cal.calibrate(image_path)

    if not result["success"]:
        return result

    dist_px = result["distance_px"]
    print(f"\nDistancia medida: {dist_px:.2f} pixels")
    print("Ingresa la distancia real entre los 2 puntos.")
    print("Ejemplos: '1 mm', '0.079 mm', '100 um', '2 um'")

    while True:
        try:
            raw = input("\nDistancia real: ").strip().lower()
            if not raw:
                continue

            # Parsear valor y unidad
            parts = raw.replace(",", ".").split()
            value = float(parts[0])

            unit = "um"
            if len(parts) > 1:
                unit = parts[1].strip()

            # Convertir a micrometros
            if unit in ("mm", "milimetros", "milimetro"):
                value_um = value * 1000
            elif unit in ("um", "µm", "micrometros", "micrometro", "micras"):
                value_um = value
            elif unit in ("cm", "centimetros"):
                value_um = value * 10000
            else:
                print(f"Unidad '{unit}' no reconocida. Usa: mm, um, cm")
                continue

            um_per_pixel = value_um / dist_px

            print(f"\nResultado:")
            print(f"  {value} {unit} = {dist_px:.2f} pixels")
            print(f"  Escala: {um_per_pixel:.6f} um/pixel")
            print(f"  Escala: {um_per_pixel / 1000:.6f} mm/pixel")

            return {
                "success": True,
                "method": "manual",
                "um_per_pixel": um_per_pixel,
                "mm_per_pixel": um_per_pixel / 1000,
                "distance_px": dist_px,
                "distance_real_um": value_um,
                "message": f"Calibrado manual: {um_per_pixel:.4f} um/px ({value} {unit} = {dist_px:.1f} px)",
            }

        except (ValueError, IndexError):
            print("Formato invalido. Ejemplo: '1 mm' o '100 um'")
