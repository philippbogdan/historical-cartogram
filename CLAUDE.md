# historical-cartogram

Read `README.md`, `EXPLORATION.md`, `DECISIONS.md` before doing anything. They are the
project's memory; update them in the same commit as the work they describe.

- Raster in, raster out. Population density is per pixel from a gridded dataset;
  country polygons are for drawing borders only, never for the density.
- Counts, not densities: re-bin people per output pixel; never reproject a density.
- One experiment = one folder `experiments/eNNN_<slug>/` with `params.json`,
  `metrics.json`, `log.txt` and PNGs. Meshes (`mesh.npz`) are gitignored.
- Every method reports the same metrics (`hc.diffusion.equalisation_metrics`):
  population-weighted log(density/area) quantiles, folds, anisotropy, displacement.
- Python: `~/.venv/default/bin/python`. Dependencies: numpy, scipy, matplotlib,
  rasterio, tifffile.
- Data lives in `data/raw` (downloads) and `data/derived` (caches); both gitignored,
  recreated by the scripts. Record every source in `DATA.md` with date and licence.
- Decisions go in `DECISIONS.md` with an as-of date. Exploration status lives in
  `EXPLORATION.md`; tick items there rather than in chat.
