python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name thermal_logger_gui tools/log_serial_gui.py

$iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
if (!(Test-Path $iscc)) {
  throw "ISCC.exe not found. Install Inno Setup 6 first."
}

& $iscc installer\thermal_logger_installer.iss
