"""Figure 6: the equal-population power diagram: N Laguerre cells of the population measure on the Mercator frame.
    python fig6_power.py [experiment=M11_power_8192_2048]"""
import sys, os, json, numpy as np
from figstyle import *
from pysdot import PowerDiagram
from pysdot.domain_types import ConvexPolyhedraAssembly
from matplotlib.collections import LineCollection

exp = sys.argv[1] if len(sys.argv) > 1 else "M11_power_8192_2048"
d = os.path.join(ROOT, "experiments", exp)
z = np.load(os.path.join(d, "sites.npz")); pos, wts, W, H = z["pos"], z["weights"], int(z["W"]), int(z["H"])
met = json.load(open(os.path.join(d, "metrics.json")))
dom = ConvexPolyhedraAssembly(); dom.add_box([0, 0], [W, H])
pd = PowerDiagram(positions=pos, weights=wts, domain=dom)
offsets, xy = pd.cell_polyhedra()
segs = []
for a, b in zip(offsets[:-1], offsets[1:]):
    ring = xy[a:b]
    if len(ring) >= 3: segs.append(np.vstack([ring, ring[:1]]))
grid = prep.Grid("mercator", W, lon0=-168.0)
coast, _, _ = vectors(grid, "110m")
fig = figure(TEXT_W_MM, TEXT_W_MM + 4)
ax = fig.add_subplot(111)
lines_to_ax(ax, split_lines(coast, W), lw=0.35, ls=(0, (0.6, 1.2)), alpha=0.9, zorder=2)
ax.add_collection(LineCollection(segs, colors=INK, linewidths=0.18, zorder=3))
frame_axes(ax, W, H)
save(fig, "fig6_power")
provenance("fig6_power", experiment=exp, sites_path=os.path.join(d, "sites.npz"), metrics=met, n_cells=int(len(pos)),
           cells="Laguerre cells of the semi-discrete optimal transport from the 2048-cell population grid to the sites; polygons from pysdot")
