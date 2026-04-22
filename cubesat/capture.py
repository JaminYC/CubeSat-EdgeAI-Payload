"""
Captura de imagenes FPM: OV5647 sin lente iluminado por OLED SPI.
El OLED muestra cada angulo de iluminacion en secuencia y el sensor captura.

Depende de picamera2 (libcamera) y luma.oled (pantalla OLED SPI).
En desarrollo fuera de la RPi estos imports fallan; el modulo los tolera.
"""
from __future__ import annotations

import time
from pathlib import Path
from datetime import datetime, timezone

try:
    from picamera2 import Picamera2  # type: ignore
    HAS_PICAMERA = True
except ImportError:
    HAS_PICAMERA = False
    Picamera2 = None  # type: ignore

try:
    from luma.core.interface.serial import spi  # type: ignore
    from luma.oled.device import ssd1351  # type: ignore
    HAS_OLED = True
except ImportError:
    HAS_OLED = False


# Angulos de iluminacion del OLED para reconstruccion FPM multi-angulo
# (posiciones de pixel brillante sobre la pantalla 128x128)
N_ANGLES = 25  # 5x5 grid
OLED_SIZE = 128


def _angle_positions():
    """Genera posiciones (x, y) en el OLED para cada angulo."""
    step = OLED_SIZE // 5
    offset = step // 2
    positions = []
    for iy in range(5):
        for ix in range(5):
            positions.append((offset + ix * step, offset + iy * step))
    return positions


class FPMCapture:
    """
    Ejecuta una secuencia de captura FPM: enciende un pixel del OLED,
    captura con el sensor, repite N_ANGLES veces. Guarda todas las imagenes
    en /var/cubesat/incoming/scan_<UTC>/ como cap_NN.jpg + metadata.json.
    """

    def __init__(self, incoming_dir: Path, logger=None):
        self.incoming_dir = Path(incoming_dir)
        self.log = logger or print
        self._cam = None
        self._oled = None

    def _init_hardware(self):
        if not HAS_PICAMERA:
            raise RuntimeError("picamera2 no instalado (solo funciona en RPi con libcamera)")
        if not HAS_OLED:
            raise RuntimeError("luma.oled no instalado")

        self._cam = Picamera2()
        cfg = self._cam.create_still_configuration(
            main={"size": (2592, 1944), "format": "RGB888"}
        )
        self._cam.configure(cfg)
        self._cam.start()
        time.sleep(0.5)  # warmup

        serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
        self._oled = ssd1351(serial, width=OLED_SIZE, height=OLED_SIZE)

    def _close_hardware(self):
        if self._cam:
            self._cam.stop()
            self._cam.close()
            self._cam = None
        if self._oled:
            self._oled.clear()
            self._oled = None

    def capture_scan(self, mode: int = 0) -> Path:
        """
        Ejecuta un scan completo.
        mode: 0=rapido (9 angulos 3x3), 1=completo (25 angulos 5x5).
        Retorna el path de la carpeta del scan.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        scan_dir = self.incoming_dir / f"scan_{timestamp}.tmp"
        scan_dir.mkdir(parents=True, exist_ok=True)

        positions = _angle_positions()
        if mode == 0:
            positions = positions[::3][:9]  # subset de 9 angulos

        self.log(f"FPM scan {timestamp}: {len(positions)} angulos, modo={mode}")

        try:
            self._init_hardware()
            from PIL import ImageDraw, Image
            import json

            metadata = {
                "scan_id": timestamp,
                "mode": mode,
                "sensor": "OV5647 lensless",
                "oled": "SSD1351 128x128",
                "n_angles": len(positions),
                "captures": [],
            }

            for i, (ox, oy) in enumerate(positions):
                img = Image.new("RGB", (OLED_SIZE, OLED_SIZE), "black")
                draw = ImageDraw.Draw(img)
                draw.ellipse((ox - 3, oy - 3, ox + 3, oy + 3), fill="white")
                self._oled.display(img)
                time.sleep(0.05)

                frame = self._cam.capture_array()
                out = scan_dir / f"cap_{i:02d}.jpg"

                from PIL import Image as PImage
                PImage.fromarray(frame).save(out, quality=90)

                metadata["captures"].append({
                    "idx": i,
                    "file": out.name,
                    "oled_x": ox,
                    "oled_y": oy,
                })

                self.log(f"  {i+1}/{len(positions)}: {out.name}")

            with open(scan_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            # Rename atomico para que el watcher solo lo vea cuando este completo
            final = scan_dir.with_suffix("")
            scan_dir.rename(final)
            self.log(f"Scan completo: {final}")
            return final

        finally:
            self._close_hardware()
