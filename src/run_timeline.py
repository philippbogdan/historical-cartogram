"""T1: every HYDE epoch through the same solver and renders, one experiment per epoch.
    python src/run_timeline.py <width> [sigma_km] [ocean_share] [epoch selection: all | every:N | list of years]"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson, render, hyde
from run import ROOT, RAW, render_all
from render_countries import country_ids, palette


def render_frame(out, grid, X, Y, rho0, p, out_w=2048):
    """The two renders a timeline frame needs: countries (coloured, labelled) and the plain cartogram."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    H, W = grid.H, grid.W; oh, ow = int(round(H * out_w / W)), out_w; scale = ow / W
    ids, names, pops = country_ids(grid, p["vectors"]); cols = palette(len(names) + 1); cols[0] = render.OCEAN
    rgb = cols[ids]; img = np.stack([render.splat(rgb[..., c], X, Y, (oh, ow), wrap=False) for c in range(3)], axis=-1)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{p['vectors']}_coastline.geojson"), grid)
    fig, ax = render._figure(oh, ow, "white"); ax.imshow(np.clip(img, 0, 1), extent=(0, ow, oh, 0), interpolation="nearest")
    render._add_lines(ax, coast, X, Y, W, scale, "#000000", 0.35)
    ax.text(0.01, 0.01, f"{p['year']}: {p['honesty']} | 1 px = {p.get('people_per_px', 0):.0f} people | {os.path.basename(out)}", transform=ax.transAxes, fontsize=9)
    fig.savefig(os.path.join(out, "countries.png"), dpi=100); plt.close(fig)

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
    params = {"name": name, "method": "ot_spectral_homotopy", "grid": "mercator", "lat_cut": grid.lat_cut, "lon0": lon0, "width": width, "W": grid.W, "H": grid.H, "people_per_px": float(total / (grid.W * grid.H)),
              "x_boundary": xb, "floor": 0.001001, "share": 0.999, "ocean_share": ocean_share, "sigma_km": sigma_km, "sigma_px": sigma_px, "vectors": mask_v,
              "source": f"HYDE 3.3 {scenario} population.nc", "year": int(y), "honesty": "modelled (HYDE allocation of regional estimates)" if y < 1950 else "census-based (HYDE, national statistics)"}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1)
    json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    # compact mesh: displacement quantised to 1/16 px as int16 (exact enough for playback and inverse maps)
    ys_, xs_ = np.mgrid[0:grid.H + 1, 0:grid.W + 1]
    np.savez_compressed(os.path.join(out, "mesh16.npz"), dx=np.round((X - xs_) * 16).astype(np.int16), dy=np.round((Y - ys_) * 16).astype(np.int16), rho0=po.rho0.astype(np.float16))
    open(os.path.join(out, "log.txt"), "w").write(f"year {y} population {total/1e6:.2f} M; residual {r:.4f}; {time.time()-t0:.0f}s\n")
    render_frame(out, grid, X, Y, po.rho0, params)
    index.append(name)
    print(f"{name}: pop {total/1e6:9.1f} M  p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f}  folds {m['folds']}  {time.time()-t0:.0f}s", flush=True)
json.dump({"scenario": scenario, "width": width, "frames": index}, open(os.path.join(out_root, f"index_{scenario}_{width}.json"), "w"), indent=1)
print("done", len(index), "frames")
