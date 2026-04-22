"""
Actualizacion Over-The-Air del codigo.

Flujo:
1. OBC envia CMD_OTA_PREPARE con el hash del commit a aplicar.
2. `prepare(hash)` hace git fetch y verifica que el hash existe.
3. OBC envia CMD_OTA_COMMIT para confirmar.
4. `commit()` hace checkout, reinstala deps si cambio requirements, y
   reinicia los servicios systemd.
5. Si algo falla, rollback automatico al commit anterior.
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from cubesat import paths

STAGING_FILE = paths.RUN_DIR / "ota_staging.json"


def _run(cmd: list[str], cwd: Path = None) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=cwd or paths.REPO_DIR,
                       capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def _current_commit() -> str:
    code, out = _run(["git", "rev-parse", "HEAD"])
    return out if code == 0 else ""


def prepare(commit_hash: str) -> bool:
    """
    Descarga el hash objetivo y valida que existe sin aplicarlo.
    Guarda el hash anterior en STAGING_FILE para rollback.
    """
    paths.ensure_dirs()
    commit_hash = commit_hash.strip()
    if len(commit_hash) < 7:
        raise ValueError(f"commit_hash demasiado corto: {commit_hash!r}")

    prev = _current_commit()
    if not prev:
        raise RuntimeError("Directorio no es un repo git valido")

    code, out = _run(["git", "fetch", "origin", commit_hash])
    if code != 0:
        raise RuntimeError(f"git fetch fallo: {out}")

    code, out = _run(["git", "cat-file", "-e", commit_hash])
    if code != 0:
        raise RuntimeError(f"commit {commit_hash} no existe tras fetch")

    STAGING_FILE.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "prev_commit": prev,
        "target_commit": commit_hash,
    }))
    return True


def commit() -> bool:
    """
    Aplica el hash preparado. Si falla algo, hace rollback.
    Reinicia cubesat-pipeline y cubesat-i2c-slave.
    """
    if not STAGING_FILE.exists():
        raise RuntimeError("No hay OTA preparada (falta CMD_OTA_PREPARE)")

    data = json.loads(STAGING_FILE.read_text())
    target = data["target_commit"]
    prev = data["prev_commit"]

    try:
        # Parar servicios dependientes (no el i2c-slave, que sigue respondiendo)
        _run(["systemctl", "stop", "cubesat-pipeline"])

        code, out = _run(["git", "checkout", target])
        if code != 0:
            raise RuntimeError(f"checkout fallo: {out}")

        # Reinstalar dependencias si cambio requirements
        req = paths.REPO_DIR / "requirements_pipeline.txt"
        if req.exists():
            _run(["pip", "install", "-r", str(req), "--quiet"])

        # Restart
        _run(["systemctl", "start", "cubesat-pipeline"])
        time.sleep(3)

        # Verificar que arranco
        code, _ = _run(["systemctl", "is-active", "--quiet", "cubesat-pipeline"])
        if code != 0:
            raise RuntimeError("cubesat-pipeline no arranco tras OTA")

        STAGING_FILE.unlink()
        return True

    except Exception:
        # Rollback
        _run(["git", "checkout", prev])
        _run(["systemctl", "restart", "cubesat-pipeline"])
        raise
