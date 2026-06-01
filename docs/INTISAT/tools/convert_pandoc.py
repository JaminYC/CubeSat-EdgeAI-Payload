import pypandoc

tex_file = "d:/INTISAT-doc/main.tex"
docx_file = "d:/INTISAT-doc/INTISAT_Nativo.docx"

try:
    print("Iniciando coversión nativa con Pandoc...")
    pypandoc.convert_file(tex_file, 'docx', outputfile=docx_file)
    print("Conversión exitosa")
except Exception as e:
    print(f"Error pandoc: {e}")
