import csv
import sys
import math
import matplotlib.pyplot as plt

def moving_average(data, window_size):
    if len(data) < window_size:
        return data
    smoothed = []
    for i in range(len(data)):
        start = max(0, i - window_size // 2)
        end = min(len(data), i + window_size // 2 + 1)
        window = data[start:end]
        smoothed.append(sum(window) / len(window))
    return smoothed

def analyze_thermal_plant(csv_filename):
    t_data = []
    temp_data = []
    
    # Leer datos
    with open(csv_filename, 'r') as f:
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
            t_data.append((t_ms - t_offset) / 1000.0)
            temp_data.append(float(row[1]))

    if not t_data:
        print("Error: No se encontraron datos.")
        return

    # Suavizar la señal de temperatura para evitar que el ruido rompa la derivada
    temp_smooth = moving_average(temp_data, window_size=15)

    # Calcular la Derivada (Tasa Térmica: °C / segundo)
    heating_rate = [0.0]  # Primer elemento es 0
    for i in range(1, len(t_data)):
        dt = t_data[i] - t_data[i-1]
        if dt == 0:
            dt = 0.001
        dT = temp_smooth[i] - temp_smooth[i-1]
        heating_rate.append(dT / dt)

    # -- ANALIZAR MÉTRICAS CLAVES DE LA PLANTA --
    
    # 1. Capacidad Máxima de Calentamiento
    max_hr_idx = heating_rate.index(max(heating_rate))
    max_heating_rate = heating_rate[max_hr_idx]
    max_heating_time = t_data[max_hr_idx]
    
    # 2. Capacidad de Enfriamiento Natural (Pérdida Térmica Máxima / Promedio)
    max_cooling_rate = min(heating_rate)
    
    # 3. Temperatura Pico Alcanzada
    peak_temp_idx = temp_smooth.index(max(temp_smooth))
    peak_temp = temp_smooth[peak_temp_idx]
    peak_time = t_data[peak_temp_idx]
    
    # 4. Analizar Tasa Promedio en la fase inicial de Calentamiento (e.g. 25C a 150C)
    idx_start = 0
    idx_150 = len(temp_smooth) - 1
    for i, t in enumerate(temp_smooth):
        if t > 50 and idx_start == 0:
            idx_start = i
        if t > 150:
            idx_150 = i
            break
            
    preheating_avg_rate = 0
    if idx_150 > idx_start:
        preheating_avg_rate = (temp_smooth[idx_150] - temp_smooth[idx_start]) / (t_data[idx_150] - t_data[idx_start])

    print("=========================================================")
    print("      REPORTE DE CARACTERIZACIÓN TÉRMICA DE PLANTA       ")
    print("=========================================================")
    print(f"Archivo analizado: {csv_filename}")
    print(f"Temperatura Pico Alcanzada: {peak_temp:.2f}°C en T={peak_time:.1f}s")
    print("\n--- DINÁMICA DE TEMPERATURA (Ecuaciones de Sistema) ---")
    print(f"Tasa MÁXIMA de calentamiento (Pendiente): {max_heating_rate:.3f} °C/seg (logrado en T={max_heating_time:.1f}s)")
    if preheating_avg_rate > 0:
        print(f"Tasa PROMEDIO de Pre-heating (50°C -> 150°C): {preheating_avg_rate:.3f} °C/seg")
    else:
        print("Tasa promedio pre-heating: N/A (No alcanzó 150°C correctamente)")
        
    print(f"Tasa MÁXIMA de enfriamiento natural: {max_cooling_rate:.3f} °C/seg")
    
    print("\n--- RESTRICCIONES KESTER (Referencia) ---")
    print("Kester Pre-heating: < 2.5 °C/seg")
    print("Kester Reflow subida: 1.3 - 1.6 °C/seg")
    
    print("\n--- CONCLUSIÓN PRELIMINAR DE ENTRADA AL PID ---")
    if max_heating_rate < 1.0:
        print("-> PRECAUCIÓN: Tu planta térmica carece de potencia bruta. Está subiendo")
        print("   muy lento. Requerirás dar potencia al 100% (Duty cycle) por un tiempo largo continuo.")
    elif max_heating_rate > 3.0:
        print("-> Tu horno tiene INMENSA potencia. Cuidado, deberás ajustar mucho tu ganancia limitativa.")
    else:
        print(f"-> Horno de potencia media. Estás entregando {max_heating_rate:.2f} °C/s máximos en las subidas libres.")
    
    print("=========================================================")

    # -- PLOT --
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    fig.patch.set_facecolor("#1e1e2e")
    
    # Eje 1: Temperatura
    ax1.set_facecolor("#1e1e2e")
    ax1.plot(t_data, temp_data, color="#45475a", alpha=0.5, label="Cruda")
    ax1.plot(t_data, temp_smooth, color="#f38ba8", linewidth=2.5, label="Temperatura Suavizada (Planta)")
    ax1.set_title("Respuesta del Sistema (Temperatura)", color="#cdd6f4")
    ax1.set_ylabel("Temperatura (°C)", color="#cdd6f4")
    ax1.tick_params(colors="#cdd6f4")
    ax1.grid(True, alpha=0.2)
    ax1.legend()
    
    # Eje 2: Derivada (Tasa de Calentamiento)
    ax2.set_facecolor("#1e1e2e")
    ax2.plot(t_data, heating_rate, color="#a6e3a1", linewidth=2)
    ax2.axhline(0, color="#f38ba8", linestyle="--", linewidth=1.5, alpha=0.6)
    ax2.axhline(2.5, color="#fab387", linestyle=":", linewidth=1.5, label="Límite Kester Pre-heating (2.5 °C/s)")
    ax2.set_title("Ecuación de Planta: Derivada (dT/dt)", color="#cdd6f4")
    ax2.set_xlabel("Tiempo (s)", color="#cdd6f4")
    ax2.set_ylabel("Tasa (°C / s)", color="#cdd6f4")
    ax2.tick_params(colors="#cdd6f4")
    ax2.grid(True, alpha=0.2)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('reporte_planta.png', facecolor=fig.get_facecolor(), dpi=150)
    print("\nGráfico de derivadas (dT/dt) generado en 'reporte_planta.png'. Cerrando programa.")
    plt.show()

if __name__ == "__main__":
    analyze_thermal_plant('prueba1_20260306_154613.csv')
