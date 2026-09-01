"""Phase 8: the population manifold kept curved.
    python src/geometry.py <width>   -> experiments/geometry_<width>/{curvature.png, geodesics.png, metric.png}
G1/G4  conformal metric g = e^{2u} (dx^2 + dy^2), u = 1/2 log(rho / rho_bar); Gaussian curvature
       K = -e^{-2u} lap(u), painted on the geographic frame (blue: negative, saddles between cities;
       red: positive, the tops of population hills).
G2     geodesics of that metric: for a conformal metric, x'' = 2 (grad u . x') x' - |x'|^2 grad u.
       A lattice of meridians and parallels shot as geodesics bends around cities like lensing.
"""
import json, os, sys, time
import numpy as np
from scipy import ndimage
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from hc.diffusion import prepare_density
from run import get_lonlat, NCOLS, ROOT, RAW

width = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
grid = prep.Grid("mercator", width, lon0=-168.0)
factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * width)))
counts, bounds = get_lonlat(factor); P, _ = prep.to_grid(counts, bounds, grid)
sigma_px = 60.0 / grid.km_per_px_equator()
ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
rho = prepare_density(P, 0.001, max(sigma_px, 2.0), "wall")   # no ocean buffer: empty land and sea alike
u = 0.5 * np.log(rho)                          # the pure humeter metric, for the curvature
u_g = 0.5 * np.log(0.2 + 0.8 * rho)            # a tempered metric for the geodesic pictures: empty regions
                                               # at the floor have wild log-gradients that only add noise
lap = ndimage.laplace(u)                      # unit spacing
K = -np.exp(-2 * u) * lap
out = os.path.join(ROOT, "experiments", f"geometry_{width}"); os.makedirs(out, exist_ok=True)
H, W = rho.shape
coast = render.lines_from_geojson(os.path.join(RAW, "ne_50m_coastline.geojson"), grid)
ys, xs = np.mgrid[0:H + 1, 0:W + 1].astype(np.float64)

def fig_geo(title):
    fig, ax = render._figure(H, W, "white"); return fig, ax

# G4: curvature as colour on the geographic frame
Ks = ndimage.gaussian_filter(K, 1.0)
lim = np.percentile(np.abs(Ks[~ocean]), 98)
img = matplotlib.colormaps["RdBu_r"](np.clip(Ks / lim, -1, 1) / 2 + 0.5)[..., :3]
fig, ax = fig_geo("curvature"); ax.imshow(img, extent=(0, W, H, 0), interpolation="nearest")
ax.add_collection(LineCollection([sg for l in coast for sg in render.split_seam(l, W)], colors="#000", linewidths=0.4))
ax.text(0.01, 0.01, f"Gaussian curvature of the population manifold (G4), +-{lim:.2g} per px^2; red positive (hilltops), blue negative (saddles between cities)", transform=ax.transAxes, fontsize=9)
fig.savefig(os.path.join(out, "curvature.png"), dpi=100); plt.close(fig)

# G2: geodesics. Integrate x'' = 2 (grad u . v) v - |v|^2 grad u with bilinear grad u.
gy, gx = np.gradient(ndimage.gaussian_filter(u_g, 1.5))
def grad_u(p):
    c = [np.clip(p[:, 1] - 0.5, 0, H - 1), np.clip(p[:, 0] - 0.5, 0, W - 1)]
    return np.stack([ndimage.map_coordinates(gx, c, order=1, mode="nearest"), ndimage.map_coordinates(gy, c, order=1, mode="nearest")], 1)
def shoot(p0, v0, steps, h=1.0):
    p, v = p0.copy(), v0.copy(); path = [p.copy()]
    for _ in range(steps):
        def acc(p, v):
            g = grad_u(p); vg = (v * g).sum(1, keepdims=True); return 2 * vg * v - (v * v).sum(1, keepdims=True) * g
        k1v = acc(p, v); k1p = v
        k2v = acc(p + h / 2 * k1p, v + h / 2 * k1v); k2p = v + h / 2 * k1v
        k3v = acc(p + h / 2 * k2p, v + h / 2 * k2v); k3p = v + h / 2 * k2v
        k4v = acc(p + h * k3p, v + h * k3v); k4p = v + h * k3v
        p = p + h / 6 * (k1p + 2 * k2p + 2 * k3p + k4p); v = v + h / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        v = v / np.linalg.norm(v, axis=1, keepdims=True)  # unit speed in the flat parameter; direction is what matters
        path.append(p.copy())
    return np.stack(path, 1)  # (n, steps+1, 2)
# fans of geodesics from three cities: the straight lines of the humeter world
fan_cities = {"London": (-0.13, 51.5), "Delhi": (77.2, 28.6), "Sao Paulo": (-46.6, -23.5)}
fan_paths, fan_cols = [], []
for nm, colr in zip(fan_cities, ("#8b0000", "#00468b", "#8b008b")):
    cx, cy = grid.xy(*fan_cities[nm]); n_dir = 48; th = np.linspace(0, 2 * np.pi, n_dir, endpoint=False)
    p0 = np.tile([[float(cx), float(cy)]], (n_dir, 1)); v0 = np.stack([np.cos(th), np.sin(th)], 1)
    fan_paths.append(shoot(p0, v0, int(W * 0.6), h=1.0)); fan_cols.append(colr)
def clip_paths(paths):
    segs = []
    for pth in paths:
        inside = (pth[:, 0] >= 0) & (pth[:, 0] <= W) & (pth[:, 1] >= 0) & (pth[:, 1] <= H)
        cut = np.nonzero(~inside)[0]; end = cut[0] if len(cut) else len(pth)
        if end > 2: segs.append(pth[:end])
    return segs
fig, ax = fig_geo("geodesics")
land = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid)
ax.imshow(np.where(land[..., None] > 0, render.LAND, render.OCEAN), extent=(0, W, H, 0), interpolation="nearest")
for pths, colr in zip(fan_paths, fan_cols):
    ax.add_collection(LineCollection(clip_paths(pths), colors=colr, linewidths=0.6, alpha=0.75))
for nm, colr in zip(fan_cities, fan_cols):
    cx, cy = grid.xy(*fan_cities[nm]); ax.plot(cx, cy, "o", color=colr, ms=4); ax.text(cx + 6, cy, nm, color=colr, fontsize=10)
ax.add_collection(LineCollection([sg for l in coast for sg in render.split_seam(l, W)], colors="#000", linewidths=0.35))
ax.text(0.01, 0.01, "geodesics of the population metric (G2) fanning out from three cities: the straight lines of the humeter world, bending away from dense regions like lensing", transform=ax.transAxes, fontsize=9)
fig.savefig(os.path.join(out, "geodesics.png"), dpi=100); plt.close(fig)
# G2b / L5: humeter distance from a city, by Dijkstra on the grid graph with the tempered metric
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
w_cell = np.exp(u_g)                                  # humeters per pixel step at each cell
idx = np.arange(H * W).reshape(H, W)
rows_, cols_, vals_ = [], [], []
for dy_, dx_, dist in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, np.sqrt(2)), (1, -1, np.sqrt(2))):
    a = idx[max(0, -dy_):H - max(0, dy_), max(0, -dx_):W - max(0, dx_)]
    b = idx[max(0, dy_):H - max(0, -dy_), max(0, dx_):W - max(0, -dx_)]
    wgt = 0.5 * (w_cell.ravel()[a.ravel()] + w_cell.ravel()[b.ravel()]) * dist
    rows_.append(a.ravel()); cols_.append(b.ravel()); vals_.append(wgt)
G = coo_matrix((np.concatenate(vals_), (np.concatenate(rows_), np.concatenate(cols_))), shape=(H * W, H * W)).tocsr()
cities_ll = {"London": (-0.13, 51.5), "Delhi": (77.2, 28.6), "Lagos": (3.4, 6.5), "Sao Paulo": (-46.6, -23.5)}
dist_maps = {}
for nm, (lo, la) in cities_ll.items():
    cx, cy = grid.xy(lo, la); src = int(idx[int(cy), int(cx)])
    d = dijkstra(G, directed=False, indices=src); dist_maps[nm] = d.reshape(H, W)
km_per_px = grid.km_per_px_equator()
fig, ax = fig_geo("distance")
ax.imshow(np.where(land[..., None] > 0, render.LAND, render.OCEAN), extent=(0, W, H, 0), interpolation="nearest")
from contourpy import contour_generator
yy_, xx_ = np.mgrid[0:H, 0:W] + 0.5
for nm, colr in zip(cities_ll, ("#8b0000", "#00468b", "#006400", "#8b008b")):
    D = dist_maps[nm] * km_per_px  # humeter-km
    gen = contour_generator(xx_, yy_, D); levels = np.arange(0, np.nanpercentile(D[np.isfinite(D)], 99), 2000)[1:]
    segs = [np.asarray(sg) for lv in levels for sg in gen.lines(lv) if len(sg) > 3]
    ax.add_collection(LineCollection(segs, colors=colr, linewidths=0.5, alpha=0.8))
    cx, cy = grid.xy(*cities_ll[nm]); ax.plot(cx, cy, "o", color=colr, ms=4); ax.text(cx + 5, cy, nm, color=colr, fontsize=10)
ax.add_collection(LineCollection([sg for l in coast for sg in render.split_seam(l, W)], colors="#000", linewidths=0.35))
ax.text(0.01, 0.01, "humeter distance from four cities (L5/G2): contours every 2000 hm-km; a humeter-kilometre crosses the world-average number of people per km", transform=ax.transAxes, fontsize=9)
fig.savefig(os.path.join(out, "distance.png"), dpi=100); plt.close(fig)
table = {}
for a_, (lo, la) in cities_ll.items():
    row = {}
    for b_, (lo2, la2) in cities_ll.items():
        cx, cy = grid.xy(lo2, la2); row[b_] = float(dist_maps[a_][int(cy), int(cx)] * km_per_px)
    table[a_] = row
json.dump({"width": width, "sigma_km": 60.0, "curvature_abs_p98": float(lim), "curvature_mean_land": float(K[~ocean].mean()), "humeter_km_table": table}, open(os.path.join(out, "metrics.json"), "w"), indent=1)
print("humeter-km London->Delhi %.0f, London->Sao Paulo %.0f, Delhi->Lagos %.0f" % (table["London"]["Delhi"], table["London"]["Sao Paulo"], table["Delhi"]["Lagos"]))
print("wrote", out)
