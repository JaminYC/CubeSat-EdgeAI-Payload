# Bibliografia — Inteligencia Artificial en operaciones espaciales

Compilacion de misiones, hardware, papers y empresas que aplican IA a bordo
de satelites y rovers, ordenadas por area de aplicacion. Curado para apoyar
el proyecto **CubeSat-EdgeAI-Payload** (microscopia FPM lensless con
procesamiento IA on-board en Raspberry Pi 5).

Ultima actualizacion: 2026-05-04.

---

## Indice

1. [Observacion de la Tierra](#1-observacion-de-la-tierra-eo)
2. [Plataformas reconfigurables (AI playground)](#2-plataformas-reconfigurables-ai-playground-en-orbita)
3. [Operaciones autonomas](#3-operaciones-autonomas-del-satelite)
4. [Mars y exploracion planetaria](#4-mars-y-exploracion-planetaria)
5. [ISS — robots con IA](#5-iss--robots-con-ia)
6. [Rendezvous, docking, landing autonomo](#6-rendezvous-docking-landing-autonomo)
7. [Astronomia y ciencia espacial](#7-astronomia-y-ciencia-espacial)
8. [Hardware AI usado en orbita](#8-hardware-ai-usado-en-orbita)
9. [Empresas y actores principales](#9-empresas-y-actores-principales)
10. [Frameworks open-source](#10-frameworks-y-herramientas-open-source)
11. [Papers de referencia (reviews)](#11-papers-de-referencia-reviews)
12. [Conferencias y workshops](#12-conferencias-y-workshops-dedicados)
13. [Datasets publicos](#13-datasets-publicos-para-entrenar-ia-espacial)
14. [Como se ubica el proyecto](#14-donde-se-ubica-cubesat-edgeai-payload)
15. [Lectura priorizada](#15-lectura-priorizada)

---

## 1. Observacion de la Tierra (EO)

El area mas activa de IA on-board: filtros de nubes, deteccion de cambios,
clasificacion de cultivos, monitoreo de incendios.

| Mision | Año | Que IA hace | Hardware | Link |
|---|---|---|---|---|
| **PhiSat-1** (ESA) | 2020 | filtra nubes con CNN antes de bajar imagenes | Intel Movidius Myriad 2 (1 W) | https://www.esa.int/Applications/Observing_the_Earth/Ph-sat |
| **PhiSat-2** (ESA) | 2024 | 6 apps de IA simultaneas (cambio detectado, water quality) | Intel Myriad X | https://www.esa.int/Applications/Observing_the_Earth/Phsat-2 |
| **HYPSO-1 / HYPSO-2** (NTNU Noruega) | 2022, 2024 | hiperspectral + onboard ML para detectar floraciones de algas | RPi CM4 | https://www.ntnu.edu/ie/smallsat |
| **Intuition-1** (KP Labs Polonia) | 2023 | IA hyperspectral on-board | Antelope edge processor (FPGA) | https://kplabs.space/intuition-1/ |
| **CogniSAT-6** (Aiko + Open Cosmos) | 2024 | primer satelite EO comercial con AI integrada | Movidius + custom | https://aikospace.com/cognisat-6/ |
| **Pleiades Neo** (Airbus) | 2021+ | clasificacion automatica + super-resolucion | propietario | https://www.intelligence-airbusds.com/pleiades-neo |
| **WorldView Legion** (Maxar) | 2024 | deteccion de objetos a bordo | propietario | https://www.maxar.com |

---

## 2. Plataformas reconfigurables (AI playground en orbita)

Satelites pensados para que cualquiera suba experimentos de IA.

| Mision | Quien | Para que | Link |
|---|---|---|---|
| **OPS-SAT** (ESA) | 2019-2024 | satelite plataforma para experimentos AI | https://www.esa.int/Enabling_Support/Operations/OPS-SAT |
| **OPS-SAT VOLT** (ESA) | 2024+ | sucesor de OPS-SAT | https://www.esa.int/Enabling_Support/Operations/OPS-SAT_VOLT |
| **D-Orbit ION SCV** | 2020+ | "satelite hostel" con AI a bordo | https://www.dorbit.space/ion-scv |
| **NASA STARLING** | 2023 | swarm autonomo de 4 CubeSats con AI distribuida | https://www.nasa.gov/smallsat-institute/sst-soa/starling |

---

## 3. Operaciones autonomas del satelite

| Aplicacion | Mision / proyecto | Que hace | Link |
|---|---|---|---|
| **Anomaly detection** | OPS-SAT, NASA cFS-AI | detecta fallos del bus antes que el OBC tradicional | https://www.esa.int/Enabling_Support/Operations/OPS-SAT |
| **Mission planning** | Aiko Mission Control AI | distribuye tareas en constelacion automaticamente | https://aikospace.com |
| **Self-healing FDIR** | NASA Resilient Spacecraft | reconfiguracion autonoma ante fallos | https://www.nasa.gov |
| **Cognitive radio** | NASA SCaN Testbed (ISS) | aprende interferencia y ajusta frecuencias | https://www.nasa.gov/scan |

---

## 4. Mars y exploracion planetaria

| Mision | IA on-board | Detalle |
|---|---|---|
| **Curiosity** (NASA, 2012-) | **AEGIS** desde 2016 | la rover elige autonomamente que rocas estudiar con ChemCam |
| **Perseverance** (NASA, 2021-) | **AutoNav** | conduccion autonoma con vision a 5 m/s. Triplica el ritmo vs teleop |
| **Ingenuity helicopter** (2021-2024) | navegacion vision-only | SLAM completo a bordo con IMU + camara |
| **PIXL** (Perseverance) | adaptive raster scanning con ML | optimiza secuencia de medidas espectrales |

Links:
- AEGIS paper: https://www.science.org/doi/10.1126/scirobotics.aan4582
- AutoNav: https://mars.nasa.gov/mars2020/mission/technology/
- Ingenuity: https://www.jpl.nasa.gov/news/ingenuity-tech-demo

---

## 5. ISS — robots con IA

| Robot | Quien | Que hace | Link |
|---|---|---|---|
| **Astrobee** (NASA) | desde 2019 | 3 robots free-flying con vision + planeamiento autonomo | https://www.nasa.gov/astrobee |
| **CIMON-2** (DLR Alemania) | desde 2019 | asistente AI en voz para astronautas, basado en Watson | https://www.airbus.com/en/cimon |
| **Robonaut 2** (NASA) | 2011-2018 | manipulacion humanoide con vision profunda | https://robonaut.jsc.nasa.gov |
| **Astro Pi** (ESA + RPi Foundation) | desde 2015 | dos Pi 4 en la ISS para experimentos estudiantiles + IA | https://astro-pi.org |

---

## 6. Rendezvous, docking, landing autonomo

| Mision | Año | Aplicacion |
|---|---|---|
| **Dragon (SpaceX)** | 2012- | docking automatico con vision + LIDAR |
| **Soyuz KURS-NA** | desde 2019 | estimacion de relativa con ML |
| **OSIRIS-REx** (NASA) | 2020 | TAGSAM: maniobra autonoma para tocar el asteroide Bennu |
| **HERA** (ESA, 2024-2026) | en vuelo | navegacion autonoma alrededor de Didymos |
| **Mars Sample Return** (NASA, plan) | 2030+ | rendezvous + docking en orbita marciana, todo autonomo |

---

## 7. Astronomia y ciencia espacial

| Telescopio | Que IA usa |
|---|---|
| **JWST** (NASA) | pipeline ML para clasificacion estelar y artefacto removal |
| **Euclid** (ESA) | clasificacion de morfologias galacticas con ML |
| **Kepler / TESS** | deteccion de exoplanetas con CNN (post-procesado) |
| **Roman Space Telescope** (NASA, 2027) | traccion de microlensing con IA tiempo real |

---

## 8. Hardware AI usado en orbita

| Chip | Donde se usa | Notas |
|---|---|---|
| **Intel Movidius Myriad 2 / X** | PhiSat, CogniSAT | el caballito de batalla. ~ 1 W. 1 TOPS |
| **Google Edge TPU (Coral)** | experimentos en LEO | testeado para radiacion por NASA y JAXA |
| **NVIDIA Jetson Nano/Orin** | algunos commercial sats | mas potente pero 5-10 W |
| **AMD Zynq Ultrascale+ MPSoC** | Mars rovers, Webb | radiation-hardened version |
| **Brainchip Akida** (neuromorphic) | testeo en orbita 2024 | spike-based, ultra bajo consumo |
| **KP Labs Antelope/Leopard** | Intuition-1 | FPGA + AI accelerators custom |
| **Ubotica CogniSAT-XE2** | varios | computer vision dedicado |
| **RPi 4 / Compute Module 4** | HYPSO-1, Astro Pi | COTS, no rad-hard, vida 1-3 años |

---

## 9. Empresas y actores principales

| Empresa | Que hace | Link |
|---|---|---|
| **ESA Φ-lab** | division de IA de ESA | https://philab.esa.int |
| **NASA Frontier Development Lab** | sprints anuales de IA aplicada al espacio | https://frontierdevelopmentlab.org |
| **Ubotica** (Irlanda) | hardware AI para PhiSat | https://ubotica.com |
| **KP Labs** (Polonia) | Antelope edge AI processor | https://kplabs.space |
| **Aiko Space** (Italia) | software AI mision control | https://aikospace.com |
| **Cognitive Space** (USA) | constelaciones autonomas | https://cognitivespace.com |
| **Open Cosmos** (UK) | satelite plataforma + AI | https://www.open-cosmos.com |
| **Spaceability AI** (UK) | dashboards AI para operadores | https://spaceability.com |
| **LeoLabs** (USA) | SDA (space domain awareness) con ML | https://leolabs.space |
| **Slingshot Aerospace** (USA) | digital twin de satelites con AI | https://slingshot.space |
| **D-Orbit** (Italia) | ION platform | https://www.dorbit.space |
| **Loft Orbital** (USA) | mision como servicio | https://loftorbital.com |
| **Spire Global** (USA) | constelacion 100+ CubeSats | https://spire.com |
| **Planet Labs** (USA) | Doves, 200+ CubeSats EO | https://www.planet.com |

---

## 10. Frameworks y herramientas open-source

| Tool | Para que | Link |
|---|---|---|
| **NASA cFS** | sistema operativo de vuelo + extensiones AI | https://github.com/nasa/cFS |
| **NASA F'** | framework usado en MarCO, Ingenuity | https://github.com/nasa/fprime |
| **ESA Onboard AI demos** | repositorio publico | https://gitlab.esa.int/PhiLab |
| **OpenVINO** | wrapper para deploy en Movidius | https://github.com/openvinotoolkit/openvino |
| **TensorFlow Lite Micro** | inferencia en MCU constrained | https://github.com/tensorflow/tflite-micro |
| **OreSat (PSAS)** | CubeSat 100% open: hardware, firmware, ground station | https://github.com/oresat |
| **UPSat (LSF Greece)** | otro CubeSat 100% open con docs operativas | https://gitlab.com/librespacefoundation/upsat |
| **CHIPLAB / SatNOGS DBs** | datasets de telemetria | https://db.satnogs.org |

---

## 11. Papers de referencia (reviews)

| Titulo | Año | Por que vale |
|---|---|---|
| *AI in Space: Opportunities and Challenges* (Furano et al., ESA) | 2020 | reporte oficial de ESA con todo el panorama |
| *A Survey of On-Board AI for Space Applications* (Salvo et al., IEEE) | 2023 | review tecnico exhaustivo |
| *Onboard AI for Earth Observation* (Esposito et al.) | 2022 | foco en EO especificamente |
| *Lessons from PhiSat-1* (Marcuccio et al.) | 2021 | post-mortem del primer satelite IA |
| *Edge ML for Space Systems* (Kabir et al.) | 2024 | hardware comparison para edge ML en orbita |
| *Cognitive Space Systems: state-of-the-art and challenges* (Ortiz et al.) | 2023 | autonomia, FDIR, cognitive radio |
| *State of the Art of CubeSats* (Bouwmeester et al.) | 2010, actualizado | el clasico panorama general de CubeSats |
| *Why CubeSats Fail* (Swartwout, IEEE Aerospace) | 2018 | top 10 razones reales de fallos |

Buscar texto completo en:
- https://arxiv.org
- https://digitalcommons.usu.edu/smallsat/

---

## 12. Conferencias y workshops dedicados

| Evento | Foco | Link |
|---|---|---|
| **OBDP** (On-Board Data Processing) | bianual ESA, lo mas alineado a IA on-board | https://obdp2024.sciencesconf.org |
| **AI4Space** (CVPR / ICCV) | computer vision para espacio | https://aiforspace.github.io |
| **SmallSat USU** | el grande, todo lo de SmallSat | https://digitalcommons.usu.edu/smallsat |
| **Space Computing Conference** (NASA) | hardware a bordo | https://nepp.nasa.gov |
| **EDHPC** (European Data Handling and Data Processing) | bianual europea | https://www.edhpc-conference.com |
| **IAC** (International Astronautical Congress) | mas politico/comercial | https://www.iafastro.org |
| **IEEE Aerospace Conference** | papers tecnicos | https://www.aeroconf.org |

---

## 13. Datasets publicos para entrenar IA espacial

| Dataset | Que tiene | Link |
|---|---|---|
| **Sentinel-2** | imagenes EO multiespectral | https://scihub.copernicus.eu |
| **Landsat** | imagenes EO 50 años | https://earthexplorer.usgs.gov |
| **PROBA-V Cloud Detection** | el dataset que entreno PhiSat-1 | https://kelvins.esa.int/proba-v-super-resolution/ |
| **Mars Curiosity images** | NASA Planetary Data System | https://pds.nasa.gov |
| **SatNOGS Network** | telemetria CubeSat | https://network.satnogs.org |
| **xView2 / xBD** | damage assessment EO | https://xview2.org |
| **EuroSAT** | clasificacion de cobertura terrestre | https://github.com/phelber/EuroSAT |
| **BigEarthNet** | Sentinel-2 con labels | https://bigearth.net |

---

## 14. Donde se ubica CubeSat-EdgeAI-Payload

El proyecto entra en:

a) **Categoria**: Earth Observation con IA on-board, pero aplicada a
**microscopia biologica** en lugar de imagenes terrestres. Es un nicho
menos poblado.

b) **Antecedentes directos**:
- **PharmaSat / GeneSat** (NASA Ames, 2006-2009): microscopia biologica en
  CubeSat sin IA on-board. Capturan imagenes y bajan crudo.
- **PhiSat-1** (ESA, 2020): IA en orbita por primera vez, pero para EO.
- **HYPSO-1** (NTNU, 2022): RPi CM4 con IA on-board, modelo similar de hardware.

c) **Lo que aporta el proyecto**: pipeline IA completo (segmentacion, mejora,
medicion) en payload de microscopia, no solo captura. Combina la linea
biologica de NASA Ames con el paradigma de PhiSat.

d) **Lo que falta para estar al nivel SOTA**:
- Migrar a hardware certificado para vuelo (Movidius o Antelope, no RPi de desarrollo).
- Tests TVAC / vibracion / radiacion.
- Demostrar uplink/downlink real a una ground station.
- Compararse con un sistema de referencia comercial (Ubotica CogniSAT-XE2).

e) **Nicho diferencial frente a la competencia**:
- Imaging biologico, no EO.
- Lensless con OLED programable (apertura sintetica, no comun en mision).
- Pipeline IA con multiples modelos (StarDist + Real-ESRGAN + N2V) en un solo Pi.
- Open-source (a diferencia de los comerciales).

---

## 15. Lectura priorizada

Si tenes tiempo limitado, en este orden:

1. **PhiSat-1 paper** (Marcuccio 2021) — el caso emblematico mas cercano al proyecto.
2. **Furano et al. AI in Space** (ESA review) — el panorama completo en un PDF.
3. **OBDP 2024 proceedings** — lo mas actual.
4. **HYPSO papers** (NTNU) — usan RPi CM4 con AI, hw mas cercano al nuestro.
5. **AI4Space workshop papers** — repositorio de ideas + benchmarks.
6. **Why CubeSats Fail** (Swartwout) — para evitar errores tipicos.
7. **Bouwmeester State of the art of CubeSats** — fundamentos.

---

## Como mantener este archivo

Cuando alguien del equipo descubra una referencia nueva relevante:

1. Identificar a que seccion pertenece (1-13).
2. Agregar fila a la tabla con fecha, descripcion y link.
3. Si es un paper especialmente importante, sumarlo al ranking de la
   seccion 15.
4. Commit + push.

Si la referencia es de un area nueva no contemplada, abrir una seccion
nueva manteniendo el formato consistente.
