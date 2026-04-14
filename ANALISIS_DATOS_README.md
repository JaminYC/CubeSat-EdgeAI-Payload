# Analisis y Visualizacion de Datos de Calibracion FPM

## Descripcion

Scripts de Python para analizar y visualizar los datos de calibracion generados por la herramienta FPM Calibration Tool. Generan graficos cientificos de calidad para publicacion y reportes estadisticos completos.

---

## Scripts Disponibles

### 1. `analisis_calibracion.py` - Analisis Individual

Analiza un unico archivo CSV de calibracion y genera:
- 6 graficos cientificos
- Reporte estadistico completo
- Evaluacion de calidad

**Uso:**
```bash
python analisis_calibracion.py
```

**Graficos generados:**
1. **Histograma de Escala** - Distribucion de valores um/pixel
2. **Boxplot de Escala** - Visualizacion de dispersion y outliers
3. **Radio Medido** - Tendencia de radios en pixeles
4. **Diametro vs Nominal** - Comparacion con valor esperado (2 um)
5. **Error Relativo** - Porcentaje de error por microesfera
6. **Q-Q Plot** - Test de normalidad de los datos

**Estadisticas calculadas:**
- Media, mediana, desviacion estandar
- Coeficiente de variacion (CV%)
- Error absoluto y relativo
- Rango de valores
- Calidad de calibracion (Excelente/Buena/Aceptable/Pobre)

---

### 2. `analisis_multiple_calibraciones.py` - Comparacion Multiple

Compara multiples sesiones de calibracion para:
- Evaluar reproducibilidad
- Detectar drift temporal
- Comparar diferentes configuraciones

**Uso:**
```bash
python analisis_multiple_calibraciones.py
```

**Graficos generados:**
1. **Comparacion de Escalas** - Barras con error bars
2. **Boxplots Multiples** - Distribucion por sesion
3. **Coeficiente de Variacion** - CV% por sesion
4. **Evolucion Temporal** - Cambios en el tiempo
5. **Violin Plots** - Distribucion completa
6. **Radio vs Escala** - Correlaciones

**Analisis incluido:**
- Estadisticas por sesion
- Estadisticas globales
- Diferencias entre sesiones
- Consistencia temporal

---

## Instalacion de Dependencias

Si no tienes las librerias necesarias:

```bash
pip install pandas numpy matplotlib seaborn scipy
```

O usa el archivo de requirements existente:

```bash
pip install -r requirements_calibration.txt
```

---

## Ejemplos de Uso

### Ejemplo 1: Analisis de una Calibracion

```bash
# Ejecutar script
python analisis_calibracion.py

# Seleccionar archivo (dialogo GUI)
fpm_calibration_20260119_120950.csv

# Resultado en consola:
===========================================================
REPORTE DE CALIBRACION - FPM CALIBRATION TOOL
===========================================================
Archivo: fpm_calibration_20260119_120950
Numero de microesferas medidas: 15

ESCALA (um/pixel)
-----------------------------------------------------------
  Media:    0.029814 um/px
  Mediana:  0.029820 um/px
  Std Dev:  0.001234 um/px
  CV:       4.14%

CALIDAD DE CALIBRACION
-----------------------------------------------------------
  CV < 5%:  ✓✓ BUENA
  Escala recomendada: 0.029820 um/px
===========================================================

# Archivos generados:
- fpm_calibration_20260119_120950_analisis.png (grafico)
- fpm_calibration_20260119_120950_reporte.txt (reporte)
```

---

### Ejemplo 2: Comparar 3 Calibraciones

```bash
# Ejecutar script
python analisis_multiple_calibraciones.py

# Seleccionar multiples archivos (Ctrl+Click)
fpm_calibration_20260119_120950.csv
fpm_calibration_20260120_093045.csv
fpm_calibration_20260121_154230.csv

# Resultado en consola:
================================================================================
RESUMEN COMPARATIVO DE CALIBRACIONES
================================================================================
Sesion     N     Escala Media    SD          CV(%)    Radio(px)
--------------------------------------------------------------------------------
S1         15    0.029814        0.001234    4.14     10.25
S2         18    0.029856        0.001089    3.65     10.18
S3         12    0.029801        0.001456    4.89     10.32
--------------------------------------------------------------------------------

ESTADISTICAS GLOBALES (todas las sesiones):
  Total mediciones: 45
  Escala global media: 0.029824 um/px
  Escala global CV: 4.15%

  Diferencia max entre sesiones: 0.000055 um/px (0.18%)
================================================================================

# Archivos generados:
- comparacion_calibraciones_TIMESTAMP.png
- datos_individuales_TIMESTAMP.png
```

---

## Interpretacion de Resultados

### Coeficiente de Variacion (CV%)

El CV% es la metrica clave de calidad:

| CV%      | Calidad    | Interpretacion                                    |
|----------|------------|---------------------------------------------------|
| < 3%     | EXCELENTE  | Altisima precision, ideal para metrologia         |
| 3-5%     | BUENA      | Buena precision, aceptable para uso cientifico    |
| 5-10%    | ACEPTABLE  | Precision moderada, considerar recalibrar         |
| > 10%    | POBRE      | Baja precision, recalibracion necesaria           |

### Error Relativo

Compara el diametro medido vs el nominal (2 um):

- **Error < 5%**: Mediciones dentro de especificaciones
- **Error 5-10%**: Revisar mediciones individuales
- **Error > 10%**: Posible problema sistematico

### Q-Q Plot (Normalidad)

- **Puntos en linea recta**: Datos normalmente distribuidos
- **Desviaciones**: Outliers o distribucion no normal

---

## Graficos Generados

### 1. Histograma de Escala
```
┌─────────────────────────────┐
│    Distribucion de Escala   │
│                             │
│     ┌──┐                    │
│  ┌──┤  ├──┐                 │
│  │  │  │  │   Media (rojo)  │
│  │  │  │  │   Mediana (vd)  │
│  └──┴──┴──┘                 │
│                             │
└─────────────────────────────┘
```

### 2. Boxplot
```
┌─────────────────────────────┐
│      Boxplot - Escala       │
│                             │
│         ┌───┐               │
│         │   │   □ Media     │
│    ─────┤   ├─────          │
│         │   │               │
│         └───┘               │
│                             │
│   Outliers marcados: ○      │
└─────────────────────────────┘
```

### 3. Error Relativo
```
┌─────────────────────────────┐
│    Error Relativo (%)       │
│                             │
│  │▓│ │▓│ │▓│ │▓│ │▓│       │
│  │▓│ │▓│ │▓│ │▓│ │▓│       │
│ ─┴─┴─┴─┴─┴─┴─┴─┴─┴─────    │
│   1  2  3  4  5  ID         │
│                             │
│ Verde: < 5% | Rojo: > 5%    │
└─────────────────────────────┘
```

---

## Casos de Uso Cientificos

### 1. Validacion de Calibracion Inicial

**Objetivo:** Verificar que la calibracion es confiable

```python
# Ejecutar
python analisis_calibracion.py

# Verificar:
- CV% < 5%? ✓
- Error medio < 5%? ✓
- Q-Q plot lineal? ✓
- Sin outliers? ✓

# Conclusion: Calibracion valida
# Escala recomendada: 0.029820 um/px
```

---

### 2. Estudio de Reproducibilidad

**Objetivo:** ¿La calibracion es reproducible dia a dia?

```python
# Calibrar 3 veces en dias diferentes
# Ejecutar
python analisis_multiple_calibraciones.py

# Verificar:
- Diferencia entre sesiones < 2%? ✓
- CV global < 5%? ✓
- Evolucion temporal estable? ✓

# Conclusion: Sistema reproducible
```

---

### 3. Comparacion de Magnificaciones

**Objetivo:** Calibrar diferentes configuraciones opticas

```python
# Calibrar con:
# - Magnificacion 10x
# - Magnificacion 40x

# Comparar escalas:
# 10x: 0.140 um/px
# 40x: 0.035 um/px
# Ratio: 4.0x ✓ (esperado)

# Conclusion: Escalas consistentes
```

---

### 4. Deteccion de Drift

**Objetivo:** ¿El sistema deriva con el tiempo?

```python
# Calibrar semanalmente durante 1 mes
# Ejecutar analisis multiple

# Verificar evolucion temporal:
- Tendencia ascendente/descendente? ✗
- Fluctuaciones < 3%? ✓

# Conclusion: Sin drift significativo
```

---

## Para Publicaciones Cientificas

### Seccion de Metodos

```
"La calibracion espacial se realizo mediante microesferas de poliestireno
de 2.0 ± 0.04 μm (Polysciences Inc.). Se midieron 15 microesferas por
imagen utilizando software personalizado basado en OpenCV 4.x. La escala
resultante fue de 0.0298 ± 0.0012 μm/pixel (media ± SD, n=15, CV=4.1%),
determinada como la mediana de todas las mediciones para minimizar el
efecto de outliers."
```

### Reporte de Resultados

```
"La reproducibilidad de la calibracion se evaluo mediante tres sesiones
independientes (n=15 cada una). La variacion entre sesiones fue de 0.18%,
indicando alta consistencia del metodo (CV global=4.1%, rango=0.0296-0.0301
μm/pixel)."
```

### Figura para Paper

Los graficos generados estan en resolucion 300 DPI, listos para publicacion:

```
Figura 1. Analisis de calibracion espacial. (A) Distribucion de valores
de escala (n=15 microesferas). (B) Boxplot mostrando mediana, cuartiles y
outliers. (C) Error relativo de cada medicion respecto al valor nominal
(2 μm). (D) Q-Q plot indicando distribucion normal de los datos.
```

---

## Tips y Trucos

### 1. Eliminar Outliers

Si detectas outliers en el analisis:

```python
# Opcion 1: Eliminar manualmente del CSV
# Abrir el CSV, borrar la fila con el outlier

# Opcion 2: Filtrar en el script (avanzado)
# En analisis_calibracion.py, agregar:
# df = df[np.abs(df['um_per_pixel'] - df['um_per_pixel'].median()) < 3*df['um_per_pixel'].std()]
```

---

### 2. Exportar Datos para Otros Softwares

Los CSV son compatibles con:
- **Excel**: Abrir directamente
- **R**: `read.csv("file.csv")`
- **MATLAB**: `readtable('file.csv')`
- **Origin**: Import ASCII
- **ImageJ**: Results Table

---

### 3. Combinar con Otros Analisis

Exporta la escala calculada para usar en otros scripts:

```python
import pandas as pd

# Leer CSV
df = pd.read_csv('fpm_calibration_20260119_120950.csv')

# Obtener escala recomendada
escala = df['um_per_pixel'].median()

# Usar en tus mediciones
distancia_px = 150
distancia_um = distancia_px * escala
print(f"Distancia: {distancia_um:.2f} um")
```

---

## Solución de Problemas

### Problema: "ModuleNotFoundError: No module named 'pandas'"

**Solucion:**
```bash
pip install pandas numpy matplotlib seaborn scipy
```

---

### Problema: Los graficos no se muestran

**Solucion:**
```python
# Asegurate de que matplotlib tiene backend correcto
import matplotlib
matplotlib.use('TkAgg')  # O 'Qt5Agg'
import matplotlib.pyplot as plt
```

---

### Problema: Errores de encoding en Windows

**Solucion:**
Ya esta manejado en los scripts con `encoding='utf-8'`

---

## Personalizacion

### Cambiar Diametro Nominal

Si usas microesferas de diferente tamaño:

```python
# En analisis_calibracion.py, linea ~24
self.diametro_real_um = 2.0  # Cambiar aqui (ej: 1.0, 5.0, etc)
```

---

### Cambiar Colores de Graficos

```python
# Al inicio del script
plt.style.use('ggplot')  # O 'seaborn', 'bmh', etc
sns.set_palette("viridis")  # O "muted", "deep", etc
```

---

### Exportar en Otros Formatos

```python
# En lugar de PNG, guardar como:
fig.savefig('output.pdf', dpi=300)  # PDF
fig.savefig('output.svg', dpi=300)  # SVG (vectorial)
fig.savefig('output.eps', dpi=300)  # EPS (publicaciones)
```

---

## Resumen

| Script | Uso | Archivos generados |
|--------|-----|-------------------|
| `analisis_calibracion.py` | Analisis individual | PNG (grafico) + TXT (reporte) |
| `analisis_multiple_calibraciones.py` | Comparacion multiple | 2 PNG (graficos) |

**Recomendacion:** Ejecuta `analisis_calibracion.py` despues de cada sesion de calibracion para verificar calidad inmediatamente.

---

## Referencias

- OpenCV Documentation: https://docs.opencv.org/
- Matplotlib Gallery: https://matplotlib.org/stable/gallery/
- Seaborn Tutorial: https://seaborn.pydata.org/tutorial.html
- Pandas User Guide: https://pandas.pydata.org/docs/user_guide/

---

**¡Tus datos de calibracion ahora tienen analisis cientifico completo!** 📊🔬
