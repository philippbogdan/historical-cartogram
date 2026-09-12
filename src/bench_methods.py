"""Matched benchmark: one prepared density, several methods, the same metrics.
    python src/bench_methods.py <tag> <width> <sigma_km> <share> <ocean_share> <method> [k=v ...]
methods: ot (spectral homotopy to <share>), diffusion (Gastner-Newman), gsm (flow-based 2018)
k=v: tol, max_disp, cap_frac, growth (diffusion); iters, damping (ot)"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson, flow, render, layers
from run import get_lonlat, NCOLS, ROOT, RAW

tag, width, sigma_km, share, ocean_share, method = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
kv = {a.split("=")[0]: float(a.split("=")[1]) for a in sys.argv[7:]}
out = os.path.join(ROOT, "experiments", "bench", tag); os.makedirs(out, exist_ok=True)
log_f = open(os.path.join(out, "log.txt"), "w")
def log(s):
    print(s, flush=True); log_f.write(s + "\n"); log_f.flush()
grid = prep.Grid("mercator", width, lon0=-168.0)
factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * width)))
counts, bounds = get_lonlat(factor)
P, _ = prep.to_grid(counts, bounds, grid)
sigma_px = sigma_km / grid.km_per_px_equator()
floor = (1 - share) / share
ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0 if ocean_share > 0 else None
rho = diffusion.prepare_density(P, floor, sigma_px, "wall", ocean=ocean, ocean_share=ocean_share)
log(f"{tag}: {grid.describe()} sigma {sigma_px:.2f} px share {share} ocean {ocean_share} method {method} {kv}")
t0 = time.time(); psi = None
if method in ("ot", "ot_direct"):
    shares = ([s for s in (0.95, 0.98, 0.99, 0.995, 0.999) if s < share] + [share]) if method == "ot" else [share]
    po, stages = ot_poisson.spectral_homotopy(P, shares, sigma_px, "wall", iters=int(kv.get("iters", 400)), damping=kv.get("damping", 0.5), log=log, ocean=ocean, ocean_share=ocean_share)
    X, Y = po.mesh(); info = {"stages": stages}; rho = po.rho0
    psi = po.psi_from_S(po.S).cpu().numpy().astype(np.float32)
elif method == "diffusion":
    dc = diffusion.TorchDiffusionCartogram(None, x_boundary="wall", rho=rho)
    md = kv.get("max_disp", float(np.clip(sigma_px / 2, 0.5, 2.0)))
    X, Y, info = dc.run(tol=kv.get("tol", 1e-3), max_disp=md, cap_frac=kv.get("cap_frac", 0.1), growth=kv.get("growth", 1.15), t_start=kv.get("t_start", 0.5), log=log)
elif method == "gsm":
    dc = flow.GSMFlow(None, x_boundary="wall", rho=rho)
    md = kv.get("max_disp", float(np.clip(sigma_px / 2, 0.5, 2.0)))
    X, Y, info = dc.run(max_disp=md, growth=kv.get("growth", 1.15), log=log)
else:
    raise SystemExit("unknown method")
secs = time.time() - t0
m = diffusion.equalisation_metrics(rho, X, Y)
_, twist = layers.stretch_and_twist(X, Y)
A = diffusion.quad_areas(X, Y); ok = A > 0; w = rho[ok]
def wq(v, w, ps):
    o = np.argsort(v); cw = np.cumsum(w[o]) / w.sum(); return [float(v[o][min(np.searchsorted(cw, p), len(o) - 1)]) for p in ps]
t50, t95 = wq(np.abs(twist[ok]), w, [0.5, 0.95])
ys, xs = np.mgrid[0:X.shape[0], 0:X.shape[1]]
disp = np.hypot(X - xs, Y - ys)
dc_ = (disp[:-1, :-1] + disp[:-1, 1:] + disp[1:, :-1] + disp[1:, 1:]) / 4
km = grid.km_per_px_equator()
m.update({"twist_popweighted_p50_deg": t50, "twist_popweighted_p95_deg": t95,
          "displacement_popweighted_mean_px": float((dc_ * rho).sum() / rho.sum()),
          "displacement_popweighted_rms_px": float(np.sqrt((dc_ ** 2 * rho).sum() / rho.sum())),
          "transport_cost_popweighted_mean_sq_px": float((dc_ ** 2 * rho).sum() / rho.sum()),
          "km_per_px_equator": km, "seconds": secs})
m.update(layers.recognisability(os.path.join(RAW, "ne_50m_admin_0_countries.geojson"), grid, X, Y, rho))
m.update({k: v for k, v in info.items() if k != "stages"})
if "stages" in info: m["stages"] = info["stages"]
json.dump({"tag": tag, "method": method, "width": width, "W": grid.W, "H": grid.H, "lat_cut": grid.lat_cut, "lon0": grid.lon0, "x_boundary": "wall", "grid": "mercator",
           "sigma_km": sigma_km, "sigma_px": sigma_px, "share": share, "floor": floor, "ocean_share": ocean_share, "kv": kv, "factor": factor}, open(os.path.join(out, "params.json"), "w"), indent=1)
json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
extra = {"psi": psi} if psi is not None else {}
np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=rho.astype(np.float32), **extra)
log(f"RESULT {tag}: err p05/p95 {m['log_ratio_popweighted_p05']:+.4f}/{m['log_ratio_popweighted_p95']:+.4f} aniso {m['anisotropy_popweighted_p50']:.2f}/{m['anisotropy_popweighted_p95']:.1f} twist {t50:.2f}/{t95:.2f} disp mean {m['displacement_mean_px']:.1f} popmean {m['displacement_popweighted_mean_px']:.1f} poprms {m['displacement_popweighted_rms_px']:.1f} shape {m['shape_error_popweighted']:.3f} folds {m['folds']} {secs:.0f}s")
