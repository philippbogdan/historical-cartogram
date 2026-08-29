"""D1 look: population density heatmaps at the data's own resolution (no warp).

Global at 5x block-sum of the 30" raster (8640 px wide), native 30" crops of a few
regions, and a native 3" (100 m) crop where a tile is on disk. Log10 people per cell.
"""
import os, sys, numpy as np, rasterio
from rasterio.windows import Window
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "notes", "resolution")
GHS30 = os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif")
CMAP = matplotlib.colormaps["magma"]


def save(arr, path, cell_km, vmax=None, title=None):
    """arr = people per cell; draw log10 density in people per km^2 so resolutions compare."""
    dens = np.maximum(arr, 0) / (cell_km * cell_km)
    v = np.log10(dens + 1)
    vmax = vmax or np.percentile(v, 99.9)
    img = CMAP(np.clip(v / vmax, 0, 1))[..., :3]
    img[arr <= 0] = 0.0
    h, w = arr.shape
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.imshow(img, interpolation="nearest")
    if title:
        ax.text(0.01, 0.01, title, transform=ax.transAxes, color="white", fontsize=max(9, w // 300))
    fig.savefig(path, dpi=100); plt.close(fig)
    print("wrote", path, arr.shape)


def crop(src, lon0, lon1, lat0, lat1):
    T = src.transform
    c0, c1 = int((lon0 - T.c) / T.a), int((lon1 - T.c) / T.a)
    r0, r1 = int((lat1 - T.f) / T.e), int((lat0 - T.f) / T.e)
    a = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(np.float64)
    a[a < 0] = 0
    return a


REGIONS = {  # lon0, lon1, lat0, lat1
    "ganges_delta": (84, 92, 21, 27),
    "java": (105, 115, -9, -5),
    "nile": (29, 33, 26, 32),
    "pearl_yangtze": (112, 123, 21, 33),
    "london_paris": (-2, 3, 48, 52),
}

if __name__ == "__main__":
    z = np.load(os.path.join(ROOT, "data", "derived", "ghs2025_lonlat_f5.npz"))
    save(z["counts"], os.path.join(OUT, "global_30ss_x5_8640.png"), 4.6, title="GHS-POP 2025, 30 arcsec block-summed x5 (~4.6 km cells at the equator), log10 people/km2")
    with rasterio.open(GHS30) as src:
        for name, (lon0, lon1, lat0, lat1) in REGIONS.items():
            a = crop(src, lon0, lon1, lat0, lat1)
            save(a, os.path.join(OUT, f"{name}_30ss_native.png"), 0.93, vmax=4.5, title=f"{name}: native 30 arcsec (~1 km), {a.shape[1]}x{a.shape[0]} cells")
    tile = os.path.join(RAW, "ghs3ss", "GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R7_C27.tif")
    if os.path.exists(tile):
        with rasterio.open(tile) as src:
            print("3ss tile", src.width, src.height, src.bounds)
            a = crop(src, 88.0, 91.0, 22.5, 24.5)  # Dhaka and the delta
            save(a, os.path.join(OUT, "dhaka_3ss_native.png"), 0.093, vmax=5.5, title=f"Dhaka region: native 3 arcsec (~100 m), {a.shape[1]}x{a.shape[0]} cells")
        with rasterio.open(GHS30) as src:
            a = crop(src, 88.0, 91.0, 22.5, 24.5)
            save(np.kron(a, np.ones((10, 10))), os.path.join(OUT, "dhaka_30ss_upsampled.png"), 0.93, vmax=4.5, title="Dhaka region: the same box at 30 arcsec, each 1 km cell shown as 10x10")
