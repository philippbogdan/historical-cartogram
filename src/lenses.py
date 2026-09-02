"""Phase 7 lenses. A lens = (measure for AREA, measure for COLOUR, moment).
    python src/lenses.py gdp <width>            L2/L4: the dollar world (area = GDP PPP 2015, Kummu 2018)
    python src/lenses.py ratio <experiment>     L9: layers through today's warp as per-capita maps (lights, roads)
    python src/lenses.py peak <experiment>      T6: epoch of maximum density painted on today's frame
    python src/lenses.py lonely <width>         L6: the complement metric, area ~ 1/rho (where empty places are vast)
"""
import json, os, sys, time
import numpy as np
OCEAN = float(os.environ.get("HC_OCEAN", "0.05")); TAG = os.environ.get("HC_TAG", "")   # 20% ocean hero variants: HC_OCEAN=0.2 HC_TAG=_o20
import rasterio
from rasterio.enums import Resampling
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion, ot_poisson, render
from run import load_mesh, ROOT, RAW, render_all
from render_countries import country_ids, palette

lon0, xb = -168.0, "wall"


def _solve(name, P, grid, sigma_km, ocean_share, extra, log=print, shares=(0.95, 0.999)):
    out = os.path.join(ROOT, "experiments", name); os.makedirs(out, exist_ok=True)
    sigma_px = sigma_km / grid.km_per_px_equator()
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
    t0 = time.time()
    po, _ = ot_poisson.spectral_homotopy(P, list(shares), sigma_px, xb, iters=400, damping=0.5, log=lambda s: None, ocean=ocean, ocean_share=ocean_share)
    X, Y = po.mesh(); m = diffusion.equalisation_metrics(po.rho0, X, Y); r, f = po.residual(); m.update({"residual": r, "cell_folds": f, "seconds": time.time() - t0})
    params = {"name": name, "method": "ot_spectral_homotopy", "grid": "mercator", "lat_cut": grid.lat_cut, "lon0": lon0, "width": grid.W, "W": grid.W, "H": grid.H, "x_boundary": xb,
              "floor": (1 - shares[-1]) / shares[-1], "share": shares[-1], "ocean_share": ocean_share, "sigma_km": sigma_km, "sigma_px": sigma_px, "vectors": "50m", **extra}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=1); json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=po.rho0.astype(np.float32))
    open(os.path.join(out, "log.txt"), "w").write(json.dumps(m) + "\n")
    render_all(out, grid, X, Y, po.rho0, params, log=lambda s: None)
    log(f"{name}: p05/p95 {m['log_ratio_popweighted_p05']:+.3f}/{m['log_ratio_popweighted_p95']:+.3f} folds {m['folds']} {time.time()-t0:.0f}s")
    return out


def read_lonlat_raster(path, band=1, out_w=8640):
    with rasterio.open(path) as src:
        h = int(round(src.height * out_w / src.width)); a = src.read(band, out_shape=(h, out_w), resampling=Resampling.average).astype(np.float64)
        b = src.bounds; a = np.nan_to_num(a); nod = src.nodata
        if nod is not None: a[np.isclose(a, nod)] = 0
        a[a < 0] = 0
        return a, (b.left, b.bottom, b.right, b.top)


def gdp(width):
    import netCDF4
    ds = netCDF4.Dataset(os.path.join(RAW, "lenses", "GDP_PPP_1990_2015_5arcmin_v2.nc"))
    var = [v for v in ds.variables if "GDP" in v or "gdp" in v][0]; v = ds.variables[var]
    a = np.array(v[-1], dtype=np.float64); a = np.nan_to_num(a); a[a < 0] = 0     # last time slice = 2015
    lat = ds.variables[[k for k in ds.variables if k.lower().startswith("lat")][0]][:]
    if lat[0] < lat[-1]: a = a[::-1]
    grid = prep.Grid("mercator", width, lon0=lon0); P, _ = prep.to_grid(a, (-180, -90, 180, 90), grid)
    print(f"GDP PPP 2015 total {a.sum()/1e12:.1f} trillion (2011 USD)")
    _solve(f"L4_gdp_{width}{TAG}", P, grid, 60.0, OCEAN, {"source": "Kummu, Taka & Guillaume 2018, GDP PPP 2015, 5 arcmin, CC0", "honesty": "downscaled from national and subnational statistics", "measure": "GDP PPP 2015"})


def lonely(width):
    from run import get_lonlat, NCOLS
    from hc.diffusion import prepare_density
    grid = prep.Grid("mercator", width, lon0=lon0)
    factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * width)))
    counts, bounds = get_lonlat(factor); P, _ = prep.to_grid(counts, bounds, grid)
    sigma_px = 60.0 / grid.km_per_px_equator()
    rho = prepare_density(P, 0.001, sigma_px, xb)          # people, smoothed, mean 1
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
    inv = 1.0 / np.maximum(rho, 1e-3); inv[ocean] = 0.0   # the loneliness measure on land: 1/rho
    _solve(f"L6_lonely_{width}", inv, grid, 0.0, 0.05, {"source": "1 / population density (GHS-POP 2025, 60 km smoothing), land only", "honesty": "the complement metric", "measure": "1/rho"}, shares=(0.95, 0.99))


def ratio(exp):
    out = os.path.join(ROOT, "experiments", exp); p = json.load(open(os.path.join(out, "params.json")))
    X, Y, _ = load_mesh(out); X, Y = X.astype(np.float64), Y.astype(np.float64)
    grid = prep.Grid(p["grid"], p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0)); wrap = p.get("x_boundary") == "periodic"
    coast = render.lines_from_geojson(os.path.join(RAW, "ne_50m_coastline.geojson"), grid)
    # night lights: radiance-like value per cell (mean over the cell), through the warp -> light per person
    bm, bb = read_lonlat_raster(os.path.join(RAW, "lenses", "BlackMarble_2016_3km_geo.tif"), band=1)
    L, _ = prep.to_grid(bm, bb, grid)  # brightness summed per source cell
    from run import get_lonlat, NCOLS
    factor = max(d for d in prep.divisors(NCOLS) if d <= max(1, NCOLS // (2 * grid.W)))
    counts, bounds = get_lonlat(factor); Pp, _ = prep.to_grid(counts, bounds, grid)   # people per source cell
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
    ref = L[~ocean].sum() / Pp[~ocean].sum()   # world-average light per person
    pc = L / np.maximum(Pp, 50.0)               # light per person per source cell (cells under 50 people are noise)
    v = np.log10((pc + 0.02 * ref) / ref); v[ocean] = np.nan; v[Pp < 50] = np.nan   # 0 = world average, +-1 = 10x
    render.draw(X, Y, np.ones(L.shape, np.uint8), os.path.join(out, "lens_lights.png"), min(grid.W, 4096), coast=coast, raster=v, cmap="RdBu_r", vmin=-1.5, vmax=1.5,
                title="night lights (Black Marble 2016) through the population warp = LIGHT PER PERSON (L9). White = world average, red = 10x more light per person, blue = 10x less", wrap=wrap)
    # roads: GRIP4 density (m per km2) -> road length per output cell -> road per person
    with open(os.path.join(RAW, "grip4", "grip4_total_dens_m_km2.asc")) as f:
        hdr = {}; 
        for _ in range(6):
            k, v = f.readline().split(); hdr[k.lower()] = float(v)
    R = np.loadtxt(os.path.join(RAW, "grip4", "grip4_total_dens_m_km2.asc"), skiprows=6); R[R == hdr.get("nodata_value", -9999)] = 0; R[R < 0] = 0
    cs = hdr["cellsize"]; nr, nc = R.shape; left = hdr["xllcorner"]; bottom = hdr["yllcorner"]
    lat_c = bottom + (nr - np.arange(nr) - 0.5) * cs
    area = (cs * 111.32) ** 2 * np.cos(np.radians(lat_c))[:, None]
    Rk = R * area / 1000.0  # km of road per source cell
    Rg, _ = prep.to_grid(Rk, (left, bottom, left + nc * cs, bottom + nr * cs), grid)
    refr = Rg[~ocean].sum() / Pp[~ocean].sum()
    pr = Rg / np.maximum(Pp, 50.0)
    vr = np.log10((pr + 0.02 * refr) / refr); vr[ocean] = np.nan; vr[Pp < 50] = np.nan
    render.draw(X, Y, np.ones(Rg.shape, np.uint8), os.path.join(out, "lens_roads.png"), min(grid.W, 4096), coast=coast, raster=vr, cmap="RdBu_r", vmin=-1.5, vmax=1.5,
                title="road length (GRIP4) through the population warp = ROAD PER PERSON (L9). White = world average, red = 10x more, blue = 10x less", wrap=wrap)
    print("wrote lens_lights.png, lens_roads.png in", out)


def peak(exp):
    out = os.path.join(ROOT, "experiments", exp); p = json.load(open(os.path.join(out, "params.json")))
    X, Y, _ = load_mesh(out); X, Y = X.astype(np.float64), Y.astype(np.float64)
    grid = prep.Grid(p["grid"], p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
    pk = np.load(os.path.join(ROOT, "experiments", "timeline", f"T6_peak_year_{grid.W}.npy")).astype(np.float64)
    coast = render.lines_from_geojson(os.path.join(RAW, "ne_50m_coastline.geojson"), grid)
    v = np.where(np.isnan(pk), 1700, pk)
    render.draw(X, Y, np.ones(v.shape, np.uint8), os.path.join(out, "lens_peak_year.png"), min(grid.W, 4096), coast=coast, raster=v, cmap="viridis", vmin=1900, vmax=2023, title="epoch of maximum population per cell, HYDE 3.3 (T6): yellow = still growing in 2023, dark = peaked before 1900", wrap=p.get("x_boundary") == "periodic")
    print("wrote lens_peak_year.png")


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"gdp": lambda: gdp(int(sys.argv[2])), "ratio": lambda: ratio(sys.argv[2]), "peak": lambda: peak(sys.argv[2]), "lonely": lambda: lonely(int(sys.argv[2]))}[cmd]()
