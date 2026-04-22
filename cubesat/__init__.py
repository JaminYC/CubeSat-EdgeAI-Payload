"""
Modulo cubesat: operacion autonoma de la payload de microscopia en RPi 5.

Se ejecuta como 4 servicios systemd:
- cubesat-pipeline   : watcher + controller (ejecuta FPM + IA cuando llega scan)
- cubesat-i2c-slave  : escucha I2C_2 @ 0x42, traduce comandos OBC a triggers
- cubesat-telemetry  : escribe /run/cubesat/telemetry.json cada 30s
- cubesat-ota        : realiza git pull + restart cuando OBC pide actualizar
"""

__version__ = "0.1.0"
