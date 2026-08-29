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
import os as _os
_W = _os.cpu_count() or 1

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
            return fft.rfft(fft.dct(a, type=2, norm="ortho", axis=0, workers=_W), axis=1)
        return fft.dctn(a, type=2, norm="ortho", workers=_W)

    def _inv(self, c):
        if self.x_boundary == "periodic":
            return fft.idct(fft.irfft(c, n=self.W, axis=1, workers=_W), type=2, norm="ortho", axis=0)
        return fft.idctn(c, type=2, norm="ortho", workers=_W)

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


class TorchPoissonOT:
    """M10 on the GPU (S1): same maths as PoissonOT, FFTs with mirror extension, all tensors on MPS."""

    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic", device=None, rho=None):
        import torch
        self.torch = torch
        assert x_boundary in ("periodic", "wall")
        self.x_boundary = x_boundary
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dev = torch.device(device)
        self.rho0 = prepare_density(counts, floor, sigma, x_boundary) if rho is None else rho
        self.H, self.W = self.rho0.shape
        self.rho = torch.tensor(self.rho0, dtype=torch.float32, device=self.dev)
        self.ext_shape = (2 * self.H, self.W if x_boundary == "periodic" else 2 * self.W)
        ky = 2 * np.pi * np.fft.fftfreq(self.ext_shape[0])
        kx = 2 * np.pi * np.fft.rfftfreq(self.ext_shape[1])
        self.k2 = torch.tensor(ky[:, None] ** 2 + kx[None, :] ** 2, dtype=torch.float32, device=self.dev)
        self.psi = torch.zeros(self.H, self.W, device=self.dev)

    def _ext(self, a):
        T = self.torch
        e = T.cat([a, a.flip(0)], 0)
        return T.cat([e, e.flip(1)], 1) if self.x_boundary == "wall" else e

    def solve_poisson(self, rhs):
        T = self.torch
        S = T.fft.rfft2(self._ext(rhs - rhs.mean()))
        S = T.where(self.k2 > 0, -S / T.clamp(self.k2, min=1e-30), T.zeros_like(S))
        return T.fft.irfft2(S, s=self.ext_shape)[:self.H, :self.W]

    def _pad(self, a):
        T = self.torch
        p = T.cat([a[:1], a, a[-1:]], 0)
        if self.x_boundary == "periodic":
            p = T.cat([p[:, -1:], p, p[:, :1]], 1)
        else:
            p = T.cat([p[:, :1], p, p[:, -1:]], 1)
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
        self.psi = self.solve_poisson(self.rho - 1)
        return self.psi

    def residual(self, psi=None):
        J = self.jacobian_det(self.psi if psi is None else psi)
        return float(((J - self.rho).abs() * self.rho).sum() / self.rho.sum()), int((J <= 0).sum())

    def iterate(self, iters=200, damping=0.5, log=print, tol=1e-3, keep_best=True, patience=5):
        """Damped fixed-point iteration; with keep_best the best-residual iterate is kept and the
        loop stops after `patience` checks without improvement (the iteration can diverge at
        extreme contrasts, e.g. the pure limit at 4096)."""
        T = self.torch
        rho = self.rho
        t0 = time.time()
        res, folds = self.residual()
        best_res, best_psi, since = res, self.psi.clone(), 0
        log(f"  iter start residual {res:.4f} folds {folds}")
        n = -1
        for n in range(iters):
            xx, xy, yy = self.hessian(self.psi)
            rhs = T.sqrt(T.clamp((1 + xx) ** 2 + 2 * xy ** 2 + (1 + yy) ** 2 + 2 * rho, min=0.0)) - 2
            self.psi = (1 - damping) * self.psi + damping * self.solve_poisson(rhs)
            if n % 10 == 0 or n == iters - 1:
                res, folds = self.residual()
                log(f"  iter {n} residual {res:.4f} folds {folds} {time.time()-t0:.0f}s")
                if res < best_res - 1e-4:
                    best_res, best_psi, since = res, self.psi.clone(), 0
                else:
                    since += 1
                    if keep_best and since >= patience:
                        break
                if res < tol:
                    break
        if keep_best:
            self.psi = best_psi
            res, folds = self.residual()
        return {"iters": n + 1, "residual": res, "cell_folds": folds}

    def mesh(self):
        T = self.torch
        H, W = self.H, self.W
        p = self._pad(self.psi)
        cols = W + 1
        a, b = p[0:H + 1, 0:cols], p[0:H + 1, 1:cols + 1]
        d, e = p[1:H + 2, 0:cols], p[1:H + 2, 1:cols + 1]
        gx = ((b - a) + (e - d)) / 2
        gy = ((d - a) + (e - b)) / 2
        ys, xs = np.mgrid[0:H + 1, 0:cols]
        X = xs + gx.cpu().numpy().astype(np.float64)
        Y = ys + gy.cpu().numpy().astype(np.float64)
        if self.x_boundary == "periodic":
            X[:, -1] = X[:, 0] + W
            Y[:, -1] = Y[:, 0]
        else:
            X[:, 0], X[:, -1] = 0.0, W
        Y[0, :], Y[-1, :] = 0.0, H
        return X, Y

    def run(self, iters=200, damping=0.5, one_shot_only=False, coarse_to_fine=True, min_width=512, log=print, **_):
        T = self.torch
        t0 = time.time()
        info = {"mode": "one_shot"}
        if not one_shot_only and coarse_to_fine and self.W > min_width:
            levels = []
            f = 1
            while self.W // (2 * f) >= min_width and (self.H // (2 * f)) * (2 * f) == self.H and (self.W // (2 * f)) * (2 * f) == self.W:
                f *= 2
                levels.append(f)
            psi = None
            for f in reversed(levels):
                h, w = self.H // f, self.W // f
                rho_c = self.rho0.reshape(h, f, w, f).mean(axis=(1, 3))
                sub = TorchPoissonOT(None, x_boundary=self.x_boundary, device=str(self.dev), rho=rho_c / rho_c.mean())
                if psi is None:
                    sub.one_shot()
                else:
                    sub.psi = psi
                log(f"  level {w}x{h}")
                sub.iterate(iters=iters, damping=damping, log=log)
                psi = T.nn.functional.interpolate(sub.psi[None, None], scale_factor=2, mode="bilinear", align_corners=False)[0, 0] * 4
            self.psi = psi
            info = self.iterate(iters=max(iters // 2, 50), damping=damping, log=log)
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


def homotopy(counts, shares, sigma, x_boundary, iters=300, damping=0.3, log=print):
    """Continuation in the humanity share: solve M10 at an easy share, then use its potential as
    the start for the next, harder share (smaller floor). Returns the final solver and per-stage info."""
    from .diffusion import prepare_density
    import torch
    po, psi, stages = None, None, []
    for s in shares:
        floor = (1 - s) / s
        rho = prepare_density(counts, floor, sigma, x_boundary)
        po = TorchPoissonOT(None, x_boundary=x_boundary, rho=rho)
        if psi is None:
            po.one_shot()
            if po.W > 512:
                po.run(iters=iters, damping=damping, coarse_to_fine=True, log=log)  # coarse-to-fine at the first share
                psi = po.psi
        else:
            po.psi = psi
        log(f"  homotopy share {s} (floor {floor:.4g})")
        info = po.iterate(iters=iters, damping=damping, log=log)
        psi = po.psi
        stages.append({"share": s, **info})
    return po, stages
