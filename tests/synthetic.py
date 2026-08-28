"""Sanity check: smooth synthetic densities must equalise almost exactly."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hc import diffusion

def run(name, rho, **kw):
    dc = diffusion.DiffusionCartogram(rho, floor=0.0, sigma=0.0)
    X, Y, info = dc.run(log=lambda s: None, **kw)
    m = diffusion.equalisation_metrics(dc.rho0, X, Y)
    print(f"{name:28s} folds={m['folds']:4d} logratio p05/p50/p95 = {m['log_ratio_popweighted_p05']:+.3f} {m['log_ratio_popweighted_p50']:+.3f} {m['log_ratio_popweighted_p95']:+.3f}  min/max {m['log_ratio_min']:+.2f} {m['log_ratio_max']:+.2f}  aniso p50 {m['anisotropy_popweighted_p50']:.2f} steps={info['steps']}")

n = 128
ys, xs = np.mgrid[0:n, 0:n] + 0.5
g = lambda cx, cy, s: np.exp(-((xs-cx)**2 + (ys-cy)**2) / (2*s*s))
run("gaussian blob, ratio 6", 1 + 5*g(50, 70, 12))
run("gaussian blob, ratio 100", 0.01 + g(50, 70, 12))
run("two blobs, ratio 100", 0.01 + g(30, 40, 8) + g(90, 90, 10))
run("sharp blob s=2, ratio 100", 0.01 + g(64, 64, 2))
run("sharp blob s=2, maxdisp .1", 0.01 + g(64, 64, 2), max_disp=0.1)
