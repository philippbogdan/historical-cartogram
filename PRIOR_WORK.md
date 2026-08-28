# Prior work (verified links)

Checked 2026-08-28 via Parallel Search plus direct fetches. UNVERIFIED items are marked.

## Population cartograms that exist

- Gastner & Newman 2004, diffusion method. https://www.pnas.org/doi/full/10.1073/pnas.0400280101
- Gastner, Seguy & More 2018, fast flow-based. https://www.pnas.org/doi/full/10.1073/pnas.1712674115
  arXiv https://arxiv.org/abs/1802.07625 . Its flow is a Poisson potential of the density contrast, solved once,
  with velocity -grad(Phi)/rho_t along a linear-in-time density (eq. 5); see notes/gravity.md.
  Code: https://github.com/mgastner/cartogram-cpp (C++20, AGPL-3.0). App: https://go-cart.io/
- Worldmapper population cartograms (country-level; years 1, 1500, 1900, 2018):
  https://worldmapper.org/maps/population-year-2018/ (CC BY-NC-SA 4.0)
- Hennig 2009, gridded world population cartogram (static, the closest prior art):
  http://www.viewsoftheworld.net/?p=638
- Dzugan 2020-21, Observable "World Population Cartogram" (method not stated):
  https://observablehq.com/collection/@mattdzugan/world-population-cartogram

## Optimal transport and cartograms

No paper, gallery or repo found that builds a geographic population cartogram with OT.
Nearest:

- Charlie Loyd (vruba), Mastodon 2026-06-17: "Messing with sliced optimal transport
  cartograms again", with an mp4. https://everything.happens.horse/@vruba/116762668933646601
  (verified via the instance API; no write-up found)
- Zhao et al. 2013, "Area-Preservation Mapping using Optimal Mass Transport" (surface
  parameterisation, not geography). https://ieeexplore.ieee.org/document/6634117/

## Other density-equalising methods

- Choi & Rycroft 2018, DEM for simply connected open surfaces. https://doi.org/10.1137/17M1124796
- Lyu, Choi & Lui 2024, bijective density-equalising quasiconformal map. https://doi.org/10.1137/23M1594376 (no public code found)
- Choi group repos (MATLAB, Apache-2.0): spherical-, ellipsoidal-, toroidal-density-equalizing-map under https://github.com/garyptchoi
- Dougenik, Chrisman & Niemeyer 1985 rubber sheet. https://doi.org/10.1111/j.0033-0124.1985.00075.x
- Tobler 1986 pseudo-cartograms. https://doi.org/10.1559/152304086783900194
- Sun 2013 Carto3F. https://doi.org/10.1080/13658816.2012.709247
- Cartogram error metrics (CGF 2015). https://doi.org/10.1111/cgf.12647

## OT solvers with public code (2D grid densities)

- Jacobs & Leger back-and-forth method: https://github.com/Math-Jacobs/bfm (C, Python/MATLAB wrappers)
- Benamou, Froese & Oberman 2014 Monge-Ampere: https://arxiv.org/abs/1208.4870 (no official code;
  https://github.com/gbonnet1/ma-ot-monotone UNVERIFIED)
- Benamou-Brenier dynamic (Papadakis-Peyre-Oudet): https://github.com/gpeyre/2013-SIIMS-ot-splitting (MATLAB)
- Convolutional Wasserstein (Solomon et al. 2015): https://github.com/gpeyre/2015-SIGGRAPH-convolutional-ot
- Semi-discrete: https://github.com/mrgt/MongeAmpere , https://github.com/sd-ot/pysdot , https://github.com/BrunoLevy/geogram
- Entropic: https://github.com/jeanfeydy/geomloss , https://github.com/ott-jax/ott , https://github.com/PythonOT/POT
- Monge-Ampere FEM: https://github.com/ekawecki/Monge--Ampere , https://github.com/METHODS-Group/ProximalGalerkin (example 10)
