"""L10: the age lens. WorldPop 2020 age bands (5 arcmin reductions) -> median age and under-15 share per cell,
painted through the population warp on the hero frame.   python src/lenses_age.py [experiment] [out_w]"""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep
from run import ROOT, DER
from warp_vectors import frame_mesh
from render_hero import draw_hero

exp = sys.argv[1] if len(sys.argv) > 1 else "e036_hero_ocean0.2_s30_share0.999_ocean0.2"; out_w = int(sys.argv[2]) if len(sys.argv) > 2 else 4096
AGES = [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]; MID = [0.5, 3, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 85]
bands = {}; bounds = None
for a in AGES:
    acc = None
    for s in ("f", "m"):
        z = np.load(os.path.join(DER, "worldpop_age", f"global_{s}_{a}_2020_1km_f10.npz")); acc = z["counts"].astype(np.float64) if acc is None else acc + z["counts"]; bounds = tuple(z["bounds"])
    bands[a] = acc
grid, X, Y, p = frame_mesh(exp)
G = {a: prep.to_grid(bands[a], bounds, grid)[0] for a in AGES}
tot = sum(G.values()); under15 = G[0] + G[1] + G[5] + G[10]
print(f"WorldPop 2020 total {tot.sum()/1e9:.2f} bn; under 15: {100*under15.sum()/tot.sum():.1f}%")
# weighted median age per cell: interpolate the cumulative share within the band that crosses 0.5
cum = np.zeros_like(tot); med = np.full(tot.shape, np.nan); done = np.zeros(tot.shape, bool)
edges = AGES + [90]
with np.errstate(invalid="ignore", divide="ignore"):
    for i, a in enumerate(AGES):
        prev = cum.copy(); cum = cum + G[a]; f0 = prev / tot; f1 = cum / tot
        hit = (~done) & (f1 >= 0.5) & (tot > 0)
        frac = np.where(f1 > f0, (0.5 - f0) / (f1 - f0), 0.5)
        med[hit] = edges[i] + frac[hit] * (edges[i + 1] - edges[i]); done |= hit
    share = np.where(tot > 0, under15 / tot, np.nan)
world_share = under15.sum() / tot.sum(); world_med = float(np.nanmedian(np.repeat(med[tot > 0], 1)))
mask = tot > 50                                        # cells with people
med_m = np.where(mask, med, np.nan); share_m = np.where(mask, np.log2(share / world_share), np.nan)
out = os.path.join(ROOT, "experiments", "L10_age"); os.makedirs(out, exist_ok=True)
p["population"] = float(tot.sum())
draw_hero(X, Y, p, os.path.join(out, "median_age.png"), out_w, title="MEDIAN AGE, ON THE PEOPLE'S WORLD", legend_text="= 10 million people", legend_unit=1e7,
          subtitle=f"The population world painted with the median age of the people in each cell: purple is under 20, yellow over 45. World median about {world_med:.0f}.\nHalf the picture is young Africa and South Asia; the old countries are the small ones.",
          source="WorldPop 2020 age and sex structures, 1 km, reduced to 5 arcmin (CC BY 4.0), through the GHS-POP 2025 optimal-transport warp.", overlay=(med_m, "viridis", 15.0, 45.0, 0.85))
draw_hero(X, Y, p, os.path.join(out, "under15.png"), out_w, title="THE NEXT GENERATION: SHARE UNDER 15", legend_text="= 10 million people", legend_unit=1e7,
          subtitle=f"The population world painted with the share of children under 15 relative to the world ({100*world_share:.0f}%): red is double, blue is half.\nWhere the next generation is, and where it is not.",
          source="WorldPop 2020 age and sex structures, 1 km, reduced to 5 arcmin (CC BY 4.0), through the GHS-POP 2025 optimal-transport warp; log2 of the ratio to the world share.", overlay=(share_m, "RdBu_r", -1.0, 1.0, 0.85))
json.dump({"world_under15_share": float(world_share), "world_median_age": world_med, "total": float(tot.sum())}, open(os.path.join(out, "age.json"), "w"), indent=1)
print("L10 written")
