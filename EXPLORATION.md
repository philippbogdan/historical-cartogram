# Exploration graph

Phases and gates live in `PLAN.md`; this file is the graph plus the status checklist.

Thesis to visualise: places with many people feel full (big); places with few people seem vast
but feel empty (small). Area = people, on a map you can still read.

```
                    "dense places feel full and big; empty places seem vast but small"
                                              │
 DATA                                         ▼                                    PREP
 D1 GHS-POP 2025 30" [x] ──┐                                          ┌── P1 exact count re-binning [x]
 D2 GHS-POP 3"       [ ] ──┼── population raster (people per cell) ───┼── P2 floor + smoothing   [~]
 D3 HYDE 3.4 (time)  [ ] ──┘                     │                    └── P3 sphere-native        [ ]
 D4 Natural Earth    [x] ── borders, coasts (drawing only)
 D5 night lights, roads, terrain, shipping, flights [ ] ── overlays (A5)
 L2 GDP, carbon, cropland, travel time, attention, under-15s [ ] ── lenses (Phase 7)
                                                 │
                                       grid choice (a parameter)
                                    ┌────────────┴────────────┐
                            Mercator pixels            equal-area cylinder, periodic lon (A1/A2) [x]
                            flat rectangle picture     anything shown on a sphere
                                    └────────────┬────────────┘
                                                 │
                       SOLVER INFRASTRUCTURE     │   S1 GPU solver [x]   S2 4096 [x]   S3 8192 [ ]
                                                 │   S4 fold gate under review [~]
                                                 ▼
                    ╔════════════════════════════════════════════════════════╗
                    ║  THE POPULATION MANIFOLD   g = (rho/rho_bar)(dx²+dy²)  ║
                    ║  unit of length: the HUMETER (1 hm = 1 km at the       ║
                    ║  world-average density, ~16 people per km²)            ║
                    ║  same construction for ANY measure mu: g_mu (see L)    ║
                    ║  areas are people, angles are geographic, and it is    ║
                    ║  CURVED:  K = -(rho_bar/2rho) lap log(rho/rho_bar)     ║
                    ║  curvature is the obstruction; every method pays it    ║
                    ╚═════════════╤═══════════════════════════╤══════════════╝
                                  │ flatten it                │ keep it curved
                                  ▼                           ▼
 FLATTENINGS = cartogram methods                       GEOMETRY (nothing moves, the metric changes)
 ┌─ process, no objective ─────────────┐               G1 conformal metric, K ~ (rho - rho_bar):
 │ M1 diffusion   v = -grad log rho [x]│                  2+1 gravity, Liouville equation      [ ]
 │ M2 GSM 2018    v = +grad Phi / rho_t│──┐            G2 geodesic graticule: lines bend around
 │                one Poisson solve [x]│  │ same          cities like lensing                  [ ]
 │ M9 anti-gravity v = +grad Phi_t     │◄─┘ Poisson    G3 3D embedding of the manifold (= A10) [ ]
 │                jellium, PM code  [x]│               G4 curvature K as colour: where space
 │ M8 Tobler 1-D baseline           [ ]│                  bends                                [ ]
 └───────────────┬─────────────────────┘                          ▲
                 │                                                │ the metric grid ties them:
 ┌─ least displacement ────────────────┐   ┌─ least angle distortion ─┐   A11 on the flat map it
 │ M10 Poisson one-shot = linearised OT│ [x]   │ M7 quasiconformal DEM    │   shows scale and shear;
 │     iterate (BFO 2010) ──► M5       │   │    Lyu-Choi-Lui 2024,    │   on the manifold it is
 │ M5 Monge-Ampère finite differences  │   │    no code, ours     [ ] │   the geodesic grid
 │ M3 OT via back-and-forth (bfm)  [ ] │   └────────────┬─────────────┘
 │ M4 OT entropic Sinkhorn         [ ] │                │
 │ M6 sliced OT (vruba 2026-06)    [ ] │                │
 └───────────────┬─────────────────────┘                │
                 │                                      │
     R5 the G-slider:  attractive (+G) ◄── Earth (0) ──► repulsive (-G) = M9 at t -> inf
         cities collapse to points          geography          the cartogram
                 │                                      │
                 └──────────────┬───────────────────────┘
                                ▼
 METRICS, identical for every method
 X1 area error [x]   X2 folds [x] (gate S4)   X3 anisotropy [x]
 X4 displacement [x] X5 seams [ ]   X6 eyes: side-by-side gallery [ ]  -> forks F2 F3 F4
                                │
                                ▼
 RENDER
 R1 warped mesh + coasts + borders + graticule + error map [x]
 R2 any raster through the warp: population, night lights, terrain [ ]
 R3 morph geography -> cartogram (OT gives the geodesic) [ ]
 R4 WebGL mesh [ ]
 A11 METRIC GRID: 100 km ground squares pushed through the warp. Big cell = feels full,
     tiny cell = feels empty. The most literal picture of the thesis. Plus Tissot ellipses
     (circles -> ellipses) so X3 is visible, not just a number. [ ]
        ┌───────────────────────┼───────────────────────────┐
        ▼                       ▼                           ▼
 FLAT RECTANGLE          GLOBE (Phase 6)               LUMPY EARTH (A10)
 the original ask        A3 sphere-native if needed    3D embedding of the population
 Mercator pixels         A4 sphere mesh, vertices      manifold: India a lobe, oceans
 fills the frame            slide, UVs pinned          creases; spring relaxation of a
                         A5 overlays = PER-CAPITA maps sphere mesh with population rest
                            (light per person, roads   lengths. The sculpture. <-> G1-G3
                            per person)                A13 as a 3D print
                         A6 labels (~300 cities),
                            ghost graticule, dark base
                         A7 time: per-epoch textures,
                            growing radius ~ sqrt(pop)
                         A8 one control cluster; time is the hero
                         A9 static site, no server, no cost
                                │
                                ▼
 TIMELINE (Phase 5)
 T1 HYDE ~80 epochs through the same prep and method [ ]
 T2 growth vs redistribution: fixed frame / caption / growing frame / growing globe [ ] (F1)
 T3 log-time scrubbing; OT displacement interpolation between epochs [ ]
 T4 honesty: pre-1700 is HYDE's model, not observation [ ]
                                │
                                ▼
 LENSES (Phase 7): a lens = (mu: the measure that gets the AREA, nu: the measure shown as COLOUR, t)
 L1 the grammar: a cartogram is a change of measure; every overlay nu on a mu-cartogram shows
    d nu / d mu, the density of one measure with respect to another (GDP on people = GDP per
    capita; lights on people = light per person; people on GDP = people per dollar)          [ ]
 L2 measure catalogue, all gridded, all free: people (GHS, WorldPop age-sex), GDP (Kummu 5',
    DOSE subnational, Chen 1 km), night lights (VIIRS), CO2 (EDGAR, ODIAC), cropland (HYDE, GAEZ),
    travel time to cities (Weiss 2018), attention (GDELT), under-15s (WorldPop) = the next generation [ ]
 L3 person-years: integrate HYDE over 12,000 years; area = human life lived there              [ ]
 L4 measure-to-measure morph: OT from the people-world to the dollar-world; the motion IS
    inequality (Africa and South Asia deflate); the transport plan is money moving to people    [ ]
 L5 humeter ruler in the UI ("1 cm = 3 million people here"); humeter geodesics = the path
    of fewest people (Fermat with index sqrt(rho/rho_bar)); distances London-Moscow in hm       [ ]
 L6 the complement metric 1/rho: the loneliness lens, where empty places are vast; the thesis
    has two halves and each metric renders one                                                [ ]
 L7 one person per pixel: an 8.2-gigapixel zoomable image where every pixel is a person        [ ]
 L8 uncertainty as texture: HYDE ships lower/upper bounds; blur or grain the ancient frames
    by their uncertainty                                                                       [ ]
                                │
                                ▼
 THE VIEWER (Phase 9, last): Apple-Maps grade, flat and globe from the same assets
 ┌──────────────────────────────────────────────────────────────────────────────────────┐
 │ V1 zoom, pan, rotate; inertia; fluid fractional zoom                            [ ]  │
 │ V2 continuous level of detail driven by local magnification: a magnified Dhaka        │
 │    gets finer source data than a compressed Siberia at the same screen zoom     [ ]  │
 │ V3 flat and globe from the same assets                                          [ ]  │
 │ V4 time scrubber    V5 lens switch    V6 method switch + G-slider + morph      [ ]  │
 │ V7 labels with collision handling     V8 metric grid + Tissot toggle           [ ]  │
 │ V9 native-resolution textures, zoom to city scale anywhere                      [ ]  │
 │ A12 the zoomable warped tile pyramid behind V9 (warp 4-8k, textures 100 m/500 m)[ ]  │
 │ V10 static hosting inside free tiers                                            [ ]  │
 │ V11 asset budget: warp fields per epoch + tiles sized and listed; anything that       │
 │     would cost money goes to Phil with numbers first                            [ ]  │
 └──────────────────────────────────────────────────────────────────────────────────────┘
```

Rules for lenses: one measure per visual channel (area, colour, height, label size), never two on one
channel, at most three channels at once. Height (extrinsic bulges) fights the area reading; use it
only when area is not carrying a measure.

Edges worth remembering: M2 and M9 share the Poisson potential (GSM 2018 is gravity in disguise);
M10 iterated becomes M5 (the gravity picture is an OT solver); R5 joins M9 to the anti-cartogram;
A11 joins the flattenings to the geometry branch; X2 gates the globe; T2 is a design fork.


# Status checklist

As of 2026-08-28 (evening). Legend: `[ ]` todo, `[~]` in progress, `[x]` done, `[!]` blocked.
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
  [~] P2 floor and smoothing policy: floor as fraction of mean, sigma in px (first sweep in experiments/INDEX.md)
  [ ] P3 sphere-native variant (skip Mercator; Choi spherical DEM style)

 METHODS (each one: same input, same metrics, same render)
  [x] M1 diffusion, Gastner-Newman 2004: DCT heat flow, Neumann box, RK4 particles   (v0 works, e001-e005)
  [ ] M2 flow-based, Gastner-Seguy-More 2018, via cartogram-cpp (reference implementation)
  [ ] M3 OT / W2 Brenier map via back-and-forth method (Jacobs-Leger 2020, bfm)      <- the new picture
  [ ] M4 OT via entropic Sinkhorn on the grid (separable kernel), barycentric map
  [ ] M5 OT via monotone Monge-Ampere finite differences (BFO 2014), own implementation
  [ ] M6 sliced OT (what vruba is playing with, 2026-06)
  [ ] M7 quasiconformal / min-anisotropy DEM (Lyu-Choi-Lui 2024); no public code, would be ours
  [ ] M8 Tobler pseudo-cartogram (separable 1-D integrals): the trivial baseline
  [x] M9 anti-gravity (jellium) flow, particle-mesh on the GPU (e016b): best equalisation of the flows
  [x] M10 Poisson one-shot (e010, folds everywhere, as predicted) and BFO iteration with coarse-to-fine (e011-e013, e017): +-3.5%, creases in the ocean

 METRICS (X1..X5 computed; X6 is eyes)
  [x] X1 area error: population-weighted log(rho0/area) p05/p50/p95, min, max
  [x] X2 folds: number of negative-area cells (bijectivity)
  [x] X3 shape: anisotropy = singular-value ratio of the local Jacobian
  [x] X4 displacement: mean and max |T(x) - x| in px
  [ ] X5 seams: how the ocean collapsed (width statistics along coast pairs)
  [ ] X6 recognisability: side-by-side gallery, judged by eye

 KNOBS (sweep per method)
  humanity share lambda in {1.0, 0.95, 0.9, 0.8, 0.5} (floor = (1-lambda)/lambda) | sigma in km | lat cut in {80, 85.05}
  width in {512, 1024, 2048, 4096} | ocean floor vs ocean removed

 RENDER
  [x] R1 warped mesh (pcolormesh) + warped coastlines, borders, graticule, error map
  [ ] R2 rasters through the same field: population, night lights, terrain
  [ ] R3 morph geography -> cartogram (interpolate displacement; OT gives the geodesic)
  [ ] R4 WebGL mesh for the site (scrub in the browser)
  [ ] R5 the human-gravity slider G in [-1, +1]: attractive flow (anti-cartogram) | Earth | repulsive flow (cartogram)
  [x] A11 metric grid (100 km ground squares through the warp) + Tissot ellipses
  [ ] A12 zoomable warped tile pyramid; [ ] A13 3D print
  [ ] L1 lens grammar (mu area, nu colour, t); [ ] L2 measure catalogue; [ ] L3 person-years cartogram
  [ ] L4 measure-to-measure OT morph; [ ] L5 humeter ruler + geodesics; [ ] L6 loneliness metric 1/rho
  [ ] L7 one person per pixel gigapixel; [ ] L8 uncertainty texture from HYDE bounds

 SOLVER INFRASTRUCTURE
  [x] S1 GPU solver (M4, MPS)   [x] S2 4096 run (e008 e009)   [ ] S3 8192 run   [ ] S5 exact field evaluation (NUFFT) for the flows   [~] S4 fold gate: repair exists, gate definition under review (see DECISIONS 2026-08-29)

 VIEWER (Phase 9, last)
  [ ] V1 zoom/pan/rotate  [ ] V2 LOD by local magnification  [ ] V3 flat + globe, same assets
  [ ] V4 time scrubber  [ ] V5 lens switch  [ ] V6 method switch, G-slider, morph
  [ ] V7 labels with collision  [ ] V8 metric grid toggle  [ ] V9 native textures, zoom to city
  [ ] V10 static hosting in free tiers  [ ] V11 asset budget and cost gate

 ARTEFACT (the globe, Act 3)
  [x] A1 compute on a cylinder: periodic in longitude (FFT in x, DCT in y); the dateline must not tear
  [x] A2 equal-area cylindrical grid (x = lon, y = sin lat) for anything shown on a sphere:
         sphere area = people, exactly; Mercator pixels stay only for the flat rectangle picture
  [ ] A3 sphere-native solvers later (diffusion via spherical harmonics; OT on S^2 is research-grade,
         Hamfeldt-Turnquist 2021 has numerics, no public code)
  [ ] A4 globe renderer: one sphere mesh (~1024x512), vertices displaced along the sphere per epoch,
         UVs fixed to geography so every raster overlay comes for free; no inverse map needed
  [ ] A5 overlays as textures through the same warp: night lights (VIIRS VNL / Black Marble), road
         density (GRIP4), terrain, shipping (AIS density), flights; each one reads as a PER-CAPITA map
  [ ] A6 labels: ~300 largest cities at warped positions, text unwarped; ghost graticule; dark Apple-style base
  [ ] A7 time on the globe: per-epoch displacement textures (RGBA16F 1024x512 x ~80 epochs ~ 80 MB),
         blended in the vertex shader; log-time scrubber; growth shown by globe radius ~ sqrt(population)
  [ ] A8 controls kept small: time is the hero; method, G-slider, morph and overlay behind one cluster
  [ ] A9 static hosting on the existing site (no server, no cost); WebGL2 or WebGPU
  [ ] A10 lumpy Earth: isometric-ish 3D embedding of the population manifold on the sphere (spring
         relaxation of a sphere mesh with population rest lengths); the sculpture, ties to G1-G3

 TIMELINE (Act 2)
  [ ] T1 HYDE ingestion, ~80 epochs through the same prep
  [ ] T2 how to show growth vs redistribution: fixed frame / growing frame / people-per-pixel caption /
         growing globe (radius ~ sqrt(pop): 6000 BC is a marble)
  [ ] T3 time interpolation (log-time); OT displacement interpolation between epochs
  [ ] T4 honesty: pre-1700 HYDE is a model, not observation; say so on the artefact
```

## Side branch: population geometry (not a warp)
  [ ] G1 conformal metric with curvature K ~ (rho - rho_bar) (2+1 gravity, Liouville equation)
  [ ] G2 geodesic graticule: lat/long lines bent around cities like lensing
  [ ] G3 3D embedding of the population manifold (rho/rho_bar)(dx^2+dy^2), a surface whose area is people
  [ ] G4 curvature field K rendered as colour on the map

## Open questions

- Ocean: floor density (readable) or removed (the original ask)? Both get rendered; decide by eye.
- Frame: square Web-Mercator cut (85.05) or a wall-map cut (80)? Parameter, decide by eye.
- Which OT formulation survives zero-density oceans best (M3 vs M4 vs M5)?
