import win32com.client
import os

pdf_path = os.path.abspath(r"d:\INTISAT-doc\main.pdf")
docx_path = os.path.abspath(r"d:\INTISAT-doc\INTISAT_Documento_Completo.docx")

try:
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(pdf_path)
    doc.SaveAs(docx_path, FileFormat=16) # 16 is wdFormatDocumentDefault or docx
    doc.Close()
    word.Quit()
    print("Conversion successful!")
except Exception as e:
    print(f"Error: {e}")
