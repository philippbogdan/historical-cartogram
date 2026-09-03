"""V16/V18: warped vector tiles for the interactive map. Countries (with region colours, shares, bboxes),
coastline, provinces (NE 10m admin-1), urban centres (GHS-UCDB), districts (geoBoundaries ADM2), graticule,
each pushed through the frame's warp into pseudo lon/lat and packed with tippecanoe into PMTiles.
    python src/build_map_tiles.py <experiment> [layers: countries,admin1,cities,admin2,graticule]"""
import colorsys, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from hc.diffusion import quad_areas
from run import ROOT, RAW
from warp_vectors import frame_mesh, warp_ring, warp_ring_xy, frame_clip, to_pseudo_lonlat, NestedWarp
import warp_vectors
from render_countries import country_ids
from render_hero import region_palette

SITE = os.path.join(ROOT, "site", "map"); TILES = os.path.join(SITE, "tiles"); TMP = os.path.join(ROOT, "data", "derived", "map_tmp")
BND = os.path.join(RAW, "boundaries")


def hexc(rgb): return "#%02x%02x%02x" % tuple(int(round(255 * c)) for c in rgb)


def write_features(path, feats):
    with open(path, "w") as f:
        for ft in feats: f.write(json.dumps(ft) + "\n")


def warp_polys(g, grid, X, Y):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    out = []
    for poly in polys:
        for part in frame_clip(poly, grid):                       # cut at the frame's walls before warping
            rings = [warp_ring_xy(r, X, Y, grid) for r in part]; rings = [r for r in rings if r and len(r) >= 4]
            if rings: out.append(rings)
    if not out: return None
    return {"type": "MultiPolygon", "coordinates": out} if len(out) > 1 else {"type": "Polygon", "coordinates": out[0]}


def bbox(geom):
    pts = np.array([p for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]) for ring in poly for p in ring])
    return [float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max())]


def tippecanoe(out, layers, maxzoom):
    args = ["tippecanoe", "-o", out, "-f", "-z", str(maxzoom), "--drop-densest-as-needed", "--extend-zooms-if-still-dropping", "--no-tile-size-limit", "--simplification=4"]
    for name, path in layers: args += ["-L", f"{name}:{path}"]
    subprocess.run(args, check=True, capture_output=True); print("tiles:", os.path.basename(out), f"{os.path.getsize(out)/1e6:.1f} MB")


def main(exp, layers):
    global TILES, TMP
    grid, X, Y, p = frame_mesh(exp); W, H = grid.W, grid.H
    if grid.kind != "equalarea":                                   # V2: the city windows' composed maps ride inside the flat map
        warp_vectors.NESTED = NestedWarp(exp); print("nested windows:", len(warp_vectors.NESTED.windows))
    if grid.kind == "equalarea": TILES = os.path.join(SITE, "tiles_globe"); TMP = TMP + "_globe"     # the globe's tile set
    os.makedirs(TILES, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    ids, names, pops = country_ids(grid, "50m"); cols = region_palette("50m")
    A = np.abs(quad_areas(X, Y)); share = np.bincount(ids.ravel(), weights=A.ravel(), minlength=len(names) + 1)[1:] / A.sum()
    gj = json.load(open(os.path.join(RAW, "ne_50m_admin_0_countries.geojson")))
    feats_c = [f for f in gj["features"] if f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
    colour_of = {}
    if "countries" in layers:
        out = []
        for k, f in enumerate(feats_c):
            g = warp_polys(f["geometry"], grid, X, Y)
            if g is None: continue
            pr = f["properties"]; iso = pr.get("ISO_A3") or pr.get("ADM0_A3"); colour_of[iso] = cols[k + 1]
            out.append({"type": "Feature", "properties": {"name": pr.get("NAME"), "iso": iso, "pop": float(pr.get("POP_EST") or 0), "share": float(share[k]), "fill": hexc(cols[k + 1]), "bbox": json.dumps(bbox(g)), "region": pr.get("SUBREGION")}, "geometry": g})
        write_features(os.path.join(TMP, "countries.geojsonl"), out)
        coast = render.lines_from_geojson(os.path.join(RAW, "ne_50m_coastline.geojson"), grid); cl = []
        for ln in coast:
            pts = render._densify(np.asarray(ln, np.float64), max_seg=0.5); wp = render.warp_points(pts, X, Y, W); ll = to_pseudo_lonlat(wp, grid)
            cl.append({"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[round(float(a), 5), round(float(b), 5)] for a, b in ll]}})
        write_features(os.path.join(TMP, "coast.geojsonl"), cl)
        tippecanoe(os.path.join(TILES, "countries.pmtiles"), [("countries", os.path.join(TMP, "countries.geojsonl")), ("coast", os.path.join(TMP, "coast.geojsonl"))], 9)
        print("countries:", len(out))
    else:
        for k, f in enumerate(feats_c): colour_of[f["properties"].get("ISO_A3") or f["properties"].get("ADM0_A3")] = cols[k + 1]
    if "admin1" in layers:
        gj1 = json.load(open(os.path.join(BND, "ne_10m_admin_1_states_provinces.geojson"))); out = []; count = {}
        for f in gj1["features"]:
            if f["geometry"] is None or f["geometry"]["type"] not in ("Polygon", "MultiPolygon"): continue
            pr = f["properties"]; iso = pr.get("adm0_a3"); base = colour_of.get(iso, (0.85, 0.85, 0.85))
            i = count.get(iso, 0); count[iso] = i + 1
            h, l, s = colorsys.rgb_to_hls(*base); fill = colorsys.hls_to_rgb(h, min(0.92, max(0.55, l + 0.12 * (((i * 0.618) % 1.0) - 0.5))), s)
            g = warp_polys(f["geometry"], grid, X, Y)
            if g is None: continue
            out.append({"type": "Feature", "properties": {"name": pr.get("name"), "iso": iso, "fill": hexc(fill)}, "geometry": g})
        write_features(os.path.join(TMP, "admin1.geojsonl"), out); tippecanoe(os.path.join(TILES, "admin1.pmtiles"), [("admin1", os.path.join(TMP, "admin1.geojsonl"))], 10); print("admin1:", len(out))
    if "cities" in layers:
        import pyogrio.raw, shapely
        meta_, _, wkb, fields = pyogrio.raw.read(os.path.join(BND, "GHS_STAT_UCDB2015MT_GLOBE_R2019A", "GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_2.gpkg"), columns=["UC_NM_MN", "CTR_MN_NM", "P15"], return_fids=False)
        col = {n: fields[i] for i, n in enumerate(meta_["fields"])}          # field order follows the file, not the request
        out = []
        for geom_wkb, name, ctr, p15 in zip(wkb, col["UC_NM_MN"], col["CTR_MN_NM"], col["P15"]):
            geom = shapely.from_wkb(geom_wkb)
            geom = geom.buffer(0.012, join_style="round").buffer(-0.012, join_style="round").simplify(0.003)   # the 1 km raster staircase would become spikes under the warp
            if geom.is_empty: continue
            gg = geom.__geo_interface__
            g = warp_polys(gg, grid, X, Y)
            if g is None: continue
            out.append({"type": "Feature", "properties": {"name": name, "country": ctr, "pop": float(p15 or 0)}, "geometry": g})
        write_features(os.path.join(TMP, "cities.geojsonl"), out); tippecanoe(os.path.join(TILES, "cities.pmtiles"), [("cities", os.path.join(TMP, "cities.geojsonl"))], 11); print("cities:", len(out))
    if "admin2" in layers:
        gj2 = json.load(open(os.path.join(BND, "geoBoundariesCGAZ_ADM2.geojson"))); out = []
        for f in gj2["features"]:
            if f["geometry"] is None or f["geometry"]["type"] not in ("Polygon", "MultiPolygon"): continue
            pr = f["properties"]; g = warp_polys(f["geometry"], grid, X, Y)
            if g is None: continue
            out.append({"type": "Feature", "properties": {"name": pr.get("shapeName"), "iso": pr.get("shapeGroup")}, "geometry": g})
        del gj2
        write_features(os.path.join(TMP, "admin2.geojsonl"), out); tippecanoe(os.path.join(TILES, "admin2.pmtiles"), [("admin2", os.path.join(TMP, "admin2.geojsonl"))], 11); print("admin2:", len(out))
    if "graticule" in layers:
        out = []
        for ln in render.graticule(grid, 15):
            wp = render.warp_points(np.asarray(ln, np.float64), X, Y, W); ll = to_pseudo_lonlat(wp, grid)
            out.append({"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[round(float(a), 5), round(float(b), 5)] for a, b in ll]}})
        write_features(os.path.join(TMP, "graticule.geojsonl"), out); tippecanoe(os.path.join(TILES, "graticule.pmtiles"), [("graticule", os.path.join(TMP, "graticule.geojsonl"))], 8)
    mpath = os.path.join(ROOT, "experiments", exp, "metrics.json"); met = json.load(open(mpath)) if os.path.exists(mpath) else {}
    pop = met.get("population") or 8.191e9
    json.dump({"experiment": exp, "W": W, "H": H, "lon0": grid.lon0, "people_per_px": pop / (W * H), "population": pop,
               "region_colours": {k: hexc(v) for k, v in zip([f["properties"].get("SUBREGION") for f in feats_c], cols[1:])}}, open(os.path.join(SITE, "meta_globe.json" if grid.kind == "equalarea" else "meta.json"), "w"), indent=1)
    print("meta.json written")


if __name__ == "__main__":
    main(sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "countries,admin1,cities,admin2,graticule").split(","))
