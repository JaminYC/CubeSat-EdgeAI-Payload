# Archivos del Proyecto FPM Calibration Tool

## 📁 Estructura del Proyecto

```
PruebaRealSgan/
│
├── 🔧 HERRAMIENTA PRINCIPAL
│   └── fpm_calibration_tool.py       ← Programa principal de calibración
│
├── 📚 DOCUMENTACIÓN
│   ├── INICIO_RAPIDO.txt             ← Guía rápida (empieza aquí!)
│   ├── QUICK_START.md                ← Inicio rápido en Markdown
│   ├── README_calibration.md         ← Documentación técnica completa
│   └── ARCHIVOS_PROYECTO.md          ← Este archivo
│
├── 🔨 INSTALACIÓN Y SETUP
│   ├── requirements_calibration.txt  ← Dependencias Python
│   ├── setup_calibration.py          ← Script de verificación
│   ├── demo_run.bat                  ← Demo para Windows
│   └── demo_run.sh                   ← Demo para Linux/Mac
│
├── 🧪 HERRAMIENTAS DE PRUEBA
│   └── generate_test_image.py        ← Genera imagen sintética de prueba
│
└── 🗂️ ARCHIVOS PREVIOS
    └── escalar_x4.py                 ← Script RealESRGAN (tu archivo original)
```

## 📄 Descripción de Archivos

### Herramienta Principal

**fpm_calibration_tool.py** (500+ líneas)
- Herramienta completa de calibración y medición
- Interfaz gráfica para selección de imágenes
- Soporta .tiff, .png, .jpg, .bmp
- Modos: Calibración y Medición
- Exporta resultados a CSV

**Uso:**
```bash
python fpm_calibration_tool.py              # Con diálogo GUI
python fpm_calibration_tool.py imagen.tiff  # Por línea de comandos
```

### Documentación

**INICIO_RAPIDO.txt**
- Guía de inicio rápido en texto plano
- Instrucciones paso a paso
- Controles y comandos
- Solución de problemas básicos

**QUICK_START.md**
- Versión Markdown de la guía rápida
- Ejemplos de uso
- Flujo de trabajo recomendado

**README_calibration.md**
- Documentación técnica completa
- Fundamentos científicos
- Cálculos matemáticos
- Validación metrológica
- Referencias bibliográficas

### Instalación

**requirements_calibration.txt**
- Lista de dependencias Python
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- Notas sobre tkinter

**setup_calibration.py**
- Verifica versión de Python
- Comprueba módulos instalados
- Instala dependencias automáticamente
- Ejecuta tests de funcionalidad

**Uso:**
```bash
python setup_calibration.py
```

### Scripts de Demostración

**demo_run.bat** (Windows)
- Ejecuta verificación completa
- Genera imagen de prueba
- Lanza la herramienta
- Script batch para Windows

**demo_run.sh** (Linux/Mac)
- Versión bash del script de demo
- Mismo flujo que la versión Windows

**Uso:**
```bash
# Windows
demo_run.bat

# Linux/Mac
chmod +x demo_run.sh
./demo_run.sh
```

### Herramientas de Prueba

**generate_test_image.py**
- Genera imagen sintética de prueba
- Simula 25 microesferas de 2 µm
- Incluye estructuras biológicas de ejemplo
- Útil para familiarizarse con la herramienta

**Uso:**
```bash
python generate_test_image.py
# Genera: test_fpm_image.png
```

## 🚀 Flujo de Trabajo Sugerido

### Para Nuevos Usuarios

1. Leer `INICIO_RAPIDO.txt`
2. Ejecutar `python setup_calibration.py`
3. Generar prueba: `python generate_test_image.py`
4. Probar herramienta: `python fpm_calibration_tool.py`

### Para Calibración Real

1. Preparar imagen FPM con microesferas (.tiff recomendado)
2. Ejecutar: `python fpm_calibration_tool.py`
3. Seleccionar imagen en el diálogo
4. Calibrar con tecla 'c' (10-20 microesferas)
5. Guardar con tecla 's'
6. Medir estructuras con tecla 'm'

### Para Usuarios Avanzados

1. Revisar `README_calibration.md` para fundamentos
2. Ejecutar desde línea de comandos con rutas específicas
3. Procesar múltiples imágenes con scripts batch
4. Analizar archivos CSV generados

## 📊 Archivos de Salida

Después de usar la herramienta, se generan:

- `fpm_calibration_YYYYMMDD_HHMMSS.csv`
  - Datos tabulados de calibración
  - Columnas: id, center_x, center_y, border_x, border_y, radius_px, diameter_px, um_per_pixel

- `fpm_calibration_summary_YYYYMMDD_HHMMSS.txt`
  - Resumen estadístico
  - Escala mediana (µm/pixel)
  - Desviación estándar
  - Coeficiente de variación
  - Lista de mediciones individuales

## 🔧 Requisitos del Sistema

### Software
- Python 3.7 o superior
- OpenCV (cv2)
- NumPy
- Tkinter (generalmente preinstalado)

### Hardware
- Cualquier PC con Windows, Linux o macOS
- Mínimo 4 GB RAM
- Pantalla para visualizar imágenes

### Imágenes
- Formato: TIFF, PNG, JPG, BMP
- Contenido: Imágenes FPM reconstruidas
- Patrón: Microesferas de poliestireno 2 µm

## 📞 Soporte

Para problemas técnicos:
1. Revisar sección "Solución de Problemas" en `INICIO_RAPIDO.txt`
2. Consultar documentación completa en `README_calibration.md`
3. Verificar instalación con `python setup_calibration.py`

## 📝 Notas

- Los archivos originales del proyecto (como `escalar_x4.py`) permanecen intactos
- Todos los archivos nuevos tienen el prefijo o sufijo relacionado con "calibration"
- El proyecto es modular: puedes usar solo los archivos que necesites
