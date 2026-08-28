"""Post-process an existing experiment with the fold repair (S4), refresh metrics and renders."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, diffusion
from run import render_all, ROOT
for name in sys.argv[1:]:
    out = os.path.join(ROOT, "experiments", name)
    p = json.load(open(os.path.join(out, "params.json")))
    m = json.load(open(os.path.join(out, "metrics.json")))
    z = np.load(os.path.join(out, "mesh.npz"))
    X, Y, rho0 = z["X"].astype(np.float64), z["Y"].astype(np.float64), z["rho0"].astype(np.float64)
    m0 = diffusion.equalisation_metrics(rho0, X, Y)
    X, Y, rep = diffusion.repair_folds(X, Y, periodic=(p.get("x_boundary", "wall") == "periodic"), mass=rho0)
    m1 = diffusion.equalisation_metrics(rho0, X, Y)
    m.update(m1); m.update(rep); m["p95_shift_by_repair"] = m1["log_ratio_popweighted_p95"] - m0["log_ratio_popweighted_p95"]
    json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(out, "mesh.npz"), X=X.astype(np.float32), Y=Y.astype(np.float32), rho0=rho0.astype(np.float32))
    grid = prep.Grid(p.get("grid", "mercator"), p["W"], p["lat_cut"])
    render_all(out, grid, X, Y, rho0, p)
    print(name, rep, "gate", m["gate_folds"])
