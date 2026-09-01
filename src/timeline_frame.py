"""One timeline epoch through the solver and the renders (shared by the HYDE, GHS and SSP runners)."""
import json, os, time
import numpy as np
from hc import prep, diffusion, ot_poisson, render
from run import RAW
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


def run_epoch(out, grid, counts, bounds, year, source, honesty, sigma_km, ocean, ocean_share, xb="wall", lon0=-168.0, mask_v="50m"):
    """Solve one epoch (spectral OT homotopy, land pure, ocean buffer), write params/metrics/log, mesh16 and the renders."""
    os.makedirs(out, exist_ok=True)
    t0 = time.time(); name = os.path.basename(out)
    sigma_px = sigma_km / grid.km_per_px_equator()
    total = float(counts.sum())
    P, dropped = prep.to_grid(counts, bounds, grid)
    po, stages = ot_poisson.spectral_homotopy(P, [0.95, 0.999], sigma_px, xb, iters=400, damping=0.5, log=lambda s: None, ocean=ocean, ocean_share=ocean_share)
    X, Y = po.mesh()
    m = diffusion.equalisation_metrics(po.rho0, X, Y)
    r, f = po.residual()
    m.update({"residual": r, "cell_folds": f, "year": int(year), "population": total, "people_per_px": total / (grid.W * grid.H), "seconds": time.time() - t0})
    params = {"name": name, "method": "ot_spectral_homotopy", "grid": "mercator", "lat_cut": grid.lat_cut, "lon0": lon0, "width": grid.W, "W": grid.W, "H": grid.H, "people_per_px": total / (grid.W * grid.H),
              "x_boundary": xb, "floor": 0.001001, "share": 0.999, "ocean_share": ocean_share, "sigma_km": sigma_km, "sigma_px": sigma_px, "vectors": mask_v,
              "source": source, "year": int(year), "honesty": honesty}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1)
    json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    # compact mesh: displacement quantised to 1/16 px as int16 (exact enough for playback and inverse maps)
    ys_, xs_ = np.mgrid[0:grid.H + 1, 0:grid.W + 1]
    np.savez_compressed(os.path.join(out, "mesh16.npz"), dx=np.round((X - xs_) * 16).astype(np.int16), dy=np.round((Y - ys_) * 16).astype(np.int16), rho0=po.rho0.astype(np.float16))
    open(os.path.join(out, "log.txt"), "w").write(f"year {year} population {total/1e6:.2f} M; residual {r:.4f}; {time.time()-t0:.0f}s\n")
    render_frame(out, grid, X, Y, po.rho0, params)
    print(f"{name}: pop {total/1e6:9.1f} M  p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f}  folds {m['folds']}  {time.time()-t0:.0f}s", flush=True)
    return m
