"""The legible map for an experiment: countries coloured, rivers, lakes, ghost coastline, city
labels; plus equipotentials (if the run saved a potential), stretch and twist rasters.
    python src/render_map.py <experiment> [out_width]"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render, layers
from hc.diffusion import quad_areas
from run import ROOT, RAW
from render_countries import country_ids, palette


def main(name, out_w=None):
    out = os.path.join(ROOT, "experiments", name)
    p = json.load(open(os.path.join(out, "params.json")))
    z = np.load(os.path.join(out, "mesh.npz"))
    X, Y, rho0 = z["X"].astype(np.float64), z["Y"].astype(np.float64), z["rho0"].astype(np.float64)
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"])
    H, W = grid.H, grid.W
    out_w = out_w or min(W, 4096)
    oh, ow = int(round(H * out_w / W)), out_w
    scale = ow / W
    wrap = p.get("x_boundary", "periodic") == "periodic"
    v = p.get("vectors", "50m")
    ids, names, pops = country_ids(grid, v)
    cols = palette(len(names) + 1); cols[0] = render.OCEAN
    rgb = cols[ids]
    img = np.stack([render.splat(rgb[..., c], X, Y, (oh, ow), wrap=wrap) for c in range(3)], axis=-1)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_coastline.geojson"), grid)
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_admin_0_countries.geojson"), grid)
    riv = layers.rivers(RAW, grid, v)
    lak = layers.lakes(RAW, grid, v)
    places = layers.cities(os.path.join(RAW, "ne_10m_populated_places_simple.geojson"), grid, n=400)

    fig, ax = render._figure(oh, ow, "white")
    ax.imshow(np.clip(img, 0, 1), extent=(0, ow, oh, 0), interpolation="nearest")
    layers.ghost_coast(ax, coast, scale)
    render._add_lines(ax, riv, X, Y, W, scale, "#3b6fa0", 0.45)
    render._add_lines(ax, lak, X, Y, W, scale, "#3b6fa0", 0.35)
    render._add_lines(ax, borders, X, Y, W, scale, "#00000070", 0.35)
    render._add_lines(ax, coast, X, Y, W, scale, "#000000", 0.4)
    n = layers.draw_city_labels(ax, places, X, Y, W, scale, (oh, ow))
    ax.text(0.01, 0.01, f"{name}: map with {n} city labels, rivers, ghost coastline", transform=ax.transAxes, fontsize=9)
    fig.savefig(os.path.join(out, "map.png"), dpi=100); plt.close(fig)

    stretch, twist = layers.stretch_and_twist(X, Y)
    for arr, fname, cmap, vmin, vmax, title in [(stretch, "stretch.png", "RdBu_r", -4, 4, "log area scale (R6): red = enlarged, blue = shrunk"),
                                                (twist, "twist.png", "PuOr", -60, 60, "local rotation in degrees (X8): white = none")]:
        render.draw(X, Y, np.ones_like(rho0, dtype=np.uint8), os.path.join(out, fname), out_w, coast, [], [], raster=arr, cmap=cmap, vmin=vmin, vmax=vmax, title=title, wrap=wrap)
    m = json.load(open(os.path.join(out, "metrics.json")))
    w = rho0 / rho0.sum()
    m["twist_popweighted_p50_deg"] = float(np.interp(0.5, np.cumsum(w.ravel()[np.argsort(np.abs(twist).ravel())]), np.sort(np.abs(twist).ravel())))
    m["twist_popweighted_p95_deg"] = float(np.interp(0.95, np.cumsum(w.ravel()[np.argsort(np.abs(twist).ravel())]), np.sort(np.abs(twist).ravel())))
    json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    if "psi" in z.files:
        lines = layers.equipotential_lines(z["psi"].astype(np.float64), levels=48)
        render.draw(X, Y, np.ones_like(rho0, dtype=np.uint8), os.path.join(out, "equipotentials.png"), out_w, coast, [], [], grat=(), mgrid=lines,
                    raster=None, title="equipotentials of the transport potential (R7)", wrap=wrap)
    print("wrote map, stretch, twist" + (", equipotentials" if "psi" in z.files else ""), "twist p50/p95", round(m["twist_popweighted_p50_deg"], 2), round(m["twist_popweighted_p95_deg"], 2))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
