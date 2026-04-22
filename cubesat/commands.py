"""
Protocolo I2C entre OBC (maestro) y payload (esclavo 0x42).

Formato de cada transaccion I2C:
    OBC → Payload:  [CMD_ID (1 byte)] [LEN (1 byte)] [PAYLOAD (LEN bytes)]
    Payload → OBC:  [STATUS (1 byte)] [LEN (1 byte)] [DATA (LEN bytes)]

Si una respuesta excede 30 bytes (limite practico I2C por read burst), el OBC
debe hacer lecturas encadenadas via CMD_GET_CHUNK con offset.
"""

# ── Codigos de comando (OBC → Payload) ────────────────────────────────
CMD_GET_STATUS       = 0x01  # No payload. Responde 16 bytes de estado.
CMD_START_CAPTURE    = 0x02  # Payload: 1 byte modo (0=rapido, 1=completo)
CMD_STOP             = 0x03  # No payload. Cancela scan en curso.
CMD_GET_LAST_SUMMARY = 0x04  # Payload: 1 byte offset en chunks de 30B.
CMD_GET_TELEMETRY    = 0x05  # No payload. Responde JSON chunked.
CMD_GET_THUMBNAIL    = 0x06  # Payload: 2 bytes offset (uint16 LE).
CMD_GET_DATA_CSV     = 0x07  # Payload: 2 bytes offset.
CMD_LIST_RESULTS     = 0x08  # No payload. Lista scans disponibles.
CMD_SAFE_MODE        = 0x10  # Suspende captura, baja consumo
CMD_RESUME           = 0x11  # Vuelve a modo operativo
CMD_OTA_PREPARE      = 0x20  # Payload: 40 bytes commit hash (sha)
CMD_OTA_COMMIT       = 0x21  # Confirma y reinicia servicios
CMD_REBOOT           = 0x30  # Reinicio suave de la RPi

# ── Codigos de estado (Payload → OBC) ─────────────────────────────────
STATUS_OK            = 0x00
STATUS_BUSY          = 0x01  # Hay scan en curso
STATUS_NO_DATA       = 0x02  # Aun no hay resultados
STATUS_ERROR         = 0xFF  # Error generico (leer GET_TELEMETRY)
STATUS_UNKNOWN_CMD   = 0xFE

# ── Estados del daemon ────────────────────────────────────────────────
STATE_IDLE          = 0x00
STATE_CAPTURING     = 0x01
STATE_PROCESSING    = 0x02
STATE_EXPORTING     = 0x03
STATE_ERROR         = 0x04
STATE_SAFE_MODE     = 0x05
STATE_OTA_IN_PROGRESS = 0x06

STATE_NAMES = {
    STATE_IDLE:           "idle",
    STATE_CAPTURING:      "capturing",
    STATE_PROCESSING:     "processing",
    STATE_EXPORTING:      "exporting",
    STATE_ERROR:          "error",
    STATE_SAFE_MODE:      "safe_mode",
    STATE_OTA_IN_PROGRESS: "ota_in_progress",
}


def encode_status(state: int, n_pending: int, last_scan_id: int,
                  temp_c: float, ram_pct: int, disk_pct: int,
                  uptime_s: int, errors: int) -> bytes:
    """Serializa estado en 16 bytes para CMD_GET_STATUS."""
    import struct
    return struct.pack(
        "<BBHBBBIHH",
        state & 0xFF,                    # 1 byte  estado
        n_pending & 0xFF,                # 1 byte  scans pendientes
        last_scan_id & 0xFFFF,           # 2 bytes id del ultimo scan
        int(temp_c) & 0xFF,              # 1 byte  temperatura CPU (C)
        ram_pct & 0xFF,                  # 1 byte  RAM % uso
        disk_pct & 0xFF,                 # 1 byte  disco % uso
        uptime_s & 0xFFFFFFFF,           # 4 bytes uptime en seg
        errors & 0xFFFF,                 # 2 bytes contador de errores
        0                                # 2 bytes reservado
    )


def decode_status(data: bytes) -> dict:
    """Inverso de encode_status para uso en el OBC o debug."""
    import struct
    if len(data) < 14:
        raise ValueError(f"data too short: {len(data)}")
    (state, n_pending, last_scan_id, temp_c, ram_pct, disk_pct,
     uptime_s, errors, _reserved) = struct.unpack("<BBHBBBIHH", data[:14])
    return {
        "state": state,
        "state_name": STATE_NAMES.get(state, f"unknown({state})"),
        "n_pending": n_pending,
        "last_scan_id": last_scan_id,
        "temp_c": temp_c,
        "ram_pct": ram_pct,
        "disk_pct": disk_pct,
        "uptime_s": uptime_s,
        "errors": errors,
    }
