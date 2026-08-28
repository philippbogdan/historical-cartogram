"""One diffusion-cartogram experiment: prep -> warp -> metrics -> render.

Usage: python src/run_diffusion.py --name e001 --width 512 --floor 0.01 --sigma 0
"""
import argparse, json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
DER = os.path.join(ROOT, "data", "derived")
GHS = os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif")


def get_lonlat(factor):
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
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--lat-cut", type=float, default=85.0511)
    ap.add_argument("--floor", type=float, default=0.01, help="ocean/empty floor as a fraction of mean density")
    ap.add_argument("--sigma", type=float, default=0.0, help="extra gaussian pre-smoothing in pixels (solver already starts at t=0.5 px^2)")
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--max-disp", type=float, default=0.5)
    ap.add_argument("--vectors", default="50m", choices=["110m", "50m"])
    args = ap.parse_args()

    out = os.path.join(ROOT, "experiments", args.name)
    os.makedirs(out, exist_ok=True)
    log_f = open(os.path.join(out, "log.txt"), "w")
    def log(s):
        print(s); log_f.write(s + "\n"); log_f.flush()

    factor = max(d for d in prep.divisors(43200) if d <= max(1, 43200 // (args.width * 4)))
    log(f"reading GHS-POP block-summed by {factor}")
    counts, bounds = get_lonlat(factor)
    merc, dropped = prep.to_mercator(counts, bounds, args.width, args.lat_cut)
    H, W = merc.shape
    log(f"grid {W}x{H}, total {merc.sum()/1e9:.4f} bn people, dropped beyond +-{args.lat_cut}: {dropped:.0f}")

    t0 = time.time()
    dc = diffusion.DiffusionCartogram(merc, floor=args.floor, sigma=args.sigma)
    X, Y, info = dc.run(tol=args.tol, max_disp=args.max_disp, log=log)
    metrics = diffusion.equalisation_metrics(dc.rho0, X, Y)
    metrics.update(info); metrics["seconds"] = time.time() - t0
    log(json.dumps(metrics, indent=1))
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X, Y=Y, rho0=dc.rho0)
    json.dump(vars(args) | {"H": H, "W": W}, open(os.path.join(out, "params.json"), "w"), indent=1)
    json.dump(metrics, open(os.path.join(out, "metrics.json"), "w"), indent=1)

    v = args.vectors
    mask = render.land_mask(os.path.join(RAW, f"ne_{v}_land.geojson"), H, W, args.lat_cut)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_coastline.geojson"), H, W, args.lat_cut)
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_admin_0_countries.geojson"), H, W, args.lat_cut)
    grat = render.graticule(H, W, args.lat_cut)
    ys, xs = np.mgrid[0:H + 1, 0:W + 1]
    title = f"{args.name}: diffusion, {W}x{H}, floor {args.floor}, sigma {args.sigma}"
    render.draw(xs, ys, mask, os.path.join(out, "geography.png"), coast, borders, grat, title="geography (Mercator)")
    render.draw(X, Y, mask, os.path.join(out, "cartogram.png"), coast, borders, grat, title=title)
    render.draw(X, Y, mask, os.path.join(out, "cartogram_density.png"), coast, [], [],
                raster=np.log10(dc.rho0), title=title + " (log10 source density through the warp)")
    log(f"wrote {out}")


if __name__ == "__main__":
    main()
