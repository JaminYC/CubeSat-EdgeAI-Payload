"""
Servicio esclavo I2C: escucha en I2C_2 @ 0x42 comandos del OBC y los deposita
como archivos en /run/cubesat/commands/ para que el daemon los procese.

Requiere pigpio (daemon pigpiod debe estar corriendo).
En dev fuera de RPi, los imports de pigpio fallan; se tolera.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

try:
    import pigpio  # type: ignore
    HAS_PIGPIO = True
except ImportError:
    HAS_PIGPIO = False
    pigpio = None  # type: ignore

from cubesat import paths, commands, telemetry

I2C_BUS = 1          # I2C_2 en PC-104 = /dev/i2c-1 en el kernel de la RPi
I2C_ADDR = 0x42      # Direccion esclava de la payload

# Buffer interno para respuestas chunked (>30 bytes)
_response_buffer = b""
_response_offset = 0


def _drop_command(cmd_byte: int, payload: bytes):
    """Convierte bytes I2C en un archivo JSON que el daemon leera."""
    paths.ensure_dirs()

    body = {"cmd": cmd_byte, "payload": {}}

    if cmd_byte == commands.CMD_START_CAPTURE:
        mode = payload[0] if payload else 0
        body["payload"]["mode"] = mode
    elif cmd_byte == commands.CMD_OTA_PREPARE:
        body["payload"]["commit_hash"] = payload.decode("ascii", errors="ignore").strip()

    fname = f"{int(time.time())}_{uuid.uuid4().hex[:6]}.json"
    (paths.COMMAND_QUEUE / fname).write_text(json.dumps(body))


def _build_status_response() -> bytes:
    """Arma respuesta binaria para CMD_GET_STATUS (16 bytes)."""
    # Lee el status actual del daemon
    state = commands.STATE_IDLE
    n_pending = 0
    last_scan_id = 0
    errors = 0
    if paths.STATUS_FILE.exists():
        try:
            s = json.loads(paths.STATUS_FILE.read_text())
            state = s.get("state", 0)
            last_scan_id = s.get("last_scan_id", 0)
            errors = s.get("errors", 0)
        except Exception:
            pass

    if paths.INCOMING_DIR.exists():
        n_pending = len([p for p in paths.INCOMING_DIR.glob("scan_*")
                         if not (p / ".processed").exists()])

    t = telemetry.collect()
    return commands.encode_status(
        state=state,
        n_pending=n_pending,
        last_scan_id=last_scan_id,
        temp_c=t["temp_c"],
        ram_pct=t["ram_pct"],
        disk_pct=t["disk_pct"],
        uptime_s=t["uptime_s"],
        errors=errors,
    )


def _load_file_for_chunking(path: Path, offset: int, chunk_size: int = 30) -> bytes:
    """Lee un archivo y devuelve un chunk con prefijo (offset, more_flag)."""
    if not path.exists():
        return bytes([commands.STATUS_NO_DATA, 0])
    data = path.read_bytes()
    start = offset * chunk_size
    if start >= len(data):
        return bytes([commands.STATUS_OK, 0])  # EOF
    chunk = data[start:start + chunk_size]
    more = 1 if start + chunk_size < len(data) else 0
    return bytes([commands.STATUS_OK, len(chunk), more]) + chunk


def handle_request(cmd_byte: int, payload: bytes) -> bytes:
    """
    Dispatch central de comandos I2C. Retorna los bytes a responder al OBC.
    """
    if cmd_byte == commands.CMD_GET_STATUS:
        resp = _build_status_response()
        return bytes([commands.STATUS_OK, len(resp)]) + resp

    if cmd_byte == commands.CMD_GET_TELEMETRY:
        offset = payload[0] if payload else 0
        return _load_file_for_chunking(paths.TELEMETRY_FILE, offset)

    if cmd_byte == commands.CMD_GET_LAST_SUMMARY:
        offset = payload[0] if payload else 0
        # Ultimo scan en downlink por mtime
        scans = sorted(paths.DOWNLINK_DIR.glob("scan_*"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not scans:
            return bytes([commands.STATUS_NO_DATA, 0])
        return _load_file_for_chunking(scans[0] / "summary.json", offset)

    if cmd_byte == commands.CMD_GET_THUMBNAIL:
        offset = int.from_bytes(payload[:2], "little") if len(payload) >= 2 else 0
        scans = sorted(paths.DOWNLINK_DIR.glob("scan_*"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not scans:
            return bytes([commands.STATUS_NO_DATA, 0])
        return _load_file_for_chunking(scans[0] / "thumbnail.jpg", offset)

    if cmd_byte == commands.CMD_GET_DATA_CSV:
        offset = int.from_bytes(payload[:2], "little") if len(payload) >= 2 else 0
        scans = sorted(paths.RESULTS_DIR.glob("scan_*"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not scans:
            return bytes([commands.STATUS_NO_DATA, 0])
        return _load_file_for_chunking(scans[0] / "data.csv", offset)

    if cmd_byte == commands.CMD_LIST_RESULTS:
        scans = sorted(paths.DOWNLINK_DIR.glob("scan_*"),
                       key=lambda p: p.stat().st_mtime)
        names = b"\n".join(p.name.encode() for p in scans[-5:])
        return bytes([commands.STATUS_OK, len(names)]) + names

    if cmd_byte in (commands.CMD_START_CAPTURE, commands.CMD_STOP,
                    commands.CMD_SAFE_MODE, commands.CMD_RESUME,
                    commands.CMD_OTA_PREPARE, commands.CMD_OTA_COMMIT,
                    commands.CMD_REBOOT):
        _drop_command(cmd_byte, payload)
        return bytes([commands.STATUS_OK, 0])

    return bytes([commands.STATUS_UNKNOWN_CMD, 0])


def run_loop():
    """
    Loop principal del esclavo I2C.

    pigpio emula un esclavo I2C usando el hardware BSC (Broadcom Serial
    Controller). En la RPi 5 se conecta por GPIO2/3 (I2C1 bus), que en el
    PC-104 INTISAT corresponde a los pines H1.21 (SCL) y H1.23 (SDA) del
    bus I2C_2 del satelite.
    """
    if not HAS_PIGPIO:
        raise RuntimeError("pigpio no instalado: `sudo apt install pigpio python3-pigpio`")

    pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("pigpiod no esta corriendo: `sudo systemctl start pigpiod`")

    pi.bsc_i2c(I2C_ADDR)  # Activa modo esclavo
    print(f"[i2c_slave] escuchando en /dev/i2c-{I2C_BUS} @ 0x{I2C_ADDR:02X}")

    try:
        while True:
            status, count, data = pi.bsc_i2c(I2C_ADDR)
            if count > 0:
                cmd = data[0]
                payload = data[1:count] if count > 1 else b""
                response = handle_request(cmd, payload)
                pi.bsc_i2c(I2C_ADDR, response)
            time.sleep(0.005)  # 5ms poll
    finally:
        pi.bsc_i2c(0)  # Cierra modo esclavo
        pi.stop()


if __name__ == "__main__":
    run_loop()
