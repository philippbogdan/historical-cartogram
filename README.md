# The humeter world

A map of the Earth in which **area is people**: every square centimetre of the picture holds the
same number of human beings. Built from the finest complete population raster (GHS-POP, 100 m) by
optimal transport, so nothing rotates and everything moves as little as it can. Land is pure; the
ocean keeps 5% of the frame. The unit of length is the *humeter*: 1 hm is 1 km at the world-average
density, about 16 people per km².

Dense places feel full and big; empty places seem vast but feel empty and small. This is that feeling, drawn.

```
 today      experiments/e033_M10s_4096_wall_share0.999_ocean0.05/map.png     (4096 px, +-2.7%)
 zoomable   site/flat/           static tiles + labels + humeter ruler (Leaflet)
 globe      site/globe/          three.js, sphere area = people, geography <-> cartogram slider
 time       site/time/           HYDE 3.3, GHS-POP and SSP2: 10,000 BC to 2100 (projected), log-time scrubber
 lenses     site/lenses.html     GDP world, loneliness, light and roads per person, peak year, person-years
 geometry   site/geometry.html   curvature, geodesics, humeter distances, the lumpy Earth
 map        site/map/            the interactive map: countries, provinces and cities, districts, four base styles (MapLibre over warped PMTiles)
 globe      site/map/globe.html  the same on MapLibre's globe projection
 story      site/story.html      the hero set: today, the morph, twelve thousand years, wealth against life, trees and cropland, the power diagram
 tour       site/story.html      eight stops; site/compare.html swipes any two worlds
```

Serve the site locally: `cd site && python -m http.server 8768` then open http://localhost:8768/.
The 100 m zoomable cartogram with the full inverse map runs from `src/serve_warped.py <experiment>`;
the 100 m data viewer from `src/serve_tiles.py data/raw/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif`.

## How it is made

```
 population raster (counts per cell) -> exact re-binning onto a Mercator or equal-area cylinder
   -> Gaussian smoothing in km -> land pure + ocean buffer -> spectral optimal-transport solver
   (Monge-Ampere fixed point on the GPU, continuation in the humanity share) -> corner mesh
   -> metrics (area error, folds, anisotropy, twist, shape error) -> renders through the warp
```

Persistent files, read in this order: `PLAN.md` (the goal, phases, node IDs, status), `DECISIONS.md`
(dated decisions and findings), `EXPLORATION.md` (the graph), `PRIOR_WORK.md`, `DATA.md`
(every source, licence, date), `notes/` (the maths), `experiments/INDEX.md` and `experiments/gallery.html`.

One experiment: `python src/run.py --name e0NN --method ot_homotopy --width 2048 --share 0.999 --ocean-share 0.05`
(methods: diffusion, gsm, jellium, gravity, ot_poisson, ot_homotopy, bfm, tobler). The spectral solver
with every share stage saved: `python src/run_homotopy.py <prefix> <width> <sigma_km> 0.95,0.999 400 0.05 -168 wall`.
Timeline: `python src/run_timeline.py 2048 60 0.05 all base`. Tests: `python tests/synthetic.py`, `python tests/regression.py`.

## Honesty

Population: GHS-POP R2023A (JRC), 2025 epoch, census counts disaggregated onto satellite-detected
buildings. History: HYDE 3.3 (Utrecht University), modelled before 1950. Lights: NASA Black Marble
2016. Roads: GRIP4 (CC0). GDP: Kummu et al. 2018 (CC0). Historical cities: Reba, Reitsma and Seto 2016.
Borders, coasts, rivers, places: Natural Earth. Every picture states its source and whether it is
observed, modelled or interpolated.


## Status, 2026-09-03

Sixty-plus of the plan's 84 nodes are done (PLAN.md has the graph with marks). The interactive map runs locally
(`python -m RangeHTTPServer 8768` in `site/`, `src/serve_warped.py` on 8766 for the base textures); the built
tiles (`site/map/tiles*`) are not in git and come from `src/build_map_tiles.py`. The hero renders live under
`experiments/*/hero.png` (local) with 2k JPEGs in git. Nested 100 m city solves (`src/nested_solve.py`) make
the district level true inside the forty largest urban centres. See `notes/paper-2026-09-03.md` for the
prior-art verdict and the paper's claims.
