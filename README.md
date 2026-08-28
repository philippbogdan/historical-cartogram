# historical-cartogram

Density-equalising warps of the Mercator rectangle: every pixel of the output holds
the same number of people, the frame stays the same rectangle, and the map is built
from a population raster (coordinate-granular), never from country totals.

Two acts:

1. Pin time at today (GHS-POP 2025) and compare methods: diffusion (Gastner-Newman),
   optimal transport (the picture nobody has published), and the rest.
2. Run the winning method over HYDE's 10,000 BC to 2025 population grids and play
   the result back as a morph.

Persistent files (read these first, they are the state of the project):

- `EXPLORATION.md`   the map of what we try, with status
- `DECISIONS.md`     dated decision log
- `PRIOR_WORK.md`    verified links to what exists already
- `DATA.md`          data sources, resolutions, licences, what is on disk
- `experiments/`     one folder per run: params.json, metrics.json, log.txt, PNGs

Run: `~/.venv/default/bin/python src/run_diffusion.py --name e001 --width 512`
