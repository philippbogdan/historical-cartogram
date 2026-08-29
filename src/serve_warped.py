"""A12 prototype: the cartogram, zoomable, at the source data's own resolution.

    python src/serve_warped.py <experiment> [port]      -> http://localhost:8766/

The frame is the experiment's output space (W x H mesh pixels). A tile (z, x, y) covers W/2^z
mesh pixels; for each tile pixel the inverse map gives the source (Mercator-grid) coordinate,
which becomes lon/lat, which is sampled from the 100 m GHS-POP raster (windowed, decimated read)
or from a 1 km country-id raster. Layers: pop (log density, magma), country (coloured ids).
Folds never matter here: the inverse map is single-valued by construction.
"""
import io, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
from scipy import ndimage
from PIL import Image
import matplotlib
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep
from run import ROOT, RAW
from render_countries import country_ids, palette

CMAP = matplotlib.colormaps["magma"]
TILE = 256
GHS3 = os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif")
GHS30 = os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif")


class Warped:
    def __init__(self, name):
        out = os.path.join(ROOT, "experiments", name)
        self.p = json.load(open(os.path.join(out, "params.json")))
        z = np.load(os.path.join(out, "inverse.npz"))
        self.IX, self.IY = z["IX"].astype(np.float64), z["IY"].astype(np.float64)
        self.oh, self.ow = self.IX.shape
        self.H, self.W = int(z["src_hw"][0]), int(z["src_hw"][1])
        self.grid = prep.Grid(self.p.get("grid", "mercator"), self.W, self.p["lat_cut"])
        self.src = rasterio.open(GHS3 if os.path.exists(GHS3) else GHS30)
        T = self.src.transform
        self.left, self.top, self.dx, self.dy = T.c, T.f, T.a, -T.e
        self.lock = threading.Lock()
        # country ids on a 1 km lon/lat grid (drawing only), cached
        cache = os.path.join(ROOT, "data", "derived", "country_ids_8640.npz")
        if os.path.exists(cache):
            self.cids = np.load(cache)["ids"]
        else:
            g = prep.Grid("equalarea", 8640, 90.0)  # any grid works for rasterising; we resample by lon/lat below
            ids, names, _ = country_ids(prep.Grid("mercator", 8640, 85.0511), "50m")
            self.cids = ids
            np.savez_compressed(cache, ids=ids)
        self.cid_grid = prep.Grid("mercator", 8640, 85.0511)
        self.cols = (palette(int(self.cids.max()) + 1) * 255).astype(np.uint8)
        self.cols[0] = (168, 196, 216)
        self.maxz = int(np.ceil(np.log2(self.ow / TILE))) + 5

    def tile(self, z, x, y, layer="pop", vmax=4.7, ss=2):
        span = self.ow / (2 ** z)                      # mesh px per tile
        n = TILE * ss
        u = x * span + (np.arange(n) + 0.5) * span / n  # output pixel coords of tile samples
        v = y * span + (np.arange(n) + 0.5) * span / n
        if u[0] >= self.ow or v[0] >= self.oh:
            return None
        U, V = np.meshgrid(u, v)
        # inverse map: output px -> source mesh px (periodic in x: interpolate cos/sin)
        coords = [np.clip(V - 0.5, 0, self.oh - 1), np.clip(U - 0.5, 0, self.ow - 1)]
        ang = self.IX / self.W * 2 * np.pi
        cx = ndimage.map_coordinates(np.cos(ang), coords, order=1, mode="nearest")
        sx = ndimage.map_coordinates(np.sin(ang), coords, order=1, mode="nearest")
        sxp = (np.arctan2(sx, cx) / (2 * np.pi)) % 1.0 * self.W
        syp = ndimage.map_coordinates(self.IY, coords, order=1, mode="nearest")
        lon, lat = self.grid.lonlat(sxp, syp)
        if layer == "country":
            gx, gy = self.cid_grid.xy(lon, lat)
            ids = self.cids[np.clip(gy.astype(int), 0, self.cids.shape[0] - 1), np.clip(gx.astype(int), 0, self.cids.shape[1] - 1)]
            rgb = self.cols[ids]
            rgb = rgb.reshape(TILE, ss, TILE, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
        else:
            # source raster window covering the sampled lon/lat box, read at a resolution matched to the tile
            lon0, lon1, lat0, lat1 = lon.min(), lon.max(), lat.min(), lat.max()
            c0 = int(np.floor((lon0 - self.left) / self.dx)) - 1; c1 = int(np.ceil((lon1 - self.left) / self.dx)) + 1
            r0 = int(np.floor((self.top - lat1) / self.dy)) - 1; r1 = int(np.ceil((self.top - lat0) / self.dy)) + 1
            c0, r0 = max(c0, 0), max(r0, 0); c1, r1 = min(c1, self.src.width), min(r1, self.src.height)
            if c1 <= c0 or r1 <= r0:
                return None
            nc, nr = c1 - c0, r1 - r0
            dec = max(1, int(min(nc, nr) / n))  # cells per sample
            oc, orr = max(1, nc // dec), max(1, nr // dec)
            with self.lock:
                a = self.src.read(1, window=Window(c0, r0, nc, nr), out_shape=(orr, oc), resampling=Resampling.average if dec > 1 else Resampling.nearest).astype(np.float64)
            a[a < 0] = 0
            cell_km2 = (self.dx * dec * 111.32) ** 2 * np.maximum(np.cos(np.radians((lat0 + lat1) / 2)), 0.05)
            dens = a / cell_km2
            fx = (lon - (self.left + c0 * self.dx)) / (self.dx * dec) - 0.5
            fy = ((self.top - r0 * self.dy) - lat) / (self.dy * dec) - 0.5
            d = ndimage.map_coordinates(dens, [fy, fx], order=1, mode="nearest")
            vv = np.log10(d + 1) / vmax
            rgb = (CMAP(np.clip(vv, 0, 1))[..., :3] * 255)
            rgb = rgb.reshape(TILE, ss, TILE, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
        buf = io.BytesIO(); Image.fromarray(rgb).save(buf, format="PNG"); return buf.getvalue()


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>cartogram viewer</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body,#map{height:100%;margin:0;background:#000}#info{position:absolute;top:8px;left:50px;z-index:1000;color:#ddd;font:12px/1.4 -apple-system,sans-serif;background:#0008;padding:6px 8px;border-radius:4px}</style>
</head><body><div id="map"></div><div id="info">loading</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
fetch('/meta').then(r=>r.json()).then(m=>{
  const map=L.map('map',{crs:L.CRS.Simple,minZoom:0,maxZoom:m.maxZoom,zoomSnap:0.25,wheelPxPerZoomLevel:90});
  const opts={tileSize:256,minZoom:0,maxNativeZoom:m.maxZoom,maxZoom:m.maxZoom+2,noWrap:true,bounds:[[-256,0],[0,256]]};
  const pop=L.tileLayer('/tiles/{z}/{x}/{y}.png?layer=pop',opts), cty=L.tileLayer('/tiles/{z}/{x}/{y}.png?layer=country',opts);
  pop.addTo(map); map.fitBounds([[-256,0],[0,256]]);
  L.control.layers({'population (100 m, log density)':pop,'countries':cty},null,{collapsed:false}).addTo(map);
  document.getElementById('info').textContent=m.name+'  |  the cartogram frame, zoomable; population through the inverse map';
});
</script></body></html>"""


def main():
    name = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8766
    wp = Warped(name)

    class Hd(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            if self.path.startswith("/tiles/"):
                path, _, qs = self.path.partition("?")
                layer = "country" if "layer=country" in qs else "pop"
                try:
                    z, x, y = (int(v) for v in path[7:].split(".")[0].split("/"))
                    png = wp.tile(z, x, y, layer=layer)
                except Exception as e:
                    self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode()); return
                if png is None:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200); self.send_header("Content-Type", "image/png"); self.send_header("Cache-Control", "max-age=3600"); self.end_headers(); self.wfile.write(png)
            elif self.path.startswith("/meta"):
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"maxZoom": wp.maxz, "name": name}).encode())
            else:
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(PAGE.encode())
    print(f"serving warped {name} at http://localhost:{port}/ (maxZoom {wp.maxz})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Hd).serve_forever()


if __name__ == "__main__":
    main()
