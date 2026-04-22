"""
Daemon principal: procesa scans entrantes y ejecuta comandos de la cola.

Arquitectura:
1. Watcher de filesystem (inotify) sobre /var/cubesat/incoming/
   - Cuando aparece una carpeta scan_*/ completa, la procesa.
2. Watcher de filesystem sobre /run/cubesat/commands/
   - Cuando i2c_slave deposita un archivo de comando, lo ejecuta.

El pipeline real vive en pipeline/controller.py (ya existente en el repo).
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Permite importar pipeline/... cuando el daemon corre desde /opt/cubesat
sys.path.insert(0, "/opt/cubesat")

from cubesat import paths, commands, capture, telemetry

_running = True
_error_counter = 0
_current_state = commands.STATE_IDLE
_last_scan_id = 0


def _sig_handler(signum, frame):
    global _running
    _running = False


def set_state(state: int):
    global _current_state
    _current_state = state
    write_status()


def write_status():
    """Escritura atomica de status.json."""
    paths.ensure_dirs()
    data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "state": _current_state,
        "state_name": commands.STATE_NAMES.get(_current_state, "?"),
        "last_scan_id": _last_scan_id,
        "errors": _error_counter,
    }
    tmp = paths.STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(paths.STATUS_FILE)


def process_scan(scan_dir: Path):
    """Dispara el pipeline sobre un scan entrante."""
    global _last_scan_id
    try:
        set_state(commands.STATE_PROCESSING)
        _last_scan_id = int(time.time()) & 0xFFFF

        # Lock para evitar reentrada
        paths.LOCK_FILE.write_text(str(os.getpid()))

        # Aqui se conecta con el controller existente del repo
        from pipeline.controller import PipelineController  # noqa
        ctrl = PipelineController(
            input_dir=scan_dir,
            output_dir=paths.RESULTS_DIR / scan_dir.name,
            enhance_method="n2v",      # obligatorio
            seg_ai_method="stardist",  # mas rapido en RPi
        )
        ctrl.run()

        # Publicar archivos para downlink
        set_state(commands.STATE_EXPORTING)
        publish_downlink(paths.RESULTS_DIR / scan_dir.name)

        # Mover el scan procesado para que no se reprocese
        done_marker = scan_dir / ".processed"
        done_marker.touch()

        set_state(commands.STATE_IDLE)

    except Exception:
        global _error_counter
        _error_counter += 1
        traceback.print_exc()
        set_state(commands.STATE_ERROR)
    finally:
        if paths.LOCK_FILE.exists():
            paths.LOCK_FILE.unlink()


def publish_downlink(results_dir: Path):
    """
    Copia a /var/cubesat/downlink/<scan_id>/ los archivos que van al satelite.
    Siempre: summary.json, telemetry.json, thumbnail.jpg (640x480, ~100KB).
    On-demand: data.csv, masks, originales (via comandos I2C).
    """
    import shutil
    scan_id = results_dir.name
    out = paths.DOWNLINK_DIR / scan_id
    out.mkdir(parents=True, exist_ok=True)

    # summary + telemetry siempre
    for fname in ("summary.json",):
        src = results_dir / fname
        if src.exists():
            shutil.copy2(src, out / fname)

    # Thumbnail 640x480 JPEG calidad 70 (~100KB)
    overlay = results_dir / "overlay.png"
    if overlay.exists():
        from PIL import Image
        img = Image.open(overlay).convert("RGB")
        img.thumbnail((640, 480), Image.LANCZOS)
        img.save(out / "thumbnail.jpg", quality=70, optimize=True)

    # Snapshot de telemetria al momento del export
    if paths.TELEMETRY_FILE.exists():
        shutil.copy2(paths.TELEMETRY_FILE, out / "telemetry.json")


def execute_command(cmd_file: Path):
    """Lee un archivo de comando depositado por i2c_slave y lo ejecuta."""
    try:
        data = json.loads(cmd_file.read_text())
        cmd = data.get("cmd")
        payload = data.get("payload", {})

        if cmd == commands.CMD_START_CAPTURE:
            set_state(commands.STATE_CAPTURING)
            cap = capture.FPMCapture(paths.INCOMING_DIR)
            cap.capture_scan(mode=payload.get("mode", 0))
        elif cmd == commands.CMD_SAFE_MODE:
            set_state(commands.STATE_SAFE_MODE)
        elif cmd == commands.CMD_RESUME:
            set_state(commands.STATE_IDLE)
        elif cmd == commands.CMD_OTA_PREPARE:
            from cubesat import ota
            set_state(commands.STATE_OTA_IN_PROGRESS)
            ota.prepare(payload.get("commit_hash", ""))
        elif cmd == commands.CMD_OTA_COMMIT:
            from cubesat import ota
            ota.commit()
        elif cmd == commands.CMD_REBOOT:
            os.system("systemctl reboot")
    except Exception:
        global _error_counter
        _error_counter += 1
        traceback.print_exc()
    finally:
        cmd_file.unlink(missing_ok=True)


def scan_is_complete(scan_dir: Path) -> bool:
    """Un scan esta completo cuando existe su metadata.json y no esta .tmp."""
    if scan_dir.suffix == ".tmp":
        return False
    if (scan_dir / ".processed").exists():
        return False
    return (scan_dir / "metadata.json").exists()


def run_loop():
    """Loop principal del daemon."""
    paths.ensure_dirs()
    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    set_state(commands.STATE_IDLE)
    sd_notify_ready()

    while _running:
        try:
            # 1. Comandos pendientes (mayor prioridad)
            for cmd_file in sorted(paths.COMMAND_QUEUE.glob("*.json")):
                execute_command(cmd_file)

            if _current_state == commands.STATE_SAFE_MODE:
                time.sleep(2)
                sd_notify_watchdog()
                continue

            # 2. Scans entrantes pendientes
            for scan_dir in sorted(paths.INCOMING_DIR.glob("scan_*")):
                if scan_is_complete(scan_dir):
                    process_scan(scan_dir)

            sd_notify_watchdog()
            time.sleep(1)
        except Exception:
            global _error_counter
            _error_counter += 1
            traceback.print_exc()
            time.sleep(5)


def sd_notify_ready():
    try:
        import sdnotify
        sdnotify.SystemdNotifier().notify("READY=1")
    except ImportError:
        pass


def sd_notify_watchdog():
    try:
        import sdnotify
        sdnotify.SystemdNotifier().notify("WATCHDOG=1")
    except ImportError:
        pass


if __name__ == "__main__":
    run_loop()
