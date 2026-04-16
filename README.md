# CubeSat EdgeAI Payload

Pipeline autónomo de microscopía para CubeSat: calibración, mejora por IA, segmentación celular, detección de fibras y reporte — diseñado para correr en Raspberry Pi 5.

---

## Arquitectura del Pipeline

```mermaid
flowchart TD
    START(["Iniciar analisis"]) --> LOAD["Carga de imagenes\nLee todos los archivos de imagen\nde la carpeta seleccionada"]

    LOAD --> CLASSIFY["Clasificacion automatica\nAnaliza histogramas, bordes y\npatrones para determinar\nel tipo de cada imagen"]

    CLASSIFY --> R["Imagen de regla\nContiene marcas de escala\nconocidas para calibrar"]
    CLASSIFY --> O["Piel de cebolla\nTejido epidermal con celulas\nrectangulares visibles"]
    CLASSIFY --> F["Fibra de algodon\nEstructuras filamentosas\nalargadas y delgadas"]
    CLASSIFY --> U["Imagen no reconocida\nNo coincide con ningun patron\nSe procesa como cebolla por defecto"]

    R --> CAL["Calibracion\nDetecta lineas de la regla con\nTransformada de Hough y calcula\nla relacion micrometros por pixel"]
    CAL --> SCALE[("Factor de escala\num/pixel\nAplica a todas las\nmediciones del lote")]

    O --> ENH_O["Mejora de imagen por IA\nEtapa obligatoria: en el espacio las\nimagenes llegan con ruido del sensor,\nradiacion y optica limitada (lensless)\n\nDenoising:\nN2V - self-supervised, no necesita\nimagen limpia de referencia\nCARE - noise2clean con ruido sintetico\n\nSuper-resolucion:\nReal-ESRGAN - upscaling x4 con red\ngenerativa adversarial (RRDBNet)\nFPM - reconstruccion multi-angulo,\naumenta resolucion real desde\nmultiples capturas lensless+OLED"]
    F --> ENH_F["Mejora de imagen por IA\nDenoising obligatorio para fibras:\nN2V o CARE para reducir ruido\nantes de detectar bordes finos"]

    ENH_O --> SEG_O["Segmentacion celular\nCellpose cyto3: predice campos de flujo\nvectorial que apuntan al centro de cada\ncelula y agrupa pixeles que convergen\nal mismo centro para formar mascaras\nStarDist: predice distancias radiales\ndesde cada pixel al borde del objeto\nen multiples direcciones y reconstruye\npoligonos convexos como contorno celular\nOpenCV: umbral adaptativo + watershed\ncon marcadores morfologicos como fallback"]
    ENH_F --> SEG_F["Deteccion de fibras\nCanny para bordes + Hough para\nlineas + esqueletizacion para\nextraer el eje central de cada fibra"]
    U --> ENH_O

    SEG_O --> MEAS_O["Medicion celular\nArea en um2, perimetro en um,\ncircularidad, conteo total,\nestadisticas por imagen"]
    SEG_F --> MEAS_F["Medicion de fibras\nGrosor promedio en um,\nlongitud en um, numero de\ncruces entre fibras"]

    SCALE --> MEAS_O
    SCALE --> MEAS_F

    MEAS_O --> AGG["Agregacion de resultados\nCombina mediciones de todas\nlas imagenes del lote en\nun resumen estadistico global"]
    MEAS_F --> AGG

    AGG --> OUT_IMG["Imagenes procesadas\nOverlays con contornos coloreados\nsobre la imagen original\nMascaras de segmentacion"]
    AGG --> OUT_CSV["Datos estructurados\nCSV con mediciones por celula/fibra\nJSON con metadata completa\nincluyendo calibracion y config"]
    AGG --> OUT_RPT["Reporte de texto\nResumen legible con promedios,\ndesviaciones, conteos totales\ny parametros del pipeline"]
```

### Por que la mejora de imagen es obligatoria

En un CubeSat las condiciones de captura son hostiles: el sensor opera sin lente (lensless), la iluminacion proviene de una pantalla OLED programable, hay ruido por radiacion cosmica, ruido termico del sensor en el vacio, y la resolucion optica esta limitada por la apertura numerica del sistema sin lente. Las imagenes crudas llegan con un nivel de ruido y una resolucion que hacen imposible segmentar celulas o fibras directamente. La mejora de imagen no es una optimizacion, es un requisito para que el resto del pipeline funcione.

### Por que N2V/CARE y no solo Real-ESRGAN

El proyecto comenzo usando Real-ESRGAN (RRDBNet, 23 bloques residuales) para super-resolucion x4. Real-ESRGAN produce imagenes visualmente mas nitidas y con mas detalle, pero tiene limitaciones para microscopia cientifica:

| Aspecto | Real-ESRGAN | N2V / CARE | FPM |
|---|---|---|---|
| Funcion | Super-resolucion (upscaling) | Denoising (reduccion de ruido) | Reconstruccion multi-angulo |
| Que hace | Interpola pixeles nuevos con una GAN | Elimina ruido preservando la senal real | Combina capturas reales para resolver frecuencias perdidas |
| Resolucion nueva | Alucinada (la red inventa detalles) | No cambia resolucion | Real (informacion de multiples angulos) |
| Riesgo cientifico | Puede inventar estructuras que no existen | Bajo, solo reduce varianza del ruido | Bajo, usa datos reales |
| Necesita referencia | No (modelo preentrenado) | N2V no, CARE usa ruido sintetico | Si (multiples capturas) |
| Uso en el pipeline | Post-procesamiento visual | Antes de segmentacion | Antes de todo (reemplaza captura cruda) |

**Conclusion**: Real-ESRGAN sirve para visualizacion y presentacion, pero no debe usarse antes de segmentacion cientifica porque puede crear bordes celulares falsos. N2V y CARE reducen ruido sin inventar informacion. FPM aumenta la resolucion real del sistema. El pipeline usa los tres de forma complementaria:

1. **FPM** (si hay multiples capturas): reconstruccion multi-angulo para obtener imagen de alta resolucion real
2. **N2V o CARE**: denoising sobre la imagen reconstruida (o cruda si no hay FPM)
3. **Real-ESRGAN** (opcional, solo para visualizacion): upscaling para reportes visuales, no para medicion

### Descripcion de cada etapa

**1. Carga y clasificacion.** El pipeline lee todas las imagenes de la carpeta de entrada y las clasifica automaticamente segun su contenido. Analiza histogramas de intensidad, densidad de bordes y patrones espaciales para distinguir entre imagenes de regla (para calibracion), piel de cebolla (tejido epidermal), fibra de algodon (estructuras filamentosas) e imagenes no reconocidas. Las imagenes no reconocidas se procesan como cebolla por defecto.

**2. Calibracion.** Si existe una imagen de regla en el lote, el pipeline detecta las marcas de escala usando la Transformada de Hough para lineas y calcula automaticamente cuantos micrometros equivale cada pixel. Este factor se aplica a todas las mediciones posteriores. Tambien se puede calibrar manualmente desde la GUI o usar un valor por defecto del archivo de configuracion.

**3. Mejora de imagen por IA.** Etapa obligatoria. Todas las imagenes pasan por al menos un metodo de mejora antes de la segmentacion. Para denoising hay dos opciones: Noise2Void (N2V) es un metodo self-supervised que entrena una red U-Net (470K parametros) directamente sobre la imagen ruidosa, enmascara pixeles al azar (blind-spot) y obliga a la red a predecir el valor limpio usando solo vecinos. Es ideal para el espacio porque no necesita imagenes limpias de referencia, que son imposibles de obtener en orbita. CARE (Content-Aware Restoration) usa la misma arquitectura U-Net con enfoque noise2clean: genera pares de entrenamiento agregando ruido gaussiano sintetico (30% de intensidad) y entrena la red para reconstruir la version sin ruido. Para super-resolucion: FPM (Fourier Ptychographic Microscopy) combina multiples capturas desde diferentes angulos de iluminacion para reconstruir una imagen de resolucion superior real, no interpolada. Real-ESRGAN (RRDBNet, 64 filtros, 23 bloques residuales) hace upscaling x4 con una red generativa adversarial, pero solo se usa para visualizacion porque puede inventar detalles que no existen en la muestra real.

**4. Segmentacion.** Para cebolla hay tres opciones. Cellpose cyto3 es una red neuronal entrenada en miles de imagenes de celulas de distintos tipos: predice dos campos de flujo vectorial (horizontal y vertical) donde cada vector apunta hacia el centro de la celula mas cercana, luego agrupa todos los pixeles cuyos flujos convergen al mismo punto para formar la mascara de cada celula individual. Esto le permite separar celulas que se tocan sin sobre-segmentar. StarDist predice desde cada pixel la distancia al borde del objeto mas cercano en 32 direcciones radiales, y con esas distancias reconstruye un poligono convexo que representa el contorno de cada celula. Es mas rapido que Cellpose (4s vs 38s en CPU) porque la inferencia es un solo paso sin iteracion de flujos. OpenCV usa umbral adaptativo para binarizar la imagen, operaciones morfologicas (apertura, cierre) para limpiar ruido, distance transform para encontrar marcadores y watershed para separar celulas tocandose. Si el modelo de IA seleccionado falla por cualquier razon, el pipeline cae automaticamente a OpenCV (graceful degradation). Para fibras: deteccion de bordes Canny, Transformada de Hough para segmentos de linea y esqueletizacion morfologica para extraer el eje central de un pixel de ancho.

**5. Medicion.** Convierte las segmentaciones en mediciones fisicas usando el factor de calibracion. Para celulas: area (um2), perimetro (um), circularidad (0-1 donde 1 es circulo perfecto), conteo total. Para fibras: grosor promedio (um), longitud (um), numero de cruces entre fibras.

**6. Exportacion.** Genera tres tipos de salida: imagenes con overlays coloreados sobre la original y mascaras binarias; archivos CSV con una fila por celula/fibra y JSON con metadata completa; y un reporte de texto legible con estadisticas resumidas del lote completo.

---

## Modelos de IA Integrados

### Mejora de imagen (etapa obligatoria)

| Modelo | Funcion | Tipo | Tiempo (CPU) | Para medicion | Para visualizacion |
|---|---|---|---|---|---|
| **N2V** | Denoising | Self-supervised (sin referencia limpia) | ~80s (10 epochs) | Si | Si |
| **CARE** | Denoising | Noise2Clean (ruido sintetico) | ~80s (10 epochs) | Si | Si |
| **FPM multi-angulo** | Super-resolucion real | Reconstruccion en Fourier | ~5-15s | Si | Si |
| **Real-ESRGAN** | Super-resolucion visual | GAN (RRDBNet x4) | ~3s GPU, ~30s CPU | No (inventa detalles) | Si |

### Segmentacion

| Modelo | Tipo | Tamanio | Tiempo (CPU) | Celulas detectadas* | Viable RPi 5 |
|---|---|---|---|---|---|
| **Cellpose v3 (cyto3)** | Deep Learning | ~25 MB | ~38s | 162 | Con ONNX |
| **StarDist 2D** | Deep Learning | ~30 MB | ~4s | ~150 | Si (mas rapido) |
| **OpenCV** | Clasico | -- | <1s | Variable | Si |

*\*Resultados en imagen de prueba 630x1200*

> **Nota RPi 5:** StarDist es 9x mas rapido que Cellpose en CPU -- candidato ideal para exportar a ONNX.

---

## Reconstrucción FPM

Módulo de Fourier Ptychographic Microscopy para setup lensless + OLED:

| Método | Descripción | Uso |
|---|---|---|
| `multiangle` | Fusión multi-ángulo (lensless + OLED) | Setup CubeSat |
| `multiframe` | Multi-frame con shifts sub-pixel | Microscopio con stage |
| `fourier` | Ptychography completa con lente | Microscopio convencional |

```bash
python main.py --fpm SCAN_FOLDER --fpm-method multiangle --fpm-upscale 2
```

---

## GUI (Interfaz con Tabs)

La GUI está organizada en 3 pestañas:

| Tab | Contenido |
|---|---|
| **Pipeline** | Carpeta entrada, vista previa, calibración, selección de mejora (N2V/CARE), selección de segmentación (Cellpose/StarDist/OpenCV), ejecución y progreso |
| **FPM** | Reconstrucción FPM: carpeta, método, upscale, iteraciones, alineación |
| **Modelos IA** | Prueba individual de modelos: selección de imagen, ejecución de Cellpose/StarDist/N2V/CARE, ejecución de todos |

Log compartido en la parte inferior de todas las pestañas.

---

## Estructura del Proyecto

```
PruebaRealSgan/
├── main.py                              # Entry point (GUI / CLI / FPM / Viewer)
├── config.yaml                          # Configuración del pipeline
├── requirements_pipeline.txt            # Dependencias
│
├── pipeline/                            # Módulos del pipeline autónomo
│   ├── __init__.py
│   ├── gui.py                           # GUI con tabs (Pipeline / FPM / Modelos IA)
│   ├── controller.py                    # Orquestador del pipeline completo
│   ├── config.py                        # Carga de configuración YAML
│   ├── classifier.py                    # Clasificación automática de imágenes
│   ├── calibration.py                   # Calibración automática (regla)
│   ├── manual_calibration.py            # Calibración manual (GUI)
│   ├── preprocess.py                    # CLAHE, denoise, preprocesamiento
│   ├── ai_enhance.py                    # Modelos IA: Cellpose, StarDist, N2V, CARE
│   ├── segmentation_onion.py            # Segmentación celular (OpenCV)
│   ├── segmentation_fiber.py            # Detección de fibras
│   ├── measurement.py                   # Mediciones dimensionales
│   ├── export.py                        # Exportación JSON/CSV/imágenes
│   ├── fpm_reconstruction.py            # Reconstrucción FPM multi-ángulo
│   └── viewer.py                        # Visor interactivo de resultados
│
├── fpm_calibration_tool.py              # GUI calibración FPM (standalone)
├── cell_analyzer_gui.py                 # GUI análisis celular (standalone)
├── analisis_calibracion.py              # Análisis de resultados de calibración
├── analisis_multiple_calibraciones.py   # Análisis multi-sesión
│
├── models/                              # Pesos de modelos descargados
├── Imagenes/                            # Imágenes de entrada
├── Resultados/                          # Salidas procesadas
├── Minimal/                             # Inferencia mínima Real-ESRGAN
├── Real-ESRGAN/                         # Repo completo Real-ESRGAN
├── Documentos de Referencia/            # Papers y datasheets
└── prompts/                             # Prompts de evaluación IA
```

---

## Uso Rápido

```bash
# Activar entorno virtual
venv310\Scripts\activate        # Windows
source venv310/bin/activate     # Linux

# Abrir GUI completa (modo por defecto)
python main.py

# Pipeline CLI (sin GUI)
python main.py --cli --folder ./Imagenes/mi_carpeta

# Reconstrucción FPM desde CLI
python main.py --fpm ./scan_folder --fpm-method multiangle --fpm-upscale 2

# Visor de resultados
python main.py --viewer --folder ./Resultados/run_20260416

# Calibración FPM standalone
python fpm_calibration_tool.py imagen.tiff
```

---

## Instalación

```bash
# Dependencias del pipeline
pip install -r requirements_pipeline.txt
```

### Dependencias principales

```
opencv-python>=4.8.0
numpy>=1.24.0,<2
scikit-image>=0.21.0
PyYAML>=6.0
cellpose>=3.0,<4          # v3 con cyto3 (v4 CPSAM demasiado pesado para CPU)
csbdeep>=0.7.2
stardist>=0.9.0
tensorflow>=2.11
torch>=2.0
```

> **Nota:** `numpy<2` es necesario por compatibilidad con torch. Cellpose se instala con `--no-deps` para evitar conflictos con opencv-python-headless.

---

## Pipeline de Evaluación de Modelos

Estrategia de 4 fases para seleccionar el mejor modelo de segmentación:

| Fase | Objetivo | Estado |
|---|---|---|
| **1. Baseline clásico** | Establecer rendimiento base con OpenCV | Completado |
| **2. Modelos preentrenados** | Evaluar Cellpose cyto3, StarDist, N2V, CARE | Completado |
| **3. Fine-tuning** | Especializar mejor modelo para piel de cebolla | Pendiente |
| **4. Edge Deploy** | Export ONNX + benchmark en RPi 5 | Pendiente |

### Resultados de Fase 2 (imagen de prueba 630×1200)

| Modelo | Células | Tiempo | Notas |
|---|---|---|---|
| Cellpose cyto3 | 162 | 38.1s | Diámetro auto: 77.7 px |
| StarDist 2D | ~150 | ~4s | 9× más rápido que Cellpose |
| N2V denoising | — | 80.9s | 470K params, 400 patches |

### Graceful Degradation

| Condición | Método | Latencia | Precisión |
|---|---|---|---|
| Normal (GPU/RPi) | Cellpose/StarDist (ONNX) | ~2-5s | Alta |
| Recursos limitados | OpenCV watershed + morfología | ~0.5s | Media |
| Modo mínimo | Solo medición con escala calibrada | ~0.1s | Básica |

---

## Configuración (`config.yaml`)

Secciones principales:

| Sección | Contenido |
|---|---|
| `mode` | Modo de operación (onion/fiber/auto) |
| `paths` | Carpetas de entrada/salida |
| `calibration` | Default µm/pixel, parámetros de detección de regla |
| `preprocess` | CLAHE clip limit, denoise strength |
| `onion` | Método de segmentación, parámetros de watershed |
| `fiber` | Detección Canny, Hough, skeleton |
| `ai_enhance` | Config de Cellpose, StarDist, N2V, CARE |

---

## Datasets de Referencia

| Dataset | Utilidad | Link |
|---|---|---|
| BBBC (Broad Bioimage Benchmark) | Benchmark de segmentación celular | broad.io/bbbc |
| Cellpose training data | Dataset base de cyto3 | cellpose.org |
| Data Science Bowl 2018 | Segmentación de núcleos | kaggle.com/c/data-science-bowl-2018 |
| Imágenes propias de cebolla | Fine-tuning especializado | Este repositorio |
