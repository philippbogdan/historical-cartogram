"""Render a warped mesh: land mask and any raster through the warp, vectors on top."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from rasterio import features
from rasterio.transform import Affine
from scipy import ndimage

from .prep import lonlat_to_pixel

LAND = "#d9d2c3"
OCEAN = "#a8c4d8"


def _iter_geoms(geojson_path):
    with open(geojson_path) as f:
        gj = json.load(f)
    for feat in gj["features"]:
        yield feat["geometry"], feat.get("properties", {})


def _map_coords(coords, H, W, lat_cut):
    coords = np.asarray(coords, np.float64)
    x, y = lonlat_to_pixel(coords[:, 0], coords[:, 1], H, W, lat_cut)
    return np.stack([x, y], axis=1)


def _transform_geometry(geom, H, W, lat_cut):
    t = geom["type"]
    if t == "Polygon":
        return {"type": t, "coordinates": [_map_coords(r, H, W, lat_cut).tolist() for r in geom["coordinates"]]}
    if t == "MultiPolygon":
        return {"type": t, "coordinates": [[_map_coords(r, H, W, lat_cut).tolist() for r in poly] for poly in geom["coordinates"]]}
    raise ValueError(t)


def land_mask(geojson_path, H, W, lat_cut):
    shapes = [(_transform_geometry(g, H, W, lat_cut), 1) for g, _ in _iter_geoms(geojson_path)
              if g["type"] in ("Polygon", "MultiPolygon")]
    return features.rasterize(shapes, out_shape=(H, W), transform=Affine.identity(),
                              fill=0, dtype="uint8", all_touched=False)


def _densify(pts, max_seg=1.0):
    out = [pts[:1]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = int(np.ceil(np.hypot(*(b - a)) / max_seg))
        if n > 1:
            out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
        else:
            out.append(b[None])
    return np.vstack(out)


def warp_points(pts, X, Y):
    """Push (x, y) pixel points through the corner-mesh warp (bilinear)."""
    coords = [pts[:, 1], pts[:, 0]]
    wx = ndimage.map_coordinates(X, coords, order=1, mode="nearest")
    wy = ndimage.map_coordinates(Y, coords, order=1, mode="nearest")
    return np.stack([wx, wy], axis=1)


def lines_from_geojson(geojson_path, H, W, lat_cut):
    lines = []
    for g, _ in _iter_geoms(geojson_path):
        if g["type"] == "LineString":
            parts = [g["coordinates"]]
        elif g["type"] == "MultiLineString":
            parts = g["coordinates"]
        elif g["type"] == "Polygon":
            parts = g["coordinates"]
        elif g["type"] == "MultiPolygon":
            parts = [r for poly in g["coordinates"] for r in poly]
        else:
            continue
        for p in parts:
            lines.append(_densify(_map_coords(p, H, W, lat_cut)))
    return lines


def graticule(H, W, lat_cut, step=15):
    lines = []
    for lon in np.arange(-180, 181, step):
        lat = np.linspace(-lat_cut, lat_cut, 400)
        x, y = lonlat_to_pixel(np.full_like(lat, lon), lat, H, W, lat_cut)
        lines.append(np.stack([x, y], 1))
    for lat in np.arange(-75, 76, step):
        lon = np.linspace(-180, 180, 800)
        x, y = lonlat_to_pixel(lon, np.full_like(lon, lat), H, W, lat_cut)
        lines.append(np.stack([x, y], 1))
    return lines


def draw(X, Y, mask, out_png, coast_lines=(), border_lines=(), grat_lines=(),
         raster=None, cmap="magma", title=None, px_per_cell=2.0):
    H, W = mask.shape
    fig = plt.figure(figsize=(W * px_per_cell / 100, H * px_per_cell / 100), dpi=100, facecolor=OCEAN)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(OCEAN)
    if raster is not None:
        ax.pcolormesh(X, Y, raster, cmap=cmap, shading="flat", rasterized=True, antialiased=False)
    else:
        ax.pcolormesh(X, Y, np.ma.masked_where(mask == 0, mask), cmap=matplotlib.colors.ListedColormap([LAND]),
                      shading="flat", rasterized=True, antialiased=False)
    if grat_lines:
        ax.add_collection(LineCollection([warp_points(l, X, Y) for l in grat_lines], colors="#00000030", linewidths=0.4))
    if border_lines:
        ax.add_collection(LineCollection([warp_points(l, X, Y) for l in border_lines], colors="#00000060", linewidths=0.3))
    if coast_lines:
        ax.add_collection(LineCollection([warp_points(l, X, Y) for l in coast_lines], colors="#000000", linewidths=0.5))
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.text(0.01, 0.01, title, transform=ax.transAxes, fontsize=9, color="#222", va="bottom")
    fig.savefig(out_png, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_error(X, Y, rho0, out_png, px_per_cell=2.0, vmax=1.0):
    """log(rho0 / warped area): 0 everywhere is a perfect cartogram; red = too small, blue = too big."""
    from .diffusion import quad_areas
    A = quad_areas(X, Y)
    lr = np.log(rho0 / np.maximum(A, 1e-12))
    lr[A <= 0] = np.nan
    H, W = rho0.shape
    fig = plt.figure(figsize=(W * px_per_cell / 100, H * px_per_cell / 100), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.pcolormesh(X, Y, np.ma.masked_invalid(lr), cmap="RdBu_r", vmin=-vmax, vmax=vmax, shading="flat", rasterized=True, antialiased=False)
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_aspect("equal"); ax.axis("off")
    ax.text(0.01, 0.01, f"log(rho0/area), range +-{vmax}; folds black", transform=ax.transAxes, fontsize=9)
    if (A <= 0).any():
        fy, fx = np.nonzero(A <= 0)
        ax.plot(X[fy, fx], Y[fy, fx], "k.", ms=2)
    fig.savefig(out_png, dpi=100)
    plt.close(fig)
