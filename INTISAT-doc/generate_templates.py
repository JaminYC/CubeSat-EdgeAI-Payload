import os
import re

base_path = r"D:\INTISAT-doc"
template_file = os.path.join(base_path, "report_template.tex")

with open(template_file, 'r', encoding='utf-8') as f:
    template_content = f.read()

systems = [
    {
        "filename": "plantilla_obc.tex",
        "doccode": "INTI-OBC-2025",
        "doctitle": "Computadora de a Bordo (OBC)",
        "docsubtitle": "Reporte de Diseño del Subsistema de Manejo de Datos",
        "intro_text": r"El hardware principal o módulo On-Board Data Handling (OBDH) es el \textit{corazón} de la plataforma, concebido de manera específica para aplicaciones enfocadas de nanosatélites. Este procesador central sincroniza todo el flujo de trabajo operacional, los diagnósticos y las cadenas de comunicación del satélite tanto con el segmento espacial como con la estación terrena en la Tierra."
    },
    {
        "filename": "plantilla_eps.tex",
        "doccode": "INTI-EPS-2025",
        "doctitle": "Sistema de Energía (EPS)",
        "docsubtitle": "Reporte de Diseño del Subsistema de Potencia",
        "intro_text": r"El subsistema de control de Electricidad Térmica y Potencia (EPS, Electrical Power System) es el encargado primario de tres misiones en órbita LEO: recolección energética celular, protección temporal/almacenamiento mediante celdas de batería y, por último, acondicionamiento y distribución segura a todo el bus de carga."
    },
    {
        "filename": "plantilla_uhf.tex",
        "doccode": "INTI-TTC-2025",
        "doctitle": "Telecomunicaciones UHF y TTC",
        "docsubtitle": "Reporte de Diseño del Enlace y Rastreo",
        "intro_text": r"El subsistema TTC (Telemetry, Tracking and Command) establece el enlace fundamental de comunicación entre la Tierra (estación terrena) y el nanosatélite. Sus funciones primarias se dividen típicamente en sub-módulos: un emisor periódico tipo Beacon (baliza) y el transceptor de Subida/Bajada (Uplink/Downlink) modulados típicamente en GMSK."
    },
    {
        "filename": "plantilla_payload_ia.tex",
        "doccode": "INTI-SAI-2025",
        "doctitle": "Carga Útil: Inteligencia Artificial (SAI)",
        "docsubtitle": "Aceleración y Súper Resolución en Órbita",
        "intro_text": r"El sub-bloque de la estructura o acelerador de red neuronal (Hardware de A.I.) tiene la meta principal de analizar topografías moleculares e inducir resoluciones matemáticas superiores sin generar pesos extra al ancho de banda clásico. La implementación es un requerimiento ineludible en el bus del espacio profundo debido al alto nivel fotográfico que las telecomunicaciones UHF no pueden cubrir directamente."
    },
    {
        "filename": "plantilla_payload_cmos.tex",
        "doccode": "INTI-CMOS-2025",
        "doctitle": "Carga Útil: Microscopía CMOS",
        "docsubtitle": "Biometría y Microscopía Computacional",
        "intro_text": r"El sistema de microscopía se organiza en cuatro bloques funcionales: adquisición óptica, iluminación, control/procesamiento y almacenamiento. Está compuesto por un sensor CMOS comercial operando en configuración de microscopía sin lentes (\textit{lensless/contact}), siendo la computadora de carga útil (como Raspberry Pi 5) la que coordina la captura y el control de la iluminación."
    },
    {
        "filename": "plantilla_estructura.tex",
        "doccode": "INTI-STR-2025",
        "doctitle": "Estructura y Mecánica",
        "docsubtitle": "Diseño Estructural General",
        "intro_text": r"La chapa y fuselaje comprenden el contenedor maestro modular (esquema PC-104 acoplado estibado típico del estándar internacional CubeSat). Sus finalidades son la resistencia a los estragos mecánicos que implican abandonar nuestro planeta, y facilitar guías rígidas precisas o rieles permitiendo la inyección a alta velocidad al vacio."
    },
    {
        "filename": "plantilla_adcs.tex",
        "doccode": "INTI-ADCS-2025",
        "doctitle": "Control de Actitud (ADCS)",
        "docsubtitle": "Determinación y Maniobra LEO",
        "intro_text": r"El módulo de control de actitud (ADCS) tiene como fin estabilizar giros remanentes (detumbling) arrastrados post-separación del vehículo lanzador/eyector e inyectar un referencial espacial orientado en el micro/nanosatélite que mantenga estabilidad inercial respecto a líneas terrestres (empleando estandarización pasiva mediante barras de histéresis y magnetos de tierras raras)."
    }
]

for sys in systems:
    content = template_content
    # Reemplazos de encabezados
    content = re.sub(r"\\newcommand\{\\doccode\}\{.*?\}", rf"\\newcommand{{\\doccode}}{{{sys['doccode']}}}", content)
    content = re.sub(r"\\newcommand\{\\doctitle\}\{.*?\}", rf"\\newcommand{{\\doctitle}}{{{sys['doctitle']}}}", content)
    content = re.sub(r"\\newcommand\{\\docsubtitle\}\{.*?\}", rf"\\newcommand{{\\docsubtitle}}{{{sys['docsubtitle']}}}", content)

    # Insertar el texto en la introducción
    intro_pattern = r"\\chapter\{Introduccion\}\nContenido inicial aqui\."
    content = re.sub(intro_pattern, rf"\\chapter{{Introduccion}}\n{sys['intro_text']}", content)

    # Reemplazar imagenes placeholder por las del repositorio directamente al path real si fue necesario, 
    # en este caso "Images/..." ya asume la raiz del repo, pero podriamos hacer ../Images o lo que corresponda
    # Si estas plantillas van a estar en la raiz D:\INTISAT-doc, la ruta "Images/..." funcionará.

    filepath = os.path.join(base_path, sys['filename'])
    with open(filepath, 'w', encoding='utf-8') as fw:
        fw.write(content)

print(f"Creadas {len(systems)} plantillas individualizadas en D:\\INTISAT-doc\\")
