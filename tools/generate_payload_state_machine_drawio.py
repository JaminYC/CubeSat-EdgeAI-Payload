"""Genera un drawio XML con la maquina de estados del payload de
microscopia FPM del INTISAT, en el mismo formato visual que el de
OBC (estilo "HW State Machine - Neils Vilchez").

El payload corre en la Raspberry Pi CM5 y se activa cuando el OBC
entra en Estado F (adquisicion solar y payload).

Salida: Documentos de Referencia/Diagramas/Maquina_Estados_Payload_INTISAT.drawio
"""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "Diagramas" / "Maquina_Estados_Payload_INTISAT.drawio"


COLOR_INIT     = "#FFF8DC"
COLOR_INIT_S   = "#D4AC0D"
COLOR_CAL      = "#E8DAEF"   # violeta claro: calibracion
COLOR_CAL_S    = "#7D3C98"
COLOR_OPS      = "#D5F5E3"   # verde claro: operacion / captura / proceso
COLOR_OPS_S    = "#27AE60"
COLOR_COMM     = "#D6EAF8"   # azul claro: downlink
COLOR_COMM_S   = "#2E86C1"
COLOR_SAFE     = "#FADBD8"   # rojo claro: safe / error
COLOR_SAFE_S   = "#C0392B"


def state_value(title: str, entry: list[str], exit_: list[str]) -> str:
    entry_html = "<br>".join(escape(c) for c in entry)
    exit_html  = "<br>".join(escape(c) for c in exit_)
    return (
        f"<b><u>{escape(title)}</u></b>"
        f"<br><br>"
        f"<u>Entry Condition:</u><br>"
        f"{entry_html}"
        f"<br><br>"
        f"<u>Exit Condition:</u><br>"
        f"{exit_html}"
    )


STATES = [
    dict(
        id="P_OFF", title="OFF: Payload apagado",
        x=80, y=60, w=240, h=220,
        fill=COLOR_INIT, stroke=COLOR_INIT_S,
        entry=[
            "OBC fuera de Estado F",
            "CM5 sin alimentacion",
            "Camara, LEDs y FPGA OFF",
            "ECB irrelevante (no consumo)",
        ],
        exit=[
            "CMD_PL_ON recibido del OBC",
            "(OBC en Estado F + EHPC = 1)",
            "Alimentar CM5 -> ir a BOOT",
        ],
    ),
    dict(
        id="P_BOOT", title="BOOT: Arranque CM5 y drivers",
        x=400, y=60, w=240, h=220,
        fill=COLOR_INIT, stroke=COLOR_INIT_S,
        entry=[
            "CMD_PL_ON activo, alimentando",
            "CM5 booteando Linux + daemon",
            "T = 0s, BOOT_OK = 0",
            "Cargar drivers camara, LEDs",
        ],
        exit=[
            "T <= T_BOOT (timeout 60s)",
            "BOOT_OK = 1, daemon arriba",
            "Drivers cargados sin errores",
            "ERR_BOOT_PL = 0",
        ],
    ),
    dict(
        id="P_CAL", title="CAL: Calibracion optica",
        x=720, y=60, w=240, h=240,
        fill=COLOR_CAL, stroke=COLOR_CAL_S,
        entry=[
            "BOOT_OK = 1",
            "Camara y LEDs respondiendo",
            "TEMP_CMOS dentro de rango",
            "(verificar -10C a 40C)",
        ],
        exit=[
            "CAM_OK = 1 (test pattern OK)",
            "LED_OK = 1 (todos LEDs probados)",
            "FOCUS_OK = 1 (autofocus listo)",
            "-> ir a IDLE",
        ],
    ),
    dict(
        id="P_IDLE", title="IDLE: Espera comando",
        x=1040, y=60, w=240, h=220,
        fill=COLOR_OPS, stroke=COLOR_OPS_S,
        entry=[
            "CAL completa, todo nominal",
            "Buffers vacios, disco con espacio",
            "DISK_OK = 1, ECB = 1",
            "Consumo bajo (~3W)",
        ],
        exit=[
            "CMD_CAP -> ir a WARMUP",
            "OR CMD_DL + BS_READY -> DLPREP",
            "OR ECB = 0 -> ir a LP",
            "OR ERR_* = 1 -> ir a ERR",
        ],
    ),
    dict(
        id="P_WARM", title="WARMUP: Estabilizacion termica",
        x=1040, y=340, w=240, h=200,
        fill=COLOR_OPS, stroke=COLOR_OPS_S,
        entry=[
            "CMD_CAP recibido",
            "T_WARM = 0s",
            "Encender LED array progresivo",
            "Monitorear TEMP_CMOS, TEMP_LED",
        ],
        exit=[
            "T_WARM >= T_w (~30s)",
            "TEMP_CMOS estable",
            "TEMP_LED estable",
            "-> ir a CAPT",
        ],
    ),
    dict(
        id="P_CAPT", title="CAPT: Captura FPM",
        x=1360, y=340, w=240, h=220,
        fill=COLOR_OPS, stroke=COLOR_OPS_S,
        entry=[
            "WARMUP OK, sistema termico",
            "N_CAP = 0, N_TARGET = 49..225",
            "(secuencia LED de N angulos)",
            "Camara en modo captura RAW",
        ],
        exit=[
            "N_CAP = N_TARGET",
            "(secuencia FPM completa)",
            "IMG_BUF lleno, listo procesar",
            "-> ir a PROC",
        ],
    ),
    dict(
        id="P_PROC", title="PROC: Procesamiento FPM + IA",
        x=1680, y=340, w=240, h=240,
        fill=COLOR_OPS, stroke=COLOR_OPS_S,
        entry=[
            "IMG_BUF completo (N_TARGET img)",
            "Iniciar reconstruccion FPM",
            "Luego Real-ESRGAN super-resol.",
            "GPU CM5 activa (~6W extra)",
        ],
        exit=[
            "PROC_DONE = 1",
            "Imagen reconstruida + SR lista",
            "OR ERR_PROC = 1 -> ir a ERR",
            "-> ir a STORE",
        ],
    ),
    dict(
        id="P_STORE", title="STORE: Almacenamiento",
        x=1680, y=60, w=240, h=200,
        fill=COLOR_OPS, stroke=COLOR_OPS_S,
        entry=[
            "PROC_DONE = 1",
            "Imagen final + metadata listas",
            "Compresion (PNG/JPEG-XL)",
            "Calcular checksum CRC32",
        ],
        exit=[
            "Archivo escrito a disco",
            "DISK_OK actualizado",
            "Log entry registrada",
            "-> volver a IDLE",
        ],
    ),
    dict(
        id="P_DLPREP", title="DLPREP: Preparacion downlink",
        x=720, y=340, w=240, h=220,
        fill=COLOR_COMM, stroke=COLOR_COMM_S,
        entry=[
            "CMD_DL recibido del OBC",
            "Hay archivos pendientes en disco",
            "ZS = 1 (en zona ventana)",
            "Banda S inicializandose",
        ],
        exit=[
            "BS_READY = 1",
            "Paquetes CCSDS armados",
            "Lock con estacion confirmado",
            "-> ir a DL",
        ],
    ),
    dict(
        id="P_DL", title="DL: Downlink activo (banda S)",
        x=400, y=340, w=240, h=220,
        fill=COLOR_COMM, stroke=COLOR_COMM_S,
        entry=[
            "BS_READY = 1, BS_TX = 1",
            "Transmitiendo a estacion",
            "Consumo alto (~12W)",
            "Monitorear errores TX",
        ],
        exit=[
            "Todos los archivos enviados",
            "OR ZS = 0 (fin de ventana)",
            "OR ECB = 0 -> ir a LP",
            "-> volver a IDLE",
        ],
    ),
    dict(
        id="P_LP", title="LP: Bajo consumo",
        x=80, y=620, w=240, h=200,
        fill=COLOR_SAFE, stroke=COLOR_SAFE_S,
        entry=[
            "ECB = 0 desde cualquier estado",
            "Apagar LEDs, FPGA, banda S",
            "CM5 en suspend (~0.5W)",
            "Mantener daemon vivo",
        ],
        exit=[
            "ECB = 1 sostenido (>5 min)",
            "OR CMD_PL_OFF -> ir a OFF",
            "Retomar IDLE si todo OK",
        ],
    ),
    dict(
        id="P_ERR", title="ERR: Estado de error",
        x=400, y=620, w=240, h=200,
        fill=COLOR_SAFE, stroke=COLOR_SAFE_S,
        entry=[
            "ERR_CAM | ERR_LED | ERR_PROC = 1",
            "Detener operacion actual",
            "Registrar error en log",
            "Notificar al OBC (telemetria)",
        ],
        exit=[
            "Recovery automatico -> ir a CAL",
            "(intentar 3 veces)",
            "OR CMD_PL_OFF -> ir a OFF",
            "OR error fatal -> permanecer",
        ],
    ),
]


# Comando OBC (inicio externo, equivalente a "Eyeccion" del OBC)
TRIGGER_OBC = dict(
    id="OBC_TRIG", x=80, y=340, w=240, h=80,
)


EDGES = [
    ("OBC_TRIG", "P_OFF",
     "Trigger:\nReset / power-on inicial",
     "Transition:\nPayload en estado OFF",
     "exitX=0.5;exitY=0;entryX=0.5;entryY=1;"),

    ("P_OFF", "P_BOOT",
     "Trigger:\nCMD_PL_ON del OBC\n(OBC en Estado F)",
     "Transition:\nAlimentar CM5, T = 0s,\nBOOT_OK = 0",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("P_BOOT", "P_CAL",
     "Trigger:\nBOOT_OK = 1\nDrivers cargados",
     "Transition:\nIniciar CAM_SELFTEST,\nLED_SELFTEST, FOCUS_CAL",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("P_CAL", "P_IDLE",
     "Trigger:\nCAM_OK = 1 AND LED_OK = 1\nAND FOCUS_OK = 1",
     "Transition:\nDISK_OK = 1,\nLEDs en modo bajo, esperar",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("P_IDLE", "P_WARM",
     "Trigger:\nCMD_CAP recibido",
     "Transition:\nEncender LEDs progresivo,\nT_WARM = 0s",
     "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"),

    ("P_WARM", "P_CAPT",
     "Trigger:\nT_WARM >= T_w AND\nTEMP_CMOS y TEMP_LED OK",
     "Transition:\nCamara modo RAW,\nN_CAP = 0",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("P_CAPT", "P_PROC",
     "Trigger:\nN_CAP = N_TARGET\n(secuencia completa)",
     "Transition:\nApagar LEDs,\niniciar reconstruccion FPM",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("P_PROC", "P_STORE",
     "Trigger:\nPROC_DONE = 1\n(FPM + SR completo)",
     "Transition:\nComprimir resultado,\ncalcular CRC32",
     "exitX=0.5;exitY=0;entryX=0.5;entryY=1;"),

    ("P_STORE", "P_IDLE",
     "Trigger:\nArchivo escrito,\nlog entry OK",
     "Transition:\nLiberar buffers,\nactualizar DISK_OK",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"),

    ("P_IDLE", "P_DLPREP",
     "Trigger:\nCMD_DL del OBC AND\nZS = 1 (zona ventana)",
     "Transition:\nInicializar banda S,\narmar paquetes CCSDS",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"),

    ("P_DLPREP", "P_DL",
     "Trigger:\nBS_READY = 1\nLock con estacion",
     "Transition:\nBS_TX = 1, comenzar TX,\nconsumo alto (~12W)",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"),

    ("P_DL", "P_IDLE",
     "Trigger:\nArchivos enviados\nOR ZS = 0",
     "Transition:\nBS_TX = 0, apagar banda S,\nlog de transmision",
     "exitX=0.5;exitY=0;entryX=0.5;entryY=1;exitDx=0;exitDy=0;"
     "entryDx=0;entryDy=0;"),

    # Transiciones de seguridad (a LP cuando ECB = 0)
    ("P_IDLE", "P_LP",
     "Trigger:\nECB = 0",
     "Transition:\nApagar perifericos,\nCM5 en suspend",
     "exitX=0.25;exitY=1;entryX=0.75;entryY=0;dashed=1;"),

    ("P_CAPT", "P_LP",
     "Trigger:\nECB = 0",
     "Transition:\nAbortar captura,\ndescartar buffer",
     "exitX=0;exitY=1;entryX=1;entryY=0.25;dashed=1;"),

    ("P_DL", "P_LP",
     "Trigger:\nECB = 0",
     "Transition:\nAbortar TX banda S",
     "exitX=0;exitY=1;entryX=1;entryY=0.5;dashed=1;"),

    ("P_LP", "P_IDLE",
     "Trigger:\nECB = 1 sostenido (>5min)",
     "Transition:\nReanudar CM5, volver a idle",
     "exitX=1;exitY=0;entryX=0.25;entryY=1;dashed=1;"),

    ("P_LP", "P_OFF",
     "Trigger:\nCMD_PL_OFF del OBC",
     "Transition:\nApagar CM5 totalmente",
     "exitX=0.75;exitY=0;entryX=0;entryY=1;dashed=1;"),

    # Errores (a ERR desde estados criticos)
    ("P_CAL", "P_ERR",
     "Trigger:\nERR_CAM | ERR_LED = 1",
     "Transition:\nLog error,\nnotificar OBC",
     "exitX=0;exitY=1;entryX=1;entryY=0;dashed=1;"),

    ("P_PROC", "P_ERR",
     "Trigger:\nERR_PROC = 1\n(FPM o SR fallaron)",
     "Transition:\nDescartar resultado,\nlog error",
     "exitX=0;exitY=1;entryX=1;entryY=0.25;dashed=1;"),

    ("P_ERR", "P_CAL",
     "Trigger:\nRecovery: reintentar\n(max 3 veces)",
     "Transition:\nResetear drivers,\nrecalibrar",
     "exitX=1;exitY=0;entryX=0.25;entryY=1;dashed=1;"),
]


def cell_state(s) -> str:
    style = (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={s['fill']};strokeColor={s['stroke']};"
        "fontSize=11;align=left;verticalAlign=top;"
        "spacingLeft=8;spacingRight=8;spacingTop=8;"
        "arcSize=8;strokeWidth=2;"
    )
    val = escape(state_value(s["title"], s["entry"], s["exit"]), quote=True)
    return (
        f'<mxCell id="{s["id"]}" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{s["x"]}" y="{s["y"]}" '
        f'width="{s["w"]}" height="{s["h"]}" as="geometry"/>'
        f'</mxCell>'
    )


def cell_obc_trig() -> str:
    style = ("rounded=1;whiteSpace=wrap;html=1;"
             "fillColor=#34495E;strokeColor=#1B2631;"
             "fontColor=#FFFFFF;fontSize=11;fontStyle=1;"
             "strokeWidth=2;arcSize=10;align=center;verticalAlign=middle;")
    val = escape("OBC pasa a Estado F\n(activar payload)\n\nEHPC = 1, ECB = 1, ZV = 1", quote=True)
    return (
        f'<mxCell id="{TRIGGER_OBC["id"]}" value="{val}" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{TRIGGER_OBC["x"]}" y="{TRIGGER_OBC["y"]}" '
        f'width="{TRIGGER_OBC["w"]}" height="{TRIGGER_OBC["h"]}" as="geometry"/>'
        f'</mxCell>'
    )


def cell_edge(idx: int, src: str, tgt: str, trigger: str,
              transition: str, extra: str) -> list[str]:
    eid = f"PE{idx}"
    style = (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
        "jettySize=auto;html=1;exitDx=0;exitDy=0;entryDx=0;entryDy=0;"
        "strokeColor=#444;strokeWidth=1.5;endArrow=classic;endFill=1;"
        f"{extra}"
    )
    edge = (
        f'<mxCell id="{eid}" style="{style}" edge="1" '
        f'source="{src}" target="{tgt}" parent="1">'
        f'<mxGeometry relative="1" as="geometry"/>'
        f'</mxCell>'
    )
    trig_val = escape(trigger).replace(chr(10), "&#10;")
    tran_val = escape(transition).replace(chr(10), "&#10;")
    lab_trig = (
        f'<mxCell id="{eid}_T" value="{trig_val}" '
        f'style="edgeLabel;html=1;align=center;verticalAlign=middle;'
        f'resizable=0;points=[];labelBackgroundColor=#FFFFFF;'
        f'fontSize=9;fontColor=#1A5276;" '
        f'vertex="1" connectable="0" parent="{eid}">'
        f'<mxGeometry x="-0.4" relative="1" as="geometry">'
        f'<mxPoint as="offset"/>'
        f'</mxGeometry>'
        f'</mxCell>'
    )
    lab_tran = (
        f'<mxCell id="{eid}_X" value="{tran_val}" '
        f'style="edgeLabel;html=1;align=center;verticalAlign=middle;'
        f'resizable=0;points=[];labelBackgroundColor=#FFF8DC;'
        f'fontSize=9;fontColor=#7D6608;" '
        f'vertex="1" connectable="0" parent="{eid}">'
        f'<mxGeometry x="0.4" relative="1" as="geometry">'
        f'<mxPoint as="offset"/>'
        f'</mxGeometry>'
        f'</mxCell>'
    )
    return [edge, lab_trig, lab_tran]


def cell_legend() -> str:
    legend_text = (
        "<b><u>Leyenda de flags del payload</u></b><br>"
        "<b>CMD_PL_ON / OFF</b> = comandos OBC (encendido)<br>"
        "<b>CMD_CAP</b> = comando de captura FPM<br>"
        "<b>CMD_DL</b> = comando de downlink banda S<br>"
        "<b>BOOT_OK</b> = CM5 + daemon listos<br>"
        "<b>CAM_OK</b> = camara responde y test pattern OK<br>"
        "<b>LED_OK</b> = todos los LEDs del array OK<br>"
        "<b>FOCUS_OK</b> = autofocus calibrado<br>"
        "<b>TEMP_CMOS</b> = temperatura sensor (-10 a 40C)<br>"
        "<b>TEMP_LED</b> = temperatura array LED<br>"
        "<b>T_WARM</b> = timer warmup, <b>T_w</b> = umbral (~30s)<br>"
        "<b>N_CAP</b> = imagenes capturadas en secuencia<br>"
        "<b>N_TARGET</b> = imagenes objetivo FPM (49..225)<br>"
        "<b>IMG_BUF</b> = buffer de captura en RAM<br>"
        "<b>PROC_DONE</b> = reconstruccion FPM + SR terminada<br>"
        "<b>BS_READY</b> = banda S inicializada<br>"
        "<b>BS_TX</b> = transmision activa<br>"
        "<b>DISK_OK</b> = espacio en disco disponible<br>"
        "<b>ERR_CAM/LED/PROC</b> = flags de error<br>"
        "<b>ECB</b> = energia suficiente (heredado del OBC)<br>"
        "<b>ZS / ZV</b> = zona ventana / experimental (del OBC)"
    )
    val = escape(legend_text, quote=True)
    style = (
        "rounded=1;whiteSpace=wrap;html=1;"
        "fillColor=#FBFCFC;strokeColor=#566573;"
        "fontSize=10;align=left;verticalAlign=top;"
        "spacingLeft=8;spacingRight=8;spacingTop=8;arcSize=8;"
    )
    return (
        f'<mxCell id="LEGEND_PL" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="720" y="620" width="320" height="340" as="geometry"/>'
        f'</mxCell>'
    )


def cell_title() -> str:
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=18;fontStyle=1;fontColor=#7D3C98;")
    return (
        f'<mxCell id="TITLE_PL" '
        f'value="Maquina de estados del Payload (microscopia FPM) - INTISAT" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="80" y="10" width="1840" height="40" as="geometry"/>'
        f'</mxCell>'
    )


def cell_subtitle() -> str:
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=11;fontColor=#566573;fontStyle=2;")
    return (
        f'<mxCell id="SUBTITLE_PL" '
        f'value="Payload sobre Raspberry Pi CM5. Se activa cuando el OBC entra en Estado F. '
        f'Formato adaptado del documento &#34;HW State Machine - Neils Vilchez&#34;." '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="80" y="970" width="1840" height="20" as="geometry"/>'
        f'</mxCell>'
    )


def build_xml() -> str:
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(cell_title())
    cells.append(cell_obc_trig())
    for s in STATES:
        cells.append(cell_state(s))
    for i, (src, tgt, trig, tran, extra) in enumerate(EDGES, 1):
        cells.extend(cell_edge(i, src, tgt, trig, tran, extra))
    cells.append(cell_legend())
    cells.append(cell_subtitle())

    cells_xml = "".join(cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" type="device">\n'
        '  <diagram name="Payload State Machine" id="payload-fsm-intisat">\n'
        '    <mxGraphModel dx="2400" dy="1400" grid="1" gridSize="10" '
        'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        'pageScale="1" pageWidth="2000" pageHeight="1000" math="0" shadow="0">\n'
        '      <root>'
        f'{cells_xml}'
        '</root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>\n'
    )


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    xml = build_xml()
    OUT.write_text(xml, encoding="utf-8")
    print(f"OK -> {OUT}")
    print(f"   {OUT.stat().st_size} bytes")
    print(f"   {len(STATES)} estados, {len(EDGES)} transiciones")
