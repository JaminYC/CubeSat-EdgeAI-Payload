import pypandoc

tex_file = "d:/INTISAT-doc/main.tex"
docx_file = "d:/INTISAT-doc/INTISAT_Nativo_Final.docx"

try:
    print("Generando DOCX con Indice y Numeración...")
    # Agregamos --toc (Table of Contents) y --number-sections (Enumeracion automatica)
    pypandoc.convert_file(tex_file, 'docx', outputfile=docx_file, extra_args=['--toc', '--number-sections'])
    print("Conversión completada con éxito.")
except Exception as e:
    print(f"Error: {e}")
