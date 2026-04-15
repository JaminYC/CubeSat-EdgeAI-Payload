# Prompt: Evaluación de Modelos de Segmentación Celular para Piel de Cebolla

> Copiar este prompt completo en Claude para obtener el análisis comparativo de modelos.

---

Actúa como un investigador senior en visión computacional para microscopía, segmentación celular e IA embebida. Quiero que me ayudes a diseñar y evaluar un pipeline para segmentar células de piel de cebolla, con el objetivo final de crear un modelo propio optimizado para Raspberry Pi, pero sin empezar desde cero.

## Contexto del proyecto

Tengo imágenes de microscopía de piel de cebolla capturadas con un microscopio FPM (Fourier Ptychographic Microscopy). El sistema final debe correr de forma autónoma en una Raspberry Pi como parte de un payload CubeSat de análisis biológico.

Ya cuento con:
- Herramienta de calibración FPM (microesferas de 2 µm)
- Pipeline de super-resolución (Real-ESRGAN x4)
- Análisis celular básico con OpenCV (threshold + contornos + watershed)
- Imágenes reales de piel de cebolla en distintas condiciones

Necesito entender:

1. Qué modelos base del estado del arte sirven mejor como punto de partida
2. Qué características visuales de la muestra son las más importantes para segmentar correctamente
3. Qué errores comete cada enfoque
4. Cómo traducir esa evaluación en el diseño de un modelo propio

No quiero una respuesta genérica. Quiero un análisis experimental y comparativo, orientado a tomar decisiones reales de desarrollo.

## Lo que debes hacer

Estructura tu respuesta en estas secciones:

### 1. Definición del problema

Explica qué hace difícil o fácil segmentar piel de cebolla como problema de visión computacional. Considera:

- Bordes celulares (grosor, continuidad, contraste)
- Homogeneidad interna de las células
- Células tocándose o compartiendo pared
- Variaciones de iluminación y viñeteo del microscopio
- Posibilidad de núcleos visibles según la preparación
- Comparación con otros tipos celulares más estudiados

### 2. Modelos base a evaluar

Propón una evaluación comparativa entre estos enfoques:

- OpenCV clásico: threshold + contornos
- Watershed con marcadores
- Cellpose cyto3 (modelo generalista)
- Cellpose nuclei (si aplica según la preparación)
- StarDist (si las células son convexas)
- Fine-tuning de Cellpose con imágenes propias
- Cualquier otro enfoque razonable que aporte valor

Para cada uno indica:
- Si sirve como baseline o como candidato serio
- Si requiere dataset anotado propio
- Qué ventajas tiene específicamente para piel de cebolla
- Qué limitaciones tiene
- Viabilidad para deployment en Raspberry Pi

### 3. Datasets de referencia y estrategia de arranque

Propón una estrategia para no entrenar desde cero:

- Qué datasets tipo BBBC o similares pueden servir como base
- Cómo combinar datos externos con imágenes propias
- Cuánto debería anotar al inicio para un fine-tuning útil (número concreto)
- Qué formato de anotación conviene para máscaras de instancia
- Herramientas de anotación recomendadas (CVAT, Cellpose GUI, Label Studio)

### 4. Pipeline experimental completo

Diseña el pipeline en etapas con entradas, salidas y criterios de avance:

- Adquisición y organización del dataset
- Anotación mínima viable
- Preprocesamiento (CLAHE, denoise, normalización)
- Evaluación de modelos base (sin entrenar)
- Análisis de errores (dónde falla cada modelo)
- Selección del mejor enfoque
- Fine-tuning con datos propios
- Exportación a ONNX para Raspberry Pi
- Benchmarking de latencia y memoria en edge

### 5. Métricas de evaluación

Define las métricas cuantitativas y cualitativas:

**Cuantitativas:**
- IoU (Intersection over Union)
- Dice score
- F1 por instancia
- Precisión y recall
- Error en conteo de células
- Error en área y perímetro medio

**De rendimiento:**
- Tiempo por imagen (PC y Raspberry Pi)
- Uso de memoria RAM
- Tamaño del modelo (MB)

**De robustez:**
- Rendimiento con ruido agregado
- Rendimiento con blur artificial
- Rendimiento con contraste reducido
- Estabilidad entre imágenes similares

### 6. Características visuales importantes para rescatar

Identifica explícitamente cuáles son las características que un modelo debe aprender en piel de cebolla:

- Continuidad del borde celular
- Contraste entre pared celular y citoplasma
- Regularidad geométrica (células rectangulares/elongadas)
- Grosor aparente del borde
- Separación entre células contiguas
- Sensibilidad a blur o iluminación desigual

Para cada una, explica:
- Por qué importa para la segmentación
- Cómo detectar si realmente está influyendo en el rendimiento
- Cómo preservarla durante el preprocesamiento

### 7. Tablas comparativas

Genera estas tablas:

**Tabla 1 — Comparación de modelos:**
| Modelo | Tipo | Dataset requerido | Fortaleza | Debilidad | IoU esperado | Viable RPi |

**Tabla 2 — Características visuales:**
| Rasgo | Importancia | Evidencia en resultados | Preservar en preproceso |

**Tabla 3 — Recomendación por escenario:**
| Escenario | Modelo recomendado | Motivo | Latencia esperada |

### 8. Recomendación final

Concluye con:

- Qué modelo probar primero y por qué
- Cuál debe ser el baseline de referencia
- En qué momento vale la pena hacer fine-tuning (criterio concreto)
- Camino más realista para terminar con modelo propio en Raspberry Pi
- Qué evitar (errores comunes en este tipo de proyectos)

---

## Prompt de seguimiento (copiar después del primer análisis)

> Ahora toma la recomendación anterior y conviértela en un plan de implementación de 4 fases:
>
> **Fase 1:** Baseline clásico (OpenCV)
> **Fase 2:** Evaluación con modelos preentrenados (Cellpose, StarDist)
> **Fase 3:** Fine-tuning con imágenes de piel de cebolla
> **Fase 4:** Exportación y evaluación en Raspberry Pi
>
> Para cada fase dame:
> - Objetivo concreto
> - Entradas requeridas
> - Herramientas y comandos
> - Salida esperada
> - Criterio para pasar a la siguiente fase
> - Código Python de ejemplo para el paso clave

## Estilo de respuesta

Respuesta técnica, detallada, estructurada y orientada a ejecución real de proyecto. Incluir tablas, pseudocódigo, criterios de decisión y recomendaciones concretas. No teoría genérica.
