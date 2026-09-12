"""Figure 1: one dot per million people, on the map and under the transport map.
    python fig1_dots.py <bench_tag> [people_per_dot=1e6]"""
import sys, numpy as np
from figstyle import *

tag = sys.argv[1] if len(sys.argv) > 1 else "b4096_ot_hero"
per = float(sys.argv[2]) if len(sys.argv) > 2 else 1e6
X, Y, rho, grid, p, m = load_bench(tag)
P = population_grid(grid)
dots = systematic_dots(P, per, seed=20260912)
W = grid.W
coast, borders, grat = vectors(grid, "50m")
dots_w = render.warp_points(dots, X, Y, W)
fig = figure(TEXT_W_MM, TEXT_W_MM / 2 + 4)
axs = fig.subplots(1, 2)
for ax, pts, segs, label in ((axs[0], dots, split_lines(coast, W), "geography"), (axs[1], dots_w, warp_lines(coast, X, Y), "area is people")):
    lines_to_ax(ax, segs, lw=0.25, color="#000000", alpha=0.55, zorder=2)
    ax.scatter(pts[:, 0], pts[:, 1], s=0.55, c=INK, marker="o", linewidths=0, zorder=4, rasterized=False)
    frame_axes(ax, W, grid.H)
    ax.text(0.0, -0.01, label, transform=ax.transAxes, ha="left", va="top", fontsize=8)
save(fig, "fig1_dots")
provenance("fig1_dots", bench_tag=tag, mesh_path=os.path.join(BENCH, tag, "mesh.npz"), people_per_dot=per, n_dots=int(len(dots)),
           dots="systematic sampling along raster order, seed 20260912, uniform jitter within the cell", vectors="Natural Earth 1:50m coastline",
           population="GHS-POP R2023A epoch 2025, 30 arcsec, re-binned to the solver grid", total_people=float(P.sum()))
