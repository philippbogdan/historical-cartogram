"""T1: every HYDE epoch through the same solver and renders, one experiment per epoch.
    python src/run_timeline.py <width> [sigma_km] [ocean_share] [epoch selection: all | every:N | list of years]"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson, render, hyde
from run import ROOT, RAW, render_all

width = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
sigma_km = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
ocean_share = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
sel = sys.argv[4] if len(sys.argv) > 4 else "all"
scenario = sys.argv[5] if len(sys.argv) > 5 else "base"
lon0, xb = -168.0, "wall"

H = hyde.Hyde(os.path.join(RAW, "hyde33", f"population_{scenario}.nc"))
years = list(H.years)
if sel.startswith("every:"):
    idx = list(range(0, len(years), int(sel.split(":")[1])))
    if idx[-1] != len(years) - 1: idx.append(len(years) - 1)
elif sel == "all":
    idx = list(range(len(years)))
else:
    want = [int(y) for y in sel.split(",")]; idx = [years.index(y) for y in want]
grid = prep.Grid("mercator", width, lon0=lon0)
sigma_px = sigma_km / grid.km_per_px_equator()
ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
mask_v = "50m"
out_root = os.path.join(ROOT, "experiments", "timeline")
os.makedirs(out_root, exist_ok=True)
index = []
for i in idx:
    y = years[i]
    name = f"t_{scenario}_{y:+06d}"
    out = os.path.join(out_root, name)
    if os.path.exists(os.path.join(out, "metrics.json")):
        index.append(name); print("skip", name); continue
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    counts = H.counts(i)
    total = counts.sum()
    P, dropped = prep.to_grid(counts, H.bounds, grid)
    po, stages = ot_poisson.spectral_homotopy(P, [0.95, 0.999], sigma_px, xb, iters=400, damping=0.5, log=lambda s: None, ocean=ocean, ocean_share=ocean_share)
    X, Y = po.mesh()
    m = diffusion.equalisation_metrics(po.rho0, X, Y)
    r, f = po.residual()
    m.update({"residual": r, "cell_folds": f, "year": int(y), "population": float(total), "people_per_px": float(total / (grid.W * grid.H)), "seconds": time.time() - t0})
    params = {"name": name, "method": "ot_spectral_homotopy", "grid": "mercator", "lat_cut": grid.lat_cut, "lon0": lon0, "width": width, "W": grid.W, "H": grid.H,
              "x_boundary": xb, "floor": 0.001001, "share": 0.999, "ocean_share": ocean_share, "sigma_km": sigma_km, "sigma_px": sigma_px, "vectors": mask_v,
              "source": f"HYDE 3.3 {scenario} population.nc", "year": int(y), "honesty": "modelled (HYDE allocation of regional estimates)" if y < 1950 else "census-based (HYDE, national statistics)"}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1)
    json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    psi = po.psi_from_S(po.S).cpu().numpy().astype(np.float32)
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=po.rho0.astype(np.float32), psi=psi, counts=P.astype(np.float32))
    open(os.path.join(out, "log.txt"), "w").write(f"year {y} population {total/1e6:.2f} M; residual {r:.4f}; {time.time()-t0:.0f}s\n")
    render_all(out, grid, X, Y, po.rho0, params, log=lambda s: None)
    index.append(name)
    print(f"{name}: pop {total/1e6:9.1f} M  p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f}  folds {m['folds']}  {time.time()-t0:.0f}s", flush=True)
json.dump({"scenario": scenario, "width": width, "frames": index}, open(os.path.join(out_root, f"index_{scenario}_{width}.json"), "w"), indent=1)
print("done", len(index), "frames")
