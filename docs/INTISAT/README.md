# INTISAT — Documentación oficial (INRAS – PUCP)

Documentación de misión del nanosatélite **INTISAT**, desarrollado por el **Instituto de Radioastronomía – PUCP**.
Sigue la filosofía de documentación abierta del proyecto [FloripaSat-2](https://github.com/spacelab-ufsc/floripasat2-doc) adaptada a la misión peruana INTISAT.

## 🛰️ Resumen de la misión

INTISAT es un nanosatélite 2U-CubeSat de demostración tecnológica para integrar y validar subsistemas desarrollados en PUCP:
- **Payload de microscopía digital CMOS** (lensless / contact)
- **Payload de aceleración IA en órbita** (super-resolución)
- **Bus modular** (OBC, EPS, TTC, ADCS, TCS)
- **Segmento Tierra (AYNISAT)** para telemetría y control autónomos

Sigue estándares NASA-SP-2007-6105, ECSS-E-ST-10C, PMBOK 7, CCSDS 133.0-B-2.

---

## 📂 Estructura del repositorio

```
INTISAT-doc/
│
├── 00_documento_principal_ES/     Master CDR integrador EN ESPAÑOL (main.tex + 12 caps)
│   ├── main.tex                   Documento maestro (\selectlanguage{spanish})
│   ├── main.pdf                   PDF compilado (41 páginas)
│   ├── chapters/                  Capítulos 01–12
│   ├── appendices/                Referencias y anexos
│   ├── figures/                   Figuras del documento principal
│   ├── references/, header/
│   ├── pucp_intisat.sty           Estilo PUCP/INRAS
│   └── Makefile
│
├── 00_documento_principal_EN/     Master CDR integrador IN ENGLISH (parallel version)
│   ├── main.tex                   Master document (\selectlanguage{english})
│   ├── main.pdf                   Compiled PDF (41 pages)
│   ├── chapters/                  Chapters 01–12
│   ├── appendices/                References and annexes
│   └── figures/                   Same shared figures
│
├── 01_CDRs_subsistemas/           CDRs detallados por subsistema (Fase C)
│   ├── 00_System/                 INTI-C-00.00-CDR  (System-level)
│   ├── 01_OBC/                    INTI-C-01.00-OBC-CDR  ← ACTIVO
│   ├── 02_UHF/                    INTI-C-02.00-UHF-CDR  ← ACTIVO (era COMM)
│   ├── 03_EPS/                    INTI-C-03.00-EPS-CDR  ← ACTIVO
│   ├── 04_Payload_Microscopia/    INTI-C-05.02-CMOSM-CDR  ← ACTIVO
│   └── _planificados/             ADCS, TCS, Structure, Payload_ODS/LLPC/AI
│   ├── 03_EPS/                    INTI-C-03.00-EPS-CDR
│   ├── 04_ADCS/                   INTI-C-04.00-ADCS-CDR
│   ├── 05.00_Payload_ODS/         INTI-C-05.00-ODS-CDR
│   ├── 05.01_Payload_LLPC/        INTI-C-05.01-LLPC-CDR
│   ├── 05.02_Payload_Microscopy/  INTI-C-05.02-CMOSM-CDR
│   ├── 05.03_Payload_AI/          INTI-C-05.03-SAI-CDR
│   ├── 07_Structure/              INTI-C-07.00-STR-CDR
│   └── 09_TCS/                    INTI-C-09.00-TCS-CDR
│
├── 02_reportes_semanales/         Reportes semanales por subsistema
│   ├── _plantilla/
│   ├── obc/
│   ├── eps/
│   ├── payload_microscopia/
│   └── intisat_ism_latex_project/
│
├── 03_recursos/                   Insumos y referencias
│   ├── presupuestos/              Requerimiento de energía (xlsx)
│   ├── presentaciones/            Slides INTISAT (EPS, máquinas de estado, redes…)
│   ├── plantillas_tex/            plantilla_*.tex y report_template
│   ├── cad/                       PCB.step y modelos CAD
│   ├── entregables/               Avances de proyecto, instrucciones
│   ├── imagenes_referencia/       Fotos, capturas, imágenes
│   └── referencias_externas/      FloripaSat extract, astrometry.net
│
├── 04_exports_word/               Exports a Word (.docx)
├── 05_exports_pdf/                PDFs exportados / versiones consolidadas
│   ├── main_CDR.pdf
│   ├── INTISAT_Documentacion.pdf
│   └── Estructura_general_INTISAT.pdf
│
├── tools/                         Scripts auxiliares (Python / shell)
│   ├── convert_*.py               Conversores Pandoc / PDF / Word
│   ├── extract_toc.py
│   ├── generate_templates.py
│   └── gen_intisat_cdrs.sh
│
├── 06_quarantine/                 Archivos sospechosos / duplicados
│                                  (revisar antes de borrar manualmente)
│
└── 99_no_relacionado/             Material NO INTISAT (cursos, IDE installer, etc.)
                                   Mover fuera del repo cuando se confirme.
```

---

## 🧠 Estándares y referencias

| Estándar | Aplicación |
|-----------|--------------|
| NASA-SP-2007-6105 Rev2 | Systems Engineering Handbook |
| ECSS-E-ST-10C | Space Engineering – System Engineering |
| ECSS-M-ST-40 Rev1 | Space Project Management |
| ISO 21502:2020 | Project Management |
| PMBOK 7th Edition | Methodology for project processes |
| CCSDS 133.0-B-2 | Telemetry & Telecommand standard |

---

## 🧰 Cómo compilar el documento principal

**Versión en español:**
```bash
cd 00_documento_principal_ES/
make            # o pdflatex main.tex (2 pasadas para refs cruzadas)
```
PDF generado: `00_documento_principal_ES/main.pdf`

**Versión en inglés (para APSCO Xi'an):**
```bash
cd 00_documento_principal_EN/
pdflatex main.tex && pdflatex main.tex
```
PDF generado: `00_documento_principal_EN/main.pdf`

---

## 📘 Licencia

Documentación liberada bajo **Creative Commons Attribution–ShareAlike 4.0 (CC BY-SA 4.0)**.

**Autor:** Instituto de Radioastronomía – PUCP (INRAS)
