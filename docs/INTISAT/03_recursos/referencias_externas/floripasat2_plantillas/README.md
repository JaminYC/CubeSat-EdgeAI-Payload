# Plantillas extraídas de FloripaSat-2 (GOLDS-UFSC)

**Fuente:** *GOLDS-UFSC Design and Mission Overview*, SpaceLab UFSC, junio 2023.
Documento de referencia citado en el README principal de INTISAT.
Extracto local: `../floripa_output.txt` (7578 líneas).
Repo público: https://github.com/spacelab-ufsc/floripasat2-doc

---

## ¿Qué hay aquí?

Plantillas LaTeX **adaptadas a INTISAT 2U** basadas en cómo lo hizo FloripaSat-2 (también 2U). Sirven como punto de partida para llenar las secciones vacías del CDR INTISAT:

| Plantilla | Reemplaza / completa |
|---|---|
| `mass_budget_template.tex` | Cap. 2.2.2 "Presupuesto de Masa" (vacío) |
| `power_budget_template.tex` | Cap. 2.2.3 "Presupuesto de Potencia" (vacío) |
| `link_budget_template.tex` | Cap. 2.2.4 "Cálculo de Enlace" (vacío) |
| `ait_plan_template.tex` | Cap. 11.2/11.3 plan de pruebas AIT |

## Cómo usarlas

1. Copiar la plantilla relevante dentro de `00_documento_principal/chapters/0X_*.tex`.
2. **Reemplazar los valores TBD** con los datos reales de INTISAT (del Excel `03_recursos/presupuestos/Requerimiento de energía - INTISAT.xlsx` y mediciones del modelo de ingeniería).
3. Conservar la **estructura de tabla** (columnas, formato) — esa es la convención que APSCO y los jueces ECSS esperan ver.

## ⚠️ Importante

Esto NO es copia textual del FloripaSat-2. Solo se reutiliza el **esquema** y los **encabezados de tabla**. Los valores numéricos son placeholders/TBD que el equipo INTISAT debe llenar con sus datos.

Licencia del original: CC BY-SA 4.0 (SpaceLab UFSC).
