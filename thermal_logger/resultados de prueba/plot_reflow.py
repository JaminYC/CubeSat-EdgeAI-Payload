import csv
import sys
import math
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import json

def draw_reflow_reference(ax):
    # Zonas de tiempo (segundos)
    zones = [
        (0,   90,  "#fab387", "Pre-heating (0-90 s)"),
        (90,  180, "#f9e2af", "Soaking (90-180 s)"),
        (180, 240, "#f38ba8", "Reflow (180-240 s)"),
        (240, 300, "#89b4fa", "Cooling"),
    ]
    for t0, t1, color, label in zones:
        ax.axvspan(t0, t1, alpha=0.08, color=color, zorder=0)
        if label != "Cooling":
            ax.text((t0+t1)/2, 8, label, ha="center", va="bottom",
                    fontsize=7.5, color=color, alpha=0.9)

    hlines = [
        (150, "#f9e2af", "150°C soak start"),
        (183, "#fab387", "183°C liquidus"),
        (217, "#f38ba8", "217°C peak min"),
        (225, "#f38ba8", "225°C peak max"),
    ]
    for temp, color, label in hlines:
        ax.axhline(temp, color=color, linewidth=0.8, linestyle="--", alpha=0.6, zorder=1)
        ax.text(495, temp, label, va="center", fontsize=7, color=color, alpha=0.85)

    for t in [90, 180, 240]:
        ax.axvline(t, color="#6c7086", linewidth=0.8, linestyle=":", alpha=0.7)

    ax.set_xlim(0, 500)
    ax.set_ylim(0, 250)

t_s_data = []
temp_raw_data = []
try:
    with open('prueba1_20260306_154613.csv', 'r') as f:
        reader = csv.reader(f)
        headers = None
        t_offset = None
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            if headers is None:
                headers = row
                continue
            t_ms = int(row[0])
            if t_offset is None:
                t_offset = t_ms
            t_s_data.append((t_ms - t_offset) / 1000.0)
            temp_raw_data.append(float(row[1]))

    if not t_s_data:
        sys.exit("No data found")

    max_t = int(math.ceil(t_s_data[-1]))
    num_intervals = int(math.ceil(max_t / 30.0))
    if num_intervals == 0: num_intervals = 1

    fig, ax = plt.subplots(figsize=(15, 8))
    # Leave room on the right for all sliders, and bottom for time sliders
    plt.subplots_adjust(left=0.05, right=0.55, bottom=0.15, top=0.9)
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#1e1e2e")
    ax.set_xlabel("Tiempo (s)", color="#cdd6f4")
    ax.set_ylabel("Temperatura (°C)", color="#cdd6f4")
    ax.tick_params(colors="#cdd6f4")
    for spine in ax.spines.values():
        spine.set_edgecolor("#45475a")
    ax.grid(True, alpha=0.2, color="#45475a")
    ax.set_title("Prueba 1 vs Kester Reflow (Tuning cada 30s)", color="#cdd6f4", fontsize=12, pad=10)

    draw_reflow_reference(ax)

    gains = [1.0] * num_intervals
    offsets = [0.0] * num_intervals

    def get_calibrated_data(g_arr, o_arr):
        calib = []
        for t, raw in zip(t_s_data, temp_raw_data):
            idx = int(t // 30)
            if idx >= num_intervals:
                idx = num_intervals - 1
            calib.append((raw * g_arr[idx]) + o_arr[idx])
        return calib

    temp_calibrated = get_calibrated_data(gains, offsets)

    real_line, = ax.plot(t_s_data, temp_calibrated, color="#f38ba8", linewidth=2.0, marker="o", markersize=3, label="Data Real Calibrada")
    ideal_t = [0, 90, 150, 180, 210, 240, 270]
    ideal_temp = [25, 150, 165, 180, 215, 180, 150]
    ideal_line, = ax.plot(ideal_t, ideal_temp, color="#a6e3a1", linewidth=2.0, linestyle="-.", marker="s", markersize=4, label="Patrón Kester")
    ax.legend(facecolor="#313244", labelcolor="#cdd6f4", fontsize=10, loc="upper left")

    # Dibujar las lineas divisorias de 30s en la grafica para guiar al usuario
    for i in range(1, num_intervals):
        ax.axvline(i * 30, color="#f38ba8", linestyle=":", linewidth=0.5, alpha=0.3)

    # Añadir los sliders a la derecha
    slider_gains = []
    slider_offsets = []
    dy = 0.85 / num_intervals

    for i in range(num_intervals):
        t_start = i * 30
        t_end = t_start + 30
        # invertimos el eje Y para que los primeros segundos esten arriba
        y_pos = 0.92 - (i + 1) * dy 
        
        ax_g = plt.axes([0.62, y_pos + dy*0.2, 0.12, min(dy*0.6, 0.03)], facecolor='#313244')
        ax_o = plt.axes([0.83, y_pos + dy*0.2, 0.12, min(dy*0.6, 0.03)], facecolor='#313244')
        
        sg = Slider(ax_g, f'{t_start}-{t_end}s G', 0.1, 10.0, valinit=1.0, valstep=0.01, color="#fab387")
        so = Slider(ax_o, f'OFS (°C)', -250.0, 250.0, valinit=0.0, valstep=0.5, color="#89b4fa")
        
        sg.label.set_color('#cdd6f4'); sg.label.set_fontsize(8)
        sg.valtext.set_color('#cdd6f4'); sg.valtext.set_fontsize(8)
        so.label.set_color('#cdd6f4'); so.label.set_fontsize(8)
        so.valtext.set_color('#cdd6f4'); so.valtext.set_fontsize(8)
        
        slider_gains.append(sg)
        slider_offsets.append(so)

    # Añadir globales de tiempo
    ax_time_scale = plt.axes([0.1, 0.06, 0.4, 0.02], facecolor='#313244')
    ax_time_shift = plt.axes([0.1, 0.02, 0.4, 0.02], facecolor='#313244')
    st_scale = Slider(ax_time_scale, 'Time Stretch', 0.1, 5.0, valinit=1.0, valstep=0.01, color="#a6e3a1")
    st_shift = Slider(ax_time_shift, 'Time Shift', -300.0, 300.0, valinit=0.0, valstep=1.0, color="#a6e3a1")
    st_scale.label.set_color('#cdd6f4'); st_scale.valtext.set_color('#cdd6f4')
    st_shift.label.set_color('#cdd6f4'); st_shift.valtext.set_color('#cdd6f4')

    def update(val):
        curr_gains = [s.val for s in slider_gains]
        curr_offsets = [s.val for s in slider_offsets]
        x_scale = st_scale.val
        x_shift = st_shift.val
        
        new_y = get_calibrated_data(curr_gains, curr_offsets)
        new_x = [(t * x_scale) + x_shift for t in t_s_data]
        
        real_line.set_data(new_x, new_y)
        fig.canvas.draw_idle()

    for sg, so in zip(slider_gains, slider_offsets):
        sg.on_changed(update)
        so.on_changed(update)
        
    st_scale.on_changed(update)
    st_shift.on_changed(update)

    # Save button
    ax_save = plt.axes([0.65, 0.04, 0.2, 0.05])
    btn_save = Button(ax_save, 'Guardar Config', color="#89b4fa", hovercolor="#a6e3a1")
    
    def save_config(event):
        config_data = {
            "time_stretch": round(st_scale.val, 4),
            "time_shift": round(st_shift.val, 4),
            "intervals_30s": []
        }
        for i, (sg, so) in enumerate(zip(slider_gains, slider_offsets)):
            config_data["intervals_30s"].append({
                "time_start_s": i * 30,
                "time_end_s": (i + 1) * 30,
                "gain": round(sg.val, 4),
                "offset_C": round(so.val, 4)
            })
        with open("calibracion_horno.json", "w", encoding="utf-8") as file:
            json.dump(config_data, file, indent=4)
        print("¡Configuración guardada exitosamente en calibracion_horno.json!")
        
    btn_save.on_clicked(save_config)

    # Hover events
    annot = ax.annotate("", xy=(0,0), xytext=(10,10),textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="#313244", ec="#cdd6f4", alpha=0.9),
                        arrowprops=dict(arrowstyle="->", color="#cdd6f4"),
                        color="#cdd6f4", fontsize=9)
    annot.set_visible(False)

    def update_annot(ind, line):
        x, y = line.get_data()
        idx = ind["ind"][0]
        pos_x, pos_y = x[idx], y[idx]
        annot.xy = (pos_x, pos_y)
        text = f"T = {pos_y:.1f} °C\nt = {pos_x:.1f} s"
        annot.set_text(text)
        annot.get_bbox_patch().set_alpha(0.9)

    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == ax:
            cont_real, ind_real = real_line.contains(event)
            cont_ideal, ind_ideal = ideal_line.contains(event)
            if cont_real:
                update_annot(ind_real, real_line)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            elif cont_ideal:
                update_annot(ind_ideal, ideal_line)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)
    plt.show()

except Exception as e:
    print("Error:", e)
    sys.exit(1)
