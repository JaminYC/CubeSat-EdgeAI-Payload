"""
CubeSat EdgeAI — Entry point.

Uso:
    python main.py              # Abre GUI
    python main.py --cli        # Corre pipeline sin GUI
    python main.py --folder X   # Especifica carpeta de entrada
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="CubeSat EdgeAI Pipeline")
    parser.add_argument("--cli", action="store_true",
                        help="Ejecutar en modo CLI (sin GUI)")
    parser.add_argument("--folder", type=str, default=None,
                        help="Carpeta de imagenes de entrada")
    parser.add_argument("--config", type=str, default=None,
                        help="Ruta al archivo config.yaml")
    args = parser.parse_args()

    if args.cli:
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
