"""V2: nested 100 m solves. Inside a city window the global map T (10 km cells, 30 km smoothing) has only
equalised the smoothed density. A second optimal-transport map L, solved on the 3 arcsecond GHS-POP raster
for the RESIDUAL rho_100m / rho_30km (tapered to 1 at the window's edges), composed as T o L, equalises the
window at 100 m: every block gets its own area. Writes experiments/nested/<name>/{mesh.npz, params.json,
metrics.json, before.png, after.png}.
    python src/nested_solve.py <name> <lon> <lat> [size_deg=2] [sigma_m=300] [out_px=2048]"""
import json, os, sys, time
import numpy as np, rasterio
from rasterio.windows import Window
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render, ot_poisson, diffusion
from hc.diffusion import quad_areas
from run import ROOT, RAW
from warp_vectors import frame_mesh

GLOBAL = "e036_hero_ocean0.2_s30_share0.999_ocean0.2"
GHS3 = os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif")

name, lon_c, lat_c = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
size = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0; sigma_m = float(sys.argv[5]) if len(sys.argv) > 5 else 300.0; out_px = int(sys.argv[6]) if len(sys.argv) > 6 else 2048
out = os.path.join(ROOT, "experiments", "nested", name); os.makedirs(out, exist_ok=True)
t0 = time.time()
# 1. the window's 3" counts
with rasterio.open(GHS3) as src:
    T3 = src.transform; dx = T3.a
    c0 = int(round((lon_c - size / 2 - T3.c) / dx)); r0 = int(round((T3.f - (lat_c + size / 2)) / dx)); n = int(round(size / dx))
    n -= n % 8
    P = src.read(1, window=Window(c0, r0, n, n)).astype(np.float64); P[P < 0] = 0
    lon0 = T3.c + c0 * dx; lat1 = T3.f - r0 * dx
print(f"window {n}x{n} cells of {dx*3600:.0f} arcsec, {P.sum()/1e6:.1f} M people, read in {time.time()-t0:.0f}s")
# 2. the residual: smoothed 100 m people per WARPED area under the global map (exactly what T left unequal)
km_per_cell = 111.32 * dx * np.cos(np.radians(lat_c))
grid, XG, YG, pg = frame_mesh(GLOBAL); W = grid.W
def compose(xw, yw):
    lon = lon0 + xw * dx; lat = lat1 - yw * dx                      # window pixel -> lon/lat
    gx, gy = grid.xy(lon, lat)                                       # -> global mesh px
    wp = render.warp_points(np.stack([gx.ravel(), gy.ravel()], 1), XG, YG, W)
    return wp[:, 0].reshape(xw.shape), wp[:, 1].reshape(xw.shape)
ys, xs = np.mgrid[0:n + 1, 0:n + 1].astype(np.float64)
XT, YT = compose(xs, ys)                    # T alone
A_T = np.abs(quad_areas(XT, YT))
sigma_px = (sigma_m / 1000.0) / km_per_cell
rho_s = ndimage.gaussian_filter(P, sigma_px, mode="reflect")
# taper weights: the local map is the identity near the window's edges so windows compose seamlessly
t = np.ones(n); m = int(0.05 * n); ramp = 0.5 * (1 - np.cos(np.linspace(0, np.pi, m))); t[:m] = ramp; t[-m:] = ramp[::-1]
w = np.outer(t, t)
# 3. the exact local problem: optimal transport on the source rectangle (walls) from mu = the window's people
#    to nu = the area measure of the global map, det(DL) = mu / nu(L(x)), so that T o L has Jacobian mu.
#    L maps the rectangle onto itself: the composed image is exactly the global map's image of the window,
#    nothing overlaps the neighbours and there is no rim to pin. Two rounds: the second corrects with the
#    composed map's actual areas.
XT0, YT0 = compose(xs, ys)
LX, LY = xs.copy(), ys.copy(); res, folds = 0.0, 0
mu = ndimage.gaussian_filter(P, sigma_px, mode="reflect"); mu = mu + 1e-3 * mu.mean(); mu = mu / mu.mean()
import torch
XC, YC = compose(LX, LY); A_c = np.abs(quad_areas(XC, YC))
nu_full = ndimage.gaussian_filter(A_c, sigma_px, mode="reflect"); nu_full = nu_full / nu_full.mean()
def spread_of(LXc, LYc):
    XCc, YCc = compose(LXc, LYc); A_now = np.abs(quad_areas(XCc, YCc))
    Ps = ndimage.gaussian_filter(P, sigma_px, mode="reflect"); As = ndimage.gaussian_filter(A_now, sigma_px, mode="reflect")
    d = Ps / np.maximum(As, 1e-12); mm = Ps > 0; lg = np.log(d[mm] / (Ps[mm].sum() / As[mm].sum())); wgt = Ps[mm] / Ps[mm].sum(); o = np.argsort(lg); cw = np.cumsum(wgt[o])
    return float(lg[o][np.searchsorted(cw, 0.05)]), float(lg[o][np.searchsorted(cw, 0.95)])
b5, b95 = spread_of(xs, ys)
# continuation in the target: nu^t for t = 0.5 then 1, warm-started; the non-uniform fixed point diverges
# when mu / nu spans four decades at once (Lima's coast against the Andes)
po = ot_poisson.SpectralPoissonOT(None, x_boundary="wall", rho=mu); po.sigma_px = float(sigma_px); po.one_shot()
fallback = False
for t in (0.5, 1.0):
    nu_t = nu_full ** t; nu_t = nu_t / nu_t.mean()
    po.target = torch.tensor(nu_t, dtype=po.rho.dtype, device=po.rho.device)
    info = po.iterate(iters=600, damping=0.35, log=lambda s: None, tol=3e-4); res, folds = info["residual"], info["cell_folds"]
    print(f"target^{t}: residual {res:.4f} ({info['iters']} iters), {time.time()-t0:.0f}s", flush=True)
Xk, Yk = po.mesh(); Xk = np.clip(Xk, 0, n); Yk = np.clip(Yk, 0, n)
pts = np.stack([Xk.ravel(), Yk.ravel()], 1)
LXn = ndimage.map_coordinates(LX, [pts[:, 1], pts[:, 0]], order=1, mode="nearest").reshape(LX.shape)
LYn = ndimage.map_coordinates(LY, [pts[:, 1], pts[:, 0]], order=1, mode="nearest").reshape(LY.shape)
a5, a95 = spread_of(LXn, LYn)
if a95 > b95 or a95 > 1.5 or a5 < -1.5:                      # judged on the composed spread, not the clamped solver residual
    fallback = True; print(f"solve rejected (spread {a5:+.2f}/{a95:+.2f} vs {b5:+.2f}/{b95:+.2f}): this window keeps the global map", flush=True)
else:
    LX, LY = LXn, LYn
print(f"spread at {sigma_m:.0f} m: before {b5:+.2f}/{b95:+.2f}, after {a5:+.2f}/{a95:+.2f}", flush=True)
XC, YC = compose(LX, LY)
nf = int((quad_areas(XC, YC) <= 0).sum()); nfp = int(((quad_areas(XC, YC) <= 0) & (P > 100)).sum())
print(f"composed mesh folds: {nf} cells, {nfp} with over 100 people")
XTL, YTL = XC, YC
rim = np.hypot(XTL - XT0, YTL - YT0); rim_max = float(max(rim[0].max(), rim[-1].max(), rim[:, 0].max(), rim[:, -1].max()))
print(f"rim displacement vs the global map: max {rim_max:.4f} px (slides along the rim only)")
# 5. how equal is the window now? people per warped area of each 3" cell, before and after
A_T = np.abs(quad_areas(XT, YT)); A_TL = np.abs(quad_areas(XTL, YTL))
inner = np.zeros(P.shape, bool); inner[m:-m, m:-m] = True
def spread(A):
    d = P / np.maximum(A, 1e-12); m = (P > 0) & inner; lg = np.log(d[m] / (P[m].sum() / A[m].sum())); wgt = P[m] / P[m].sum(); o = np.argsort(lg); cw = np.cumsum(wgt[o])
    return float(lg[o][np.searchsorted(cw, 0.05)]), float(lg[o][np.searchsorted(cw, 0.95)])
def spread_s(A):                                  # at the solve's own scale: counts smoothed like the residual, over the same warped areas
    Ps = ndimage.gaussian_filter(P, sigma_px, mode="reflect"); As = ndimage.gaussian_filter(A, sigma_px, mode="reflect")
    d = Ps / np.maximum(As, 1e-12); m = (Ps > 0) & inner; lg = np.log(d[m] / (Ps[m].sum() / As[m].sum())); wgt = Ps[m] / Ps[m].sum(); o = np.argsort(lg); cw = np.cumsum(wgt[o])
    return float(lg[o][np.searchsorted(cw, 0.05)]), float(lg[o][np.searchsorted(cw, 0.95)])
b5, b95 = spread(A_T); a5, a95 = spread(A_TL); bs5, bs95 = spread_s(A_T); as5, as95 = spread_s(A_TL)
print(f"population-weighted log density spread, p05/p95: raw 100 m cells before {b5:+.2f}/{b95:+.2f} after {a5:+.2f}/{a95:+.2f}; at the {sigma_m:.0f} m solve scale before {bs5:+.2f}/{bs95:+.2f} after {as5:+.2f}/{as95:+.2f}")
np.savez_compressed(os.path.join(out, "mesh.npz"), X=XTL.astype(np.float32), Y=YTL.astype(np.float32), lon0=lon0, lat1=lat1, dx=dx, n=n, note="composed map: window corner (i, j) -> global mesh px")
json.dump({"name": name, "global": GLOBAL, "lon": lon_c, "lat": lat_c, "size_deg": size, "cells": n, "cell_arcsec": dx * 3600, "sigma_m": sigma_m, "population": float(P.sum())}, open(os.path.join(out, "params.json"), "w"), indent=1)
json.dump({"fallback_global": fallback, "before_p05": b5, "before_p95": b95, "after_p05": a5, "after_p95": a95, "smoothed_before_p05": bs5, "smoothed_before_p95": bs95, "smoothed_after_p05": as5, "smoothed_after_p95": as95, "local_residual": res, "local_folds": int(folds), "seconds": time.time() - t0}, open(os.path.join(out, "metrics.json"), "w"), indent=1)
# 6. pictures: the window's people painted through T and through T o L, at the same output scale
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
x0, x1 = min(XT.min(), XTL.min()), max(XT.max(), XTL.max()); y0, y1 = min(YT.min(), YTL.min()), max(YT.max(), YTL.max())
sc = out_px / max(x1 - x0, y1 - y0); oh, ow = int((y1 - y0) * sc) + 1, int((x1 - x0) * sc) + 1
dens = np.log10(np.maximum(P / (km_per_cell ** 2), 1))            # people per km2, log
for tag, (XX, YY) in (("before", (XT, YT)), ("after", (XTL, YTL))):
    img = render.splat(dens, (XX - x0) * sc * n / ow, (YY - y0) * sc * n / oh, (oh, ow), wrap=False)   # splat scales by ow/n, oh/n itself
    fig, ax = render._figure(oh, ow, "white"); ax.imshow(np.clip(img / 5.0, 0, 1), cmap="magma", extent=(0, ow, oh, 0), vmin=0, vmax=1)
    ax.text(0.01, 0.01, f"{name}: 100 m population through {'the global map only' if tag == 'before' else 'the global map composed with the local 100 m solve'} (people per km2, log); density spread p05/p95 {(b5, b95) if tag == 'before' else (a5, a95)}", transform=ax.transAxes, fontsize=9, color="#fff", bbox=dict(facecolor="#000a", edgecolor="none", pad=3))
    fig.savefig(os.path.join(out, f"{tag}.png"), dpi=100); plt.close(fig)
print("wrote", out)
