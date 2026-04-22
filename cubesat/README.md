# CubeSat Payload Daemon

Operacion autonoma de la payload de microscopia en Raspberry Pi 5 integrada al bus INTISAT via PC-104.

## Arquitectura

```
┌─ OBC ─────────┐  I2C_2 @ 0x42  ┌──────────── RPi 5 ────────────┐
│  Maestro I2C  │◄──────────────►│  cubesat-i2c-slave.service    │
│               │                │         │                     │
│               │                │         ▼ escribe en          │
│               │                │    /run/cubesat/commands/     │
│               │                │         │                     │
│               │                │         ▼ watcher             │
│               │                │  cubesat-pipeline.service     │
│               │                │         │                     │
│               │                │         ▼ orquesta            │
│               │                │   FPMCapture (OV5647+OLED)    │
│               │                │   pipeline/controller.py      │
│               │                │   (segmentacion + mediciones) │
│               │                │         │                     │
│               │                │         ▼                     │
│               │                │   /var/cubesat/downlink/      │
│               │                │     scan_<UTC>/               │
│               │                │       summary.json            │
│               │                │       thumbnail.jpg (100KB)   │
│               │                │       telemetry.json          │
└───────────────┘                └───────────────────────────────┘
```

## Servicios systemd

| Servicio | Funcion | Reinicio |
|---|---|---|
| `cubesat-pipeline` | Watcher + controller | `Restart=always`, `WatchdogSec=600` |
| `cubesat-i2c-slave` | Esclavo I2C en 0x42 | `Restart=always` |
| `cubesat-telemetry` | Snapshots cada 30s | `Restart=always` |

## Protocolo I2C (ver `commands.py`)

| CMD | Nombre | Descripcion |
|---|---|---|
| `0x01` | GET_STATUS | 16 bytes con estado + RAM + temp + errores |
| `0x02` | START_CAPTURE | Dispara captura FPM (payload: 1 byte modo) |
| `0x03` | STOP | Cancela scan en curso |
| `0x04` | GET_LAST_SUMMARY | summary.json chunked |
| `0x05` | GET_TELEMETRY | telemetry.json chunked |
| `0x06` | GET_THUMBNAIL | thumbnail.jpg chunked (100KB max) |
| `0x07` | GET_DATA_CSV | data.csv chunked (on-demand) |
| `0x08` | LIST_RESULTS | Lista de scans disponibles |
| `0x10` | SAFE_MODE | Suspende operacion |
| `0x11` | RESUME | Sale de safe mode |
| `0x20` | OTA_PREPARE | Prepara commit (payload: 40 bytes hash) |
| `0x21` | OTA_COMMIT | Aplica update y reinicia |
| `0x30` | REBOOT | Reinicio suave |

## Instalacion en RPi 5

```bash
# 1. Clonar el repo en la Pi
git clone git@github.com:JaminYC/CubeSat-EdgeAI-Payload.git /tmp/repo
cd /tmp/repo

# 2. Ejecutar el instalador
sudo ./cubesat/install.sh

# 3. Verificar
cat /run/cubesat/status.json
sudo i2cdetect -y 1   # debe mostrar 42 en la tabla
journalctl -u cubesat-pipeline -f
```

## Test local desde el OBC (o cualquier maestro I2C)

```python
import smbus
bus = smbus.SMBus(1)
bus.write_byte(0x42, 0x01)   # CMD_GET_STATUS
time.sleep(0.01)
data = bus.read_i2c_block_data(0x42, 0, 18)
# data[0] = STATUS_OK, data[1] = len, data[2:18] = 16 bytes de estado
```

## Directorio de datos

```
/var/cubesat/
├── incoming/         # Scans del sensor (antes de procesar)
│   └── scan_<UTC>/
│       ├── cap_00.jpg  ...  cap_NN.jpg
│       └── metadata.json
├── results/          # Salida del pipeline
│   └── scan_<UTC>/
│       ├── overlay.png
│       ├── mask.png
│       ├── data.csv
│       └── summary.json
└── downlink/         # Empaquetado listo para bajar
    └── scan_<UTC>/
        ├── summary.json
        ├── thumbnail.jpg  (640x480, ~100KB)
        └── telemetry.json
```

## OTA Update

El OBC puede actualizar el codigo remotamente:

1. En tierra: `git push origin main` (idealmente tag `vX.Y.Z`)
2. Ground station → uplink S-Band → OBC recibe hash nuevo
3. OBC ejecuta: `I2C write 0x42 [0x20, 40, <hash_40_bytes>]`
4. RPi hace `git fetch && git cat-file -e <hash>` (valida)
5. OBC confirma: `I2C write 0x42 [0x21]`
6. RPi hace `git checkout <hash>`, reinicia servicios
7. Si falla → rollback automatico al commit anterior
