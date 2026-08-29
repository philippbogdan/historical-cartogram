"""A12: the inverse map of an experiment: for every output pixel of the cartogram frame, the source
pixel (mesh coordinates) that lands there, by splatting the source coordinates through the warp.
    python src/inverse_map.py <experiment> [out_width]     -> experiments/<name>/inverse.npz"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import render
from run import ROOT

def main(name, out_w=None):
    out = os.path.join(ROOT, "experiments", name)
    p = json.load(open(os.path.join(out, "params.json")))
    z = np.load(os.path.join(out, "mesh.npz"))
    X, Y = z["X"].astype(np.float64), z["Y"].astype(np.float64)
    H, W = p["H"], p["W"]
    out_w = out_w or W
    oh, ow = int(round(H * out_w / W)), out_w
    wrap = p.get("x_boundary", "periodic") == "periodic"
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    # splat the source x as (cos, sin) on the cylinder so averaging across the seam stays sane
    ang = xs / W * 2 * np.pi
    cx = render.splat(np.cos(ang), X, Y, (oh, ow), wrap=wrap)
    sx = render.splat(np.sin(ang), X, Y, (oh, ow), wrap=wrap)
    IX = (np.arctan2(sx, cx) / (2 * np.pi)) % 1.0 * W
    IY = render.splat(ys, X, Y, (oh, ow), wrap=wrap)
    np.savez_compressed(os.path.join(out, "inverse.npz"), IX=IX.astype(np.float32), IY=IY.astype(np.float32), out_hw=np.array([oh, ow]), src_hw=np.array([H, W]))
    print("wrote", os.path.join(out, "inverse.npz"), (oh, ow))

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
