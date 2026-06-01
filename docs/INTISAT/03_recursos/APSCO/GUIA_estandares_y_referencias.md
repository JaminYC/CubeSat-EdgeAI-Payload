# Guía de estándares y referencias — INTISAT @ APSCO ACC

**Propósito:** mapa rápido para saber *qué se espera entregar en Xi'an Aug-2026* y *dónde mirarlo* mientras se llenan los capítulos del CDR INTISAT.

---

## 1. El evento

| Campo | Valor |
|---|---|
| Evento | APSCO ACC Project Summer Camp |
| Fechas | 12–25 agosto 2026 |
| Lugar | Xi'an, China |
| Organización | APSCO Secretariat (Beijing) |
| Documento oficial | [`APSCO_Invitacion_Summer_Camp_Xian_2026.pdf`](APSCO_Invitacion_Summer_Camp_Xian_2026.pdf) |
| Contacto | Ms. Mu Zi Xiong "Charis" — charis@apsco.int — +86 10 6370 2677 ext. 304 |

---

## 2. Equipo de referencia (ya copiamos su estructura)

**FloripaSat-2 / GOLDS-UFSC** — CubeSat 2U de la UFSC (Brasil), ya en órbita.

- Repo: https://github.com/spacelab-ufsc/floripasat2-doc
- Documento extraído localmente: [`../referencias_externas/floripa_output.txt`](../referencias_externas/floripa_output.txt) (7578 líneas)
- Plantillas adaptadas: [`../referencias_externas/floripasat2_plantillas/`](../referencias_externas/floripasat2_plantillas/)
  - `mass_budget_template.tex`
  - `power_budget_template.tex`
  - `link_budget_template.tex`
  - `ait_plan_template.tex`

**Otros CubeSats de universidades asiáticas con docs públicas:**
- BIRDS-3 / BIRDS-4 (Kyutech, Japón)
- NepaliSat-1 (Nepal, vía Kyutech)
- PSAT (PIAS, Pakistán) — ganador APSCO previo

---

## 3. Estándares aplicables (qué pide cada capítulo)

| # | Capítulo INTISAT | Estándar primario | Estado |
|---|---|---|---|
| 1 | Misión, ConOps | NASA-SP-2007-6105 §4 | 🟢 Hecho (traducido) |
| 2 | Arquitectura + presupuestos (masa, potencia, link) | ECSS-E-ST-10C §5; SMAD/Wertz §10 | 🔴 Plantillas listas, llenar valores |
| 3 | OBC / OBDH | ECSS-E-ST-50; ECSS-Q-ST-60 (componentes) | 🟡 Unificar modos pendiente |
| 4 | EPS | ECSS-E-ST-20; Wertz §11 | 🔴 Fase C vacío; CDR principal OK |
| 5 | ADCS | ECSS-E-ST-60; Wertz §19 | 🟢 No prioritario (pasivo) |
| 6 | TTC | CCSDS 133.0-B-2; CCSDS 232.0-B (TM); IARU coord | 🟡 Ventana silencio pendiente |
| 7 | Payload | (específico al instrumento) | 🟡 Microscopía + IA en CDRs Fase C |
| 8 | Estructura | CubeSat Design Spec Rev 14 (Cal Poly); GSFC-STD-7000 | 🟡 Renombrar |
| 9 | TCS | ECSS-E-ST-31 | 🟢 No prioritario |
| 10 | Segmento tierra | CCSDS; IARU UHF/VHF | 🟡 OK |
| 11 | AIT | ECSS-E-ST-10-02; ECSS-E-ST-10-03; GSFC-STD-7000 | 🔴 Plantilla lista, llenar |
| 12 | Gestión | PMBOK 7 / ECSS-M-ST-40; ISO 21502 | 🟡 OK |

---

## 4. Estándares clave — qué define cada uno

### NASA-SP-2007-6105 Rev2 — *NASA Systems Engineering Handbook*
Bíblia para estructurar un CDR. Define:
- Fases del proyecto (Pre-A, A, B, C, D, E, F)
- V-Model de verificación
- Estructura de Mission Concept Review → SRR → PDR → **CDR** → FRR
- Documentos esperados en cada hito

### ECSS-E-ST-10C — *Space Engineering – System Engineering*
Estándar europeo equivalente a NASA Handbook. Adoptado por APSCO. Define:
- Requerimientos a nivel sistema y subsistema
- Trazabilidad de requerimientos (matriz de cumplimiento)
- Definición de interfaces (ICDs)
- Presupuestos técnicos

### CubeSat Design Specification (CDS) Rev 14
Cal Poly SLO. Define **el formato físico**:
- 2U = 100 × 100 × 227 mm
- Masa máxima 2.66 kg
- Tolerancias de envolvente
- Kill-switches obligatorios
- Materiales aceptables (Al-7075-T73, Al-6061-T6)
- Tests obligatorios (vibración, masa, fit-check)

📌 **Crítico para INTISAT** — incluir referencia explícita en Cap. 8 (Estructura).

### CCSDS 133.0-B-2 — *Space Packet Protocol*
Estándar de paquetización de telemetría/comandos. Define:
- Estructura del paquete espacial (APID, secuencia, timestamp)
- Coordinación con AX.25 (radioafición CubeSat)
- Frame format

📌 Cap. 6 (TTC) y Cap. 10 (Segmento tierra) deben citarlo.

### GSFC-STD-7000 — *General Environmental Verification Standard (GEVS)*
Define los perfiles de **prueba ambiental** para hardware espacial:
- Vibración random (perfil "minimum workmanship")
- Shock pirotécnico
- Ciclos térmicos (rangos típicos)
- TVAC duración mínima

📌 Crítico para Cap. 11 (AIT).

### PMBOK 7 / ISO 21502:2020
Gestión de proyectos para Cap. 12 (WBS, hitos, riesgo, cronograma).

### Wertz — *Space Mission Analysis and Design (SMAD)*
Libro canónico. Secciones más usadas en INTISAT:
- §10 Power systems (presupuesto de potencia, sizing de batería)
- §11 EPS detail
- §13 Link budget (uplink/downlink)
- §19 ADCS

---

## 5. Qué APSCO usualmente exige (basado en convocatorias ACC previas)

### Documentación
- ✅ CDR completo (este `main.tex` integrado)
- ✅ CDRs por subsistema (carpeta `01_CDRs_subsistemas/`)
- ✅ Presupuestos masa/potencia/enlace **firmados** con margen
- ✅ Plan de AIT detallado
- ✅ ICDs (Interface Control Documents) entre subsistemas
- ✅ Plan de gestión (WBS, riesgo, hitos)

### Hardware
- ✅ **Engineering Model** físico funcional (no necesariamente flight)
- ✅ Demostración FlatSat
- 🟡 Resultados parciales de pruebas ambientales (idealmente)

### Presentación
- ✅ Slide deck (~30–45 min de presentación + Q&A)
- ✅ Resumen ejecutivo de 1–2 páginas
- ✅ Mission patch / branding del equipo

### Coordinación
- 🟡 Asignación de frecuencias UHF/VHF (IARU coordination iniciada)
- 🟡 Carta de intención con un lanzador (TBD)

---

## 6. Cómo trabajar con esta guía

1. **Para cada capítulo del CDR**, mirar la columna "Estándar primario" y el extracto del FloripaSat-2.
2. **Para presupuestos**, copiar las plantillas de [`../referencias_externas/floripasat2_plantillas/`](../referencias_externas/floripasat2_plantillas/) directamente al capítulo y reemplazar TBD con datos reales.
3. **Para AIT**, seguir la secuencia de pruebas del FloripaSat-2 (probada y aceptada por APSCO).
4. **Para presentación**, usar la estructura de `1 mission → 2 system → 3 subsystems → 4 budgets → 5 AIT → 6 management → 7 demo`.

---

## 7. Cronograma sugerido hasta Xi'an (1 jun → 12 ago, ~10 semanas)

| Semana | Bloque | Responsable |
|---|---|---|
| 1–2 | Cerrar Cap. 2 (presupuestos) + Fase C EPS | Equipo EPS |
| 3–4 | Cerrar Cap. 3 (OBC) y Fase C OBC; Cap. 11 (AIT plan) | Equipo OBC + Sistemas |
| 5–6 | Pruebas FlatSat + integración hardware | Todo el equipo |
| 7 | Pruebas vibración + térmicas (lo que se pueda) | Sistemas |
| 8 | Cierre del CDR integrado, freeze de docs | Líder de proyecto |
| 9 | Slide deck final + rehearsal | Líder presentador |
| 10 | Empaquetado, logística viaje, contingencia | Todos |

---

**Última actualización:** ver `git log` del repo.
