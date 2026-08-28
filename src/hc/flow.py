"""Potential flows: population as mass.

M2  GSMFlow     Gastner-Seguy-More 2018: one Poisson solve of the density contrast,
                rho_t = (1-t) rho0 + t, v = -grad(Phi)/rho_t, t in [0, 1]. Exact mass
                conservation by construction.
M9  JelliumFlow the anti-gravity gradient flow: v = +grad(Phi_t) with lap(Phi_t) = rho_t - 1
                recomputed from the CURRENT density each step (a particle-mesh code with
                the sign of gravity flipped and a neutralising background). Runs until the
                density is uniform. The G-slider (R5) is this flow with the sign and time as knobs.
"""
import numpy as np
from .diffusion import TorchDiffusionCartogram


def quad_areas_t(X, Y):
    x0, x1, x2, x3 = X[:-1, :-1], X[:-1, 1:], X[1:, 1:], X[1:, :-1]
    y0, y1, y2, y3 = Y[:-1, :-1], Y[:-1, 1:], Y[1:, 1:], Y[1:, :-1]
    return 0.5 * ((x0 * y1 - x1 * y0) + (x1 * y2 - x2 * y1) + (x2 * y3 - x3 * y2) + (x3 * y0 - x0 * y3))


class GSMFlow(TorchDiffusionCartogram):
    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic", device=None):
        super().__init__(counts, floor, sigma, x_boundary, device)
        T = self.torch
        self.rho = T.tensor(self.rho0, dtype=T.float32, device=self.dev)
        phi = self.solve_poisson(self.rho - 1)
        self.gx, self.gy = self._grad(phi)

    def velocity(self, t):
        rho_t = (1 - t) * self.rho + t
        return self._pad_velocity(self.gx / rho_t, self.gy / rho_t), rho_t  # lap(Phi) = rho0 - 1, so +grad(Phi) flows out of overdensities

    def run(self, log=print, **kw):
        kw = {k: v for k, v in kw.items() if k in ("max_disp", "growth")}
        pts, info = self.advect(self.corner_mesh(), t_start=0.0, dt0=1e-4, t_end=1.0, log=log, **kw)
        X, Y = self.mesh_from_points(pts)
        return X, Y, info


class JelliumFlow(TorchDiffusionCartogram):
    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic", device=None, sign=+1.0, smooth_px=1.0, ss=1.5):
        super().__init__(counts, floor, sigma, x_boundary, device)
        T = self.torch
        self.mass = T.tensor(self.rho0, dtype=T.float32, device=self.dev)  # mean 1: mass per cell
        self.sign = sign
        self.smooth_px = smooth_px
        self.ss = ss
        self.V = None
        self.rho_t = None

    def deposit(self, pts):
        """Splat the cell masses through the warped corner mesh onto the grid (continuous deposition)."""
        T = self.torch
        H, W = self.H, self.W
        cols = W if self.x_boundary == "periodic" else W + 1
        X = pts[:, 0].reshape(H + 1, cols)
        Y = pts[:, 1].reshape(H + 1, cols)
        if self.x_boundary == "periodic":
            X = T.cat([X, X[:, :1] + W], 1)
            Y = T.cat([Y, Y[:, :1]], 1)
        A = quad_areas_t(X, Y).abs()
        k = T.clamp(T.ceil(self.ss * T.sqrt(A)), 1, 12).to(T.int64)
        acc = T.zeros(H * W, device=self.dev)
        for kk in T.unique(k).tolist():
            ii, jj = T.nonzero(k == kk, as_tuple=True)
            x00, x01, x10, x11 = X[ii, jj], X[ii, jj + 1], X[ii + 1, jj], X[ii + 1, jj + 1]
            y00, y01, y10, y11 = Y[ii, jj], Y[ii, jj + 1], Y[ii + 1, jj], Y[ii + 1, jj + 1]
            m = self.mass[ii, jj] / (kk * kk)
            for a in range(kk):
                for b in range(kk):
                    u, v = (a + 0.5) / kk, (b + 0.5) / kk
                    x = (1 - u) * (1 - v) * x00 + u * (1 - v) * x01 + (1 - u) * v * x10 + u * v * x11
                    y = (1 - u) * (1 - v) * y00 + u * (1 - v) * y01 + (1 - u) * v * y10 + u * v * y11
                    px = T.floor(x).to(T.int64)
                    px = px % W if self.x_boundary == "periodic" else px.clamp(0, W - 1)
                    py = T.floor(y).to(T.int64).clamp(0, H - 1)
                    acc.index_put_((py * W + px,), m, accumulate=True)
        return acc.reshape(H, W)

    def begin_step(self, pts):
        rho = self.deposit(pts)
        phi = self.solve_poisson(rho - 1, smooth_px=self.smooth_px)
        gx, gy = self._grad(phi)
        self.V = self._pad_velocity(self.sign * gx, self.sign * gy)
        # the convergence check uses the smoothed density the field actually saw
        T = self.torch
        ext = T.cat([rho, rho.flip(0)], 0)
        if self.x_boundary == "wall":
            ext = T.cat([ext, ext.flip(1)], 1)
        S = T.fft.rfft2(ext) * T.exp(-self.k2 * self.smooth_px ** 2 / 2)
        self.rho_t = T.fft.irfft2(S, s=self.ext_shape)[:self.H, :self.W]
        return True

    def velocity(self, t):
        return self.V, self.rho_t

    def run(self, log=print, tol=1e-2, t_max=30.0, **kw):
        kw = {k: v for k, v in kw.items() if k in ("max_disp", "growth")}
        pts, info = self.advect(self.corner_mesh(), t_start=0.0, dt0=1e-4, tol=tol, t_max=t_max, cap_frac=0.0, log=log, **kw)
        X, Y = self.mesh_from_points(pts)
        return X, Y, info
