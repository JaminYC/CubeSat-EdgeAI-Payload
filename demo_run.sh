#!/bin/bash
# Script de demostración rápida para Linux/Mac
# ============================================

echo ""
echo "============================================================"
echo "FPM CALIBRATION TOOL - DEMO RAPIDA"
echo "============================================================"
echo ""

echo "1. Verificando instalacion..."
python3 setup_calibration.py
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Problema en la verificacion"
    exit 1
fi

echo ""
echo "2. Generando imagen de prueba..."
python3 generate_test_image.py
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: No se pudo generar la imagen de prueba"
    exit 1
fi

echo ""
echo "3. Iniciando herramienta de calibracion..."
echo "   Se abrira un dialogo para seleccionar la imagen"
echo ""

python3 fpm_calibration_tool.py
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Problema al ejecutar la herramienta"
    exit 1
fi

echo ""
echo "============================================================"
echo "DEMO COMPLETADA"
echo "============================================================"
echo ""
