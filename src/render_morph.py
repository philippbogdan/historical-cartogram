"""H2/R3: the morph from geography to the cartogram. For an optimal-transport map the straight-line
(McCann) interpolation of positions is the displacement geodesic, so every in-between frame is itself a map.
    python src/render_morph.py <experiment> [frames=48] [out_w=2048] -> experiments/<exp>/morph/f####.png, morph.mp4, morph.gif"""
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from run import ROOT
from warp_vectors import frame_mesh
from render_hero import draw_hero

exp = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 48; out_w = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
grid, X, Y, p = frame_mesh(exp); H, W = grid.H, grid.W
ys, xs = np.mgrid[0:H + 1, 0:W + 1].astype(np.float64)
out = os.path.join(ROOT, "experiments", exp, "morph"); os.makedirs(out, exist_ok=True)
hold = max(2, n // 8)
ts = [0.0] * hold + list((1 - np.cos(np.linspace(0, np.pi, n))) / 2) + [1.0] * hold      # ease in and out, hold both ends
for i, t in enumerate(ts):
    png = os.path.join(out, f"f{i:04d}.png")
    if os.path.exists(png): continue
    draw_hero(xs * (1 - t) + X * t, ys * (1 - t) + Y * t, p, png, out_w, band=False, labels=(t in (0.0, 1.0)))
    print(f"frame {i}/{len(ts)} t={t:.3f}", flush=True)
if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(out, "f%04d.png"), "-vf", f"scale={out_w}:-2:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "20", os.path.join(out, "morph.mp4")])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(out, "f%04d.png"), "-vf", "scale=1024:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer", os.path.join(out, "morph.gif")])
    print("wrote morph.mp4 and morph.gif")
else:
    print("ffmpeg not found; frames only")
