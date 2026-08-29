"""Rendering through a warp: rasters by forward splatting (R2), vectors by point warping,
metric grid and Tissot ellipses (A11). Works at any resolution; no pcolormesh."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from scipy import ndimage

from .diffusion import quad_areas
from .prep import R_EARTH_KM

LAND = np.array([0xd9, 0xd2, 0xc3]) / 255
OCEAN = np.array([0xa8, 0xc4, 0xd8]) / 255


# ---------------------------------------------------------------- rasters
def splat(values, X, Y, out_hw, wrap=True, ss_max=16, weights=None):
    """Forward-warp `values` (H, W) through the corner mesh into an image of shape out_hw.
    GPU (torch, MPS) when available, numpy otherwise. Weighted mean of what lands on each pixel."""
    try:
        import torch  # noqa: F401
        return _splat_torch(values, X, Y, out_hw, wrap=wrap, ss_max=min(ss_max, 12), weights=weights)
    except ImportError:
        return _splat_numpy(values, X, Y, out_hw, wrap=wrap, ss_max=ss_max, weights=weights)


def _fill_holes(img):
    if np.isnan(img).any():
        _, (iy, ix) = ndimage.distance_transform_edt(np.isnan(img), return_indices=True)
        img = img[iy, ix]
    return img


def _splat_torch(values, X, Y, out_hw, wrap=True, ss_max=12, weights=None):
    import torch
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    H, W = values.shape
    oh, ow = out_hw
    sx, sy = ow / W, oh / H
    Xt = torch.tensor(X, dtype=torch.float32, device=dev)
    Yt = torch.tensor(Y, dtype=torch.float32, device=dev)
    V = torch.tensor(np.asarray(values, np.float32), device=dev)
    Wt = torch.ones_like(V) if weights is None else torch.tensor(np.asarray(weights, np.float32), device=dev)
    x0, x1, x2, x3 = Xt[:-1, :-1], Xt[:-1, 1:], Xt[1:, 1:], Xt[1:, :-1]
    y0, y1, y2, y3 = Yt[:-1, :-1], Yt[:-1, 1:], Yt[1:, 1:], Yt[1:, :-1]
    A = (0.5 * ((x0 * y1 - x1 * y0) + (x1 * y2 - x2 * y1) + (x2 * y3 - x3 * y2) + (x3 * y0 - x0 * y3))).abs() * sx * sy
    k = torch.clamp(torch.ceil(torch.sqrt(A)), 1, ss_max).to(torch.int64)
    acc = torch.zeros(oh * ow, device=dev)
    wacc = torch.zeros(oh * ow, device=dev)
    for kk in torch.unique(k).tolist():
        ii, jj = torch.nonzero(k == kk, as_tuple=True)
        x00, x01, x10, x11 = Xt[ii, jj], Xt[ii, jj + 1], Xt[ii + 1, jj], Xt[ii + 1, jj + 1]
        y00, y01, y10, y11 = Yt[ii, jj], Yt[ii, jj + 1], Yt[ii + 1, jj], Yt[ii + 1, jj + 1]
        v = V[ii, jj]
        w = Wt[ii, jj] / (kk * kk)
        for a in range(kk):
            for b in range(kk):
                u, t = (a + 0.5) / kk, (b + 0.5) / kk
                x = (1 - u) * (1 - t) * x00 + u * (1 - t) * x01 + (1 - u) * t * x10 + u * t * x11
                y = (1 - u) * (1 - t) * y00 + u * (1 - t) * y01 + (1 - u) * t * y10 + u * t * y11
                px = torch.floor(x * sx).to(torch.int64)
                px = px % ow if wrap else px.clamp(0, ow - 1)
                py = torch.floor(y * sy).to(torch.int64).clamp(0, oh - 1)
                idx = py * ow + px
                acc.index_put_((idx,), v * w, accumulate=True)
                wacc.index_put_((idx,), w, accumulate=True)
    img = torch.where(wacc > 0, acc / torch.clamp(wacc, min=1e-30), torch.full_like(acc, float("nan")))
    return _fill_holes(img.reshape(oh, ow).cpu().numpy().astype(np.float64))


def _splat_numpy(values, X, Y, out_hw, wrap=True, ss_max=16, weights=None):
    """Forward-warp per-cell `values` (H, W) through the corner mesh X, Y ((H+1), (W+1))
    into an image of shape out_hw. Big cells are supersampled so they leave no holes;
    the result is the weighted mean of the values that land on each output pixel."""
    H, W = values.shape
    oh, ow = out_hw
    sx, sy = ow / W, oh / H
    A = np.abs(quad_areas(X, Y)) * sx * sy
    n = np.clip(np.ceil(np.sqrt(A)).astype(int), 1, ss_max)
    acc = np.zeros(oh * ow)
    wacc = np.zeros(oh * ow)
    wts = np.ones_like(values, dtype=np.float64) if weights is None else weights
    for k in np.unique(n):
        ii, jj = np.nonzero(n == k)
        x00, x01, x10, x11 = X[ii, jj], X[ii, jj + 1], X[ii + 1, jj], X[ii + 1, jj + 1]
        y00, y01, y10, y11 = Y[ii, jj], Y[ii, jj + 1], Y[ii + 1, jj], Y[ii + 1, jj + 1]
        v = values[ii, jj]
        wv = wts[ii, jj] / (k * k)
        for a in range(k):
            for b in range(k):
                u, t = (a + 0.5) / k, (b + 0.5) / k
                x = (1 - u) * (1 - t) * x00 + u * (1 - t) * x01 + (1 - u) * t * x10 + u * t * x11
                y = (1 - u) * (1 - t) * y00 + u * (1 - t) * y01 + (1 - u) * t * y10 + u * t * y11
                px = np.floor(x * sx).astype(int)
                px = px % ow if wrap else np.clip(px, 0, ow - 1)
                py = np.clip(np.floor(y * sy).astype(int), 0, oh - 1)
                idx = py * ow + px
                acc += np.bincount(idx, weights=v * wv, minlength=oh * ow)
                wacc += np.bincount(idx, weights=wv, minlength=oh * ow)
    img = np.full(oh * ow, np.nan)
    hit = wacc > 0
    img[hit] = acc[hit] / wacc[hit]
    return _fill_holes(img.reshape(oh, ow))


# ---------------------------------------------------------------- vectors
def _iter_geoms(geojson_path):
    with open(geojson_path) as f:
        gj = json.load(f)
    for feat in gj["features"]:
        yield feat["geometry"]


def _densify(pts, max_seg=1.0):
    out = [pts[:1]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = int(np.ceil(np.hypot(*(b - a)) / max_seg))
        out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None] if n > 1 else b[None])
    return np.vstack(out)


def lines_from_geojson(geojson_path, grid):
    lines = []
    for g in _iter_geoms(geojson_path):
        t = g["type"]
        parts = ([g["coordinates"]] if t == "LineString" else g["coordinates"] if t in ("MultiLineString", "Polygon")
                 else [r for poly in g["coordinates"] for r in poly] if t == "MultiPolygon" else [])
        for p in parts:
            c = np.asarray(p, np.float64)
            x, y = grid.xy(c[:, 0], c[:, 1])
            lines.append(_densify(np.stack([x, y], 1)))
    return lines


def land_mask(geojson_path, grid):
    from rasterio import features
    from rasterio.transform import Affine
    def tf(ring):
        c = np.asarray(ring, np.float64)
        x, y = grid.xy(c[:, 0], c[:, 1])
        return np.stack([x, y], 1).tolist()
    shapes = []
    for g in _iter_geoms(geojson_path):
        if g["type"] == "Polygon":
            shapes.append(({"type": "Polygon", "coordinates": [tf(r) for r in g["coordinates"]]}, 1))
        elif g["type"] == "MultiPolygon":
            shapes.append(({"type": "MultiPolygon", "coordinates": [[tf(r) for r in poly] for poly in g["coordinates"]]}, 1))
    return features.rasterize(shapes, out_shape=(grid.H, grid.W), transform=Affine.identity(), fill=0, dtype="uint8")


def graticule(grid, step=15):
    lines = []
    for lon in np.arange(-180, 181, step):
        lat = np.linspace(-grid.lat_cut, grid.lat_cut, 400)
        x, y = grid.xy(np.full_like(lat, lon), lat)
        lines.append(np.stack([x, y], 1))
    for lat in np.arange(-75, 76, step):
        lon = np.linspace(-180, 180, 800)
        x, y = grid.xy(lon, np.full_like(lon, lat))
        lines.append(np.stack([x, y], 1))
    return lines


def metric_grid(grid, cell_km=100.0):
    """A11: equal-area cells of cell_km x cell_km (exact area everywhere, square at the equator)."""
    d = cell_km / R_EARTH_KM
    lines = []
    for lon in np.degrees(np.arange(-np.pi, np.pi + 1e-9, d)):
        lat = np.linspace(-grid.lat_cut, grid.lat_cut, 200)
        x, y = grid.xy(np.full_like(lat, lon), lat)
        lines.append(np.stack([x, y], 1))
    for s in np.arange(-1.0, 1.0 + 1e-9, d):
        lat = np.degrees(np.arcsin(np.clip(s, -1, 1)))
        if abs(lat) > grid.lat_cut:
            continue
        lon = np.linspace(-180, 180, 1440)
        x, y = grid.xy(lon, np.full_like(lon, lat))
        lines.append(np.stack([x, y], 1))
    return lines


def tissot_circles(grid, spacing_deg=15, radius_km=300.0, n=48):
    """Small circles of geodesic radius radius_km around a lon/lat lattice, as pixel polygons."""
    delta = radius_km / R_EARTH_KM
    polys = []
    for lat1 in np.radians(np.arange(-75, 76, spacing_deg)):
        for lon1 in np.radians(np.arange(-180, 180, spacing_deg)):
            th = np.linspace(0, 2 * np.pi, n, endpoint=False)
            lat2 = np.arcsin(np.sin(lat1) * np.cos(delta) + np.cos(lat1) * np.sin(delta) * np.cos(th))
            lon2 = lon1 + np.arctan2(np.sin(th) * np.sin(delta) * np.cos(lat1), np.cos(delta) - np.sin(lat1) * np.sin(lat2))
            x, y = grid.xy(np.degrees(lon2), np.degrees(lat2))
            polys.append(np.stack([x, y], 1))
    return polys


def warp_points(pts, X, Y, W):
    """Push (x, y) pixel points through the corner-mesh warp (bilinear). Periodic in x."""
    coords = [pts[:, 1], pts[:, 0] % W]
    wx = ndimage.map_coordinates(X, coords, order=1, mode="nearest") + np.floor(pts[:, 0] / W) * W
    wy = ndimage.map_coordinates(Y, coords, order=1, mode="nearest")
    return np.stack([wx, wy], axis=1)


def split_seam(line, W):
    """Break a polyline where it jumps across the periodic seam; draw both copies."""
    out = []
    x = line[:, 0] % W
    y = line[:, 1]
    pts = np.stack([x, y], 1)
    cut = np.nonzero(np.abs(np.diff(x)) > W / 2)[0] + 1
    for seg in np.split(pts, cut):
        if len(seg) > 1:
            out.append(seg)
    return out


# ---------------------------------------------------------------- figures
def _figure(oh, ow, bg):
    fig = plt.figure(figsize=(ow / 100, oh / 100), dpi=100, facecolor=bg)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, ow)
    ax.set_ylim(oh, 0)
    ax.axis("off")
    return fig, ax


def _add_lines(ax, lines, X, Y, W, scale, color, lw):
    segs = []
    for l in lines:
        for s in split_seam(warp_points(l, X, Y, W), W):
            segs.append(s * scale)
    if segs:
        ax.add_collection(LineCollection(segs, colors=color, linewidths=lw))


def draw(X, Y, mask, out_png, out_w=None, coast=(), borders=(), grat=(), mgrid=(), tissot=(),
         raster=None, cmap="magma", vmin=None, vmax=None, title=None, wrap=True):
    """Land (or a raster) through the warp, vectors on top, at output width out_w."""
    H, W = mask.shape
    out_w = out_w or W
    oh, ow = int(round(H * out_w / W)), out_w
    scale = ow / W
    if raster is None:
        cov = splat(mask.astype(np.float64), X, Y, (oh, ow), wrap=wrap)
        img = OCEAN[None, None, :] * (1 - cov[..., None]) + LAND[None, None, :] * cov[..., None]
    else:
        v = splat(raster.astype(np.float64), X, Y, (oh, ow), wrap=wrap)
        vmin = np.nanmin(v) if vmin is None else vmin
        vmax = np.nanmax(v) if vmax is None else vmax
        img = matplotlib.colormaps[cmap]((v - vmin) / (vmax - vmin + 1e-12))[..., :3]
    fig, ax = _figure(oh, ow, "white")
    ax.imshow(img, extent=(0, ow, oh, 0), interpolation="nearest")
    if mgrid:
        _add_lines(ax, mgrid, X, Y, W, scale, "#00000045", 0.35)
    if tissot:
        polys = [split_seam(warp_points(p, X, Y, W), W) for p in tissot]
        ax.add_collection(PolyCollection([s * scale for ps in polys for s in ps if len(s) > 2],
                                         facecolors="#d0303040", edgecolors="#a02020", linewidths=0.5))
    if grat:
        _add_lines(ax, grat, X, Y, W, scale, "#00000030", 0.4)
    if borders:
        _add_lines(ax, borders, X, Y, W, scale, "#00000060", 0.3)
    if coast:
        _add_lines(ax, coast, X, Y, W, scale, "#000000", 0.5)
    if title:
        ax.text(0.01, 0.01, title, transform=ax.transAxes, fontsize=9, color="#222", va="bottom")
    fig.savefig(out_png, dpi=100)
    plt.close(fig)


def draw_error(X, Y, rho0, out_png, out_w=None, vmax=1.0, wrap=True):
    """log(rho0 / warped area): 0 is perfect; red = too small, blue = too big; folds black."""
    H, W = rho0.shape
    out_w = out_w or W
    oh, ow = int(round(H * out_w / W)), out_w
    A = quad_areas(X, Y)
    lr = np.log(rho0 / np.maximum(A, 1e-12))
    v = splat(np.where(A > 0, lr, 0.0), X, Y, (oh, ow), wrap=wrap)
    img = matplotlib.colormaps["RdBu_r"]((np.clip(v, -vmax, vmax) + vmax) / (2 * vmax))[..., :3]
    fig, ax = _figure(oh, ow, "white")
    ax.imshow(img, extent=(0, ow, oh, 0), interpolation="nearest")
    if (A <= 0).any():
        fy, fx = np.nonzero(A <= 0)
        ax.plot((X[fy, fx] % W) * ow / W, Y[fy, fx] * oh / H, "k.", ms=2)
    ax.text(0.01, 0.01, f"log(rho0/area), range +-{vmax}; folds black ({int((A <= 0).sum())})", transform=ax.transAxes, fontsize=9)
    fig.savefig(out_png, dpi=100)
    plt.close(fig)
