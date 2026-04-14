"""
Script de Analisis y Visualizacion de Calibracion FPM
Genera graficos cientificos para evaluar calidad de calibracion
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

# Configuracion de estilo cientifico
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class AnalisisCalibraccion:
    def __init__(self, csv_path, patron_nominal_um=2.0):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.nombre_archivo = Path(csv_path).stem

        # Parametros conocidos
        self.diametro_real_um = float(patron_nominal_um)
        self.radio_real_um = self.diametro_real_um / 2.0

    def calcular_estadisticas(self):
        """Calcula estadisticas completas de la calibracion"""
        stats = {}

        # Escala um/pixel
        stats['escala_media'] = self.df['um_per_pixel'].mean()
        stats['escala_mediana'] = self.df['um_per_pixel'].median()
        stats['escala_std'] = self.df['um_per_pixel'].std()
        stats['escala_cv'] = (stats['escala_std'] / stats['escala_media']) * 100
        stats['escala_min'] = self.df['um_per_pixel'].min()
        stats['escala_max'] = self.df['um_per_pixel'].max()

        # Radio medido en pixeles
        stats['radio_px_media'] = self.df['radius_px'].mean()
        stats['radio_px_std'] = self.df['radius_px'].std()
        stats['radio_px_cv'] = (stats['radio_px_std'] / stats['radio_px_media']) * 100

        # Diametros calculados en micrometros usando cada escala
        self.df['diametro_calculado_um'] = self.df['diameter_px'] * self.df['um_per_pixel']
        stats['diametro_um_media'] = self.df['diametro_calculado_um'].mean()
        stats['diametro_um_std'] = self.df['diametro_calculado_um'].std()

        # Error respecto al valor nominal (2 um)
        self.df['error_absoluto'] = self.df['diametro_calculado_um'] - self.diametro_real_um
        self.df['error_relativo'] = (self.df['error_absoluto'] / self.diametro_real_um) * 100
        stats['error_medio'] = self.df['error_relativo'].mean()
        stats['error_std'] = self.df['error_relativo'].std()

        # Numero de mediciones
        stats['n_mediciones'] = len(self.df)

        return stats

    def generar_reporte_texto(self, stats):
        """Genera reporte de texto con estadisticas"""
        print("\n" + "="*70)
        print("REPORTE DE CALIBRACION - FPM CALIBRATION TOOL")
        print("="*70)
        print(f"Archivo: {self.nombre_archivo}")
        print(f"Numero de mediciones: {stats['n_mediciones']}")
        print(f"Dimension nominal patron: {self.diametro_real_um} um")
        print("\n" + "-"*70)
        print("ESCALA (um/pixel)")
        print("-"*70)
        print(f"  Media:    {stats['escala_media']:.6f} um/px")
        print(f"  Mediana:  {stats['escala_mediana']:.6f} um/px")
        print(f"  Std Dev:  {stats['escala_std']:.6f} um/px")
        print(f"  CV:       {stats['escala_cv']:.2f}%")
        print(f"  Rango:    [{stats['escala_min']:.6f}, {stats['escala_max']:.6f}] um/px")

        print("\n" + "-"*70)
        print("RADIO MEDIDO (pixeles)")
        print("-"*70)
        print(f"  Media:    {stats['radio_px_media']:.2f} px")
        print(f"  Std Dev:  {stats['radio_px_std']:.2f} px")
        print(f"  CV:       {stats['radio_px_cv']:.2f}%")

        print("\n" + "-"*70)
        print("DIMENSION CALCULADA (micrometros)")
        print("-"*70)
        print(f"  Media:    {stats['diametro_um_media']:.4f} um")
        print(f"  Std Dev:  {stats['diametro_um_std']:.4f} um")
        print(f"  Nominal:  {self.diametro_real_um} um")

        print("\n" + "-"*70)
        print("ERROR RESPECTO AL NOMINAL")
        print("-"*70)
        print(f"  Error medio:     {stats['error_medio']:.2f}%")
        print(f"  Error std:       {stats['error_std']:.2f}%")

        print("\n" + "-"*70)
        print("CALIDAD DE CALIBRACION")
        print("-"*70)
        if stats['escala_cv'] < 3:
            calidad = "EXCELENTE"
            icono = "✓✓✓"
        elif stats['escala_cv'] < 5:
            calidad = "BUENA"
            icono = "✓✓"
        elif stats['escala_cv'] < 10:
            calidad = "ACEPTABLE"
            icono = "✓"
        else:
            calidad = "POBRE - Recalibrar recomendado"
            icono = "✗"

        print(f"  CV < 5%:  {icono} {calidad}")
        print(f"  Escala recomendada: {stats['escala_mediana']:.6f} um/px")
        print("="*70 + "\n")

        return calidad

    def plot_completo(self, stats):
        """Genera figura completa con 6 subplots cientificos"""
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle(f'Analisis de Calibracion FPM - {self.nombre_archivo}',
                     fontsize=16, fontweight='bold')

        # 1. Distribucion de escala (um/pixel)
        ax1 = plt.subplot(2, 3, 1)
        ax1.hist(self.df['um_per_pixel'], bins=15, color='steelblue',
                edgecolor='black', alpha=0.7)
        ax1.axvline(stats['escala_media'], color='red', linestyle='--',
                   linewidth=2, label=f'Media: {stats["escala_media"]:.4f}')
        ax1.axvline(stats['escala_mediana'], color='green', linestyle='--',
                   linewidth=2, label=f'Mediana: {stats["escala_mediana"]:.4f}')
        ax1.set_xlabel('Escala (um/pixel)', fontsize=11)
        ax1.set_ylabel('Frecuencia', fontsize=11)
        ax1.set_title('Distribucion de Escala', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Boxplot de escala
        ax2 = plt.subplot(2, 3, 2)
        bp = ax2.boxplot([self.df['um_per_pixel']],
                         labels=['Escala (um/px)'],
                         patch_artist=True,
                         showmeans=True)
        bp['boxes'][0].set_facecolor('lightblue')
        bp['means'][0].set_marker('D')
        bp['means'][0].set_markerfacecolor('red')
        ax2.set_ylabel('um/pixel', fontsize=11)
        ax2.set_title('Boxplot - Escala', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        # Agregar texto con estadisticas
        textstr = f'CV = {stats["escala_cv"]:.2f}%\nn = {stats["n_mediciones"]}'
        ax2.text(0.7, 0.95, textstr, transform=ax2.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 3. Radio medido (pixeles) vs ID
        ax3 = plt.subplot(2, 3, 3)
        ax3.plot(self.df.index + 1, self.df['radius_px'], 'o-',
                color='purple', markersize=8, linewidth=2)
        ax3.axhline(stats['radio_px_media'], color='red', linestyle='--',
                   linewidth=2, label=f'Media: {stats["radio_px_media"]:.2f} px')
        ax3.fill_between(self.df.index + 1,
                        stats['radio_px_media'] - stats['radio_px_std'],
                        stats['radio_px_media'] + stats['radio_px_std'],
                        alpha=0.2, color='red', label=f'±1 SD')
        ax3.set_xlabel('ID de medición', fontsize=11)
        ax3.set_ylabel('Distancia Media (pixeles)', fontsize=11)
        ax3.set_title('Dist. Media Medida en Pixeles', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. Diametro calculado vs nominal
        ax4 = plt.subplot(2, 3, 4)
        ax4.scatter(range(1, len(self.df) + 1), self.df['diametro_calculado_um'],
                   s=100, alpha=0.6, c=self.df['error_absoluto'],
                   cmap='RdYlGn_r', edgecolors='black')
        ax4.axhline(self.diametro_real_um, color='blue', linestyle='-',
                   linewidth=3, label=f'Nominal: {self.diametro_real_um} um')
        ax4.axhline(stats['diametro_um_media'], color='red', linestyle='--',
                   linewidth=2, label=f'Medido: {stats["diametro_um_media"]:.4f} um')
        ax4.set_xlabel('ID de medición', fontsize=11)
        ax4.set_ylabel('Dimensión completada (um)', fontsize=11)
        ax4.set_title('Dimensión: Medido vs Nominal', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        cbar = plt.colorbar(ax4.collections[0], ax=ax4)
        cbar.set_label('Error absoluto (um)', fontsize=9)

        # 5. Error relativo
        ax5 = plt.subplot(2, 3, 5)
        colors = ['red' if abs(e) > 5 else 'green' for e in self.df['error_relativo']]
        ax5.bar(self.df.index + 1, self.df['error_relativo'],
               color=colors, alpha=0.7, edgecolor='black')
        ax5.axhline(0, color='black', linestyle='-', linewidth=2)
        ax5.axhline(5, color='orange', linestyle='--', linewidth=1,
                   label='±5% limite')
        ax5.axhline(-5, color='orange', linestyle='--', linewidth=1)
        ax5.set_xlabel('ID de medición', fontsize=11)
        ax5.set_ylabel('Error (%)', fontsize=11)
        ax5.set_title('Error Relativo vs Nominal', fontweight='bold')
        ax5.legend()
        ax5.grid(True, alpha=0.3, axis='y')

        # 6. QQ-plot (normalidad)
        ax6 = plt.subplot(2, 3, 6)
        from scipy import stats as sp_stats
        sp_stats.probplot(self.df['um_per_pixel'], dist="norm", plot=ax6)
        ax6.set_title('Q-Q Plot (Normalidad)', fontweight='bold')
        ax6.grid(True, alpha=0.3)

        plt.tight_layout()

        # Guardar figura
        output_path = Path(self.csv_path).parent / f"{self.nombre_archivo}_analisis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nGrafico guardado en: {output_path}")

        return fig

    def exportar_reporte_completo(self, stats, calidad):
        """Exporta reporte completo en formato texto"""
        output_path = Path(self.csv_path).parent / f"{self.nombre_archivo}_reporte.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("REPORTE DE CALIBRACION - FPM CALIBRATION TOOL\n")
            f.write("="*70 + "\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Archivo: {self.nombre_archivo}\n")
            f.write(f"Numero de mediciones: {stats['n_mediciones']}\n")
            f.write(f"Dimension nominal patron: {self.diametro_real_um} um\n\n")

            f.write("-"*70 + "\n")
            f.write("RESULTADOS PRINCIPALES\n")
            f.write("-"*70 + "\n")
            f.write(f"Escala recomendada:  {stats['escala_mediana']:.6f} um/pixel\n")
            f.write(f"Desviacion estandar: {stats['escala_std']:.6f} um/pixel\n")
            f.write(f"Coeficiente de variacion: {stats['escala_cv']:.2f}%\n")
            f.write(f"Calidad de calibracion: {calidad}\n\n")

            f.write("-"*70 + "\n")
            f.write("ESTADISTICAS DETALLADAS\n")
            f.write("-"*70 + "\n")
            f.write(f"Escala media:        {stats['escala_media']:.6f} um/px\n")
            f.write(f"Escala mediana:      {stats['escala_mediana']:.6f} um/px\n")
            f.write(f"Escala min:          {stats['escala_min']:.6f} um/px\n")
            f.write(f"Escala max:          {stats['escala_max']:.6f} um/px\n")
            f.write(f"Radio medio (px):    {stats['radio_px_media']:.2f} px\n")
            f.write(f"Diametro medido:     {stats['diametro_um_media']:.4f} um\n")
            f.write(f"Error medio:         {stats['error_medio']:.2f}%\n\n")

            f.write("-"*70 + "\n")
            f.write("DATOS INDIVIDUALES\n")
            f.write("-"*70 + "\n")
            f.write("ID | Dist.Media(px) | Escala(um/px) | Dim.Completa(um) | Error(%)\n")
            f.write("-"*70 + "\n")
            for idx, row in self.df.iterrows():
                f.write(f"{idx+1:2d} | {row['radius_px']:9.2f} | {row['um_per_pixel']:13.6f} | "
                       f"{row['diametro_calculado_um']:8.4f} | {row['error_relativo']:7.2f}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("INTERPRETACION\n")
            f.write("="*70 + "\n")
            f.write("CV < 3%:  Excelente - Alta precision\n")
            f.write("CV < 5%:  Buena - Aceptable para uso cientifico\n")
            f.write("CV < 10%: Aceptable - Considerar recalibrar\n")
            f.write("CV > 10%: Pobre - Recalibrar necesario\n")
            f.write("="*70 + "\n")

        print(f"Reporte de texto guardado en: {output_path}")

    def analizar(self):
        """Ejecuta analisis completo"""
        print("\nAnalizando datos de calibracion...")

        # Calcular estadisticas
        stats = self.calcular_estadisticas()

        # Generar reporte en consola
        calidad = self.generar_reporte_texto(stats)

        # Generar graficos
        print("\nGenerando graficos...")
        fig = self.plot_completo(stats)

        # Exportar reporte
        self.exportar_reporte_completo(stats, calidad)

        # Mostrar graficos
        plt.show()

        return stats


def seleccionar_archivo():
    """Abre dialogo para seleccionar archivo CSV"""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print("\n" + "="*70)
    print("ANALISIS DE CALIBRACION FPM")
    print("="*70)
    print("Selecciona el archivo CSV de calibracion...")

    file_path = filedialog.askopenfilename(
        title="Selecciona archivo CSV de calibracion",
        filetypes=[
            ("CSV files", "*.csv"),
            ("Todos los archivos", "*.*")
        ]
    )

    root.destroy()

    if not file_path:
        print("No se selecciono ningun archivo. Saliendo...")
        return None

    print(f"Archivo seleccionado: {file_path}\n")
    return file_path


def main():
    """Funcion principal"""
    from tkinter import simpledialog

    # Seleccionar archivo
    csv_path = seleccionar_archivo()

    if csv_path is None:
        return

    # Dialog to select pattern size
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    patron_str = simpledialog.askstring(
        "Dimensión del Patrón", 
        "Introduce la dimensión nominal del patrón en um:\n(Ej: 2.0 para microesferas, 1000 para línea 1mm, 300 para 0.3mm...)",
        initialvalue="1000.0"
    )
    
    root.destroy()
    
    if not patron_str:
        print("No se ingreso dimension. Saliendo...")
        return
        
    try:
        patron_nominal_um = float(patron_str)
    except ValueError:
        print("Valor de dimension invalido. Saliendo...")
        return

    try:
        # Crear analizador y ejecutar
        analizador = AnalisisCalibraccion(csv_path, patron_nominal_um)
        stats = analizador.analizar()

        print("\nAnalisis completado exitosamente!")

    except Exception as e:
        print(f"\nError durante el analisis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
