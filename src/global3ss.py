"""Global heatmap from the 100 m raster, block-averaged by `factor` (default 25 -> 17280 px wide).
Streams through GDAL's decimated read, so memory is the output only. Writes PNG via PIL."""
import os, sys, numpy as np, rasterio
from rasterio.enums import Resampling
from PIL import Image
import matplotlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "raw", "GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif")
factor = int(sys.argv[2]) if len(sys.argv) > 2 else 25
with rasterio.open(path) as src:
    W, H = src.width // factor, src.height // factor
    print("source", src.width, src.height, "overviews", src.overviews(1)[:5], "->", W, H, flush=True)
    a = src.read(1, out_shape=(H, W), resampling=Resampling.average).astype(np.float64)
    T = src.transform
a[a < 0] = 0
a *= factor * factor  # average -> sum: people per output cell
cell_km = T.a * factor * 111.32
lat = np.radians(T.f + (np.arange(H) + 0.5) * T.e * factor)
area = (cell_km ** 2) * np.maximum(np.cos(lat), 0.02)[:, None]
v = np.log10(a / area + 1)
vmax = np.percentile(v[a > 0], 99.9)
rgb = (matplotlib.colormaps["magma"](np.clip(v / vmax, 0, 1))[..., :3] * 255).astype(np.uint8)
rgb[a <= 0] = 0
out = os.path.join(ROOT, "notes", "resolution", f"global_3ss_x{factor}_{W}.png")
Image.fromarray(rgb).save(out, optimize=False, compress_level=6)
print("wrote", out, rgb.shape, f"total {a.sum()/1e9:.3f} bn", flush=True)
