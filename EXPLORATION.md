# Exploration graph

v2 (2026-08-29): IDs and phases in `PLAN.md`; NEW nodes from notes/ideas-2026-08-29.md are in the graph.

Phases and gates live in `PLAN.md`; this file is the graph plus the status checklist.

Thesis to visualise: places with many people feel full (big); places with few people seem vast
but feel empty (small). Area = people, on a map you can still read.

```
                    "dense places feel full and big; empty places seem vast but small"
                                              │
 DATA                                         ▼                                    PREP
 D1 GHS-POP 2025 30" [x]   D2 GHS-POP 3" 100 m global [x]             ┌── P1 exact count re-binning [x]
 D3 HYDE 3.4 [x]  D6 GHS 1975-2030 [x]  D8 SSP 2100 [x]  D9 Reba cities [x]  ├── P2 share + smoothing [~]
 D4 Natural Earth [x]  D11 rivers [x]  D10 GHS-UCDB cities [ ]  D7 BUILT/SMOD [ ]  └── P3 sphere-native [ ]
 D5 lights, roads, terrain, shipping, flights [~]   D12 lens measures [~]
                                                 │
                                       grid choice (a parameter) [x]
                                    ┌────────────┴────────────┐
                            Mercator pixels            equal-area cylinder, periodic lon
                            flat rectangle picture     anything shown on a sphere
                                    └────────────┬────────────┘
                       SOLVER INFRASTRUCTURE     │   S1 GPU [x]  S2 4096 [x]  S3 8192 [x]
                                                 │   S4 fold gate (F5) [~]  S5 exact fields [ ]
                                                 ▼
                    ╔════════════════════════════════════════════════════════╗
                    ║  THE POPULATION MANIFOLD   g = (rho/rho_bar)(dx²+dy²)  ║
                    ║  humeter: 1 hm = 1 km at world-average density         ║
                    ║  same construction for ANY measure mu (lenses)         ║
                    ║  curved: curvature is what every flattening pays for   ║
                    ╚═════════════╤═══════════════════════════╤══════════════╝
                                  │ flatten it                │ keep it curved
                                  ▼                           ▼
 FLATTENINGS                                           GEOMETRY (Phase 8)
 ┌─ process, no objective ─────────────┐               G1 curvature metric (2+1 gravity)  [x]
 │ M1 diffusion  [x]                   │               G2 geodesic graticule (lensing)     [x]
 │ M2 GSM flow   [x]  ──┐ same Poisson │               G3 3D embedding = A10 lumpy Earth   [~]
 │ M9 jellium    [x]  ◄─┘              │               G4 curvature as colour              [x]
 │ M8 Tobler     [x]                   │                          ▲
 └───────────────┬─────────────────────┘                          │ A11 metric grid [x] ties them
 ┌─ least displacement (OT) ───────────┐   ┌─ least angle distortion ─┐
 │ M10 Poisson iteration [x] (not pure)│   │ M7 quasiconformal [ ]    │
 │ M3 back-and-forth     [~]  <- now   │   └──────────────────────────┘
 │ M11 semi-discrete     [x]  NEW      │
 │ M5 monotone FD [ ]  M4 Sinkhorn [ ] │
 │ M6 sliced [ ]   M12 on sphere [ ]   │
 └───────────────┬─────────────────────┘
     R5 G-slider: attractive (+G) ◄── Earth ──► repulsive (-G) = M9   [x]
                                ▼
 METRICS  X1 area [x]  X2 folds [x]  X3 anisotropy [x]  X4 displacement [x]  X5 seams [x]
          X6 gallery [x]  X7 recognisability NEW [x]  X8 twist NEW [x]      -> F2 F3 F4 (defaults set)
                                ▼
 RENDER   R1 mesh+coasts+borders+graticule+error [x]  R2 rasters through the warp [x]  R3 morph [x]
          R4 WebGL mesh [x]  R6 stretch map NEW [x]  R7 equipotentials NEW [x]  R8 flow lines NEW [x]
          R9 ghost coastline NEW [x]  R10 gallery page NEW [x]  countries coloured+labelled [x]
        ┌───────────────────────┼───────────────────────────┐
        ▼                       ▼                           ▼
 FLAT RECTANGLE [x]      GLOBE (Phase 6)                 LUMPY EARTH (A10 [~] relief globe, A13 [~] obj)
 share knob [x]          A4 renderer [x]  A5 overlays = per-capita [~]  A6 labels [x]  A7 time, growing radius [x]
 pure via spectral OT [x] A8 controls [x]  A9 hosting [ ] (Phil)  A14 cities [x]  A15 rivers [x]  A16 pole cap [ ]
                                ▼
 TIMELINE (Phase 5)   T1 epochs [x]  T3 measure interpolation [~] (blend stills)  T4 honesty [x]  T8 handover [x]
                      T5 future 2100 [x]  T6 peak time [x]  T7 events [x]  L3 person-years [x]  L8 uncertainty [x]  (F1 default kept)
                                ▼
 LENSES (Phase 7)     L1 grammar [x]  D12 catalogue [~]  L4 measure morph [x]  L5 humeter ruler+geodesics [x]  L6 loneliness [x]
                      L7 one person per pixel (M11) [x]  L9 ratios [x]  L10 age [~]  L11 attention [ ]
                      L12 non-human world [x]  L13 cumulative person-years [ ]
                                ▼
 VIEWER (Phase 9)     V0 dev viewer [x]  A12 warped tiles [x]  V1 zoom/pan/rotate [x]  V2 LOD by magnification [~]
                      V3 flat+globe [x]  V4 time [x]  V5 lens [x]  V6 method/G/morph [~]  V7 labels [~]  V8 metric grid [~]
                      V9 native textures [x]  V10 static hosting [ ] (Phil)  V11 asset budget [x]
                      V12 permalinks [x]  V13 compare [x]  V14 story mode [x]  V15 print export [x]
 PROCESS              PR1 golden regression [x]  PR2 honesty labels [x]
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
  [x] D2 GHS-POP 2020, 3 arcsec (~100 m) for final renders
  [x] D3 HYDE 3.4, 5 arcmin population grids, 10000 BC to 2025  <- timeline, LAST
  [x] D4 Natural Earth 50m / 110m land, coastline, borders (drawing only)
  [~] D5 night lights (VIIRS) as a texture to push through the warp

 PREP
  [x] P1 counts -> Mercator rectangle by exact re-binning (no density reprojection)
  [~] P2 floor and smoothing policy: floor as fraction of mean, sigma in px (first sweep in experiments/INDEX.md)
  [ ] P3 sphere-native variant (skip Mercator; Choi spherical DEM style)

 METHODS (each one: same input, same metrics, same render)
  [x] M1 diffusion, Gastner-Newman 2004: DCT heat flow, Neumann box, RK4 particles   (v0 works, e001-e005)
  [x] M2 flow-based, Gastner-Seguy-More 2018, via cartogram-cpp (reference implementation)
  [~] M3 OT / W2 Brenier map via back-and-forth method (Jacobs-Leger 2020, bfm)      <- the new picture
  [ ] M4 OT via entropic Sinkhorn on the grid (separable kernel), barycentric map
  [ ] M5 OT via monotone Monge-Ampere finite differences (BFO 2014), own implementation
  [ ] M6 sliced OT (what vruba is playing with, 2026-06)
  [ ] M7 quasiconformal / min-anisotropy DEM (Lyu-Choi-Lui 2024); no public code, would be ours
  [x] M8 Tobler pseudo-cartogram (separable 1-D integrals): the trivial baseline
  [x] M9 anti-gravity (jellium) flow, particle-mesh on the GPU (e016b): best equalisation of the flows
  [x] M10 Poisson one-shot (e010, folds everywhere, as predicted) and BFO iteration with coarse-to-fine (e011-e013, e017): +-3.5%, creases in the ocean

 METRICS (X1..X5 computed; X6 is eyes)
  [x] X1 area error: population-weighted log(rho0/area) p05/p50/p95, min, max
  [x] X2 folds: number of negative-area cells (bijectivity)
  [x] X3 shape: anisotropy = singular-value ratio of the local Jacobian
  [x] X4 displacement: mean and max |T(x) - x| in px
  [x] X5 seams: how the ocean collapsed (width statistics along coast pairs)
  [x] X6 recognisability: side-by-side gallery, judged by eye

 KNOBS (sweep per method)
  humanity share lambda in {1.0, 0.95, 0.9, 0.8, 0.5} (floor = (1-lambda)/lambda) | sigma in km | lat cut in {80, 85.05}
  width in {512, 1024, 2048, 4096} | ocean floor vs ocean removed

 RENDER
  [x] R1 warped mesh (pcolormesh) + warped coastlines, borders, graticule, error map
  [x] R2 rasters through the same field: population, night lights, terrain
  [x] R3 morph geography -> cartogram (interpolate displacement; OT gives the geodesic)
  [x] R4 WebGL mesh for the site (scrub in the browser)
  [x] R5 the human-gravity slider G in [-1, +1]: attractive flow (anti-cartogram) | Earth | repulsive flow (cartogram)
  [x] A11 metric grid (100 km ground squares through the warp) + Tissot ellipses
  [x] A12 zoomable warped tile pyramid; [~] A13 3D print
  [x] L1 lens grammar (mu area, nu colour, t); [~] L2 measure catalogue; [x] L3 person-years cartogram
  [x] L4 measure-to-measure OT morph; [x] L5 humeter ruler + geodesics; [x] L6 loneliness metric 1/rho
  [~] L7 one person per pixel gigapixel; [x] L8 uncertainty texture from HYDE bounds

 SOLVER INFRASTRUCTURE
  [x] S1 GPU solver (M4, MPS)   [x] S2 4096 run (e008 e009)   [x] S3 8192 run   [ ] S5 exact field evaluation (NUFFT) for the flows   [~] S4 fold gate: repair exists, gate definition under review (see DECISIONS 2026-08-29)

 VIEWER (Phase 9, last)
  [x] V0 dev viewer (local tile server + Leaflet), serving the 100 m raster
  [x] V1 zoom/pan/rotate  [~] V2 LOD by local magnification  [x] V3 flat + globe, same assets
  [x] V4 time scrubber  [x] V5 lens switch  [~] V6 method switch, G-slider, morph
  [~] V7 labels with collision  [~] V8 metric grid toggle  [x] V9 native textures, zoom to city
  [ ] V10 static hosting in free tiers  [x] V11 asset budget and cost gate

 ARTEFACT (the globe, Act 3)
  [x] A1 compute on a cylinder: periodic in longitude (FFT in x, DCT in y); the dateline must not tear
  [x] A2 equal-area cylindrical grid (x = lon, y = sin lat) for anything shown on a sphere:
         sphere area = people, exactly; Mercator pixels stay only for the flat rectangle picture
  [ ] A3 sphere-native solvers later (diffusion via spherical harmonics; OT on S^2 is research-grade,
         Hamfeldt-Turnquist 2021 has numerics, no public code)
  [x] A4 globe renderer: one sphere mesh (~1024x512), vertices displaced along the sphere per epoch,
         UVs fixed to geography so every raster overlay comes for free; no inverse map needed
  [~] A5 overlays as textures through the same warp: night lights (VIIRS VNL / Black Marble), road
         density (GRIP4), terrain, shipping (AIS density), flights; each one reads as a PER-CAPITA map
  [x] A6 labels: ~300 largest cities at warped positions, text unwarped; ghost graticule; dark Apple-style base
  [x] A7 time on the globe: per-epoch displacement textures (RGBA16F 1024x512 x ~80 epochs ~ 80 MB),
         blended in the vertex shader; log-time scrubber; growth shown by globe radius ~ sqrt(population)
  [x] A8 controls kept small: time is the hero; method, G-slider, morph and overlay behind one cluster
  [ ] A9 static hosting on the existing site (no server, no cost); WebGL2 or WebGPU
  [~] A10 lumpy Earth (first version is a relief globe, radius = humeter scale; free spring relaxation buckles): isometric-ish 3D embedding of the population manifold on the sphere (spring
         relaxation of a sphere mesh with population rest lengths); the sculpture, ties to G1-G3

 TIMELINE (Act 2)
  [x] T1 HYDE ingestion, ~80 epochs through the same prep
  [ ] T2 how to show growth vs redistribution: fixed frame / growing frame / people-per-pixel caption /
         growing globe (radius ~ sqrt(pop): 6000 BC is a marble)
  [~] T3 time interpolation (log-time); OT displacement interpolation between epochs
  [x] T4 honesty: pre-1700 HYDE is a model, not observation; say so on the artefact
```

## Side branch: population geometry (not a warp)
  [x] G1 conformal metric with curvature K ~ (rho - rho_bar) (2+1 gravity, Liouville equation)
  [x] G2 geodesic graticule: lat/long lines bent around cities like lensing
  [~] G3 3D embedding of the population manifold (relief globe only, see A10) (rho/rho_bar)(dx^2+dy^2), a surface whose area is people
  [x] G4 curvature field K rendered as colour on the map

## Open questions

- Ocean: floor density (readable) or removed (the original ask)? Both get rendered; decide by eye.
- Frame: square Web-Mercator cut (85.05) or a wall-map cut (80)? Parameter, decide by eye.
- Which OT formulation survives zero-density oceans best (M3 vs M4 vs M5)?

 NEW in v2 (see PLAN.md for the phase each belongs to)
  [x] M11 semi-discrete OT   [ ] M12 OT on the sphere   [ ] S5 exact field evaluation
  [x] X7 recognisability     [x] X8 twist map
  [x] R6 stretch map  [x] R7 equipotentials  [x] R8 flow lines  [x] R9 ghost coastline  [x] R10 gallery page
  [x] D6 GHS 1975-2030  [ ] D7 BUILT/SMOD  [x] D8 SSP 2100  [x] D9 Reba cities  [ ] D10 GHS-UCDB  [x] D11 rivers  [~] D12 lens measures
  [x] A14 city labels  [x] A15 rivers  [ ] A16 pole cap
  [x] T5 future  [x] T6 peak time  [x] T7 events  [x] T8 handover
  [x] L9 ratios  [~] L10 age  [ ] L11 attention  [x] L12 non-human world  [ ] L13 cumulative person-years
  [x] V12 permalinks  [x] V13 compare  [x] V14 story mode  [x] V15 print export
  [x] PR1 golden regression  [x] PR2 honesty labels
