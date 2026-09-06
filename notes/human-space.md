# H5: the human fabric

The current goal is stated in PRODUCT.md and at the top of PLAN.md. The existing numerical
experiments supply material; their completion reports are not substitutes for checking the
delivered data and the running experience.

## Population and geometry

GHS-POP 2025 counts are re-binned onto the existing 2048 by 2048 wall frame. A conservative
subcell quadrature carries this population through the display map. Capacity-constrained
Laguerre cells divide the resulting measure into approximately one-million-person groups.
Centroidal relaxation chooses compact cell shapes in human space. Their boundaries and centres
are pulled back through the same triangulation to establish the geographic endpoint.

The resampling uses adaptive subpixel quadrature rather than a fixed number of samples. Final
cell capacities are calibrated against the original population: split each source pixel along
the browser mesh diagonal, transport its two triangles, then integrate their intersections with
every population cell. This avoids trusting conservation of the global total as evidence of
correct per-cell counts. `source-population-check.json` records this separate check.

The display map uses the earlier 20% ocean frame, filtered at roughly 120 km at the equator
and blended with 4% geographic coordinates. These are explicit legibility concessions. A
selected cell always refers to the same modelled population allocation; the animation is a
change in representation, not migration.

The browser uses one vertex deformation for the country texture, cell edges and population
dots. All colours are lookups by fixed cell or country IDs. Boundaries remain subnational;
country polygons supply recognisable geography rather than population totals.

## Colour

Output per person is a matched-year comparison: Kummu GDP PPP 2015 divided by GHS-POP 2015,
relative to the global ratio. Units are constant 2011 international dollars per person per year.
The map's area and selectable units still represent the 2025 population.
The source GDP grid was allocated using HYDE 3.2, so division by GHS-POP is a
cross-model spatial estimate. Local differences between those population models
can affect the ratio. The source note states this limitation explicitly.

The history lens is `(cell GDP / world GDP) / (cell person-years / world person-years)`.
Person-years are a trapezoidal integral of HYDE 3.3 population from 10,000 BC to 2023. This is
a comparison between two spatial distributions. It is not accumulated wealth, a biography of
current residents, or evidence that historical population causes current economic output.

## Verification

`node --test tests/human_space.test.mjs` verifies the actual shipped population units, data
hashes and units, matching economic years, and positivity of every rendered triangle for all
transformation values. This is a data gate, not a visual-quality score.

Browser verification must separately exercise forward and reverse motion, scrubbing, a selected
unit, all colour modes, zoom, touch-sized layouts, keyboard controls and reduced motion. A fresh
adversarial agent judges the user contract without reading implementation or expected results.

On 6 September 2026 the final bundle passed that independent visual/interaction review:
recognisable geography, intermediate motion, a more even human-space fabric, a selected cell
through both representations and economic lenses, reversal, and a measured 320 CSS-pixel phone
layout. No blocking clipping or marker overlap remained. This was one reviewer's bounded
inspection, not an exhaustive browser survey or a numerical source audit.

The static publication contains only the new landing page and its own assets. The large research
tile sets and intermediate rasters do not need to be uploaded to serve this experience.

## Build environment

The 5 September build used Python with NumPy 2.4.6, SciPy 1.18.0, rasterio 1.5.1,
matplotlib 3.11.1, Pillow 12.2.0, Shapely 2.1.2, pysdot 0.2.39 and netCDF4 1.7.4,
plus the existing `src/hc` project modules. Rebuilding needs the local source
rasters and the e036/M11 experiment inputs listed in the README; these large
inputs are not part of the static publication.

## Visitor-facing information, 6 September 2026

Selection identifies a place and gives a rounded comparison. Internal cell IDs and solver-level
population precision remain in the data, not the interface. Currency values are available through
optional selection details. The slider has one pair of endpoint labels; source-grid and build
provenance belong in the linked source notes. Cell edges are clipped to land in the fragment
shader, preserving the underlying population partition and motion while clearing empty ocean.

## Repulsive motion, 6 September 2026

Animation timing uses a coarse-grained repulsive field. Each population group supplies equal
positive charge, deposited onto a grid and spatially averaged. The force kernel is
`r / (|r|² + epsilon²)^(3/2)`, approaching an inverse-square magnitude away from the softened
centre. Projecting the sampled force onto the existing atlas displacement gives a collective
pressure curve, averaged across neighbouring transformation states.

The browser exponentially approaches the requested endpoint with a rate driven by that pressure.
A short exponential launch ramp and a lower motion rate give the viewer time to follow the
groups, with a long settling phase and no random particle jitter. It is a
repulsion-driven timing model constrained to the atlas's existing path, not an unconstrained
Coulomb simulation or a new population equilibrium. Reversal is a controlled return along that
same path. Every layer still uses one shared transformation coordinate.

`src/build_human_motion.py` writes `motion.json`, including the source geometry and population
hashes. `tests/human_motion.test.mjs` checks the association with the current atlas, a gentle launch,
settling, bounded reversal and consistency across refresh rates. Reduced motion keeps direct
endpoint changes; manual scrubbing remains immediate and pauses playback.

The launch ramp has a 0.18-second time constant. Expansion reaches its final settled endpoint
in roughly 6.6 seconds and collapse in roughly 4.3 seconds, plus the existing endpoint holds.
