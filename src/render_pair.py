"""H4: the GDP world beside the person-years world, then GDP per person-year painted on the person-years world.
    python src/render_pair.py <gdp_exp> <personyears_exp> [out_w]"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, hyde
from run import ROOT, RAW
from warp_vectors import frame_mesh
from render_hero import draw_hero
import netCDF4

gdp_exp, py_exp = sys.argv[1], sys.argv[2]; out_w = int(sys.argv[3]) if len(sys.argv) > 3 else 4096
out = os.path.join(ROOT, "experiments", "H4_pair"); os.makedirs(out, exist_ok=True)
ds = netCDF4.Dataset(os.path.join(RAW, "lenses", "GDP_PPP_1990_2015_5arcmin_v2.nc")); var = [v for v in ds.variables if "GDP" in v or "gdp" in v][0]
a = np.nan_to_num(np.array(ds.variables[var][-1], dtype=np.float64)); a[a < 0] = 0
lat = ds.variables[[k for k in ds.variables if k.lower().startswith("lat")][0]][:]
if lat[0] < lat[-1]: a = a[::-1]
H = hyde.Hyde(os.path.join(RAW, "hyde33", "population_base.nc")); ys = list(H.years); acc = np.zeros(H.counts(0).shape)
for i in range(len(ys) - 1): acc += 0.5 * (H.counts(i) + H.counts(i + 1)) * (ys[i + 1] - ys[i])
# panel 1: GDP world
grid, X, Y, p = frame_mesh(gdp_exp); tot = float(a.sum()); p["population"] = tot
draw_hero(X, Y, p, os.path.join(out, "gdp_world.png"), out_w, title="THE WORLD, AREA = GDP", legend_text="= 100 billion dollars a year (PPP, 2015)", legend_unit=1e11,
          subtitle=f"Every part of the picture holds as much economic output as its area says; the whole frame is {tot/1e12:.0f} trillion dollars a year.\nCountries keep their colours from the population world, so a country that grew is rich per head and one that shrank is poor per head.",
          source="Optimal transport of Kummu, Taka and Guillaume 2018 GDP PPP 2015 (5 arcmin, CC0), land pure, ocean 20% of the frame.")
# panel 2: person-years world, and the ratio GDP per person-year painted on it
grid2, X2, Y2, p2 = frame_mesh(py_exp); tot2 = float(acc.sum()); p2["population"] = tot2
draw_hero(X2, Y2, p2, os.path.join(out, "personyears_world.png"), out_w, title="THE WORLD, AREA = YEARS OF HUMAN LIFE SINCE 10,000 BC", legend_text="= 10 billion person-years", legend_unit=1e10,
          subtitle=f"Every part of the picture holds as many person-years as its area says: all the years everyone has lived there since the end of the Ice Age, {tot2/1e12:.2f} trillion in the frame.\nSixty percent of them were lived before 1700. The picture looks like today's population because population growth is exponential.",
          source="HYDE 3.3 population, integrated over its 126 epochs; optimal transport, land pure, ocean 20% of the frame.")
# ratio raster on the person-years grid: GDP / person-years per source cell, relative to the world ratio, log2 scale
G, _ = prep.to_grid(a, (-180, -90, 180, 90), grid2)
PY, _ = prep.to_grid(acc, H.bounds, grid2)
from scipy import ndimage
Gs = ndimage.gaussian_filter(G, 5); Ps = ndimage.gaussian_filter(PY, 5)
ratio = np.where(Ps > 1e5, Gs / np.maximum(Ps, 1), np.nan); world = G.sum() / PY.sum()
lg = np.log2(ratio / world)
draw_hero(X2, Y2, p2, os.path.join(out, "gdp_per_personyear.png"), out_w, title="GDP PER YEAR OF HUMAN LIFE", legend_text="= 10 billion person-years", legend_unit=1e10,
          subtitle="The person-years world, painted with output per person-year: blue is a quarter of the world average or less, red four times or more.\nIf history equalised wealth this picture would be one flat colour. It spans a factor of 64 between the 5th and 95th percentile countries.",
          source="Kummu GDP PPP 2015 divided by HYDE person-years since 10,000 BC, per 5 arcmin cell, smoothed 5 cells; log2 scale, RdBu.",
          overlay=(lg, "RdBu_r", -2.0, 2.0, 0.85))
print("H4 written to", out)
