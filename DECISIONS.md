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
- 2026-08-28  Two artefacts, one codebase: (i) the flat Mercator-rectangle cartogram (area in the picture =
  people), (ii) the globe (sphere area = people). (ii) cannot reuse a Mercator warp: it must be computed on
  an equal-area cylindrical grid, periodic in longitude. The solver takes the grid as a parameter.
- 2026-08-28  Overlays are the intellectual payload of the globe: any layer pushed through a population
  cartogram becomes a per-capita map (light per person, roads per person). Night lights should come
  out almost uniform; where they do not is the story.
- 2026-08-28  Folds (X2) must be exactly zero before anything goes on a sphere mesh.
- 2026-08-28  Resolution policy: no cap. Three resolutions, kept distinct: the WARP grid (solver;
  4096 now, 8192 once the solver runs on the GPU; smoothing in km shrinks with it, 230 km at 512 px,
  15 km at 8k), the TEXTURE (native: GHS-POP 100 m, VIIRS 500 m, served as a warped tile pyramid),
  and the DATA (HYDE is 5 arcmin and nothing finer exists before 1975). Compute stays on the M4
  (free, hours to a day per full run); any rented GPU goes in front of Phil with numbers first.
- 2026-08-28  The humeter: 1 hm = 1 km at the world-average population density (about 16 per km²),
  i.e. the conformal factor is rho/rho_bar and the Earth has the same area in hm² as in km².
- 2026-08-28  Lens grammar adopted: (mu -> area, nu -> colour, t). "Combining maps" is not convolution,
  it is the density of one measure with respect to another; the warp makes the ratio visible.
- 2026-08-28  Closest ancestor for multi-measure gridded cartograms is Hennig's "Rediscovering the
  World" (2013, static). What is new here: the metric-space framing, OT, time, the globe, the
  lens grammar as one pipeline.
