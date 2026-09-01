"""A4: export a globe package from an EQUAL-AREA, periodic experiment.
    python src/export_globe.py <experiment> [vertex step] -> site/globe/data/<experiment>/
Mesh: for a lattice of source points, the warped lon/lat (where the point lands) and the original
lon/lat; the page places each vertex at the warped position on the sphere and pins the texture UV to
the original, so any equirectangular texture rides the warp. Textures: countries, population,
night lights (if on disk), all 4096 x 2048 plate carree."""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from run import ROOT, RAW
from render_countries import country_ids, palette
import rasterio
from rasterio.enums import Resampling

name = sys.argv[1]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 4
out = os.path.join(ROOT, "experiments", name)
p = json.load(open(os.path.join(out, "params.json")))
assert p.get("grid") == "equalarea" and p.get("x_boundary") == "periodic", "the globe needs an equal-area periodic warp"
z = np.load(os.path.join(out, "mesh.npz"))
X, Y = z["X"].astype(np.float64), z["Y"].astype(np.float64)
grid = prep.Grid("equalarea", p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
H, W = grid.H, grid.W
dst = os.path.join(ROOT, "site", "globe", "data", name)
os.makedirs(dst, exist_ok=True)
# vertices on the corner lattice, every `step`
rows = np.arange(0, H + 1, step); cols = np.arange(0, W + 1, step)
if rows[-1] != H: rows = np.append(rows, H)
if cols[-1] != W: cols = np.append(cols, W)
R, C = np.meshgrid(rows, cols, indexing="ij")
lon_o, lat_o = grid.lonlat(C.astype(np.float64), R.astype(np.float64))
lon_w, lat_w = grid.lonlat(X[R, C] % W, np.clip(Y[R, C], 0, H))
# the seam column must coincide with its origin copy
lon_w[:, -1] = lon_w[:, 0]; lat_w[:, -1] = lat_w[:, 0]
arr = np.stack([lon_o, lat_o, lon_w, lat_w], axis=-1).astype(np.float32)
arr.tofile(os.path.join(dst, "mesh.bin"))
# textures (plate carree 4096 x 2048)
tg = prep.Grid("platecarree", 4096, 90.0)
ids, names, pops = country_ids(tg, "50m")
cols_rgb = (palette(len(names) + 1) * 255).astype(np.uint8); cols_rgb[0] = (168, 196, 216)
Image.fromarray(cols_rgb[ids]).save(os.path.join(dst, "countries.png"))
with rasterio.open(os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif")) as src:
    a = src.read(1, out_shape=(2048, 4096), resampling=Resampling.average).astype(np.float64); a[a < 0] = 0
    T = src.transform; cell_km = T.a * (src.width / 4096) * 111.32
    lat = np.radians(T.f + (np.arange(2048) + 0.5) * T.e * (src.height / 2048))
    dens = a / ((cell_km ** 2) * np.maximum(np.cos(lat), 0.02))[:, None]
import matplotlib
v = np.clip(np.log10(dens + 1) / 4.5, 0, 1)
rgb = (matplotlib.colormaps["magma"](v)[..., :3] * 255).astype(np.uint8); rgb[a <= 0] = 0
Image.fromarray(rgb).save(os.path.join(dst, "population.png"))
bm = os.path.join(RAW, "lenses", "BlackMarble_2016_3km_geo.tif")
if os.path.exists(bm) and os.path.getsize(bm) > 1e6:
    with rasterio.open(bm) as src:
        b = src.read(out_shape=(src.count, 2048, 4096), resampling=Resampling.average)
    img = np.moveaxis(b[:3], 0, -1).astype(np.uint8) if b.shape[0] >= 3 else np.repeat(b[0][..., None], 3, -1).astype(np.uint8)
    Image.fromarray(img).save(os.path.join(dst, "lights.png"))
# cities: warped positions of the largest places
from hc import layers
places = layers.cities(os.path.join(RAW, "ne_10m_populated_places_simple.geojson"), grid, n=300)
pts = np.array([[pl[1], pl[2]] for pl in places]); wp = render.warp_points(pts, X, Y, W)
lonc, latc = grid.lonlat(wp[:, 0] % W, np.clip(wp[:, 1], 0, H))
json.dump([{"name": pl[0], "pop": pl[3], "lon": float(lo), "lat": float(la), "lon0": float(grid.lonlat(pl[1], pl[2])[0]), "lat0": float(grid.lonlat(pl[1], pl[2])[1])} for pl, lo, la in zip(places, lonc, latc)],
          open(os.path.join(dst, "cities.json"), "w"))
json.dump({"rows": int(len(rows)), "cols": int(len(cols)), "experiment": name, "textures": [f for f in ("countries.png", "population.png", "lights.png") if os.path.exists(os.path.join(dst, f))],
           "population": 8.19e9, "share": p.get("share"), "ocean_share": p.get("ocean_share")}, open(os.path.join(dst, "meta.json"), "w"), indent=1)
print("wrote", dst, "mesh", arr.shape, "textures", os.listdir(dst))
