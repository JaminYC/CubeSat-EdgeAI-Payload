"""
Generador de imagen de prueba para FPM Calibration Tool
========================================================
Crea una imagen sintética con microesferas simuladas para probar
la herramienta de calibración.

NOTA: Esta es solo una imagen de PRUEBA. Para calibración real,
      usa imágenes FPM reconstruidas con microesferas reales.
"""

import cv2
import numpy as np


def create_test_image():
    """
    Crea una imagen de prueba con microesferas simuladas.
    """
    # Crear imagen de fondo (simulando campo claro)
    width, height = 1920, 1440
    image = np.ones((height, width, 3), dtype=np.uint8) * 220

    # Añadir ruido de fondo
    noise = np.random.normal(0, 10, (height, width, 3))
    image = np.clip(image + noise, 0, 255).astype(np.uint8)

    # Parámetros de simulación
    # Asumimos una escala de ~0.03 µm/pixel (típica para FPM)
    # Microesfera de 2 µm → ~67 píxeles de diámetro
    sphere_diameter_px = 67
    sphere_radius_px = sphere_diameter_px // 2

    # Posiciones de microesferas (distribuidas aleatoriamente)
    np.random.seed(42)
    num_spheres = 25
    sphere_positions = []

    margin = 100
    for _ in range(num_spheres):
        x = np.random.randint(margin, width - margin)
        y = np.random.randint(margin, height - margin)
        sphere_positions.append((x, y))

    # Dibujar microesferas
    for center in sphere_positions:
        # Añadir variación de tamaño (±5%)
        variation = np.random.uniform(0.95, 1.05)
        radius = int(sphere_radius_px * variation)

        # Crear círculo con gradiente (simulando iluminación)
        overlay = image.copy()

        # Círculo oscuro (cuerpo de la esfera)
        cv2.circle(overlay, center, radius, (80, 80, 80), -1)

        # Borde más definido
        cv2.circle(overlay, center, radius, (50, 50, 50), 2)

        # Resaltado (simulando reflexión especular)
        highlight_offset = (-radius // 3, -radius // 3)
        highlight_pos = (center[0] + highlight_offset[0],
                        center[1] + highlight_offset[1])
        cv2.circle(overlay, highlight_pos, radius // 4, (200, 200, 200), -1)

        # Mezclar con la imagen original
        alpha = 0.8
        image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)

    # Añadir algunas "estructuras biológicas" simuladas
    # (para probar el modo de medición)

    # Célula simulada 1
    cell_center = (500, 400)
    cv2.ellipse(image, cell_center, (80, 120), 45, 0, 360, (120, 140, 160), 3)

    # Célula simulada 2
    cell_center = (1200, 800)
    cv2.ellipse(image, cell_center, (60, 90), -30, 0, 360, (110, 130, 150), 3)

    # Fibra simulada
    fiber_points = np.array([
        [300, 1000], [500, 1050], [700, 1020], [900, 1080]
    ])
    cv2.polylines(image, [fiber_points], False, (100, 120, 140), 4)

    # Añadir texto informativo
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "Imagen de prueba FPM - Microesferas 2um simuladas"
    cv2.putText(image, text, (50, 50), font, 0.8, (0, 0, 0), 2)

    return image


def main():
    """
    Genera y guarda la imagen de prueba.
    """
    print("Generando imagen de prueba...")

    image = create_test_image()

    output_path = "test_fpm_image.png"
    cv2.imwrite(output_path, image)

    print(f"✓ Imagen guardada: {output_path}")
    print("\nPara probar la herramienta de calibración:")
    print(f"  python fpm_calibration_tool.py {output_path}")
    print("\nNOTA: Esta es una imagen sintética de PRUEBA.")
    print("      Para calibración real, usa imágenes FPM con microesferas reales.")


if __name__ == "__main__":
    main()
