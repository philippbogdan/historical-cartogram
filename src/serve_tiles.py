"""V0 dev viewer: a local tile server over any GeoTIFF (EPSG:4326), Leaflet in front.

    python src/serve_tiles.py data/raw/GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif [port]
then open http://localhost:8765/ . Tiles are lon/lat aligned (no reprojection): tile (z, x, y)
covers 180/2^z degrees; each is a windowed, decimated read of the raster (overviews if present),
rendered as log10 people per km^2 in magma. Cell area is corrected for latitude.
"""
import io, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
from PIL import Image
import matplotlib
CMAP = matplotlib.colormaps["magma"]
TILE = 256
VIEWER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "viewer", "index.html")


class Tiles:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.src = rasterio.open(path)
        T = self.src.transform
        self.left, self.top, self.dx, self.dy = T.c, T.f, T.a, -T.e
        self.cell_km_eq = self.dx * 111.32  # km at the equator

    def tile(self, z, x, y, vmax=4.7, mode="avg", ss=None):
        """mode 'avg': people per km^2 averaged over the display pixel (honest density).
        mode 'max': the densest 100 m cell under the pixel (settlement structure at any zoom).
        Tiles are read at ss x the tile size and reduced, so fine structure survives decimation."""
        deg = 180.0 / (2 ** z)
        lon0, lat1 = -180 + x * deg, 90 - y * deg
        lon1, lat0 = lon0 + deg, lat1 - deg
        c0 = int(np.floor((lon0 - self.left) / self.dx)); c1 = int(np.ceil((lon1 - self.left) / self.dx))
        r0 = int(np.floor((self.top - lat1) / self.dy)); r1 = int(np.ceil((self.top - lat0) / self.dy))
        c0, r0 = max(c0, 0), max(r0, 0)
        c1, r1 = min(c1, self.src.width), min(r1, self.src.height)
        if c1 <= c0 or r1 <= r0:
            return None
        win = Window(c0, r0, c1 - c0, r1 - r0)
        ss = ss or (4 if mode == "max" else 2)  # max mode: max over 4x4 finer averages under each pixel
        n = TILE * ss
        cells_per_px = max((c1 - c0) / n, 1.0)
        with self.lock:
            a = self.src.read(1, window=win, out_shape=(n, n), resampling=Resampling.average if cells_per_px > 1 else Resampling.nearest).astype(np.float64)
        a[a < 0] = 0
        a = a.reshape(TILE, ss, TILE, ss)
        a = a.max(axis=(1, 3)) if mode == "max" else a.mean(axis=(1, 3))
        lat_c = np.radians((lat0 + lat1) / 2)
        cell_area = (self.cell_km_eq ** 2) * max(np.cos(lat_c), 0.05)  # km^2 per source cell
        dens = a / cell_area  # people per km^2 of the source cell (per-cell counts survive both resamplings)
        v = np.log10(dens + 1) / vmax
        rgb = (CMAP(np.clip(v, 0, 1))[..., :3] * 255).astype(np.uint8)
        rgb[a <= 0] = 0
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format="PNG")
        return buf.getvalue()


def main():
    path = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    tiles = Tiles(path)
    maxz = int(np.ceil(np.log2(360.0 / (tiles.dx * TILE)))) + 1

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/tiles/"):
                try:
                    path, _, qs = self.path.partition("?")
                    mode = "max" if "mode=max" in qs else "avg"
                    z, x, y = (int(p) for p in path[7:].split(".")[0].split("/"))
                    png = tiles.tile(z, x, y, mode=mode)
                except Exception as e:
                    self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode()); return
                if png is None:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200); self.send_header("Content-Type", "image/png"); self.send_header("Cache-Control", "max-age=3600"); self.end_headers(); self.wfile.write(png)
            elif self.path.startswith("/meta"):
                body = f'{{"maxZoom": {maxz}, "cell_deg": {tiles.dx}, "file": "{os.path.basename(tiles.path)}"}}'.encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
            else:
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(open(VIEWER, "rb").read())

    print(f"serving {path} ({tiles.src.width}x{tiles.src.height}, {tiles.dx*3600:.1f} arcsec, maxZoom {maxz}) at http://localhost:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
