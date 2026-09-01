"""Phase 9: the static site.
    python src/build_site.py tiles <experiment> [maxz]   A12/V10: pre-rendered warped tiles for the flat viewer
    python src/build_site.py time [width]                V4: timeline frames (1024 px JPEG) + frames.json
    python src/build_site.py pages                       index, lenses, geometry pages; copies key renders
"""
import glob, json, os, shutil, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from run import ROOT
SITE = os.path.join(ROOT, "site")


def tiles(exp, maxz=5):
    import serve_warped as sw
    wp = sw.Warped(exp)
    root = os.path.join(SITE, "flat", "tiles"); os.makedirs(root, exist_ok=True)
    n = 0
    for layer, mode in (("pop", "max"), ("country", "max")):
        for z in range(0, maxz + 1):
            for x in range(2 ** z):
                for y in range(2 ** z):
                    d = os.path.join(root, layer, str(z), str(x)); os.makedirs(d, exist_ok=True)
                    f = os.path.join(d, f"{y}.png")
                    if os.path.exists(f): continue
                    png = wp.tile(z, x, y, layer=layer, mode=mode)
                    if png: open(f, "wb").write(png); n += 1
        print(layer, "done", flush=True)
    cities = json.load(open(os.path.join(SITE, "globe", "data", glob.glob(os.path.join(SITE, "globe", "data", "e*"))[0].split("/")[-1], "cities.json"))) if False else None
    # city labels in the flat frame: warped positions in mesh px from the experiment mesh
    from hc import prep, render, layers
    from run import RAW
    p = json.load(open(os.path.join(ROOT, "experiments", exp, "params.json")))
    z = np.load(os.path.join(ROOT, "experiments", exp, "mesh.npz")); X, Y = z["X"].astype(np.float64), z["Y"].astype(np.float64)
    grid = prep.Grid(p["grid"], p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
    places = layers.cities(os.path.join(RAW, "ne_10m_populated_places_simple.geojson"), grid, n=400)
    pts = np.array([[pl[1], pl[2]] for pl in places]); wpts = render.warp_points(pts, X, Y, grid.W)
    json.dump([{"name": pl[0], "pop": pl[3], "x": float(wx % grid.W) / grid.W, "y": float(wy) / grid.H} for pl, (wx, wy) in zip(places, wpts)], open(os.path.join(SITE, "flat", "cities.json"), "w"))
    json.dump({"experiment": exp, "maxz": maxz, "W": grid.W, "H": grid.H, "share": p.get("share"), "ocean_share": p.get("ocean_share"), "note": "land = people, ocean 5% of the frame, walls at the Bering Strait"}, open(os.path.join(SITE, "flat", "meta.json"), "w"), indent=1)
    print("tiles written:", n)


def time_frames(width=2048):
    src = os.path.join(ROOT, "experiments", "timeline"); dst = os.path.join(SITE, "time", "frames"); os.makedirs(dst, exist_ok=True)
    frames = []
    for d in sorted(glob.glob(os.path.join(src, "t_base_*"))):
        if not os.path.exists(os.path.join(d, "metrics.json")): continue
        p = json.load(open(os.path.join(d, "params.json"))); m = json.load(open(os.path.join(d, "metrics.json")))
        pic = os.path.join(d, "countries.png") if os.path.exists(os.path.join(d, "countries.png")) else os.path.join(d, "cartogram.png")
        name = f"{p['year']:+06d}.jpg"; out = os.path.join(dst, name)
        if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(pic):
            im = Image.open(pic).convert("RGB"); im.thumbnail((1024, 1024)); im.save(out, quality=85)
        frames.append({"year": p["year"], "file": name, "population": m.get("population", m.get("total")), "honesty": p.get("honesty", ""), "error_p05": m["log_ratio_popweighted_p05"], "error_p95": m["log_ratio_popweighted_p95"]})
    frames.sort(key=lambda f: f["year"])
    json.dump(frames, open(os.path.join(SITE, "time", "frames.json"), "w"), indent=1)
    print("frames:", len(frames))


def pages():
    ex = os.path.join(ROOT, "experiments"); img = os.path.join(SITE, "img"); os.makedirs(img, exist_ok=True)
    def cp(src, name, maxw=2048):
        if os.path.exists(src):
            im = Image.open(src).convert("RGB"); im.thumbnail((maxw, maxw)); im.save(os.path.join(img, name), quality=88); return name
    today = "e033_M10s_4096_wall_share0.999_ocean0.05"
    pics = {
        "today_map": cp(os.path.join(ex, today, "map.png"), "today_map.jpg"), "today_countries": cp(os.path.join(ex, today, "countries.png"), "today_countries.jpg"),
        "today_metric": cp(os.path.join(ex, today, "metric_grid.png"), "today_metric.jpg"), "today_tissot": cp(os.path.join(ex, today, "tissot.png"), "today_tissot.jpg"),
        "today_equi": cp(os.path.join(ex, today, "equipotentials.png"), "today_equipotentials.jpg"), "today_twist": cp(os.path.join(ex, today, "twist.png"), "today_twist.jpg"),
        "lights": cp(os.path.join(ex, today, "lens_lights.png"), "lens_lights.jpg"), "roads": cp(os.path.join(ex, today, "lens_roads.png"), "lens_roads.jpg"),
        "gdp": cp(os.path.join(ex, "L4_gdp_2048", "countries.png"), "lens_gdp.jpg"), "lonely": cp(os.path.join(ex, "L6_lonely_2048", "countries.png"), "lens_lonely.jpg"),
        "peak": cp(os.path.join(ex, today, "lens_peak_year.png"), "lens_peak.jpg"), "personyears": cp(os.path.join(ex, "timeline", "L3_personyears_2048", "countries.png"), "lens_personyears.jpg"),
        "curvature": cp(os.path.join(ex, "geometry_1024", "curvature.png"), "geo_curvature.jpg"), "geodesics": cp(os.path.join(ex, "geometry_1024", "geodesics.png"), "geo_geodesics.jpg"),
        "distance": cp(os.path.join(ex, "geometry_1024", "distance.png"), "geo_distance.jpg"), "diffusion": cp(os.path.join(ex, "e009_S2_merc_4096_f05", "cartogram.png"), "method_diffusion.jpg"),
        "antigravity": cp(os.path.join(ex, "e027_R5_gravity_t0.1_1024", "cartogram.png"), "method_antigravity.jpg"), "jellium": cp(os.path.join(ex, "e026_M9_jellium_2048", "cartogram.png"), "method_jellium.jpg"),
    }
    def fig(key, cap):
        return f'<figure><a href="img/{pics[key]}"><img src="img/{pics[key]}" loading="lazy"></a><figcaption>{cap}</figcaption></figure>' if pics.get(key) else ""
    css = "body{font:15px/1.5 -apple-system,sans-serif;background:#0b0d12;color:#ddd;margin:0;padding:24px;max-width:1200px}a{color:#7cc}h1,h2{font-weight:600}figure{margin:18px 0}img{max-width:100%;border-radius:4px}figcaption{color:#9ab;font-size:13px;margin-top:6px}nav a{margin-right:14px}.note{color:#9ab;font-size:13px}"
    nav = '<nav><a href="index.html">home</a><a href="flat/">today, zoomable</a><a href="globe/">globe</a><a href="time/">time</a><a href="lenses.html">lenses</a><a href="geometry.html">geometry</a><a href="../experiments/gallery.html">gallery</a></nav>'
    open(os.path.join(SITE, "index.html"), "w").write(f"""<!doctype html><html><head><meta charset="utf-8"><title>the humeter world</title><style>{css}</style></head><body>{nav}
<h1>The humeter world</h1><p>A map of the Earth in which <b>area is people</b>: every square centimetre holds the same number of human beings. Built from the finest complete population raster (GHS-POP, 100 m), by optimal transport, so nothing rotates and everything moves as little as it can. Land is pure; the ocean keeps 5% of the frame so you can see where the Atlantic went. The unit of length is the humeter: 1 hm is 1 km at the world-average density, about 16 people per km².</p>
<p>Dense places feel full and big; empty places seem vast but feel empty and small. This is that feeling, drawn.</p>
{fig("today_map", "Today (GHS-POP 2025): 4096 px, countries, 300 cities, rivers; a ghost of the real coastline underneath. Density error ±2.7%.")}
<h2>Read it at every scale</h2><p><a href="flat/">Zoom and pan the flat frame</a> down to the 100 m settlement texture, or <a href="globe/">spin the globe</a> (sphere area = people; the slider morphs geography into the cartogram). <a href="time/">Then play it through time</a>: every HYDE epoch from 10,000 BC to 2023.</p>
{fig("today_metric", "The metric grid: 100 km × 100 km cells of ground pushed through the warp. A big cell feels full, a sliver feels empty.")}
{fig("today_tissot", "Tissot circles: 300 km circles become ellipses; the elongation is the price of flattening a curved population manifold.")}
{fig("today_equi", "Equipotentials: level sets of the transport potential, the gravity of population made visible.")}
<h2>Why optimal transport</h2><p>Three ways to flatten the same manifold. Diffusion melts; population as repelling mass comes close; optimal transport keeps every coastline's orientation (its twist is exactly zero) and moves things least.</p>
{fig("diffusion", "Diffusion (Gastner-Newman 2004): the flow swirls, coastlines rotate up to 30°.")}
{fig("jellium", "Population as repelling mass with a neutralising background (a particle-mesh code with gravity's sign flipped).")}
{fig("antigravity", "The same physics with ordinary gravity, stopped early: cities pull the graticule in like wells. The anti-cartogram.")}
<h2>Honesty</h2><p class="note">Population: GHS-POP R2023A (JRC), 2025 epoch, census counts disaggregated onto satellite-detected buildings. History: HYDE 3.3 (Utrecht University), modelled before 1950 from regional estimates. Lights: NASA Black Marble 2016. Roads: GRIP4 (CC0). GDP: Kummu et al. 2018 (CC0). Borders and coasts: Natural Earth. Every picture on this site states its source and whether it is observed, modelled or interpolated. Code and every experiment: <a href="https://github.com/philippbogdan/historical-cartogram">github.com/philippbogdan/historical-cartogram</a>.</p>
</body></html>""")
    open(os.path.join(SITE, "lenses.html"), "w").write(f"""<!doctype html><html><head><meta charset="utf-8"><title>lenses</title><style>{css}</style></head><body>{nav}
<h1>Lenses</h1><p>A lens is (the measure that gets the area, the measure painted as colour, the moment). Painting a second measure on a population cartogram shows it <b>per person</b>, by construction.</p>
{fig("lights", "Night lights per person. White is the world average; red is ten times more light per person, blue ten times less. Wealth, without a single statistic.")}
{fig("roads", "Road length per person (GRIP4).")}
{fig("gdp", "The dollar world: area is GDP (PPP, 2015, Kummu et al.). Compare with the people world above it.")}
{fig("lonely", "The loneliness lens: area proportional to 1/density on land. The complement of the humeter: where empty places are vast.")}
{fig("peak", "When each place peaked: the HYDE epoch of maximum population per cell, painted on today's frame. Yellow is still growing; dark peaked long ago.")}
{fig("personyears", "Person-years: area is human life lived there between 10,000 BC and 2023, integrated over HYDE.")}
</body></html>""")
    open(os.path.join(SITE, "geometry.html"), "w").write(f"""<!doctype html><html><head><meta charset="utf-8"><title>geometry</title><style>{css}</style></head><body>{nav}
<h1>The population manifold, kept curved</h1><p>Give the map the metric g = (ρ/ρ̄)(dx² + dy²): areas are people, angles are geographic, and it is curved. The cartogram is what you get by flattening it; these pictures leave it curved.</p>
{fig("curvature", "Gaussian curvature as colour: red on the tops of population hills, blue in the saddles between cities.")}
{fig("geodesics", "Geodesics fanning out from London, Delhi and São Paulo: the straight lines of the humeter world bend away from dense regions like light around a lens.")}
{fig("distance", "Humeter distance from four cities, contours every 2000 hm-km. Crossing India costs more than crossing the Atlantic.")}
</body></html>""")
    print("pages written", {k: v for k, v in pics.items() if v})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "tiles": tiles(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    elif cmd == "time": time_frames()
    elif cmd == "pages": pages()
