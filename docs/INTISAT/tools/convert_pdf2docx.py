from pdf2docx import Converter
import sys

pdf_file = "d:/INTISAT-doc/main.pdf"
docx_file = "d:/INTISAT-doc/INTISAT_Estructura.docx"

try:
    cv = Converter(pdf_file)
    cv.convert(docx_file)      # all pages by default
    cv.close()
    print("Conversión exitosa")
except Exception as e:
    print(f"Error en conversión: {e}", file=sys.stderr)
