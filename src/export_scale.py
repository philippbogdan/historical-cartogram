"""L5: the humeter ruler for the flat viewer: km of ground per mesh pixel at every point of the
cartogram frame (from the inverse map), as a small JSON grid. python src/export_scale.py <experiment>"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep
from run import ROOT
exp = sys.argv[1]; out = os.path.join(ROOT, "experiments", exp)
z = np.load(os.path.join(out, "inverse.npz")); IX, IY = z["IX"].astype(np.float64), z["IY"].astype(np.float64)
p = json.load(open(os.path.join(out, "params.json"))); grid = prep.Grid(p["grid"], p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
n = 128; step = IX.shape[0] // n
ix = IX[step // 2::step, step // 2::step][:n, :n]; iy = IY[step // 2::step, step // 2::step][:n, :n]
gx = np.gradient(ix, axis=1) / step; gy = np.gradient(iy, axis=0) / step  # source px per output px
lon, lat = grid.lonlat(ix, iy)
km = np.hypot(gx, gy) / np.sqrt(2) * grid.km_per_px_equator() * np.cos(np.radians(lat))  # km of ground per output mesh px
json.dump({"n": n, "W": grid.W, "km_per_px": np.round(km, 2).tolist(), "people_per_px": float(8.19e9 / (grid.W * grid.H))}, open(os.path.join(ROOT, "site", "flat", "scale.json"), "w"))
print("scale grid written; median km per mesh px on the frame:", float(np.median(km)))
