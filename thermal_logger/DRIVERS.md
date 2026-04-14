# ESP32 Drivers for Windows

Thermal Logger needs the ESP32 board to appear as a COM port.
If no COM port is shown, install the USB-serial driver for your board chip.

## Common USB chips
- CP210x (Silicon Labs)
- CH340 / CH341 (WCH)
- FT232 (FTDI)

## Quick check
1. Connect ESP32 with a data USB cable.
2. Open Device Manager.
3. Check `Ports (COM & LPT)`.
4. If there is no COM device or there is a warning icon, install the correct driver.

## Notes
- Use a USB cable with data lines, not charge-only.
- After installing a driver, reconnect the board.
- In Thermal Logger, press `Refresh` and select the COM port.
