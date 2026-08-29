"""PR1 golden regression: the world at 512 with fixed knobs must reproduce stored metrics.
    python tests/regression.py          # check
    python tests/regression.py --update # re-baseline (only after a deliberate change)
"""
import json, os, sys, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from hc import prep, diffusion, ot_poisson
from run import get_lonlat, NCOLS

GOLDEN = os.path.join(ROOT, "tests", "golden.json")
KEYS = ["log_ratio_popweighted_p05", "log_ratio_popweighted_p95", "anisotropy_popweighted_p50", "displacement_mean_px"]
TOL = {"log_ratio_popweighted_p05": 0.01, "log_ratio_popweighted_p95": 0.01, "anisotropy_popweighted_p50": 0.1, "displacement_mean_px": 2.0}


def world512():
    grid = prep.Grid("mercator", 512)
    factor = max(d for d in prep.divisors(NCOLS) if d <= NCOLS // 1024)
    counts, bounds = get_lonlat(factor)
    P, _ = prep.to_grid(counts, bounds, grid)
    sigma_px = 235.0 / grid.km_per_px_equator()
    out = {}
    dc = diffusion.TorchDiffusionCartogram(P, floor=0.05, sigma=sigma_px, x_boundary="periodic")
    X, Y, _ = dc.run(tol=1e-3, max_disp=1.5, cap_frac=0.1, log=lambda s: None)
    out["diffusion"] = diffusion.equalisation_metrics(dc.rho0, X, Y)
    po = ot_poisson.TorchPoissonOT(P, floor=0.05, sigma=sigma_px, x_boundary="periodic")
    X, Y, _ = po.run(iters=300, damping=0.5, log=lambda s: None)
    out["ot_poisson"] = diffusion.equalisation_metrics(po.rho0, X, Y)
    return out


if __name__ == "__main__":
    got = world512()
    if "--update" in sys.argv or not os.path.exists(GOLDEN):
        json.dump(got, open(GOLDEN, "w"), indent=1)
        print("golden written")
        sys.exit(0)
    gold = json.load(open(GOLDEN))
    bad = []
    for method in gold:
        for k in KEYS:
            d = abs(got[method][k] - gold[method][k])
            flag = "" if d <= TOL[k] else "  <-- FAIL"
            if flag:
                bad.append((method, k))
            print(f"{method:11s} {k:28s} golden {gold[method][k]:9.4f} now {got[method][k]:9.4f} diff {d:.4f}{flag}")
    print("REGRESSION", "FAIL" if bad else "PASS")
    sys.exit(1 if bad else 0)
