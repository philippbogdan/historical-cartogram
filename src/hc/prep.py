"""Population raster -> Mercator count grid.

Counts are re-binned exactly (people per output pixel); densities are never
reprojected, so Mercator's area distortion needs no separate correction.
Row 0 is north. x = longitude (uniform), y = Mercator y (uniform), square pixels.
"""
import numpy as np
import rasterio
from rasterio.windows import Window


def merc_y(lat_deg):
    """Mercator y (unit sphere), increasing northward."""
    return np.log(np.tan(np.pi / 4 + np.radians(lat_deg) / 2))


def inv_merc_y(y):
    return np.degrees(2 * np.arctan(np.exp(y)) - np.pi / 2)


def grid_shape(width, lat_cut):
    """Output (H, W) with square pixels for a given width and latitude cut."""
    ymax = merc_y(lat_cut)
    return int(round(width * ymax / np.pi)), width


def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def block_sum(a, f):
    h, w = a.shape
    return a.reshape(h // f, f, w // f, f).sum(axis=(1, 3))


def load_lonlat_counts(path, factor):
    """Read a GeoTIFF of population counts, block-summed by `factor` (exact).

    Columns are cropped to the 360 degrees starting at -180; rows are trimmed
    at the south to a multiple of `factor`. Returns counts and (l, b, r, t).
    """
    with rasterio.open(path) as src:
        T = src.transform
        dx, dy = T.a, -T.e
        ncols = int(round(360.0 / dx))
        col0 = int(round((-180.0 - T.c) / dx))
        col0 = max(col0, 0)
        ncols = min(ncols, src.width - col0)
        ncols -= ncols % factor
        nrows = src.height - src.height % factor
        assert ncols % factor == 0 and nrows % factor == 0
        out = np.zeros((nrows // factor, ncols // factor), np.float64)
        rows_per = factor * max(1, 1000 // factor)
        for r0 in range(0, nrows, rows_per):
            n = min(rows_per, nrows - r0)
            a = src.read(1, window=Window(col0, r0, ncols, n)).astype(np.float64)
            a = np.nan_to_num(a)
            a[a < 0] = 0.0  # GHS-POP nodata is -200
            out[r0 // factor:(r0 + n) // factor] = block_sum(a, factor)
        left = T.c + col0 * dx
        top = T.f
        bounds = (left, top - nrows * dy, left + ncols * dx, top)
    return out, bounds


def _rebin_axis(c, edges_src, edges_out, axis):
    """Exact re-binning along one axis assuming uniform density within a source cell.

    edges_src: monotone source cell edges (n+1); edges_out: output edges (m+1),
    same direction. Uses the cumulative sum interpolated at output edges.
    """
    c = np.moveaxis(c, axis, 0)
    n = c.shape[0]
    cum = np.concatenate([np.zeros((1,) + c.shape[1:]), np.cumsum(c, axis=0)], axis=0)
    # fractional source index of each output edge
    fi = np.interp(edges_out, edges_src, np.arange(n + 1))
    i0 = np.minimum(np.floor(fi).astype(int), n - 1)
    t = (fi - i0).reshape((-1,) + (1,) * (c.ndim - 1))
    cum_b = cum[i0] * (1 - t) + cum[i0 + 1] * t
    out = cum_b[1:] - cum_b[:-1]
    return np.moveaxis(out, 0, axis)


def to_mercator(counts, bounds, width, lat_cut):
    """Re-bin a lon/lat count grid onto a Mercator pixel grid, conserving counts."""
    Hs, Ws = counts.shape
    left, bottom, right, top = bounds
    H, W = grid_shape(width, lat_cut)
    # columns: longitude, uniform on both sides
    lon_src = np.linspace(left, right, Ws + 1)
    lon_out = np.linspace(-180.0, 180.0, W + 1)
    c = _rebin_axis(counts, lon_src, lon_out, axis=1)
    # rows: source edges in latitude descending from the north; output edges in Mercator y
    lat_src = np.linspace(top, bottom, Hs + 1)
    ymax = merc_y(lat_cut)
    yb = ymax - np.arange(H + 1) * (2 * ymax / H)
    lat_out = inv_merc_y(yb)
    # np.interp needs increasing x: flip both
    merc = _rebin_axis(c[::-1], lat_src[::-1], lat_out[::-1], axis=0)[::-1]
    dropped = counts.sum() - merc.sum()
    return merc, dropped


def lonlat_to_pixel(lon, lat, H, W, lat_cut):
    """Map lon/lat to Mercator pixel coordinates (x right, y down, corners at integers)."""
    ymax = merc_y(lat_cut)
    lat = np.clip(lat, -lat_cut, lat_cut)
    x = (np.asarray(lon) + 180.0) / 360.0 * W
    y = (ymax - merc_y(lat)) / (2 * ymax) * H
    return x, y
