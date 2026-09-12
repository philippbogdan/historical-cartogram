# Human atlas: sources and transformations

This bundle was built on 5 September 2026. Its cells describe a population model,
not individually tracked people. Numerical precision in the cell allocation does
not remove uncertainty in the source estimates.

## Population

Schiavina, M., Freire, S., Carioli, A. and MacManus, K. (2023).
[GHS-POP R2023A](https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE).
European Commission, Joint Research Centre.

The atlas uses the 2025 projection for its geometry and the 2015 estimate for its
economic denominator. Counts are re-binned onto a 2,048 by 2,048 grid and divided
into population cells. The display transformation retains ocean space, smooths
the earlier transport mesh and includes a geographical component for legibility.
These are modifications made by this project. See the provider's linked dataset
record for attribution and reuse terms.

## Economic output

Kummu, M., Taka, M. and Guillaume, J. H. A.
[Gridded global datasets for GDP and HDI](https://zenodo.org/records/4972425),
associated with the [2018 methods paper](https://doi.org/10.1038/sdata.2018.4).
The dataset record specifies CC0 1.0.

The input is the 2015 slice of `GDP_PPP_1990_2015_5arcmin_v2.nc`, in constant
2011 international dollars. This gridded GDP product was itself distributed using
HYDE 3.2 population. Our output-per-person lens divides its cell totals by
GHS-POP 2015 population in the same patches. Differences between those population
models can therefore affect local ratios. Values are spatial estimates, not
individual incomes or independent measurements at the displayed cell scale.

## Accumulated person-years

Klein Goldewijk, K. (2023), with contribution by Beusen, A.
[History Database of the Global Environment 3.3](https://doi.org/10.24416/UU01-AEZZIT).
Utrecht University.

The input is the baseline population NetCDF with 126 epochs from 10,000 BC to
2023, identifying the March 2023 run in its metadata. The project integrates
between epochs by the trapezoidal rule, reallocates this measure into its cells,
and compares each cell's share of 2015 output with its share of person-years.
This is a comparison of spatial distributions, not a causal explanation of wealth.

The dataset's DOI record specifies
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The downloaded package also contains older CC BY 3.0 wording. The HYDE-derived
history values distributed in this bundle follow the DOI record's CC BY-NC-SA
4.0 terms, retaining attribution and identifying the transformations above.

## Boundaries and typeface

Boundaries and place information: [Natural Earth](https://www.naturalearthdata.com/),
public-domain cartographic data, transformed by this project.

Chivo: Omnibus-Type, distributed with its [SIL Open Font License](OFL.txt).

## Verification

`source-population-check.json` records integration of the original population
grid through the final cell geometry. `verification.json` records the delivered
asset hashes. The repository's `tests/human_space.test.mjs` checks population
accounting, all rendered triangles over the continuous transformation, compatible
economic years and the delivered asset hashes.

## Interactive Figure 6 (12 September 2026)

The active renderer now uses `paper.json` and `paper-cells.bin`, exported by
`src/build_paper_hero.py` directly from `experiments/M11_power_8192_2048/sites.npz`.
These are the original 8,192 Laguerre cells from `paper/figures/fig6_power.py`,
with 999,998.593833 people per cell and the original square Mercator frame.
The metadata records the source and geometry hashes. The older world, atlas and
population verification assets above remain archived in this bundle; their cell
allocation is not the active Figure 6 drawing.

Push and pull animate the Figure 6 geometry forward and backward through the
existing smoothed `warp.bin` display mesh, using the established momentum timing.
This is an interactive illustration, not a new optimal-transport solve. The mesh's
longitude seam differs from the paper frame by 0.046875 degrees, less than one tenth
of a mesh cell. Polygon edges are subdivided at at most 1/512 of the frame width
before mapping. The reference endpoint is the original, undeformed power diagram.
The coastline uses the same Natural Earth 110m source as Figure 6.

Colours and labels simplify attribution: a site's containing country supplies its
colour, with the nearest country used for the 383 offshore sites. Whole cells take
that colour, including their ocean extensions. Island groups classified by Natural
Earth as open ocean receive a geographic continent for display. This changes no
population masses, sites or cell boundaries. Country colours have a saturation
floor; polygon fills mix their colour with white. No missing-value grey is drawn.
Country names are anchored to a site belonging to that country, with small offsets
to avoid overlaps, prioritised by
site count, and suppressed on collisions; smaller names appear when zooming in.

Polygon fills use a 2048-pixel cell-ID texture on the GPU's continuous deformation
mesh. Black polygon borders use the exported vector vertices, independent of the
texture, so zoom retains sharp lines. The canvas renderer remains a compatibility
fallback when WebGL 2 is unavailable. Dot and label anchors share the same warp.

## Borderless gravity modes (12 September 2026)

The display now projects the original Mercator cells to linear latitude at the
geographic endpoint, using the earlier wide human-space shape for push. The
source Figure 6 cells and population masses are unchanged. Outer frame edges
are omitted, and geometry south of 60 degrees south is not drawn. This removes
the Antarctic coastline; all 8,192 population sites remain inside the visible
latitude range. Fullscreen uses a cover view with pan/zoom, hiding the selectors.

Push retains the existing outward display deformation. Pull is a separate visual
flow exported by `src/build_pull_gravity.py` to `pull.bin`. Equal-population sites
supply an attractive softened inverse-square field on a 256 by 145 density grid.
Gaussian averaging suppresses cell-scale noise. Mobility drops in dense cores,
which lets incoming material gather around core margins. The flow is integrated
with midpoint steps, then its strength is limited to preserve a usable drawing
mesh. This is an illustrative force field, not a new optimal-transport solution.
`gravity.json` records source hashes, softening, integration settings and strength.

Both modes use the same eased playback between geography and the selected field.
Changing push/pull changes the field, independently of playback direction. A
second damped coordinate blends the two fields. Tests check the determinant's
minimum over all convex combinations of geography, push and pull, so both the
animation and changing the gravity mode preserve mesh orientation.


## Labels sized to the current drawing

`label-area.js` measures country footprints in each frame, after the same
deformation and southern cutoff as the renderer. `src/build_label_regions.py`
exports Natural Earth 50m outlines with seam handling, holes and densification
into `label-regions.bin` and a source-hashed sidecar. Land areas are summed by
country and then by continent. Ocean extensions of the Laguerre cells do not
inflate island labels. The footprints are clipped to the current viewport before
measuring, so zooming or panning partly out of view changes the measured area.
Type dimensions scale with the square root of the pixel area, with a fixed
adjustment for long names. Collision priority also follows current area. No fixed
population-count threshold or fixed country/continent font size determines size.
