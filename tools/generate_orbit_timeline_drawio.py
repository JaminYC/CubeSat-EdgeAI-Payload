"""Drawio del timeline orbital del payload (90 min LEO).

Cada estado del payload aparece como un bloque temporal sobre un eje
horizontal de 0 a 90 min. La altura del bloque representa el consumo
en W. Se muestran tambien las "swimlanes" para fases orbitales
(eclipse, iluminado, zona estacion, zona experimental).

Salida: Documentos de Referencia/Diagramas/Timeline_Orbital_Payload_INTISAT.drawio
"""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parent.parent / "Documentos de Referencia" / "Diagramas" / "Timeline_Orbital_Payload_INTISAT.drawio"


# Secuencia de estados en una orbita tipica de 90 min (5400 s).
# Cada item: (nombre, duracion_seg, potencia_W, color_fill, color_stroke)
SEQUENCE = [
    ("OFF",     1800, 0.00,  "#95A5A6", "#566573"),  # eclipse
    ("BOOT",      60, 4.50,  "#F39C12", "#B7791F"),
    ("CAL",      120, 5.20,  "#9B59B6", "#7D3C98"),
    ("IDLE",     300, 3.00,  "#27AE60", "#1E8449"),
    ("WARMUP",    30, 6.00,  "#16A085", "#117A65"),
    ("CAPT",     180, 8.50,  "#229954", "#1D8348"),
    ("PROC",     240, 8.20,  "#1E8449", "#196F3D"),
    ("STORE",     30, 3.20,  "#52BE80", "#27AE60"),
    ("IDLE",     300, 3.00,  "#27AE60", "#1E8449"),
    ("DLPREP",    60, 5.00,  "#5DADE2", "#2874A6"),
    ("DL",       240, 12.80, "#2874A6", "#1B4F72"),
    ("IDLE",     300, 3.00,  "#27AE60", "#1E8449"),
    ("LP",       840, 0.55,  "#E74C3C", "#A93226"),
    ("IDLE",     900, 3.00,  "#27AE60", "#1E8449"),
]


# Layout: canvas 2200 wide, eje horizontal de 0 a 5400 s mapeado a x in [100, 2100]
X0 = 100
X1 = 2100
Y_BASE = 600    # baseline del grafico de potencia (al fondo)
H_PER_W = 25    # 25 px por watt
Y_TOP = Y_BASE - 14 * H_PER_W   # tope para 14 W max


def t_to_x(t_seconds):
    return X0 + (X1 - X0) * t_seconds / 5400


def w_to_h(power_w):
    return power_w * H_PER_W


def cell_block(idx, t_start, dur, name, power_w, fill, stroke):
    """Bloque que muestra un estado en el timeline."""
    x = t_to_x(t_start)
    width = max(t_to_x(t_start + dur) - x, 8)
    h = max(w_to_h(power_w), 4)
    y = Y_BASE - h
    style = (
        "rounded=0;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
        "fontSize=8;fontStyle=1;fontColor=#1A202C;align=center;"
        "verticalAlign=middle;"
    )
    energy_wh = power_w * dur / 3600
    if dur >= 120:
        label = f"{name}\\n{power_w:.1f}W\\n{energy_wh:.3f}Wh"
    elif dur >= 30:
        label = f"{name}\\n{power_w:.1f}W"
    else:
        label = name
    val = escape(label.replace("\\n", "\n")).replace("\n", "&#10;")
    return (
        f'<mxCell id="BLK{idx}" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x:.1f}" y="{y:.1f}" '
        f'width="{width:.1f}" height="{h:.1f}" as="geometry"/>'
        f'</mxCell>'
    )


def cell_axis():
    """Eje X horizontal con marcas cada 10 min."""
    cells = []
    # linea base
    cells.append(
        f'<mxCell id="AXIS_BASE" style="endArrow=none;html=1;strokeColor=#1A202C;'
        f'strokeWidth=1.5;" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{X0-20}" y="{Y_BASE}" as="sourcePoint"/>'
        f'<mxPoint x="{X1+30}" y="{Y_BASE}" as="targetPoint"/>'
        f'</mxGeometry></mxCell>'
    )
    # marcas cada 10 min (600 s)
    for i in range(10):  # 0, 10, 20, ..., 90 min
        t = i * 600
        x = t_to_x(t)
        cells.append(
            f'<mxCell id="TICK{i}" style="endArrow=none;html=1;'
            f'strokeColor=#566573;strokeWidth=1;" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x}" y="{Y_BASE}" as="sourcePoint"/>'
            f'<mxPoint x="{x}" y="{Y_BASE+8}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>'
        )
        cells.append(
            f'<mxCell id="TLBL{i}" '
            f'value="{i*10} min" '
            f'style="text;html=1;align=center;verticalAlign=middle;'
            f'fontSize=10;fontColor=#566573;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x-30}" y="{Y_BASE+10}" width="60" height="18" as="geometry"/>'
            f'</mxCell>'
        )
    # marca final 90 min
    x90 = t_to_x(5400)
    cells.append(
        f'<mxCell id="TICK90" style="endArrow=none;html=1;'
        f'strokeColor=#566573;strokeWidth=1;" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{x90}" y="{Y_BASE}" as="sourcePoint"/>'
        f'<mxPoint x="{x90}" y="{Y_BASE+8}" as="targetPoint"/>'
        f'</mxGeometry></mxCell>'
    )
    cells.append(
        f'<mxCell id="TLBL90" '
        f'value="90 min" '
        f'style="text;html=1;align=center;verticalAlign=middle;'
        f'fontSize=10;fontColor=#566573;" vertex="1" parent="1">'
        f'<mxGeometry x="{x90-30}" y="{Y_BASE+10}" width="60" height="18" as="geometry"/>'
        f'</mxCell>'
    )

    # Eje Y (potencia)
    cells.append(
        f'<mxCell id="AXIS_Y" style="endArrow=none;html=1;strokeColor=#1A202C;'
        f'strokeWidth=1.5;" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{X0-20}" y="{Y_BASE+5}" as="sourcePoint"/>'
        f'<mxPoint x="{X0-20}" y="{Y_TOP-20}" as="targetPoint"/>'
        f'</mxGeometry></mxCell>'
    )
    for w in [0, 2, 4, 6, 8, 10, 12, 14]:
        y = Y_BASE - w_to_h(w)
        cells.append(
            f'<mxCell id="YTICK{w}" style="endArrow=none;html=1;'
            f'strokeColor=#566573;strokeWidth=0.8;dashed=1;dashPattern=2 4;" '
            f'edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{X0-20}" y="{y}" as="sourcePoint"/>'
            f'<mxPoint x="{X1+30}" y="{y}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>'
        )
        cells.append(
            f'<mxCell id="YLBL{w}" '
            f'value="{w} W" '
            f'style="text;html=1;align=right;verticalAlign=middle;'
            f'fontSize=10;fontColor=#566573;fontStyle=1;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{X0-65}" y="{y-9}" width="40" height="18" as="geometry"/>'
            f'</mxCell>'
        )

    # Etiqueta eje Y
    cells.append(
        f'<mxCell id="YTITLE" '
        f'value="Potencia (W)" '
        f'style="text;html=1;align=center;verticalAlign=middle;'
        f'fontSize=11;fontStyle=1;fontColor=#1A365D;rotation=-90;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{X0-110}" y="{(Y_TOP+Y_BASE)/2 - 50}" width="100" height="20" as="geometry"/>'
        f'</mxCell>'
    )
    # Etiqueta eje X
    cells.append(
        f'<mxCell id="XTITLE" '
        f'value="Tiempo en la orbita LEO (minutos)" '
        f'style="text;html=1;align=center;verticalAlign=middle;'
        f'fontSize=12;fontStyle=1;fontColor=#1A365D;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{(X0+X1)/2 - 200}" y="{Y_BASE+40}" width="400" height="20" as="geometry"/>'
        f'</mxCell>'
    )
    return cells


def cell_phase_band(idx, t_start, t_end, color, label):
    """Banda horizontal sobre el grafico para una fase orbital."""
    x0 = t_to_x(t_start)
    w = t_to_x(t_end) - x0
    style = (
        f"rounded=0;whiteSpace=wrap;html=1;"
        f"fillColor={color};strokeColor=none;fillOpacity=20;"
        f"fontSize=11;fontStyle=1;align=center;verticalAlign=middle;"
    )
    return (
        f'<mxCell id="PHASE{idx}" value="{escape(label)}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x0:.1f}" y="{Y_TOP-10}" '
        f'width="{w:.1f}" height="30" as="geometry"/>'
        f'</mxCell>'
    )


def cell_title():
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=20;fontStyle=1;fontColor=#1A5276;")
    return (
        f'<mxCell id="TITLE_TIM" '
        f'value="Timeline orbital del payload (LEO 90 min) - INTISAT FPM" '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="100" y="20" width="2000" height="40" as="geometry"/>'
        f'</mxCell>'
    )


def cell_subtitle():
    style = ("text;html=1;align=center;verticalAlign=middle;"
             "fontSize=11;fontStyle=2;fontColor=#566573;")
    return (
        f'<mxCell id="SUBTITLE_TIM" '
        f'value="Cada bloque = un estado del payload. Altura = potencia (W), '
        f'ancho = duracion (s). El area del bloque = energia consumida (Wh)." '
        f'style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="100" y="60" width="2000" height="22" as="geometry"/>'
        f'</mxCell>'
    )


def cell_total_legend():
    total_dur = sum(s[1] for s in SEQUENCE)
    total_wh = sum(s[1] * s[2] / 3600 for s in SEQUENCE)
    avg_w = total_wh / (total_dur / 3600) if total_dur > 0 else 0
    info = (
        f"<b>Resumen de la orbita</b><br>"
        f"Duracion: <b>{total_dur} s</b> ({total_dur/60:.1f} min)<br>"
        f"Energia total payload: <b>{total_wh:.3f} Wh</b><br>"
        f"Potencia promedio: <b>{avg_w:.2f} W</b><br>"
        f"Pico: <b>{max(s[2] for s in SEQUENCE):.1f} W</b> (estado DL)<br>"
        f"<br>"
        f"<b>Recomendaciones:</b><br>"
        f"&#8226; Mantener OFF durante eclipse<br>"
        f"&#8226; DL solo en zona ventana (5-10 min)<br>"
        f"&#8226; PROC fuera de zona ventana (no compite con UHF)<br>"
        f"&#8226; LP si SOC bateria &lt; 40%"
    )
    style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#FBFCFC;"
        "strokeColor=#566573;fontSize=10;align=left;verticalAlign=top;"
        "spacingLeft=10;spacingTop=10;arcSize=8;"
    )
    val = escape(info, quote=True)
    return (
        f'<mxCell id="TOTALS" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="100" y="700" width="380" height="200" as="geometry"/>'
        f'</mxCell>'
    )


def cell_color_legend():
    """Mini-leyenda de colores por categoria."""
    rows = (
        "<b>Categorias de estados:</b><br>"
        "<font color='#D4AC0D'>&#9608;</font> Arranque (OFF/BOOT)<br>"
        "<font color='#7D3C98'>&#9608;</font> Calibracion (CAL)<br>"
        "<font color='#1E8449'>&#9608;</font> Operacion (IDLE/CAPT/PROC/STORE)<br>"
        "<font color='#2874A6'>&#9608;</font> Comunicacion (DLPREP/DL)<br>"
        "<font color='#A93226'>&#9608;</font> Safe (LP/ERR)<br>"
    )
    style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#FBFCFC;"
        "strokeColor=#566573;fontSize=10;align=left;verticalAlign=top;"
        "spacingLeft=10;spacingTop=10;arcSize=8;"
    )
    val = escape(rows, quote=True)
    return (
        f'<mxCell id="COLOR_LEG" value="{val}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="520" y="700" width="320" height="200" as="geometry"/>'
        f'</mxCell>'
    )


def build_xml():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(cell_title())
    cells.append(cell_subtitle())

    # Bandas de fase orbital (eclipse vs iluminado)
    cells.append(cell_phase_band(1, 0, 1800, "#566573",
                                 "ECLIPSE (sin sol, payload OFF)"))
    cells.append(cell_phase_band(2, 1800, 4500, "#27AE60",
                                 "ILUMINADO - zona solar (operacion nominal)"))
    cells.append(cell_phase_band(3, 4500, 5400, "#7D6608",
                                 "ZONA SOMBRA gradual"))

    # Eje
    cells.extend(cell_axis())

    # Bloques de estados
    t = 0
    for i, (name, dur, p, fill, stroke) in enumerate(SEQUENCE, 1):
        cells.append(cell_block(i, t, dur, name, p, fill, stroke))
        t += dur

    # Banda inferior: cuando esta sobre estacion (zona ventana ZS)
    # Asumo zona ventana entre min 50 y min 56 (6 min de paso sobre estacion)
    cells.append(
        f'<mxCell id="ZV_BAND" '
        f'value="Ventana sobre estacion terrena (ZS = 1, 6 min)" '
        f'style="rounded=1;whiteSpace=wrap;html=1;'
        f'fillColor=#5DADE2;strokeColor=#2874A6;fillOpacity=35;'
        f'fontSize=10;fontStyle=1;align=center;verticalAlign=middle;'
        f'fontColor=#1B4F72;" vertex="1" parent="1">'
        f'<mxGeometry x="{t_to_x(3000):.1f}" y="{Y_BASE+70}" '
        f'width="{t_to_x(3360)-t_to_x(3000):.1f}" height="30" as="geometry"/>'
        f'</mxCell>'
    )

    cells.append(cell_total_legend())
    cells.append(cell_color_legend())

    cells_xml = "".join(cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" type="device">\n'
        '  <diagram name="Orbit Timeline" id="orbit-timeline-intisat">\n'
        '    <mxGraphModel dx="2400" dy="1400" grid="1" gridSize="10" '
        'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        'pageScale="1" pageWidth="2300" pageHeight="950" math="0" shadow="0">\n'
        f'      <root>{cells_xml}</root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>\n'
    )


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_xml(), encoding="utf-8")
    print(f"OK -> {OUT}")
    print(f"   {OUT.stat().st_size} bytes, {len(SEQUENCE)} bloques temporales")
