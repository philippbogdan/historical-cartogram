"""V2: the inverse of a window's composed map, for the raster tile server: for every pixel of a grid over the
window's warped footprint, the source lon/lat that lands there (splat of the source coordinates through the
composed corner mesh).   python src/nested_inverse.py <window> [n_out=2048]"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import render
from run import ROOT
name = sys.argv[1]; n_out = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
d = os.path.join(ROOT, "experiments", "nested", name); z = np.load(os.path.join(d, "mesh.npz"))
X, Y = z["X"].astype(np.float64), z["Y"].astype(np.float64); n = int(z["n"]); lon0, lat1, dx = float(z["lon0"]), float(z["lat1"]), float(z["dx"])
x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max(); sc = n_out / max(x1 - x0, y1 - y0); oh, ow = int((y1 - y0) * sc) + 1, int((x1 - x0) * sc) + 1
# source lon/lat at cell centres, pushed through the composed corner mesh
cc = np.arange(n) + 0.5; lon = lon0 + cc * dx; lat = lat1 - cc * dx; LON, LAT = np.meshgrid(lon, lat)
ILON = render.splat(LON, (X - x0) * sc, (Y - y0) * sc, (oh, ow), wrap=False); ILAT = render.splat(LAT, (X - x0) * sc, (Y - y0) * sc, (oh, ow), wrap=False)
np.savez_compressed(os.path.join(d, "inverse.npz"), ILON=ILON.astype(np.float32), ILAT=ILAT.astype(np.float32), x0=x0, y0=y0, sc=sc, lon0=lon0, lat1=lat1, n=n, dx=dx)
print(f"{name}: inverse {oh}x{ow} over warped bbox x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f} (global px)")
