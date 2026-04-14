"""
Script de configuración e instalación para FPM Calibration Tool
================================================================
Verifica las dependencias y prueba la instalación.
"""

import sys
import subprocess


def check_python_version():
    """Verifica que la versión de Python sea adecuada."""
    print("Verificando versión de Python...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("  ⚠ Advertencia: Se recomienda Python 3.7 o superior")
        return False
    else:
        print("  ✓ Versión adecuada")
        return True


def check_module(module_name, import_name=None):
    """Verifica si un módulo está instalado."""
    if import_name is None:
        import_name = module_name

    try:
        __import__(import_name)
        print(f"  ✓ {module_name} instalado")
        return True
    except ImportError:
        print(f"  ✗ {module_name} NO instalado")
        return False


def install_requirements():
    """Instala las dependencias desde requirements_calibration.txt."""
    print("\n¿Deseas instalar las dependencias ahora? (s/n): ", end="")
    response = input().lower()

    if response == 's':
        print("\nInstalando dependencias...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r",
                "requirements_calibration.txt"
            ])
            print("✓ Dependencias instaladas correctamente")
            return True
        except subprocess.CalledProcessError:
            print("✗ Error al instalar dependencias")
            return False
    else:
        print("Instalación cancelada")
        return False


def test_opencv():
    """Prueba básica de OpenCV."""
    print("\nProbando OpenCV...")
    try:
        import cv2
        import numpy as np

        # Crear una imagen de prueba
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.circle(img, (50, 50), 30, (0, 255, 0), 2)

        print(f"  OpenCV versión: {cv2.__version__}")
        print("  ✓ OpenCV funciona correctamente")
        return True
    except Exception as e:
        print(f"  ✗ Error en OpenCV: {e}")
        return False


def test_tkinter():
    """Prueba básica de Tkinter."""
    print("\nProbando Tkinter (GUI)...")
    try:
        from tkinter import Tk
        root = Tk()
        root.withdraw()
        root.destroy()
        print("  ✓ Tkinter funciona correctamente")
        return True
    except Exception as e:
        print(f"  ✗ Error en Tkinter: {e}")
        print("  Nota: Tkinter es necesario para el diálogo de selección de archivos")
        return False


def main():
    """Función principal."""
    print("="*60)
    print("FPM CALIBRATION TOOL - SETUP Y VERIFICACIÓN")
    print("="*60)

    # Verificar Python
    python_ok = check_python_version()

    # Verificar módulos
    print("\nVerificando módulos Python...")
    opencv_installed = check_module("opencv-python", "cv2")
    numpy_installed = check_module("numpy", "numpy")
    tkinter_installed = check_module("tkinter", "tkinter")

    # Resumen
    all_ok = opencv_installed and numpy_installed

    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)

    if all_ok:
        print("✓ Todos los módulos requeridos están instalados")

        # Tests adicionales
        opencv_ok = test_opencv()
        tkinter_ok = test_tkinter()

        if opencv_ok and tkinter_ok:
            print("\n" + "="*60)
            print("✓ INSTALACIÓN COMPLETA Y FUNCIONAL")
            print("="*60)
            print("\nPuedes ejecutar la herramienta con:")
            print("  python fpm_calibration_tool.py")
            print("\nO generar una imagen de prueba:")
            print("  python generate_test_image.py")
        else:
            print("\n⚠ Hay problemas con algunos módulos")

    else:
        print("✗ Faltan módulos requeridos")
        install_requirements()

        # Re-verificar después de la instalación
        print("\nVerificando instalación...")
        opencv_installed = check_module("opencv-python", "cv2")
        numpy_installed = check_module("numpy", "numpy")

        if opencv_installed and numpy_installed:
            print("\n✓ Instalación exitosa")
            test_opencv()
            test_tkinter()
        else:
            print("\n✗ Algunos módulos aún no están instalados")
            print("\nPuedes instalar manualmente con:")
            print("  pip install -r requirements_calibration.txt")


if __name__ == "__main__":
    main()
