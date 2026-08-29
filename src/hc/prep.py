"""Population raster -> count grid on a cylindrical projection.

Counts are re-binned exactly (people per output pixel); densities are never
reprojected, so no area correction exists anywhere. Row 0 is north, x is
longitude (uniform), y is the projection's vertical coordinate (uniform).

Grids (A2): 'mercator' (y = Mercator y, the flat rectangle picture) and
'equalarea' (y = sin lat, Lambert cylindrical: pixel area = sphere area, for
anything shown on a globe). Pixels are square in projection units.
"""
import numpy as np
import rasterio
from rasterio.windows import Window

R_EARTH_KM = 6371.0


def merc_y(lat_deg):
    return np.log(np.tan(np.pi / 4 + np.radians(lat_deg) / 2))


def inv_merc_y(y):
    return np.degrees(2 * np.arctan(np.exp(y)) - np.pi / 2)


class Grid:
    """A cylindrical pixel grid: W columns over 360 degrees, H rows over +-lat_cut."""

    def __init__(self, kind, width, lat_cut=None, lon0=-180.0):
        assert kind in ("mercator", "equalarea"), kind
        self.kind = kind
        self.W = int(width)
        # longitude at the left edge, snapped to a column edge so rasters and vectors agree exactly
        self.lon0 = -180.0 + round((float(lon0) + 180.0) / 360.0 * self.W) * 360.0 / self.W
        if lat_cut is None:
            lat_cut = 85.0511 if kind == "mercator" else 90.0
        self.lat_cut = float(lat_cut)
        self.ymax = self._v(self.lat_cut)
        self.H = int(round(self.W * self.ymax / np.pi))

    # vertical projection coordinate, increasing northward
    def _v(self, lat_deg):
        if self.kind == "mercator":
            return merc_y(lat_deg)
        return np.sin(np.radians(lat_deg))

    def _inv_v(self, v):
        if self.kind == "mercator":
            return inv_merc_y(v)
        return np.degrees(np.arcsin(np.clip(v, -1, 1)))

    def xy(self, lon, lat):
        """lon/lat (deg) -> pixel coords, x right, y down, corners at integers."""
        lon = np.asarray(lon, np.float64)
        lat = np.clip(np.asarray(lat, np.float64), -self.lat_cut, self.lat_cut)
        x = ((lon - self.lon0) % 360.0) / 360.0 * self.W
        y = (self.ymax - self._v(lat)) / (2 * self.ymax) * self.H
        return x, y

    def lonlat(self, x, y):
        lon = (np.asarray(x, np.float64) / self.W * 360.0 + self.lon0 + 180.0) % 360.0 - 180.0
        v = self.ymax - np.asarray(y, np.float64) / self.H * 2 * self.ymax
        return lon, self._inv_v(v)

    def row_edge_lats(self):
        """Latitude of the H+1 row boundaries, north to south."""
        vb = self.ymax - np.arange(self.H + 1) * (2 * self.ymax / self.H)
        return self._inv_v(vb)

    def km_per_px_equator(self):
        return 2 * np.pi * R_EARTH_KM / self.W

    def describe(self):
        return f"{self.kind} {self.W}x{self.H} lat_cut {self.lat_cut} lon0 {self.lon0}"


def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def block_sum(a, f):
    h, w = a.shape
    return a.reshape(h // f, f, w // f, f).sum(axis=(1, 3))


def load_lonlat_counts(path, factor):
    """Read a GeoTIFF of counts, block-summed by `factor` (exact).

    Columns are cropped to the 360 degrees starting at -180; rows are trimmed
    at the south to a multiple of `factor`. Returns counts and (l, b, r, t).
    """
    with rasterio.open(path) as src:
        T = src.transform
        dx, dy = T.a, -T.e
        ncols = int(round(360.0 / dx))
        col0 = max(int(round((-180.0 - T.c) / dx)), 0)
        ncols = min(ncols, src.width - col0)
        ncols -= ncols % factor
        nrows = src.height - src.height % factor
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
    """Exact re-binning along one axis, uniform density within a source cell.

    edges_src (n+1) and edges_out (m+1) must be increasing in the same units.
    """
    c = np.moveaxis(c, axis, 0)
    n = c.shape[0]
    cum = np.concatenate([np.zeros((1,) + c.shape[1:]), np.cumsum(c, axis=0)], axis=0)
    fi = np.interp(edges_out, edges_src, np.arange(n + 1))
    i0 = np.minimum(np.floor(fi).astype(int), n - 1)
    t = (fi - i0).reshape((-1,) + (1,) * (c.ndim - 1))
    cum_b = cum[i0] * (1 - t) + cum[i0 + 1] * t
    return np.moveaxis(cum_b[1:] - cum_b[:-1], 0, axis)


def to_grid(counts, bounds, grid):
    """Re-bin a lon/lat count grid onto `grid`, conserving counts. Returns (counts, dropped)."""
    Hs, Ws = counts.shape
    left, bottom, right, top = bounds
    lon_src = np.linspace(left, right, Ws + 1)
    lon_out = np.linspace(-180.0, 180.0, grid.W + 1)
    c = _rebin_axis(counts, lon_src, lon_out, axis=1)
    k = int(round((grid.lon0 + 180.0) / 360.0 * grid.W))
    if k:
        c = np.roll(c, -k, axis=1)  # column 0 starts at lon0 (exact: lon0 is snapped to a column edge)
    lat_src = np.linspace(top, bottom, Hs + 1)
    lat_out = grid.row_edge_lats()
    out = _rebin_axis(c[::-1], lat_src[::-1], lat_out[::-1], axis=0)[::-1]
    return out, counts.sum() - out.sum()
