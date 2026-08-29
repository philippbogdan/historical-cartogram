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
