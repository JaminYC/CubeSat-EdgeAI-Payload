# Contexto del proyecto CubeSat-EdgeAI-Payload

## Que es

Payload de **microscopia Fourier Ptychographic (FPM) lensless** para el
satelite **INTISAT**, integrado al bus PC-104 mediante una **Raspberry Pi 5**
que actua como esclavo del OBC (computadora de a bordo del satelite).

**Objetivo cientifico**: capturar imagenes de muestras biologicas (epidermis
de cebolla como modelo) a bordo del satelite, procesarlas autonomamente con
IA (segmentacion de celulas con StarDist), y bajar el resultado al OBC para
downlink terrestre.

**Repositorio**: `github.com/JaminYC/CubeSat-EdgeAI-Payload`

## Hardware

| Componente | Modelo | Funcion |
|---|---|---|
| Computadora payload | **Raspberry Pi 5** (4 GB) | corre el pipeline IA + sirve I2C esclavo |
| Sensor optico | **OmniVision OV5647** | imagen 5 MP, 2592x1944, pixel 1.4 um. **Sin lente.** |
| Iluminacion | **OLED SSD1351 RGB 128x128** | matriz LED programable (FPM) |
| Bus al satelite | **PC-104** (INTISAT) | alimentacion 5V@6A + I2C_2 a OBC |
| Level shifter | **TXS0108E** | aisla 3V3 RPi del 3V3 OBC |

**El sensor NO tiene lente**: la imagen se forma por difraccion + iluminacion
controlada (FPM). La calidad depende criticamente de **mascaras opticas
fisicas** que se montan entre la muestra y el sensor.

## Mascaras opticas (dimensiones reales medidas en CAD Inventor)

| Mascara | Dimension | Para que |
|---|---|---|
| **Pinhole circular** | $\varnothing\,3.000$ mm | referencia metrologica (PSF Airy) |
| **Apertura cuadrada** | $3.054 \times 3.054$ mm | uso general (mas luz, mas FOV) |
| **Rendija (slit)** | $0.178$ mm $\times$ $5.606$ mm | line-scanning, perfilometria |
| **Profundidad housing** | $h = 5.0$ mm | distancia mascara-sensor |

Todas se evaluan en **3 modos de ensamblaje** (A/B/C). Ver `ARQUITECTURA.md`.

## Decisiones frozen (NO relitigar sin razon nueva)

a) **I2C esclavo en 0x42 sobre I2C_2** (H1.21 / H1.23 del PC-104). I2C_1 esta
saturado con sensores de sistema; no usarlo.

b) **Modo reactivo**: la payload NO captura sola; espera comando del OBC.
No hay scheduler interno periodico.

c) **Calidad media en downlink**: thumbnail JPEG 640x480, ~100 KB. El CSV
completo es on-demand (chunked I2C, ~100 s para 1 MB).

d) **OV5647 sin lente** (lensless). NO se va a integrar lente nunca; el
diseño optico depende de las mascaras fisicas + iluminacion OLED.

e) **Pipeline IA con StarDist `2D_versatile_he`**, no `2D_versatile_fluo`
(las imagenes son bright-field, no fluorescencia).

f) **N2V o CARE para denoising**, ambos opcionales, controlables desde GUI.

g) **OTA via git fetch + checkout** con rollback automatico si el health
check falla en 30 s.

h) **Atomic file pattern**: todo archivo se escribe como `.tmp` y se renombra
al final (evita corrupcion ante reboot).

## Componentes de software (resumen)

```
cubesat/                        # daemon en la RPi
├── daemon.py                  # servicio principal, watchdog 600 s
├── i2c_slave.py               # esclavo I2C en 0x42, 14 comandos
├── capture.py                 # FPMCapture: 25 angulos OLED + snap OV5647
├── telemetry.py               # snapshots cada 30 s
├── ota.py                     # update via git con rollback
├── commands.py                # opcodes I2C (CMD_GET_STATUS, CMD_START_CAPTURE, etc.)
└── systemd/                   # 3 servicios systemd

pipeline/                       # pipeline IA (corre en la Pi pero tambien dev local)
├── controller.py              # orquesta clasificacion -> calibracion -> IA -> medicion
├── segmentation_onion.py      # OpenCV / Cellpose / ONNX
├── ai_enhance.py              # Real-ESRGAN / N2V / CARE / StarDist
├── fpm_reconstruction.py      # reconstruccion FPM (multi-angulo)
└── ...

tools/                          # utilidades dev
├── tune_onion.py              # tuner interactivo de segmentacion
├── aperture_patterns.py       # genera patrones para el OLED (FPM, DPC, etc.)
├── aperture_masks.py          # genera SVG/STL de mascaras fisicas + galeria
├── modes_comparison_table.py  # tabla A/B/C
├── tareas_microscopia_slide.py# slide de tareas para presentaciones
├── power_profiler.py          # logger INA219 para presupuesto energetico
└── build_energy_budget_xlsx.py# genera Energy_Budget_Microscopia.xlsx
```

## Glosario rapido

| Sigla | Significado |
|---|---|
| **NA** | Apertura Numerica (cono de aceptacion del sistema). $\mathrm{NA} = D/2h$ |
| **FOV** | Field of View (campo de vision en mm) |
| **FPM** | Fourier Ptychographic Microscopy (super-resolucion por barrido angular) |
| **PSF** | Point Spread Function (respuesta al impulso optico) |
| **OBC** | On-Board Computer (computadora principal del satelite) |
| **EPS** | Electrical Power System (gestion de energia del satelite) |
| **PC-104** | Estandar de bus mecanico/electrico para CubeSats |
| **TVAC** | Thermal Vacuum Cycle (test ambiental criticos para vuelo) |
| **TRL** | Technology Readiness Level (NASA, escala 1-9 de madurez) |
| **DPC** | Differential Phase Contrast (modalidad de microscopia) |
| **SEU/TID** | Single Event Upset / Total Ionizing Dose (efectos de radiacion espacial) |
