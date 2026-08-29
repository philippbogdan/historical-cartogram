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

## Current state (2026-08-29)

Repo `~/historical-cartogram`, public, 30 commits, 24 experiments, `experiments/INDEX.md` generated.

Working today:
- Data: GHS-POP 2025 at 1 km and at 100 m globally (11 GB + overviews, 8.191 bn people); Natural Earth.
- Prep: exact count re-binning onto a Mercator or equal-area cylinder, periodic in longitude.
- Solvers, all on the M4 GPU: diffusion (M1, 4096 in 90 s), GSM flow (M2), jellium flow (M9),
  Poisson-iterated OT with coarse-to-fine (M10, 4096 in ~1 min). Numpy references kept, multi-core.
- Metrics X1-X4 on every run; population-aware fold repair; humanity-share knob (the floor, generalised).
- Renders: forward-splat renderer on the GPU (any raster, any resolution), coasts, borders, graticule,
  metric grid and Tissot (A11), error map, countries coloured and labelled.
- V0 dev viewer: local tile server over any GeoTIFF, Leaflet, retina, settlement/density modes;
  serving the 100 m world at http://localhost:8765/.
- Findings that shape the rest: OT reads as a real map (no rotation, least movement, 3x more accurate
  than diffusion); accuracy is set by smoothing in pixels, resolution buys sharpness; folds are
  convexity failures of the discrete OT potential and interpolation error for the flows, they scale
  with ocean compression and live in the seams; the Poisson iteration cannot reach the pure limit.

Open: M3 (pure OT without folds), city labels and rivers, the gallery and the F decisions, everything
from Phase 5 on.

## Defaults I will take unless you object at approval

- F4 method: OT is the default for the artefact; diffusion and jellium stay as comparisons.
- F2 ocean: pure (share 1) is the resting picture once M3 delivers it; the share slider exists for
  readers who want to see where the Atlantic went; 0.95 is the interim default until M3.
- F3 frame: square Web-Mercator cut for the flat picture; the globe has no frame.
- F5 fold gate: the globe renders from the inverse map (single-valued by construction); the gate is
  "zero folds in populated cells, ocean folds below the pixel scale"; M3/M11 aim for zero anywhere.
- F1 growth across time: flat playback keeps the frame full with a people-per-pixel caption; the
  globe grows with radius ~ sqrt(population). Revisited when the first playback exists.
- Money and publication: nothing is spent and nothing is deployed to philippbogdan.com without a
  checkpoint; everything else proceeds.

## The build, in order

```
 Phase 1  foundations        A1 A2 S1 S2 A11 R2 V0            [x]  S4 (F5 default)  S5 [ ]
 Phase 2  optimal transport  M10 [x]  M3 M11 -> pure, no folds     the picture nobody has made
 Phase 3  gravity            M2 M9 [x]  R5 M8                        the G-slider picture
 Phase 4  legibility+gallery A14 A15 R6 R7 R8 R9 X7 X8 R10 X5 X6 S3  pictures explain themselves
 Phase 5  time               D3 D6 D8 D9 T8 T1 T3 L3 L8 T4 T5 T6 T7 R3   10,000 BC to 2100
 Phase 6  globe              A4 D5 A5 A6 A7 A8 A9 A16 (M12 if needed)   sphere area = people
 Phase 7  lenses             L1 D12 L9 L10 L11 L12 L4 L5 L6 L7 L13       any measure, any moment
 Phase 8  geometry (side)    G1 G4 G2 G3/A10 A13                          the curved manifold
 Phase 9  the viewer         A12 V1-V15                                   Apple-Maps grade, last
 Process  PR1 PR2 throughout
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
- M3 `[x]` back-and-forth method implemented (C Legendre transforms, GPU pushforward, Monge-Ampère polish);
  it gives the global convex structure but its discrete map is a staircase where the map compresses and
  the ascent stalls at 4096 pure (21% mass misplaced). Kept as a solver for moderate contrasts; the pure
  route is M10 homotopy. Gate status: ±5% met (±3.5%); populated folds 5.5k of 1.9M, not zero (F5 default applies).
- M11 `[ ]` NEW semi-discrete OT (Laguerre cells): one convex cell per N people, exact areas, no folds;
  a new picture (the power diagram of humanity) and the engine for L7. Mérigot/Lévy code as reference.
- M5 `[ ]` monotone Monge-Ampère finite differences, only if M3 stalls. M4, M6 `[ ]` optional comparisons.
- Gate: MET 2026-08-29 on error; folds gate under F5 default. e025 is the pure OT world at 4096.

### Phase 3: gravity `[~]`

- M2 `[x]` GSM flow (own torch; sign fixed). M9 `[x]` jellium flow at 512, 1024 (e028: -3.5%/+5.7%, 40 folds) and 2048 (e026: -4.3%/+5.5%); 4096 needs a scale-aware step cap.
- R5 `[~]` the G-slider as stills: attractive at t = 0.1 and 0.3 (e027, the anti-cartogram: India and China pinch to points) | Earth | repulsive = M9; the animation waits for the viewer.
- M8 `[x]` Tobler baseline (e029: density error -0.85/+2.45, the trivial answer is in the table).

### Phase 4: legibility and the gallery

- A14 `[x]` NEW city labels: GHS-UCDB urban centres (free, with population), ~300 largest at warped
  positions, unwarped text; sized by population.
- A15 `[x]` NEW rivers through the warp (Natural Earth rivers): Nile, Ganges, Yangtze as lines.
- R7 `[ ]` NEW equipotentials: contour lines of the OT potential, the level sets of population gravity.
- R6 `[x]` NEW stretch map (log area scale as colour) and X8 `[x]` NEW twist map (local rotation angle);
  OT is zero rotation everywhere, diffusion is not.
- R8 `[ ]` NEW flow lines from geography to cartogram. R9 `[x]` NEW ghost coastline under the warped one.
- X7 `[x]` NEW recognisability: per-country shape error after the best similarity transform, and label
  legibility (share of countries whose warped area holds their name).
- X5 `[ ]` seam statistics. R10 `[x]` NEW generated gallery page from INDEX with thumbnails and metrics.
- X6 `[~]` gallery generated (experiments/gallery.html, 33 runs); F2-F4 defaults applied and written; Phil reviews asynchronously.
- S3 `[x]` the default method at 8192: e030, pure (share 0.999), 15 km smoothing, float64 homotopy, ±3.6%, 25k populated folds of 7.6M (0.3%), 65 min; the 100 m texture through it: A12 prototype `[x]` (`src/serve_warped.py`, the cartogram zoomable at 100 m through the inverse map).
- Gate: MET 2026-08-29 (defaults); reopened only if Phil changes an F.

### Phase 5: time, 10,000 BC to 2100

- D3 `[ ]` HYDE 3.4 verified and ingested (epochs, bounds, format). D6 `[ ]` NEW GHS-POP 1975-2030 at 1 km.
- T8 `[ ]` NEW handover: HYDE before 1975, GHS after, one normalisation of totals at the seam.
- T1 `[ ]` every epoch through the default method; population conserved per epoch.
- T3 `[ ]` playback by interpolating the MEASURE between epochs (every frame a true cartogram); log-time scrubbing.
- L3 `[ ]` person-years frame. L8 `[ ]` uncertainty from HYDE bounds. T4 `[ ]` honesty label.
- D8 `[ ]` NEW SSP gridded projections (Jones and O'Neill 2016) and T5 `[ ]` NEW the future to 2100 by scenario.
- D9 `[ ]` NEW Reba historical city points and T7 `[ ]` NEW events on the map through each epoch's warp.
- T6 `[ ]` NEW peak-time lens (epoch of maximum density per pixel). R3 `[ ]` geography-to-cartogram morph.
- (F1) growth display, default as above. Gate: full playback reviewed.

### Phase 6: the globe

- A4 `[ ]` globe renderer: sphere mesh, vertices slide, textures pinned to geography, inverse-map textures.
- D5 `[ ]` overlay data: VIIRS night lights, GRIP4 roads, terrain, AIS shipping, flights.
- A5 `[ ]` overlays through the warp as per-capita maps (night lights nearly uniform as the check).
- A6 `[ ]` labels (countries + A14 cities), ghost graticule, dark base. A16 `[ ]` NEW pole cap treatment.
- A7 `[ ]` time on the globe, growing radius. A8 `[ ]` one control cluster. A9 `[ ]` static hosting (checkpoint).
- M12 `[ ]` NEW sphere-native OT only if the equal-area cylinder shows polar damage (was A3).
- Gate: sphere area = people to Phase 2 tolerance; 60 fps on the M4.

### Phase 7: lenses

- L1 `[ ]` the grammar in the pipeline. D12 `[ ]` NEW measure catalogue ingested (GDP: Kummu/DOSE; lights;
  carbon: EDGAR/ODIAC; cropland: HYDE/GAEZ; travel time: Weiss 2018; attention; age: WorldPop; biomass).
- L9 `[ ]` NEW ratio family (people/lights, people/cropland, people/CO2, people/roads).
- L10 `[ ]` NEW age lens (median age; under-15s as the next generation). L11 `[ ]` NEW attention lens.
- L12 `[ ]` NEW the non-human world (Earth by trees, cropland, protected land) as the complement.
- L4 `[ ]` measure-to-measure OT morph. L5 `[ ]` humeter ruler and geodesics. L6 `[ ]` loneliness metric.
- L7 `[ ]` one person per pixel (via M11). L13 `[ ]` NEW cumulative person-years as a slider.
- Gate: at least three lenses live with sources and honesty notes.

### Phase 8: geometry (side)

- G1 curvature metric, G4 curvature as colour, G2 geodesic graticule, G3/A10 lumpy Earth, A13 3D print. All `[ ]`.

### Phase 9: the viewer, last

- A12 `[~]` on-the-fly warped tiles exist (prototype); the pyramid / static form is Phase 9.
- V1-V11 `[ ]` as in v1 (zoom/pan/rotate, LOD by local magnification, flat + globe, time, lens, method,
  labels with collision, metric grid toggle, native textures, static hosting, asset budget).
- V12 `[ ]` NEW permalinks. V13 `[ ]` NEW compare/swipe. V14 `[ ]` NEW story mode. V15 `[ ]` NEW print export.

### Process, throughout

- PR1 `[x]` NEW golden regression: the world at 512 with fixed knobs, metrics within tolerance, run before commits
  (synthetic tests exist in `tests/synthetic.py`).
- PR2 `[ ]` NEW honesty labels per layer on every artefact: observed / modelled / projected, with the source.
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
 D3 HYDE 3.4 [ ]  D6 GHS 1975-2030 [ ]  D8 SSP 2100 [ ]  D9 Reba cities [ ]  ├── P2 share + smoothing [~]
 D4 Natural Earth [x]  D11 rivers [ ]  D10 GHS-UCDB cities [ ]  D7 BUILT/SMOD [ ]  └── P3 sphere-native [ ]
 D5 lights, roads, terrain, shipping, flights [ ]   D12 lens measures [ ]
                                                 │
                                       grid choice (a parameter) [x]
                                    ┌────────────┴────────────┐
                            Mercator pixels            equal-area cylinder, periodic lon
                            flat rectangle picture     anything shown on a sphere
                                    └────────────┬────────────┘
                       SOLVER INFRASTRUCTURE     │   S1 GPU [x]  S2 4096 [x]  S3 8192 [ ]
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
 ┌─ process, no objective ─────────────┐               G1 curvature metric (2+1 gravity)  [ ]
 │ M1 diffusion  [x]                   │               G2 geodesic graticule (lensing)     [ ]
 │ M2 GSM flow   [x]  ──┐ same Poisson │               G3 3D embedding = A10 lumpy Earth   [ ]
 │ M9 jellium    [x]  ◄─┘              │               G4 curvature as colour              [ ]
 │ M8 Tobler     [ ]                   │                          ▲
 └───────────────┬─────────────────────┘                          │ A11 metric grid [x] ties them
 ┌─ least displacement (OT) ───────────┐   ┌─ least angle distortion ─┐
 │ M10 Poisson iteration [x] (not pure)│   │ M7 quasiconformal [ ]    │
 │ M3 back-and-forth     [ ]  <- next  │   └──────────────────────────┘
 │ M11 semi-discrete     [ ]  NEW      │
 │ M5 monotone FD [ ]  M4 Sinkhorn [ ] │
 │ M6 sliced [ ]   M12 on sphere [ ]   │
 └───────────────┬─────────────────────┘
     R5 G-slider: attractive (+G) ◄── Earth ──► repulsive (-G) = M9   [ ]
                                ▼
 METRICS  X1 area [x]  X2 folds [x]  X3 anisotropy [x]  X4 displacement [x]  X5 seams [ ]
          X6 gallery [ ]  X7 recognisability NEW [ ]  X8 twist NEW [ ]      -> F2 F3 F4 (defaults set)
                                ▼
 RENDER   R1 mesh+coasts+borders+graticule+error [x]  R2 rasters through the warp [x]  R3 morph [ ]
          R4 WebGL mesh [ ]  R6 stretch map NEW [ ]  R7 equipotentials NEW [ ]  R8 flow lines NEW [ ]
          R9 ghost coastline NEW [ ]  R10 gallery page NEW [ ]  countries coloured+labelled [x]
        ┌───────────────────────┼───────────────────────────┐
        ▼                       ▼                           ▼
 FLAT RECTANGLE [x]      GLOBE (Phase 6)                 LUMPY EARTH (A10, A13)
 share knob [x]          A4 renderer  A5 overlays = per-capita  A6 labels  A7 time, growing radius
 pure needs M3           A8 controls  A9 hosting (checkpoint)  A14 cities NEW  A15 rivers NEW  A16 pole cap NEW
                                ▼
 TIMELINE (Phase 5)   T1 epochs  T3 measure interpolation (changed)  T4 honesty  T8 handover NEW
                      T5 future 2100 NEW  T6 peak time NEW  T7 events NEW  L3 person-years  L8 uncertainty  (F1)
                                ▼
 LENSES (Phase 7)     L1 grammar  D12 catalogue  L4 measure morph  L5 humeter ruler+geodesics  L6 loneliness
                      L7 one person per pixel (M11)  L9 ratios NEW  L10 age NEW  L11 attention NEW
                      L12 non-human world NEW  L13 cumulative person-years NEW
                                ▼
 VIEWER (Phase 9)     V0 dev viewer [x]  A12 warped tiles  V1 zoom/pan/rotate  V2 LOD by magnification
                      V3 flat+globe  V4 time  V5 lens  V6 method/G/morph  V7 labels  V8 metric grid
                      V9 native textures  V10 static hosting  V11 asset budget
                      V12 permalinks NEW  V13 compare NEW  V14 story mode NEW  V15 print export NEW
 PROCESS              PR1 golden regression NEW  PR2 honesty labels NEW
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
