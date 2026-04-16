"""
CubeSat EdgeAI — Entry point.

Uso:
    python main.py                  # Abre GUI
    python main.py --cli            # Corre pipeline sin GUI
    python main.py --viewer         # Abre visor interactivo
    python main.py --fpm FOLDER     # Reconstruccion FPM desde CLI
    python main.py --folder X       # Especifica carpeta de entrada
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="CubeSat EdgeAI Pipeline")
    parser.add_argument("--cli", action="store_true",
                        help="Ejecutar en modo CLI (sin GUI)")
    parser.add_argument("--viewer", action="store_true",
                        help="Abrir visor interactivo de resultados")
    parser.add_argument("--fpm", type=str, default=None, metavar="FOLDER",
                        help="Reconstruccion FPM desde carpeta de scan")
    parser.add_argument("--fpm-upscale", type=int, default=2,
                        help="Factor de upscale FPM (2, 3, 4)")
    parser.add_argument("--fpm-iters", type=int, default=15,
                        help="Iteraciones FPM")
    parser.add_argument("--fpm-method", type=str, default="multiangle",
                        choices=["multiangle", "multiframe", "fourier"],
                        help="Metodo: multiangle (lensless+OLED), multiframe (con shifts), fourier (con lente)")
    parser.add_argument("--folder", type=str, default=None,
                        help="Carpeta de imagenes de entrada")
    parser.add_argument("--config", type=str, default=None,
                        help="Ruta al archivo config.yaml")
    args = parser.parse_args()

    if args.fpm:
        from pipeline.fpm_reconstruction import reconstruct_fpm
        result = reconstruct_fpm(
            scan_folder=args.fpm,
            upscale_factor=args.fpm_upscale,
            max_iters=args.fpm_iters,
            method=args.fpm_method,
        )
        print(f"\nFPM completado: x{result['upscale_factor']}")
        print(f"  Escala HR: {result['um_per_pixel_hr']:.4f} um/px")
        print(f"  Archivos: {result['files']}")
    elif args.viewer:
        from pipeline.viewer import run_viewer
        run_viewer(input_folder=args.folder, config_path=args.config)
    elif args.cli:
        from pipeline.controller import PipelineController
        controller = PipelineController(config_path=args.config)
        result = controller.run(input_folder=args.folder)
        print(f"\nResultados en: {result['output_dir']}")
    else:
        from pipeline.gui import PipelineGUI
        app = PipelineGUI()
        if args.folder:
            app.input_folder.set(args.folder)
        app.run()


if __name__ == "__main__":
    main()
