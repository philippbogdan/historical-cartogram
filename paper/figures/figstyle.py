"""Shared figure infrastructure for the paper: monochrome style, mesh loading, vector warping,
dot placement. Every figure script imports this and records its provenance in a sidecar JSON."""
import json, os, sys, hashlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
from hc import prep, render, diffusion  # noqa: E402
from hc.diffusion import quad_areas  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
BENCH = os.path.join(ROOT, "experiments", "bench")
OUT = os.path.join(ROOT, "paper", "figures")
INK = "#000000"
PAPER = "#ffffff"
TEXT_W_MM = 160.0     # article text width (geometry: 160 mm)
COL_W_MM = 77.0       # half width with a gutter

RC = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.5, "lines.linewidth": 0.6, "patch.linewidth": 0.5,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "figure.dpi": 100, "savefig.dpi": 600,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False,
}


def mm(x):
    return x / 25.4


def figure(w_mm, h_mm, **kw):
    plt.rcParams.update(RC)
    return plt.figure(figsize=(mm(w_mm), mm(h_mm)), layout="constrained", **kw)


def load_bench(tag, repaired=True):
    """X, Y (float64, corner mesh), rho0, params, metrics; folds repaired for drawing unless repaired=False."""
    d = os.path.join(BENCH, tag)
    z = np.load(os.path.join(d, "mesh.npz"))
    X, Y, rho = z["X"].astype(np.float64), z["Y"].astype(np.float64), z["rho0"].astype(np.float64)
    p = json.load(open(os.path.join(d, "params.json"))); m = json.load(open(os.path.join(d, "metrics.json")))
    if repaired:
        cache = os.path.join(d, "mesh_repaired.npz")
        if os.path.exists(cache):
            zz = np.load(cache); X, Y = zz["X"].astype(np.float64), zz["Y"].astype(np.float64)
        else:
            X, Y, _ = diffusion.repair_folds(X, Y, periodic=False, mass=rho, log=lambda *_: None)
            np.savez_compressed(cache, X=X.astype(np.float32), Y=Y.astype(np.float32))
    grid = prep.Grid(p["grid"], p["width"], p["lat_cut"], lon0=p["lon0"])
    return X, Y, rho, grid, p, m


def population_grid(grid):
    """People per cell on `grid` from GHS-POP 2025 (30 arcsec), exact re-binning."""
    from run import get_lonlat, NCOLS  # noqa
    factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * grid.W)))
    counts, bounds = get_lonlat(factor)
    P, _ = prep.to_grid(counts, bounds, grid)
    return np.maximum(P, 0.0)


def warp_lines(lines, X, Y, wall=True):
    """Warp densified pixel polylines through the corner mesh; split at any jump (frame walls)."""
    W = X.shape[1] - 1
    out = []
    for l in lines:
        wp = render.warp_points(l, X, Y, W)
        for s in render.split_seam(wp, W, jump=W / 8):
            out.append(s)
    return out


def split_lines(lines, W):
    """Split unwarped pixel polylines where they jump across the frame's wall (lon0)."""
    out = []
    for l in lines:
        for s in render.split_seam(l, W, jump=W / 8):
            out.append(s)
    return out


def lines_from_geojson(path, grid):
    """Like render.lines_from_geojson, but a polyline is cut where it crosses the frame's wall BEFORE
    densification, so no segment is drawn straight across the frame."""
    W = grid.W
    out = []
    for g in render._iter_geoms(path):
        t = g["type"]
        parts = ([g["coordinates"]] if t == "LineString" else g["coordinates"] if t in ("MultiLineString", "Polygon")
                 else [r for poly in g["coordinates"] for r in poly] if t == "MultiPolygon" else [])
        for p in parts:
            c = np.asarray(p, np.float64)
            x, y = grid.xy(c[:, 0], c[:, 1])
            pts = np.stack([x, y], 1)
            cut = np.nonzero(np.abs(np.diff(pts[:, 0])) > W / 2)[0] + 1
            for seg in np.split(pts, cut):
                if len(seg) > 1:
                    out.append(render._densify(seg))
    return out


def vectors(grid, res="50m"):
    coast = lines_from_geojson(os.path.join(RAW, f"ne_{res}_coastline.geojson"), grid)
    borders = lines_from_geojson(os.path.join(RAW, f"ne_{res}_admin_0_countries.geojson"), grid)
    grat = render.graticule(grid, 15)
    return coast, borders, grat


def lines_to_ax(ax, segs, scale=1.0, lw=0.4, color=INK, ls="solid", alpha=1.0, zorder=3):
    if segs:
        ax.add_collection(LineCollection([s * scale for s in segs], colors=color, linewidths=lw, linestyles=ls, alpha=alpha, zorder=zorder, capstyle="round"))


def systematic_dots(P, people_per_dot, seed=0):
    """One dot per `people_per_dot` people: systematic sampling along raster order with a fixed random
    offset, then uniform jitter inside the cell. Deterministic; every cell's expected dot count is
    exactly its population divided by people_per_dot."""
    rng = np.random.default_rng(seed)
    flat = P.ravel()
    cum = np.cumsum(flat)
    total = cum[-1]
    n = int(total // people_per_dot)
    targets = (np.arange(n) + rng.random()) * people_per_dot
    idx = np.searchsorted(cum, targets, side="right")
    idx = np.minimum(idx, flat.size - 1)
    r, c = np.divmod(idx, P.shape[1])
    pts = np.stack([c + rng.random(n), r + rng.random(n)], 1).astype(np.float64)
    return pts


def frame_axes(ax, W, H, scale=1.0):
    ax.set_xlim(0, W * scale); ax.set_ylim(H * scale, 0)
    ax.set_aspect("equal"); ax.axis("off")


def provenance(name, **info):
    """Write a sidecar JSON next to the figure with inputs, transformations and hashes."""
    rec = {"figure": name}
    rec.update(info)
    for k, v in list(info.items()):
        if k.endswith("_path") and isinstance(v, str) and os.path.exists(v):
            rec[k + "_sha256"] = hashlib.sha256(open(v, "rb").read()).hexdigest()[:16]
    json.dump(rec, open(os.path.join(OUT, name + ".provenance.json"), "w"), indent=1)


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=600)
    plt.close(fig)
    print("wrote", name)
