# historical-cartogram: the megaplan

As of 2026-08-28. Every node has an ID; the IDs match `EXPLORATION.md` and are the names we
use in commits, experiment folders and chat. This file says WHAT we want and in what order.
The hows get decided per node and land in `DECISIONS.md` and `notes/`. Approved 2026-08-28; this is the
master plan of the project.

Status legend: `[x]` done, `[~]` in progress, `[ ]` todo, `(F)` a fork that is Phil's call.

## Context

Thesis: places with many people feel full and big; places with few people seem vast but feel
empty and small. Instrument: maps whose area is people, from population rasters (never country
totals), for today, then across 12,000 years, then on a globe, then with any measure as a lens,
and finally in a zoomable, pannable, Apple-Maps-grade viewer.

Unit: the humeter, 1 hm = 1 km at world-average population density (~16 per km²). The Earth has
the same area in hm² as in km². The same construction works for any measure (GDP, light, carbon).

Done so far: repo `~/historical-cartogram` (public), exact count re-binning (P1), diffusion
cartogram (M1) with metrics X1-X4 and render R1, experiments e001-e005 at 512 px, the exploration
graph, verified prior work: no published optimal-transport population cartogram, no gridded
animated timeline, Hennig 2013 the closest static ancestor, GSM 2018 is a Poisson flow in disguise.

## The build, in order

```
 Phase 1  foundations      A1 A2 S1 S2 S4 A11 R2            grid, GPU, 4k, no folds, metric grid
    │
 Phase 2  optimal transport M10 -> M5, M3, (M4, M6)           the picture nobody has made
    │
 Phase 3  gravity           M9, R5, M2, M8                    population as repelling mass
    │
 Phase 4  gallery + choice  X5 X6, knobs, S3, D2  -> (F2)(F3)(F4)   Phil picks the method
    │
 Phase 5  time              D3 T1 L3 T3 L8 T4 R3  -> (F1)     10,000 BC to 2025
    │
 Phase 6  globe             A3? A4 D5 A5 A6 A7 A8 A9          sphere area = people
    │
 Phase 7  lenses            L1 L2 L4 L5 L6 L7                 any measure, any colour, any moment
    │
 Phase 8  geometry (side)   G1 G4 G2 G3/A10 A13               the curved manifold, lumpy Earth
    │
 Phase 9  the viewer        V1-V11, A12                       Apple-Maps grade, last
```

### Phase 1: foundations (Act 1a)

- A1 `[x]` longitude seam closed: the warp is periodic in x so the dateline never tears.
- A2 `[x]` equal-area cylindrical grid as an option next to Mercator pixels; the solver takes the
  grid as a parameter; Mercator stays for the flat picture, equal-area for anything on a sphere.
- S1 `[x]` the solver on the GPU (M4, free) so 4096 is hours and 8192 is feasible.
- S2 `[x]` diffusion at 4096 with smoothing in km that shrinks with resolution (about 30 km).
- S4 `[~]` fold gate: folds must be exactly zero for a run to count; fix resolution or smoothing until they are.
- S5 `[ ]` exact band-limited field evaluation (NUFFT) for the flows, so their folds vanish structurally.
- A11 `[x]` metric grid (100 km ground squares through the warp) and Tissot ellipses on every render.
- R2 `[~]` any raster through the warp: population itself as the first heatmap.
- Gate: a 4096 diffusion run, zero folds, population-weighted density error within ±10%, metric grid visible.

### Phase 2: optimal transport (Act 1b)

- M10 `[x]` Poisson one-shot (the linearised OT map, the gravity intuition) then the Poisson
  iteration that converges to the Monge-Ampère solution; this is our own OT solver.
- M5 `[ ]` the same Monge-Ampère solution by monotone finite differences if M10 stalls on zero-density seams.
- M3 `[ ]` the back-and-forth method: convexity-preserving, so fold-free by construction; now the primary OT route.
- M4 `[ ]` entropic Sinkhorn on the grid, optional, for the blurred-but-smooth comparison.
- M6 `[ ]` sliced OT, optional, to see what vruba was playing with.
- Gate: an OT cartogram at 4096 with the same metrics as diffusion; a side-by-side of the two;
  a written note on how OT behaves at the ocean seams (creases) versus diffusion.

### Phase 3: gravity (Act 1c)

- M9 `[x]` the anti-gravity flow: population as repelling mass with a neutralising background,
  run to convergence; a third cartogram next to diffusion and OT.
- R5 `[ ]` the G-slider as pictures and a short animation: attractive (cities collapse) | Earth | repulsive.
- M2 `[~]` the 2018 flow-based method via its reference implementation, for numbers, not pictures.
- M8 `[ ]` Tobler's separable baseline, so the trivial answer is in the table.
- Gate: three cartograms (M1, OT, M9) of the same input in one table and one gallery row.

### Phase 4: gallery and the choice (Act 1d)

- X5 `[ ]` seam statistics: how each method collapses the ocean.
- X6 `[ ]` the gallery: every method, side by side, with metric grid, judged by eye.
- Knobs swept and rendered: humanity share 1.0 / 0.95 / 0.9 / 0.8 / 0.5 (the floor generalised), frame cut 80 / 85.05, smoothing.
- S3 `[ ]` the chosen method at 8192.
- D2 `[x]` GHS-POP 3" (100 m) on disk globally (11 GB + overviews); the texture for the chosen method's renders.
- (F2) ocean: floor visible or pushed to seams. (F3) frame: square Web-Mercator or wall-map cut.
  (F4) the default method for the artefact. All three decided by Phil from the gallery.
- Gate: F2, F3, F4 answered and written to `DECISIONS.md`.

### Phase 5: time (Act 2)

- D3 `[ ]` HYDE 3.4 verified (download, format, epochs, bounds) and ingested through P1.
- T1 `[ ]` every epoch (about 80) through the chosen method; population conserved per epoch.
- L3 `[ ]` person-years: one frame where area is human life lived, integrated over the span.
- T3 `[ ]` playback: log-time scrubbing, interpolation between epochs (OT displacement interpolation if it looks better).
- L8 `[ ]` HYDE's lower and upper bounds shown as uncertainty on the ancient frames.
- T4 `[ ]` honesty label: pre-1700 is a model, not observation, on the artefact itself.
- R3 `[ ]` the geography-to-cartogram morph for any single epoch.
- (F1) how growth shows: fixed frame with a people-per-pixel caption, growing frame, or growing globe.
- Gate: the full playback reviewed by Phil; F1 answered.

### Phase 6: the globe (Act 3)

- A3 `[ ]` sphere-native solvers only if the equal-area cylinder shows visible polar damage.
- A4 `[ ]` globe renderer: one sphere mesh whose vertices slide along the sphere, textures pinned to geography.
- D5 `[ ]` overlay data: night lights, road density, terrain, shipping density, flights.
- A5 `[ ]` overlays through the same warp, each read as a per-capita map; night lights nearly uniform as the check.
- A6 `[ ]` labels for the largest ~300 cities at warped positions with unwarped text; ghost graticule; dark base.
- A7 `[ ]` time on the globe; growing radius with population if F1 says so.
- A8 `[ ]` one small control cluster; time is the hero.
- A9 `[ ]` static hosting on the existing site, no server, no running cost.
- Gate: sphere area equals people to the Phase 1 tolerance; 60 fps on the M4; deployed.

### Phase 7: lenses (Act 4)

- L1 `[ ]` the grammar in the pipeline: (measure for area, measure for colour, moment) as one object.
- L2 `[ ]` the measure catalogue ingested: GDP (honest subnational sources), night lights, carbon,
  cropland, travel time to cities, attention, under-15s; each with source, resolution, honesty note.
- L4 `[ ]` measure-to-measure morph: people-world to dollar-world; the motion is inequality.
- L5 `[ ]` humeter ruler under the cursor; humeter geodesics (the path of fewest people); a distance table.
- L6 `[ ]` the complement metric 1/rho, the loneliness lens, so both halves of the thesis render.
- L7 `[ ]` one person per pixel: the gigapixel image where fully zoomed every pixel is a person.
- Channel rule: one measure per channel (area, colour, height, label size); at most three at once.
- Gate: at least three lenses live with documented sources.

### Phase 8: geometry, the side branch

- G1 `[ ]` the conformal metric with curvature proportional to density contrast (the 2+1 gravity reading).
- G4 `[ ]` curvature painted as colour: where space bends.
- G2 `[ ]` geodesic graticule: lat/long lines bending around cities like lensing.
- G3 / A10 `[ ]` the lumpy Earth: the population manifold embedded in 3D, India a lobe, oceans creases.
- A13 `[ ]` the lumpy Earth as a 3D print.
- Gate: one picture per node; no gate beyond eyes.

### Phase 9: the viewer, last (Act 5)

- V0 `[x]` dev viewer: local tile server over any GeoTIFF, Leaflet front end (`src/serve_tiles.py`).
- V1 `[ ]` zoom, pan, rotate with inertia and fluid fractional zoom.
- V2 `[ ]` continuous level of detail driven by local magnification: a magnified Dhaka gets finer
  source data than a compressed Siberia at the same screen zoom.
- V3 `[ ]` flat and globe from the same assets.
- V4 `[ ]` time scrubber.  V5 `[ ]` lens switch.  V6 `[ ]` method switch, G-slider, morph.
- V7 `[ ]` labels with collision handling.  V8 `[ ]` metric grid and Tissot toggle.
- V9 `[ ]` native-resolution textures, zoom to city scale anywhere.
- A12 `[ ]` the zoomable warped tile pyramid behind V9.
- V10 `[ ]` static hosting inside free tiers.
- V11 `[ ]` asset budget: warp fields per epoch and tiles sized and listed; any storage or compute
  that would cost money goes to Phil with numbers before it is spent.
- Gate: zoom to city scale anywhere without artefacts; deployed on the site.

## The full graph

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
                            Mercator pixels            equal-area cylinder, periodic lon (A1/A2)
                            flat rectangle picture     anything shown on a sphere
                                    └────────────┬────────────┘
                                                 │
                       SOLVER INFRASTRUCTURE     │   S1 GPU solver [ ]   S2 4096 [ ]   S3 8192 [ ]
                                                 │   S4 fold gate: X2 must be 0 [ ]
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
 │ M2 GSM 2018    v = -grad Phi / rho_t│──┐            G2 geodesic graticule: lines bend around
 │                one Poisson solve [ ]│  │ same          cities like lensing                  [ ]
 │ M9 anti-gravity v = +grad Phi_t     │◄─┘ Poisson    G3 3D embedding of the manifold (= A10) [ ]
 │                jellium, PM code  [ ]│               G4 curvature K as colour: where space
 │ M8 Tobler 1-D baseline           [ ]│                  bends                                [ ]
 └───────────────┬─────────────────────┘                          ▲
                 │                                                │ the metric grid ties them:
 ┌─ least displacement ────────────────┐   ┌─ least angle distortion ─┐   A11 on the flat map it
 │ M10 Poisson one-shot = linearised OT│   │ M7 quasiconformal DEM    │   shows scale and shear;
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
A11 joins the flattenings to the geometry branch; S4/X2 gates the globe; A12 feeds V2 and V9;
F1-F4 are Phil's forks.

## Invariants (every phase)

- Raster in, raster out; polygons draw borders only.
- Counts per pixel, never reprojected densities; no Mercator correction exists as code.
- Zero density never reaches a solver; the floor is a knob relative to the mean.
- Same metrics X1-X6 for every method; X2 (folds) is a gate from Phase 1 on.
- One experiment = one folder with params, metrics, log, pictures; `experiments/INDEX.md` is generated.
- Resolution: no cap; warp, texture and data resolutions are three different things
  (warp 4096 then 8192; textures native 100 m / 500 m; HYDE is 5' and nothing finer exists before 1975).
- Compute on the M4, free; nothing spends silently.
- Persistent files updated in the same commit as the work; no Claude attribution anywhere.

## Data index

| ID | what | source | status |
|---|---|---|---|
| D1 | people today, 30" | GHS-POP R2023A 2025 | `[x]` on disk |
| D2 | people today, 3" (100 m) | GHS-POP R2023A | `[x]` on disk |
| D3 | people through time, 5', with bounds | HYDE 3.4 | `[ ]` Phase 5 |
| D4 | coasts, borders, land | Natural Earth 50m/110m | `[x]` on disk |
| D5 | night lights, roads, terrain, shipping, flights | VIIRS, GRIP4, SRTM/ETOPO, AIS density, OpenSky | `[ ]` Phase 6 |
| L2 | GDP, carbon, cropland, travel time, attention, under-15s | Kummu/DOSE, EDGAR/ODIAC, HYDE/GAEZ, Weiss 2018, GDELT, WorldPop | `[ ]` Phase 7 |

## Node index (everything, one line each)

- D1-D5 data (above). P1 `[x]` exact re-binning. P2 `[~]` floor and smoothing policy. P3 `[ ]` sphere-native prep.
- S1 GPU solver. S2 4096 run. S3 8192 run. S4 fold gate.
- M1 `[x]` diffusion. M2 flow-based reference. M3 OT back-and-forth. M4 OT Sinkhorn. M5 OT Monge-Ampère FD.
  M6 sliced OT. M7 quasiconformal (stretch). M8 Tobler baseline. M9 anti-gravity flow. M10 Poisson one-shot and iteration.
- X1 `[x]` area error. X2 `[x]` folds. X3 `[x]` anisotropy. X4 `[x]` displacement. X5 seams. X6 gallery.
- R1 `[x]` warped mesh, coasts, borders, graticule, error map. R2 rasters through the warp. R3 morph. R4 WebGL mesh. R5 G-slider.
- A1 periodic longitude. A2 equal-area grid. A3 sphere-native solvers. A4 globe renderer. A5 overlays as per-capita.
  A6 labels, ghost graticule, dark base. A7 time on the globe, growing radius. A8 controls. A9 static hosting.
  A10 lumpy Earth. A11 metric grid and Tissot. A12 warped tile pyramid. A13 3D print.
- T1 HYDE epochs. T2 growth display (F1). T3 log-time and interpolation. T4 honesty label.
- G1 curvature metric. G2 geodesic graticule. G3 3D embedding. G4 curvature as colour.
- L1 lens grammar. L2 measure catalogue. L3 person-years. L4 measure-to-measure morph. L5 humeter ruler and geodesics.
  L6 loneliness metric. L7 one person per pixel. L8 uncertainty texture.
- V1-V11 viewer (Phase 9).

## Forks that are Phil's

- F1 growth across time: fixed frame + caption / growing frame / growing globe (Phase 5).
- F2 ocean: floor visible or pushed to seams (Phase 4, from the gallery).
- F3 frame: square Web-Mercator cut or wall-map cut (Phase 4, from the gallery).
- F4 the default method for the artefact (Phase 4, from the gallery).

## First moves

1. Copy this file into the repo as `PLAN.md`; link from `README.md` and `CLAUDE.md`; sync the IDs into `EXPLORATION.md`.
2. A1, A2 (grid as a parameter, seam closed).
3. S1 (GPU), then S2 (4096) with S4 (fold gate) and A11 (metric grid) on the render.
4. M10 (Poisson one-shot, then iterated), with M3 as the reference.
5. M9 and R5.
6. X6 gallery, then F2-F4 to Phil.
