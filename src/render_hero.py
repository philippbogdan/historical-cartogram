"""Hero render: regional colours, the original graticule through the warp, an inset of the ordinary map,
a people-square legend, proper labels.   python src/render_hero.py <experiment> [out_w] [graticule_step]"""
import colorsys, json, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render, layers
from hc.diffusion import quad_areas
from run import ROOT, RAW, load_mesh
from render_countries import country_ids
from rasterio import features
from rasterio.transform import Affine
from scipy import ndimage


def line_mask(lines, H, W, width_px=1):
    """Rasterise polylines (grid pixel coords) into a 0/1 mask; pushed through the same splat as the fills,
    so a coastline is drawn exactly where its land lands and a collapsed seam becomes a thin dark line
    instead of a spiky polyline."""
    shapes = [({"type": "LineString", "coordinates": [(float(x), float(y)) for x, y in ln]}, 1) for ln in lines if len(ln) > 1]
    m = features.rasterize(shapes, out_shape=(H, W), transform=Affine.identity(), fill=0, dtype="uint8", all_touched=True).astype(np.float32)
    if width_px > 1: m = ndimage.grey_dilation(m, size=(width_px, width_px))
    return m

FONT = next((f for f in ("Helvetica Neue", "Avenir Next", "Inter", "DejaVu Sans") if any(x.name == f for x in font_manager.fontManager.ttflist)), "DejaVu Sans")
plt.rcParams["font.family"] = FONT
OCEAN = np.array([0.965, 0.962, 0.950])
# hue families by UN subregion (Worldmapper-like regional colouring, muted for print)
FAMILY = {"Northern America": 0.60, "Central America": 0.08, "Caribbean": 0.08, "South America": 0.13,
          "Northern Europe": 0.72, "Western Europe": 0.78, "Southern Europe": 0.84, "Eastern Europe": 0.92,
          "Northern Africa": 0.03, "Western Asia": 0.98, "Central Asia": 0.95,
          "Western Africa": 0.24, "Eastern Africa": 0.28, "Middle Africa": 0.32, "Southern Africa": 0.36,
          "Southern Asia": 0.50, "Eastern Asia": 0.44, "South-Eastern Asia": 0.40,
          "Australia and New Zealand": 0.66, "Melanesia": 0.64, "Micronesia": 0.64, "Polynesia": 0.64}


def warped_country_ids(vectors, grid, X, Y, W, oh, ow, sc):
    """Country polygons densified, pushed through the warp vertex by vertex and rasterised at the OUTPUT
    resolution: borders stay crisp where the land is magnified (a source-pixel splat gives staircases there)."""
    gj = json.load(open(os.path.join(RAW, f"ne_{vectors}_admin_0_countries.geojson")))
    shapes = []; k = 0
    for f in gj["features"]:
        g = f["geometry"]
        if g["type"] not in ("Polygon", "MultiPolygon"): continue
        k += 1
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            rings = []
            for ring in poly:
                c = np.asarray(ring, np.float64); x, y = grid.xy(c[:, 0], c[:, 1])
                pts = render._densify(np.stack([x, y], 1), max_seg=0.5)
                wp = render.warp_points(pts, X, Y, W)
                rings.append([(float(px * sc), float(py * sc)) for px, py in wp])
            if len(rings[0]) >= 4: shapes.append(({"type": "Polygon", "coordinates": rings}, k))
    return features.rasterize(shapes, out_shape=(oh, ow), transform=Affine.identity(), fill=0, dtype="int32")


def draw_city_labels_big(ax, places, X, Y, W, scale, out_hw, color="#111", max_labels=120, base=1.0):
    """Like layers.draw_city_labels, with type sizes readable at a quarter of the pixel size."""
    oh, ow = out_hw; cell = 24
    occ = np.zeros((oh // cell + 2, ow // cell + 2), bool)
    pts = np.array([[p[1], p[2]] for p in places]); wp = render.warp_points(pts, X, Y, W); drawn = 0
    for (name, _, _, pop), (wx, wy) in zip(places, wp):
        fs = float(np.clip(11 + 4.5 * np.log10(max(pop, 1e5) / 1e6), 11, 22)) * base
        px, py = (wx % W) * scale, wy * scale
        w_cells = int(len(name) * fs * 0.62 * 100 / 72 / cell) + 2
        i, j = int(py // cell), int(px // cell)
        if i < 1 or i >= occ.shape[0] - 1 or j < 0 or j + w_cells >= occ.shape[1]: continue
        if occ[i - 1:i + 2, max(j - 1, 0):j + w_cells + 1].any(): continue
        occ[i - 1:i + 2, max(j - 1, 0):j + w_cells + 1] = True
        ax.plot(px, py, "o", ms=fs * 0.3, color=color, alpha=0.85)
        ax.text(px + fs * 0.5, py, name, fontsize=fs, color=color, va="center", ha="left")
        drawn += 1
        if drawn >= max_labels: break
    return drawn


def region_palette(vectors="50m"):
    gj = json.load(open(os.path.join(RAW, f"ne_{vectors}_admin_0_countries.geojson")))
    feats = [f for f in gj["features"] if f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
    subs = [f["properties"].get("SUBREGION", "") for f in feats]
    # within a family, lightness steps by the country's rank in longitude so neighbours differ
    lon = []
    for f in feats:
        c = f["geometry"]["coordinates"]; ring = c[0][0] if f["geometry"]["type"] == "MultiPolygon" else c[0]
        lon.append(float(np.mean([p[0] for p in ring])))
    cols = np.zeros((len(feats) + 1, 3)); cols[0] = OCEAN
    for sub in set(subs):
        idx = [i for i, s in enumerate(subs) if s == sub]; idx.sort(key=lambda i: lon[i])
        h = FAMILY.get(sub)
        for r, i in enumerate(idx):
            if h is None: cols[i + 1] = (0.88, 0.88, 0.87); continue        # Antarctica, open-ocean territories: neutral
            l = 0.70 + 0.16 * ((r * 0.618) % 1.0); s = 0.42
            cols[i + 1] = colorsys.hls_to_rgb(h, l, s)
    return cols


def draw_uncollapsed(ax, lines, X, Y, W, sc, color, lw, max_compression=7.0, area=None, min_area=0.05):
    """Coastlines through the warp, dropping the runs the solver squeezed into a seam: warped length below
    1/max_compression of the geographic length, or local area scale below min_area (the collapsed ocean)."""
    H_, W_ = area.shape if area is not None else (None, None)
    for ln in lines:
        wp = render.warp_points(ln, X, Y, W)
        d0 = np.hypot(*np.diff(ln, axis=0).T) + 1e-9; d1 = np.hypot(*np.diff(wp, axis=0).T)
        keep = d1 * max_compression >= d0
        if area is not None:
            ix = np.clip((ln[:, 0] % W).astype(int), 0, W_ - 1); iy = np.clip(ln[:, 1].astype(int), 0, H_ - 1)
            a = np.minimum.reduce([area[iy, ix], area[iy, np.clip(ix + 1, 0, W_ - 1)], area[iy, np.clip(ix - 1, 0, W_ - 1)], area[np.clip(iy + 1, 0, H_ - 1), ix], area[np.clip(iy - 1, 0, H_ - 1), ix]])
            keep &= (a[:-1] >= min_area) & (a[1:] >= min_area)
        i = 0
        while i < len(keep):
            if not keep[i]: i += 1; continue
            j = i
            while j < len(keep) and keep[j]: j += 1
            seg = wp[i:j + 1]
            if len(seg) > 3: ax.plot(seg[:, 0] * sc, seg[:, 1] * sc, color=color, lw=lw, solid_capstyle="round")
            i = j


def main(name, out_w=4096, grat_step=15):
    out = os.path.join(ROOT, "experiments", name); p = json.load(open(os.path.join(out, "params.json")))
    from warp_vectors import frame_mesh                      # population-aware fold repair, cached per experiment
    _, X, Y, _ = frame_mesh(name); X, Y = X.astype(np.float64), Y.astype(np.float64)
    draw_hero(X, Y, p, os.path.join(out, "hero.png"), out_w, grat_step)


def draw_hero(X, Y, p, out_png, out_w=4096, grat_step=15, title="THE WORLD, AREA = PEOPLE", subtitle=None, source=None, band=True, labels=True, overlay=None, legend_text="= 10 million people", legend_unit=1e7, corner_text=None):
    """One hero picture from a corner mesh (X, Y) on the frame's grid described by params p."""
    out = os.path.dirname(out_png)
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0)); H, W = grid.H, grid.W
    wrap = p.get("x_boundary", "periodic") == "periodic"
    oh, ow = int(round(H * out_w / W)), out_w; sc = ow / W
    vec = p.get("vectors", "50m")
    ids, names, pops = country_ids(grid, vec); cols = region_palette(vec); rgb = cols[ids]
    ids_out = warped_country_ids(vec, grid, X, Y, W, oh, ow, sc)
    img = cols[ids_out]
    if overlay is not None:                                   # a per-source-cell raster painted through the warp (the lens grammar)
        vals, cmap, vmin, vmax, alpha = overlay
        v = np.clip(render.splat(np.nan_to_num(vals, nan=vmin).astype(np.float64), X, Y, (oh, ow), wrap=wrap), vmin, vmax)
        col = plt.get_cmap(cmap)((v - vmin) / (vmax - vmin))[..., :3]
        land = (ids_out > 0)[..., None]
        img = np.where(land, img * (1 - alpha) + col * alpha, img)
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{vec}_admin_0_countries.geojson"), grid)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{vec}_coastline.geojson"), grid)
    grat = render.graticule(grid, grat_step)
    # lines of constant width in the OUTPUT domain, derived from the warped fills themselves, so a collapsed
    # seam becomes one thin dark line and no polyline overshoots through a fold:
    # coast = edge of the warped ocean coverage; borders = colour edges of the warped country fill
    lw_px = max(1, int(round(out_w / 2048)))
    oc = ndimage.gaussian_filter((ids_out == 0).astype(np.float64), 0.8)
    coast_a = np.clip(np.hypot(ndimage.sobel(oc, 0), ndimage.sobel(oc, 1)) * 1.2, 0, 1)
    coast_a = ndimage.grey_dilation(coast_a, size=(lw_px, lw_px))
    diff = np.zeros(ids_out.shape, bool); diff[:, 1:] |= ids_out[:, 1:] != ids_out[:, :-1]; diff[1:, :] |= ids_out[1:, :] != ids_out[:-1, :]
    border_a = ndimage.grey_dilation(diff.astype(np.float64), size=(lw_px, lw_px)) * (1 - coast_a)
    img = img * (1 - 0.65 * border_a[..., None]) + np.array([1, 1, 1]) * 0.65 * border_a[..., None]
    img = img * (1 - 0.85 * coast_a[..., None]) + np.array([0.27, 0.27, 0.27]) * 0.85 * coast_a[..., None]
    band = int(0.13 * oh) if band else 0; fig = plt.figure(figsize=(ow / 100, (oh + band) / 100), dpi=100, facecolor="white")
    ax = fig.add_axes([0, band / (oh + band), 1, oh / (oh + band)]); ax.set_axis_off(); ax.set_xlim(0, ow); ax.set_ylim(oh, 0)
    ax.imshow(np.clip(img, 0, 1), extent=(0, ow, oh, 0), interpolation="nearest")
    render._add_lines(ax, grat, X, Y, W, sc, "#00000040", 0.6)          # the original graticule, stretched
    A = np.abs(quad_areas(X, Y))
    # country labels at area-weighted centroids of the warped area
    cx = (X[:-1, :-1] + X[:-1, 1:] + X[1:, :-1] + X[1:, 1:]) / 4; cy = (Y[:-1, :-1] + Y[:-1, 1:] + Y[1:, :-1] + Y[1:, 1:]) / 4
    total = A.sum(); flat = ids.ravel(); order = np.argsort(flat); sid = flat[order]
    st = np.searchsorted(sid, np.arange(1, len(names) + 1)); en = np.searchsorted(sid, np.arange(1, len(names) + 1), side="right")
    Af, cxf, cyf = A.ravel()[order], (cx.ravel() % W)[order], cy.ravel()[order]
    for k, nm in enumerate(names):
        s, e = st[k], en[k]
        if e <= s or not labels: continue
        a = Af[s:e]; share = a.sum() / total
        if share < 0.0008: continue
        ang = cxf[s:e] / W * 2 * np.pi
        mx = (np.arctan2((np.sin(ang) * a).sum(), (np.cos(ang) * a).sum()) / (2 * np.pi)) % 1.0 * W; my = (cyf[s:e] * a).sum() / a.sum()
        fs = float(np.clip(12 + 110 * np.sqrt(share), 13, 96)) * out_w / 4096
        ax.text(mx * sc, my * sc, nm.upper() if share > 0.01 else nm, fontsize=fs, ha="center", va="center", color="#222", alpha=0.85, fontweight="medium" if share > 0.01 else "normal")
    if labels:
        places = layers.cities(os.path.join(RAW, "ne_10m_populated_places_simple.geojson"), grid, n=400)
        draw_city_labels_big(ax, places, X, Y, W, sc, (oh, ow), color="#1a1a1a", max_labels=120, base=out_w / 4096)
    # caption band: title and explanation (left), the people square (middle), the ordinary map (right)
    if corner_text:
        ax.text(0.012 * ow, 0.015 * oh, corner_text, fontsize=30 * out_w / 4096, fontweight="bold", color="#111", va="top", bbox=dict(facecolor="#ffffffcc", edgecolor="none", pad=6))
    if not band:
        fig.savefig(out_png, dpi=100); plt.close(fig); print("wrote", out_png); return
    mpath = os.path.join(out, "metrics.json"); met = json.load(open(mpath)) if os.path.exists(mpath) else {}
    pop = met.get("population") or p.get("population") or 8.191e9          # GHS-POP 2025 world total as the fallback
    ppp = pop / (W * H)
    side = np.sqrt(legend_unit / ppp) * sc             # pixels holding one legend unit (10 million people by default)
    cap = fig.add_axes([0, 0, 1, band / (oh + band)]); cap.set_axis_off(); cap.set_xlim(0, ow); cap.set_ylim(band, 0)
    fs = out_w / 4096
    cap.text(0.015 * ow, 0.20 * band, title, fontsize=64 * fs, fontweight="bold", color="#111", va="center")
    cap.text(0.015 * ow, 0.50 * band, subtitle or f"Every part of the picture holds as many people as its area says: the square is 10 million people, the whole frame {pop/1e9:.2f} billion.\nCoastlines and borders are drawn where they land. The grey lines are the ordinary 15° graticule, stretched with the land.",
             fontsize=26 * fs, color="#333", va="center", linespacing=1.5)
    cap.text(0.015 * ow, 0.82 * band, source or f"Optimal transport of the GHS-POP 2025 population raster (100 m), land pure, ocean kept at {100 * p.get('ocean_share', 0):.0f}% of the frame. Colours follow UN subregions.", fontsize=19 * fs, color="#666", va="center")
    sx = 0.56 * ow; cap.add_patch(plt.Rectangle((sx, 0.5 * band - side / 2), side, side, facecolor="#ffffff", edgecolor="#222", lw=1.2))
    cap.text(sx + side + 0.006 * ow, 0.5 * band, legend_text, fontsize=26 * fs, va="center", color="#222")
    _, y_top = grid.xy(0.0, 76.0); _, y_bot = grid.xy(0.0, -58.0)          # inset shows 58S to 76N
    ih = 0.86 * band; iw = ih * W / (y_bot - y_top)
    ins = fig.add_axes([0.985 - iw / ow, (band - ih) / 2 / (oh + band), iw / ow, ih / (oh + band)]); ins.imshow(rgb, extent=(0, W, H, 0), interpolation="nearest")
    for ln in coast: ins.plot(ln[:, 0], ln[:, 1], color="#4a4a4a", lw=0.3)
    ins.set_xlim(0, W); ins.set_ylim(y_bot, y_top); ins.set_xticks([]); ins.set_yticks([])
    for sp in ins.spines.values(): sp.set_edgecolor("#222"); sp.set_linewidth(0.8)
    ins.set_title("the same colours on the ordinary map", fontsize=19 * fs, color="#333", pad=6)
    fig.savefig(out_png, dpi=100); plt.close(fig); print("wrote", out_png, FONT)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4096, int(sys.argv[3]) if len(sys.argv) > 3 else 15)
