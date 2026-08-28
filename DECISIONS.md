# Decisions

- 2026-08-28  Two acts: methods at pinned time (2025) first, timeline (HYDE) last.
- 2026-08-28  Pinned dataset for method work: GHS-POP R2023A epoch 2025, 30 arcsec
  WGS84 counts. Finest complete global raster is GHS-POP 3 arcsec; used later for renders only.
- 2026-08-28  Coordinate-granular only: densities come from rasters; polygons draw borders.
- 2026-08-28  Prep works in counts per Mercator pixel (exact re-binning), so no explicit
  Mercator area correction exists anywhere in the code.
- 2026-08-28  Zero density is never fed to a solver: floor = fraction of the global mean,
  a knob, default 1%. "Ocean removed" means floor -> small, not zero.
- 2026-08-28  Frame default: Web-Mercator cut at 85.0511 (square). A knob.
- 2026-08-28  Diffusion (Gastner-Newman) is the first method, own implementation in numpy/scipy,
  not cartogram-cpp, so every later method shares prep, metrics and render.
- 2026-08-28  Same metrics for every method, computed on the warped corner mesh.
