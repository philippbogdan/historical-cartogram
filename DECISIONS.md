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
- 2026-08-28  A1: x is periodic by default (a cylinder); `--x-boundary wall` keeps the old rectangle with
  hard dateline edges. A2: `Grid('mercator'|'equalarea')`; equal-area is Lambert cylindrical (y = sin lat).
- 2026-08-28  S1: torch backend on MPS (mirror-extended FFT for Neumann walls, grid_sample for particles);
  512 px in 2 s instead of 65 s; numpy backend kept as the reference; both agree to 1e-3 on synthetic tests.
- 2026-08-28  Rendering is forward splatting through the warp at any resolution (no pcolormesh); big cells are
  supersampled, holes filled from the nearest hit. Vectors are warped point-wise and split at the seam.
- 2026-08-28  A11: the metric grid is EQUAL-AREA cells (100 km x 100 km everywhere, square at the equator, taller
  towards the poles); Tissot circles are 300 km geodesic circles on a 15-degree lattice.
- 2026-08-28  Smoothing is specified in km (`--sigma-km`, default 30) so it shrinks with resolution; at 512 px
  the honest value is ~235 km (3 px).
- 2026-08-29  Solver step control: the displacement cap grows with the diffusion scale, max(max_disp,
  0.1 sqrt(2t)); 4096 diffusion now solves in 90 s on the M4 GPU (314 steps).
- 2026-08-29  Accuracy is set by smoothing in PIXELS, not by resolution: sigma 3 px gives +-10% population-
  weighted density error at 512 and at 4096 alike. Resolution buys sharpness (km), smoothing buys accuracy.
- 2026-08-29  M10 works: the Poisson one-shot folds everywhere (linearisation fails at 800x contrasts, as
  predicted); the BFO iteration converges to +-3.5% at 512-1024 and needs coarse-to-fine above that
  (fixed-point convergence slows with grid size). Its folds are the ocean creases OT theory predicts.
- 2026-08-29  GSM's flow needs +grad(Phi)/rho_t with lap(Phi) = rho0 - 1 (sign fixed after e014 came out
  inverted). GSM shears more (anisotropy p50 8.4) than diffusion (4.0), OT (3.4) or jellium (3.7).
- 2026-08-29  M9 (jellium) stops on the Lagrangian error (mesh areas), not on the deposited density, whose
  pixel noise never falls below ~1 in max-norm. At 512 it beats diffusion: -5%/+7% vs +-10%.
- 2026-08-29  S4 under review: folds never reach zero at floors <= 5% for any method (they scale with ocean
  compression and fall ~4x per mesh-stride doubling, e.g. e009: 37k at 4096, 2.3k at 1024). Fold repair
  only helps in the ocean; folds inside populated cells are reported separately. Proposed gate: the globe
  renders from the INVERSE map texture (splat-averaged, single-valued by construction), so the gate becomes
  "zero folds in populated cells, ocean folds below the pixel scale". Phil decides (F5).
- 2026-08-29  The humanity share lambda (`--share`) replaces the floor as the first-class knob: the solver
  equalises the blended measure lambda*people + (1-lambda)*frame area, so every lambda is a true cartogram of
  a stated measure and lambda = 0 is the untouched base map. floor f == share 1/(1+f) (floor 5% = share 0.95).
  At 1024 OT: share 0.95 -> 22.8k folds, 0.9 -> 9.8k, 0.8 -> 1.5k, 0.5 -> 0 folds, anisotropy p50 2.7.
  This is also the semantic version of the geography -> cartogram morph (R3): sweep lambda, not the displacement.
- 2026-08-29  Resolution ladder recorded in notes/resolution: data 100 m (GHS-POP 3", one tile on disk, 13 GB
  global), ingested 1 km, solver 10 km at 4096, smoothing 30 km. The 100 m detail is census counts disaggregated
  onto satellite-detected buildings (modelled below the census unit).
- 2026-08-29  Folds are convexity failures of the discrete OT potential (and interpolation error for the flows),
  not a property of the maps; M3 (back-and-forth) and M5 (monotone FD) preserve convexity by construction and
  move up the order. S5 added: exact band-limited field evaluation (NUFFT) for the flows.
- 2026-08-29  Compute policy (Phil): anything heavy runs on Metal (torch MPS), the rest on all cores. Done: the
  OT solver (TorchPoissonOT, 1024 c2f in 19 s), the splat renderer (4096 renders in seconds), scipy FFTs with
  workers = cpu_count. The numpy paths stay as references only.
- 2026-08-29  Pure limit (share 0.995) at 4096: the Poisson iteration does NOT converge there (residual 3.8,
  7.1M folds, +-15% density error) even with 600 iterations per level on the GPU; the picture still reads
  because the splat averages folds, but it is not a measurement. Pure needs the convexity-preserving solver
  (M3). Share 0.95 (e013) is the honest OT picture today; diffusion reaches 0.99 (e008) with +-10%.
- 2026-08-29  Naming: lambda is the HUMANITY share (1 = pure people, 0 = base map). Phil says "lambda = 0"
  meaning pure people; in the repo that is share 1.
- 2026-08-29  M3 is a two-stage solver: the back-and-forth ascent on the discrete dual (exact c-transforms
  in C, continuous pushforwards on the GPU, every iterate tightened so it is c-concave) gives the global
  convex transport structure; its map is a staircase where the map compresses (the argmin is quantised),
  so the Monge-Ampere iteration (M10) polishes it, started from the lightly smoothed BFM potential and
  keeping its best iterate, because the unguarded iteration diverges at the pure limit at 4096.
- 2026-08-29  X8 twist: OT's rotation is exactly zero by construction (gradient map, symmetric Jacobian);
  diffusion rotates 9 degrees at the median and 34 at p95 (e009). X7 shape error (Procrustes per country,
  population-weighted): OT 0.74, diffusion 0.86, OT at share 0.8 0.68.
- 2026-08-29  City labels come from Natural Earth populated places (pop_max), top 300-400, biggest first
  with a coarse occupancy grid for collisions; GHS-UCDB stays an option for Phase 6.
- 2026-08-29  Pure limit, what works: continuation in the share (M10 homotopy 0.95 -> 0.98 -> 0.99 -> 0.995 ->
  0.999, each stage warm-started, keep-best guard) reaches +-3.4% at 1024 pure with 222 folds in populated
  cells. The BFM route (M3) stalls at 4096 pure: 21% of the population misplaced after the ascent and the
  polish cannot recover (residual 4.3). M3 stays as a solver for moderate contrasts and as the reference
  for convexity; the artefact route to pure is the homotopy. M11 (semi-discrete) remains the other candidate.
- 2026-08-29  The pure OT world exists: e025 (share 0.999, 4096, float64 homotopy 0.95 -> 0.999), +-3.5%
  population-weighted density error, oceans 0.6% of the frame, 5.5k folds in populated cells (0.3%). float32
  on the GPU cannot hold the Hessian of a px^2 potential above ~1024 (residual 3.4 vs 1.0 in float64), so
  M10 runs in numpy float64 above 1024; the coarse levels are smoothed to 3 px at their own scale.
- 2026-08-29  Phase 2 closed: OT is the artefact's method (F4 default confirmed by the pictures); M3 stays as
  research code; M11 (semi-discrete) is the remaining route to zero folds anywhere.
- 2026-08-29  R5: the attractive flow (population as ordinary mass, stopped at t = 0.1) is the anti-cartogram
  Phil imagined: India and eastern China pinch to points and drag the graticule in like wells (e027).
  It is a picture with a free parameter (t), not a measurement; its equalisation metrics are meaningless.
- 2026-08-29  Jellium at 4096 is too slow with a per-step pixel cap (0.5 px per step at 8x the 512 displacement,
  ~2 h); stopped, run at 2048 instead (e026). A cap that grows with the smoothing scale, as in diffusion, is
  the fix if 4096 is ever needed for M9.
