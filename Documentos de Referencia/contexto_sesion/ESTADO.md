# Estado del proyecto (snapshot)

Ultima actualizacion: 2026-05-06.

## TRL actual: 3 -> 4 (en transicion)

Ya tenemos **proof-of-concept en lab** (TRL 3). Para llegar a **TRL 4
(componentes integrados en lab)** falta el experimento de mascaras
integrado, las **mediciones energeticas reales** y la validacion de
metricas de rendimiento.

## TAREA ACTUAL EN CURSO: pruebas energeticas

El equipo esta arrancando la **medicion real del presupuesto energetico**
del payload. Hay dos caminos paralelos:

### Camino A: medicion con multimetro (sin hardware extra)

Protocolo descrito en el Capitulo "Limitaciones y trabajo futuro" del
`Informe_Mascaras_Lensless.pdf` y en el chat de session anterior:

1. Multimetro en SERIE en el rail 5V que va a la Pi.
2. Forzar cada fase (IDLE / CAPTURING / PROCESSING / DOWNLINK / SAFE)
   por al menos 30--60 s para tener lecturas estables.
3. Usar boton MAX HOLD si el multimetro lo tiene.
4. Anotar resultados en la **Hoja 5 "Mediciones_reales"** del archivo
   `Documentos de Referencia/Energy_Budget_Microscopia.xlsx`.

### Camino B: medicion con INA219 (preciso, automatizado)

Hardware: sensor I2C INA219 (~5 USD en Mouser/Adafruit) entre el rail 5V
y la Pi. Software: `tools/power_profiler.py` ya implementado.

```bash
# Idle
python tools/power_profiler.py --duration 600 --phase idle --output idle.csv --plot

# Scan completo
python tools/power_profiler.py --duration 90 --phase full_scan --output scan.csv --plot
# (en otra terminal lanzar el scan)
python -m cubesat.daemon --capture --tag energy_test
```

### Estado de la tarea energetica

- [x] Planilla xlsx con presupuesto teorico (Energy_Budget_Microscopia.xlsx)
- [x] Script `tools/power_profiler.py` para INA219
- [x] Protocolo de multimetro documentado
- [ ] Compra del INA219 (si se elige camino B)
- [ ] Mediciones reales en banco
- [ ] Llenado de la hoja 5 con valores medidos
- [ ] Comparacion estimado vs real, ajuste de parametros

## Hecho en sesiones anteriores

### Software
- Daemon completo en RPi: `cubesat/` con 13 archivos (1164 lineas)
- 3 servicios systemd (pipeline, i2c-slave, telemetry)
- Protocolo I2C: 14 comandos, chunked responses
- OTA via git fetch + checkout + rollback
- Pipeline IA: clasificacion, calibracion, mejora (N2V/CARE), segmentacion
  (StarDist/Cellpose/OpenCV), medicion, exportacion
- GUI tk

### Hardware (CAD)
- 3 mascaras opticas medidas en Inventor:
  - Pinhole circular Ø 3.000 mm
  - Apertura cuadrada 3.054 mm
  - Rendija (slit) 0.178 x 5.606 mm
- 3 housings (camaras), profundidad h = 5.0 mm

### Documentacion (PDFs en `Documentos de Referencia/`)
- `Curso_Vision_Computadora.pdf` --- libro 81 paginas
- `Pipeline_IA_Microscopia.pdf` --- 13 paginas
- `Plan_CubeSat_RPi.md` --- plan integracion al INTISAT
- `Informe_Mascaras_Lensless.pdf` --- 21 paginas, formal IMRyD
- `Guion_Mascaras_Lensless.pdf` --- 25 paginas con narrativa
- `Presentacion_Mascaras_Lensless.pptx` --- 14 slides
- `Energy_Budget_Microscopia.xlsx` --- planilla energetica (5 hojas)
- `Bibliografia_AI_Espacial.pdf` --- 18 paginas, IA en espacio
- `Raspberry_Pi_5_Profundo.pdf` --- 25 paginas, profundidad tecnica RPi 5
- `Guia_Empleo_Industrial_Mineria.pdf` --- 25 paginas (no aplica a la Pi, es de carrera)
- `cubesat/ARCHITECTURE.md` + `architecture.html` --- 6 diagramas Mermaid

### Diagramas en `out/`
- `aperture_masks_assembly.png` --- 3 modos de ensamblaje
- `aperture_masks_gallery.png` --- 8 mascaras opticas tipicas
- `modes_comparison_table.png` --- tabla comparativa A/B/C
- `tareas_microscopia.png` --- slide de tareas con barras

### Tools en `tools/`
- `tune_onion.py` --- tuner interactivo de segmentacion
- `aperture_patterns.py` --- patrones para el OLED (FPM, DPC, etc.)
- `aperture_masks.py` --- generador de SVG/STL + galeria de mascaras
- `modes_comparison_table.py` --- regenera la tabla A/B/C
- `tareas_microscopia_slide.py` --- regenera el slide de tareas
- `build_apertures_presentation.py` --- regenera la PPTX
- `build_energy_budget_xlsx.py` --- regenera la planilla de energia
- **`power_profiler.py`** --- logger INA219 (lo nuevo)

## Pendientes ordenados por urgencia

### En curso (esta semana)
a) **Pruebas energeticas reales** (lo descrito arriba)
b) Imprimir las 3 mascaras + 3 housings (PLA negro mate)
c) Calibrar um/px con regleta en cada modo (A, B, C)
d) Capturar las 9 condiciones x 3 repeticiones = 27 imagenes

### Bug critico (no resuelto)
En `pipeline/controller.py:184-203`, las segmentaciones IA (Cellpose / StarDist)
NO se miden porque el dict que se pasa a `measure_cells` no incluye la key
`"contours"`. Solo trae `"labels"` y `"overlay"`.

`measure_cells` lee unicamente `"contours"`, asi que aunque Cellpose detecte
200 celulas, el CSV final sale vacio.

**Fix de ~10 minutos**: extraer contornos de `labels` con `cv2.findContours`
en cada label y agregarlos al dict de seg.

### Cuando lleguen los componentes
e) INA219: medicion fina de potencia (camino B descrito arriba)
f) MCP2515: implementar CAN_1 como backup de I2C_2

### Pre-vuelo (mas adelante)
g) Migracion a Compute Module 5 con eMMC
h) Burn-in 8 horas de scans continuos
i) Test termico (-10 a +50 C minimo)
j) Test de vibracion 3 g RMS
k) Validacion de metricas (resolucion con carta USAF-1951, repetibilidad)

## Decisiones recientes

- **h = 5 mm**: profundidad real medida del housing impreso (CAD).
- **Mascara default para uso general**: hipotesis actual es la cuadrada
  (3.054 mm, mas area = mas luz).
- **Hardware de vuelo**: migrar a CM5 con eMMC, NO a Toradex / industrial
  por ahora (presupuesto + complejidad).
- **Edge AI hardware referencia**: Movidius Myriad / Hailo-8 si se decide
  acelerar; Jetson Orin Nano si se necesita salto grande. Pero por ahora
  el Pi 5/CM5 es suficiente.
