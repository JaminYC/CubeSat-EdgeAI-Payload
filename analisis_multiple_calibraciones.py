"""
Analisis Comparativo de Multiples Calibraciones
Permite comparar varias sesiones de calibracion en el tiempo
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from tkinter import Tk, filedialog
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")


class AnalisisMultipleCalibr:
    def __init__(self):
        self.datos = []
        self.nombres = []
        self.fechas = []

    def cargar_csv(self, csv_path):
        """Carga un CSV de calibracion"""
        df = pd.read_csv(csv_path)
        nombre = Path(csv_path).stem

        # Extraer fecha del nombre si es posible
        try:
            # Formato: fpm_calibration_YYYYMMDD_HHMMSS
            partes = nombre.split('_')
            if len(partes) >= 3:
                fecha_str = partes[2] + partes[3]
                fecha = datetime.strptime(fecha_str, '%Y%m%d%H%M%S')
            else:
                fecha = datetime.now()
        except:
            fecha = datetime.now()

        self.datos.append(df)
        self.nombres.append(nombre)
        self.fechas.append(fecha)

        print(f"Cargado: {nombre} ({len(df)} microesferas)")

    def calcular_estadisticas_por_sesion(self):
        """Calcula estadisticas para cada sesion"""
        stats_list = []

        for i, df in enumerate(self.datos):
            stats = {
                'nombre': self.nombres[i],
                'fecha': self.fechas[i],
                'n': len(df),
                'escala_media': df['um_per_pixel'].mean(),
                'escala_mediana': df['um_per_pixel'].median(),
                'escala_std': df['um_per_pixel'].std(),
                'escala_cv': (df['um_per_pixel'].std() / df['um_per_pixel'].mean()) * 100,
                'radio_px_media': df['radius_px'].mean(),
                'radio_px_std': df['radius_px'].std()
            }
            stats_list.append(stats)

        return pd.DataFrame(stats_list)

    def plot_comparacion_escalas(self, stats_df):
        """Grafico comparativo de escalas entre sesiones"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Comparacion de Calibraciones - Escala (um/pixel)',
                     fontsize=16, fontweight='bold')

        # 1. Barras con escala media y error bars
        ax1 = axes[0, 0]
        x_pos = np.arange(len(stats_df))
        ax1.bar(x_pos, stats_df['escala_media'], yerr=stats_df['escala_std'],
               capsize=5, alpha=0.7, color='steelblue', edgecolor='black')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels([f"S{i+1}" for i in range(len(stats_df))], rotation=0)
        ax1.set_ylabel('Escala (um/pixel)', fontsize=11)
        ax1.set_xlabel('Sesion', fontsize=11)
        ax1.set_title('Escala Media ± SD', fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')

        # 2. Boxplots de todas las sesiones
        ax2 = axes[0, 1]
        data_for_box = [df['um_per_pixel'].values for df in self.datos]
        bp = ax2.boxplot(data_for_box,
                        labels=[f"S{i+1}" for i in range(len(self.datos))],
                        patch_artist=True,
                        showmeans=True)
        for patch, color in zip(bp['boxes'], sns.color_palette("Set2", len(self.datos))):
            patch.set_facecolor(color)
        ax2.set_ylabel('Escala (um/pixel)', fontsize=11)
        ax2.set_xlabel('Sesion', fontsize=11)
        ax2.set_title('Distribucion por Sesion', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. Coeficiente de variacion
        ax3 = axes[1, 0]
        colors = ['green' if cv < 5 else 'orange' if cv < 10 else 'red'
                 for cv in stats_df['escala_cv']]
        ax3.bar(x_pos, stats_df['escala_cv'], color=colors, alpha=0.7, edgecolor='black')
        ax3.axhline(5, color='orange', linestyle='--', linewidth=2, label='Limite 5%')
        ax3.axhline(10, color='red', linestyle='--', linewidth=2, label='Limite 10%')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels([f"S{i+1}" for i in range(len(stats_df))], rotation=0)
        ax3.set_ylabel('CV (%)', fontsize=11)
        ax3.set_xlabel('Sesion', fontsize=11)
        ax3.set_title('Coeficiente de Variacion', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. Evolucion temporal (si hay fechas)
        ax4 = axes[1, 1]
        if len(set(self.fechas)) > 1:  # Si hay fechas diferentes
            ax4.plot(self.fechas, stats_df['escala_media'], 'o-',
                    markersize=10, linewidth=2, color='navy')
            ax4.fill_between(self.fechas,
                           stats_df['escala_media'] - stats_df['escala_std'],
                           stats_df['escala_media'] + stats_df['escala_std'],
                           alpha=0.3, color='blue')
            ax4.set_xlabel('Fecha', fontsize=11)
            ax4.set_ylabel('Escala (um/pixel)', fontsize=11)
            ax4.set_title('Evolucion Temporal', fontweight='bold')
            ax4.grid(True, alpha=0.3)
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            ax4.text(0.5, 0.5, 'Datos de una sola fecha\nNo hay evolucion temporal',
                    ha='center', va='center', fontsize=12, transform=ax4.transAxes)
            ax4.set_title('Evolucion Temporal (N/A)', fontweight='bold')

        plt.tight_layout()
        return fig

    def plot_todos_los_datos(self):
        """Grafico con todos los datos individuales"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('Datos Individuales - Todas las Calibraciones',
                     fontsize=16, fontweight='bold')

        # 1. Violin plot de escalas
        ax1 = axes[0]
        all_data = []
        labels = []
        for i, df in enumerate(self.datos):
            all_data.extend(df['um_per_pixel'].values)
            labels.extend([f"S{i+1}"] * len(df))

        df_plot = pd.DataFrame({'Escala': all_data, 'Sesion': labels})
        sns.violinplot(data=df_plot, x='Sesion', y='Escala', ax=ax1, palette="Set2")
        ax1.set_ylabel('Escala (um/pixel)', fontsize=11)
        ax1.set_xlabel('Sesion', fontsize=11)
        ax1.set_title('Violin Plot - Distribucion Completa', fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')

        # 2. Scatter de radio vs escala
        ax2 = axes[1]
        for i, df in enumerate(self.datos):
            ax2.scatter(df['radius_px'], df['um_per_pixel'],
                       label=f"S{i+1}", s=80, alpha=0.6, edgecolors='black')
        ax2.set_xlabel('Radio (pixeles)', fontsize=11)
        ax2.set_ylabel('Escala (um/pixel)', fontsize=11)
        ax2.set_title('Radio vs Escala', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def generar_tabla_resumen(self, stats_df):
        """Genera tabla resumen en consola"""
        print("\n" + "="*100)
        print("RESUMEN COMPARATIVO DE CALIBRACIONES")
        print("="*100)
        print(f"{'Sesion':<10} {'N':<5} {'Escala Media':<15} {'SD':<12} {'CV(%)':<8} {'Radio(px)':<12}")
        print("-"*100)

        for idx, row in stats_df.iterrows():
            print(f"S{idx+1:<9} {row['n']:<5} {row['escala_media']:<15.6f} "
                  f"{row['escala_std']:<12.6f} {row['escala_cv']:<8.2f} {row['radio_px_media']:<12.2f}")

        print("-"*100)

        # Estadisticas globales
        todas_escalas = np.concatenate([df['um_per_pixel'].values for df in self.datos])
        print(f"\nESTADISTICAS GLOBALES (todas las sesiones):")
        print(f"  Total mediciones: {len(todas_escalas)}")
        print(f"  Escala global media: {todas_escalas.mean():.6f} um/px")
        print(f"  Escala global SD: {todas_escalas.std():.6f} um/px")
        print(f"  Escala global CV: {(todas_escalas.std()/todas_escalas.mean())*100:.2f}%")
        print(f"  Rango: [{todas_escalas.min():.6f}, {todas_escalas.max():.6f}] um/px")

        # Diferencia entre sesiones
        if len(stats_df) > 1:
            max_diff = (stats_df['escala_media'].max() - stats_df['escala_media'].min())
            max_diff_pct = (max_diff / stats_df['escala_media'].mean()) * 100
            print(f"\n  Diferencia max entre sesiones: {max_diff:.6f} um/px ({max_diff_pct:.2f}%)")

        print("="*100 + "\n")

    def analizar(self):
        """Ejecuta analisis completo"""
        if len(self.datos) == 0:
            print("No hay datos cargados!")
            return

        print("\nAnalizando calibraciones...")

        # Calcular estadisticas
        stats_df = self.calcular_estadisticas_por_sesion()

        # Tabla resumen
        self.generar_tabla_resumen(stats_df)

        # Graficos
        print("Generando graficos...")
        fig1 = self.plot_comparacion_escalas(stats_df)
        fig2 = self.plot_todos_los_datos()

        # Guardar
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path1 = Path(self.datos[0]).parent if hasattr(self.datos[0], 'parent') else Path.cwd()

        # Intentar obtener directorio del primer archivo
        # (ya que self.datos contiene DataFrames, no paths)
        output_dir = Path.cwd()  # Por defecto

        fig1.savefig(output_dir / f"comparacion_calibraciones_{timestamp}.png",
                    dpi=300, bbox_inches='tight')
        fig2.savefig(output_dir / f"datos_individuales_{timestamp}.png",
                    dpi=300, bbox_inches='tight')

        print(f"Graficos guardados en: {output_dir}")

        plt.show()


def main():
    """Funcion principal"""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print("\n" + "="*70)
    print("ANALISIS COMPARATIVO DE MULTIPLES CALIBRACIONES")
    print("="*70)
    print("\nSelecciona los archivos CSV de calibracion que deseas comparar...")
    print("(Puedes seleccionar multiples archivos manteniendo Ctrl)")

    file_paths = filedialog.askopenfilenames(
        title="Selecciona archivos CSV de calibracion",
        filetypes=[
            ("CSV files", "*.csv"),
            ("Todos los archivos", "*.*")
        ]
    )

    root.destroy()

    if not file_paths or len(file_paths) == 0:
        print("No se seleccionaron archivos. Saliendo...")
        return

    print(f"\n{len(file_paths)} archivo(s) seleccionado(s)\n")

    try:
        # Crear analizador
        analizador = AnalisisMultipleCalibr()

        # Cargar todos los archivos
        for path in file_paths:
            analizador.cargar_csv(path)

        # Analizar
        analizador.analizar()

        print("\nAnalisis completado exitosamente!")

    except Exception as e:
        print(f"\nError durante el analisis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
