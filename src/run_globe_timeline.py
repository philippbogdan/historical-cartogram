"""A7: the globe through time. Equal-area periodic solves for a set of HYDE epochs at `width`,
exported as globe packages (mesh.bin per epoch) plus an index with population, so the page can
scale the radius with sqrt(population). python src/run_globe_timeline.py <width> <years comma-separated>"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson, render, hyde
from run import ROOT, RAW

width = int(sys.argv[1]); years = [int(y) for y in sys.argv[2].split(",")]
H = hyde.Hyde(os.path.join(RAW, "hyde33", "population_base.nc")); ys = list(H.years)
grid = prep.Grid("equalarea", width, 90.0, lon0=-180.0)
sigma_px = 60.0 / grid.km_per_px_equator()
ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
dst_root = os.path.join(ROOT, "site", "globe", "data"); os.makedirs(dst_root, exist_ok=True)
index = []
step = max(1, width // 512)
for y in years:
    name = f"globe_{y:+06d}"; dst = os.path.join(dst_root, name); os.makedirs(dst, exist_ok=True)
    if os.path.exists(os.path.join(dst, "mesh.bin")):
        index.append(json.load(open(os.path.join(dst, "meta.json")))); print("skip", name); continue
    t0 = time.time(); counts = H.counts(ys.index(y)); total = float(counts.sum())
    P, _ = prep.to_grid(counts, H.bounds, grid)
    po, _ = ot_poisson.spectral_homotopy(P, [0.95, 0.999], sigma_px, "periodic", iters=400, damping=0.5, log=lambda s: None, ocean=ocean, ocean_share=0.05)
    X, Y = po.mesh(); m = diffusion.equalisation_metrics(po.rho0, X, Y)
    Hh, W = grid.H, grid.W
    rows = np.arange(0, Hh + 1, step); cols = np.arange(0, W + 1, step)
    if rows[-1] != Hh: rows = np.append(rows, Hh)
    if cols[-1] != W: cols = np.append(cols, W)
    R, C = np.meshgrid(rows, cols, indexing="ij")
    lon_o, lat_o = grid.lonlat(C.astype(np.float64), R.astype(np.float64))
    lon_w, lat_w = grid.lonlat(X[R, C] % W, np.clip(Y[R, C], 0, Hh)); lon_w[:, -1] = lon_w[:, 0]; lat_w[:, -1] = lat_w[:, 0]
    np.stack([lon_o, lat_o, lon_w, lat_w], axis=-1).astype(np.float32).tofile(os.path.join(dst, "mesh.bin"))
    meta = {"rows": int(len(rows)), "cols": int(len(cols)), "experiment": name, "year": y, "population": total, "textures": [], "error_p05": m["log_ratio_popweighted_p05"], "error_p95": m["log_ratio_popweighted_p95"],
            "honesty": "modelled (HYDE)" if y < 1950 else "census-based (HYDE)"}
    json.dump(meta, open(os.path.join(dst, "meta.json"), "w"), indent=1); index.append(meta)
    print(f"{name}: pop {total/1e6:.1f} M  p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f}  {time.time()-t0:.0f}s", flush=True)
json.dump(sorted(index, key=lambda d: d["year"]), open(os.path.join(dst_root, "timeline.json"), "w"), indent=1)
print("done", len(index))
