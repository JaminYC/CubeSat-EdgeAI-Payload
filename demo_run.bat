@echo off
REM Script de demostración rápida para Windows
REM ==========================================

echo.
echo ============================================================
echo FPM CALIBRATION TOOL - DEMO RAPIDA
echo ============================================================
echo.

echo 1. Verificando instalacion...
python setup_calibration.py
if errorlevel 1 goto error

echo.
echo 2. Generando imagen de prueba...
python generate_test_image.py
if errorlevel 1 goto error

echo.
echo 3. Iniciando herramienta de calibracion...
echo    Se abrira un dialogo para seleccionar la imagen
echo    O presiona Ctrl+C para salir
echo.
pause

python fpm_calibration_tool.py
if errorlevel 1 goto error

echo.
echo ============================================================
echo DEMO COMPLETADA
echo ============================================================
goto end

:error
echo.
echo ERROR: Algo salio mal. Verifica los mensajes anteriores.
echo.
pause
exit /b 1

:end
echo.
pause
