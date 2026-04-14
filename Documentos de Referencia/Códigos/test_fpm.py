import torch
import fpm_py as fpm
from fpm_py.utils.data_utils import image_to_tensor
import matplotlib.pyplot as plt

# Cargar una imagen de prueba
obj = image_to_tensor("path/to/test.png", to_complex=True)

# Crear 5×5 iluminaciones sintéticas
grid_size = 5
spacing = 0.2
k_range = torch.linspace(-(grid_size // 2), grid_size // 2, grid_size) * spacing
kx, ky = torch.meshgrid(k_range, k_range, indexing="ij")
k_vectors = torch.stack((kx.flatten(), ky.flatten()), dim=1)

# Simular capturas FPM
dataset = fpm.kvectors_to_image_series(
    obj=obj,
    k_vectors=k_vectors,
    pupil_radius=100,
    wavelength=550e-9,
    pixel_size=1e-6,
    magnification=10.0
)

# Reconstruir el objeto de alta resolución
reconstruction = fpm.reconstruct(dataset, output_scale_factor=4, max_iters=10)

plt.imshow(reconstruction.abs().cpu().numpy(), cmap="gray")
plt.show()
