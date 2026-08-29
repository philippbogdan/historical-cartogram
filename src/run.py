"""One cartogram experiment: prep -> warp -> metrics (with the fold gate S4) -> renders.

Usage: python src/run.py --name e006_S2 --method diffusion --grid mercator --width 4096
"""
import argparse, json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, render, ot_poisson, flow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
DER = os.path.join(ROOT, "data", "derived")
GHS = os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif")
NCOLS = 43200


def get_lonlat(factor):
    os.makedirs(DER, exist_ok=True)
    path = os.path.join(DER, f"ghs2025_lonlat_f{factor}.npz")
    if os.path.exists(path):
        z = np.load(path)
        return z["counts"], tuple(z["bounds"])
    counts, bounds = prep.load_lonlat_counts(GHS, factor)
    np.savez_compressed(path, counts=counts, bounds=np.array(bounds))
    return counts, bounds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--method", default="diffusion", choices=["diffusion", "ot_poisson_oneshot", "ot_poisson", "gsm", "jellium", "gravity"])
    ap.add_argument("--t-max", type=float, default=None, help="jellium/gravity: stop time (gravity: the anti-cartogram time)")
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--grid", default="mercator", choices=["mercator", "equalarea"])
    ap.add_argument("--lat-cut", type=float, default=None)
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--x-boundary", default="periodic", choices=["periodic", "wall"])
    ap.add_argument("--backend", default="torch", choices=["torch", "numpy"])
    ap.add_argument("--floor", type=float, default=0.01, help="empty-cell floor as a fraction of mean density (= (1-share)/share)")
    ap.add_argument("--share", type=float, default=None, help="humanity share lambda: area = lambda*people + (1-lambda)*frame area; overrides --floor")
    ap.add_argument("--sigma-km", type=float, default=30.0, help="gaussian pre-smoothing, km at the equator")
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--max-disp", type=float, default=None, help="px per step; default sigma_px/2 clipped to [0.5, 2]")
    ap.add_argument("--cap-frac", type=float, default=0.1, help="late-time displacement cap as a fraction of sqrt(2t)")
    ap.add_argument("--no-repair", action="store_true", help="skip the fold repair post-process (S4)")
    ap.add_argument("--out-width", type=int, default=None, help="render width in px (default = grid width, max 4096)")
    ap.add_argument("--vectors", default="50m", choices=["110m", "50m"])
    args = ap.parse_args()

    out = os.path.join(ROOT, "experiments", args.name)
    os.makedirs(out, exist_ok=True)
    log_f = open(os.path.join(out, "log.txt"), "w")
    def log(s):
        print(s, flush=True); log_f.write(s + "\n"); log_f.flush()

    if args.share is not None:
        args.floor = (1 - args.share) / args.share
    grid = prep.Grid(args.grid, args.width, args.lat_cut)
    factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * args.width)))
    log(f"grid {grid.describe()}; GHS-POP block-summed by {factor}")
    counts, bounds = get_lonlat(factor)
    P, dropped = prep.to_grid(counts, bounds, grid)
    sigma_px = args.sigma_km / grid.km_per_px_equator()
    max_disp = args.max_disp or float(np.clip(sigma_px / 2, 0.5, 2.0))
    log(f"total {P.sum()/1e9:.4f} bn people; dropped beyond +-{grid.lat_cut}: {dropped:.0f}; sigma {sigma_px:.2f} px; max_disp {max_disp}")

    t0 = time.time()
    if args.method == "diffusion":
        cls = diffusion.TorchDiffusionCartogram if args.backend == "torch" else diffusion.DiffusionCartogram
        dc = cls(P, floor=args.floor, sigma=sigma_px, x_boundary=args.x_boundary)
        X, Y, info = dc.run(tol=args.tol, max_disp=max_disp, cap_frac=args.cap_frac, log=log)
    elif args.method == "gsm":
        dc = flow.GSMFlow(P, floor=args.floor, sigma=sigma_px, x_boundary=args.x_boundary)
        X, Y, info = dc.run(max_disp=max_disp, log=log)
    elif args.method in ("jellium", "gravity"):
        dc = flow.JelliumFlow(P, floor=args.floor, sigma=sigma_px, x_boundary=args.x_boundary, sign=+1.0 if args.method == "jellium" else -1.0)
        X, Y, info = dc.run(max_disp=max_disp, tol=args.tol if args.method == "jellium" else 0.0, t_max=args.t_max or (30.0 if args.method == "jellium" else 0.5), log=log)
    else:
        dc = ot_poisson.PoissonOT(P, floor=args.floor, sigma=sigma_px, x_boundary=args.x_boundary)
        X, Y, info = dc.run(iters=args.iters, damping=args.damping, one_shot_only=(args.method == "ot_poisson_oneshot"), log=log)
    metrics0 = diffusion.equalisation_metrics(dc.rho0, X, Y)
    log("pre-repair: " + json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in metrics0.items()}))
    if metrics0["folds"] > 0 and not args.no_repair:
        X, Y, rep = diffusion.repair_folds(X, Y, periodic=(args.x_boundary == "periodic"), mass=dc.rho0, log=log)
        metrics = diffusion.equalisation_metrics(dc.rho0, X, Y)
        metrics.update(rep)
        metrics["p95_shift_by_repair"] = metrics["log_ratio_popweighted_p95"] - metrics0["log_ratio_popweighted_p95"]
        metrics["pre_repair"] = {k: metrics0[k] for k in ("log_ratio_popweighted_p05", "log_ratio_popweighted_p95", "anisotropy_popweighted_p50", "anisotropy_popweighted_p95")}
    else:
        metrics = metrics0
    metrics.update(info)
    metrics["seconds"] = time.time() - t0
    log(json.dumps(metrics, indent=1))
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=dc.rho0.astype(np.float32))
    params = vars(args) | {"H": grid.H, "W": grid.W, "lat_cut": grid.lat_cut, "sigma_px": sigma_px, "max_disp": max_disp, "factor": factor}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1)
    json.dump(metrics, open(os.path.join(out, "metrics.json"), "w"), indent=1)

    render_all(out, grid, X, Y, dc.rho0, params, log)
    log(f"gate S4 folds: {metrics['gate_folds']} ({metrics['folds']}); wrote {out}")


def render_all(out, grid, X, Y, rho0, p, log=print):
    v = p["vectors"]
    out_w = p.get("out_width") or min(grid.W, 4096)
    wrap = p["x_boundary"] == "periodic"
    mask = render.land_mask(os.path.join(RAW, f"ne_{v}_land.geojson"), grid)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_coastline.geojson"), grid)
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_admin_0_countries.geojson"), grid)
    grat = render.graticule(grid)
    mg = render.metric_grid(grid, 100.0)
    tis = render.tissot_circles(grid)
    ys, xs = np.mgrid[0:grid.H + 1, 0:grid.W + 1]
    title = f"{os.path.basename(out)}: {p['method']}, {grid.describe()}, floor {p['floor']}, sigma {p['sigma_km']} km"
    t0 = time.time()
    render.draw(xs, ys, mask, os.path.join(out, "geography.png"), out_w, coast, borders, grat, title="geography", wrap=wrap)
    render.draw(X, Y, mask, os.path.join(out, "cartogram.png"), out_w, coast, borders, grat, title=title, wrap=wrap)
    render.draw(X, Y, mask, os.path.join(out, "metric_grid.png"), out_w, coast, [], [], mgrid=mg, title=title + " | 100 km equal-area cells", wrap=wrap)
    render.draw(X, Y, mask, os.path.join(out, "tissot.png"), out_w, coast, [], [], tissot=tis, title=title + " | Tissot, 300 km circles", wrap=wrap)
    render.draw(X, Y, mask, os.path.join(out, "cartogram_density.png"), out_w, coast, [], [], raster=np.log10(rho0), title=title + " | log10 density", wrap=wrap)
    render.draw_error(X, Y, rho0, os.path.join(out, "error.png"), out_w, wrap=wrap)
    log(f"renders in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
