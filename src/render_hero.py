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
    X, Y, rho0 = load_mesh(out); X, Y = X.astype(np.float64), Y.astype(np.float64)
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0)); H, W = grid.H, grid.W
    wrap = p.get("x_boundary", "periodic") == "periodic"
    oh, ow = int(round(H * out_w / W)), out_w; sc = ow / W
    vec = p.get("vectors", "50m")
    ids, names, pops = country_ids(grid, vec); cols = region_palette(vec); rgb = cols[ids]
    img = np.stack([render.splat(rgb[..., c], X, Y, (oh, ow), wrap=wrap) for c in range(3)], -1)
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{vec}_admin_0_countries.geojson"), grid)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{vec}_coastline.geojson"), grid)
    grat = render.graticule(grid, grat_step)
    # lines of constant width in the OUTPUT domain, derived from the warped fills themselves, so a collapsed
    # seam becomes one thin dark line and no polyline overshoots through a fold:
    # coast = edge of the warped ocean coverage; borders = colour edges of the warped country fill
    oc = np.clip(render.splat((ids == 0).astype(np.float64), X, Y, (oh, ow), wrap=wrap), 0, 1)
    oc = ndimage.gaussian_filter(oc, 1.2)                                       # soften fold bristles before the edge
    coast_a = np.clip(np.hypot(ndimage.sobel(oc, 0), ndimage.sobel(oc, 1)) * 1.2, 0, 1)
    cedge = sum(np.hypot(ndimage.sobel(img[..., c], 0), ndimage.sobel(img[..., c], 1)) for c in range(3))
    border_a = np.clip(cedge * 2.5, 0, 1) * (1 - coast_a)
    img = img * (1 - 0.65 * border_a[..., None]) + np.array([1, 1, 1]) * 0.65 * border_a[..., None]
    img = img * (1 - 0.85 * coast_a[..., None]) + np.array([0.27, 0.27, 0.27]) * 0.85 * coast_a[..., None]
    band = int(0.13 * oh); fig = plt.figure(figsize=(ow / 100, (oh + band) / 100), dpi=100, facecolor="white")
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
        if e <= s: continue
        a = Af[s:e]; share = a.sum() / total
        if share < 0.0006: continue
        ang = cxf[s:e] / W * 2 * np.pi
        mx = (np.arctan2((np.sin(ang) * a).sum(), (np.cos(ang) * a).sum()) / (2 * np.pi)) % 1.0 * W; my = (cyf[s:e] * a).sum() / a.sum()
        fs = float(np.clip(7 + 70 * np.sqrt(share), 7, 54)) * out_w / 4096
        ax.text(mx * sc, my * sc, nm.upper() if share > 0.01 else nm, fontsize=fs, ha="center", va="center", color="#222", alpha=0.85, fontweight="medium" if share > 0.01 else "normal")
    places = layers.cities(os.path.join(RAW, "ne_10m_populated_places_simple.geojson"), grid, n=400)
    layers.draw_city_labels(ax, places, X, Y, W, sc, (oh, ow), color="#1a1a1a", max_labels=160)
    # caption band: title and explanation (left), the people square (middle), the ordinary map (right)
    mpath = os.path.join(out, "metrics.json"); met = json.load(open(mpath)) if os.path.exists(mpath) else {}
    pop = met.get("population") or p.get("population") or 8.191e9          # GHS-POP 2025 world total as the fallback
    ppp = pop / (W * H)
    side = np.sqrt(1e7 / ppp) * sc                     # pixels holding 10 million people
    cap = fig.add_axes([0, 0, 1, band / (oh + band)]); cap.set_axis_off(); cap.set_xlim(0, ow); cap.set_ylim(band, 0)
    fs = out_w / 4096
    cap.text(0.015 * ow, 0.22 * band, "THE WORLD, AREA = PEOPLE", fontsize=34 * fs, fontweight="bold", color="#111", va="center")
    cap.text(0.015 * ow, 0.50 * band, f"Every part of the picture holds as many people as its area says: the square is 10 million people, the whole frame {pop/1e9:.2f} billion.\nCoastlines and borders are drawn where they land. The grey lines are the ordinary 15° graticule, stretched with the land.",
             fontsize=14 * fs, color="#333", va="center", linespacing=1.5)
    cap.text(0.015 * ow, 0.82 * band, f"Optimal transport of the GHS-POP 2025 population raster (100 m), land pure, ocean kept at {100 * p.get('ocean_share', 0):.0f}% of the frame. Colours follow UN subregions.", fontsize=11.5 * fs, color="#666", va="center")
    sx = 0.60 * ow; cap.add_patch(plt.Rectangle((sx, 0.5 * band - side / 2), side, side, facecolor="#ffffff", edgecolor="#222", lw=1.2))
    cap.text(sx + side + 0.006 * ow, 0.5 * band, "= 10 million people", fontsize=14 * fs, va="center", color="#222")
    _, y_top = grid.xy(0.0, 76.0); _, y_bot = grid.xy(0.0, -58.0)          # inset shows 58S to 76N
    ih = 0.86 * band; iw = ih * W / (y_bot - y_top)
    ins = fig.add_axes([0.985 - iw / ow, (band - ih) / 2 / (oh + band), iw / ow, ih / (oh + band)]); ins.imshow(rgb, extent=(0, W, H, 0), interpolation="nearest")
    for ln in coast: ins.plot(ln[:, 0], ln[:, 1], color="#4a4a4a", lw=0.3)
    ins.set_xlim(0, W); ins.set_ylim(y_bot, y_top); ins.set_xticks([]); ins.set_yticks([])
    for sp in ins.spines.values(): sp.set_edgecolor("#222"); sp.set_linewidth(0.8)
    ins.set_title("the same colours on the ordinary map", fontsize=11 * fs, color="#333", pad=4)
    fig.savefig(os.path.join(out, "hero.png"), dpi=100); plt.close(fig); print("wrote", os.path.join(out, "hero.png"), FONT)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4096, int(sys.argv[3]) if len(sys.argv) > 3 else 15)
