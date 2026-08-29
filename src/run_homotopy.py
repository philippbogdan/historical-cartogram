"""Spectral homotopy at one resolution, every stage saved as its own experiment (metrics + renders).
    python src/run_homotopy.py <prefix> <width> <sigma_km> <shares comma-separated> [iters]"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson
from run import get_lonlat, NCOLS, ROOT, render_all

prefix, width, sigma_km, shares = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), [float(x) for x in sys.argv[4].split(",")]
iters = int(sys.argv[5]) if len(sys.argv) > 5 else 400
ocean_share = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
lon0 = float(sys.argv[7]) if len(sys.argv) > 7 else -128.0
grid = prep.Grid("mercator", width)
factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * width)))
counts, bounds = get_lonlat(factor)
P, _ = prep.to_grid(counts, bounds, grid)
sigma_px = sigma_km / grid.km_per_px_equator()
from hc import render
from run import RAW
ocean = None
if ocean_share > 0:
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
t0 = time.time()

def on_stage(share, po):
    name = f"{prefix}_share{share}" + (f"_ocean{ocean_share}" if ocean_share else "")
    out = os.path.join(ROOT, "experiments", name)
    os.makedirs(out, exist_ok=True)
    X, Y = po.mesh()
    m = diffusion.equalisation_metrics(po.rho0, X, Y)
    r, f = po.residual()
    m.update({"residual": r, "cell_folds": f, "mode": "spectral_homotopy", "seconds": time.time() - t0})
    params = {"name": name, "method": "ot_spectral_homotopy", "grid": "mercator", "lat_cut": grid.lat_cut, "width": width, "W": grid.W, "H": grid.H,
              "x_boundary": "periodic", "backend": "torch-spectral", "floor": (1 - share) / share, "share": share, "ocean_share": ocean_share, "lon0": lon0, "sigma_km": sigma_km, "sigma_px": sigma_px, "vectors": "50m", "iters": iters}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1)
    json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    psi = po.psi_from_S(po.S).cpu().numpy().astype(np.float32)
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=po.rho0.astype(np.float32), psi=psi)
    open(os.path.join(out, "log.txt"), "w").write(f"spectral homotopy stage share {share}: residual {r:.4f} folds {f}\n")
    render_all(out, grid, X, Y, po.rho0, params, log=print)
    print(f"stage {share}: p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f} aniso {m['anisotropy_popweighted_p50']:.2f} folds {m['folds']} residual {r:.4f}", flush=True)

po, stages = ot_poisson.spectral_homotopy(P, shares, sigma_px, "periodic", iters=iters, damping=0.5, log=lambda s: None, on_stage=on_stage, ocean=ocean, ocean_share=ocean_share)
print("done", f"{time.time()-t0:.0f}s")
