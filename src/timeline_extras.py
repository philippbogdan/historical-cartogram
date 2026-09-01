"""Phase 5 extras on top of the epoch frames.
    python src/timeline_extras.py personyears <width>        L3: area = human life lived, 10,000 BC to 2023
    python src/timeline_extras.py peak <width>               T6: epoch of maximum density per pixel, drawn on today's frame
    python src/timeline_extras.py cities <frame name>        T7: Reba/Chandler cities through one epoch's warp
    python src/timeline_extras.py uncertainty <frame name>   L8: log(upper/lower) through the warp as a grain layer
    python src/timeline_extras.py blend <width> <year_a> <year_b> <s>   T3: cartogram of the blended measure
"""
import csv, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson, render, hyde, layers
from run import ROOT, RAW, render_all

lon0, xb = -168.0, "wall"
TL = os.path.join(ROOT, "experiments", "timeline")


def solve_and_save(name, P, grid, sigma_km, ocean_share, extra_params, log=print):
    out = os.path.join(TL, name); os.makedirs(out, exist_ok=True)
    sigma_px = sigma_km / grid.km_per_px_equator()
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
    t0 = time.time()
    po, stages = ot_poisson.spectral_homotopy(P, [0.95, 0.999], sigma_px, xb, iters=400, damping=0.5, log=lambda s: None, ocean=ocean, ocean_share=ocean_share)
    X, Y = po.mesh(); m = diffusion.equalisation_metrics(po.rho0, X, Y); r, f = po.residual()
    m.update({"residual": r, "cell_folds": f, "seconds": time.time() - t0, "total": float(P.sum())})
    params = {"name": name, "method": "ot_spectral_homotopy", "grid": "mercator", "lat_cut": grid.lat_cut, "lon0": lon0, "width": grid.W, "W": grid.W, "H": grid.H, "x_boundary": xb,
              "floor": 0.001001, "share": 0.999, "ocean_share": ocean_share, "sigma_km": sigma_km, "sigma_px": sigma_px, "vectors": "50m", **extra_params}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1); json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=po.rho0.astype(np.float32), counts=P.astype(np.float32))
    render_all(out, grid, X, Y, po.rho0, params, log=lambda s: None)
    log(f"{name}: p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f} folds {m['folds']} {time.time()-t0:.0f}s")
    return out


def personyears(width):
    H = hyde.Hyde(os.path.join(RAW, "hyde33", "population_base.nc")); ys = list(H.years)
    acc = np.zeros(H.counts(0).shape); total = 0.0
    for i in range(len(ys) - 1):  # trapezoid over the epoch schedule
        dt = ys[i + 1] - ys[i]; a, b = H.counts(i), H.counts(i + 1); acc += 0.5 * (a + b) * dt
    grid = prep.Grid("mercator", width, lon0=lon0); P, _ = prep.to_grid(acc, H.bounds, grid)
    print(f"person-years total {acc.sum()/1e9:.1f} bn person-years from {ys[0]} to {ys[-1]}")
    solve_and_save(f"L3_personyears_{width}", P, grid, 60.0, 0.05, {"source": "HYDE 3.3 base, integrated 10,000 BC to 2023", "honesty": "modelled before 1950", "measure": "person-years"})


def peak(width):
    H = hyde.Hyde(os.path.join(RAW, "hyde33", "population_base.nc")); ys = np.array(list(H.years))
    best = np.full(H.counts(0).shape, -1e30); arg = np.zeros(H.counts(0).shape, int)
    for i in range(len(ys)):
        c = H.counts(i); m = c > best; best[m] = c[m]; arg[m] = i
    peak_year = ys[arg].astype(np.float64); peak_year[best <= 0] = np.nan
    # on today's frame: average peak year per grid cell (people-weighted would need counts; use simple mean)
    grid = prep.Grid("mercator", width, lon0=lon0)
    pk, _ = prep.to_grid(np.nan_to_num(peak_year, nan=0.0) * (best > 0), H.bounds, grid); n, _ = prep.to_grid((best > 0).astype(np.float64), H.bounds, grid)
    pk = np.where(n > 0, pk / np.maximum(n, 1e-9), np.nan)
    np.save(os.path.join(TL, f"T6_peak_year_{width}.npy"), pk.astype(np.float32))
    print("peak-year grid written; share of cells peaking in 2023:", float(np.nanmean(pk >= 2020)))


def cities(frame):
    out = os.path.join(TL, frame); p = json.load(open(os.path.join(out, "params.json"))); year = p["year"]
    z = np.load(os.path.join(out, "mesh.npz")); X, Y = z["X"].astype(np.float64), z["Y"].astype(np.float64)
    grid = prep.Grid(p["grid"], p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0)); W = grid.W
    rows = []
    for fn in ("chandlerV2.csv", "modelskiAncientV2.csv", "modelskiModernV2.csv"):
        with open(os.path.join(RAW, "reba", fn), encoding="utf-8", errors="replace") as f:
            rd = csv.reader(f); head = next(rd)
            ycols = [(j, h) for j, h in enumerate(head) if h.strip().lstrip("-").replace("BC", "").replace("AD", "").strip().isdigit() or h.strip().startswith(("BC_", "AD_"))]
            def yv(h):
                h = h.strip()
                if h.startswith("BC_"): return -int(h[3:])
                if h.startswith("AD_"): return int(h[3:])
                return int(h)
            ycols = [(j, yv(h)) for j, h in ycols]
            try: ilat = head.index("Latitude"); ilon = head.index("Longitude"); iname = head.index("City")
            except ValueError: continue
            for r in rd:
                try: lat, lon = float(r[ilat]), float(r[ilon])
                except (ValueError, IndexError): continue
                best = None
                for j, y in ycols:
                    if y <= year and (best is None or y > best[0]) and j < len(r) and r[j].strip():
                        try: best = (y, float(r[j]))
                        except ValueError: pass
                if best and year - best[0] <= 200:
                    rows.append((r[iname], lon, lat, best[1] * 1000.0, best[0]))
    if not rows: print("no cities for", year); return
    pts = np.array([[c[1], c[2]] for c in rows]); x, y = grid.xy(pts[:, 0], pts[:, 1]); wp = render.warp_points(np.stack([x, y], 1), X, Y, W)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from PIL import Image
    base = Image.open(os.path.join(out, "countries.png")) if os.path.exists(os.path.join(out, "countries.png")) else Image.open(os.path.join(out, "cartogram.png"))
    ow, oh = base.size; sc = ow / W
    fig = plt.figure(figsize=(ow / 100, oh / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.imshow(base, extent=(0, ow, oh, 0))
    pops = np.array([c[3] for c in rows]); s = np.clip(np.sqrt(pops / 1e4), 1.5, 60) * ow / 4096
    ax.scatter((wp[:, 0] % W) * sc, wp[:, 1] * sc, s=s ** 2, c="#c0392b", alpha=0.6, edgecolors="#600", linewidths=0.5)
    for c, (x1, y1), pp in sorted(zip(rows, wp, pops), key=lambda t: -t[2])[:40]:
        ax.text((x1 % W) * sc + 4, y1 * sc, c[0], fontsize=7 * ow / 4096 + 3, color="#300")
    ax.text(0.01, 0.01, f"{frame}: {len(rows)} cities with a Chandler/Modelski population record within 200 years before {year} (T7)", transform=ax.transAxes, fontsize=9)
    fig.savefig(os.path.join(out, "cities.png"), dpi=100); plt.close(fig); print("wrote", os.path.join(out, "cities.png"), len(rows), "cities")


def uncertainty(frame):
    out = os.path.join(TL, frame); p = json.load(open(os.path.join(out, "params.json"))); year = p["year"]
    Hl = hyde.Hyde(os.path.join(RAW, "hyde33", "population_lower.nc")); Hu = hyde.Hyde(os.path.join(RAW, "hyde33", "population_upper.nc"))
    i = list(Hl.years).index(year); lo, up = Hl.counts(i), Hu.counts(i)
    grid = prep.Grid(p["grid"], p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
    L, _ = prep.to_grid(lo, Hl.bounds, grid); U, _ = prep.to_grid(up, Hu.bounds, grid)
    ratio = np.log(np.maximum(U, 1) / np.maximum(L, 1))
    z = np.load(os.path.join(out, "mesh.npz")); X, Y = z["X"].astype(np.float64), z["Y"].astype(np.float64)
    mask = np.ones(ratio.shape, np.uint8)
    render.draw(X, Y, mask, os.path.join(out, "uncertainty.png"), min(grid.W, 4096), raster=ratio, cmap="Greys", vmin=0, vmax=2.0, title=f"{frame}: log(upper/lower) HYDE bounds (L8); white = certain, dark = the estimate could be 7x off", wrap=False)
    print("wrote uncertainty for", frame, "median log ratio where people live:", float(np.median(ratio[U > 100])))


def blend(width, ya, yb, s):
    H = hyde.Hyde(os.path.join(RAW, "hyde33", "population_base.nc")); ys = list(H.years)
    a, b = H.counts(ys.index(ya)), H.counts(ys.index(yb)); c = (1 - s) * a + s * b
    grid = prep.Grid("mercator", width, lon0=lon0); P, _ = prep.to_grid(c, H.bounds, grid)
    solve_and_save(f"t_blend_{ya:+06d}_{yb:+06d}_{s:.2f}", P, grid, 60.0, 0.05, {"source": f"HYDE 3.3 base, measure blend {1-s:.2f}*{ya} + {s:.2f}*{yb}", "year": ya + s * (yb - ya), "honesty": "interpolated measure (T3)"})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "personyears": personyears(int(sys.argv[2]))
    elif cmd == "peak": peak(int(sys.argv[2]))
    elif cmd == "cities": cities(sys.argv[2])
    elif cmd == "uncertainty": uncertainty(sys.argv[2])
    elif cmd == "blend": blend(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]))
