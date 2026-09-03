"""L12: the non-human world. Area = trees, area = cropland, from the Copernicus 100 m cover fractions
(fraction x cell area = km2 of trees or crops per cell), solved like the population world and drawn in the hero
language.   python src/lenses_landcover.py <tree|crops> [width=2048]"""
import json, os, sys, time
import numpy as np, rasterio
from rasterio.windows import Window
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from run import ROOT, RAW, DER
from lenses import _solve
from warp_vectors import frame_mesh
from render_hero import draw_hero

what = sys.argv[1]; width = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
name = {"tree": "Tree", "crops": "Crops"}[what]
path = os.path.join(RAW, "landcover", f"PROBAV_LC100_global_v3.0.1_2019-nrt_{name}-CoverFraction-layer_EPSG-4326.tif")
cache = os.path.join(DER, f"landcover_{what}_km2_f100.npz"); F = 100
if os.path.exists(cache):
    z = np.load(cache); area, bounds = z["counts"], tuple(z["bounds"])
else:
    t0 = time.time()
    with rasterio.open(path) as src:
        T = src.transform; W, H = src.width, src.height; nd = src.nodata
        w = W - W % F; h = H - H % F; acc = np.zeros((h // F, w // F), np.float64); step = 2000
        for r0 in range(0, h, step):
            n = min(step, h - r0); a = src.read(1, window=Window(0, r0, w, n)).astype(np.float64)
            if nd is not None: a[a == nd] = 0
            a[(a < 0) | (a > 100)] = 0                                          # percent cover; 255 marks no data
            acc[r0 // F:(r0 + n) // F] += a.reshape(n // F, F, w // F, F).sum(axis=(1, 3)) / 100.0 / (F * F)   # mean fraction per 5' cell
        bounds = (T.c, T.f - h * (-T.e), T.c + w * T.a, T.f)
    # fraction -> km2: cell area at that latitude
    lat_edges = np.linspace(bounds[3], bounds[1], acc.shape[0] + 1); latc = np.radians(0.5 * (lat_edges[:-1] + lat_edges[1:]))
    dlon = (bounds[2] - bounds[0]) / acc.shape[1]; dlat = (bounds[3] - bounds[1]) / acc.shape[0]
    cell_km2 = (111.32 * dlat) * (111.32 * dlon * np.cos(latc))
    area = acc * cell_km2[:, None]
    np.savez_compressed(cache, counts=area.astype(np.float32), bounds=np.array(bounds)); print(f"reduced {what} in {time.time()-t0:.0f}s")
total = float(area.sum()); print(f"{what}: {total/1e6:.2f} million km2")
grid = prep.Grid("mercator", width, lon0=-168.0); P, _ = prep.to_grid(area.astype(np.float64), bounds, grid)
exp = f"L12_{what}_{width}_o20"
if not os.path.exists(os.path.join(ROOT, "experiments", exp, "metrics.json")):
    _solve(exp, P, grid, 60.0, 0.2, {"source": f"Copernicus Global Land Cover 100 m 2019, {name} cover fraction (CC BY 4.0)", "honesty": "satellite classification, 2019", "measure": f"km2 of {what}", "population": total})
g, X, Y, p = frame_mesh(exp); p["population"] = total
title = "THE WORLD, AREA = TREES" if what == "tree" else "THE WORLD, AREA = CROPLAND"
unit = 1e6 if what == "tree" else 5e5
draw_hero(X, Y, p, os.path.join(ROOT, "experiments", exp, "hero.png"), 4096, title=title, legend_text=f"km² of {'trees' if what == 'tree' else 'cropland'}", legend_unit=unit,
          subtitle=(f"Every part of the picture holds as much tree cover as its area says; the frame is {total/1e6:.1f} million km² of trees. The people's world turned inside out: Russia, Canada, Brazil and the Congo grow; India shrinks."
                    if what == "tree" else f"Every part of the picture holds as much cropland as its area says; the frame is {total/1e6:.1f} million km² of crops. The plains that feed the world: India, the US Midwest, the Black Earth, the North China Plain."),
          source=f"Optimal transport of the Copernicus 100 m {name.lower()} cover fraction (2019, CC BY 4.0), land pure, ocean 20% of the frame. Colours follow UN subregions.")
print("done", exp)
