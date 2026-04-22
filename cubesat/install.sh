#!/bin/bash
# Instalador de la payload CubeSat en Raspberry Pi 5.
# Ejecutar desde el repo clonado: sudo ./cubesat/install.sh
#
# Pasos:
#  1. Verifica Raspberry Pi OS 64-bit
#  2. Instala paquetes del sistema (pigpio, libcamera, etc)
#  3. Habilita I2C y SPI via raspi-config
#  4. Clona/copia repo a /opt/cubesat y crea venv
#  5. Instala dependencias Python
#  6. Copia los archivos .service a /etc/systemd/system/
#  7. Habilita y arranca los servicios
#  8. Crea /var/cubesat/ y /run/cubesat/ con permisos

set -e

REPO_SRC="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DST="/opt/cubesat"
DATA_DIR="/var/cubesat"
RUN_DIR="/run/cubesat"
USER_NAME="${SUDO_USER:-pi}"

if [[ $EUID -ne 0 ]]; then
   echo "Este script requiere sudo"
   exit 1
fi

echo "== 1. Verificando sistema =="
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null && [ -f /proc/cpuinfo ]; then
    echo "WARN: no parece una Raspberry Pi — continuando de todos modos"
fi
uname -m | grep -q "aarch64" || echo "WARN: no es arm64"

echo "== 2. Instalando paquetes del sistema =="
apt-get update
apt-get install -y \
    python3 python3-pip python3-venv \
    pigpio python3-pigpio \
    i2c-tools \
    libcamera-apps python3-picamera2 \
    git

systemctl enable pigpiod
systemctl start pigpiod

echo "== 3. Habilitando I2C y SPI =="
raspi-config nonint do_i2c 0
raspi-config nonint do_spi 0
raspi-config nonint do_camera 0 || true

# Agregar i2c-slave al device tree si no esta
if ! grep -q "dtoverlay=i2c-gpio" /boot/firmware/config.txt 2>/dev/null; then
    echo "# CubeSat payload I2C slave on bus 1 (pins H1.21/H1.23 of PC-104)" >> /boot/firmware/config.txt
fi

echo "== 4. Copiando repo a $REPO_DST =="
mkdir -p "$REPO_DST"
rsync -a --delete --exclude='.git' --exclude='venv' --exclude='models' \
      --exclude='__pycache__' "$REPO_SRC/" "$REPO_DST/"
chown -R "$USER_NAME":"$USER_NAME" "$REPO_DST"

echo "== 5. Creando venv e instalando Python deps =="
sudo -u "$USER_NAME" python3 -m venv "$REPO_DST/venv"
sudo -u "$USER_NAME" "$REPO_DST/venv/bin/pip" install --upgrade pip --quiet
sudo -u "$USER_NAME" "$REPO_DST/venv/bin/pip" install --quiet \
    numpy opencv-python-headless \
    scikit-image pillow pyyaml \
    pigpio sdnotify \
    luma.oled

# Dependencias pesadas (IA) — opcional, pueden tardar mucho en RPi
if [ "${INSTALL_AI:-1}" = "1" ]; then
    echo "   Instalando modelos IA (puede tardar ~20 min)..."
    sudo -u "$USER_NAME" "$REPO_DST/venv/bin/pip" install --quiet \
        onnxruntime \
        cellpose stardist csbdeep
fi

echo "== 6. Instalando servicios systemd =="
cp "$REPO_DST/cubesat/systemd/cubesat-pipeline.service"  /etc/systemd/system/
cp "$REPO_DST/cubesat/systemd/cubesat-i2c-slave.service" /etc/systemd/system/
cp "$REPO_DST/cubesat/systemd/cubesat-telemetry.service" /etc/systemd/system/
systemctl daemon-reload

echo "== 7. Creando directorios de datos =="
mkdir -p "$DATA_DIR"/{incoming,results,downlink}
mkdir -p /var/log/cubesat
chown -R "$USER_NAME":"$USER_NAME" "$DATA_DIR" /var/log/cubesat

# /run/cubesat se crea con tmpfiles.d para persistir entre reinicios
cat > /etc/tmpfiles.d/cubesat.conf <<EOF
d $RUN_DIR 0755 $USER_NAME $USER_NAME -
d $RUN_DIR/commands 0755 $USER_NAME $USER_NAME -
EOF
systemd-tmpfiles --create /etc/tmpfiles.d/cubesat.conf

echo "== 8. Habilitando servicios =="
systemctl enable cubesat-telemetry cubesat-i2c-slave cubesat-pipeline
systemctl start  cubesat-telemetry cubesat-i2c-slave cubesat-pipeline

sleep 3
systemctl --no-pager status cubesat-telemetry cubesat-i2c-slave cubesat-pipeline \
  | head -30

echo ""
echo "== Instalacion completa =="
echo "  - Codigo:       $REPO_DST"
echo "  - Datos:        $DATA_DIR"
echo "  - Logs:         journalctl -u cubesat-pipeline -f"
echo "  - Test I2C:     sudo i2cdetect -y 1"
echo "  - Test estado:  cat /run/cubesat/status.json"
echo "  - Test telem:   cat /run/cubesat/telemetry.json"
