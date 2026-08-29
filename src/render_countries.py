"""Countries coloured and labelled through a warp: python src/render_countries.py <experiment> [out_width]."""
import json, os, sys, colorsys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from rasterio import features
from rasterio.transform import Affine
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from hc.diffusion import quad_areas
from run import ROOT, RAW


def country_ids(grid, vectors="50m"):
    with open(os.path.join(RAW, f"ne_{vectors}_admin_0_countries.geojson")) as f:
        gj = json.load(f)
    shapes, names, pops = [], [], []
    for k, feat in enumerate(gj["features"]):
        g = feat["geometry"]
        def tf(ring):
            c = np.asarray(ring, np.float64)
            x, y = grid.xy(c[:, 0], c[:, 1])
            return np.stack([x, y], 1).tolist()
        if g["type"] == "Polygon":
            geom = {"type": "Polygon", "coordinates": [tf(r) for r in g["coordinates"]]}
        elif g["type"] == "MultiPolygon":
            geom = {"type": "MultiPolygon", "coordinates": [[tf(r) for r in poly] for poly in g["coordinates"]]}
        else:
            continue
        shapes.append((geom, k + 1))
        names.append(feat["properties"].get("NAME", feat["properties"].get("ADMIN", str(k))))
        pops.append(float(feat["properties"].get("POP_EST", 0) or 0))
    ids = features.rasterize(shapes, out_shape=(grid.H, grid.W), transform=Affine.identity(), fill=0, dtype="int32")
    return ids, names, pops


def palette(n, seed=3):
    rng = np.random.default_rng(seed)
    cols = []
    for i in range(n):
        h = (i * 0.618033988749895 + 0.11) % 1.0
        s = 0.28 + 0.22 * rng.random()
        v = 0.82 + 0.12 * rng.random()
        cols.append(colorsys.hsv_to_rgb(h, s, v))
    return np.array(cols)


def main(name, out_w=None, label_min_share=0.0004):
    out = os.path.join(ROOT, "experiments", name)
    p = json.load(open(os.path.join(out, "params.json")))
    z = np.load(os.path.join(out, "mesh.npz"))
    X, Y, rho0 = z["X"].astype(np.float64), z["Y"].astype(np.float64), z["rho0"].astype(np.float64)
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"])
    X = X - (p.get("lon0", -180.0) + 180.0) / 360.0 * grid.W  # frame cut (the warp lives on a cylinder)
    H, W = grid.H, grid.W
    out_w = out_w or min(W, 4096)
    oh, ow = int(round(H * out_w / W)), out_w
    scale = ow / W
    wrap = p.get("x_boundary", "periodic") == "periodic"
    ids, names, pops = country_ids(grid, p.get("vectors", "50m"))
    cols = palette(len(names) + 1)
    cols[0] = render.OCEAN
    rgb = cols[ids]  # H, W, 3
    img = np.stack([render.splat(rgb[..., c], X, Y, (oh, ow), wrap=wrap) for c in range(3)], axis=-1)
    fig, ax = render._figure(oh, ow, "white")
    ax.imshow(np.clip(img, 0, 1), extent=(0, ow, oh, 0), interpolation="nearest")
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{p.get('vectors','50m')}_admin_0_countries.geojson"), grid)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{p.get('vectors','50m')}_coastline.geojson"), grid)
    render._add_lines(ax, borders, X, Y, W, scale, "#00000070", 0.35)
    render._add_lines(ax, coast, X, Y, W, scale, "#000000", 0.4)
    # labels at the centroid of each country's warped area
    A = np.abs(quad_areas(X, Y))
    cx = (X[:-1, :-1] + X[:-1, 1:] + X[1:, :-1] + X[1:, 1:]) / 4
    cy = (Y[:-1, :-1] + Y[:-1, 1:] + Y[1:, :-1] + Y[1:, 1:]) / 4
    total = A.sum()
    flat_ids = ids.ravel()
    order = np.argsort(flat_ids)
    sorted_ids = flat_ids[order]
    starts = np.searchsorted(sorted_ids, np.arange(1, len(names) + 1))
    ends = np.searchsorted(sorted_ids, np.arange(1, len(names) + 1), side="right")
    Af, cxf, cyf = A.ravel()[order], (cx.ravel() % W)[order], cy.ravel()[order]
    for k, nm in enumerate(names):
        s, e = starts[k], ends[k]
        if e <= s:
            continue
        a = Af[s:e]
        share = a.sum() / total
        if share < label_min_share:
            continue
        # circular mean in x (periodic), plain mean in y, area-weighted
        ang = cxf[s:e] / W * 2 * np.pi
        mx = (np.arctan2((np.sin(ang) * a).sum(), (np.cos(ang) * a).sum()) / (2 * np.pi)) % 1.0 * W
        my = (cyf[s:e] * a).sum() / a.sum()
        fs = float(np.clip(6 + 60 * np.sqrt(share), 6, 48)) * out_w / 4096
        ax.text(mx * scale, my * scale, nm, fontsize=fs, ha="center", va="center", color="#111", alpha=0.9,
                path_effects=None)
    ax.text(0.01, 0.01, f"{name}: countries, share {p.get('share') or round(1/(1+p['floor']),3)}", transform=ax.transAxes, fontsize=9)
    fig.savefig(os.path.join(out, "countries.png"), dpi=100)
    plt.close(fig)
    print("wrote", os.path.join(out, "countries.png"))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
