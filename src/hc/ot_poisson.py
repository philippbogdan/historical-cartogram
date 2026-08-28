"""M10: optimal transport by Poisson iteration.

The Brenier map is T = x + grad(psi) with det(I + D^2 psi) = rho (mean 1). Linearised,
that is Poisson's equation lap(psi) = rho - 1: the "population as repelling mass" one-shot.
Iterating with the 2-D identity (lap phi)^2 = |D^2 phi|^2 + 2 det D^2 phi, phi = |x|^2/2 + psi,
gives Benamou-Froese-Oberman's (2010) explicit method: each step is one Poisson solve
    lap(phi_{n+1}) = sqrt(|D^2 phi_n|^2 + 2 rho),
which converges to the Monge-Ampere solution. Cylinder (periodic x, Neumann y) or box.
"""
import time
import numpy as np
from scipy import fft

from .diffusion import prepare_density, quad_areas


class PoissonOT:
    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic"):
        assert x_boundary in ("periodic", "wall")
        self.x_boundary = x_boundary
        self.rho0 = prepare_density(counts, floor, sigma, x_boundary)
        self.H, self.W = self.rho0.shape
        H, W = self.H, self.W
        ky = np.pi * np.arange(H) / H
        kx = 2 * np.pi * np.fft.rfftfreq(W) if x_boundary == "periodic" else np.pi * np.arange(W) / W
        self.k2 = ky[:, None] ** 2 + kx[None, :] ** 2
        self.k2[0, 0] = np.inf  # the mean is fixed to zero
        self.psi = np.zeros((H, W))

    # spectral helpers
    def _fwd(self, a):
        if self.x_boundary == "periodic":
            return fft.rfft(fft.dct(a, type=2, norm="ortho", axis=0), axis=1)
        return fft.dctn(a, type=2, norm="ortho")

    def _inv(self, c):
        if self.x_boundary == "periodic":
            return fft.idct(fft.irfft(c, n=self.W, axis=1), type=2, norm="ortho", axis=0)
        return fft.idctn(c, type=2, norm="ortho")

    def solve_poisson(self, rhs):
        """lap(psi) = rhs - mean(rhs), zero-mean psi."""
        return self._inv(-self._fwd(rhs - rhs.mean()) / self.k2)

    def _pad(self, a):
        p = np.pad(a, 1, mode="symmetric")
        if self.x_boundary == "periodic":
            p[:, 0] = p[:, -2]
            p[:, -1] = p[:, 1]
        return p

    def hessian(self, psi):
        p = self._pad(psi)
        c = p[1:-1, 1:-1]
        xx = p[1:-1, 2:] - 2 * c + p[1:-1, :-2]
        yy = p[2:, 1:-1] - 2 * c + p[:-2, 1:-1]
        xy = (p[2:, 2:] - p[2:, :-2] - p[:-2, 2:] + p[:-2, :-2]) / 4
        return xx, xy, yy

    def jacobian_det(self, psi):
        xx, xy, yy = self.hessian(psi)
        return (1 + xx) * (1 + yy) - xy ** 2

    def one_shot(self):
        self.psi = self.solve_poisson(self.rho0 - 1)
        return self.psi

    def iterate(self, iters=200, damping=0.5, log=print, tol=1e-3):
        rho = self.rho0
        t0 = time.time()
        hist = []
        for n in range(iters):
            xx, xy, yy = self.hessian(self.psi)
            rhs = np.sqrt(np.maximum((1 + xx) ** 2 + 2 * xy ** 2 + (1 + yy) ** 2 + 2 * rho, 0.0)) - 2
            psi_new = self.solve_poisson(rhs)
            self.psi = (1 - damping) * self.psi + damping * psi_new
            J = self.jacobian_det(self.psi)
            res = float((np.abs(J - rho) * rho).sum() / rho.sum())  # population-weighted |det - rho|
            folds = int((J <= 0).sum())
            hist.append(res)
            if n % 10 == 0 or n == iters - 1:
                log(f"  iter {n} residual {res:.4f} folds {folds} {time.time()-t0:.0f}s")
            if res < tol:
                break
        return {"iters": n + 1, "residual": res, "cell_folds": folds}

    def mesh(self):
        """Corner positions x + grad(psi), gradient averaged from the four neighbouring cells."""
        p = self._pad(self.psi)  # (H+2, W+2); cell (i, j) at p[i+1, j+1]
        H, W = self.H, self.W
        cols = W + 1
        # corner (r, c) touches cells (r-1, c-1), (r-1, c), (r, c-1), (r, c) -> padded rows r, r+1; cols c, c+1
        a = p[0:H + 1, 0:cols]        # cell (r-1, c-1)
        b = p[0:H + 1, 1:cols + 1]    # cell (r-1, c)
        d = p[1:H + 2, 0:cols]        # cell (r, c-1)
        e = p[1:H + 2, 1:cols + 1]    # cell (r, c)
        gx = ((b - a) + (e - d)) / 2
        gy = ((d - a) + (e - b)) / 2
        ys, xs = np.mgrid[0:H + 1, 0:cols]
        X, Y = xs + gx, ys + gy
        if self.x_boundary == "periodic":  # close the cylinder exactly
            X[:, -1] = X[:, 0] + W
            Y[:, -1] = Y[:, 0]
        else:
            X[:, 0], X[:, -1] = 0.0, W
        Y[0, :], Y[-1, :] = 0.0, H
        return X, Y

    def run(self, iters=200, damping=0.5, one_shot_only=False, coarse_to_fine=True, min_width=512, log=print, **_):
        """Coarse-to-fine: solve on block-summed grids from min_width up, upsampling psi
        (x4 per doubling, psi is in px^2) as the next level's initial guess. The Poisson
        iteration is a fixed-point scheme whose convergence slows with grid size, so a
        good initial guess is what makes 4096 affordable."""
        t0 = time.time()
        info = {"mode": "one_shot"}
        if not one_shot_only and coarse_to_fine and self.W > min_width:
            from scipy import ndimage
            levels = []
            f = 1
            while self.W // (2 * f) >= min_width and (self.H // (2 * f)) * (2 * f) == self.H and (self.W // (2 * f)) * (2 * f) == self.W:
                f *= 2
                levels.append(f)
            psi = None
            for f in reversed(levels):
                h, w = self.H // f, self.W // f
                rho_c = self.rho0.reshape(h, f, w, f).mean(axis=(1, 3))
                sub = PoissonOT.__new__(PoissonOT)
                sub.x_boundary = self.x_boundary
                sub.rho0 = rho_c / rho_c.mean()
                sub.H, sub.W = h, w
                ky = np.pi * np.arange(h) / h
                kx = 2 * np.pi * np.fft.rfftfreq(w) if self.x_boundary == "periodic" else np.pi * np.arange(w) / w
                sub.k2 = ky[:, None] ** 2 + kx[None, :] ** 2
                sub.k2[0, 0] = np.inf
                sub.psi = np.zeros((h, w)) if psi is None else psi
                if psi is None:
                    sub.one_shot()
                log(f"  level {w}x{h}")
                sub.iterate(iters=iters, damping=damping, log=log)
                psi = ndimage.zoom(sub.psi, 2, order=1, mode="wrap" if self.x_boundary == "periodic" else "reflect") * 4
            self.psi = psi
            info = self.iterate(iters=max(iters // 4, 50), damping=damping, log=log)
            info["mode"] = "coarse_to_fine"
        elif not one_shot_only:
            self.one_shot()
            info = self.iterate(iters=iters, damping=damping, log=log)
            info["mode"] = "iterated"
        else:
            self.one_shot()
        X, Y = self.mesh()
        info["seconds_solve"] = time.time() - t0
        return X, Y, info
