"""V16/V18: push vector boundaries through a frame's warp and write them as GeoJSON in pseudo lon/lat, so
MapLibre draws the cartogram as if it were an ordinary Web-Mercator world. The wall-frame warp maps the
Mercator square to itself, so warped pixel (x, y) -> lon = x / W * 360 + lon0, lat = Web-Mercator inverse of y.
    python src/warp_vectors.py <experiment> <in.geojson> <out.geojson> [name_field] [pop_field] [level]"""
import json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render, diffusion
from hc.diffusion import quad_areas
from run import ROOT, load_mesh


def frame_mesh(exp):
    out = os.path.join(ROOT, "experiments", exp); p = json.load(open(os.path.join(out, "params.json")))
    X, Y, rho0 = load_mesh(out); X, Y = X.astype(np.float64), Y.astype(np.float64)
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
    cache = os.path.join(out, "mesh_repaired.npz")
    if os.path.exists(cache):
        z = np.load(cache); X, Y = z["X"], z["Y"]
    else:
        X, Y, _ = diffusion.repair_folds(X, Y, periodic=(p.get("x_boundary") == "periodic"), mass=np.asarray(rho0, np.float64), log=lambda *_: None)
        np.savez_compressed(cache, X=X.astype(np.float32), Y=Y.astype(np.float32)); X, Y = X.astype(np.float64), Y.astype(np.float64)
    return grid, X, Y, p


def to_pseudo_lonlat(pts, grid):
    """Warped pixel coordinates -> lon/lat of the Web-Mercator square (lat_cut = 85.05 makes it exact).
    The frame's left wall becomes -180 whatever the geographic lon0: the square is its own world, and
    nothing may wrap, or polygons at the east wall would be torn across the antimeridian."""
    W, H = grid.W, grid.H
    if grid.kind == "equalarea":                      # the globe's periodic frame: true longitude, equal-area latitude
        lon = (pts[:, 0] / W * 360.0 + grid.lon0 + 180.0) % 360.0 - 180.0
        lat = np.degrees(np.arcsin(np.clip(1 - 2 * pts[:, 1] / H, -1, 1)))
        return np.stack([lon, lat], 1)
    lon = np.clip(pts[:, 0] / W * 360.0 - 180.0, -179.999, 179.999)
    ymax = math.log(math.tan(math.pi / 4 + math.radians(grid.lat_cut) / 2))
    ym = ymax * (1 - 2 * np.clip(pts[:, 1], 0, H) / H)
    lat = np.degrees(2 * np.arctan(np.exp(ym)) - math.pi / 2)
    return np.stack([lon, lat], 1)


def frame_clip(poly_rings_lonlat, grid):
    """A polygon (list of lon/lat rings) -> list of polygons in pixel coords, cut at the frame's walls.
    grid.xy wraps longitude into [0, W), so a polygon straddling the wall (Alaska at lon0 = -168) would
    otherwise be rasterised as a band across the whole world. Unwrap x along each ring, then intersect
    with the frame and with the frame shifted by one world width."""
    from shapely.geometry import Polygon, box
    from shapely.affinity import translate
    from shapely.validation import make_valid
    W, H = grid.W, grid.H; rings = []
    for ring in poly_rings_lonlat:
        c = np.asarray(ring, np.float64); x, y = grid.xy(c[:, 0], c[:, 1]); x = np.asarray(x, np.float64).copy()
        d = np.diff(x); jump = np.round(d / W); x[1:] -= np.cumsum(jump) * W      # unwrap: no consecutive jump above half a world
        rings.append(np.stack([x, y], 1))
    if len(rings[0]) < 4: return []
    try:
        poly = make_valid(Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]))
    except Exception:
        return []
    out = []
    xmin, xmax = poly.bounds[0], poly.bounds[2]
    for k in range(int(np.floor(xmin / W)), int(np.floor(xmax / W)) + 1):
        part = poly.intersection(box(k * W, -1e9, (k + 1) * W, 1e9))
        if part.is_empty: continue
        part = translate(part, xoff=-k * W)
        geoms = getattr(part, "geoms", [part])
        for g in geoms:
            if g.geom_type != "Polygon" or g.area < 1e-6: continue
            out.append([np.asarray(g.exterior.coords)] + [np.asarray(i.coords) for i in g.interiors])
    return out


NESTED = None          # set by build_map_tiles when city windows exist


def warp_ring_xy(pts_xy, X, Y, grid, max_seg=0.5):
    pts = render._densify(np.asarray(pts_xy, np.float64), max_seg=max_seg)
    wp = NESTED.warp(pts) if NESTED is not None else render.warp_points(pts, X, Y, X.shape[1] - 1)
    ll = to_pseudo_lonlat(wp, grid)
    return [[round(float(a), 5), round(float(b), 5)] for a, b in ll]


def warp_ring(ring, grid, X, Y, max_seg=0.5):
    c = np.asarray(ring, np.float64)
    if len(c) < 2: return None
    x, y = grid.xy(c[:, 0], c[:, 1]); pts = render._densify(np.stack([x, y], 1), max_seg=max_seg)
    wp = render.warp_points(pts, X, Y, X.shape[1] - 1)
    ll = to_pseudo_lonlat(wp, grid)
    return [[round(float(a), 5), round(float(b), 5)] for a, b in ll]


def warp_geojson(exp, src, dst, name_field=None, pop_field=None, level=None, keep=()):
    grid, X, Y, p = frame_mesh(exp)
    gj = json.load(open(src)); n = 0
    with open(dst, "w") as f:
        for feat in gj["features"]:
            g = feat["geometry"]; pr = feat.get("properties", {})
            if g is None or g["type"] not in ("Polygon", "MultiPolygon"): continue
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            out_polys = []
            for poly in polys:
                rings = [warp_ring(r, grid, X, Y) for r in poly]
                rings = [r for r in rings if r and len(r) >= 4]
                if rings: out_polys.append(rings)
            if not out_polys: continue
            props = {k: pr.get(k) for k in keep if k in pr}
            if name_field: props["name"] = pr.get(name_field)
            if pop_field: props["pop"] = pr.get(pop_field)
            if level is not None: props["level"] = level
            geom = {"type": "MultiPolygon", "coordinates": out_polys} if len(out_polys) > 1 else {"type": "Polygon", "coordinates": out_polys[0]}
            f.write(json.dumps({"type": "Feature", "properties": props, "geometry": geom}) + "\n"); n += 1
    print(f"wrote {n} features to {dst}")


if __name__ == "__main__":
    a = sys.argv
    warp_geojson(a[1], a[2], a[3], a[4] if len(a) > 4 else None, a[5] if len(a) > 5 else None, int(a[6]) if len(a) > 6 else None)


class NestedWarp:
    """V2: the global map with the city windows' composed maps inside them. Points (global mesh px) inside
    a window's lon/lat box are warped by that window's corner mesh (already composed with the global map);
    everything else by the global mesh. Windows are chosen by nearest centre where they overlap."""
    def __init__(self, exp, windows_dir=None):
        self.grid, self.X, self.Y, self.p = frame_mesh(exp); self.W = self.grid.W
        import glob
        self.windows = []
        for d in sorted(glob.glob(os.path.join(windows_dir or os.path.join(ROOT, "experiments", "nested"), "*", "mesh.npz"))):
            z = np.load(d); n = int(z["n"]); lon0, lat1, dx = float(z["lon0"]), float(z["lat1"]), float(z["dx"])
            self.windows.append({"name": os.path.basename(os.path.dirname(d)), "X": z["X"].astype(np.float64), "Y": z["Y"].astype(np.float64), "lon0": lon0, "lat1": lat1, "dx": dx, "n": n,
                                 "lon1": lon0 + n * dx, "lat0": lat1 - n * dx, "clon": lon0 + 0.5 * n * dx, "clat": lat1 - 0.5 * n * dx})

    def warp(self, pts):
        """pts: (N, 2) global mesh px -> warped global px."""
        pts = np.asarray(pts, np.float64); out = render.warp_points(pts, self.X, self.Y, self.W)
        if not self.windows: return out
        lon, lat = self.grid.lonlat(pts[:, 0] % self.W, pts[:, 1]); lon = np.asarray(lon); lat = np.asarray(lat)
        best = np.full(len(pts), -1); bestd = np.full(len(pts), np.inf)
        for k, w in enumerate(self.windows):
            inside = (lon >= w["lon0"]) & (lon < w["lon1"]) & (lat <= w["lat1"]) & (lat > w["lat0"])
            d = np.hypot(lon - w["clon"], lat - w["clat"]); take = inside & (d < bestd); best[take] = k; bestd[take] = d[take]
        from scipy import ndimage
        for k, w in enumerate(self.windows):
            m = best == k
            if not m.any(): continue
            u = (lon[m] - w["lon0"]) / w["dx"]; v = (w["lat1"] - lat[m]) / w["dx"]
            out[m, 0] = ndimage.map_coordinates(w["X"], [v, u], order=1, mode="nearest")
            out[m, 1] = ndimage.map_coordinates(w["Y"], [v, u], order=1, mode="nearest")
        return out
