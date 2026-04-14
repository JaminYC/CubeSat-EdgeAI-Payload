# Quick Start - FPM Calibration Tool

## Instalación Rápida

```bash
pip install -r requirements_calibration.txt
```

## Dos Formas de Ejecutar

### Opción 1: Con Interfaz Gráfica (Recomendado)

Simplemente ejecuta sin argumentos y selecciona la imagen desde el diálogo:

```bash
python fpm_calibration_tool.py
```

Se abrirá un diálogo de selección de archivos donde puedes elegir:
- ✅ Archivos .tiff / .tif
- ✅ Archivos .png
- ✅ Archivos .jpg / .jpeg
- ✅ Archivos .bmp

### Opción 2: Por Línea de Comandos

```bash
python fpm_calibration_tool.py ruta/a/tu/imagen_fpm.tiff
```

## Prueba Rápida (Imagen Sintética)

1. Generar imagen de prueba:
```bash
python generate_test_image.py
```

2. Ejecutar herramienta:
```bash
python fpm_calibration_tool.py
```
   Luego selecciona `test_fpm_image.png` en el diálogo

3. Probar calibración:
   - Presiona `c`
   - Click en centro de una microesfera circular
   - Click en el borde
   - Repite 10-15 veces con diferentes microesferas
   - Presiona `s` para guardar

## Flujo de Trabajo Recomendado

### Fase 1: Calibración (5-10 minutos)

1. Cargar imagen FPM con microesferas visibles
2. Presionar `c` (modo calibración)
3. Medir 10-20 microesferas diferentes:
   - Buscar microesferas bien definidas
   - Click centro → Click borde
   - Verificar círculo dibujado
4. Revisar estadísticas en consola
5. Verificar CV% < 5%
6. Presionar `s` para guardar

### Fase 2: Medición (según necesidad)

1. En la misma imagen o cargar nueva con misma óptica
2. Presionar `m` (modo medición)
3. Medir estructuras biológicas:
   - Click punto inicial
   - Click punto final
   - Ver resultado en µm
4. Repetir para múltiples estructuras

## Interpretación de Resultados

### Ejemplo de Salida en Consola

```
============================================================
ESTADÍSTICAS DE CALIBRACIÓN
============================================================
Número de microesferas medidas: 15
Escala (mediana): 0.0298 µm/pixel
Desviación estándar: 0.0012 µm/pixel
Coeficiente de variación: 4.03%
============================================================
```

**Interpretación**:
- ✅ CV% = 4.03% → Excelente (< 5%)
- Escala: 0.0298 µm/pixel
- Incertidumbre: ±0.0012 µm/pixel

### Archivos Generados

- `fpm_calibration_20260119_143022.csv` - Datos crudos
- `fpm_calibration_summary_20260119_143022.txt` - Resumen

## Consejos Prácticos

### ✅ HACER

- Medir al menos 10 microesferas
- Distribuir mediciones en toda la imagen
- Seleccionar microesferas bien enfocadas
- Verificar CV% < 5-10%
- Hacer clicks precisos (zoom si es necesario)

### ❌ NO HACER

- Medir microesferas borrosas o parciales
- Usar menos de 5 mediciones
- Mezclar calibraciones de diferentes imágenes
- Asumir que pixel pitch = escala real

## Solución de Problemas

### "No se pudo cargar la imagen"
- Verificar ruta del archivo
- Formato soportado: PNG, JPG, TIFF

### "CV% muy alto (> 10%)"
- Revisar calidad de microesferas medidas
- Descartar mediciones erróneas
- Repetir con microesferas más definidas

### "Círculo no se ajusta bien"
- Mejorar precisión de clicks
- Usar zoom de ventana (función de Windows/OS)
- Repetir medición (presionar `r`)

## Contacto

Para preguntas o problemas técnicos, consulta la documentación completa en [README_calibration.md](README_calibration.md).
