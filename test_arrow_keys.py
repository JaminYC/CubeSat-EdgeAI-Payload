"""
Script simple para depurar los códigos de las teclas de flecha
"""
import cv2
import numpy as np

print("Presiona las teclas de flecha para ver sus códigos.")
print("Presiona 'q' para salir.")
print("="*60)

# Crear ventana simple
img = np.zeros((400, 600, 3), dtype=np.uint8)
img[:] = (50, 50, 50)

cv2.putText(img, "Presiona las flechas del teclado", (50, 200),
           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

cv2.namedWindow("Test Arrow Keys")

while True:
    cv2.imshow("Test Arrow Keys", img)
    key = cv2.waitKeyEx(1)

    if key != -1:  # Si se presionó alguna tecla
        if key == ord('q'):
            print("\nSaliendo...")
            break
        else:
            print(f"Tecla presionada - Código: {key}")

            # Mostrar información adicional
            if key == 2490368:
                print("  -> Flecha ARRIBA detectada!")
            elif key == 2621440:
                print("  -> Flecha ABAJO detectada!")
            elif key == 2424832:
                print("  -> Flecha IZQUIERDA detectada!")
            elif key == 2555904:
                print("  -> Flecha DERECHA detectada!")

cv2.destroyAllWindows()
