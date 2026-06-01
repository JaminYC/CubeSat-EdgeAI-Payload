import win32com.client
import os
import sys

pdf_path = os.path.abspath(r"d:\INTISAT-doc\main.pdf")
docx_path = os.path.abspath(r"d:\INTISAT-doc\INTISAT_Diseno_Exacto.docx")

try:
    print("Iniciando conversión nativa con Microsoft Word (Ignorando alertas)...")
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0  # Desactiva el popup "Se va a convertir el archivo..."
    
    # Abrimos el PDF directamente, Word lo reconvierte manteniendo Headers, Footers y Portada
    doc = word.Documents.Open(FileName=pdf_path, ConfirmConversions=False)
    doc.SaveAs(FileName=docx_path, FileFormat=16)
    doc.Close()
    word.Quit()
    print("Conversión completada con éxito.")
except Exception as e:
    print(f"Error usando Word: {e}")
    try:
        word.Quit()
    except:
        pass
