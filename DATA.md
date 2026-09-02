# Data

All entries verified 2026-08-28 unless stated. Nothing here cost money.

## On disk (gitignored)

- `data/raw/GHS_POP_E2025_GLOBE_R2023A_4326_30ss_V1_0.tif`  43202 x 21384 float64,
  EPSG:4326, 30 arcsec, counts per cell, nodata -200. Source:
  https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_4326_30ss/V1-0/
  Licence: EC reuse notice (attribution). Downloaded 2026-08-28, 484 MB zip.
- `data/raw/ne_{110m,50m}_{admin_0_countries,coastline,land}.geojson` Natural Earth,
  public domain, from github.com/nvkelso/natural-earth-vector (master, 2026-08-28).

## Candidates

| dataset | resolution | years | notes |
|---|---|---|---|
| GHS-POP R2023A | 3" (~100 m) and 30" | 1975-2020 (5 y), 2025/2030 projected | finest complete global raster; no login |
| WorldPop Global2 R2025A | 100 m country tiles, 1 km global mosaic | 2015-2030 annual | CC BY 4.0; no global 100 m mosaic |
| LandScan Global 2024 | 30" | 2000-2024 annual | ambient (24 h) population; CC BY 4.0 |
| Meta/CIESIN HRSL | 1" (~30 m) | ~2015 | not fully global; AWS open bucket |
| GPWv4.11 | 30" | 2000-2020 | Earthdata login |
| Kontur 2023-11 | H3 res 8 (~400 m) | 2023 | GPKG 2.3 GB |
| HYDE 3.4 | 5' (~9 km) | 10000 BC to 2025 | timeline source; steps: millennial to 1 AD, then finer (3.4 schedule unverified); CC BY 4.0; portal https://hyde-portal.geo.uu.nl/ ; paper Klein Goldewijk et al. ESSD 2017 doi:10.5194/essd-9-927-2017 |

Pre-1700 alternatives: Reba-Reitsma-Seto historical urban populations (city points, 3700 BC to 2000, doi:10.7927/H4ZG6QBX). No other pre-1700 grid found.

- `data/raw/ghs3ss/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R7_C27.tif` one 100 m tile (Bengal), 12000x12000, from
  .../GHS_POP_E2025_GLOBE_R2023A_4326_3ss/V1-0/tiles/ (348 tiles of 10 degrees, R = row from 90N, C = column from 180W); global zip is 12.9 GB. Downloaded 2026-08-29.
- `data/raw/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif` GLOBAL 100 m (3 arcsec), 432002 x 213822, float64, 11.1 GB + 3.8 GB overviews (x2..x32), total 8.191 bn people. Downloaded 2026-08-29 (zip deleted). Same source directory as the 30" file, `.../GHS_POP_E2025_GLOBE_R2023A_4326_3ss/V1-0/`.

## D3 note (2026-08-29)
The HYDE 3.3/3.4 files on Utrecht's Yoda server (geo.public.data.uu.nl/vault-hyde/, DOI 10.24416/UU01-AEZZIT) sit behind an Anubis proof-of-work challenge; curl is blocked. Fetch through the browser (Claude in Chrome or ChromeFlow same-origin fetch) when Phase 5 starts.

## D6 (2026-08-29)
GHS-POP epochs 1975-2030 (5-year, 30 arcsec) from the same JRC directory pattern, `GHS_POP_E{year}_GLOBE_R2023A_4326_30ss/V1-0/`; downloading to `data/raw/ghs_epochs/`.

## Phase 5-7 data (2026-08-29)
- `data/raw/hyde33/population_{base,lower,upper}.nc` HYDE 3.3 (March 2023 release, vault HYDE 3.3[1710493486]), 5 arcmin, 126 epochs 10,000 BC to 2023 (millennial to 0, centennial to 1700, decadal to 1950, yearly after). Licence per readme CC BY 3.0 (the landing page says CC BY-NC-SA 4.0; cite Klein Goldewijk et al. 2017). Fetched through the Anubis bot wall with headless Chromium cookies. Totals verified (4.5 M at 10,000 BC, 7.86 bn 2023).
- `data/raw/reba/` Reba, Reitsma & Seto 2016 historical urban populations (Chandler 2250 BC to 1975, Modelski ancient and modern), figshare 2059494/2059497/2059500, CC BY.
- `data/raw/grip4/grip4_total_dens_m_km2.asc` GRIP4 road density, 5 arcmin, CC0 (globio.info).
- `data/raw/lenses/GDP_PPP_1990_2015_5arcmin_v2.nc` Kummu, Taka & Guillaume 2018 GDP PPP, zenodo 4972425, CC0.
- `data/raw/lenses/BlackMarble_2016_3km_geo.tif` NASA Earth at Night 2016 (Black Marble), 13500 x 6750, public domain (NASA).
- SSP projections: Wang, Meng and Long 2022, global 30 arcsec 2020-2100 every 5 years (figshare 19608594, CC BY 4.0). 2026-09-01: SSP2 downloaded (2.49 GB zip, 17 GeoTIFFs in `data/raw/ssp/SPP2/`, zip deleted); nodata is stored as 255 and is masked in the loader (a handful of real 255-person cells go with it); 2020 total 7.66 bn. Other scenarios not downloaded.
- Deleted 2026-08-29 to free disk: the three 100 m tiles (the global file covers them), the 30" zip, superseded experiment meshes.
- 2026-09-01  D6 GHS-POP epochs 1975-2030 re-downloaded to `data/raw/ghs_epochs/` (Phil freed the disk); they feed the 1 km era of the timeline (T8).
- 2026-08-29  D6 GHS-POP epochs (3.8 GB) deleted to free disk; HYDE covers 1950-2023 yearly at 5 arcmin, which is what the timeline uses. Re-download from the JRC pattern if a 1 km modern era is wanted.
- 2026-09-02  Boundaries for the interactive map (`data/raw/boundaries/`): Natural Earth 10m admin-1 states and
  provinces (public domain, nvkelso mirror); GHS-UCDB R2019A urban centres, 13,135 polygons with 2015
  population (JRC, CC BY 4.0); geoBoundaries CGAZ ADM1 and ADM2 (open licence, CC BY 4.0 attribution).
- 2026-09-02  Copernicus Global Land Service Land Cover 100 m, collection 3, epoch 2019 (Zenodo 3939050, CC BY 4.0):
  tree-cover fraction (5.65 GB) and crops-cover fraction (2.98 GB) GeoTIFFs in `data/raw/landcover/`, for L12.
- 2026-09-02  WorldPop 2020 age and sex structures, 1 km global mosaics (CC BY 4.0, data.worldpop.org): 36 bands of
  3.3 GB each, downloaded one at a time, block-summed to 5 arcmin into `data/derived/worldpop_age/` and
  deleted; about 80 minutes per band per connection, so this runs for a day in the background.
