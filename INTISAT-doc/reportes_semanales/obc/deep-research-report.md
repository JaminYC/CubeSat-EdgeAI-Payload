# Revisión técnica del OBC de INTISAT basada en archivos del usuario

## Alcance y disponibilidad de fuentes
El alcance que has pedido es muy específico: **usar únicamente la información disponible en tus archivos vinculados a esta cuenta** (sin complementar con web u otras fuentes externas). En este momento, **no hay archivos adjuntos en esta conversación ni fuentes conectadas/consultables** desde las que pueda extraer evidencias textuales y, por lo tanto, **no puedo hacer todavía el análisis técnico ni aportar citas** “precisas a los archivos” como solicitas.

Esto no es un problema de “falta de tiempo”, sino de **ausencia de material fuente accesible** en el chat. En cuanto compartas los documentos (subiéndolos aquí o habilitando una fuente conectada), puedo producir el informe completo con trazabilidad y citas.

## Evidencias necesarias para cubrir todo lo que pides
Para poder revisar “TODO lo relacionado con el OBC” con el nivel de detalle que pides (hardware, buses, modos, protocolos, validación, integración y tus contribuciones), necesito que el material incluya —idealmente— los siguientes tipos de documentos del proyecto:

Documentación de arquitectura y roles:
- **Diagrama/Documento de arquitectura del satélite** (bloques, topología, roles del OBC, subsistemas y responsabilidades).
- **ICD / Interface Control Document** (OBC ↔ EPS/ADCS/COM-UHF/COM-SBand/PCU/payload), con señales, buses, tramas y límites.

Documentación de hardware del OBC:
- **Esquemáticos** (PDF) y, si existe, **lista de materiales (BOM)**.
- **Diseño de PCB** (PDF de capas / gerbers exportados o reportes de CAD) y notas de diseño (impedancias, length matching, conectores, protecciones).
- **Datasheets** o notas internas (si están en tu repositorio) para componentes clave: MCU, memorias, aisladores, transceptores CAN/UART, sensores, etc.

Documentación de software/firmware del OBC:
- Arquitectura de firmware (tareas/RTOS si aplica), drivers de buses, manejo de modos, watchdog, bootloader, logging.
- Mapa de telemetría/housekeeping y manejo de eventos/fallas.

Protocolos y operación de misión:
- **Especificación del protocolo interno** (OBC ↔ subsistemas): trama, campos, CRC, secuencias, CMD_ID, tipos de mensaje.
- **Especificación del protocolo externo** (misión ↔ estación): servicios/subservicios, APIDs/IDs, telecommands, ACK/responses, file transfer, etc.
- Procedimientos de operación (nominal, safe mode, reset report, contingencias).

Validación e integración:
- Planes/procedimientos de prueba (unit, integration, thermal/vac si aplica), reportes de resultados, logs de pruebas, checklists de integración.

Si solo tienes 1–2 documentos (por ejemplo un PDF de protocolo y un CV), aún puedo hacer un informe útil, pero quedará necesariamente **incompleto** (y lo marcaré en “vacíos de información”).

## Metodología de análisis que aplicaré en cuanto tenga los archivos
Cuando subas los documentos, haré un análisis “tipo auditoría técnica” para que cada afirmación importante quede respaldada por citas. En concreto:

Primero, construiré un **mapa de evidencias**: qué documento define cada cosa (p. ej., “trama interna”, “IDs de comando”, “MCU”, “ensayo CAN”, “safe mode”). Después, extraeré la información y la organizaré en secciones alineadas con tus puntos: rol, arquitectura, hardware, buses, comunicación con subsistemas, modos, housekeeping, telemetría/TC, eventos, safe mode/reset report, protocolos interno/externo, y validación/integración.

Luego, crearé una **matriz de trazabilidad** para que sea fácil verificar:
- Requisito o elemento (p. ej. “CRC16 del protocolo interno”)
- Detalle encontrado (p. ej. “polinomio, init, endianess, cobertura del CRC”)
- Fuente exacta (documento y líneas citadas)

Finalmente, cerraré con **resumen ejecutivo**, **vacíos de información** y la **tabla Elemento / Detalle / Fuente** que has pedido.

## Plantilla del informe que produciré
En cuanto tenga los archivos, el informe final estará estructurado (en español técnico, claro, y con citas) con esta lógica:

Rol del OBC dentro del satélite:
- Funciones del OBC y límites (qué controla y qué no)
- Relación maestro/esclavo si existe y responsabilidades por subsistema

Arquitectura general del OBC:
- Diagrama lógico (tareas, servicios, estados/modos)
- Arquitectura de comunicaciones internas y externas
- Gestión de tiempo, watchdog, reset causes, persistencia, etc.

Hardware asociado al OBC:
- Microcontrolador (modelo, razones si aparecen, periféricos usados)
- Memorias (tipo, buses, particiones si existen)
- Sensores (qué mide el OBC y por qué)
- Aisladores/protecciones (aislamiento, ESD, transceptores)
- PCB (capas, reglas críticas, conectividad, conectores)
- Interfaces eléctricas (niveles lógicos, alimentación, líneas críticas)

Buses y protocolos:
- CAN / I2C / SPI / UART (y otros si aparecen)
- Parámetros: velocidades, topología, direccionamiento, tramas, arbitraje, timeouts, retries

Comunicación OBC ↔ subsistemas:
- EPS, ADCS, COM-UHF, COM-SBand, payload controller
- Qué mensajes/telemetrías intercambian y con qué periodicidad
- Gestión de fallos de enlace por subsistema

Operación: modos, housekeeping, telemetría, telecomandos, eventos:
- Definición exacta de modos (nominal/safe/otros)
- Contenido y frecuencia de housekeeping
- Catálogo de eventos y severidades
- Reset report y sus campos (causas, contadores, uptime, modo previo)

Protocolo interno:
- Estructura de trama, campos, CMD_ID, tipos de mensaje, CRC, secuencia/correlación
- Reglas de compatibilidad (versionado, MTU/longitud, endianess)
- Requisitos de robustez (duplicados, pérdidas, replay)

Protocolo externo (misión):
- Servicios/subservicios relevantes al OBC
- Identificadores (APID u otros) y ruteo (UHF/S-Band si aplica)
- ACK/Response y correlación (TXN_ID o equivalente)

Validaciones, pruebas e integración:
- Evidencias de tests (qué se probó, cómo, resultados)
- Integración con subsistemas y lecciones aprendidas

Contribuciones del usuario:
- Qué diseñaste/implementaste (hardware/firmware/protocolo/pruebas)
- Alcance, responsabilidades y entregables mencionados

## Vacíos de información actuales
Actualmente el vacío es total por falta de acceso a documentos: no dispongo de ninguna especificación, esquema, ICD, protocolo o reporte de pruebas dentro del chat/fuentes conectadas, así que no puedo afirmar nada sobre el OBC de INTISAT sin incumplir tu requisito de “solo archivos” y sin poder citar.

En la práctica, cuando se comparten pocos documentos, los vacíos más frecuentes que suelen quedar (y que marcaré explícitamente si ocurre) son: pinout y niveles eléctricos, parámetros exactos de buses (bitrate, pull-ups, terminación), tablas completas de telemetría, definición precisa de modos y transiciones, cobertura real de pruebas y resultados, y justificación de decisiones de diseño.

## Tabla de elemento, detalle y fuente
| Elemento | Detalle encontrado | Fuente |
|---|---|---|
| Rol del OBC | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Arquitectura general del OBC | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Microcontrolador | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Memorias | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Sensores | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Aisladores | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| PCB e interfaces eléctricas | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| CAN / I2C / SPI / UART | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| OBC ↔ EPS/ADCS/COM/payload | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Modos, HK, TM/TC, eventos, safe, reset report | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Protocolo interno (trama, campos, CMD_ID, CRC, secuencias) | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Protocolo externo (misión) | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Validaciones e integración | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |
| Contribuciones del usuario | No disponible: no hay documentos accesibles en el chat/fuentes conectadas. | — |

## Resumen ejecutivo
No puedo aún ejecutar la revisión “deep research” del OBC de INTISAT bajo tu condición de **usar solo tus archivos** y **citar cada afirmación**, porque **no hay archivos accesibles** en esta conversación ni fuentes conectadas consultables. En cuanto compartas los PDFs/documentos (idealmente protocolo/ICD + esquemáticos/PCB + pruebas), puedo producir el informe completo con secciones técnicas, citas precisas y la tabla final de trazabilidad.