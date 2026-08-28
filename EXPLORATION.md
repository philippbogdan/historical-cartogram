# Exploration map

As of 2026-08-28. Legend: `[ ]` todo, `[~]` in progress, `[x]` done, `[!]` blocked.
Act 1 pins time at 2025 and compares methods. Act 2 (timeline) is last.

```
 DATA
  [x] D1 GHS-POP 2025, 30 arcsec (~1 km), counts, global     <- pinned "today" for all method work
  [ ] D2 GHS-POP 2020, 3 arcsec (~100 m) for final renders
  [ ] D3 HYDE 3.4, 5 arcmin population grids, 10000 BC to 2025  <- timeline, LAST
  [x] D4 Natural Earth 50m / 110m land, coastline, borders (drawing only)
  [ ] D5 night lights (VIIRS) as a texture to push through the warp

 PREP
  [x] P1 counts -> Mercator rectangle by exact re-binning (no density reprojection)
  [ ] P2 floor and smoothing policy: floor as fraction of mean, sigma in px
  [ ] P3 sphere-native variant (skip Mercator; Choi spherical DEM style)

 METHODS (each one: same input, same metrics, same render)
  [~] M1 diffusion, Gastner-Newman 2004: DCT heat flow, Neumann box, RK4 particles   <- start
  [ ] M2 flow-based, Gastner-Seguy-More 2018, via cartogram-cpp (reference implementation)
  [ ] M3 OT / W2 Brenier map via back-and-forth method (Jacobs-Leger 2020, bfm)      <- the new picture
  [ ] M4 OT via entropic Sinkhorn on the grid (separable kernel), barycentric map
  [ ] M5 OT via monotone Monge-Ampere finite differences (BFO 2014), own implementation
  [ ] M6 sliced OT (what vruba is playing with, 2026-06)
  [ ] M7 quasiconformal / min-anisotropy DEM (Lyu-Choi-Lui 2024); no public code, would be ours
  [ ] M8 Tobler pseudo-cartogram (separable 1-D integrals): the trivial baseline

 METRICS (X1..X5 computed; X6 is eyes)
  [x] X1 area error: population-weighted log(rho0/area) p05/p50/p95, min, max
  [x] X2 folds: number of negative-area cells (bijectivity)
  [x] X3 shape: anisotropy = singular-value ratio of the local Jacobian
  [x] X4 displacement: mean and max |T(x) - x| in px
  [ ] X5 seams: how the ocean collapsed (width statistics along coast pairs)
  [ ] X6 recognisability: side-by-side gallery, judged by eye

 KNOBS (sweep per method)
  floor in {0.1, 1, 5, 10}% of mean | sigma in {0, 1, 2} px | lat cut in {80, 85.05}
  width in {512, 1024, 2048, 4096} | ocean floor vs ocean removed

 RENDER
  [~] R1 warped mesh (pcolormesh) + warped coastlines, borders, graticule
  [ ] R2 rasters through the same field: population, night lights, terrain
  [ ] R3 morph geography -> cartogram (interpolate displacement; OT gives the geodesic)
  [ ] R4 WebGL mesh for the site (scrub in the browser)

 TIMELINE (Act 2)
  [ ] T1 HYDE ingestion, ~80 epochs through the same prep
  [ ] T2 how to show growth vs redistribution: fixed frame / growing frame / people-per-pixel caption
  [ ] T3 time interpolation (log-time); OT displacement interpolation between epochs
  [ ] T4 honesty: pre-1700 HYDE is a model, not observation; say so on the artefact
```

## Open questions

- Ocean: floor density (readable) or removed (the original ask)? Both get rendered; decide by eye.
- Frame: square Web-Mercator cut (85.05) or a wall-map cut (80)? Parameter, decide by eye.
- Which OT formulation survives zero-density oceans best (M3 vs M4 vs M5)?
