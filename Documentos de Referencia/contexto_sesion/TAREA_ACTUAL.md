# Tarea actual: pruebas energeticas del payload

Este archivo describe el trabajo INMEDIATO que el equipo esta haciendo,
para que cualquier sesion nueva de Claude (especialmente la que se abra
en la Raspberry Pi) sepa por que esta corriendo el codigo y que datos
se esperan medir.

## Objetivo

Validar el presupuesto energetico teorico del payload contra mediciones
reales en banco. Llenar la **Hoja 5 "Mediciones_reales"** del archivo
`Documentos de Referencia/Energy_Budget_Microscopia.xlsx`.

## Por que importa

- El payload tiene un presupuesto de ~ 1.81 Wh por orbita asumido sobre
  datasheet. Si el real difiere mas del 20%, el dimensionado de bateria
  y rail 5V_PAYLOAD del INTISAT podria estar mal calculado.
- Sin medicion real no podemos pasar de TRL 3 a TRL 4.
- Es un dato que la presentacion al equipo de mision exigira.

## Componentes del payload y su consumo teorico (a verificar)

| Componente | Idle | Activo | Pico |
|---|---|---|---|
| Raspberry Pi 5 (4 GB) | 3.0 W | 5.5 W | 8.0 W |
| OV5647 sensor | 50 mW | 200 mW | 300 mW |
| OLED SSD1351 (50% pixels) | 0 W | 250 mW | 800 mW |
| TXS0108E shifter | 5 mW | 10 mW | 20 mW |
| **Total** | **~ 3.1 W** | **~ 5.9 W** | **~ 9.0 W** |

## Estados del daemon a medir

| Modo | Que hace | t (s) tipico | Notas |
|---|---|---|---|
| **IDLE pre-scan** | espera comando | 5 | sistema arranca aqui |
| **CAPTURING** | barre 25 angulos OLED + snap del sensor | 8 | el OLED se enciende |
| **PROCESSING** | corre IA (StarDist + CLAHE) | 30 | CPU al 100% |
| **DOWNLINK** | envia thumbnail por I2C al OBC | 10 | I2C-bound |
| **IDLE post** | espera proximo comando | 5 | igual a pre |

## Dos caminos de medicion

### Camino A: multimetro (sin hardware extra)

**Setup:**
```
EPS / fuente +5V ─────[A]──── 5V de la RPi
                       ↑
                multimetro EN SERIE
                modo: A DC, escala 10 A
```

**Procedimiento:**

1. Verificar setup con resistencia de 5 ohm: lectura debe ser 1.0 A.
2. Por cada estado, forzar la condicion durante 30-60 s y anotar:
   - Lectura promedio (mA)
   - Lectura pico (con MAX HOLD si esta disponible)
   - Duracion exacta (cronometro)
3. Calcular `E = V * I * t` en cada fase.
4. Cargar en la Hoja 5 del xlsx.

**Como forzar cada estado:**
- IDLE: bootear la Pi y esperar 2 minutos sin tocar nada.
- CAPTURING: encadenar 10 scans con `for i in {1..10}; do python -m cubesat.daemon --capture --tag energy_$i; done`
- PROCESSING: correr `python -m pipeline.controller run --input Imagenes/Variados/ --batch`
- DOWNLINK: en otra Pi/OBC simulado, peticionar 50 thumbnails seguidos via i2cget.
- SAFE: enviar `CMD_SAFE_MODE` (0x10) por I2C, esperar 30 s.

### Camino B: INA219 (preciso, automatizado)

**Hardware necesario:**
- Modulo INA219 con conector I2C (5 USD en Mouser/Adafruit)
- Resistor shunt 0.1 ohm interno

**Conexion:**
```
EPS 5V → INA219 IN+ → INA219 IN− → RPi 5V
                ↓
          I2C al RPi (bus diferente al primario)
```

**Software:** `tools/power_profiler.py` (ya implementado, usa libreria
`adafruit-circuitpython-ina219`).

**Comandos:**
```bash
# Instalar dependencia
sudo pip install adafruit-circuitpython-ina219

# Idle por 10 minutos
python tools/power_profiler.py --duration 600 --phase idle --output idle.csv --plot

# Scan completo (90 s, lanzar el scan en otra terminal)
python tools/power_profiler.py --duration 90 --phase full_scan --output scan.csv --plot
# (en otra terminal)
python -m cubesat.daemon --capture --tag energy_test
```

El script genera CSV con timestamp + voltaje + corriente + potencia, y un
PNG con la grafica.

## Resultado esperado

Una tabla cargada en la Hoja 5 del xlsx con:

| Fase | P media medida (W) | P pico medida (W) | Duracion (s) | E (J) | Diff vs estimado (%) |
|---|---|---|---|---|---|
| IDLE pre-scan | ? | ? | ? | ? | ? |
| CAPTURING | ? | ? | ? | ? | ? |
| PROCESSING | ? | ? | ? | ? | ? |
| DOWNLINK | ? | ? | ? | ? | ? |
| IDLE post | ? | ? | ? | ? | ? |

Con los valores reales se actualiza el presupuesto orbital y se valida
el rail 5V_PAYLOAD del INTISAT.

## Riesgos / cuidados

- **Multimetro en paralelo = corto + fusible quemado.** Siempre en serie.
- **Verificar polaridad** antes de cada conexion.
- **Boot transient** de hasta 2 A durante 3-4 s al arrancar: NO confundir
  con IDLE.
- **Corriente USB** del puerto de teclado/mouse no es la del rail principal.
  Medir solo el cable 5V de la EPS hacia la Pi.
- **Si se cuelga el sistema** durante test: el watchdog systemd reinicia
  pipeline tras 600 s. Es comportamiento esperado.

## Archivos relacionados

- `Documentos de Referencia/Energy_Budget_Microscopia.xlsx` --- la planilla
- `tools/power_profiler.py` --- script INA219
- `Documentos de Referencia/Raspberry_Pi_5_Profundo.pdf` --- capitulo
  "Sistema de potencia" con detalles
- `Documentos de Referencia/Informe_Mascaras_Lensless.pdf` --- contexto
  experimental general

## Despues de esto

Cuando esta tarea termine, las siguientes son:

1. Imprimir mascaras y housings.
2. Calibrar um/px con regleta.
3. Ejecutar las 9 condiciones del experimento de mascaras (3x3 matriz).
4. Procesar con pipeline IA y comparar con predicciones.
5. Escribir RESULTS.md con conclusiones.
