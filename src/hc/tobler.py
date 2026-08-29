"""M8: Tobler's pseudo-cartogram (1986), the separable baseline. Columns are re-spaced by the
column marginal of the population and rows by the row marginal, independently: exact for a
separable density, a rough approximation otherwise, and it fills the rectangle by construction."""
import numpy as np
from .diffusion import prepare_density


class Tobler:
    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic"):
        self.x_boundary = x_boundary
        self.rho0 = prepare_density(counts, floor, sigma, x_boundary)
        self.H, self.W = self.rho0.shape

    def run(self, log=print, **_):
        H, W = self.H, self.W
        col = self.rho0.sum(axis=0); row = self.rho0.sum(axis=1)
        cx = np.concatenate([[0.0], np.cumsum(col)]) / col.sum() * W   # new x position of each column edge
        cy = np.concatenate([[0.0], np.cumsum(row)]) / row.sum() * H
        X = np.broadcast_to(cx[None, :], (H + 1, W + 1)).copy()
        Y = np.broadcast_to(cy[:, None], (H + 1, W + 1)).copy()
        log(f"  tobler: separable re-spacing, x range {cx.min():.1f}-{cx.max():.1f}")
        return X, Y, {"mode": "tobler"}
