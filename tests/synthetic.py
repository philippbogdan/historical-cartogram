"""Sanity check: smooth synthetic densities must equalise almost exactly, on both backends."""
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hc import diffusion

def run(name, rho, cls, xb, **kw):
    dc = cls(rho, floor=0.0, sigma=0.0, x_boundary=xb)
    X, Y, info = dc.run(log=lambda s: None, **kw)
    m = diffusion.equalisation_metrics(dc.rho0, X, Y)
    print(f"{name:26s} {cls.__name__[:5]:5s} {xb:8s} folds={m['folds']:3d} logratio p05/p50/p95 = {m['log_ratio_popweighted_p05']:+.3f} {m['log_ratio_popweighted_p50']:+.3f} {m['log_ratio_popweighted_p95']:+.3f}  min/max {m['log_ratio_min']:+.2f} {m['log_ratio_max']:+.2f}  steps={info['steps']}")
    return m

n = 128
ys, xs = np.mgrid[0:n, 0:n] + 0.5
g = lambda cx, cy, s: sum(np.exp(-((xs-cx-k*n)**2 + (ys-cy)**2) / (2*s*s)) for k in (-1, 0, 1))  # periodic in x
cases = [("blob ratio 6", 1 + 5*g(50, 70, 12)), ("blob ratio 100", 0.01 + g(50, 70, 12)),
         ("two blobs ratio 100", 0.01 + g(30, 40, 8) + g(90, 90, 10)), ("blob at the seam", 0.01 + g(2, 60, 10))]
worst = 0
for name, rho in cases:
    for cls in (diffusion.DiffusionCartogram, diffusion.TorchDiffusionCartogram):
        for xb in ("wall", "periodic"):
            m = run(name, rho, cls, xb)
            worst = max(worst, abs(m["log_ratio_popweighted_p05"]), abs(m["log_ratio_popweighted_p95"]), m["folds"])
print("WORST", worst, "PASS" if worst < 0.05 else "FAIL")
