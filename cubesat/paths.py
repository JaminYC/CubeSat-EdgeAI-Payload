"""Rutas canonicas en el filesystem de la RPi."""
from pathlib import Path

# Estados efimeros (tmpfs, se borran al reiniciar)
RUN_DIR = Path("/run/cubesat")
STATUS_FILE = RUN_DIR / "status.json"
TELEMETRY_FILE = RUN_DIR / "telemetry.json"
COMMAND_QUEUE = RUN_DIR / "commands"   # Un archivo por comando pendiente
LOCK_FILE = RUN_DIR / "pipeline.lock"

# Datos persistentes
DATA_DIR = Path("/var/cubesat")
INCOMING_DIR = DATA_DIR / "incoming"   # El capture script escribe aqui
RESULTS_DIR = DATA_DIR / "results"     # El pipeline escribe aqui
DOWNLINK_DIR = DATA_DIR / "downlink"   # Archivos listos para bajar
LOG_DIR = Path("/var/log/cubesat")

# Codigo
REPO_DIR = Path("/opt/cubesat")        # Clon del repo
CONFIG_FILE = REPO_DIR / "cubesat" / "config.yaml"


def ensure_dirs():
    """Crea todos los directorios necesarios. Llamar al arranque."""
    for d in [RUN_DIR, COMMAND_QUEUE, INCOMING_DIR, RESULTS_DIR, DOWNLINK_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)
