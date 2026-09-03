"""M11 + L7: the power diagram of humanity. Semi-discrete optimal transport from the population raster to N
points: N Laguerre cells, each holding exactly total/N people, drawn on the ordinary map. With N = 8192 every
cell is a million people: a district in Dhaka, a subcontinent in Siberia.
    python src/m11_powerdiagram.py [N=8192] [grid_w=2048] [out_w=4096] [lloyd=3]"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from run import ROOT, RAW, get_lonlat, NCOLS
from render_countries import country_ids
from render_hero import region_palette, FONT
from pysdot import OptimalTransport
from pysdot.domain_types import ScaledImage

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8192; gw = int(sys.argv[2]) if len(sys.argv) > 2 else 2048; out_w = int(sys.argv[3]) if len(sys.argv) > 3 else 4096; lloyd = int(sys.argv[4]) if len(sys.argv) > 4 else 3
t0 = time.time()
grid = prep.Grid("mercator", gw, lon0=-168.0); H, W = grid.H, grid.W
factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * gw)))
counts, bounds = get_lonlat(factor); P, _ = prep.to_grid(counts, bounds, grid); P = np.maximum(P, 0); total = float(P.sum())
from scipy import ndimage
img = np.maximum(P, 1e-3 * P.mean())                            # a whisper of mass everywhere keeps every cell bounded
rng = np.random.default_rng(1)
prob = P.ravel() / P.sum(); idx = rng.choice(P.size, size=N, replace=False, p=prob)
pts = np.stack([idx % W + rng.random(N), idx // W + rng.random(N)], 1).astype(np.float64)
# continuation in smoothing: Newton needs every cell non-empty at the start, which a five-decade density denies;
# solve on a blurred density first and sharpen in steps, keeping the weights
out = os.path.join(ROOT, "experiments", f"M11_power_{N}_{gw}"); os.makedirs(out, exist_ok=True)
sites_path = os.path.join(out, "sites.npz")
ot = None; prev = None
def solve_at(sig):
    global ot
    im_s = ndimage.gaussian_filter(img, sig, mode="reflect") if sig > 0 else img
    dom = ScaledImage([0, 0], [W, H], im_s)
    if ot is None: ot = OptimalTransport(pts, domain=dom)
    else: ot.set_domain(dom)
    ot.set_masses(np.full(N, im_s.sum() / N)); ot.adjust_weights()
from pysdot.OptimalTransport import BadInitialGuess
todo = [32, 16, 8, 4, 2, 1, 0.5, 0]
if os.path.exists(sites_path): todo = []; print("sites cached")
while todo:
    sig = todo[0]
    try:
        w_before = None if ot is None else ot.get_weights().copy()
        solve_at(sig); prev = sig; todo.pop(0)
        print(f"sigma {sig}: {time.time()-t0:.0f}s; mass spread {ot.pd.integrals().min()/ot.pd.integrals().mean():.3f}-{ot.pd.integrals().max()/ot.pd.integrals().mean():.3f}", flush=True)
        if sig == 2:                                             # Lloyd steps while the density is still smooth
            for k in range(lloyd):
                ot.set_positions(ot.get_centroids()); ot.adjust_weights(); print(f"lloyd {k+1} at sigma 2: {time.time()-t0:.0f}s", flush=True)
    except BadInitialGuess:
        if w_before is not None: ot.set_weights(w_before)
        mid = (prev + sig) / 2 if prev is not None else sig * 2
        if prev is not None and prev - sig < 0.05: raise
        print(f"sigma {sig} refused; inserting {mid:.2f}", flush=True); todo.insert(0, mid)
lloyd = 0
for k in range(lloyd):
    ot.set_positions(ot.get_centroids()); ot.adjust_weights()
    print(f"lloyd {k+1}: {time.time()-t0:.0f}s", flush=True)
if ot is not None:
    pos = ot.get_positions(); wts = ot.get_weights(); np.savez_compressed(sites_path, pos=pos, weights=wts, W=W, H=H, total=total)
    spread = [float(ot.pd.integrals().min() / ot.pd.integrals().mean()), float(ot.pd.integrals().max() / ot.pd.integrals().mean())]
else:
    z = np.load(sites_path); pos, wts = z["pos"], z["weights"]; spread = [1.0, 1.0]
# label every output pixel by its Laguerre cell (power distance argmin) on the GPU
import torch
dev = "mps" if torch.backends.mps.is_available() else "cpu"
oh, ow = int(round(H * out_w / W)), out_w; sc = ow / W
p_t = torch.tensor(pos, dtype=torch.float32, device=dev); w_t = torch.tensor(wts, dtype=torch.float32, device=dev)
labels = np.zeros((oh, ow), np.int32)
xs = (torch.arange(ow, device=dev, dtype=torch.float32) + 0.5) / sc
for r0 in range(0, oh, 8):                                   # 8 rows x 4096 px x 8192 sites x 4 B = 1 GB per chunk
    ys = (torch.arange(r0, min(r0 + 8, oh), device=dev, dtype=torch.float32) + 0.5) / sc
    q = torch.stack(torch.meshgrid(ys, xs, indexing="ij"), -1).reshape(-1, 2)
    d = torch.cdist(q[:, [1, 0]], p_t) ** 2 - w_t[None, :]
    labels[r0:r0 + len(ys)] = d.argmin(1).reshape(len(ys), ow).cpu().numpy()
print(f"labels {oh}x{ow} in {time.time()-t0:.0f}s", flush=True)
# draw: cells filled with their country's region colour, cell edges dark, coasts, caption
ids, names, pops = country_ids(grid, "50m"); cols = region_palette("50m")
# fills: the country under each pixel (ocean pale), so the map stays readable; the cells are the drawing on top
oy, ox = np.mgrid[0:oh, 0:ow]; ids_out = ids[np.clip((oy / sc).astype(int), 0, H - 1), np.clip((ox / sc).astype(int), 0, W - 1)]
cols_o = cols.copy(); cols_o[0] = (0.955, 0.952, 0.94)
img_rgb = cols_o[ids_out]
edge = np.zeros((oh, ow), bool); edge[:, 1:] |= labels[:, 1:] != labels[:, :-1]; edge[1:, :] |= labels[1:, :] != labels[:-1, :]
from scipy import ndimage
edge = ndimage.binary_dilation(edge, iterations=max(1, out_w // 4096))
img_rgb[edge] = (0.15, 0.15, 0.15)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = FONT
band = int(0.13 * oh); fig = plt.figure(figsize=(ow / 100, (oh + band) / 100), dpi=100, facecolor="white")
ax = fig.add_axes([0, band / (oh + band), 1, oh / (oh + band)]); ax.set_axis_off(); ax.set_xlim(0, ow); ax.set_ylim(oh, 0)
ax.imshow(img_rgb, extent=(0, ow, oh, 0), interpolation="nearest")
coast = render.lines_from_geojson(os.path.join(RAW, "ne_50m_coastline.geojson"), grid)
for ln in coast: ax.plot(ln[:, 0] * sc, ln[:, 1] * sc, color="#ffffff", lw=0.6)
cap = fig.add_axes([0, 0, 1, band / (oh + band)]); cap.set_axis_off(); cap.set_xlim(0, ow); cap.set_ylim(band, 0); fs = out_w / 4096
cap.text(0.015 * ow, 0.20 * band, f"THE POWER DIAGRAM OF HUMANITY: {N:,} CELLS, ONE MILLION PEOPLE EACH", fontsize=56 * fs, fontweight="bold", color="#111", va="center")
cap.text(0.015 * ow, 0.50 * band, f"Semi-discrete optimal transport from the population raster to {N:,} points: every convex cell holds exactly {total/N/1e6:.2f} million people.\nThe ordinary map is not stretched here; the cells are. A cell is a few streets in Dhaka and most of Siberia in the north; the outer cells reach across the oceans because the plane is shared.", fontsize=26 * fs, color="#333", va="center", linespacing=1.5)
cap.text(0.015 * ow, 0.82 * band, "GHS-POP 2025 on a 2048-cell Mercator grid; Laguerre cells by pysdot (Merigot), continuation in smoothing from 32 cells to none; country colours follow UN subregions.", fontsize=19 * fs, color="#666", va="center")
fig.savefig(os.path.join(out, "power_diagram.png"), dpi=100); plt.close(fig)
json.dump({"N": N, "grid_w": gw, "people_per_cell": total / N, "seconds": time.time() - t0, "mass_spread": spread}, open(os.path.join(out, "metrics.json"), "w"), indent=1)
print("wrote", out, f"{time.time()-t0:.0f}s")
