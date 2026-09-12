"""Figure 3: Tissot indicatrices (300 km geodesic circles on a 15-degree lattice) through two maps.
    python fig3_tissot.py <ot_tag> <diffusion_tag>"""
import sys, numpy as np
from figstyle import *
from matplotlib.collections import LineCollection

tags = sys.argv[1:3] if len(sys.argv) > 2 else ["b4096_ot_s95", "b4096_d_s95"]
labels = ["optimal transport", "diffusion"]
fig = figure(TEXT_W_MM, TEXT_W_MM / 2 + 4)
axs = fig.subplots(1, 2)
for ax, tag, label in zip(axs, tags, labels):
    X, Y, rho, grid, p, m = load_bench(tag)
    coast, _, _ = vectors(grid, "110m")
    circles = render.tissot_circles(grid, spacing_deg=15, radius_km=300.0, n=96)
    W = grid.W
    polys = []
    for c in circles:
        cc = np.vstack([c, c[:1]])
        wp = render.warp_points(cc, X, Y, W)
        for s in render.split_seam(wp, W, jump=W / 8):
            polys.append(s)
    lines_to_ax(ax, warp_lines(coast, X, Y), lw=0.2, alpha=0.45, zorder=2)
    ax.add_collection(LineCollection(polys, colors=INK, linewidths=0.45, zorder=4, capstyle="round"))
    frame_axes(ax, W, grid.H)
    ax.text(0.0, -0.01, label, transform=ax.transAxes, ha="left", va="top", fontsize=8)
save(fig, "fig3_tissot")
provenance("fig3_tissot", tags=tags, indicatrix="geodesic circles of radius 300 km centred on a 15-degree lon/lat lattice, 96 vertices, warped point by point")
