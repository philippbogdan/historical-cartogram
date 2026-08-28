# Experiment index

All diffusion (M1) unless stated. log-ratio = population-weighted log(rho0/area), p05 / p95 (0 = perfect). Anisotropy p50 / p95. Time on the M4.

| run | width | floor | sigma | folds | log-ratio p05/p95 | anisotropy | mean disp px | s |
|---|---|---|---|---|---|---|---|---|
| e001_diffusion_512 | 512 | 0.01 | 0.0 | 413 | -0.81 / +1.80 | 4.7 / 42 | 137 | 64 |
| e002_s1_f01 | 512 | 0.01 | 1.0 | 198 | -0.43 / +0.50 | 4.6 / 39 | 137 | 68 |
| e003_s2_f01 | 512 | 0.01 | 2.0 | 82 | -0.18 / +0.16 | 4.3 / 33 | 137 | 67 |
| e004_s3_f01 | 512 | 0.01 | 3.0 | 50 | -0.10 / +0.07 | 4.1 / 28 | 137 | 67 |
| e005_s2_f05 | 512 | 0.05 | 2.0 | 1 | -0.18 / +0.16 | 4.3 / 34 | 128 | 60 |

Reading: smoothing is what buys accuracy at 512 px (sigma 3 px gives about +-10% density error); floor 5% removes folds at sigma 2; the seams where the ocean collapses are where the remaining error and the folds live (see error.png).
