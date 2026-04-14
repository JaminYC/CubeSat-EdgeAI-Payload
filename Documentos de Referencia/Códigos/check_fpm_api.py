import sys, pkgutil
print("Python:", sys.executable)
print("Modules starting with fpm:")
for m in pkgutil.iter_modules():
    if m.name.startswith("fpm"):
        print(" -", m.name)

try:
    import fpm_py as fpm
    print("\nimport fpm_py OK")
    print("Version:", getattr(fpm,"__version__", "unknown"))
    print("Has ImageCapture?", hasattr(fpm,"ImageCapture"))
    print("Has ImageSeries?", hasattr(fpm,"ImageSeries"))
    print("Has FPM?", hasattr(fpm,"FPM"))
except Exception as e:
    print("\nimport fpm_py FAILED:", e)

try:
    import fpm
    print("\nimport fpm OK")
    import inspect
    print("file:", inspect.getsourcefile(fpm))
except Exception as e:
    print("\nimport fpm FAILED:", e)
