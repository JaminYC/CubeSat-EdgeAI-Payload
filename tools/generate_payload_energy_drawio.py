"""Drawio del payload de microscopia FPM con analisis energetico
embebido en cada estado.

Cada caja de estado muestra:
  - Titulo
  - Potencia instantanea (W)
  - Duracion tipica por orbita (s)
  - Energia consumida (Wh por orbita)
  - Componentes ON en ese estado

Salida: Documentos de Referencia/Diagramas/Maquina_Estados_Payload_Energetico_INTISAT.drawio
"""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "Diagramas" / "Maquina_Estados_Payload_Energetico_INTISAT.drawio"


C_INIT_BG, C_INIT_S   = "#FFF8DC", "#D4AC0D"
C_CAL_BG, C_CAL_S     = "#E8DAEF", "#7D3C98"
C_OPS_BG, C_OPS_S     = "#D5F5E3", "#27AE60"
C_COMM_BG, C_COMM_S   = "#D6EAF8", "#2E86C1"
C_SAFE_BG, C_SAFE_S   = "#FADBD8", "#C0392B"


def state_value(title, power_w, dur_s, comps_on, color_acento="#1A365D"):
    """HTML para una caja de estado con info energetica."""
    energy_wh = power_w * dur_s / 3600
    comps_html = "<br>".join(f"&#8226; {escape(c)}" for c in comps_on)
    return (
        f"<b><u>{escape(title)}</u></b>"
        f"<br><br>"
        f"<font color='{color_acento}'><b>Potencia:</b></font> "
        f"<b>{power_w:.2f} W</b><br>"
        f"<font color='{color_acento}'><b>Duracion/orbita:</b></font> "
        f"{dur_s} s ({dur_s/60:.1f} min)<br>"
        f"<font color='{color_acento}'><b>Energia:</b></font> "
        f"<b>{energy_wh:.4f} Wh/orbita</b>"
        f"<br><br>"
        f"<u>Componentes ON:</u><br>"
        f"{comps_html}"
    )


STATES = [
    dict(
        id="P_OFF", title="OFF: Payload apagado",
        x=80, y=60, w=240, h=240,
        fill=C_INIT_BG, stroke=C_INIT_S,
        power=0.00, dur=1800,
        comps=["(ninguno - todo OFF)", "Solo housekeeping del OBC"],
    ),
    dict(
        id="P_BOOT", title="BOOT: Arranque CM5",
        x=400, y=60, w=240, h=240,
        fill=C_INIT_BG, stroke=C_INIT_S,
        power=4.50, dur=60,
        comps=["CM5 (boot)", "LDO 5V/3.3V", "eMMC (carga kernel)"],
    ),
    dict(
        id="P_CAL", title="CAL: Calibracion optica",
        x=720, y=60, w=240, h=260,
        fill=C_CAL_BG, stroke=C_CAL_S,
        power=5.20, dur=120,
        comps=["CM5 (Python)", "Camara IMX477", "LED array (test, baja P)",
               "Driver STM32G4", "Sensores temperatura"],
    ),
    dict(
        id="P_IDLE", title="IDLE: Espera comando",
        x=1040, y=60, w=240, h=240,
        fill=C_OPS_BG, stroke=C_OPS_S,
        power=3.00, dur=1500,
        comps=["CM5 (daemon idle)", "Sensores temperatura",
               "LDO siempre on"],
    ),
    dict(
        id="P_WARM", title="WARMUP: Estab. termica",
        x=1040, y=360, w=240, h=240,
        fill=C_OPS_BG, stroke=C_OPS_S,
        power=6.00, dur=30,
        comps=["CM5 (Python)", "LED array (warmup progresivo)",
               "Driver LEDs", "Sensores temperatura"],
    ),
    dict(
        id="P_CAPT", title="CAPT: Captura FPM",
        x=1360, y=360, w=240, h=260,
        fill=C_OPS_BG, stroke=C_OPS_S,
        power=8.50, dur=180,
        comps=["CM5 (capture mode)", "Camara IMX477 (RAW)",
               "LED array (1 LED ON x captura)",
               "Driver LEDs (multiplex)", "eMMC (buffer RAW)"],
    ),
    dict(
        id="P_PROC", title="PROC: FPM + Real-ESRGAN",
        x=1680, y=360, w=240, h=260,
        fill=C_OPS_BG, stroke=C_OPS_S,
        power=8.20, dur=240,
        comps=["CM5 (GPU + CPU full)",
               "RAM (LPDDR4X full uso)",
               "eMMC (lectura RAW)"],
    ),
    dict(
        id="P_STORE", title="STORE: Compresion + disco",
        x=1680, y=60, w=240, h=240,
        fill=C_OPS_BG, stroke=C_OPS_S,
        power=3.20, dur=30,
        comps=["CM5 (compress + CRC32)",
               "eMMC (escritura final)"],
    ),
    dict(
        id="P_DLPREP", title="DLPREP: Banda S init",
        x=720, y=400, w=240, h=240,
        fill=C_COMM_BG, stroke=C_COMM_S,
        power=5.00, dur=60,
        comps=["CM5 (CCSDS packetizer)",
               "Radio banda S (boot, lock)",
               "eMMC (lectura archivos)"],
    ),
    dict(
        id="P_DL", title="DL: Downlink banda S",
        x=400, y=400, w=240, h=260,
        fill=C_COMM_BG, stroke=C_COMM_S,
        power=12.80, dur=240,
        comps=["CM5 (TX driver)",
               "<b>Radio banda S (TX 10W RF)</b>",
               "eMMC (lectura streaming)",
               "<i>(estado mas costoso)</i>"],
    ),
    dict(
        id="P_LP", title="LP: Bajo consumo",
        x=80, y=400, w=240, h=240,
        fill=C_SAFE_BG, stroke=C_SAFE_S,
        power=0.55, dur=840,
        comps=["CM5 (suspend-to-RAM)",
               "Sensores T (housekeeping)"],
    ),
    dict(
        id="P_ERR", title="ERR: Error / retry",
        x=80, y=720, w=240, h=240,
        fill=C_SAFE_BG, stroke=C_SAFE_S,
        power=3.50, dur=300,
        comps=["CM5 (logger + diag)",
               "Sensores temperatura",
               "Componente con error en eval."],
    ),
]


EDGES = [
    ("P_OFF",   "P_BOOT",   "CMD_PL_ON\n(OBC -> F)",        "Alimentar CM5",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
    ("P_BOOT",  "P_CAL",    "BOOT_OK = 1",                   "Iniciar selftest",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
    ("P_CAL",   "P_IDLE",   "CAM_OK, LED_OK,\nFOCUS_OK",    "Esperar comando",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
    ("P_IDLE",  "P_WARM",   "CMD_CAP",                       "Warmup LEDs",
     "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"),
    ("P_WARM",  "P_CAPT",   "T_WARM >= T_w",                 "Camara RAW",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
    ("P_CAPT",  "P_PROC",   "N_CAP = N_TARGET",              "Iniciar FPM+SR",
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"),
    ("P_PROC",  "P_STORE",  "PROC_DONE = 1",                 "Comprimir+CRC",
     "exitX=0.5;exitY=0;entryX=0.5;entryY=1;"),
    ("P_STORE", "P_IDLE",   "Archivo OK",                    "Liberar buffers",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"),
    ("P_IDLE",  "P_DLPREP", "CMD_DL + ZS = 1",               "Banda S init",
     "exitX=0;exitY=1;entryX=1;entryY=0.25;"),
    ("P_DLPREP","P_DL",     "BS_READY = 1",                  "Iniciar TX",
     "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"),
    ("P_DL",    "P_IDLE",   "Archivos enviados\nOR ZS = 0", "Apagar TX",
     "exitX=0.5;exitY=0;entryX=0.25;entryY=1;"),
    ("P_IDLE",  "P_LP",     "ECB = 0",                       "Suspend CM5",
     "exitX=0;exitY=1;entryX=0.5;entryY=0;dashed=1;"),
    ("P_LP",    "P_IDLE",   "ECB = 1\nsostenido",            "Wake-up",
     "exitX=1;exitY=0;entryX=0.25;entryY=1;dashed=1;"),
    ("P_CAL",   "P_ERR",    "ERR_CAM/LED",                   "Log + notify OBC",
     "exitX=0;exitY=1;entryX=0.5;entryY=0;dashed=1;"),
    ("P_ERR",   "P_CAL",    "Retry (<=3)",                   "Recalibrar",
     "exitX=1;exitY=0.25;entryX=0;entryY=1;dashed=1;"),
]


def cell_state(s):
    style = (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={s['fill']};strokeColor={s['stroke']};"
        "fontSize=10;align=left;verticalAlign=top;"
        "spacingLeft=8;spacingRight=8;spacingTop=8;"
        "arcSize=8;strokeWidth=2;"
    )
    val = escape(state_value(s["title"], s["power"], s["dur"], s["comps"],
                             color_acento=s["stroke"]), quote=True)
    return (
        f'<mxCell id="{s["id"]}" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{s["x"]}" y="{s["y"]}" '
        f'width="{s["w"]}" height="{s["h"]}" as="geometry"/>'
        f'</mxCell>'
    )


def cell_edge(idx, src, tgt, trig, tran, extra):
    eid = f"PEE{idx}"
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
    trig_v = escape(trig).replace(chr(10), "&#10;")
    tran_v = escape(tran).replace(chr(10), "&#10;")
    lab1 = (
        f'<mxCell id="{eid}_T" value="{trig_v}" '
        f'style="edgeLabel;html=1;align=center;verticalAlign=middle;'
        f'resizable=0;labelBackgroundColor=#FFFFFF;fontSize=9;'
        f'fontColor=#1A5276;" vertex="1" connectable="0" parent="{eid}">'
        f'<mxGeometry x="-0.4" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry>'
        f'</mxCell>'
    )
    lab2 = (
        f'<mxCell id="{eid}_X" value="{tran_v}" '
        f'style="edgeLabel;html=1;align=center;verticalAlign=middle;'
        f'resizable=0;labelBackgroundColor=#FFF8DC;fontSize=9;'
        f'fontColor=#7D6608;" vertex="1" connectable="0" parent="{eid}">'
        f'<mxGeometry x="0.5" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry>'
        f'</mxCell>'
    )
    return [edge, lab1, lab2]


def cell_title():
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=18;fontStyle=1;fontColor=#1A5276;")
    return (
        f'<mxCell id="TITLE_PLE" '
        f'value="Estados del payload con analisis energetico - INTISAT FPM" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="80" y="10" width="1840" height="40" as="geometry"/>'
        f'</mxCell>'
    )


def cell_summary():
    """Tabla resumen de energia y resaltado del balance orbital."""
    total_dur = sum(s["dur"] for s in STATES)
    total_wh = sum(s["power"] * s["dur"] / 3600 for s in STATES)
    rows = "".join(
        f"<tr><td><b>{escape(s['title'].split(':')[0])}</b></td>"
        f"<td align='right'>{s['power']:.2f} W</td>"
        f"<td align='right'>{s['dur']} s</td>"
        f"<td align='right'><b>{s['power']*s['dur']/3600:.4f}</b></td></tr>"
        for s in STATES
    )
    html = (
        "<b><u>Resumen energetico por orbita</u></b><br><br>"
        "<table style='border-collapse:collapse;font-size:9px;width:100%;'>"
        "<tr style='background-color:#1A365D;color:white;'>"
        "<th align='left'>Estado</th><th align='right'>Potencia</th>"
        "<th align='right'>Duracion</th><th align='right'>Wh/orb</th></tr>"
        f"{rows}"
        f"<tr style='background-color:#FEF9E7;'>"
        f"<td><b>TOTAL</b></td>"
        f"<td align='right'>-</td>"
        f"<td align='right'><b>{total_dur} s</b></td>"
        f"<td align='right'><b>{total_wh:.4f}</b></td></tr>"
        "</table>"
        "<br>"
        "<b>Generacion solar estimada:</b> ~6.50 Wh/orbita<br>"
        "<b>Consumo bus (OBC+EPS+UHF):</b> ~2.20 Wh/orbita<br>"
        f"<b>Consumo payload:</b> {total_wh:.2f} Wh/orbita<br>"
        f"<b>Margen:</b> "
        f"<font color='{'#27AE60' if (6.5 - 2.2 - total_wh) > 0 else '#C0392B'}'>"
        f"<b>{6.5 - 2.2 - total_wh:+.2f} Wh/orbita</b></font>"
    )
    style = (
        "rounded=1;whiteSpace=wrap;html=1;"
        "fillColor=#FBFCFC;strokeColor=#566573;"
        "fontSize=10;align=left;verticalAlign=top;"
        "spacingLeft=10;spacingRight=10;spacingTop=10;arcSize=8;"
    )
    val = escape(html, quote=True)
    return (
        f'<mxCell id="SUMMARY" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="400" y="720" width="900" height="280" as="geometry"/>'
        f'</mxCell>'
    )


def build_xml():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(cell_title())
    for s in STATES:
        cells.append(cell_state(s))
    for i, (src, tgt, trig, tran, extra) in enumerate(EDGES, 1):
        cells.extend(cell_edge(i, src, tgt, trig, tran, extra))
    cells.append(cell_summary())

    cells_xml = "".join(cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" type="device">\n'
        '  <diagram name="Payload Energy FSM" id="payload-energy-fsm">\n'
        '    <mxGraphModel dx="2400" dy="1400" grid="1" gridSize="10" '
        'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        'pageScale="1" pageWidth="2000" pageHeight="1050" math="0" shadow="0">\n'
        f'      <root>{cells_xml}</root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>\n'
    )


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_xml(), encoding="utf-8")
    print(f"OK -> {OUT}")
    print(f"   {OUT.stat().st_size} bytes")
    print(f"   {len(STATES)} estados, {len(EDGES)} transiciones")
