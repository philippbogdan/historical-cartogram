"""T1: every HYDE epoch through the same solver and renders, one experiment per epoch.
    python src/run_timeline.py <width> [sigma_km] [ocean_share] [epoch selection: all | every:N | list of years] [scenario]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render, hyde
from run import ROOT, RAW
from timeline_frame import run_epoch, render_frame   # render_frame re-exported for timeline_extras

width = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
sigma_km = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
ocean_share = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
sel = sys.argv[4] if len(sys.argv) > 4 else "all"
scenario = sys.argv[5] if len(sys.argv) > 5 else "base"
lon0, xb = -168.0, "wall"

if __name__ == "__main__":
    H = hyde.Hyde(os.path.join(RAW, "hyde33", f"population_{scenario}.nc"))
    years = list(H.years)
    if sel.startswith("every:"):
        idx = list(range(0, len(years), int(sel.split(":")[1])))
        if idx[-1] != len(years) - 1: idx.append(len(years) - 1)
    elif sel == "all":
        idx = list(range(len(years)))
    else:
        want = [int(y) for y in sel.split(",")]; idx = [years.index(y) for y in want]
    grid = prep.Grid("mercator", width, lon0=lon0)
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
    out_root = os.path.join(ROOT, "experiments", "timeline")
    os.makedirs(out_root, exist_ok=True)
    index = []
    for i in idx:
        y = years[i]
        name = f"t_{scenario}_{y:+06d}"
        out = os.path.join(out_root, name)
        if os.path.exists(os.path.join(out, "metrics.json")):
            index.append(name); print("skip", name); continue
        honesty = "modelled (HYDE allocation of regional estimates)" if y < 1950 else "census-based (HYDE, national statistics)"
        run_epoch(out, grid, H.counts(i), H.bounds, y, f"HYDE 3.3 {scenario} population.nc", honesty, sigma_km, ocean, ocean_share, xb, lon0)
        index.append(name)
    json.dump({"scenario": scenario, "width": width, "frames": index}, open(os.path.join(out_root, f"index_{scenario}_{width}.json"), "w"), indent=1)
    print("done", len(index), "frames")
