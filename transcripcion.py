import tkinter as tk
from tkinter import filedialog, messagebox
import whisper
import subprocess
import os
from threading import Thread

# Crear ventana
ventana = tk.Tk()
ventana.title("Transcriptor con Whisper")
ventana.geometry("700x500")

# Modelo de Whisper
modelo = whisper.load_model("base")

# Widgets
label_estado = tk.Label(ventana, text="Selecciona un archivo para transcribir", fg="blue")
label_estado.pack(pady=5)

btn_seleccionar = tk.Button(ventana, text="📂 Subir audio o video", font=("Arial", 12, "bold"))
btn_seleccionar.pack(pady=10)

text_resultado = tk.Text(ventana, wrap="word", height=20)
text_resultado.pack(padx=10, pady=10, fill="both", expand=True)

btn_guardar = tk.Button(ventana, text="💾 Guardar transcripción", state="disabled", font=("Arial", 10))
btn_guardar.pack(pady=5)

# Función para guardar transcripción
def guardar_transcripcion():
    texto = text_resultado.get("1.0", tk.END).strip()
    if texto:
        archivo = filedialog.asksaveasfilename(defaultextension=".txt",
                                                filetypes=[("Archivo de texto", "*.txt")])
        if archivo:
            with open(archivo, "w", encoding="utf-8") as f:
                f.write(texto)
            messagebox.showinfo("Guardado", f"Transcripción guardada en:\n{archivo}")

# Función de transcripción en hilo separado
def transcribir_en_hilo(ruta):
    def proceso():
        try:
            label_estado.config(text="🎙️ Extrayendo audio...", fg="orange")
            ventana.update()

            temp_audio = "temp_audio.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", ruta,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", temp_audio
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            label_estado.config(text="🧠 Transcribiendo con Whisper...", fg="orange")
            ventana.update()

            resultado = modelo.transcribe(temp_audio)
            os.remove(temp_audio)

            text_resultado.delete("1.0", tk.END)
            text_resultado.insert(tk.END, resultado["text"])

            label_estado.config(text="✅ Transcripción completada.", fg="green")
            btn_guardar.config(state="normal")
        except Exception as e:
            label_estado.config(text="❌ Error durante la transcripción", fg="red")
            messagebox.showerror("Error", str(e))
    Thread(target=proceso).start()

# Función al presionar botón
def seleccionar_archivo():
    ruta = filedialog.askopenfilename(
        title="Seleccionar archivo de audio o video",
        filetypes=[("Todos los archivos soportados", 
            "*.mp3 *.wav *.aac *.m4a *.flac *.ogg *.mp4 *.mkv *.avi *.mov *.webm *.wmv *.3gp *.ts *.flv *.mpeg *.mpg")]

    )
    if ruta:
        btn_guardar.config(state="disabled")
        text_resultado.delete("1.0", tk.END)
        transcribir_en_hilo(ruta)

btn_seleccionar.config(command=seleccionar_archivo)
btn_guardar.config(command=guardar_transcripcion)

# Ejecutar GUI
ventana.mainloop()
