"""Redraw an experiment's PNGs from its saved mesh."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep
from run import render_all, ROOT
for name in sys.argv[1:]:
    out = os.path.join(ROOT, "experiments", name)
    p = json.load(open(os.path.join(out, "params.json")))
    z = np.load(os.path.join(out, "mesh.npz"))
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"], lon0=p.get("lon0", -180.0))
    p.setdefault("method", "diffusion"); p.setdefault("x_boundary", "wall"); p.setdefault("sigma_km", p.get("sigma", 0))
    render_all(out, grid, z["X"].astype(np.float64), z["Y"].astype(np.float64), z["rho0"].astype(np.float64), p)
    print("rerendered", name)
