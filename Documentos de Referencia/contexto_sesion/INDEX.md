# Indice de documentos del proyecto

Lista completa de los documentos generados, ordenados por uso. Cuando le pidas
algo a Claude, podes mencionarle directamente la ruta para que lea solo el
necesario.

## Documentos de contexto (este folder)

| Archivo | Tamaño | Para que |
|---|---|---|
| `PROMPT_NUEVA_SESION.md` | corto | el prompt que pegas al iniciar Claude |
| `CONTEXTO.md` | medio | que es el proyecto, decisiones frozen, glosario |
| `ESTADO.md` | medio | snapshot de progreso, bugs, pendientes |
| **`TAREA_ACTUAL.md`** | medio | **lo que se esta haciendo AHORA (medicion energetica)** |
| `ARQUITECTURA.md` | largo | hardware, software, pinout, archivos clave |
| `INDEX.md` | este archivo | mapa de todos los docs del proyecto |

## Documentos tecnicos (PDF)

| Archivo | Paginas | Para que |
|---|---|---|
| `Documentos de Referencia/Pipeline_IA_Microscopia.pdf` | 13 | flujo del pipeline IA |
| `Documentos de Referencia/Curso_Vision_Computadora.pdf` | 81 | libro de teoria CV (cero a vanguardia) |
| `Documentos de Referencia/Informe_Mascaras_Lensless.pdf` | 21 | informe formal IMRyD del experimento |
| `Documentos de Referencia/Guion_Mascaras_Lensless.pdf` | 25 | version narrativa para presentar |
| `Documentos de Referencia/Bibliografia_AI_Espacial.pdf` | 18 | mapa de IA en operaciones espaciales |
| `Documentos de Referencia/Raspberry_Pi_5_Profundo.pdf` | 25 | profundo tecnico del Pi 5 (ver cap. potencia) |
| `Documentos de Referencia/Guia_Empleo_Industrial_Mineria.pdf` | 25 | guia de carrera (no aplica al desarrollo del payload) |

## Documentos de planificacion

| Archivo | Tipo | Para que |
|---|---|---|
| `Documentos de Referencia/Plan_CubeSat_RPi.md` | markdown | plan integracion al INTISAT |
| `Documentos de Referencia/INTISAT_PC-104_pinout.xlsx` | excel | pinout del bus + sheet de payload |
| `Documentos de Referencia/Energy_Budget_Microscopia.xlsx` | excel | presupuesto energetico (5 hojas) |
| `Documentos de Referencia/Presentacion_Mascaras_Lensless.pptx` | powerpoint | 14 slides template INTISAT |

## Modelos CAD (Autodesk Inventor)

| Archivo | Componente |
|---|---|
| `Documentos de Referencia/Muesca Circular.png` | mascara pinhole Ø 3.000 mm |
| `Documentos de Referencia/Muesca Cuadrada.png` | mascara cuadrada 3.054 mm |
| `Documentos de Referencia/Muesca Rejilla.png` | mascara slit 0.178 x 5.606 mm |
| `Documentos de Referencia/Camara Circular.png` | housing pinhole |
| `Documentos de Referencia/Camara Cuadrada.png` | housing cuadrada |
| `Documentos de Referencia/Camara Rejilla.png` | housing slit |
| `Documentos de Referencia/Medida/*.png` | 10 imagenes con dimensiones medidas |

## Diagramas de arquitectura

| Archivo | Para que |
|---|---|
| `cubesat/ARCHITECTURE.md` | 6 diagramas Mermaid (renderiza en GitHub) |
| `cubesat/architecture.html` | HTML auto-renderizado, doble-click y se abre en browser |
| `out/aperture_masks_assembly.png` | 3 modos de ensamblaje A/B/C |
| `out/aperture_masks_gallery.png` | 8 mascaras opticas tipicas |
| `out/modes_comparison_table.png` | tabla A/B/C codificada por color |
| `out/tareas_microscopia.png` | slide de tareas con barras de progreso |

## Codigo (en orden de uso)

### Daemon en la RPi
| Archivo | Funcion |
|---|---|
| `cubesat/__init__.py` | version |
| `cubesat/paths.py` | constantes de paths (/run, /var, /opt) |
| `cubesat/commands.py` | opcodes I2C + status struct |
| `cubesat/capture.py` | FPMCapture (25 angulos + atomic rename) |
| `cubesat/telemetry.py` | snapshots cada 30 s |
| `cubesat/i2c_slave.py` | esclavo I2C en 0x42, dispatch de 14 comandos |
| `cubesat/daemon.py` | servicio principal con watchdog systemd |
| `cubesat/ota.py` | git fetch + checkout + rollback |
| `cubesat/install.sh` | instalador para RPi OS 64-bit |
| `cubesat/systemd/*.service` | 3 unidades systemd |

### Pipeline IA (corre en la Pi y en dev)
| Archivo | Funcion |
|---|---|
| `pipeline/controller.py` | orquestrador. **BUG en lineas 184-203** |
| `pipeline/classifier.py` | clasifica imagenes por nombre |
| `pipeline/calibration.py` | calibra um/px con regleta |
| `pipeline/preprocess.py` | CLAHE, NLM denoise, vignette |
| `pipeline/segmentation_onion.py` | OpenCV / Cellpose / ONNX |
| `pipeline/segmentation_fiber.py` | Hough lines para fibras |
| `pipeline/measurement.py` | metricas por celula y agregadas |
| `pipeline/ai_enhance.py` | StarDist / Cellpose / N2V / CARE wrappers |
| `pipeline/fpm_reconstruction.py` | reconstruccion FPM iterativa |
| `pipeline/export.py` | salida overlay/mask/csv/json |
| `pipeline/gui.py` | interfaz tk para debug |
| `pipeline/manual_calibration.py` | calibracion interactiva con clicks |
| `pipeline/viewer.py` | viewer de resultados |

### Tools de desarrollo
| Archivo | Funcion |
|---|---|
| `tools/tune_onion.py` | tuner interactivo (sliders OpenCV) |
| `tools/aperture_patterns.py` | patrones para el OLED (FPM, DPC, dark field) |
| `tools/aperture_masks.py` | genera SVG/STL + galerias de mascaras fisicas |
| `tools/modes_comparison_table.py` | regenera la tabla A/B/C |
| `tools/tareas_microscopia_slide.py` | regenera el slide de tareas |
| `tools/build_apertures_presentation.py` | regenera la presentacion pptx |
| `tools/build_energy_budget_xlsx.py` | regenera la planilla energetica |
| **`tools/power_profiler.py`** | **logger INA219 para tarea actual de medicion** |

## Configuracion

| Archivo | Que controla |
|---|---|
| `config.yaml` | TODO: paths, calibracion, preprocess, segmentacion, FPM, mode |

## Recursos para nueva sesion

Si vas a abrir Claude Code en este directorio:

1. **Pega `PROMPT_NUEVA_SESION.md`** como mensaje inicial
2. Espera la confirmacion de 6 lineas
3. Recien ahi haces tu pregunta especifica

Si vas a abrir Claude desktop o web (sin Code):

1. Adjunta los 4 archivos: `CONTEXTO.md`, `ESTADO.md`, `ARQUITECTURA.md`, `INDEX.md`
2. Pega el contenido de `PROMPT_NUEVA_SESION.md` como mensaje
3. Eso da el contexto basico sin acceso al codigo (Claude no podra leer
   los `.py` ni ejecutar nada).

## Como mantener este folder vivo

- Cuando hagas un cambio importante: `git diff Documentos\ de\ Referencia/contexto_sesion/`
  y actualiza el archivo correspondiente.
- Si agregas un archivo nuevo al proyecto, agregalo al `INDEX.md`.
- Si cambias una decision frozen, actualizala en `CONTEXTO.md` con la fecha
  del cambio.
- Cada vez que termines una tarea grande, actualiza `ESTADO.md`.
