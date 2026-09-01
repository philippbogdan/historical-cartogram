"""A10/G3: the lumpy Earth. A sphere mesh whose rest edge lengths are humeter lengths (sqrt of the
population density), relaxed as a spring network in 3D: a closed surface whose area is people.
    python src/lumpy_earth.py [rows] -> experiments/geometry_1024/lumpy_earth.png, lumpy_earth.obj"""
import json, os, sys, time
import numpy as np
from scipy import ndimage
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from hc.diffusion import prepare_density
from run import get_lonlat, NCOLS, ROOT, RAW
from render_countries import country_ids, palette

rows = int(sys.argv[1]) if len(sys.argv) > 1 else 96
cols = 2 * rows
grid = prep.Grid("platecarree", cols, 90.0)          # one vertex per cell centre, plate carree
factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * cols)))
counts, bounds = get_lonlat(factor); P, _ = prep.to_grid(counts, bounds, grid)
ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
rho = prepare_density(P, 0.02, 1.5, "periodic", ocean=ocean, ocean_share=0.08)   # gentle: a sculpture, not a proof
rho = ndimage.gaussian_filter(rho, rows / 48, mode=("reflect", "wrap")); rho /= rho.mean()   # ~4 degrees: lumps, not spikes
scale = np.sqrt(rho)                                    # humeter length per unit geographic length
# lattice on the sphere: vertices at cell centres; edges to east and south neighbours (periodic in lon)
lat = np.radians(90 - (np.arange(rows) + 0.5) * 180 / rows); lon = np.radians(-180 + (np.arange(cols) + 0.5) * 360 / cols)
LA, LO = np.meshgrid(lat, lon, indexing="ij")
V = np.stack([np.cos(LA) * np.cos(LO), np.sin(LA), -np.cos(LA) * np.sin(LO)], -1).reshape(-1, 3)
idx = np.arange(rows * cols).reshape(rows, cols)
E = []; L0 = []
def add(a, b):
    E.append((a, b)); L0.append(np.linalg.norm(V[a] - V[b]) * 0.5 * (scale.ravel()[a] + scale.ravel()[b]))
for r in range(rows):
    for c in range(cols):
        add(idx[r, c], idx[r, (c + 1) % cols])
        if r + 1 < rows: add(idx[r, c], idx[r + 1, c]); add(idx[r, c], idx[r + 1, (c + 1) % cols])
E = np.array(E); L0 = np.array(L0); L0 *= np.sqrt(4 * np.pi / (L0 ** 2).sum() * len(L0) / (4 * np.pi) )  # keep total scale sane
# A free spring relaxation buckles and self-intersects (no bending energy), so this first version is a
# star-shaped relief: radius grows with the humeter scale, which keeps the surface readable. The true
# isometric embedding (a bending-regularised solver) is left open in PLAN.md.
rad = 0.62 + 0.38 * (scale / np.percentile(scale, 99.5)).clip(0, 1) ** 0.8
X = V * rad.reshape(-1, 1)
d = X[E[:, 1]] - X[E[:, 0]]; ln = np.linalg.norm(d, axis=1)
print(f"relief globe: radius 0.55 (empty) to 1.0 (densest); mean edge error vs humeter lengths {np.abs(ln - L0).mean():.3f}")
out = os.path.join(ROOT, "experiments", "geometry_1024")
ids, names, _ = country_ids(grid, "110m"); cols_rgb = palette(len(names) + 1); cols_rgb[0] = render.OCEAN
colour = cols_rgb[ids].reshape(-1, 3)
with open(os.path.join(out, "lumpy_earth.obj"), "w") as f:
    for v, c in zip(X, colour): f.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f} {c[0]:.3f} {c[1]:.3f} {c[2]:.3f}\n")
    for r in range(rows - 1):
        for c in range(cols):
            a, b, cc, d = idx[r, c] + 1, idx[r, (c + 1) % cols] + 1, idx[r + 1, (c + 1) % cols] + 1, idx[r + 1, c] + 1
            f.write(f"f {a} {d} {cc}\nf {a} {cc} {b}\n")
# render three views
fig = plt.figure(figsize=(18, 6), dpi=120, facecolor="#05070c")
tri = []
for r in range(rows - 1):
    for c in range(cols):
        a, b, cc, d = idx[r, c], idx[r, (c + 1) % cols], idx[r + 1, (c + 1) % cols], idx[r + 1, c]
        tri.append([a, d, cc]); tri.append([a, cc, b])
tri = np.array(tri); base = colour[tri].mean(1)
n = np.cross(X[tri[:, 1]] - X[tri[:, 0]], X[tri[:, 2]] - X[tri[:, 0]]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
n *= np.sign((n * X[tri].mean(1)).sum(1))[:, None]           # outward
# matplotlib azimuth a looks from plot direction (cos a, sin a); plot axes are (x, z, y) of the model, so
# a = 30 faces lon -30 (the Atlantic), a = -80 faces lon 80 (India), a = 170 faces the Pacific
for k, (az, ttl) in enumerate([(30, "Americas, Europe, Africa"), (-80, "India and China"), (170, "Pacific side")]):
    a, e = np.radians(az - 35), np.radians(45)          # light: from the camera, up and to the left
    light = np.array([np.cos(e) * np.cos(a), np.sin(e), np.cos(e) * np.sin(a)])
    lam = (n @ light).clip(0, 1); fc = base * (0.28 + 0.72 * lam)[:, None]   # Lambert shading, per face
    ax = fig.add_subplot(1, 3, k + 1, projection="3d"); ax.set_facecolor("#05070c")
    surf = ax.plot_trisurf(X[:, 0], X[:, 2], X[:, 1], triangles=tri, shade=False, linewidth=0, antialiased=False)
    surf.set_facecolor(fc); surf.set_edgecolor("none")
    ax.view_init(elev=20, azim=az); ax.set_axis_off(); ax.set_box_aspect((1, 1, 1)); ax.set_title(ttl, color="#ddd")
    ax.set_xlim(-0.7, 0.7); ax.set_ylim(-0.7, 0.7); ax.set_zlim(-0.7, 0.7)
fig.text(0.01, 0.02, "the lumpy Earth (A10, first version): a relief globe whose radius follows the humeter scale sqrt(rho); the isometric embedding with area = people is still open", color="#9ab", fontsize=10)
fig.savefig(os.path.join(out, "lumpy_earth.png"), dpi=120, facecolor=fig.get_facecolor()); plt.close(fig)
print("wrote lumpy_earth.png/.obj")
