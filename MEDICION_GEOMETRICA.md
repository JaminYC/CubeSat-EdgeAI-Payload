# Medicion Geometrica - FPM Calibration Tool

## Que hay de nuevo?

Ahora puedes medir figuras geometricas completas: circulos, rectangulos, triangulos y poligonos!

## Modos de Medicion Disponibles

### 1. Circulo (3 puntos)
Mide circulos haciendo click en **3 puntos del perimetro**.

**Como usar:**
1. Presionar `g` (modo geometria)
2. Presionar `1` (circulo)
3. Click en 3 puntos del perimetro del circulo
4. La herramienta calcula automaticamente:
   - Centro del circulo
   - Radio (en um y px)
   - Diametro (en um y px)
   - Area (en um^2)

**Ejemplo:**
```
Medir una celula circular:
  Click 1: Lado izquierdo (9 en punto)
  Click 2: Parte superior (12 en punto)
  Click 3: Lado derecho (3 en punto)

Resultado:
  G1: CIRCULO
  Radio: 15.47um (519.0px)
  Diametro: 30.94um (1038.0px)
  Area: 751.82um^2
```

**Beneficios:**
- No necesitas hacer click exactamente en el centro
- Funciona con circulos parcialmente visibles
- Mas preciso que medir solo el diametro

---

### 2. Rectangulo (2 esquinas)
Mide rectangulos haciendo click en **2 esquinas opuestas**.

**Como usar:**
1. Presionar `g` (modo geometria)
2. Presionar `2` (rectangulo)
3. Click en una esquina (ej. superior izquierda)
4. Click en la esquina opuesta (ej. inferior derecha)
5. La herramienta calcula:
   - Ancho (en um y px)
   - Alto (en um y px)
   - Area (en um^2)
   - Perimetro (en um)

**Ejemplo:**
```
Medir una estructura rectangular:
  Click 1: Esquina superior izquierda
  Click 2: Esquina inferior derecha

Resultado:
  G1: RECTANGULO
  Ancho: 45.23um (1518.0px)
  Alto: 23.56um (791.0px)
  Area: 1065.42um^2
  Perimetro: 137.58um
```

**Casos de uso:**
- Tejidos rectangulares
- Chips o arrays de micropatrones
- Areas de interes (ROI)

---

### 3. Triangulo (3 vertices)
Mide triangulos haciendo click en **3 vertices**.

**Como usar:**
1. Presionar `g` (modo geometria)
2. Presionar `3` (triangulo)
3. Click en cada uno de los 3 vertices
4. La herramienta calcula:
   - Longitudes de los 3 lados (en um y px)
   - Area (en um^2) usando formula de Heron
   - Perimetro (en um)

**Ejemplo:**
```
Medir una estructura triangular:
  Click 1: Vertice superior
  Click 2: Vertice inferior izquierdo
  Click 3: Vertice inferior derecho

Resultado:
  G1: TRIANGULO
  Lado 1: 34.12um (1145.0px)
  Lado 2: 29.87um (1002.0px)
  Lado 3: 25.64um (860.0px)
  Area: 412.56um^2
  Perimetro: 89.63um
```

**Formula de Heron:**
```
s = (a + b + c) / 2
Area = sqrt(s * (s-a) * (s-b) * (s-c))
```

---

### 4. Poligono (N vertices)
Mide poligonos de cualquier numero de lados (N >= 3).

**Como usar:**
1. Presionar `g` (modo geometria)
2. Presionar `4` (poligono)
3. Click en cada vertice del poligono (en orden)
4. Presionar **Enter** para finalizar
5. La herramienta calcula:
   - Numero de vertices
   - Area (en um^2) usando formula de Shoelace
   - Perimetro (en um)

**Ejemplo:**
```
Medir un pentagono irregular:
  Click 1: Vertice 1
  Click 2: Vertice 2
  Click 3: Vertice 3
  Click 4: Vertice 4
  Click 5: Vertice 5
  Enter: Finalizar

Resultado:
  G1: POLIGONO (5 vertices)
  Area: 892.45um^2
  Perimetro: 124.78um
```

**Formula de Shoelace:**
```
Area = 0.5 * |sum(x[i]*y[i+1] - x[i+1]*y[i])|
```

**Casos de uso:**
- Celulas irregulares
- Nucleos
- Cualquier estructura poligonal compleja

---

## Flujo de Trabajo

### Workflow Completo

```
PASO 1: Calibrar o establecer escala
  Option A: Presionar 'c' -> Medir microesferas
  Option B: Presionar 'e' -> Introducir escala manual

PASO 2: Activar modo geometria
  Presionar 'g'

PASO 3: Seleccionar tipo de figura
  1 = Circulo
  2 = Rectangulo
  3 = Triangulo
  4 = Poligono

PASO 4: Hacer clicks
  - Para circulo: 3 clicks en perimetro
  - Para rectangulo: 2 clicks en esquinas opuestas
  - Para triangulo: 3 clicks en vertices
  - Para poligono: N clicks + Enter

PASO 5: Repetir para mas figuras
  - La figura queda guardada
  - Puedes medir otra figura del mismo tipo
  - O presionar otro numero para cambiar tipo

PASO 6: Guardar resultados
  Presionar 's' -> Guarda todas las mediciones en CSV
```

---

## Visualizacion en Pantalla

Cada tipo de figura tiene su propio color:

- **CIRCULO**: Cyan (0, 255, 255)
  - Circulo dibujado en cyan
  - Punto central marcado
  - Etiqueta con ID y mediciones

- **RECTANGULO**: Amarillo (0, 255, 255)
  - Rectangulo dibujado en amarillo
  - Etiqueta con dimensiones y area

- **TRIANGULO**: Naranja (0, 165, 255)
  - Triangulo dibujado en naranja
  - Vertices marcados
  - Etiqueta con area

- **POLIGONO**: Naranja (0, 165, 255)
  - Poligono cerrado dibujado en naranja
  - Todos los vertices marcados
  - Etiqueta con numero de vertices y area

---

## Ejemplos Practicos

### Ejemplo 1: Medir Celulas Circulares

```bash
# Terminal
python fpm_calibration_tool.py

# En la herramienta:
1. Seleccionar imagen con celulas
2. Presionar 'e' -> Introducir 0.0298
3. Presionar 'g'
4. Presionar '1' (circulo)
5. Hacer zoom con rueda del raton
6. Click en 3 puntos del borde de una celula
   -> Aparece circulo cyan con mediciones
7. Repetir para otras celulas
8. Presionar 's' para guardar
```

### Ejemplo 2: Medir Area de Tejido Rectangular

```bash
# En la herramienta (ya calibrada):
1. Presionar 'g'
2. Presionar '2' (rectangulo)
3. Alejar con '-' para ver toda el area
4. Click en esquina superior izquierda del tejido
5. Click en esquina inferior derecha
   -> Aparece rectangulo amarillo con dimensiones
6. Presionar 's' para guardar
```

### Ejemplo 3: Medir Nucleos Irregulares (Poligono)

```bash
# En la herramienta (ya calibrada):
1. Presionar 'g'
2. Presionar '4' (poligono)
3. Hacer zoom a un nucleo
4. Click en cada punto del contorno (8-12 puntos)
5. Presionar Enter
   -> Aparece poligono naranja con area
6. Repetir para otros nucleos
7. Presionar 's' para guardar
```

---

## Archivo CSV Generado

Cuando presionas 's', se guarda un CSV con TODAS las mediciones:

```csv
ID,Tipo,Medida,Valor_um,Valor_px
C1,Calibracion,Radio,1.02,34.2
C2,Calibracion,Radio,0.98,32.9
...
M1,Medicion_Lineal,Distancia,45.23,1518.0
M2,Medicion_Lineal,Distancia,23.56,791.0
...
G1,Circulo,Radio,15.47,519.0
G1,Circulo,Diametro,30.94,1038.0
G1,Circulo,Area_um2,751.82,-
G2,Rectangulo,Ancho,45.23,1518.0
G2,Rectangulo,Alto,23.56,791.0
G2,Rectangulo,Area_um2,1065.42,-
G2,Rectangulo,Perimetro_um,137.58,-
...
```

---

## Formulas Matematicas Usadas

### Circulo desde 3 Puntos

Para encontrar el centro (ux, uy) de un circulo que pasa por 3 puntos (x1,y1), (x2,y2), (x3,y3):

```
d = 2 * (x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))

ux = ((x1^2+y1^2)*(y2-y3) + (x2^2+y2^2)*(y3-y1) + (x3^2+y3^2)*(y1-y2)) / d
uy = ((x1^2+y1^2)*(x3-x2) + (x2^2+y2^2)*(x1-x3) + (x3^2+y3^2)*(x2-x1)) / d

radio = distancia_euclidiana((x1,y1), (ux,uy))
```

### Area de Triangulo (Formula de Heron)

```
a, b, c = longitudes de los 3 lados
s = (a + b + c) / 2  # Semi-perimetro
Area = sqrt(s * (s-a) * (s-b) * (s-c))
```

### Area de Poligono (Formula de Shoelace)

```
vertices = [(x0,y0), (x1,y1), ..., (xn,yn)]

Area = 0.5 * |sum(x[i]*y[i+1] - x[i+1]*y[i]) for i in range(n)|

donde x[n+1] = x[0] y y[n+1] = y[0] (cierra el poligono)
```

---

## Tips y Trucos

### Para Mejores Resultados:

1. **Usa zoom**: Acerca la imagen con la rueda del raton para clicks precisos
2. **Circulo**: Distribuye los 3 puntos uniformemente alrededor del perimetro
3. **Poligono**: Usa mas puntos para formas complejas (10-15 puntos)
4. **Verificacion**: Los valores en pixeles te permiten verificar manualmente

### Atajos de Teclado:

```
GEOMETRIA:
  g -> Activar modo geometria
  1 -> Circulo
  2 -> Rectangulo
  3 -> Triangulo
  4 -> Poligono
  Enter -> Finalizar poligono

NAVEGACION:
  +/- -> Zoom
  Rueda -> Zoom continuo
  Flechas -> Desplazar imagen

OTROS:
  r -> Reset (limpiar actual)
  s -> Guardar CSV
  q -> Salir
```

---

## Casos de Uso Cientificos

### Biologia Celular:
- Medir diametro de celulas (circulo)
- Medir area de nucleos (poligono)
- Medir tejidos rectangulares (rectangulo)

### Microscopia de Materiales:
- Medir granos cristalinos (poligono)
- Medir particulas circulares (circulo)
- Medir defectos rectangulares (rectangulo)

### Analisis de Imagenes:
- Segmentacion manual
- Validacion de segmentacion automatica
- Ground truth para machine learning

---

## Para el Paper

### Seccion de Metodos:

```
"Geometric measurements were performed using custom software based on
OpenCV (version 4.x). Circle measurements utilized the three-point
circumference method to calculate center coordinates and radius.
Polygon area calculations employed the Shoelace formula. All measurements
were performed on calibrated images (scale = 0.0298 +/- 0.0010 um/pixel,
n=15 microsphere calibrations)."
```

### Reportar Resultados:

```
"Cell diameter: 30.94 +/- 2.15 um (n=25 cells, measured using 3-point
circle fitting)"

"Nuclear area: 412.56 +/- 34.28 um^2 (n=18 nuclei, measured using
polygon tracing with 10-15 vertices per nucleus)"
```

---

## Resumen

**Nuevo:**
- 4 tipos de figuras geometricas
- Calculos automaticos de areas, perimetros, radios
- Visualizacion en color por tipo de figura
- Exportacion a CSV con todas las mediciones

**Beneficios:**
- Mas preciso que mediciones lineales simples
- Permite medir estructuras complejas
- Datos trazables y verificables
- Compatible con analisis estadistico

**Tu herramienta FPM ahora puede medir CUALQUIER geometria!**
