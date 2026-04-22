"""
Telemetria del sistema: cada 30s escribe telemetry.json con metricas de salud
que el OBC puede leer via CMD_GET_TELEMETRY para downlink.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone

from cubesat import paths


def read_cpu_temp() -> float:
    """Temperatura del SoC en grados C. RPi: /sys/class/thermal/thermal_zone0/temp (milli-C)."""
    p = Path("/sys/class/thermal/thermal_zone0/temp")
    if p.exists():
        return int(p.read_text().strip()) / 1000.0
    return 0.0


def read_ram_usage() -> tuple[int, int, int]:
    """(used_mb, total_mb, pct_used) via /proc/meminfo."""
    info = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, _, rest = line.partition(":")
        info[k.strip()] = int(rest.strip().split()[0])
    total = info.get("MemTotal", 0) // 1024
    avail = info.get("MemAvailable", 0) // 1024
    used = total - avail
    pct = int(100 * used / total) if total else 0
    return used, total, pct


def read_disk_usage(path: Path = Path("/var/cubesat")) -> tuple[int, int, int]:
    """(used_mb, total_mb, pct_used) de la particion donde vive path."""
    import shutil
    u = shutil.disk_usage(path if path.exists() else Path("/"))
    total = u.total // (1024 * 1024)
    used = (u.total - u.free) // (1024 * 1024)
    pct = int(100 * used / u.total) if u.total else 0
    return used, total, pct


def read_uptime() -> int:
    """Uptime del sistema en segundos."""
    return int(float(Path("/proc/uptime").read_text().split()[0]))


def collect() -> dict:
    """Snapshot completo del estado del sistema."""
    used_ram, total_ram, pct_ram = read_ram_usage()
    used_disk, total_disk, pct_disk = read_disk_usage()

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "temp_c": round(read_cpu_temp(), 1),
        "ram_used_mb": used_ram,
        "ram_total_mb": total_ram,
        "ram_pct": pct_ram,
        "disk_used_mb": used_disk,
        "disk_total_mb": total_disk,
        "disk_pct": pct_disk,
        "uptime_s": read_uptime(),
        "n_scans_incoming": len(list(paths.INCOMING_DIR.glob("scan_*")))
                            if paths.INCOMING_DIR.exists() else 0,
        "n_scans_done": len(list(paths.RESULTS_DIR.glob("scan_*")))
                        if paths.RESULTS_DIR.exists() else 0,
    }


def write_snapshot():
    """Escritura atomica: tmp → rename."""
    paths.ensure_dirs()
    data = collect()
    tmp = paths.TELEMETRY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(paths.TELEMETRY_FILE)


def run_loop(interval_s: int = 30):
    """Loop principal del servicio cubesat-telemetry."""
    while True:
        try:
            write_snapshot()
        except Exception as e:
            # Errores de telemetria no deben tumbar el sistema
            print(f"[telemetry] error: {e}")
        time.sleep(interval_s)


if __name__ == "__main__":
    run_loop()
