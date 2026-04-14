# ESP32 Thermal Logger — Fase 1

Registra perfil térmico de horno con termocupla tipo K (MAX6675) y ESP32.

---

## Conexión de hardware

| MAX6675 | ESP32 |
|---------|-------|
| VCC     | 3.3V  |
| GND     | GND   |
| SCK     | GPIO18|
| CS      | GPIO5 |
| SO      | GPIO19|

> El MAX6675 funciona a 3.3V — no conectar a 5V.

---

## Compilar y subir

```bash
# En la carpeta del proyecto
pio run --target upload

# ESP32 Thermal Logger — Fase 1

Registra perfil térmico de horno con termocupla tipo K (MAX6675) y ESP32.

---

## Conexión de hardware

| MAX6675 | ESP32 |
|---------|-------|
| VCC     | 3.3V  |
| GND     | GND   |
| SCK     | GPIO18|
| CS      | GPIO5 |
| SO      | GPIO19|

> El MAX6675 funciona a 3.3V — no conectar a 5V.

---

## Compilar y subir

```bash
# En la carpeta del proyecto
pio run --target upload

# Abrir monitor serial
pio device monitor
```

---

## Comandos Serial (115200 baud)

| Comando          | Descripción                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `START`          | Inicia el logging CSV                                                       |
| `STOP`           | Detiene el logging y muestra estadísticas                                   |
| `RATE <ms>`      | Cambia periodo (200–5000 ms). Ej: `RATE 1000`                               |
| `MODE RAW`       | Salida: `t_ms,temp_C`                                                       |
| `MODE FILTER`    | Salida: `t_ms,temp_C,temp_C_filtered` (EMA)                                 |
| `OFFSET <C>`     | Calibración por offset. Ej: `OFFSET -2.5`                                  |
| `GAIN <factor>`  | Factor multiplicativo de calibración. Ej: `GAIN 1.02`                       |
| `ALPHA <0-1>`    | Suavizado EMA. Menor = más suave. Ej: `ALPHA 0.05` (default: 0.10)          |
| `SPIKE <C>`      | Umbral anti-spike EMI en °C. Ej: `SPIKE 15` — usa `SPIKE 0` para desactivar|
| `STATS`          | Muestra muestras válidas, spikes rechazados y % de tasa de spike            |
| `RESET`          | Reinicia tiempo base, filtro EMA y contadores de estadísticas               |

Las líneas que empiezan con `#` son comentarios/estado — no son datos CSV.

---

## Formato de salida

**Modo RAW:**
```
t_ms,temp_C
0,24.50
500,25.25
1000,26.00
```

**Modo FILTER:**
```
t_ms,temp_C,temp_C_filtered
0,24.50,24.50
500,25.25,24.58
1000,26.00,24.72
```

**Falla de termocupla:**
```
# WARN t=5000 thermocouple fault
5000,NaN
```

---

## Graficar en tiempo real

### Opción A — Serial Plotter de PlatformIO / Arduino IDE
Abre el Serial Plotter. Solo funciona bien en modo RAW (dos columnas).

### Opción B — Script Python (recomendado)
Ver `tools/log_serial.py`. Guarda CSV y puede graficar con matplotlib.

```bash
pip install pyserial matplotlib
python tools/log_serial.py --port COM4 --output perfil.csv
```

### Opcion C — GUI de experimento (nueva, aditiva)
Interfaz con botones para conectar, iniciar/finalizar experimento, aplicar `MODE`, `RATE`, `OFFSET`,
guardar CSV por sesion y ver ventana de logs.

```bash
pip install pyserial matplotlib
python tools/log_serial_gui.py
```

Flujo sugerido:
1. Seleccionar `Port` y `Baud`.
2. Clic en `Connect`.
3. Definir nombre en `Experiment`.
4. Clic en `Start Experiment`.
5. Al terminar, clic en `Finish Experiment`.

Salida:
- Los CSV se guardan por defecto en `results/YYYY-MM-DD/`.
- Se puede cambiar carpeta con el boton `Output Folder`.

### Empaquetar a EXE (Windows)
Para llevar la GUI a otra laptop sin instalar Python:

```bash
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name thermal_logger_gui tools/log_serial_gui.py
```

Resultado:
- EXE: `dist/thermal_logger_gui.exe`
- Opcional portable: comprimir ese EXE en un `.zip` y copiarlo a la otra PC.

### Instalador completo (Setup.exe)
Instala app + accesos directos + desinstalador.

```bash
winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
powershell -ExecutionPolicy Bypass -File tools/build_installer.ps1
```

Resultado:
- Instalador: `dist/thermal_logger_setup.exe`
- Incluye: app, `README.md`, `DRIVERS.md`.

---

## Colocación de la termocupla en el horno

| Posición                  | Mide                             | Útil para                       |
|---------------------------|----------------------------------|---------------------------------|
| Centro del aire (colgada) | Temperatura de aire real         | Perfil de rampa general         |
| Sobre PCB dummy (cobre)   | Temperatura de masa térmica PCB  | Perfil de soldadura real        |
| Cerca del elemento calef. | Temperatura máxima               | Detectar overshoots             |
| Esquina del horno         | Gradiente espacial               | Uniformidad del horno           |

**Recomendación para soldadura:** coloca la termocupla pegada con cinta kapton sobre una PCB de cobre desnudo del mismo tamaño que tus PCBs de producción.

---

## Parámetros configurables en código

En `src/main.cpp`:

```cpp
static constexpr uint32_t DEFAULT_RATE_MS   = 500;   // periodo inicial
static constexpr float    DEFAULT_EMA_ALPHA = 0.10f; // suavizado (0.05=lento, 0.3=rápido)
static constexpr float    DEFAULT_SPIKE_THR = 15.0f; // umbral anti-spike en °C (0=off)
```

### Guía de parámetros `SPIKE` y `ALPHA`

| Escenario | SPIKE recomendado | ALPHA recomendado |
|---|---|---|
| Horno con elemento resistivo (mucho EMI) | `SPIKE 10` | `ALPHA 0.07` |
| Horno con control por relé | `SPIKE 15` | `ALPHA 0.10` |
| Ambiente sin ruido (validación) | `SPIKE 0` | `ALPHA 0.20` |

> **Nota**: Al cambiar `ALPHA` se reinicia la EMA automáticamente para evitar transiciones bruscas.
