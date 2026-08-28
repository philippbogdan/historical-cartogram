"""Redraw an experiment's PNGs from its saved mesh (after render changes)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import render
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
for name in sys.argv[1:]:
    out = os.path.join(ROOT, "experiments", name)
    p = json.load(open(os.path.join(out, "params.json")))
    z = np.load(os.path.join(out, "mesh.npz"))
    X, Y, rho0 = z["X"], z["Y"], z["rho0"]
    H, W, lc, v = p["H"], p["W"], p["lat_cut"], p["vectors"]
    mask = render.land_mask(os.path.join(RAW, f"ne_{v}_land.geojson"), H, W, lc)
    coast = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_coastline.geojson"), H, W, lc)
    borders = render.lines_from_geojson(os.path.join(RAW, f"ne_{v}_admin_0_countries.geojson"), H, W, lc)
    grat = render.graticule(H, W, lc)
    title = f"{name}: diffusion, {W}x{H}, floor {p['floor']}, sigma {p['sigma']}"
    render.draw(X, Y, mask, os.path.join(out, "cartogram.png"), coast, borders, grat, title=title)
    render.draw(X, Y, mask, os.path.join(out, "cartogram_density.png"), coast, [], [], raster=np.log10(rho0), title=title + " (log10 source density through the warp)")
    render.draw_error(X, Y, rho0, os.path.join(out, "error.png"))
    print("rerendered", name)
