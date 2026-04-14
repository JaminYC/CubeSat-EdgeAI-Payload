# FPM Calibration Tool - Guía de Uso

## Descripción

Herramienta de calibración y medición dimensional para imágenes de microscopía FPM (Fourier Ptychographic Microscopy) usando microesferas de poliestireno de 2 µm como patrón de referencia.

## Características

- ✅ Calibración metrológica con microesferas de diámetro conocido (2 µm)
- ✅ Interfaz interactiva basada en OpenCV (sin dependencias complejas)
- ✅ Cálculo de escala µm/pixel usando mediana estadística
- ✅ Medición de estructuras biológicas calibradas
- ✅ Exportación de resultados a CSV
- ✅ Estadísticas de calibración (desviación estándar, CV%)

## Requisitos

```bash
pip install opencv-python numpy
```

## Uso Básico

### 1. Ejecutar la herramienta

**Opción A: Con interfaz gráfica (Recomendado)**

```bash
python fpm_calibration_tool.py
```

Se abrirá un diálogo para seleccionar la imagen. Soporta:
- TIFF (.tiff, .tif) ← Formato científico común
- PNG (.png)
- JPEG (.jpg, .jpeg)
- BMP (.bmp)

**Opción B: Por línea de comandos**

```bash
python fpm_calibration_tool.py <ruta_a_imagen_fpm>
```

Ejemplos:
```bash
python fpm_calibration_tool.py Imagenes/fpm_microesferas.tiff
python fpm_calibration_tool.py resultado_fpm.png
```

### 2. Calibración con Microesferas

**Objetivo**: Establecer la escala µm/pixel del sistema

**Procedimiento**:

1. Presiona `c` para activar el **modo calibración**
2. Localiza una microesfera visible en la imagen
3. Haz click en el **centro** de la microesfera
4. Haz click en el **borde** de la microesfera
5. El software dibujará un círculo y calculará:
   - Diámetro en píxeles
   - Escala µm/pixel (asumiendo 2 µm reales)
6. Repite el proceso para 10-20 microesferas diferentes
7. La escala final se calcula como la **mediana** de todas las mediciones

**Recomendaciones científicas**:
- Medir al menos 10 microesferas para buena estadística
- Seleccionar microesferas bien definidas y en foco
- Distribuir las mediciones en diferentes zonas de la imagen
- Verificar que CV% < 5% para calibración confiable

### 3. Medición de Estructuras Desconocidas

**Objetivo**: Medir dimensiones de tejidos u objetos biológicos

**Procedimiento**:

1. Presiona `m` para activar el **modo medición**
2. Haz click en el **primer punto** de la estructura a medir
3. Haz click en el **segundo punto**
4. El software mostrará:
   - Distancia en píxeles
   - Distancia en micrómetros (calibrada)

### 4. Guardar Resultados

Presiona `s` para guardar los resultados. Se generarán dos archivos:

- `fpm_calibration_YYYYMMDD_HHMMSS.csv` - Datos tabulados
- `fpm_calibration_summary_YYYYMMDD_HHMMSS.txt` - Resumen estadístico

### 5. Zoom y Navegación

**Zoom:**
- `+` o `=` - Acercar (zoom in)
- `-` - Alejar (zoom out)
- Rueda del ratón - Zoom continuo (más preciso)

**Desplazamiento (Pan):**
- Flechas del teclado (↑↓←→) - Desplaza la imagen en pasos
- Botón derecho del ratón + arrastrar - Desplazamiento libre

**Características:**
- Zoom de 0.1x a 10x
- Panel de información superior con controles visibles
- Textos grandes y legibles
- Las mediciones se mantienen en las coordenadas originales de la imagen

### 6. Otros Controles

- `r` - Reset: Limpia la medición actual sin borrar calibraciones previas
- `q` - Salir: Cierra la aplicación

## Cálculos Realizados

### Calibración

Para cada microesfera medida:

```
radio_px = √[(x_borde - x_centro)² + (y_borde - y_centro)²]
diámetro_px = 2 × radio_px
escala = 2.0 µm / diámetro_px
```

### Escala Final

```
escala_final = mediana(escala₁, escala₂, ..., escalaₙ)
desviación_std = std(escala₁, escala₂, ..., escalaₙ)
CV% = (desviación_std / escala_final) × 100
```

### Medición

```
distancia_px = √[(x₂ - x₁)² + (y₂ - y₁)²]
distancia_µm = distancia_px × escala_final
```

## Formato de Salida CSV

```csv
id,center_x,center_y,border_x,border_y,radius_px,diameter_px,um_per_pixel
1,450,320,485,320,35.00,70.00,0.0286
2,680,450,710,455,30.41,60.82,0.0329
...
```

## Ejemplo de Flujo de Trabajo

```
1. Capturar imagen FPM reconstruida con microesferas visibles
2. python fpm_calibration_tool.py imagen_fpm.png
3. Presionar 'c' y medir 15 microesferas diferentes
4. Verificar estadísticas en consola (CV% < 5%)
5. Presionar 's' para guardar calibración
6. Presionar 'm' para medir estructuras biológicas
7. Medir células, tejidos, etc.
8. Guardar resultados finales
```

## Validación Científica

### Criterios de Calidad

- **Número de mediciones**: n ≥ 10
- **Coeficiente de variación**: CV% < 5% (excelente), CV% < 10% (aceptable)
- **Distribución espacial**: Microesferas en diferentes zonas de la imagen

### Fuentes de Error

1. **Error de localización manual**: ±1-2 píxeles en centro/borde
2. **Variabilidad de microesferas**: ±2% (especificación del fabricante)
3. **Aberraciones ópticas**: Pueden causar distorsión radial

### Trazabilidad Metrológica

- Patrón: Microesferas de poliestireno certificadas (2.0 ± 0.04 µm)
- Método: Metrología manual asistida por computadora
- Estadística: Mediana robusta + desviación estándar

## Limitaciones

- La escala es válida **solo para la imagen FPM reconstruida**, no para frames crudos
- Se asume que la imagen no tiene distorsión significativa
- La precisión depende de la calidad de la reconstrucción FPM

## Notas Técnicas

### Diferencia con Pixel Pitch

**NO** confundir:
- **Pixel pitch físico**: 1.4 µm (tamaño del sensor OV5647)
- **Escala efectiva**: Calculada por este software (depende del sistema óptico completo)

La escala efectiva incluye:
- Magnificación del objetivo
- Reconstrucción FPM
- Procesamiento de imagen

Por eso es **crítico** calibrar con objetos de tamaño conocido.

## Soporte

Para reportar problemas o sugerencias, contacta con el desarrollador del sistema FPM.

## Referencias

- Fourier Ptychographic Microscopy: Zheng et al., Nature Photonics (2013)
- Metrología óptica: ISO 10012:2003
- Microesferas de calibración: Polysciences, Thermo Fisher
