"""Genera un drawio XML traduciendo el OBC state machine actual
al formato del PDF "HW State Machine Neils Vilchez".

Cada estado se representa como una caja con:
  - Titulo en negrita y subrayado
  - "Entry Condition:" subrayado + lista de condiciones de entrada
  - "Exit Condition:" subrayado + lista de condiciones de salida

Entre cajas, las transiciones llevan dos labels separados:
  - "Trigger: ..."  (que evento dispara la transicion)
  - "Transition: ..."  (que cambios de estado/flags ocurren)

Salida: Documentos de Referencia/Diagramas/Maquina_Estados_OBC_INTISAT.drawio
"""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "Diagramas" / "Maquina_Estados_OBC_INTISAT.drawio"


COLOR_INIT   = "#FFF8DC"   # amarillo claro: arranque / verificacion
COLOR_INIT_S = "#D4AC0D"
COLOR_DEPLOY = "#D6EAF8"   # azul claro: despliegue
COLOR_DEPLOY_S = "#2E86C1"
COLOR_NOM    = "#D5F5E3"   # verde claro: operacion nominal
COLOR_NOM_S  = "#27AE60"
COLOR_SAFE   = "#FADBD8"   # rojo claro: standby / supervivencia
COLOR_SAFE_S = "#C0392B"


def state_value(title: str, entry: list[str], exit_: list[str]) -> str:
    """Construye el HTML interno de una caja de estado estilo Neils."""
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
        id="ST_A", title="Estado A: Verificacion de arranque",
        x=240, y=60, w=240, h=220,
        fill=COLOR_INIT, stroke=COLOR_INIT_S,
        entry=[
            "Eyeccion del CubeSat detectada",
            "T = 0s, GL = 1, ECB = 1",
            "ERR_BOOT = 1 (al inicio)",
        ],
        exit=[
            "T >= 30 min",
            "BUS_OK = 1",
            "MAG_OK = 1",
            "ERR_BOOT = 0",
        ],
    ),
    dict(
        id="ST_B", title="Estado B: Estabilizacion de rotacion",
        x=560, y=60, w=240, h=220,
        fill=COLOR_DEPLOY, stroke=COLOR_DEPLOY_S,
        entry=[
            "BUS_OK = 1 AND MAG_OK = 1",
            "ERR_BOOT = 0",
            "MTQ_EN = 1 (magnetorquers activos)",
            "ECB = 1",
        ],
        exit=[
            "Rotacion residual aceptable",
            "ERR_DET = 0",
            "Listo para verificar antenas",
        ],
    ),
    dict(
        id="ST_VC", title="Estado VC: Verificacion despliegue antenas",
        x=880, y=60, w=240, h=240,
        fill=COLOR_INIT, stroke=COLOR_INIT_S,
        entry=[
            "MTQ_EN = 0 (estabilizacion OK)",
            "ECB = 1",
            "AD = 0 | 1 | 2 (lectura inicial)",
        ],
        exit=[
            "AD = 1 -> ir a VS",
            "AD = 0 AND N_DA < 3 -> ir a C",
            "AD != 1 AND N_DA = 3",
            "AND N_DR < 2 -> ir a C_R",
        ],
    ),
    dict(
        id="ST_C", title="Estado C: Despliegue de antenas",
        x=880, y=360, w=240, h=200,
        fill=COLOR_DEPLOY, stroke=COLOR_DEPLOY_S,
        entry=[
            "N_DA < 3",
            "AD = 0 (antenas no desplegadas)",
            "ECB = 1, CMD_DA = 1",
            "T_DEP = 0s",
        ],
        exit=[
            "T_DEP = Td (tiempo cumplido)",
            "N_DA = N_DA + 1",
            "Volver a VC para reverificar",
        ],
    ),
    dict(
        id="ST_CR", title="Estado C_R: Despliegue redundante",
        x=1200, y=360, w=240, h=200,
        fill=COLOR_DEPLOY, stroke=COLOR_DEPLOY_S,
        entry=[
            "AD != 1 AND N_DA = 3",
            "(despliegue principal fallo)",
            "N_DR < 2, ECB = 1",
            "ERR_ANT = 0",
        ],
        exit=[
            "T_DEP = Td",
            "N_DR = N_DR + 1",
            "Volver a VC para reverificar",
        ],
    ),
    dict(
        id="ST_VS", title="Estado VS: Verificacion de subsistemas",
        x=1200, y=60, w=240, h=220,
        fill=COLOR_INIT, stroke=COLOR_INIT_S,
        entry=[
            "AD = 1 (antenas OK)",
            "ECB = 1",
            "Verificar sensores, memorias,",
            "transceivers, buses OBC/EPS/UHF",
        ],
        exit=[
            "Todos los subsistemas operativos",
            "EHPC = 1 (energia para payload)",
            "Listo para modo nominal",
        ],
    ),
    dict(
        id="ST_D", title="Estado D: Nominal",
        x=1520, y=60, w=240, h=200,
        fill=COLOR_NOM, stroke=COLOR_NOM_S,
        entry=[
            "EHPC = 1, ECB = 1",
            "AD = 1, GL = 0",
            "Beacon UHF activo",
            "Telemetria almacenada en OBC",
        ],
        exit=[
            "ZS = 1 (entrada zona solar)",
            "-> ir a Estado E (ventana)",
            "OR ECB = 0 -> ir a STB",
        ],
    ),
    dict(
        id="ST_E", title="Estado E: Ventana",
        x=1520, y=300, w=240, h=220,
        fill=COLOR_NOM, stroke=COLOR_NOM_S,
        entry=[
            "ZS = 1 (en zona ventana)",
            "EHPC = 1",
            "Preparado para downlink UHF",
            "y/o transicion a zona solar",
        ],
        exit=[
            "ZV = 1 -> ir a Estado F",
            "OR ZS = 0 -> volver a D",
            "OR ECB = 0 -> ir a STB",
        ],
    ),
    dict(
        id="ST_F", title="Estado F: Adquisicion solar y payload",
        x=1200, y=620, w=240, h=220,
        fill=COLOR_NOM, stroke=COLOR_NOM_S,
        entry=[
            "ZV = 1 (zona experimental OK)",
            "ZE = 0, EHPC = 1",
            "Payload activo (microscopia)",
            "Banda S preparada para downlink",
        ],
        exit=[
            "ZE = 1 (experimento terminado)",
            "-> volver a Estado D",
            "OR ECB = 0 -> ir a STB",
        ],
    ),
    dict(
        id="ST_STB", title="Estado STB: Standby",
        x=560, y=620, w=240, h=200,
        fill=COLOR_SAFE, stroke=COLOR_SAFE_S,
        entry=[
            "ECB = 0 (desde cualquier estado)",
            "Energia insuficiente",
            "Apagar payload y MTQ",
            "Solo OBC + EPS minimo",
        ],
        exit=[
            "ECB = 1 (recuperacion solar)",
            "-> volver al ultimo estado valido",
            "OR ECB = 0 persistente",
            "-> ir a Estado SV",
        ],
    ),
    dict(
        id="ST_SV", title="Estado SV: Supervivencia",
        x=240, y=620, w=240, h=200,
        fill=COLOR_SAFE, stroke=COLOR_SAFE_S,
        entry=[
            "ECB = 0 sostenido tras STB",
            "Modo de ultimo recurso",
            "Solo watchdog + carga solar",
            "Beacon minimo si hay energia",
        ],
        exit=[
            "(Ultimo estado del OBC)",
            "ECB = 1 recuperacion -> STB",
            "Sin energia: permanece aqui",
        ],
    ),
]


# Eyeccion (circulo de inicio)
EYECCION = dict(
    id="EYECT", x=80, y=140, w=120, h=80,
)


# Transiciones: (source, target, trigger, transition, [edge_style_extra])
EDGES = [
    ("EYECT", "ST_A",
     "Trigger:\nEyeccion del CubeSat",
     "Transition:\nArranque OBC, T = 0s,\nGL = 1, BUS_OK = 0",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("ST_A", "ST_B",
     "Trigger:\nT >= 30 min AND\nBUS_OK = 1 AND MAG_OK = 1",
     "Transition:\nActivacion de MTQ_EN,\nERR_BOOT = 0",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("ST_B", "ST_VC",
     "Trigger:\nRotacion estabilizada\n(ERR_DET = 0)",
     "Transition:\nDesactivacion de MTQ_EN,\nIniciar verificacion antenas",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("ST_VC", "ST_C",
     "Trigger:\nAD = 0 AND N_DA < 3",
     "Transition:\nCMD_DA = 1,\nT_DEP = 0s",
     "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"),

    ("ST_C", "ST_VC",
     "Trigger:\nT_DEP = Td\n(timeout despliegue)",
     "Transition:\nN_DA = N_DA + 1,\nReverificar AD",
     "exitX=0.25;exitY=0;entryX=0.75;entryY=1;"),

    ("ST_VC", "ST_CR",
     "Trigger:\nAD != 1 AND N_DA = 3\nAND N_DR < 2",
     "Transition:\nActivar mecanismo redundante,\nT_DEP = 0s",
     "exitX=1;exitY=1;entryX=0.5;entryY=0;"),

    ("ST_CR", "ST_VC",
     "Trigger:\nT_DEP = Td\n(timeout despliegue red.)",
     "Transition:\nN_DR = N_DR + 1,\nReverificar AD",
     "exitX=0;exitY=0;entryX=1;entryY=1;"),

    ("ST_VC", "ST_VS",
     "Trigger:\nAD = 1 (antenas OK)",
     "Transition:\nIniciar verificacion\nde subsistemas",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("ST_VS", "ST_D",
     "Trigger:\nSubsistemas OK,\nEHPC = 1",
     "Transition:\nActivar beacon UHF,\nentrar en modo nominal",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),

    ("ST_D", "ST_E",
     "Trigger:\nZS = 1\n(entrada zona ventana)",
     "Transition:\nPreparar downlink UHF",
     "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"),

    ("ST_E", "ST_D",
     "Trigger:\nZS = 0\n(salida zona ventana)",
     "Transition:\nVolver a beacon + telemetria",
     "exitX=0.25;exitY=0;entryX=0.75;entryY=1;"),

    ("ST_E", "ST_F",
     "Trigger:\nZV = 1\n(zona experimental)",
     "Transition:\nActivar payload (microscopia),\npreparar banda S",
     "exitX=0;exitY=1;entryX=1;entryY=0;"),

    ("ST_F", "ST_D",
     "Trigger:\nZE = 1\n(experimento finalizado)",
     "Transition:\nDesactivar payload,\nalmacenar telemetria",
     "exitX=0;exitY=0.5;entryX=0.5;entryY=1;"),

    # Transiciones de seguridad (a STB desde cualquier estado operativo)
    ("ST_D", "ST_STB",
     "Trigger:\nECB = 0",
     "Transition:\nApagar payload,\nmodo bajo consumo",
     "exitX=0;exitY=1;entryX=0.5;entryY=0;dashed=1;"),

    ("ST_E", "ST_STB",
     "Trigger:\nECB = 0",
     "Transition:\nApagar UHF downlink",
     "exitX=0;exitY=0.5;entryX=1;entryY=0;dashed=1;"),

    ("ST_F", "ST_STB",
     "Trigger:\nECB = 0",
     "Transition:\nApagar payload y banda S",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;dashed=1;"),

    ("ST_STB", "ST_SV",
     "Trigger:\nECB = 0 sostenido",
     "Transition:\nSolo watchdog + carga solar",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"),

    ("ST_SV", "ST_STB",
     "Trigger:\nECB = 1\n(recuperacion energia)",
     "Transition:\nReactivar OBC nominal",
     "exitX=1;exitY=0.25;entryX=0;entryY=0.75;"),

    ("ST_STB", "ST_D",
     "Trigger:\nECB = 1 sostenido,\nsubsistemas OK",
     "Transition:\nRetomar modo nominal",
     "exitX=1;exitY=0;entryX=0.25;entryY=1;dashed=1;"),
]


def cell_state(s) -> str:
    """mxCell para una caja de estado."""
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


def cell_eyeccion() -> str:
    style = ("ellipse;whiteSpace=wrap;html=1;"
             "fillColor=#34495E;strokeColor=#1B2631;"
             "fontColor=#FFFFFF;fontSize=12;fontStyle=1;"
             "strokeWidth=2;")
    return (
        f'<mxCell id="{EYECCION["id"]}" '
        f'value="Eyeccion&#10;del CubeSat" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{EYECCION["x"]}" y="{EYECCION["y"]}" '
        f'width="{EYECCION["w"]}" height="{EYECCION["h"]}" as="geometry"/>'
        f'</mxCell>'
    )


def cell_edge(idx: int, src: str, tgt: str, trigger: str,
              transition: str, extra: str) -> list[str]:
    """Devuelve mxCell del edge + 2 mxCell de labels (trigger + transition)."""
    eid = f"E{idx}"
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
    # label del trigger (mas cerca del origen)
    lab_trig = (
        f'<mxCell id="{eid}_T" value="{escape(trigger).replace(chr(10), "&#10;")}" '
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
        f'<mxCell id="{eid}_X" value="{escape(transition).replace(chr(10), "&#10;")}" '
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
    """Leyenda de flags usados en la maquina."""
    legend_text = (
        "<b><u>Leyenda de flags</u></b><br>"
        "<b>T</b> = tiempo en estado<br>"
        "<b>T_DEP</b> = timer de despliegue antenas<br>"
        "<b>Td</b> = umbral de tiempo de despliegue<br>"
        "<b>GL</b> = ground-link autorizado (1=si)<br>"
        "<b>BUS_OK</b> = buses OBC/EPS/UHF operativos<br>"
        "<b>MAG_OK</b> = magnetometro operativo<br>"
        "<b>MTQ_EN</b> = magnetorquers habilitados<br>"
        "<b>AD</b> = antennas deployed (0/1/2)<br>"
        "<b>N_DA</b> = intentos despliegue principal (0..3)<br>"
        "<b>N_DR</b> = intentos despliegue redundante (0..2)<br>"
        "<b>CMD_DA</b> = comando de despliegue antenas<br>"
        "<b>ERR_BOOT</b> = error de arranque<br>"
        "<b>ERR_DET</b> = error de deteccion en B<br>"
        "<b>ERR_ANT</b> = error de despliegue antenas<br>"
        "<b>ECB</b> = energia cumple bateria (suf.)<br>"
        "<b>EHPC</b> = energia habilita payload cientifico<br>"
        "<b>ZS</b> = zona ventana (sobre estacion)<br>"
        "<b>ZV</b> = zona experimental (sobre objetivo)<br>"
        "<b>ZE</b> = zona experimental finalizada"
    )
    val = escape(legend_text, quote=True)
    style = (
        "rounded=1;whiteSpace=wrap;html=1;"
        "fillColor=#FBFCFC;strokeColor=#566573;"
        "fontSize=10;align=left;verticalAlign=top;"
        "spacingLeft=8;spacingRight=8;spacingTop=8;arcSize=8;"
    )
    return (
        f'<mxCell id="LEGEND" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="80" y="280" width="280" height="320" as="geometry"/>'
        f'</mxCell>'
    )


def cell_title() -> str:
    """Titulo del diagrama."""
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=18;fontStyle=1;fontColor=#1A5276;")
    return (
        f'<mxCell id="TITLE" '
        f'value="Maquina de estados del OBC - CubeSat INTISAT" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="240" y="10" width="1520" height="40" as="geometry"/>'
        f'</mxCell>'
    )


def cell_subtitle() -> str:
    """Subtitulo con la fuente."""
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=11;fontColor=#566573;fontStyle=2;")
    return (
        f'<mxCell id="SUBTITLE" '
        f'value="Formato adaptado del documento &#34;HW State Machine - Neils Vilchez&#34;" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="240" y="848" width="1520" height="20" as="geometry"/>'
        f'</mxCell>'
    )


def build_xml() -> str:
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(cell_title())
    cells.append(cell_eyeccion())
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
        '  <diagram name="OBC State Machine" id="obc-fsm-intisat">\n'
        '    <mxGraphModel dx="2400" dy="1400" grid="1" gridSize="10" '
        'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        'pageScale="1" pageWidth="2000" pageHeight="900" math="0" shadow="0">\n'
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
