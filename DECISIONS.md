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
- 2026-08-28  The diffusion solver starts at t = 0.5 px^2 (heat kernel one pixel wide) because
  raw 1 km spikes on a coarse grid make v = -grad(rho)/rho meaningless below a pixel; the first
  run without this stalled at dt ~ 1e-5. Extra smoothing sigma is a separate knob.
- 2026-08-28  At 512 px the honest defaults are sigma 3 px, floor 1-5%: about +-10% density error,
  few folds, 65 s. Resolution and accuracy trade directly; the OT methods must beat this bar.
- 2026-08-28  experiments/INDEX.md is the running comparison table; regenerate it, do not hand-edit.
- 2026-08-28  Population-as-mass ideas recorded in notes/gravity.md: M9 (jellium flow), M10 (Poisson
  iteration) and the G-slider (R5) join the map; the curvature/GR version is a side branch, not a cartogram.
