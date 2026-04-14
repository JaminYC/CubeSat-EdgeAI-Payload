#!/usr/bin/env python3
"""
GUI thermal logger for ESP32.

This file is additive and does not replace tools/log_serial.py.
"""

import csv
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import matplotlib
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from serial.tools import list_ports

matplotlib.use("TkAgg")


@dataclass
class SerialConfig:
    port: str
    baud: int = 115200


class SerialWorker(threading.Thread):
    def __init__(self, config: SerialConfig, event_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.config = config
        self.event_queue = event_queue
        self.stop_event = stop_event
        self.command_queue: queue.Queue[str] = queue.Queue()
        self.ser = None

    def send_command(self, cmd: str) -> None:
        self.command_queue.put(cmd.strip())

    def _emit(self, event_type: str, payload: dict) -> None:
        self.event_queue.put({"type": event_type, **payload})

    def run(self) -> None:
        try:
            self.ser = serial.Serial(self.config.port, self.config.baud, timeout=0.4)
            time.sleep(1.5)
            self._emit("status", {"message": f"Connected: {self.config.port} @ {self.config.baud}"})
        except serial.SerialException as exc:
            self._emit("error", {"message": f"Serial open error: {exc}"})
            return

        while not self.stop_event.is_set():
            try:
                while not self.command_queue.empty():
                    cmd = self.command_queue.get_nowait()
                    if not cmd:
                        continue
                    self.ser.write((cmd + "\n").encode("utf-8"))
                    self._emit("log", {"message": f"TX> {cmd}"})
            except Exception as exc:
                self._emit("error", {"message": f"Command send error: {exc}"})

            try:
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("#"):
                    self._emit("comment", {"line": line})
                    continue
                self._emit("line", {"line": line})
            except Exception as exc:
                self._emit("error", {"message": f"Read error: {exc}"})
                time.sleep(0.2)

        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self._emit("status", {"message": "Serial closed"})


class ThermalLoggerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Thermal Logger - Experiment UI")
        self.root.geometry("1200x760")

        self.event_queue: queue.Queue = queue.Queue()
        self.serial_stop = threading.Event()
        self.worker = None

        self.is_connected = False
        self.is_running = False
        self.expecting_header = False
        self.current_headers = None
        self.current_csv_file = None
        self.current_writer = None
        self.current_csv_path = None
        self.first_t_ms = None

        self.t_data = []
        self.temp_data = []
        self.filt_data = []
        self.plot_dirty = False
        self.template_artists = []
        self.zoom_window_s = 120.0

        self.output_dir = Path.cwd() / "results"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._build_ui()
        self._refresh_ports()
        self.root.after(150, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Port").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(top, width=16, textvariable=self.port_var, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(top, text="Refresh", command=self._refresh_ports).grid(row=0, column=2, padx=4, pady=4)

        ttk.Label(top, text="Baud").grid(row=0, column=3, padx=4, pady=4, sticky="w")
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(top, width=10, textvariable=self.baud_var).grid(row=0, column=4, padx=4, pady=4)

        self.connect_btn = ttk.Button(top, text="Connect", command=self._connect)
        self.connect_btn.grid(row=0, column=5, padx=6, pady=4)
        self.disconnect_btn = ttk.Button(top, text="Disconnect", command=self._disconnect, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=6, padx=6, pady=4)

        ttk.Separator(top, orient=tk.VERTICAL).grid(row=0, column=7, sticky="ns", padx=8)

        ttk.Label(top, text="Experiment").grid(row=0, column=8, padx=4, pady=4)
        self.exp_name_var = tk.StringVar(value="perfil")
        ttk.Entry(top, width=18, textvariable=self.exp_name_var).grid(row=0, column=9, padx=4, pady=4)

        ttk.Label(top, text="Rate (ms)").grid(row=0, column=10, padx=4, pady=4)
        self.rate_var = tk.StringVar(value="500")
        ttk.Entry(top, width=8, textvariable=self.rate_var).grid(row=0, column=11, padx=4, pady=4)

        ttk.Label(top, text="Offset (C)").grid(row=0, column=12, padx=4, pady=4)
        self.offset_var = tk.StringVar(value="0.0")
        ttk.Entry(top, width=8, textvariable=self.offset_var).grid(row=0, column=13, padx=4, pady=4)

        ttk.Label(top, text="Alpha EMA").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        self.alpha_var = tk.StringVar(value="0.10")
        ttk.Entry(top, width=8, textvariable=self.alpha_var).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(top, text="Apply ALPHA", command=self._apply_alpha).grid(row=1, column=2, padx=4, pady=4)

        ttk.Label(top, text="Spike (C)").grid(row=1, column=3, padx=4, pady=4, sticky="w")
        self.spike_var = tk.StringVar(value="15.0")
        ttk.Entry(top, width=8, textvariable=self.spike_var).grid(row=1, column=4, padx=4, pady=4)
        ttk.Button(top, text="Apply SPIKE", command=self._apply_spike).grid(row=1, column=5, padx=4, pady=4)
        ttk.Button(top, text="STATS", command=lambda: self._send_command("STATS")).grid(row=1, column=6, padx=4, pady=4)

        mid = ttk.Frame(self.root, padding=(8, 0, 8, 0))
        mid.pack(side=tk.TOP, fill=tk.X)

        self.start_btn = ttk.Button(mid, text="Start Experiment", command=self._start_experiment, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=4, pady=6)
        self.finish_btn = ttk.Button(mid, text="Finish Experiment", command=self._finish_experiment, state=tk.DISABLED)
        self.finish_btn.pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(mid, text="Mode RAW", command=lambda: self._send_mode("RAW")).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(mid, text="Mode FILTER", command=lambda: self._send_mode("FILTER")).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(mid, text="Apply RATE", command=self._apply_rate).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(mid, text="Apply OFFSET", command=self._apply_offset).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(mid, text="RESET", command=lambda: self._send_command("RESET")).pack(side=tk.LEFT, padx=4, pady=6)
        self.show_template_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            mid,
            text="Plantilla Reflow",
            variable=self.show_template_var,
            command=self._toggle_template,
        ).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(mid, text="Output Folder", command=self._choose_output_dir).pack(side=tk.LEFT, padx=8, pady=6)

        status = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        status.pack(side=tk.TOP, fill=tk.X)

        self.status_var = tk.StringVar(value="Status: Idle")
        self.temp_var = tk.StringVar(value="Temp: -- C")
        self.time_var = tk.StringVar(value="Time: -- s")
        self.file_var = tk.StringVar(value=f"Output: {self.output_dir}")
        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT, padx=6)
        ttk.Label(status, textvariable=self.temp_var).pack(side=tk.LEFT, padx=20)
        ttk.Label(status, textvariable=self.time_var).pack(side=tk.LEFT, padx=20)
        ttk.Label(status, textvariable=self.file_var).pack(side=tk.LEFT, padx=20)

        body = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        plot_frame = ttk.Frame(body)
        body.add(plot_frame, weight=4)

        log_frame = ttk.Frame(body)
        body.add(log_frame, weight=2)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.ax_ref = self.figure.add_subplot(211)
        self.ax_zoom = self.figure.add_subplot(212)

        self.ax_ref.set_title("Plantilla Reflow (fijo)")
        self.ax_ref.set_xlabel("Time (s)")
        self.ax_ref.set_ylabel("Temp (C)")
        self.ax_ref.grid(True, alpha=0.3)
        self.ref_raw_line, = self.ax_ref.plot([], [], color="#d32f2f", linewidth=1.8, label="temp_C")
        self.ref_filt_line, = self.ax_ref.plot([], [], color="#2e7d32", linewidth=1.8, label="temp_C_filtered")
        self.ax_ref.legend(loc="upper left")

        self.ax_zoom.set_title("Zoom dinamico (tiempo real)")
        self.ax_zoom.set_xlabel("Time (s)")
        self.ax_zoom.set_ylabel("Temp (C)")
        self.ax_zoom.grid(True, alpha=0.3)
        self.zoom_raw_line, = self.ax_zoom.plot([], [], color="#d32f2f", linewidth=1.8, label="temp_C")
        self.zoom_filt_line, = self.ax_zoom.plot([], [], color="#2e7d32", linewidth=1.8, label="temp_C_filtered")
        self.ax_zoom.legend(loc="upper left")

        self._draw_reflow_template()
        self.figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ttk.Label(log_frame, text="Log Window").pack(anchor="w")
        self.log_text = ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{stamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _draw_reflow_template(self) -> None:
        if not self.show_template_var.get():
            return
        zones = [
            (0, 90, "#ffcc80", "Pre-heat\n(0-90 s)"),
            (90, 180, "#ffe082", "Soaking\n(90-180 s)"),
            (180, 240, "#ef9a9a", "Reflow\n(180-240 s)"),
            (240, 300, "#90caf9", "Cooling"),
        ]
        for t0, t1, color, label in zones:
            span = self.ax_ref.axvspan(t0, t1, alpha=0.12, color=color, zorder=0)
            self.template_artists.append(span)
            if label != "Cooling":
                txt = self.ax_ref.text((t0 + t1) / 2, 8, label, ha="center", va="bottom", fontsize=8, color=color)
                self.template_artists.append(txt)

        hlines = [
            (150, "#ffe082", "150C soak start"),
            (183, "#ffb74d", "183C liquidus"),
            (217, "#ef9a9a", "217C peak min"),
            (225, "#f06292", "225C peak max"),
        ]
        for temp, color, label in hlines:
            line = self.ax_ref.axhline(temp, color=color, linewidth=0.9, linestyle="--", alpha=0.8, zorder=1)
            self.template_artists.append(line)
            txt = self.ax_ref.text(302, temp, label, va="center", ha="left", fontsize=8, color=color)
            self.template_artists.append(txt)

        for t in (90, 180, 240):
            vline = self.ax_ref.axvline(t, color="#9e9e9e", linewidth=0.8, linestyle=":", alpha=0.7, zorder=1)
            self.template_artists.append(vline)
        self.ax_ref.set_xlim(0.0, 310.0)
        self.ax_ref.set_ylim(0.0, 250.0)

    def _clear_reflow_template(self) -> None:
        for artist in self.template_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self.template_artists.clear()

    def _toggle_template(self) -> None:
        self._clear_reflow_template()
        if self.show_template_var.get():
            self._draw_reflow_template()
        self.plot_dirty = True
        self._append_log(
            "Reflow template enabled." if self.show_template_var.get() else "Reflow template disabled."
        )

    def _refresh_ports(self) -> None:
        ports = [p.device for p in list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and (self.port_var.get() not in ports):
            self.port_var.set(ports[0])
        self._append_log(f"Ports found: {ports if ports else 'none'}")

    def _connect(self) -> None:
        if self.is_connected:
            return
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("Port required", "Select a COM port first.")
            return
        try:
            baud = int(self.baud_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid baud", "Baud must be an integer.")
            return

        self.serial_stop.clear()
        self.worker = SerialWorker(
            SerialConfig(port=port, baud=baud),
            self.event_queue,
            self.serial_stop,
        )
        self.worker.start()
        self.is_connected = True
        self.connect_btn.configure(state=tk.DISABLED)
        self.disconnect_btn.configure(state=tk.NORMAL)
        self.start_btn.configure(state=tk.NORMAL)
        self.status_var.set("Status: Connected")
        self._append_log("Connection requested.")

    def _disconnect(self) -> None:
        if not self.is_connected:
            return
        if self.is_running:
            self._finish_experiment()
        self.serial_stop.set()
        self.is_connected = False
        self.connect_btn.configure(state=tk.NORMAL)
        self.disconnect_btn.configure(state=tk.DISABLED)
        self.start_btn.configure(state=tk.DISABLED)
        self.finish_btn.configure(state=tk.DISABLED)
        self.status_var.set("Status: Disconnected")
        self._append_log("Disconnect requested.")

    def _safe_experiment_name(self) -> str:
        name = self.exp_name_var.get().strip() or "perfil"
        return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)

    def _build_output_path(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        folder = self.output_dir / today
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._safe_experiment_name()}_{stamp}.csv"
        return folder / filename

    def _start_experiment(self) -> None:
        if not self.is_connected:
            messagebox.showwarning("Not connected", "Connect to serial first.")
            return
        if self.is_running:
            return
        self.current_csv_path = self._build_output_path()
        self.current_csv_file = open(self.current_csv_path, "w", newline="", encoding="utf-8")
        self.current_writer = csv.writer(self.current_csv_file)
        self.current_headers = None
        self.expecting_header = True
        self.first_t_ms = None
        self.t_data.clear()
        self.temp_data.clear()
        self.filt_data.clear()
        self._write_metadata()
        self._send_command("START")
        self.is_running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.finish_btn.configure(state=tk.NORMAL)
        self.status_var.set("Status: Running")
        self.file_var.set(f"Output: {self.current_csv_path}")
        self._append_log(f"Experiment started. CSV: {self.current_csv_path}")

    def _write_metadata(self) -> None:
        assert self.current_csv_file is not None
        meta = [
            f"# experiment={self._safe_experiment_name()}",
            f"# started_at={datetime.now().isoformat(timespec='seconds')}",
            f"# port={self.port_var.get().strip()}",
            f"# baud={self.baud_var.get().strip()}",
        ]
        for line in meta:
            self.current_csv_file.write(line + "\n")
        self.current_csv_file.flush()

    def _finish_experiment(self) -> None:
        if not self.is_running:
            return
        self._send_command("STOP")
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL if self.is_connected else tk.DISABLED)
        self.finish_btn.configure(state=tk.DISABLED)
        self.status_var.set("Status: Finished")
        if self.current_csv_file:
            self.current_csv_file.write(f"# finished_at={datetime.now().isoformat(timespec='seconds')}\n")
            self.current_csv_file.flush()
            self.current_csv_file.close()
        self.current_csv_file = None
        self.current_writer = None
        self._append_log("Experiment finished.")

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=str(self.output_dir), title="Select output folder")
        if selected:
            self.output_dir = Path(selected)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.file_var.set(f"Output: {self.output_dir}")
            self._append_log(f"Output folder set to: {self.output_dir}")

    def _send_command(self, cmd: str) -> None:
        if not self.worker:
            return
        self.worker.send_command(cmd)

    def _send_mode(self, mode: str) -> None:
        self._send_command(f"MODE {mode}")
        if self.is_running:
            self.expecting_header = True
            self.current_headers = None
            self.first_t_ms = None
            self.t_data.clear()
            self.temp_data.clear()
            self.filt_data.clear()
            self._send_command("STOP")
            time.sleep(0.05)
            self._send_command("START")
        self._append_log(f"Mode requested: {mode}")

    def _apply_rate(self) -> None:
        value = self.rate_var.get().strip()
        try:
            int(value)
        except ValueError:
            messagebox.showerror("Invalid rate", "Rate must be an integer in ms.")
            return
        self._send_command(f"RATE {value}")

    def _apply_offset(self) -> None:
        value = self.offset_var.get().strip()
        try:
            float(value)
        except ValueError:
            messagebox.showerror("Invalid offset", "Offset must be numeric.")
            return
        self._send_command(f"OFFSET {value}")

    def _apply_alpha(self) -> None:
        value = self.alpha_var.get().strip()
        try:
            v = float(value)
            if not (0.0 < v <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid alpha", "Alpha debe estar entre 0.0 y 1.0 (ej. 0.05).")
            return
        self._send_command(f"ALPHA {value}")
        self._append_log(f"Alpha EMA establecido: {value}")

    def _apply_spike(self) -> None:
        value = self.spike_var.get().strip()
        try:
            v = float(value)
            if v < 0.0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid spike", "Spike threshold debe ser >= 0 (0 = desactivado).")
            return
        self._send_command(f"SPIKE {value}")
        label = f"{value} C" if float(value) > 0 else "DESACTIVADO"
        self._append_log(f"Spike threshold: {label}")

    def _handle_line(self, line: str) -> None:
        parts = line.split(",")
        if self.expecting_header and "t_ms" in line:
            self.current_headers = [p.strip() for p in parts]
            self.expecting_header = False
            if self.current_writer:
                self.current_writer.writerow(self.current_headers)
                self.current_csv_file.flush()
            self._append_log(f"Header detected: {self.current_headers}")
            return

        if self.current_headers and len(parts) != len(self.current_headers):
            self._append_log(f"Ignored malformed line: {line}")
            return

        if len(parts) < 2:
            self._append_log(f"Ignored line: {line}")
            return

        if self.current_writer and self.is_running:
            self.current_writer.writerow(parts)
            self.current_csv_file.flush()

        try:
            raw_ms = int(parts[0])
            if self.first_t_ms is None:
                self.first_t_ms = raw_ms
            t_s = (raw_ms - self.first_t_ms) / 1000.0
            raw_temp = parts[1]
            if raw_temp != "NaN":
                value = float(raw_temp)
                self.t_data.append(t_s)
                self.temp_data.append(value)
                if len(parts) > 2 and parts[2] != "NaN":
                    self.filt_data.append(float(parts[2]))
                elif self.filt_data:
                    self.filt_data.append(self.filt_data[-1])
                self.temp_var.set(f"Temp: {value:.2f} C")
                self.time_var.set(f"Time: {t_s:.1f} s")
                self.plot_dirty = True
        except ValueError:
            self._append_log(f"Parse error: {line}")

    def _update_plot(self) -> None:
        if not self.plot_dirty or not self.t_data:
            return

        # Panel superior: perfil completo sobre plantilla (fijo)
        self.ref_raw_line.set_data(self.t_data, self.temp_data)
        if self.filt_data and len(self.filt_data) == len(self.t_data):
            self.ref_filt_line.set_data(self.t_data, self.filt_data)
        else:
            self.ref_filt_line.set_data([], [])

        if self.show_template_var.get():
            t_end = max(310.0, self.t_data[-1] + 10.0)
            self.ax_ref.set_xlim(0.0, t_end)
            self.ax_ref.set_ylim(0.0, 250.0)
        else:
            self.ax_ref.relim()
            self.ax_ref.autoscale_view()

        # Panel inferior: zoom dinamico con ventana deslizante
        t_max = self.t_data[-1]
        t_min = max(0.0, t_max - self.zoom_window_s)
        vis_idx = [i for i, t in enumerate(self.t_data) if t >= t_min]
        vis_t = [self.t_data[i] for i in vis_idx]
        vis_raw = [self.temp_data[i] for i in vis_idx]
        vis_filt = []
        if self.filt_data and len(self.filt_data) == len(self.t_data):
            vis_filt = [self.filt_data[i] for i in vis_idx]

        self.zoom_raw_line.set_data(vis_t, vis_raw)
        if vis_filt:
            self.zoom_filt_line.set_data(vis_t, vis_filt)
        else:
            self.zoom_filt_line.set_data([], [])

        self.ax_zoom.set_xlim(t_min, t_min + self.zoom_window_s)
        y_vals = vis_raw + vis_filt
        if y_vals:
            y_min = min(y_vals) - 3.0
            y_max = max(y_vals) + 3.0
            if y_max - y_min < 8.0:
                mid = (y_min + y_max) / 2.0
                y_min = mid - 4.0
                y_max = mid + 4.0
            self.ax_zoom.set_ylim(y_min, y_max)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.plot_dirty = False

    def _poll_events(self) -> None:
        while not self.event_queue.empty():
            event = self.event_queue.get_nowait()
            etype = event.get("type")
            if etype == "line":
                self._handle_line(event["line"])
            elif etype == "comment":
                self._append_log(event["line"])
            elif etype == "log":
                self._append_log(event["message"])
            elif etype == "status":
                self._append_log(event["message"])
            elif etype == "error":
                self._append_log(f"ERROR: {event['message']}")
                self.status_var.set("Status: Error")
        self._update_plot()
        self.root.after(150, self._poll_events)

    def _on_close(self) -> None:
        if self.is_running:
            self._finish_experiment()
        if self.is_connected:
            self._disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = ThermalLoggerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
