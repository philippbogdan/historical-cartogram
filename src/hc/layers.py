"""Legibility layers through a warp: city labels (A14), rivers and lakes (A15), ghost coastline (R9),
equipotentials (R7), stretch and twist rasters (R6, X8). All take the closed corner mesh X, Y."""
import json, os
import numpy as np
from matplotlib.collections import LineCollection
from .render import lines_from_geojson, warp_points, split_seam, _add_lines, _iter_geoms
from .diffusion import quad_areas


def cities(geojson_path, grid, n=300):
    """Top-n populated places by pop_max: (name, x, y, pop) in pixel coords."""
    with open(geojson_path) as f:
        gj = json.load(f)
    rows = []
    for feat in gj["features"]:
        p = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"][:2]
        x, y = grid.xy(lon, lat)
        rows.append((p.get("name") or p.get("nameascii"), float(x), float(y), float(p.get("pop_max") or 0)))
    rows.sort(key=lambda r: -r[3])
    return rows[:n]


def draw_city_labels(ax, places, X, Y, W, scale, out_hw, color="#111", max_labels=300):
    """Labels at warped positions, biggest first, skipping ones that would overlap (coarse occupancy)."""
    oh, ow = out_hw
    occ = np.zeros((oh // 16 + 1, ow // 16 + 1), bool)
    pts = np.array([[p[1], p[2]] for p in places])
    wp = warp_points(pts, X, Y, W)
    drawn = 0
    for (name, _, _, pop), (wx, wy) in zip(places, wp):
        fs = float(np.clip(4.5 + 1.6 * np.log10(max(pop, 1e4) / 1e5), 4.5, 11)) * ow / 4096
        px, py = (wx % W) * scale, wy * scale
        w_cells = int(len(name) * fs * 0.6 * 100 / 72 / 16) + 1
        i, j = int(py // 16), int(px // 16)
        if i < 0 or i >= occ.shape[0] or j < 0 or j + w_cells >= occ.shape[1]:
            continue
        if occ[max(i - 1, 0):i + 2, max(j - 1, 0):j + w_cells + 1].any():
            continue
        occ[max(i - 1, 0):i + 2, max(j - 1, 0):j + w_cells + 1] = True
        ax.plot(px, py, "o", ms=fs * 0.25, color=color, alpha=0.8)
        ax.text(px + fs * 0.4, py, name, fontsize=fs, color=color, va="center", ha="left")
        drawn += 1
        if drawn >= max_labels:
            break
    return drawn


def rivers(raw_dir, grid, res="50m"):
    return lines_from_geojson(os.path.join(raw_dir, f"ne_{res}_rivers_lake_centerlines.geojson"), grid)


def lakes(raw_dir, grid, res="50m"):
    return lines_from_geojson(os.path.join(raw_dir, f"ne_{res}_lakes.geojson"), grid)


def ghost_coast(ax, coast_lines, scale, color="#00000025", lw=0.5):
    segs = [l * scale for l in coast_lines]
    ax.add_collection(LineCollection(segs, colors=color, linewidths=lw))


def equipotential_lines(psi, levels=40):
    """Contour polylines of a potential on the source grid, in pixel coords (cell centres)."""
    import matplotlib.pyplot as plt
    from contourpy import contour_generator
    H, W = psi.shape
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    gen = contour_generator(xs, ys, psi)
    lv = np.linspace(np.percentile(psi, 0.5), np.percentile(psi, 99.5), levels)
    lines = []
    for l in lv:
        for seg in gen.lines(l):
            if len(seg) > 2:
                lines.append(np.asarray(seg))
    return lines


def stretch_and_twist(X, Y):
    """Per cell: log area scale (R6) and rotation angle in degrees (X8) from the polar
    decomposition of the local Jacobian (average of the two edge vectors)."""
    dxu = (X[:-1, 1:] - X[:-1, :-1] + X[1:, 1:] - X[1:, :-1]) / 2
    dyu = (Y[:-1, 1:] - Y[:-1, :-1] + Y[1:, 1:] - Y[1:, :-1]) / 2
    dxv = (X[1:, :-1] - X[:-1, :-1] + X[1:, 1:] - X[:-1, 1:]) / 2
    dyv = (Y[1:, :-1] - Y[:-1, :-1] + Y[1:, 1:] - Y[:-1, 1:]) / 2
    a, b, c, d = dxu, dxv, dyu, dyv           # J = [[a, b], [c, d]]
    A = quad_areas(X, Y)
    stretch = np.log(np.maximum(A, 1e-9))
    # J = R S with R rotation: angle = atan2(c - b, a + d)
    twist = np.degrees(np.arctan2(c - b, a + d))
    return stretch, twist
