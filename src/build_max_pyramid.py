"""Max pyramid of the 1 km density (people per km^2) for the settlement view at any footprint:
level k holds the max over 2^k x 2^k km blocks. Levels 2 km .. 1024 km, float16, one npz."""
import os, sys, numpy as np, rasterio
from rasterio.windows import Window
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = rasterio.open(os.path.join(ROOT, "data", "raw", "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif"))
T = src.transform; W, H = src.width, src.height
cell_km = T.a * 111.32
rows = np.arange(H); lat = T.f + (rows + 0.5) * T.e
area = (cell_km ** 2) * np.maximum(np.cos(np.radians(lat)), 0.02)   # km^2 per cell by row
# level 1 (2 km) directly from row chunks; then repeated 2x2 max
H2, W2 = H // 2, W // 2
lvl = np.zeros((H2, W2), np.float32)
for r0 in range(0, H2 * 2, 2000):
    n = min(2000, H2 * 2 - r0)
    a = src.read(1, window=Window(0, r0, W2 * 2, n)).astype(np.float32); a[a < 0] = 0
    d = a / area[r0:r0 + n, None].astype(np.float32)
    lvl[r0 // 2:(r0 + n) // 2] = d.reshape(n // 2, 2, W2, 2).max(axis=(1, 3))
levels = {"L1": lvl.astype(np.float16)}
for k in range(2, 11):
    h, w = lvl.shape[0] // 2, lvl.shape[1] // 2
    lvl = lvl[:h * 2, :w * 2].reshape(h, 2, w, 2).max(axis=(1, 3))
    levels[f"L{k}"] = lvl.astype(np.float16)
meta = {"left": T.c, "top": T.f, "cell_deg": T.a}
out = os.path.join(ROOT, "data", "derived", "ghs30ss_maxpyr.npz")
np.savez(out, **levels, meta=np.array([T.c, T.f, T.a]))
print("wrote", out, {k: v.shape for k, v in levels.items()})
