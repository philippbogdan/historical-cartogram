"""Figure 5: the Delhi window, one dot per 10,000 people, under the global map alone and under the
global map composed with the local 300 m transport solve.
    python fig5_delhi.py [window_name=delhi] [people_per_dot=1e4]"""
import sys, json, os, numpy as np, rasterio
from rasterio.windows import Window
from scipy import ndimage
from figstyle import *
from warp_vectors import frame_mesh  # noqa (uses HC_GLOBAL via experiments/<exp>)

name = sys.argv[1] if len(sys.argv) > 1 else "delhi"
per = float(sys.argv[2]) if len(sys.argv) > 2 else 1e4
d = os.path.join(ROOT, "experiments", "nested", name)
z = np.load(os.path.join(d, "mesh.npz")); prm = json.load(open(os.path.join(d, "params.json"))); met = json.load(open(os.path.join(d, "metrics.json")))
XA, YA = z["X"].astype(np.float64), z["Y"].astype(np.float64); n = int(z["n"]); lon0, lat1, dx = float(z["lon0"]), float(z["lat1"]), float(z["dx"])
tile = os.environ.get("HC_GHS3", os.path.join(RAW, "ghs3ss", "delhi_region_3ss.tif"))
with rasterio.open(tile) as src:
    T3 = src.transform; c0 = int(round((lon0 - T3.c) / T3.a)); r0 = int(round((T3.f - lat1) / T3.a))
    P = src.read(1, window=Window(c0, r0, n, n)).astype(np.float64); P[P < 0] = 0
assert abs(P.sum() - prm["population"]) < 1e-3 * prm["population"], (P.sum(), prm["population"])
# the global map alone: window corners through the global mesh
grid, XG, YG, pg = frame_mesh(prm["global"]); W = grid.W
ys, xs = np.mgrid[0:n + 1, 0:n + 1].astype(np.float64)
def compose(xw, yw):
    lon = lon0 + xw * dx; lat = lat1 - yw * dx; gx, gy = grid.xy(lon, lat)
    wp = render.warp_points(np.stack([gx.ravel(), gy.ravel()], 1), XG, YG, W)
    return wp[:, 0].reshape(xw.shape), wp[:, 1].reshape(xw.shape)
XB, YB = compose(xs, ys)
dots = systematic_dots(P, per, seed=20260912)
def through(Xm, Ym, pts):
    return np.stack([ndimage.map_coordinates(Xm, [pts[:, 1], pts[:, 0]], order=1, mode="nearest"),
                     ndimage.map_coordinates(Ym, [pts[:, 1], pts[:, 0]], order=1, mode="nearest")], 1)
db, da = through(XB, YB, dots), through(XA, YA, dots)
# common extent in global-map pixels
allp = np.vstack([db, da, np.stack([XB.ravel(), YB.ravel()], 1), np.stack([XA.ravel(), YA.ravel()], 1)])
x0, x1 = allp[:, 0].min(), allp[:, 0].max(); y0, y1 = allp[:, 1].min(), allp[:, 1].max()
pad = 0.02 * max(x1 - x0, y1 - y0)
fig = figure(TEXT_W_MM, TEXT_W_MM / 2 + 4)
axs = fig.subplots(1, 2)
for ax, pts, Xm, Ym, label in ((axs[0], db, XB, YB, "global map only"), (axs[1], da, XA, YA, "composed with the local solve")):
    # the window's rim
    rim = np.vstack([np.stack([Xm[0], Ym[0]], 1), np.stack([Xm[:, -1], Ym[:, -1]], 1), np.stack([Xm[-1][::-1], Ym[-1][::-1]], 1), np.stack([Xm[::-1, 0], Ym[::-1, 0]], 1)])
    ax.plot(rim[:, 0], rim[:, 1], color=INK, lw=0.4, ls=(0, (1, 1.5)), zorder=2)
    ax.scatter(pts[:, 0], pts[:, 1], s=0.4, c=INK, linewidths=0, zorder=4)
    ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y1 + pad, y0 - pad); ax.set_aspect("equal"); ax.axis("off")
    ax.text(0.0, -0.01, label, transform=ax.transAxes, ha="left", va="top", fontsize=8)
save(fig, "fig5_delhi")
provenance("fig5_delhi", window=prm, metrics=met, people_per_dot=per, n_dots=int(len(dots)), tile_path=tile, mesh_path=os.path.join(d, "mesh.npz"),
           dots="systematic sampling of the 3 arcsecond raster, seed 20260912; positions mapped through the corner meshes bilinearly")
