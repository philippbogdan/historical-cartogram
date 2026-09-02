"""H3: the same frame across time, eight panels in the hero language.
    python src/render_multiples.py <out.png> <panel_w> <exp1,exp2,...>"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from run import ROOT
from warp_vectors import frame_mesh
from render_hero import draw_hero, FONT

out_png, pw, exps = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(",")
panels = []
for e in exps:
    d = os.path.join(ROOT, "experiments", "timeline" if e.startswith("t_") else "", e).replace("//", "/")
    if not os.path.exists(os.path.join(d, "params.json")): d = os.path.join(ROOT, "experiments", e)
    name = os.path.relpath(d, os.path.join(ROOT, "experiments"))
    grid, X, Y, p = frame_mesh(name); m = json.load(open(os.path.join(d, "metrics.json")))
    png = os.path.join(d, f"hero_{pw}.png")
    if not os.path.exists(png): draw_hero(X, Y, p, png, pw, band=False, labels=False)
    y = p["year"]; pop = m.get("population", 0)
    hon = p.get("honesty", ""); hon = "modelled (HYDE)" if hon.startswith("modelled") else "census-based (HYDE)" if hon.startswith("census") else "projected (SSP2)" if "SSP" in hon else hon
    panels.append((png, f"{-y} BC" if y < 0 else f"{y} AD", f"{pop/1e9:.2f} billion" if pop >= 1e9 else f"{pop/1e6:.0f} million", hon))
cols = 4; rows = (len(panels) + cols - 1) // cols
im0 = Image.open(panels[0][0]); w, h = im0.size; cap_h = int(0.10 * h); gap = int(0.025 * w); title_h = int(0.14 * h)
sheet = Image.new("RGB", (cols * w + (cols + 1) * gap, title_h + rows * (h + cap_h + gap) + gap), "white")
dr = ImageDraw.Draw(sheet)
try:
    fb = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", int(0.045 * h)); fs = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", int(0.026 * h)); ft = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", int(0.05 * h))
except Exception:
    fb = fs = ft = ImageFont.load_default()
dr.text((gap, int(0.18 * title_h)), "THE SAME RECTANGLE, TWELVE THOUSAND YEARS: AREA = PEOPLE", font=ft, fill="#111")
dr.text((gap, int(0.62 * title_h)), "Each panel is the world with area proportional to the people alive that year. The frame is always full, so the caption says how many people it holds. HYDE 3.3 to 2023, SSP2 projection after.", font=fs, fill="#444")
for i, (png, yr, pop, hon) in enumerate(panels):
    r, c = divmod(i, cols); x0 = gap + c * (w + gap); y0 = title_h + gap + r * (h + cap_h + gap)
    sheet.paste(Image.open(png).convert("RGB"), (x0, y0))
    dr.text((x0, y0 + h + int(0.12 * cap_h)), yr, font=fb, fill="#111"); dr.text((x0, y0 + h + int(0.62 * cap_h)), f"{pop} people · {hon}", font=fs, fill="#444")
sheet.save(out_png); print("wrote", out_png, sheet.size)
