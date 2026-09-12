"""Figure 2: coastlines, borders and the 15-degree graticule through two maps of the same density.
    python fig2_lineart.py <ot_tag> <diffusion_tag>"""
import sys, numpy as np
from figstyle import *

tags = sys.argv[1:3] if len(sys.argv) > 2 else ["b4096_ot_s95", "b4096_d_s95"]
labels = ["optimal transport", "diffusion"]
fig = figure(TEXT_W_MM, TEXT_W_MM / 2 + 4)
axs = fig.subplots(1, 2)
for ax, tag, label in zip(axs, tags, labels):
    X, Y, rho, grid, p, m = load_bench(tag)
    coast, borders, grat = vectors(grid, "50m")
    lines_to_ax(ax, warp_lines(grat, X, Y), lw=0.3, ls=(0, (0.8, 1.6)), alpha=0.6, zorder=1)
    lines_to_ax(ax, warp_lines(borders, X, Y), lw=0.18, alpha=0.7, zorder=2)
    lines_to_ax(ax, warp_lines(coast, X, Y), lw=0.4, zorder=3)
    frame_axes(ax, grid.W, grid.H)
    ax.text(0.0, -0.01, label, transform=ax.transAxes, ha="left", va="top", fontsize=8)
save(fig, "fig2_lineart")
provenance("fig2_lineart", tags=tags, vectors="Natural Earth 1:50m coastline and admin-0 borders; 15-degree graticule", note="folds repaired before drawing (population-aware smoothing of the displacement in empty cells)")
