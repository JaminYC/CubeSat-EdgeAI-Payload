# CubeSat Payload — Arquitectura Detallada

Diagramas de bloques del payload de microscopia FPM integrado al bus INTISAT.
Los diagramas estan en [Mermaid](https://mermaid.js.org/): GitHub los renderiza
automaticamente y VS Code los muestra con la extension *Markdown Preview Mermaid Support*.

Indice:
1. [Integracion fisica (hardware)](#1-integracion-fisica-hardware)
2. [Stack de software en la RPi](#2-stack-de-software-en-la-rpi)
3. [Ciclo de vida de un scan](#3-ciclo-de-vida-de-un-scan)
4. [Protocolo I2C (chunking)](#4-protocolo-i2c-chunking)
5. [Maquina de estados](#5-maquina-de-estados)
6. [Flujo OTA](#6-flujo-ota)
7. [Mapeo de pines RPi5 - PC-104](#7-mapeo-de-pines-rpi5--pc-104)

---

## 1. Integracion fisica (hardware)

```mermaid
flowchart LR
    subgraph BUS["INTISAT — PC-104 H1/H2 (104 pines)"]
      EPS["<b>EPS</b><br/>5V_PAYLOAD 6A (H1.41-43)<br/>3V3_OBDH (H1.45-46)<br/>GND_PWR (H1.47-52)"]
      OBC["<b>OBC</b> (I2C master)<br/>SDA_2 → H1.21<br/>SCL_2 → H1.23<br/>GND_D (H2.51-52)"]
      RF["<b>UHF / S-Band</b><br/>telemetria + downlink"]
    end

    subgraph COND["Tarjeta de acondicionamiento"]
      FUSE["Fusible PTC 5A<br/>(reseteable)"]
      LDO["LDO 5V→5V 6A<br/>+ proteccion inrush"]
      TXS["TXS0108E<br/>level shifter I2C<br/>(bidireccional)"]
    end

    subgraph RPI["Raspberry Pi 5 — Payload"]
      RPWR["5V IN<br/>(pin 2/4)"]
      I2C["I2C1<br/>SDA=GPIO2<br/>SCL=GPIO3"]
      SPI["SPI0<br/>MOSI/SCLK/CE0"]
      GPD["GPIO18 DC<br/>GPIO24 RST"]
      CSI["CSI-2<br/>MIPI 2-lane"]
    end

    subgraph SENS["Sensores opticos"]
      CAM["<b>OV5647</b><br/>2592×1944 Bayer<br/>SIN LENTE (lensless)"]
      OLED["<b>SSD1351</b><br/>OLED RGB 128×128<br/>fuente LED matricial"]
    end

    EPS -.->|5V| FUSE
    FUSE --> LDO
    LDO -->|5V filtrado| RPWR
    OBC ==>|SDA/SCL 3V3| TXS
    TXS ==>|SDA/SCL RPi| I2C
    CSI ---|cable FFC| CAM
    SPI --- OLED
    GPD --- OLED

    classDef pwr fill:#fff3b0,stroke:#c58f00,color:#000
    classDef data fill:#c4e1a5,stroke:#4a7a1f,color:#000
    classDef sens fill:#f6c6c6,stroke:#9c3a3a,color:#000
    class EPS,LDO,FUSE,RPWR pwr
    class OBC,TXS,I2C,RF data
    class CAM,OLED,CSI,SPI,GPD sens
```

**Puntos clave**

- **Aislamiento electrico**: el TXS0108E evita que un glitch del bus del OBC llegue directo
  a la GPIO de la Pi (ambos lados operan a 3.3 V pero con tierras referenciadas distintas).
- **Proteccion termica**: el fusible PTC protege contra corto en la payload sin afectar al
  resto del bus — si la Pi consume > 5 A se resetea sola.
- **El CSI-2 NO pasa por PC-104**: la OV5647 se conecta directo a la Pi por cable FFC de 15 pines;
  PC-104 solo lleva alimentacion y comandos.

---

## 2. Stack de software en la RPi

```mermaid
flowchart TB
    subgraph OBCS["OBC (maestro I2C)"]
      OBCAPP["OBC flight software"]
    end

    subgraph KERN["Kernel Linux en RPi 5"]
      PIG["pigpiod<br/>(I2C slave via DMA)"]
      LCAM["libcamera + picamera2"]
      SPIDEV["spidev + GPIO"]
    end

    subgraph SVC["Servicios systemd (cubesat/)"]
      direction LR
      S1["<b>cubesat-i2c-slave</b><br/>Nice=-5, 256MB<br/><code>python -m cubesat.i2c_slave</code>"]
      S2["<b>cubesat-pipeline</b><br/>Type=notify, WDT=600s<br/>2GB, CPUWeight=50<br/><code>python -m cubesat.daemon</code>"]
      S3["<b>cubesat-telemetry</b><br/>Nice=10, 128MB<br/><code>python -m cubesat.telemetry</code>"]
    end

    subgraph STATE["Estado compartido — /run/cubesat (tmpfs)"]
      ST1["status.json"]
      ST2["telemetry.json"]
      ST3["commands/cmd_*.json<br/>(cola FIFO)"]
      ST4["lock"]
    end

    subgraph PIPE["Pipeline IA (pipeline/controller.py)"]
      ENH["Real-ESRGAN / N2V"]
      SEG["StarDist / Cellpose"]
      MET["Metricas<br/>(diam, contraste)"]
    end

    subgraph DATA["Datos persistentes — /var/cubesat/"]
      D1["<b>incoming/</b>scan_UTC/<br/>cap_00..NN.jpg<br/>metadata.json"]
      D2["<b>results/</b>scan_UTC/<br/>overlay.png, mask.png<br/>data.csv, summary.json"]
      D3["<b>downlink/</b>scan_UTC/<br/>summary.json<br/>thumbnail.jpg ~100KB<br/>telemetry.json"]
    end

    OBCAPP ==>|"I2C @ 0x42"| PIG
    PIG <--> S1
    S1 -->|"escribe cmd"| ST3
    S1 -->|"lee estado"| ST1
    S3 -->|"30s snapshot"| ST2
    S2 -->|"inotify"| ST3
    S2 -->|"publica"| ST1
    S2 -->|"libcamera"| LCAM
    S2 -->|"spi+gpio"| SPIDEV
    LCAM --> D1
    SPIDEV -.->|"OLED control"| D1
    S2 -->|"invoca"| ENH
    ENH --> SEG
    SEG --> MET
    MET --> D2
    S2 -->|"empaqueta"| D3

    classDef svc fill:#c4e1a5,stroke:#4a7a1f,color:#000
    classDef state fill:#fff3b0,stroke:#c58f00,color:#000
    classDef data fill:#d4b8ff,stroke:#5a3a9c,color:#000
    class S1,S2,S3 svc
    class ST1,ST2,ST3,ST4 state
    class D1,D2,D3 data
```

**Separacion de responsabilidades**

| Servicio | Toca el bus I2C | Toca sensores | Toca IA | Reinicio si cuelga |
|---|:-:|:-:|:-:|:-:|
| `i2c-slave` | SI | NO | NO | `Restart=always` (3 s) |
| `pipeline` | NO | SI | SI | `WatchdogSec=600` |
| `telemetry` | NO | NO (solo sysfs) | NO | `Restart=always` |

---

## 3. Ciclo de vida de un scan

```mermaid
sequenceDiagram
    autonumber
    participant O as OBC
    participant I as i2c_slave
    participant Q as /run/cubesat/commands
    participant D as daemon
    participant C as FPMCapture
    participant P as Controller IA
    participant B as /var/cubesat

    O->>I: CMD_START_CAPTURE (0x02, mode=1)
    I->>Q: write cmd_UTC.json
    I-->>O: STATUS_OK (ack inmediato)

    D->>Q: inotify IN_CLOSE_WRITE
    D->>D: state = CAPTURING
    D->>C: capture_scan(mode=1)

    loop 25 angulos (5×5 OLED)
        C->>C: actualiza posicion LED OLED
        C->>C: snap OV5647
        C->>B: cap_NN.jpg.tmp → rename (atomico)
    end
    C->>B: metadata.json (atomico)

    D->>D: state = PROCESSING
    D->>P: run(scan_id)
    P->>P: enhance (Real-ESRGAN / N2V)
    P->>P: segment (StarDist)
    P->>P: metricas + CSV
    P->>B: results/scan_UTC/ completo

    D->>D: state = EXPORTING
    D->>B: downlink/scan_UTC/{summary, thumb 640×480, telem}
    D->>D: state = IDLE

    Note over O,I: Mas tarde...
    O->>I: CMD_GET_LAST_SUMMARY (0x04)
    I->>B: lee downlink/scan_UTC/summary.json
    I-->>O: [OK, len, chunk0..N]
```

**Garantias**

- **Atomicidad**: todo archivo se escribe como `.tmp` y se renombra; si la Pi se cuelga
  a mitad de captura, el watcher nunca ve un `cap_NN.jpg` corrupto.
- **Ack inmediato**: el OBC no espera que termine el scan — le contestamos `OK` en < 10 ms
  y encolamos el trabajo. Luego consulta `GET_STATUS` para ver progreso.
- **Watchdog**: si `pipeline.daemon` se cuelga > 600 s sin hacer `sdnotify("WATCHDOG=1")`,
  systemd lo mata y reinicia — y el siguiente arranque re-procesa lo que quedo en `incoming/`.

---

## 4. Protocolo I2C (chunking)

```mermaid
sequenceDiagram
    autonumber
    participant O as OBC
    participant S as i2c_slave @ 0x42

    Note over O,S: Comandos chicos (<= 16 B) → respuesta directa

    O->>S: write [0x01]   <b>CMD_GET_STATUS</b>
    S-->>O: read 18 B<br/>[OK, 16, status_struct]

    Note over O,S: Payloads grandes → chunked (30 B por frame)

    O->>S: write [0x06]   <b>CMD_GET_THUMBNAIL</b>
    S->>S: abre thumbnail.jpg (~100 KB)

    loop Mientras more=1
        O->>S: read 32 B
        S-->>O: [OK, 30, more=1, chunk_30B]
        O->>O: append a buffer
    end
    O->>S: read 32 B
    S-->>O: [OK, N, more=0, last_chunk_N]

    Note over O,S: Errores

    O->>S: write [0x04]  (sin scan previo)
    S-->>O: [NO_DATA, 0]

    O->>S: write [0xFA]  (opcode invalido)
    S-->>O: [UNKNOWN_CMD, 0]

    O->>S: write [0x20, len=40, hash...]   <b>CMD_OTA_PREPARE</b>
    S-->>O: [BUSY, 0]   (si hay scan en curso)
```

**Limites del bus (I2C @ 100 kHz)**

- Comando chico (18 B): ~2 ms
- Thumbnail de 100 KB (3.3 k chunks × 2.8 ms): ~10 s
- `data.csv` de 1 MB: ~100 s — por eso es `on-demand`, no siempre en el downlink

---

## 5. Maquina de estados

```mermaid
stateDiagram-v2
    [*] --> BOOT
    BOOT --> IDLE: boot OK\n(pigpiod + sensores)
    BOOT --> ERROR: fallo inicializacion

    IDLE --> CAPTURING: CMD_START_CAPTURE
    CAPTURING --> PROCESSING: scan completo
    PROCESSING --> EXPORTING: IA OK
    EXPORTING --> IDLE: downlink listo

    CAPTURING --> ERROR: fallo sensor/OLED
    PROCESSING --> ERROR: fallo IA o disco
    EXPORTING --> ERROR: disco lleno

    ERROR --> IDLE: CMD_RESUME\n(tras ver status)
    IDLE --> SAFE_MODE: CMD_SAFE_MODE\no bajo voltaje
    SAFE_MODE --> IDLE: CMD_RESUME

    IDLE --> OTA_IN_PROGRESS: CMD_OTA_COMMIT
    OTA_IN_PROGRESS --> IDLE: checkout + health OK
    OTA_IN_PROGRESS --> ERROR: rollback automatico

    note right of SAFE_MODE
      En SAFE_MODE solo responde
      GET_STATUS y GET_TELEMETRY.
      Ignora START_CAPTURE.
    end note
```

---

## 6. Flujo OTA

```mermaid
flowchart TB
    A["Desarrollo local"] -->|git push main| B["GitHub<br/>JaminYC/CubeSat-EdgeAI-Payload"]
    B -->|"git fetch<br/>en ground station"| C["Ground station"]
    C -->|"uplink S-Band<br/>(hash 40 B)"| D["OBC"]
    D -->|"I2C: CMD_OTA_PREPARE<br/>+ 40 B hash"| E["i2c_slave"]
    E --> F["ota.prepare()<br/>git fetch origin"]
    F --> G{"git cat-file -e hash"}
    G -->|no existe| H["STATUS_ERROR"]
    G -->|existe| I["escribe<br/>/run/cubesat/ota-staging.json"]
    I --> J["OBC: CMD_OTA_COMMIT (0x21)"]
    J --> K["ota.commit()"]
    K --> K1["systemctl stop<br/>cubesat-pipeline<br/>cubesat-i2c-slave"]
    K1 --> K2["git checkout hash"]
    K2 --> K3["pip install -r req"]
    K3 --> K4["systemctl start<br/>servicios"]
    K4 --> L{"health check<br/>(status.json OK<br/>en 30 s)"}
    L -->|si| M["STATUS_OK<br/>+ log commit nuevo"]
    L -->|no| N["rollback"]
    N --> N1["git checkout<br/>prev_commit"]
    N1 --> N2["systemctl start<br/>version vieja"]
    N2 --> H

    classDef ok fill:#c4e1a5,stroke:#4a7a1f,color:#000
    classDef err fill:#f6c6c6,stroke:#9c3a3a,color:#000
    classDef exec fill:#fff3b0,stroke:#c58f00,color:#000
    class A,B,C,D,M ok
    class H err
    class E,F,I,K,K1,K2,K3,K4,L,N,N1,N2 exec
```

**Invariantes del OTA**

- El hash siempre viene **pre-verificado** contra el repo remoto antes de apagar nada.
- Si el health check falla, la payload **vuelve sola** a la version anterior sin intervencion.
- `prev_commit` se guarda en `/var/cubesat/ota-rollback.json` antes del `checkout`.

---

## 7. Mapeo de pines RPi5 — PC-104

| Funcion | RPi 5 (BCM) | RPi 5 (Header) | PC-104 | Componente externo | Nota |
|---|---|---|---|---|---|
| 5V payload | — | pin 2/4 | H1.41-43 | EPS | pasa por LDO + fusible |
| GND potencia | — | pin 6/9/14/20/25 | H1.47-52 | EPS | 6 pines, bajo inrush |
| SDA I2C_2 | GPIO2 | pin 3 | H1.21 | OBC | via TXS0108E |
| SCL I2C_2 | GPIO3 | pin 5 | H1.23 | OBC | via TXS0108E |
| GND datos | — | pin 39 | H2.51-52 | OBC | referencia I2C |
| MOSI SPI0 | GPIO10 | pin 19 | — | OLED SSD1351 | directo |
| SCLK SPI0 | GPIO11 | pin 23 | — | OLED SSD1351 | directo |
| CE0 SPI0 | GPIO8 | pin 24 | — | OLED SSD1351 | directo |
| OLED DC | GPIO18 | pin 12 | — | OLED SSD1351 | data/command |
| OLED RST | GPIO24 | pin 18 | — | OLED SSD1351 | reset activo bajo |
| CSI-2 | — | conector FFC | — | OV5647 | cable plano 15 pines |

**Resumen de lo que NO usa el payload**

- I2C_1 del bus (ya saturado con sensores de sistema)
- UART/CAN (los libera para comms)
- SPI_2/3 del bus (solo usamos SPI0 local de la Pi para el OLED)

---

## Ver tambien

- [`README.md`](README.md) — vista general + instalacion + tabla de comandos
- [`../Documentos de Referencia/Plan_CubeSat_RPi.md`](../Documentos%20de%20Referencia/Plan_CubeSat_RPi.md) — plan de integracion completo
- [`../Documentos de Referencia/Pipeline_IA_Microscopía.pdf`](../Documentos%20de%20Referencia/) — fundamento tecnico del pipeline de IA
