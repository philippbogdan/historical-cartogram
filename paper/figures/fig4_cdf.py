"""Figure 4: population-weighted cumulative distributions of local rotation, anisotropy and displacement.
    python fig4_cdf.py <ot_tag> <diffusion_tag>"""
import sys, json, numpy as np
from figstyle import *
sys.path.insert(0, SRC)
from hc import layers

tags = sys.argv[1:3] if len(sys.argv) > 2 else ["b4096_ot_s95", "b4096_d_s95"]
labels = ["optimal transport", "diffusion"]
styles = ["solid", (0, (1.0, 1.4))]

def wcdf(v, w):
    o = np.argsort(v); return v[o], np.cumsum(w[o]) / w.sum()

fig = figure(TEXT_W_MM, 52)
axs = fig.subplots(1, 3)
stats = {}
for tag, label, ls in zip(tags, labels, styles):
    X, Y, rho, grid, p, m = load_bench(tag, repaired=False)
    A = quad_areas(X, Y); ok = A > 0; w = rho[ok]
    _, twist = layers.stretch_and_twist(X, Y)
    dxu = (X[:-1, 1:] - X[:-1, :-1] + X[1:, 1:] - X[1:, :-1]) / 2; dyu = (Y[:-1, 1:] - Y[:-1, :-1] + Y[1:, 1:] - Y[1:, :-1]) / 2
    dxv = (X[1:, :-1] - X[:-1, :-1] + X[1:, 1:] - X[:-1, 1:]) / 2; dyv = (Y[1:, :-1] - Y[:-1, :-1] + Y[1:, 1:] - Y[:-1, 1:]) / 2
    a, b, c, d = dxu, dxv, dyu, dyv
    s1 = np.sqrt((a - d) ** 2 + (b + c) ** 2) / 2; s2 = np.sqrt((a + d) ** 2 + (b - c) ** 2) / 2
    aniso = (s2 + s1) / np.maximum(np.abs(s2 - s1), 1e-12)
    ys, xs = np.mgrid[0:X.shape[0], 0:X.shape[1]]
    disp = np.hypot(X - xs, Y - ys); dc_ = (disp[:-1, :-1] + disp[:-1, 1:] + disp[1:, :-1] + disp[1:, 1:]) / 4
    for ax, v, xl in ((axs[0], np.abs(twist[ok]), None), (axs[1], aniso[ok], None), (axs[2], dc_[ok] / grid.W, None)):
        x, y = wcdf(v, w); ax.plot(x, y, color=INK, ls=ls, lw=0.9, label=label)
    stats[tag] = {"twist_p50": float(np.interp(0.5, *wcdf(np.abs(twist[ok]), w)[::-1])), "aniso_p50": float(np.interp(0.5, *wcdf(aniso[ok], w)[::-1]))}
axs[0].set(xlabel="local rotation, degrees", ylabel="population share", xlim=(0, 60), ylim=(0, 1))
axs[1].set(xlabel="anisotropy, ratio of principal stretches", xscale="log", xlim=(1, 100), ylim=(0, 1))
axs[2].set(xlabel="displacement, fraction of frame width", xlim=(0, 0.6), ylim=(0, 1))
for ax in axs: ax.set_yticks([0, 0.5, 1])
axs[2].legend(loc="lower right")
save(fig, "fig4_cdf")
provenance("fig4_cdf", tags=tags, weights="population per source cell (the smoothed, floored density used by the solver)", cells="raw meshes, cells with positive area only", stats=stats)
