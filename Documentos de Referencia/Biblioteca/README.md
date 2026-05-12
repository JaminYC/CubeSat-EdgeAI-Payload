# Biblioteca de documentos del proyecto INTISAT

Esta carpeta contiene **todos los PDFs generados** para el proyecto
CubeSat-EdgeAI-Payload, organizados por categoria.

> Los `.tex` originales y los PDFs "vivos" estan en la carpeta padre.
> Esta `Biblioteca/` es un **archivo organizado** para consulta facil.

## Estructura

### 01_Manuales_Tecnicos/

Manuales de subsistemas y conceptos tecnicos especificos. Estos son
los manuales de la coleccion CubeSat (M0, M2, M5, M10) mas referencias
electronicas.

| Archivo | Pag | Tema |
|---|---|---|
| `M0_CubeSat_101.pdf` | 29 | introduccion al ecosistema CubeSat |
| `M2_Sistemas_Potencia_EPS.pdf` | 13 | EPS, paneles solares, bateria |
| `M5_Flight_Software.pdf` | 17 | software de a bordo |
| `M10_CM5_Carrier_INTISAT.pdf` | 27 | diseño del carrier para CM5 |
| `Manual_Electronica_Practica.pdf` | 44 | electronica desde cero |
| `Raspberry_Pi_5_Profundo.pdf` | 25 | deep dive del Pi 5 |

**Total**: 155 paginas

### 02_Libros_y_Cursos/

Libros teoricos extensos para construir base.

| Archivo | Pag | Tema |
|---|---|---|
| `Curso_Vision_Computadora.pdf` | 81 | vision por computadora completa |

**Total**: 81 paginas

### 03_Informes_Experimentos/

Informes formales de experimentos especificos.

| Archivo | Pag | Tema |
|---|---|---|
| `Informe_Mascaras_Lensless.pdf` | 21 | experimento de mascaras opticas (IMRyD) |
| `Guion_Mascaras_Lensless.pdf` | 25 | version narrativa del mismo experimento |
| `Pipeline_IA_Microscopía.pdf` | 13 | descripcion tecnica del pipeline IA |

**Total**: 59 paginas

### 04_Bibliografias_Referencias/

Compilaciones de fuentes y referencias.

| Archivo | Pag | Tema |
|---|---|---|
| `Bibliografia_AI_Espacial.pdf` | 18 | IA en operaciones espaciales |
| `Referencias_OpenSource_CubeSat.pdf` | 18 | NASA, ESA, repos open-source |

**Total**: 36 paginas

### 05_Planes_y_Guias/

Planes y guias para el equipo.

| Archivo | Pag | Tema |
|---|---|---|
| `Plan_Documentacion_CubeSat.pdf` | 22 | roadmap de los 11 manuales |
| `Guia_Empleo_Industrial_Mineria.pdf` | 25 | carrera en mineria/industrial |
| `Resumen Ejecutivo Científico.pdf` | --- | resumen ejecutivo |

**Total**: 47+ paginas

### 06_Diagramas_Interactivos/

Documentos HTML interactivos con diagramas Mermaid/SVG. Se abren en
cualquier navegador con doble click, sin software adicional.

| Archivo | Tema |
|---|---|
| `state_machines_cubesat.html` | maquinas de estado completas (mision + 5 subsistemas) + matriz operacional + comparacion contra INTISAT |
| `architecture.html` | 6 diagramas Mermaid de la arquitectura del payload (HW, SW, scan lifecycle, I2C, estados, OTA) |
| `pipeline_general.html` | flujo del pipeline IA en 5 fases (recepcion, captura, procesamiento, storage, downlink) |
| `modos_operacion.html` | modos de operacion del payload con click interactivo en cada estado |

**Total**: 4 HTMLs interactivos. Todos con boton de "Imprimir / PDF" si necesitan version impresa.

## Resumen

**15 PDFs + 4 HTMLs**, **~380 paginas + diagramas interactivos** de material tecnico.

## Como usar

**Si sos miembro nuevo del equipo**:
1. Leer primero `01_Manuales_Tecnicos/M0_CubeSat_101.pdf` (es la introduccion).
2. Despues `01_Manuales_Tecnicos/Manual_Electronica_Practica.pdf`.
3. Despues el manual del subsistema que te toca.

**Si sos del payload**:
1. M0 (CubeSat 101)
2. Manual_Electronica_Practica
3. Raspberry_Pi_5_Profundo
4. M10 (CM5 Carrier)
5. Curso_Vision_Computadora (selectivo)

**Si vas a operaciones**:
1. M0 (CubeSat 101)
2. Bibliografia_AI_Espacial
3. Referencias_OpenSource_CubeSat (capitulo OpenMCT)

## Manuales pendientes (a generar en proximas sesiones)

Segun `Plan_Documentacion_CubeSat.pdf`, faltan estos:

- M1 — Mecanica y estructura
- M3 — ADCS (control de actitud)
- M4 — Comunicaciones (RF y antenas)
- M6 — Control termico
- M7 — Integracion y testing
- M8 — Operaciones y ground station
- M9 — Project management

## Mantenimiento

Cuando se regenere un PDF (desde el .tex correspondiente), reemplazar
manualmente en la carpeta correspondiente. Esta biblioteca se mantiene
sincronizada a mano (no automatico).

Para regenerar todos los PDFs:
```bash
cd "Documentos de Referencia"
for tex in *.tex; do pdflatex -interaction=nonstopmode "$tex"; done
# Despues copiar los .pdf actualizados a la categoria correspondiente
```
