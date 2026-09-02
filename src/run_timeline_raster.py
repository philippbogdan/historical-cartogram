"""D6/T8 and D8/T5: GeoTIFF epochs (GHS-POP 1975-2030, SSP2 2020-2100) through the same frame runner as HYDE.
    python src/run_timeline_raster.py <ghs|ssp2> <width> [sigma_km] [ocean_share] [years: all | list]"""
import glob, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from hc import prep, render
from run import ROOT, RAW, DER
from timeline_frame import run_epoch

source = sys.argv[1]
width = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
sigma_km = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
ocean_share = float(sys.argv[4]) if len(sys.argv) > 4 else 0.05
sel = sys.argv[5] if len(sys.argv) > 5 else "all"
tag = sys.argv[6] if len(sys.argv) > 6 else ""
lon0, xb, FACTOR = -168.0, "wall", 10        # 30 arcsec rasters block-summed to 5 arcmin, the HYDE resolution


def epochs(source):
    if source == "ghs":
        files = sorted(glob.glob(os.path.join(RAW, "ghs_epochs", "GHS_POP_E*_30ss_V1_0.tif")) + glob.glob(os.path.join(RAW, "GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif")))
        for f in files:
            y = int(re.search(r"_E(\d{4})_", f).group(1))
            yield y, f, "GHS-POP R2023A 30 arcsec", ("census-based (GHS-POP, census counts allocated to 100 m built-up)" if y <= 2020 else "projected (GHS-POP 2025/2030 extrapolation of census trends)")
    elif source.startswith("ssp"):
        files = sorted(glob.glob(os.path.join(RAW, "ssp", "**", f"*{source.upper()}*.tif"), recursive=True))
        for f in files:
            m = re.search(r"(20[2-9]\d|2100)", os.path.basename(f))
            if not m: continue
            yield int(m.group(1)), f, f"{source.upper()} 1 km (Wang, Meng and Long 2022, figshare 19608594)", f"projected ({source.upper()}, random-forest allocation of SSP national totals)"


def counts_for(f, y, source):
    os.makedirs(DER, exist_ok=True)
    cache = os.path.join(DER, f"{source}_{y}_lonlat_f{FACTOR}.npz")
    if os.path.exists(cache):
        z = np.load(cache); return z["counts"], tuple(z["bounds"])
    counts, bounds = prep.load_lonlat_counts(f, FACTOR)
    np.savez_compressed(cache, counts=counts, bounds=np.array(bounds))
    return counts, bounds


if __name__ == "__main__":
    grid = prep.Grid("mercator", width, lon0=lon0)
    ocean = render.land_mask(os.path.join(RAW, "ne_50m_land.geojson"), grid) == 0
    out_root = os.path.join(ROOT, "experiments", "timeline"); os.makedirs(out_root, exist_ok=True)
    want = None if sel == "all" else {int(y) for y in sel.split(",")}
    index = []
    for y, f, src, honesty in epochs(source):
        if want is not None and y not in want: continue
        name = f"t_{source}{tag}_{y:+06d}"; out = os.path.join(out_root, name)
        if os.path.exists(os.path.join(out, "metrics.json")):
            index.append(name); print("skip", name); continue
        counts, bounds = counts_for(f, y, source)
        run_epoch(out, grid, counts, bounds, y, src, honesty, sigma_km, ocean, ocean_share, xb, lon0)
        index.append(name)
    json.dump({"scenario": source, "width": width, "frames": index}, open(os.path.join(out_root, f"index_{source}{tag}_{width}.json"), "w"), indent=1)
    print("done", len(index), "frames")
