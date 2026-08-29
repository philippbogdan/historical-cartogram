"""M3: optimal transport by the back-and-forth method (Jacobs and Leger, 2020).

Dual problem for the quadratic cost: maximise J(phi) = int phi dnu + int phi^c dmu, where
phi^c(x) = inf_y [ |x-y|^2/2 - phi(y) ]. The gradient is nu - T#mu with T(x) = x - grad(phi^c)(x),
taken in the H^1 sense ((-lap)^{-1} of it). "Back and forth" alternates ascent on phi (on the
target) and on psi = phi^c (on the source), each time re-tightening with a c-transform, so every
iterate is c-concave: the map is the gradient of a convex function and cannot fold.

c-transforms are exact discrete Legendre transforms (C, O(N) per row); pushforwards are
continuous depositions through the corner mesh on the GPU; the Poisson preconditioner is spectral.
Cylinder (periodic x) handled by tripling the x range in the transform.
"""
import ctypes, os, time
import numpy as np
import torch

from .diffusion import prepare_density
from .gpu import Spectral, deposit, corner_mesh_from_potential, device

_lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "csrc", "liblft.so"))
_lib.lft_rows.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_double,
                          ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_int)]


def lft_rows(g, y_off, m, p_off):
    """Row-wise Legendre transform: out[r, j] = max_i (p_j y_i - g[r, i]), y_i = i + y_off, p_j = j + p_off."""
    g = np.ascontiguousarray(g, dtype=np.float64)
    rows, n = g.shape
    out = np.empty((rows, m), np.float64)
    arg = np.empty((rows, m), np.int32)
    _lib.lft_rows(g.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), rows, n, y_off, m, p_off,
                  out.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), arg.ctypes.data_as(ctypes.POINTER(ctypes.c_int)))
    return out, arg


def c_transform(phi, periodic_x, out_off=0.5, out_shape=None, with_arg=False):
    """phi^c(x) = inf_y |x-y|^2/2 - phi(y) = |x|^2/2 - (|y|^2/2 - phi)^*(x).

    phi lives on cell centres (y = i + 0.5). Evaluation points x = j + out_off, j < out_shape
    (default: the same centres). With with_arg, also returns the minimising y as (row, col)
    coordinates, sub-pixel refined by one Newton step on the discrete phi."""
    H, W = phi.shape
    Ho, Wo = out_shape or (H, W)
    yy = np.arange(H) + 0.5
    xx = np.arange(W) + 0.5
    xo = np.arange(Wo) + out_off
    yo = np.arange(Ho) + out_off
    g = 0.5 * (yy[:, None] ** 2 + xx[None, :] ** 2) - phi
    if periodic_x:
        xe = np.arange(3 * W) + 0.5 - W
        ge = np.tile(g, (1, 3)) + 0.5 * (xe ** 2 - np.tile(xx, 3) ** 2)[None, :]
        h, ax = lft_rows(ge, 0.5 - W, Wo, out_off)       # (H, Wo): sup over y2 copies, for x2 = xo
        ax = ax - W                                       # index into the extended range -> may be <0 or >=W
    else:
        h, ax = lft_rows(g, 0.5, Wo, out_off)
    k, ay = lft_rows(np.ascontiguousarray(-h.T), 0.5, Ho, out_off)   # (Wo, Ho): sup over y1, for x1 = yo
    phic = 0.5 * (yo[:, None] ** 2 + xo[None, :] ** 2) - k.T
    if not with_arg:
        return phic
    y1 = ay.T                                              # (Ho, Wo): row index of the minimiser
    y2 = ax[y1, np.arange(Wo)[None, :]]                    # (Ho, Wo): col index (unwrapped for periodic)
    # one Newton step per axis on f(y) = |x-y|^2/2 - phi(y) around the discrete minimiser
    pp = np.pad(phi, ((1, 1), (0, 0)), mode="edge")
    pp = np.concatenate([pp[:, -1:], pp, pp[:, :1]], axis=1) if periodic_x else np.pad(pp, ((0, 0), (1, 1)), mode="edge")
    r, c = y1 + 1, (y2 % W) + 1
    d1 = (pp[r + 1, c] - pp[r - 1, c]) / 2; d11 = pp[r + 1, c] - 2 * pp[r, c] + pp[r - 1, c]
    d2 = (pp[r, c + 1] - pp[r, c - 1]) / 2; d22 = pp[r, c + 1] - 2 * pp[r, c] + pp[r, c - 1]
    ys = (y1 + 0.5) - ((y1 + 0.5) - yo[:, None] - d1) / np.maximum(1 - d11, 0.05)
    xs = (y2 + 0.5) - ((y2 + 0.5) - xo[None, :] - d2) / np.maximum(1 - d22, 0.05)
    ys = np.clip(ys, 0, H)
    return phic, ys, xs


class BackForthOT:
    def __init__(self, counts, floor=0.001, sigma=0.0, x_boundary="periodic"):
        assert x_boundary in ("periodic", "wall")
        self.x_boundary = x_boundary
        self.periodic = x_boundary == "periodic"
        self.rho0 = prepare_density(counts, floor, sigma, x_boundary)
        self.H, self.W = self.rho0.shape
        self.dev = device()
        self.mu = torch.tensor(self.rho0, dtype=torch.float32, device=self.dev)
        self.nu = torch.ones_like(self.mu)
        self.spec = Spectral(self.H, self.W, x_boundary, self.dev)

    def _mesh(self, pot):
        """Map x -> x - grad(pot)(x) at corners (pot is a c-concave potential on cell centres)."""
        return corner_mesh_from_potential(-1.0, torch.tensor(pot, dtype=torch.float32, device=self.dev), self.periodic)

    def _push(self, mass, pot):
        X, Y = self._mesh(pot)
        return deposit(mass, X, Y, periodic=self.periodic)

    def _J(self, phi, psi):
        return float((torch.tensor(phi, device=self.dev, dtype=torch.float32) * self.nu).sum() + (torch.tensor(psi, device=self.dev, dtype=torch.float32) * self.mu).sum())

    def _ascend(self, phi0, iters, step_px, patience, log, sigma=None):
        """Back-and-forth ascent from phi0 (None = zero). Leaves self.phi, self.psi, self.best,
        self.iters_done, self.sigma. The step is scaled so the first update from zero moves points by
        step_px at most; from a coarse-level start the coarse step is inherited (same units), and
        the step halves whenever the misplaced mass rises."""
        t0 = time.time()
        phi = np.zeros((self.H, self.W)) if phi0 is None else np.asarray(phi0, np.float64)
        psi = c_transform(phi, self.periodic)
        phi = c_transform(psi, self.periodic)
        Tmu = self._push(self.mu, psi)
        if sigma is None:
            u = self.spec.inv_neg_laplacian(self.nu - Tmu)
            gu = torch.gradient(u)
            sigma = step_px / (float(torch.maximum(gu[0].abs().max(), gu[1].abs().max())) + 1e-12)
        best, best_psi, best_phi, since = 1e9, psi, phi, 0
        err, prev = None, 1e9
        it = -1
        for it in range(iters):
            Tmu = self._push(self.mu, psi)
            err = 0.5 * float((self.nu - Tmu).abs().mean())
            if err > prev:
                sigma *= 0.5
            elif err < prev - 1e-4:
                sigma *= 1.05
            prev = err
            if err < best - 1e-4:
                best, best_psi, best_phi, since = err, psi, phi, 0
            else:
                since += 1
                if since >= patience:
                    break
            u = self.spec.inv_neg_laplacian(self.nu - Tmu).cpu().numpy().astype(np.float64)
            psi = c_transform(phi + sigma * u, self.periodic)
            phi = c_transform(psi, self.periodic)
            Snu = self._push(self.nu, phi)
            u2 = self.spec.inv_neg_laplacian(self.mu - Snu).cpu().numpy().astype(np.float64)
            phi = c_transform(psi + sigma * u2, self.periodic)
            psi = c_transform(phi, self.periodic)
            if it % 5 == 0:
                log(f"  bfm {it} misplaced {err:.4f} {time.time()-t0:.0f}s")
        log(f"  bfm done: {it+1} iterations, misplaced mass {best:.4f}, sigma {sigma:.3g}, {time.time()-t0:.0f}s")
        self.psi, self.phi, self.best, self.iters_done, self.sigma = best_psi, best_phi, best, it + 1, sigma

    def run(self, iters=60, step_px=20.0, polish_iters=300, polish_damping=0.3, patience=12, coarse_to_fine=True, min_width=512, polish_smooth_px=2.0, log=print, **_):
        """Two stages. (1) Back-and-forth ascent on the discrete dual with a fixed H^1 step scaled so
        the first update moves points by step_px at most; every iterate is tightened (double
        c-transform), so the potential is c-concave and the transport structure is global and
        convex. The discrete map is a staircase where the map compresses (the argmin is
        quantised to the grid), so (2) the Monge-Ampere Poisson iteration (M10) polishes it into
        a smooth potential, starting from the BFM solution rather than from the linearisation,
        which is what M10 alone cannot do at the pure limit."""
        from .ot_poisson import TorchPoissonOT
        from scipy import ndimage
        t0 = time.time()
        H, W = self.H, self.W
        phi = None
        sigma = None
        if coarse_to_fine and W > min_width:
            # solve the discrete dual on block-averaged grids first; a potential in px^2 scales x4 per doubling
            f = 1
            levels = []
            while W // (2 * f) >= min_width and (H // (2 * f)) * (2 * f) == H and (W // (2 * f)) * (2 * f) == W:
                f *= 2
                levels.append(f)
            for f in reversed(levels):
                h, w = H // f, W // f
                rho_c = self.rho0.reshape(h, f, w, f).mean(axis=(1, 3))
                sub = BackForthOT.__new__(BackForthOT)
                sub.x_boundary, sub.periodic = self.x_boundary, self.periodic
                sub.rho0 = rho_c / rho_c.mean()
                sub.H, sub.W = h, w
                sub.dev = self.dev
                sub.mu = torch.tensor(sub.rho0, dtype=torch.float32, device=self.dev)
                sub.nu = torch.ones_like(sub.mu)
                sub.spec = Spectral(h, w, self.x_boundary, self.dev)
                log(f"  bfm level {w}x{h}")
                sub._ascend(None if phi is None or phi.shape != (h, w) else phi, iters, step_px, patience, log, sigma=sigma)
                sigma = sub.sigma
                phi = ndimage.zoom(sub.phi, 2, order=1, mode="wrap" if self.periodic else "nearest") * 4
            log(f"  bfm level {W}x{H}")
        self._ascend(phi, iters, step_px, patience, log, sigma=sigma)
        phi, best_psi, best, it = self.phi, self.psi, self.best, self.iters_done
        # stage 2: Monge-Ampere polish from the (lightly smoothed) BFM potential, M10 convention
        # T = x + grad psi. The polish keeps its best iterate; if it cannot beat the smoothed BFM
        # start, the start is what we use.
        self.psi_bfm = best_psi
        start = ndimage.gaussian_filter(-best_psi, polish_smooth_px, mode=("reflect", "wrap" if self.periodic else "reflect")) if polish_smooth_px > 0 else -best_psi
        po = TorchPoissonOT(None, x_boundary=self.x_boundary, rho=self.rho0)
        po.psi = torch.tensor(start, dtype=torch.float32, device=po.dev)
        pinfo = po.iterate(iters=polish_iters, damping=polish_damping, log=log)
        X, Y = po.mesh()
        self.psi = po.psi  # M10 convention, for the equipotential render
        info = {"mode": "bfm+polish", "bfm_iters": it, "bfm_misplaced_mass": best, "polish_residual": pinfo["residual"],
                "polish_cell_folds": pinfo["cell_folds"], "seconds_solve": time.time() - t0}
        return X, Y, info
