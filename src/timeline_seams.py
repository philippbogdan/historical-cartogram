"""T8: how much two sources disagree at the same year: mean and p95 displacement difference (px at 2048)
between frames, population-weighted. Writes experiments/timeline/seams.json.
    python src/timeline_seams.py"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from run import ROOT, load_mesh
TL = os.path.join(ROOT, "experiments", "timeline")
pairs = [("t_base_+01970", "t_ghs_+01975"), ("t_base_+01975", "t_ghs_+01975"), ("t_base_+02000", "t_ghs_+02000"), ("t_base_+02020", "t_ghs_+02020"),
         ("t_ghs_+02020", "t_ssp2_+02020"), ("t_base_+02020", "t_ssp2_+02020"), ("t_ghs_+02025", "t_ssp2_+02025"), ("t_ghs_+02030", "t_ssp2_+02030"), ("t_base_+02020", "t_base_+02023")]
out = {}
for a, b in pairs:
    da, db = os.path.join(TL, a), os.path.join(TL, b)
    if not (os.path.exists(os.path.join(da, "metrics.json")) and os.path.exists(os.path.join(db, "metrics.json"))): continue
    Xa, Ya, ra = load_mesh(da); Xb, Yb, rb = load_mesh(db)
    d = np.hypot(Xa - Xb, Ya - Yb)                      # corner displacement difference, px
    w = np.zeros_like(d); w[:-1, :-1] = np.asarray(ra, np.float64)   # weight corners by the source-cell population of a
    w = w / w.sum()
    mean = float((d * w).sum()); order = np.argsort(d.ravel()); cw = np.cumsum(w.ravel()[order]); p95 = float(d.ravel()[order][np.searchsorted(cw, 0.95)])
    out[f"{a} vs {b}"] = {"mean_px": mean, "p95_px": p95, "max_px": float(d.max())}
    print(f"{a} vs {b}: mean {mean:.1f} px, p95 {p95:.1f} px, max {d.max():.1f} px (of {Xa.shape[1]-1})")
json.dump(out, open(os.path.join(TL, "seams.json"), "w"), indent=1)
