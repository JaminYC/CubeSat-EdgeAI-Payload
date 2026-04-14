python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name thermal_logger_gui tools/log_serial_gui.py
Compress-Archive -Path dist/thermal_logger_gui.exe,README.md -DestinationPath dist/thermal_logger_gui_portable.zip -Force
