# historical-cartogram: the megaplan, v2

As of 2026-08-29. Supersedes v1 (2026-08-28). Every node has an ID used in commits, experiment
folders, `EXPLORATION.md` and chat. This file says WHAT we want, in what order, and what is done.
Hows land in `DECISIONS.md` and `notes/`. Approved 2026-08-29; the work proceeds autonomously in the
order below, with checkpoints at the end of each phase, at any F, any spend, any deploy.

Status legend: `[x]` done, `[~]` partial, `[ ]` todo, `(F)` Phil's fork, `NEW` added in v2.

## Context

Thesis: places with many people feel full and big; places with few people seem vast but feel
empty and small. Instrument: maps whose area is people, from population rasters (never country
totals), for today, then across 12,000 years and into the next century, then on a globe, then with
any measure as a lens, and finally in a zoomable, pannable, Apple-Maps-grade viewer.

Unit: the humeter, 1 hm = 1 km at world-average density (~16 per km²). Grammar: a lens is
(the measure that gets the AREA, the measure painted as COLOUR, the moment). Combining maps is a
change of measure: painting nu on a mu-cartogram shows d nu / d mu (GDP on people = GDP per capita).


## The goal, stated once (2026-08-29, Phil: "execute fully until the full plan is complete")

The humeter world: a public repository and a static web artefact in which the Earth is drawn with
area = people, made from population rasters at the finest available resolution, and which can be
read at every scale and every moment:

1. TODAY: the pure-land OT cartogram (ocean 5% buffer, walls at the Bering Strait) at 8192 with
   100 m textures, countries, cities and rivers; the same warp on a globe.
2. TIME: the same cartogram for every HYDE epoch 10,000 BC to 2023, the GHS epochs 1975 to 2030
   and a projection to 2100, played back with measure interpolation, person-years, uncertainty
   bands and honesty labels, with historical cities appearing through the warps.
3. GLOBE: a rotatable WebGL globe, sphere area = people, overlays as per-capita maps (night lights,
   roads), labels, radius growing with population through time.
4. LENSES: other measures as area or colour (GDP, cropland, roads, lights, age), the ratio lens,
   the complement metric, the humeter ruler and geodesics.
5. GEOMETRY: curvature as colour, geodesic graticule, the lumpy Earth.
6. VIEWER: zoom, pan, rotate, continuous detail, time scrubber, lens and method switches, labels,
   metric grid, permalinks, story mode, print export; a static build ready to host (deploy is a
   checkpoint for Phil).

Representative means: every one of the six exists, works in a real browser or as a reviewed picture,
carries its source and honesty note, and is reproducible from the repo.

## Current state (2026-09-01)

Repo `~/historical-cartogram`, public, 72 commits, 51 experiments plus 163 timeline frames, `experiments/INDEX.md` and
`experiments/gallery.html` generated. Nothing spent; nothing deployed (V10/A9 is Phil's call).

Built and reviewed:
- Data: GHS-POP 2025 at 1 km and 100 m (global), GHS-POP epochs 1975-2030, HYDE 3.3 (126 epochs, base/lower/upper),
  SSP2 2020-2100 (Wang, Meng and Long 2022), Reba/Chandler cities, GRIP4 roads, Kummu GDP, Black Marble lights, Natural Earth.
- Solver: SpectralPoissonOT on the M4 GPU (float32, residual ~0.005, +-2.5% at 4096 in about a minute); land pure,
  ocean 5% buffer; walls at the Bering Strait for the flat frame, periodic for the globe. Diffusion, GSM, jellium,
  Tobler, gravity stills and the back-and-forth method stay as comparisons/research code.
- The today frame e033 (4096) with countries, labels, rivers, metric grid, Tissot, equipotentials, stretch, twist,
  flow lines, ghost coast; the pure world at 8192 (e030) as the sharpness ceiling.
- Time: 126 HYDE epochs at 2048, the 1 km era from GHS-POP (1975-2025) and the future from SSP2 (2030-2100) in one
  handover series (103 frames on the site), log-time scrubber, honesty label per frame, seam disagreement measured,
  person-years world, peak-year lens, historical cities through each epoch's warp, measure blends (T3 stills),
  bounds frames (L8: HYDE's bounds are a constant factor per epoch, so the shape does not move).
- Globe: three.js, vertices slide to their warped positions, textures pinned, morph slider, labels, 13 epochs with a
  radius that grows with sqrt(population).
- Lenses: GDP world, loneliness, light and roads per person, person-years, peak year (grammar in the pipeline).
- Geometry: curvature as colour, geodesic fans, humeter distances, the lumpy Earth as a relief globe (embedding open).
- Viewer: 100 m data viewer and warped tile server locally, static tile pyramid (z0-5) in the flat viewer with the
  humeter ruler and permalinks, compare (swipe), story (tour), time, globe, lenses and geometry pages, print export.
- Process: golden regression (tests/regression.py), honesty labels, repo hygiene (big renders stay local), every
  viewer driven in headless Chromium before commit.

Open or deferred (each noted in DECISIONS.md): M11 semi-discrete OT and L7 one-person-per-pixel, M12 sphere OT,
S5 exact fields, A16 pole cap, L10 age (WorldPop, 24 GB), L11 attention, L12 non-human world, L13 cumulative
person-years slider, A13 print (obj exported), the isometric lumpy Earth, V2 LOD by magnification beyond the max
pyramid, V5/V6 lens and method switches inside the viewer, V8 metric grid toggle, V10 hosting, T3 measure
interpolation as continuous playback, other SSP scenarios, jellium at 4096.

## Defaults I will take unless you object at approval

- F4 method: OT is the default for the artefact; diffusion and jellium stay as comparisons.
- F2 ocean: pure (share 1) is the resting picture once M3 delivers it; the share slider exists for
  readers who want to see where the Atlantic went; 0.95 is the interim default until M3.
- F3 frame: square Web-Mercator cut, walls at the Bering Strait (lon0 -168): Americas west, Pacific east; the globe has no frame.
- F5 fold gate: the globe renders from the inverse map (single-valued by construction); the gate is
  "zero folds in populated cells, ocean folds below the pixel scale"; M3/M11 aim for zero anywhere.
- F1 growth across time: flat playback keeps the frame full with a people-per-pixel caption; the
  globe grows with radius ~ sqrt(population). Revisited when the first playback exists.
- Money and publication: nothing is spent and nothing is deployed to philippbogdan.com without a
  checkpoint; everything else proceeds.

## The build, in order

```
 Phase 1  foundations        A1 A2 S1 S2 A11 R2 V0            [x]  S4 [~]  S5 [ ]                     7 of 9 done
 Phase 2  optimal transport  M10 [x] (spectral, pure)  M3 [~]  M11 [x]                             1 of 3 (the picture exists)
 Phase 3  gravity            M2 M9 R5 M8 [x]                                                       4 of 4
 Phase 4  legibility+gallery A14 A15 R6 R7 R8 R9 X7 X8 R10 X5 X6 S3 [x]                            12 of 12
 Phase 5  time               D3 D6 D8 D9 T8 T1 L3 L8 T4 T5 T6 T7 [x]  T3 R3 [x]                    12 of 14
 Phase 6  globe              A4 A6 A7 A8 [x]  D5 A5 [~]  A9 A16 [ ]  (M12 not needed so far)        4 of 8
 Phase 7  lenses             L1 L9 L4 L5 L6 [x]  D12 [~]  L10 L11 L12 L7 L13 [ ]                    5 of 11
 Phase 8  geometry (side)    G1 G4 G2 [x]  G3/A10 A13 [~]                                          3 of 5
 Phase 9  the viewer         A12 V1 V3 V4 V9 V11 V12-V15 [x]  V2 V5 V6 V7 [~]  V8 V10 [ ]           10 of 16
 Process  PR1 PR2 [x]                                                                              60 done, 13 partial, 11 open of 84
```

### Phase 1: foundations `[x]`

- A1 `[x]` periodic longitude. A2 `[x]` equal-area grid option. S1 `[x]` GPU solver. S2 `[x]` 4096 runs.
- A11 `[x]` metric grid + Tissot. R2 `[x]` population raster through the warp (other rasters in Phase 6).
- V0 `[x]` NEW dev viewer (local tile server, Leaflet, 100 m).
- S4 `[~]` fold gate as redefined under F5; fold repair exists and is population-aware.
- S5 `[ ]` exact band-limited field evaluation (NUFFT) for the flows, so their folds vanish structurally.

### Phase 2: optimal transport, pure and fold-free

- M10 `[x]` Poisson one-shot and BFO iteration with coarse-to-fine; with continuation in the share (homotopy)
  and float64 above 1024 it reaches the pure limit: e025, share 0.999 at 4096, ±3.5%, 5.5k folds in populated cells (0.3%).
- M3 `[~]` back-and-forth method implemented (C Legendre transforms, GPU pushforward, Monge-Ampère polish);
  it gives the global convex structure but its discrete map is a staircase where the map compresses and
  the ascent stalls at 4096 pure (21% mass misplaced). Kept as a solver for moderate contrasts; the pure
  route is M10 homotopy. Gate status: ±5% met (±3.5%); populated folds 5.5k of 1.9M, not zero (F5 default applies).
- M11 `[x]` NEW semi-discrete OT (Laguerre cells): one convex cell per N people, exact areas, no folds;
  a new picture (the power diagram of humanity) and the engine for L7. Mérigot/Lévy code as reference.
- M5 `[ ]` monotone Monge-Ampère finite differences, only if M3 stalls. M4, M6 `[ ]` optional comparisons.
- Gate: MET 2026-08-29 on error; folds gate under F5 default. e025 is the pure OT world at 4096.

### Phase 3: gravity `[~]`

- M2 `[x]` GSM flow (own torch; sign fixed). M9 `[x]` jellium flow at 512, 1024 (e028: -3.5%/+5.7%, 40 folds) and 2048 (e026: -4.3%/+5.5%); 4096 needs a scale-aware step cap.
- R5 `[x]` the G-slider as stills: attractive at t = 0.1 and 0.3 (e027, the anti-cartogram: India and China pinch to points) | Earth | repulsive = M9; the animation waits for the viewer.
- M8 `[x]` Tobler baseline (e029: density error -0.85/+2.45, the trivial answer is in the table).

### Phase 4: legibility and the gallery

- A14 `[x]` NEW city labels: GHS-UCDB urban centres (free, with population), ~300 largest at warped
  positions, unwarped text; sized by population.
- A15 `[x]` NEW rivers through the warp (Natural Earth rivers): Nile, Ganges, Yangtze as lines.
- R7 `[x]` NEW equipotentials: contour lines of the OT potential, the level sets of population gravity.
- R6 `[x]` NEW stretch map (log area scale as colour) and X8 `[x]` NEW twist map (local rotation angle);
  OT is zero rotation everywhere, diffusion is not.
- R8 `[x]` NEW flow lines from geography to cartogram. R9 `[x]` NEW ghost coastline under the warped one.
- X7 `[x]` NEW recognisability: per-country shape error after the best similarity transform, and label
  legibility (share of countries whose warped area holds their name).
- X5 `[x]` seam statistics. R10 `[x]` NEW generated gallery page from INDEX with thumbnails and metrics.
- X6 `[x]` gallery generated (experiments/gallery.html, 33 runs); F2-F4 defaults applied and written; Phil reviews asynchronously.
- S3 `[x]` the default method at 8192: e030, pure (share 0.999), 15 km smoothing, float64 homotopy, ±3.6%, 25k populated folds of 7.6M (0.3%), 65 min; the 100 m texture through it: A12 prototype `[x]` (`src/serve_warped.py`, the cartogram zoomable at 100 m through the inverse map).
- Gate: MET 2026-08-29 (defaults); reopened only if Phil changes an F.

### Phase 5: time, 10,000 BC to 2100

- D3 `[x]` HYDE 3.4 verified and ingested (epochs, bounds, format). D6 `[x]` NEW GHS-POP 1975-2030 at 1 km.
- T8 `[x]` NEW handover: HYDE before 1975, GHS-POP 1975-2025, SSP2 from 2030; no normalisation needed (scale invariance), seam disagreement measured.
- T1 `[x]` (126 epochs at 2048) every epoch through the default method; population conserved per epoch.
- T3 `[~]` playback by interpolating the MEASURE between epochs (every frame a true cartogram); log-time scrubbing.
- L3 `[x]` person-years frame. L8 `[x]` uncertainty from HYDE bounds. T4 `[x]` honesty label.
- D8 `[x]` NEW SSP gridded projections (Wang, Meng and Long 2022, SSP2 only) and T5 `[x]` NEW the future to 2100 by scenario.
- D9 `[x]` NEW Reba historical city points and T7 `[x]` NEW events on the map through each epoch's warp.
- T6 `[x]` NEW peak-time lens (epoch of maximum density per pixel). R3 `[x]` geography-to-cartogram morph.
- (F1) growth display, default as above. Gate: full playback reviewed.

### Phase 6: the globe

- A4 `[x]` globe renderer: sphere mesh, vertices slide, textures pinned to geography, inverse-map textures.
- D5 `[~]` overlay data: VIIRS night lights, GRIP4 roads, terrain, AIS shipping, flights.
- A5 `[~]` (lights and roads as per-capita on the flat frame; textures on the globe) overlays through the warp as per-capita maps (night lights nearly uniform as the check).
- A6 `[x]` labels (countries + A14 cities), ghost graticule, dark base. A16 `[ ]` NEW pole cap treatment.
- A7 `[x]` time on the globe, growing radius. A8 `[x]` one control cluster. A9 `[ ]` static hosting (checkpoint).
- M12 `[ ]` NEW sphere-native OT only if the equal-area cylinder shows polar damage (was A3).
- Gate: sphere area = people to Phase 2 tolerance; 60 fps on the M4.

### Phase 7: lenses

- L1 `[x]` the grammar in the pipeline. D12 `[~]` NEW measure catalogue ingested (GDP: Kummu/DOSE; lights;
  carbon: EDGAR/ODIAC; cropland: HYDE/GAEZ; travel time: Weiss 2018; attention; age: WorldPop; biomass).
- L9 `[x]` NEW ratio family (people/lights, people/cropland, people/CO2, people/roads).
- L10 `[~]` NEW age lens (median age; under-15s as the next generation). L11 `[ ]` NEW attention lens.
- L12 `[x]` NEW the non-human world (Earth by trees, cropland, protected land) as the complement.
- L4 `[x]` measure-to-measure OT morph. L5 `[x]` humeter ruler and geodesics. L6 `[x]` loneliness metric.
- L7 `[~]` one person per pixel (via M11). L13 `[ ]` NEW cumulative person-years as a slider.
- Gate: at least three lenses live with sources and honesty notes.

### Phase 8: geometry (side)

- G1 `[x]` curvature metric, G4 `[x]` curvature as colour, G2 `[x]` geodesic fans and humeter distances; G3/A10 lumpy Earth `[~]` (relief globe, humeter radius; the isometric embedding is open), A13 3D print `[~]` (lumpy_earth.obj exported, not printed).

### Phase 9: the viewer, last

- A12 `[x]` on-the-fly warped tiles (serve_warped.py) and a static pyramid (z0-5) for the site.
- V1-V11 `[x]` (V1 V3 V4 V9 V11 done; V2 V5 V6 V7 partial; V8 V10 open) as in v1 (zoom/pan/rotate, LOD by local magnification, flat + globe, time, lens, method,
  labels with collision, metric grid toggle, native textures, static hosting, asset budget).
- V12 `[x]` permalinks. V13 `[x]` compare/swipe. V14 `[x]` story mode (eight stops). V15 `[x]` print export (4096 px).

### Process, throughout

- PR1 `[x]` NEW golden regression: the world at 512 with fixed knobs, metrics within tolerance, run before commits
  (synthetic tests exist in `tests/synthetic.py`).
- PR2 `[x]` NEW honesty labels per layer on every artefact: observed / modelled / projected, with the source.
- Persistent files updated in the same commit as the work; `experiments/INDEX.md` regenerated; no attribution.

## Autonomous work order from approval

1. M3 (torch back-and-forth); pure OT at 4096; PR1 regression alongside.
2. A14, A15, R7, R6/X8, R9, X7, R10 gallery; S3 at 8192; A12 prototype (warped tiles in V0).
3. M9 at 4096, R5 stills, M8; gallery complete; F2-F4 defaults written.
4. Phase 5 in the listed order, T5/T7 included.
5. Phase 6, then 7, then 8, then 9. Checkpoints to Phil: end of each phase, any F, any spend, any deploy.

## The full graph

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
 │ M3 back-and-forth     [~]  <- next  │   └──────────────────────────┘
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

## Forks that are Phil's

- F1 growth across time (default: full frame + caption on the flat picture; growing globe).
- F2 ocean (default: pure once M3 delivers; slider for the rest). F3 frame (default: square Web-Mercator cut).
- F4 method (default: OT). F5 fold gate (default: inverse-map rendering, zero folds in populated cells).
- Any spend; any deploy to the site.

## Where things live

`README.md`, `PLAN.md` (this), `EXPLORATION.md` (graph + checklist), `DECISIONS.md`, `PRIOR_WORK.md`,
`DATA.md`, `notes/` (maths, ideas, resolution looks), `experiments/` (runs, INDEX), `src/hc/` (code),
`src/run.py` (one experiment), `src/serve_tiles.py` + `viewer/` (V0), `tests/synthetic.py`.

## v3, 2026-09-02: the product (Phil: "do all, filter later")

Two products and four hero stills, one visual language (notes/design-2026-09-02.md).

The interactive 2D map (V16-V18, the main deliverable):
- V16 progressive disclosure by zoom, all through the same continuous warp: world = countries (admin-0);
  zoom = provinces (Natural Earth 10m admin-1) and urban centres with their boundaries (GHS-UCDB); zoom
  further = districts inside cities (geoBoundaries ADM2/ADM3, open licence). Click a country to fly into it;
  hover highlights; smooth fades between levels; labels with real collision handling.
- V17 base styles switchable: simple colour (regional palette), topographic (terrain and hillshade through
  the warp), night lights, population density, the 100 m settlement texture at the deepest zoom.
- V18 one engine for 2D and 3D: warped geometries as vector tiles (PMTiles) plus warped raster tiles, drawn
  by MapLibre GL, which has both Mercator and globe projections with a built-in transition. The 2D map uses
  the wall-frame warp (walls at the Bering Strait); the globe uses the periodic equal-area warp. The three.js
  globe and the Leaflet viewer are retired once this is live.
- V2 nested 100 m solves make the district level true rather than painted (residual OT inside city windows
  composed with the global map). D13 boundary data: NE admin-1, GHS-UCDB, geoBoundaries.

The hero stills: H1 the today world (4096 now; 8192 only via the float64 path, the GPU solver runs out of
memory at 8192); H2 the morph loop geography to cartogram (R3, McCann interpolation of the OT map); H3 eight
epochs as small multiples (T3 in-betweens on the time page); H4 the GDP pair with GDP per person-year as the
ratio. Then: V7 label collision, A5 per-capita overlays on the globe, A16 pole cap, L12 the non-human world
(Copernicus 100 m tree and crop cover, downloading), L10 age lens (WorldPop 1 km age bands, reducing to
5 arcmin one file at a time), M11 + L7 semi-discrete OT (one cell per million people), the paper's prior-art
search, the site cut to map, time and story with the gallery behind.
Dropped on purpose: S5, M3 completion, M12, P2, L11. Hosting (A9/V10) and the print (A13) stay Phil's.
Checkpoints at each piece; nothing spent; nothing deployed.

Order of work: H1 (done at 4096, e036) -> V18 engine skeleton with V16 country level -> H2 -> V16 city and
district levels -> V17 styles -> H3, H4 -> V2 -> the rest.
