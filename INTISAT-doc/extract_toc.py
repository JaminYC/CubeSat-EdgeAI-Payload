import sys

pdf_path = r"d:\Trabajo Jamin\Documentos FLORIPASAT\floripasat-repos\floripasat2-doc\slb-fsat2-doc-v0.3.pdf"

try:
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    for level, title, page in toc:
        print(f"{'  ' * (level - 1)}- {title} (Page {page})")
except ImportError:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        
        def iter_bookmarks(bookmarks, level=0):
            for item in bookmarks:
                if isinstance(item, list):
                    iter_bookmarks(item, level + 1)
                else:
                    try:
                        title = item.title
                        print(f"{'  ' * level}- {title}")
                    except Exception as e:
                        pass
        iter_bookmarks(reader.outline)
    except ImportError:
        print("Neither fitz nor PyPDF2 installed.")
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
