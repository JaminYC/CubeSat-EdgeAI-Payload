# Estado del proyecto (snapshot)

Ultima actualizacion: ver `git log -1 --format=%ci -- Documentos\ de\ Referencia/contexto_sesion/`

## TRL actual: 3 -> 4 (en transicion)

Ya tenemos **proof-of-concept en lab** (TRL 3). Para llegar a **TRL 4
(componentes integrados en lab)** falta el experimento de mascaras integrado
y la validacion de metricas de rendimiento.

## Hecho

### Software
- Daemon completo en RPi: `cubesat/` con 13 archivos (1164 lineas)
- 3 servicios systemd configurados (pipeline, i2c-slave, telemetry)
- Protocolo I2C completo: 14 comandos, chunked responses para payloads grandes
- OTA via git fetch + checkout + rollback automatico
- Pipeline IA: clasificacion, calibracion, mejora (N2V/CARE), segmentacion
  (StarDist/Cellpose/OpenCV), medicion, exportacion
- GUI tk para visualizacion y debug

### Hardware (CAD)
- 3 mascaras disenadas y medidas en Inventor:
  - Pinhole circular Ø $3.000$ mm
  - Apertura cuadrada $3.054$ mm
  - Rendija (slit) $0.178 \times 5.606$ mm
- 3 housings (camaras) impresion 3D, profundidad $h = 5.0$ mm

### Documentacion
- `Curso_Vision_Computadora.pdf` - libro 81 paginas (de pixeles a foundation models)
- `Pipeline_IA_Microscopia.pdf` - 13 paginas
- `Plan_CubeSat_RPi.md` - plan integracion al INTISAT
- `Informe_Mascaras_Lensless.pdf` - 21 paginas, formal IMRyD
- `Guion_Mascaras_Lensless.pdf` - 25 paginas con narrativa
- `Presentacion_Mascaras_Lensless.pptx` - 14 slides template INTISAT
- `Energy_Budget_Microscopia.xlsx` - planilla de presupuesto energetico
- `cubesat/ARCHITECTURE.md` + `architecture.html` - 6 diagramas Mermaid

### Diagramas / imagenes
- `out/aperture_masks_assembly.png` - 3 modos de ensamblaje
- `out/aperture_masks_gallery.png` - 8 mascaras opticas tipicas
- `out/modes_comparison_table.png` - tabla comparativa A/B/C
- `out/tareas_microscopia.png` - slide de tareas con barras de progreso

## En progreso

| Tarea | Estado | Bloqueante |
|---|---|---|
| Tarea 9.1: tiempo de captura | 0% | falta instrumentar `capture.py` |
| Tarea 9.2: analisis energetico | 20% (template xlsx) | falta INA219 + medicion banco |
| Tarea 9.3: canales backup OBC<->RPi | 30% (I2C primario hecho) | falta MCP2515 + `can_slave.py` |
| Tarea 9.4: CAD ensamblaje estructural | 40% (mascaras + housings) | falta frame + slot intercambiable |
| Tarea 9.5: hard reset desde OBC | 30% (soft via I2C ya hecho) | falta linea EPS para power cycling |

## Bug critico identificado (no resuelto)

En `pipeline/controller.py:184-203`, las segmentaciones IA (Cellpose / StarDist)
NO se miden porque el dict que se pasa a `measure_cells` no incluye la key
`"contours"`. Solo trae `"labels"` y `"overlay"`.

`measure_cells` lee unicamente `"contours"`, asi que aunque Cellpose detecte
200 celulas, el CSV final sale **vacio**.

**Fix de ~10 minutos**: extraer contornos de `labels` con `cv2.findContours`
en cada label y agregarlos al dict de seg.

## Pendientes ordenados por urgencia

### Esta semana
a) Imprimir las 3 mascaras + 3 housings (PLA negro mate o aluminio anodizado).
b) Calibrar $\mu$m/px con regleta en cada modo (A, B, C).
c) Capturar las 9 condiciones $\times$ 3 repeticiones = 27 imagenes de cebolla.
d) Fix del bug en `measure_cells` (10 min).

### Cuando lleguen los componentes (INA219, MCP2515)
e) Medir presupuesto energetico real con multimetro o INA219 (ver protocolo en
   `Informe_Mascaras_Lensless.pdf`).
f) Implementar CAN_1 como backup de I2C_2.

### Pre-vuelo
g) Burn-in 8 horas de scans continuos.
h) Test termico (-10 a +50 C minimo).
i) Test de vibracion 3 g RMS.
j) Validacion de metricas (resolucion con carta USAF-1951, repetibilidad,
   estabilidad 24 h).

## Decisiones recientes que pueden cambiar

- **$h = 5$ mm**: viene del CAD pero la pieza fabricada puede tener $\pm 0.1$ mm
  por tolerancia de impresion 3D. Si las primeras capturas dan blur excesivo,
  reducir $h$ a $3$ mm es la primera mitigacion.
- **Mascara default para uso general**: hipotesis actual es la **cuadrada**
  ($3.054$ mm, mas area = mas luz) pero el experimento puede mostrar que
  pinhole gana por mejor PSF predecible.
