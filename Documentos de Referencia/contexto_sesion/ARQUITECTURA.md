# Arquitectura tecnica

## Topologia del sistema

```
[INTISAT bus PC-104]
   |
   |---- 5V_PAYLOAD (6 A) ----> [LDO + fusible] --> RPi 5V
   |                                                     |
   |---- I2C_2 (H1.21/H1.23) -> [TXS0108E shifter] --> GPIO2/GPIO3 (SDA/SCL)
   |
   |---- (futuro) CAN_1 ------> [MCP2515] ----------> SPI RPi (backup)

[RPi 5]
   |
   |---- CSI-2 cable plano FFC --> [OV5647] (SIN LENTE)
   |                                  |
   |                                  ↑ luz
   |                                  ↑
   |                            [muestra biologica]
   |                                  ↑
   |                            [mascara optica]  <-- 3 disenos: slit/cuadrada/circular
   |                                  ↑
   |---- SPI0 + GPIO18/24 -----> [OLED SSD1351 128x128] (iluminacion)
```

## Modos de ensamblaje (cada experimento)

| Modo | Geometria | Caracteristica |
|---|---|---|
| **A) Contact imaging** | muestra apoyada directo en cover glass del sensor | maxima nitidez, sin filtrado angular, sample contamina sensor |
| **B) Lensless con mascara + spacer** | muestra apoyada sobre mascara, separadas del sensor por housing $h=5$ mm | NA controlada, sample no toca sensor |
| **C) Contact + mascara arriba** | muestra en contacto con cover glass, mascara colgada arriba ($h_2 = 4$ mm) | mantiene nitidez de A + control angular de iluminacion (DPC, DF, oblique) |

Ver `out/aperture_masks_assembly.png` y `out/modes_comparison_table.png` para
diagramas e imagenes.

## Software stack en la RPi

```
[OBC] --I2C@0x42--> [pigpiod] <--> [cubesat-i2c-slave.service]
                                          |
                                          | escribe en
                                          v
                                   /run/cubesat/commands/   (cola FIFO)
                                          |
                                          | inotify
                                          v
                                   [cubesat-pipeline.service]  (Type=notify, WDT 600s)
                                          |
                                          v
                                   [FPMCapture] -----> /var/cubesat/incoming/scan_<UTC>/
                                          |                cap_NN.jpg + metadata.json
                                          v
                                   [PipelineController]
                                     |
                                     ├── Real-ESRGAN / N2V / CARE  (mejora)
                                     ├── StarDist / Cellpose       (segmentacion)
                                     └── measurement.py             (metricas)
                                          |
                                          v
                                   /var/cubesat/results/scan_<UTC>/
                                     overlay.png, mask.png, data.csv, summary.json
                                          |
                                          v
                                   /var/cubesat/downlink/scan_<UTC>/
                                     summary.json + thumbnail.jpg + telemetry.json

[cubesat-telemetry.service] -> /run/cubesat/telemetry.json (cada 30 s)
```

Estado compartido:
- `/run/cubesat/` (tmpfs): `status.json`, `telemetry.json`, `commands/`, `lock`
- `/var/cubesat/` (persistente): `incoming/`, `results/`, `downlink/`

## Comandos I2C disponibles (`cubesat/commands.py`)

| Codigo | Comando | Descripcion |
|---|---|---|
| `0x01` | `CMD_GET_STATUS` | 16 bytes: state + RAM + temp + errores |
| `0x02` | `CMD_START_CAPTURE` | dispara FPMCapture (payload: 1 byte modo) |
| `0x03` | `CMD_STOP` | cancela scan en curso |
| `0x04` | `CMD_GET_LAST_SUMMARY` | summary.json chunked |
| `0x05` | `CMD_GET_TELEMETRY` | telemetry.json chunked |
| `0x06` | `CMD_GET_THUMBNAIL` | thumbnail.jpg chunked (~100 KB) |
| `0x07` | `CMD_GET_DATA_CSV` | data.csv chunked (~1 MB) |
| `0x08` | `CMD_LIST_RESULTS` | lista de scans disponibles |
| `0x10` | `CMD_SAFE_MODE` | suspende operacion |
| `0x11` | `CMD_RESUME` | sale de safe mode |
| `0x20` | `CMD_OTA_PREPARE` | prepara update (payload: 40 bytes hash git) |
| `0x21` | `CMD_OTA_COMMIT` | aplica update y reinicia servicios |
| `0x30` | `CMD_REBOOT` | soft reset de la RPi |

Los comandos chicos responden directo con 18 bytes (`[OK, 16, status_struct]`).
Payloads grandes se trocean en frames de **30 bytes** con flag `more=1/0`.

## Maquina de estados del daemon

```
BOOT -> IDLE -> CAPTURING -> PROCESSING -> EXPORTING -> IDLE
         |          |             |             |
         |          v             v             v
         |        ERROR (fallo sensor / IA / disco)
         |          |
         |          v
         |        IDLE (CMD_RESUME)
         |
         |-> SAFE_MODE (CMD_SAFE_MODE)  --> IDLE (CMD_RESUME)
         |
         |-> OTA_IN_PROGRESS (CMD_OTA_COMMIT) --> IDLE / ERROR (rollback)
```

## Calibracion optica

| Magnitud | Valor | Donde |
|---|---|---|
| Pixel pitch OV5647 | $1.4\;\mu$m | hardware |
| Area activa OV5647 | $3.6288 \times 2.7216$ mm | hardware |
| $\mu$m/px efectivo | **$2.66$ por defecto** | `config.yaml` (cambiar tras calibrar) |
| Distancia OLED-sensor | $15$ mm | mecanico (fijo) |
| Profundidad housing $h$ | $5.0$ mm | mecanico (fijo) |
| OLED dot pitch | $0.17$ mm | datasheet SSD1351 |

## Pinout RPi 5 <-> PC-104

| Funcion | RPi BCM | RPi pin header | PC-104 | Componente externo |
|---|---|---|---|---|
| 5V_PAYLOAD | --- | pin 2/4 | H1.41-43 | EPS via fusible PTC + LDO |
| GND | --- | pin 6/9/14/20/25 | H1.47-52 | EPS |
| SDA I2C_2 | GPIO2 | pin 3 | H1.21 | OBC via TXS0108E |
| SCL I2C_2 | GPIO3 | pin 5 | H1.23 | OBC via TXS0108E |
| GND_D | --- | pin 39 | H2.51-52 | OBC referencia |
| MOSI SPI0 | GPIO10 | pin 19 | --- | OLED SSD1351 |
| SCLK SPI0 | GPIO11 | pin 23 | --- | OLED SSD1351 |
| CE0 SPI0 | GPIO8 | pin 24 | --- | OLED SSD1351 |
| OLED DC | GPIO18 | pin 12 | --- | OLED SSD1351 |
| OLED RST | GPIO24 | pin 18 | --- | OLED SSD1351 |
| CSI-2 | --- | conector FFC | --- | OV5647 |

## Archivos clave del repo (orientacion rapida)

| Archivo | Para que |
|---|---|
| `cubesat/daemon.py` | servicio principal --- punto de entrada del daemon |
| `cubesat/i2c_slave.py` | dispatcher de comandos I2C |
| `cubesat/capture.py` | clase `FPMCapture` (25 angulos OLED + snap OV5647) |
| `cubesat/commands.py` | opcodes + struct encoder/decoder de status |
| `pipeline/controller.py` | orquesta el pipeline IA. **Bug en linea 184-203** |
| `pipeline/measurement.py` | calcula area, perimetro, circularidad por celula |
| `pipeline/ai_enhance.py` | wrappers de StarDist/Cellpose/N2V/CARE/Real-ESRGAN |
| `pipeline/segmentation_onion.py` | OpenCV / Cellpose / ONNX segmenters |
| `tools/aperture_masks.py` | genera SVG/STL + galerias de mascaras opticas |
| `tools/tune_onion.py` | tuner interactivo para parametros de segmentacion |
| `tools/power_profiler.py` | logger INA219 para presupuesto energetico |
| `config.yaml` | toda la configuracion del pipeline |
| `Documentos de Referencia/` | docs PDF, presentaciones, planillas, CADs |

## Glosario completo

Ver `CONTEXTO.md` seccion "Glosario rapido" para acronimos. Ademas:

- **Lensless**: microscopia sin lente objetivo. La imagen se forma por
  difraccion + iluminacion. Resolucion limitada por (a) pixel pitch del sensor
  y (b) NA de la apertura.
- **Bright-field**: iluminacion uniforme transmitida (lo que hace tu OLED por defecto).
- **Dark-field**: iluminacion solo desde angulos altos (anillo); solo ves dispersion.
- **DPC** (Differential Phase Contrast): 2-4 capturas con iluminacion
  asimetrica que se restan para revelar gradientes de fase.
- **FPM** (Fourier Ptychography): N capturas con iluminacion puntual desde
  diferentes angulos; cada captura cubre una banda del espectro de Fourier
  del objeto. Reconstruir todas juntas $\to$ super-resolucion sintetica.
- **PSF** (Point Spread Function): respuesta del sistema a una fuente puntual.
  Define la resolucion. Para pinhole circular: disco de Airy. Para cuadrada:
  $\mathrm{sinc}^2 \times \mathrm{sinc}^2$. Para slit: anisotropica.
- **Atomic file pattern**: escribir como `.tmp`, renombrar al final. Garantia
  de que un reboot no deja archivos a medio escribir.
- **Watchdog systemd**: si el servicio no llama `sd_notify("WATCHDOG=1")` en
  N segundos, lo reinicia. Configurado en 600 s para `cubesat-pipeline`.
