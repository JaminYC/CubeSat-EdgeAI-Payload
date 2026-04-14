import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from skimage import measure, color
import os

def remove_vignette_mask(img):
    """
    Detecta y enmascara la región negra de vignette (borde oscuro circular del microscopio).
    Devuelve la imagen con el vignette rellenado con la mediana de la imagen 
    y un mask binario de la zona válida.
    """
    # Umbral bajo para detectar el negro absoluto del borde del microscopio
    _, mask_valid = cv2.threshold(img, 10, 255, cv2.THRESH_BINARY)
    # Rellenamos el borde negro con la mediana del área válida para no confundir el Otsu
    median_val = int(np.median(img[mask_valid > 0]))
    img_no_vignette = img.copy()
    img_no_vignette[mask_valid == 0] = median_val
    return img_no_vignette, mask_valid

def smart_threshold(blurred):
    """
    Usa Canny (detector de bordes finos) + cierre morfológico
    para detectar y cerrar las paredes celulares de forma robusta.
    Mucho mejor que Otsu para imágenes con iluminación heterogénea.
    """
    # Canny detecta únicamente los bordes finos (paredes celulares)
    # Los thresholds se calculan automáticamente desde la mediana de la imagen
    sigma = 0.33
    v = np.median(blurred)
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edges = cv2.Canny(blurred, lower, upper)
    
    # Cierre morfológico: sella los huecos en las paredes celulares
    # Un kernel más grande sella huecos más grandes
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    
    # Invertimos: las paredes (líneas blancas) deben ser el fondo
    # y el interior de la célula (negro) debe ser el foreground
    foreground = cv2.bitwise_not(closed)
    
    # Apertura para eliminar pequeñas islas de ruido
    kernel_open = np.ones((3, 3), np.uint8)
    opening = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel_open, iterations=2)
    
    dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
    return opening, dist_transform, "Canny + Cierre Morfológico (bordes finos)"

def analyze_onion_cells(image_path, um_per_pixel=1.4, output_dir="Resultados"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"[1/7] Abriendo imagen: {image_path}")
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Error: No se pudo abrir la imagen en {image_path}")
        return

    h, w = img.shape
    print(f"      Tamaño original: {w} x {h} px")

    # Escalar a la mitad para velocidad en CPU
    img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    um_per_pixel = um_per_pixel * 2
    h, w = img.shape
    print(f"      Tamaño reducido (50%): {w} x {h} px  →  escala: {um_per_pixel:.2f} µm/px")

    # ─── PASO 1: Eliminar vignette del microscopio ────────────────────────────
    print("[2/7] Eliminando máscara de vignette (borde negro del microscopio)...")
    img_clean, mask_valid = remove_vignette_mask(img)

    # ─── PASO 2: CLAHE ───────────────────────────────────────────────────────
    print("[3/7] Mejorando contraste con CLAHE adaptativo...")
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(img_clean)

    # ─── PASO 3: Filtro bilateral ────────────────────────────────────────────
    print("[4/7] Suavizando ruido del sensor OV5647 (filtro Bilateral)...")
    blurred = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)

    # ─── PASO 4: Umbral automático inteligente ────────────────────────────────
    print("[5/7] Detectando tipo de contraste y binarizando (Otsu auto-adaptativo)...")
    opening, dist_transform, modo_umbral = smart_threshold(blurred)
    print(f"      Modo detectado: {modo_umbral}")

    kernel = np.ones((3, 3), np.uint8)
    sure_bg = cv2.dilate(opening, kernel, iterations=3)
    _, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
    sure_fg = np.uint8(sure_fg)
    unknown = cv2.subtract(sure_bg, sure_fg)

    # ─── PASO 5: WATERSHED ───────────────────────────────────────────────────
    print("[6/7] Ejecutando Watershed (OpenCV puro, sin IA)...")
    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0
    # Excluir el área de vignette del análisis
    markers[mask_valid == 0] = 1  # forzar a fondo

    img_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    markers = cv2.watershed(img_bgr, markers)
    labeled_mask = np.where(markers > 1, markers, 0).astype(np.int32)
    # Excluir también el área del vignette de las etiquetas finales
    labeled_mask[mask_valid == 0] = 0

    num_regiones = labeled_mask.max()
    print(f"      ¡Éxito! Detectadas {num_regiones} regiones candidatas.")

    # ─── PASO 6: METROLOGÍA ──────────────────────────────────────────────────
    print("[7/7] Extrayendo métricas de metrología en micrómetros (µm)...")
    props = measure.regionprops(labeled_mask)
    resultados = []
    for p in props:
        if p.area < 50:
            continue
        area_um2   = p.area * (um_per_pixel ** 2)
        largo_um   = p.axis_major_length * um_per_pixel
        ancho_um   = p.axis_minor_length * um_per_pixel
        perim_um   = p.perimeter * um_per_pixel
        redondez   = (4 * np.pi * p.area) / (p.perimeter ** 2) if p.perimeter > 0 else 0
        resultados.append({
            "ID_Celular":   p.label,
            "Area_um2":     round(area_um2,   2),
            "Largo_um":     round(largo_um,   2),
            "Ancho_um":     round(ancho_um,   2),
            "Perimetro_um": round(perim_um,   2),
            "Redondez":     round(redondez,   3),
        })

    df = pd.DataFrame(resultados)
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    csv_path = os.path.join(output_dir, f"metrologia_{base_name}.csv")
    df.to_csv(csv_path, index=False)

    print(f"\n✅ CSV guardado en: {csv_path}")
    print(f"   Células válidas (área > 50px): {len(df)}")
    if len(df) > 0:
        print(df.describe().to_string())

    # ─── VISUALIZACIÓN ────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.patch.set_facecolor("#1e1e2e")
    fig.suptitle(f"Metrología: {base_name} | Modo: {modo_umbral}", color='white', fontsize=11)

    axes[0].imshow(enhanced, cmap='gray')
    axes[0].set_title("1. Original CLAHE (sin vignette)", color="white", fontsize=10)
    axes[0].axis('off')

    axes[1].imshow(opening, cmap='gray')
    axes[1].set_title(f"2. Binarización {modo_umbral}", color="white", fontsize=10)
    axes[1].axis('off')

    overlay = color.label2rgb(labeled_mask, image=enhanced, bg_label=0, alpha=0.45)
    axes[2].imshow(overlay)
    axes[2].set_title(f"3. Watershed metrológico\n({len(df)} células válidas detectadas)", color="white", fontsize=10)
    axes[2].axis('off')

    plt.tight_layout()
    plot_path = os.path.join(output_dir, f"segmentacion_{base_name}.png")
    plt.savefig(plot_path, dpi=150, facecolor=fig.get_facecolor())
    print(f"✅ Imagen guardada en: {plot_path}")
    plt.show()

if __name__ == "__main__":
    ruta_imagen = r"d:\PruebaRealSgan\Imagenes\4DIC.png"
    analyze_onion_cells(ruta_imagen, um_per_pixel=1.4)
