#!/usr/bin/env bash
set -euo pipefail

# =======================================================
#  Script oficial para generar TODOS los CDR de INTISAT
#  Autor: ChatGPT + J. Yauri
#  Fecha: 2025
# =======================================================

# -------- Carpeta plantilla (la que tú tienes ahora) -----
TEMPLATE_DIR="."

# -------- Carpeta raíz donde se generarán los CDR --------
DEST_ROOT="4_PhaseC_CriticalDesign"

# =======================================================
# LISTA OFICIAL DE CÓDIGOS Y TÍTULOS DEL EXCEL
# =======================================================

DOC_CODES=(
"INTI-C-00.00-CDR"
"INTI-C-01.00-OBC-CDR"
"INTI-C-02.00-COMM-CDR"
"INTI-C-03.00-EPS-CDR"
"INTI-C-04.00-ADCS-CDR"
"INTI-C-07.00-STR-CDR"
"INTI-C-09.00-TCS-CDR"
"INTI-C-05.00-ODS-CDR"
"INTI-C-05.01-LLPC-CDR"
"INTI-C-05.02-CMOSM-CDR"
"INTI-C-05.03-SAI-CDR"
)

DOC_TITLES=(
"Critical Design Review Report"
"OBC Critical Design Review"
"Communications Critical Design Review"
"Electrical Power System CDR"
"Attitude Determination & Control CDR"
"Structure & Mechanism CDR"
"Thermal Control System CDR"
"Orbit Determination System CDR"
"LEO Light Polluting Characterization CDR"
"CMOS Microscopy CDR"
"Super-Resolution AI CDR"
)

# -------- Rutas según Excel ----------------------------
DOC_PATHS=(
"System"
"OBC"
"COMM"
"EPS"
"ADCS"
"Structure"
"TCS"
"Payload_ODS"
"Payload_LLPC"
"Payload_Microscopy"
"Payload_AI"
)

# =======================================================
# VALIDACIÓN
# =======================================================

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "❌ No se encontró la carpeta plantilla '$TEMPLATE_DIR'"
    exit 1
fi

mkdir -p "$DEST_ROOT"

if [ "${#DOC_CODES[@]}" -ne "${#DOC_TITLES[@]}" ] || \
   [ "${#DOC_CODES[@]}" -ne "${#DOC_PATHS[@]}" ]; then
    echo "❌ Tamaños desiguales en CODIGO / TÍTULO / PATH"
    exit 1
fi

# =======================================================
# CREACIÓN DE DOCUMENTOS
# =======================================================

for i in "${!DOC_CODES[@]}"; do
    code="${DOC_CODES[$i]}"
    title="${DOC_TITLES[$i]}"
    subpath="${DOC_PATHS[$i]}"

    dest="${DEST_ROOT}/${subpath}/${code}"

    echo "📁 Creando: $code → $dest"

    if [ -d "$dest" ]; then
        echo "   ⚠️  Ya existe, saltando…"
        continue
    fi

    # Crear carpeta destino
    mkdir -p "$dest"

    # Copiar plantilla: todo lo que hay en la carpeta actual,
    # EXCEPTO la carpeta de salida y el propio script.
    for entry in *; do
      # Nombre de la carpeta raíz de CDR (por ej. '4_PhaseC_CriticalDesign')
      root_name="$(basename "$DEST_ROOT")"
      script_name="$(basename "$0")"

      # Saltar la carpeta de salida y el script
      if [ "$entry" = "$root_name" ] || [ "$entry" = "$script_name" ]; then
        continue
      fi

      cp -r "$entry" "$dest/"
    done


    # Crear carpeta sections
    rm -rf "$dest/chapters" || true
    mkdir -p "$dest/sections"

    # Crear secciones base
    cat > "$dest/sections/01_introduccion.tex" <<EOF
\\section{Introducción}
Este documento corresponde al Critical Design Review del subsistema \\\\textbf{$title} ($code).
EOF

    cat > "$dest/sections/02_requerimientos.tex" <<EOF
\\section{Requerimientos del Subsistema}
% TODO: completar requerimientos técnicos
EOF

    cat > "$dest/sections/03_diseno.tex" <<EOF
\\section{Diseño del Subsistema}
% TODO: arquitectura, diagramas, interfaces
EOF

    cat > "$dest/sections/04_pruebas.tex" <<EOF
\\section{Pruebas realizadas y resultados obtenidos}
% TODO: describir pruebas, datos y análisis
EOF

    cat > "$dest/sections/05_riesgos.tex" <<EOF
\\section{Riesgos y mitigaciones}
% TODO: definir riesgos técnicos
EOF

    cat > "$dest/sections/06_conclusiones.tex" <<EOF
\\section{Conclusiones}
% TODO: sintetizar resultados, próximos pasos
EOF

    # Modificar main.tex para que cargue las secciones nuevas
    if [ -f "$dest/main.tex" ]; then
        cp "$dest/main.tex" "$dest/main.tex.bak"

        # Borrar llamadas a chapters/
        sed -i '/chapters\//d' "$dest/main.tex"

        # Insertar nuestras secciones después de begin{document}
        sed -i "/\\begin{document}/a \\\input{sections/01_introduccion}" "$dest/main.tex"
        sed -i "/\\begin{document}/a \\\input{sections/02_requerimientos}" "$dest/main.tex"
        sed -i "/\\begin{document}/a \\\input{sections/03_diseno}" "$dest/main.tex"
        sed -i "/\\begin{document}/a \\\input{sections/04_pruebas}" "$dest/main.tex"
        sed -i "/\\begin{document}/a \\\input{sections/05_riesgos}" "$dest/main.tex"
        sed -i "/\\begin{document}/a \\\input{sections/06_conclusiones}" "$dest/main.tex"

        # Reemplazar título y código (si existieran)
        sed -i "s/Critical Design Review/$title/g" "$dest/main.tex" || true
        sed -i "s/INTI-C-XX-XXX-CDR/$code/g" "$dest/main.tex" || true
    fi

    echo "   ✅ $code generado."
done

echo "🎉 Todos los CDR fueron generados con éxito."
