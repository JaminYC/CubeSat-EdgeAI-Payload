# INTISAT Project Documentation (INRAS – PUCP)

This repository contains the **official mission documentation** of the INTISAT nanosatellite developed by the **Instituto de Radioastronomía – PUCP**.

It follows the structure and open-science philosophy of the [FloripaSat-2](https://github.com/spacelab-ufsc/floripasat2-doc) project (SpaceLab–UFSC), adapting it to the Peruvian CubeSat INTISAT mission.

---

## 🛰️ Overview

**INTISAT** is a nanosatellite technology demonstration mission whose objective is to integrate and validate multiple PUCP-developed subsystems:
- A **CMOS-based digital microscopy payload**.
- A modular **bus platform** (EPS, OBC, TTC).
- A **ground segment (AYNISAT)** for autonomous telemetry and control.

The mission follows international standards (NASA–ECSS) for documentation and verification.

---

## 🧩 Repository Structure

INTISAT-doc/
├── chapters/ # Technical chapters (CONOPS, System Design, etc.)
├── figures/ # Schematics, diagrams, photos
├── appendices/ # Experimental results, logs
├── references/ # Bibliographic and normative references
├── header/ # Cover pages, templates
├── main.tex # Master LaTeX document
├── pucp_intisat.sty # PUCP style file
├── Makefile # Compile script
└── README.md # This file


---

## 🧠 Standards and References

| Standard | Application |
|-----------|--------------|
| NASA-SP-2007-6105 Rev2 | Systems Engineering Handbook |
| ECSS-E-ST-10C | Space Engineering – System Engineering |
| ECSS-M-ST-40 Rev1 | Space Project Management |
| ISO 21502:2020 | Project Management |
| PMBOK 7th Edition | Methodology for project processes |
| CCSDS 133.0-B-2 | Telemetry & Telecommand standard |

---

## 📘 License

All documentation is released under the **Creative Commons Attribution–ShareAlike 4.0 International License (CC BY-SA 4.0)**.

---

## 🧰 How to Compile

Install LaTeX (Linux or Windows WSL):

```bash
sudo apt install texlive-full latexmk
make
The resulting document will be:

slb-intisat-doc-v0.1.pdf
Author:

Instituto de Radioastronomía – PUCP (INRAS)


---

## ✅ SIGUIENTE PASO

1. Copia y pega estos contenidos en los archivos respectivos.  
2. Guarda todo y ejecuta:

   ```bash
   make