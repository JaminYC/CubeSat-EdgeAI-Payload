import os
from PIL import Image
import torch
from RealESRGAN import RealESRGAN

# ====== DISPOSITIVO ======
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("Usando dispositivo:", device)

# ====== RUTAS ======
ruta_imagen = os.path.join('Imagenes', 'Prueba.jpg')
carpeta_salida = 'Resultados'
os.makedirs(carpeta_salida, exist_ok=True)
ruta_salida = os.path.join(carpeta_salida, 'Prueba_x4.png')

ruta_pesos = os.path.join('Modelo', 'RealESRGAN_x4.pth')

# ====== MODELO (ai-forever / Sberbank) ======
print("Cargando modelo desde:", ruta_pesos)
model = RealESRGAN(device, scale=4)
model.load_weights(ruta_pesos)  # usamos TU .pth, sin descargar nada

# ====== IMAGEN ======
print("Cargando imagen:", ruta_imagen)
img = Image.open(ruta_imagen).convert('RGB')

# ====== PROCESAR ======
print("Procesando imagen (x4)...")
sr_img = model.predict(img)

# ====== GUARDAR ======
sr_img.save(ruta_salida)
print("Imagen guardada en:", ruta_salida)
