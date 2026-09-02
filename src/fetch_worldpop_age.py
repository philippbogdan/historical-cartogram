"""L10: WorldPop 2020 age-sex structure, 1 km global, downloaded one at a time, block-summed to 5 arcmin
(factor 10), one npz per band under data/derived/worldpop_age/. 36 bands, ~3.3 GB each each, deleted after reduction.
    python src/fetch_worldpop_age.py [bands...]"""
import os, sys, time
import numpy as np, rasterio
from rasterio.windows import Window
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "derived", "worldpop_age"); os.makedirs(OUT, exist_ok=True)
AGES = [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
F = 10
def reduce(sex, age):
    name = f"global_{sex}_{age}_2020_1km"; out = os.path.join(OUT, name + f"_f{F}.npz")
    if os.path.exists(out): print("have", name); return
    url = f"https://data.worldpop.org/GIS/AgeSex_structures/Global_2000_2020/2020/0_Mosaicked/global_mosaic_1km/{name}.tif"
    tmp = os.path.join(OUT, name + ".tif"); t0 = time.time()
    if os.system(f'curl -sL -C - -o "{tmp}" "{url}"') != 0: print("download failed", name); return   # no HTTP range support: whole file, then reduce, then delete
    with rasterio.open(tmp) as src:
        T = src.transform; W, H = src.width, src.height; nd = src.nodata
        w = W - W % F; h = H - H % F; acc = np.zeros((h // F, w // F), np.float64)
        step = 2000 - 2000 % F
        for r0 in range(0, h, step):
            n = min(step, h - r0)
            a = src.read(1, window=Window(0, r0, w, n)).astype(np.float64)
            if nd is not None: a[a == nd] = 0
            a = np.nan_to_num(a); a[a < 0] = 0
            acc[r0 // F:(r0 + n) // F] += a.reshape(n // F, F, w // F, F).sum(axis=(1, 3))
        bounds = (T.c, T.f - h * (-T.e), T.c + w * T.a, T.f)
    np.savez_compressed(out, counts=acc.astype(np.float32), bounds=np.array(bounds)); os.remove(tmp)
    print(f"{name}: {acc.sum()/1e6:.1f} M people, {time.time()-t0:.0f}s", flush=True)
if __name__ == "__main__":
    want = sys.argv[1:] or [f"{s}_{a}" for a in AGES for s in ("f", "m")]
    for b in want:
        s, a = b.split("_"); reduce(s, int(a))
    print("ALLDONE")
