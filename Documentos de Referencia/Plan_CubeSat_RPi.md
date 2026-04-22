# Plan de Integracion CubeSat -- Payload Microscopia (RPi 5)

Documento de planificacion para integrar la payload de microscopia (Raspberry Pi 5 + sensor lensless + OLED) en el bus INTISAT via conector PC-104.

Basado en: `INTISAT_PC-104_pinout.xlsx` (hoja `INTISATv1`).

---

## 1. Recursos disponibles en el bus PC-104

El conector PC-104 tiene 2 cabezales (H1 y H2) con 52 pines cada uno (104 total).

### 1.1 Energia (lo que el EPS entrega)

| Riel | Corriente max | Potencia max | Uso recomendado | Pines (H1/H2) |
|---|---|---|---|---|
| `5V_PAYLOAD` | 3 A x 2 pines = 6 A pico | 30 W | **RPi 5 + sensor + OLED** | H1.45, H1.46, H2.25, H2.26 |
| `5V_PSW0` | 2.5 A | 12.5 W | Reserva (UHF beacon ya lo usa) | H1.51, H1.52 |
| `5V_PSW1` | 2.5 A | 12.5 W | Reserva | H1.49, H1.50 |
| `5V_PSW2` | 2.5 A | 12.5 W | Reserva | H2.47, H2.48 |
| `5V_PSW3` | 2.5 A | 12.5 W | Reserva | H1.47, H1.48 |
| `3V3_OBDH` | -- | -- | Logica OBC (no payload) | H1.43, H1.44 |
| `3V3_PSW0` | 1 A | 3.3 W | OLED logica (si se necesita 3V3) | H2.35, H2.36 |
| `3V3_PSW1` | 1 A | 3.3 W | Reserva | H2.1, H2.2 |
| `VBUS` | -- | -- | Bateria directa, NO usar para RPi | H2.11, H2.12, H2.45, H2.46 |
| `GND/DGND` | -- | -- | Comun | H1.29-34, H2.29-32 |

**Decision**: La RPi 5 va alimentada por `5V_PAYLOAD` (6 A combinados, suficiente para RPi 5 que pide ~3 A pico). Los 5V_PSW dejarlos como reserva conmutable por EPS.

### 1.2 Buses de datos disponibles para la payload

| Bus | Pines (H1) | Velocidad tipica | Quien mas lo usa | Recomendacion |
|---|---|---|---|---|
| `I2C_1` (sistema) | H1.41 SDA, H1.42 SCL | 100-400 kHz | EPS, OBC, UHF, S-Band | **NO usar** (saturado por housekeeping) |
| `I2C_2` | H1.21 SCL, H1.23 SDA | 100-400 kHz | OBC + S-Band | **Aqui va la RPi** |
| `SPI_1` | H1.9-12 (CS1, MOSI, CLK, MISO) | 1-50 MHz | OBC ↔ S-Band/UHF | Reservado |
| `SPI_2` | H2.13-17 | 1-50 MHz | Solo OBC | Disponible si se necesita transferencia rapida |
| `SPI_3` | H1.10, 11, 12, 14 (comparte fisico con SPI_1) | 1-50 MHz | UHF | Reservado |
| `UART_1` | H1.13 TX, H1.15 RX | 115200 typ | OBC ↔ S-Band | Reservado |
| `UART_2` | H1.6 TX, H1.8 RX | 115200 typ | OBC ↔ S-Band (FPGA) | Reservado |
| `UART_3` | H2.3 TX, H2.4 RX | 115200 typ | OBC libre | Disponible para debug |
| `UART_4` | H2.6 TX, H2.8 RX | 115200 typ | OBC ↔ UHF | Reservado |
| `CAN_1` / `CAN_2` | H1.1-4 | 1 Mbps | OBC ↔ UHF/S-Band | Posible alternativa |

### 1.3 Senales de control y telemetria

| Senal | Pin | Funcion | Uso para payload |
|---|---|---|---|
| `CPU_WD_1` | H2.39 | Watchdog del OBC | Para sincronizar nuestro watchdog |
| `CPU_MODE` | H2.40 | Modo del OBC | Leer para saber si OBC esta en modo SAFE |
| `GLO_FAULT` | H2.38 | Fault del LDO global | Monitorear alimentacion |
| `GLO_SYNC` | H2.37 | Sync del LDO | Monitorear |

---

## 2. Asignacion para la payload de microscopia

### 2.1 Conexiones electricas RPi 5 ↔ PC-104

```
┌──────────────────┐           ┌─────────────────────┐
│   PC-104 (EPS)   │           │   Raspberry Pi 5    │
│                  │           │   (40-pin header)   │
│ H1.45/46 5V_PAY ─┼──────────►│ Pin 2/4  (5V IN)    │
│ H2.25/26 5V_PAY ─┘           │                     │
│                              │                     │
│ H1.29-34 GND ────┼───────────┤ Pin 6/9/14/...(GND) │
│                              │                     │
│ H1.21 I2C_2_SCL ─┼──[3V3 LS]►│ Pin 5  (GPIO3/SCL1) │
│ H1.23 I2C_2_SDA ─┼──[3V3 LS]►│ Pin 3  (GPIO2/SDA1) │
│                              │                     │
│ H2.3 UART_3_TX ──┼──[3V3 LS]►│ Pin 10 (GPIO15/RX0) │
│ H2.4 UART_3_RX ◄─┼──[3V3 LS]─┤ Pin 8  (GPIO14/TX0) │
│                              │                     │
│ H2.39 CPU_WD_1 ──┼──[3V3 LS]►│ Pin 11 (GPIO17 IN)  │ ← leemos heartbeat OBC
│ H2.40 CPU_MODE ──┼──[3V3 LS]►│ Pin 13 (GPIO27 IN)  │ ← detectamos SAFE mode
│                              │                     │
│ H1.16 GPIO_1_1 ◄─┼──[3V3 LS]─┤ Pin 16 (GPIO23 OUT) │ → senal "payload busy"
│ H1.17 GPIO_1_2 ◄─┼──[3V3 LS]─┤ Pin 18 (GPIO24 OUT) │ → senal "payload error"
└──────────────────┘           └─────────────────────┘
                                       │
                                       ├─ Sensor lensless (CSI o USB)
                                       ├─ OLED display (SPI dedicado, GPIO 19/21/23)
                                       └─ MicroSD (almacenamiento)
```

**LS = Level Shifter** (TXS0108E o similar). Necesario porque PC-104 INTISAT puede operar a 3.3V o 5V segun la linea — verificar con osciloscopio antes de conectar. La RPi 5 tiene GPIO a 3.3V estricto (no tolerante a 5V).

### 2.2 Protocolo de comunicacion RPi ↔ OBC

**Capa fisica**: I2C_2 (RPi como esclavo, OBC como maestro) + UART_3 (debug/comandos extensos)

**Por que I2C_2 y no I2C_1**:
- I2C_1 es el bus de housekeeping del sistema (EPS reporta voltajes, UHF reporta temperatura, etc). Anadir trafico de payload puede colisionar.
- I2C_2 esta libre entre OBC y S-Band, podemos co-existir como nodo extra.

**Esquema de mensajes**:

```
OBC (maestro) ──I2C── RPi (esclavo en addr 0x42)

Comandos OBC → Payload:
  0x01 GET_STATUS         → responde 4 bytes: estado, n_imgs_pendientes, temp, RAM%
  0x02 START_CAPTURE      → arranca scan FPM
  0x03 STOP               → cancela scan en curso
  0x04 GET_LAST_RESULT    → responde JSON pequeno (≤256 bytes) con resumen
  0x05 GET_TELEMETRY      → JSON completo
  0x10 SAFE_MODE          → suspende todo, baja consumo
  0x11 RESUME             → vuelve a operar
  0x20 OTA_PREPARE        → recibe trigger para actualizar codigo desde GitHub mirror

Eventos Payload → OBC (via GPIO_1_1 + I2C poll):
  GPIO_1_1 alto = payload procesando (no interrumpir)
  GPIO_1_2 alto = error detectado (OBC debe leer status)
```

**Por que I2C como esclavo**: El OBC es el orquestador del satelite. La payload no decide cuando hablar; espera comandos.

**Para datos grandes** (overlays, JSON resumen): comprimir a `.tar.gz` y entregar por SPI_2 cuando OBC lo solicite (modo burst). I2C es solo para control.

---

## 3. Bill of Materials (componentes minimos)

| Item | Cantidad | Notas |
|---|---|---|
| Raspberry Pi 5 (8 GB) | 1 | Procesador principal payload |
| MicroSD industrial 64 GB (A2 class) | 1 | OS + repo + cache de imagenes |
| Modulo PC-104 adaptador | 1 | Conector 2x52 pines a header RPi |
| Level shifter TXS0108E (8-bit, bidireccional) | 2 | Para I2C, UART y GPIOs |
| Sensor de imagen lensless | 1 | Tipo OmniVision OV5647 sin lente o sensor industrial |
| Pantalla OLED 128x128 SPI | 1 | Iluminacion programable para FPM |
| LDO 5V→3.3V (1A) | 1 | Si OLED necesita 3.3V dedicado |
| Disipador pasivo + heatsink RPi | 1 | Termal critico en vacio |
| Cable plano FFC para CSI | 1 | Conexion sensor a RPi |

---

## 4. Arquitectura software en la RPi

```
                    ┌─────────────────────────────────────┐
                    │          Raspberry Pi 5             │
                    │       (Raspberry Pi OS 64-bit)      │
                    └─────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────────────┐           ┌──────────────────┐         ┌──────────────────┐
│  systemd      │           │  cubesat-       │         │  cubesat-i2c-    │
│  WatchdogSec  │◄──pulses──┤  pipeline       │         │  slave           │
│  =600s        │           │  .service       │         │  .service        │
└───────────────┘           └──────────────────┘         └──────────────────┘
                                      │                             ▲
                                      │ inotify                     │ comandos OBC
                                      ▼                             │
                            ┌──────────────────┐                    │
                            │ /var/cubesat/    │                    │
                            │ incoming/        │                    │
                            │   scan_<UTC>/    │                    │
                            └──────────────────┘                    │
                                      │                             │
                                      ▼                             │
                            ┌──────────────────┐                    │
                            │ pipeline.        │                    │
                            │ controller       │                    │
                            │ (existente)      │                    │
                            └──────────────────┘                    │
                                      │                             │
                                      ▼                             │
                            ┌──────────────────┐                    │
                            │ /var/cubesat/    │                    │
                            │ results/         ├────────────────────┘
                            │   scan_<UTC>/    │   GET_LAST_RESULT
                            │     summary.json │   GET_TELEMETRY
                            │     overlay.jpg  │
                            └──────────────────┘
```

**Servicios systemd** que correran en el RPi:

| Servicio | Funcion |
|---|---|
| `cubesat-pipeline.service` | Watcher inotify + procesador de scans (re-usa `pipeline/controller.py`) |
| `cubesat-i2c-slave.service` | Escucha I2C_2 como esclavo en addr 0x42, responde comandos OBC |
| `cubesat-telemetry.service` | Cada 30s escribe `telemetry.json` con CPU/RAM/temp/disk/n_scans |
| `cubesat-ota.service` | Triggered por OBC: hace `git pull` desde GitHub mirror y `systemctl restart` |

---

## 5. Control remoto via GitHub (OTA updates)

Para poder actualizar el codigo desde tierra sin acceso fisico a la RPi:

### 5.1 Flujo OTA

```
[Estacion en tierra]
        │
        │  git push origin main
        ▼
[GitHub: JaminYC/CubeSat-EdgeAI-Payload]
        │
        │  webhook → estacion ground
        │  ground → uplink (S-Band)
        ▼
[OBC: recibe comando OTA_PREPARE + commit_hash]
        │
        │  I2C_2 → 0x20 OTA_PREPARE <hash>
        ▼
[RPi: cubesat-ota.service]
        │
        │  systemctl stop cubesat-pipeline
        │  cd /opt/cubesat && git fetch && git checkout <hash>
        │  pip install -r requirements_pipeline.txt
        │  systemctl start cubesat-pipeline
        │
        │  GPIO_1_2 = 0 (sin error)  o  1 (error → OBC notifica)
        ▼
[OBC: lee status post-OTA, reporta a tierra via S-Band downlink]
```

### 5.2 Requisitos del repo

- **Branch protegido**: `main` solo se actualiza con PR aprobada (evita pushear bug accidental al satelite).
- **Tag de release**: `vX.Y.Z` para cada version desplegable. La RPi solo hace checkout de tags, nunca de branches sueltas.
- **CI que valide en RPi emulada** (qemu-arm64) antes de permitir merge.
- **Mirror local en RPi**: clonar como `--depth=10` para minimizar bandwidth de uplink.

### 5.3 Claude Code corriendo en la RPi

Si quieres tener Claude Code en la RPi para diagnostico interactivo desde tierra:

| Componente | Razon |
|---|---|
| Claude Code CLI ARM64 | Disponible para Linux ARM, instala con script oficial |
| Tunel SSH reverse via S-Band | RPi inicia tunel hacia ground server cuando hay ventana de comunicacion |
| Sandbox mode obligatorio | Evita que Claude rompa el sistema sin pedir permiso |
| `--dangerously-skip-permissions=NO` | Importante: permisos manuales explicitos en cada accion |

**Realismo**: el ancho de banda de un CubeSat S-Band es 100kbps-1Mbps. Claude Code interactivo en vivo es marginal. **Mejor opcion**: Claude Code corre en tierra, opera sobre el repo, y los cambios se propagan al satelite via OTA por el flujo de arriba.

---

## 6. Tareas pendientes (orden sugerido)

| # | Tarea | Complejidad | Bloqueante de |
|---|---|---|---|
| 1 | Validar voltajes reales del PC-104 con osciloscopio | Baja | Todo (no quemar la RPi) |
| 2 | Disenar PCB adaptador PC-104 → header RPi 40 pines | Media | Integracion fisica |
| 3 | Implementar `cubesat_daemon.py` (inotify + pipeline trigger) | Media | Operacion autonoma |
| 4 | Implementar `cubesat_i2c_slave.py` (responde comandos OBC) | Media | Comunicacion con OBC |
| 5 | Definir formato `telemetry.json` y `summary.json` | Baja | Downlink |
| 6 | Crear servicios systemd + script de instalacion | Baja | Despliegue |
| 7 | Implementar OTA via git + script de rollback | Media | Updates en orbita |
| 8 | Tests de termo-vacio (TVAC) con la payload completa | Alta | Validacion final |

---

## 7. Decisiones que necesito de ti

Antes de empezar a escribir codigo:

1. **Modelo de sensor**: confirmaste lensless con OLED, pero hay que decidir el chip exacto (afecta el driver y la interfaz: CSI-2 vs USB vs SPI).
2. **Direccion I2C de la payload**: propongo `0x42`. Verificar que no colisione con devices existentes en I2C_2 del satelite.
3. **Frecuencia de captura**: cada cuanto el OBC dispara una captura? (1 vez por orbita, cada N min, etc.)
4. **Tamano de imagen post-procesamiento para downlink**: el JPG overlay para enviar a tierra debe pesar ≤200KB? ≤50KB?
5. **Que datos son criticos para downlink**: solo `summary.json` (estadisticas)? + thumbnail? + un overlay completo por captura?

---

*Documento generado para integracion CubeSat INTISAT. Abril 2026.*
