"""Gastner-Newman diffusion cartogram on a rectangle with no-flux boundaries.

rho(t) solves the heat equation with Neumann conditions (DCT-II diagonalises it);
points move with v = -grad(rho)/rho until rho is uniform. The boundary maps to
itself, so the rectangle fills itself. Pixel units throughout.
"""
import time
import numpy as np
from scipy import fft, ndimage


class DiffusionCartogram:
    def __init__(self, counts, floor=0.01, sigma=0.0):
        P = np.asarray(counts, np.float64)
        if sigma > 0:
            P = ndimage.gaussian_filter(P, sigma, mode="reflect")
        rho = P + floor * P.mean()
        rho /= rho.mean()
        self.rho0 = rho
        self.H, self.W = rho.shape
        self.coef = fft.dctn(rho, type=2, norm="ortho")
        ky = np.pi * np.arange(self.H) / self.H
        kx = np.pi * np.arange(self.W) / self.W
        self.k2 = ky[:, None] ** 2 + kx[None, :] ** 2

    def rho_at(self, t):
        return fft.idctn(self.coef * np.exp(-self.k2 * t), type=2, norm="ortho")

    def velocity(self, t):
        """Padded velocity fields (H+2, W+2); index j <-> x = j - 0.5.

        Normal component is antisymmetric across the boundary so it interpolates
        to zero exactly on the boundary; tangential component is symmetric.
        """
        rho = self.rho_at(t)
        p = np.pad(rho, 1, mode="symmetric")
        gx = (p[1:-1, 2:] - p[1:-1, :-2]) / 2
        gy = (p[2:, 1:-1] - p[:-2, 1:-1]) / 2
        vx = -gx / rho
        vy = -gy / rho
        Vx = np.pad(vx, 1, mode="symmetric")
        Vx[:, 0] *= -1
        Vx[:, -1] *= -1
        Vy = np.pad(vy, 1, mode="symmetric")
        Vy[0, :] *= -1
        Vy[-1, :] *= -1
        return Vx, Vy, rho

    @staticmethod
    def sample(V, pts):
        """Bilinear sample of padded fields at pts (N, 2) = (x, y)."""
        coords = [pts[:, 1] + 0.5, pts[:, 0] + 0.5]
        vx = ndimage.map_coordinates(V[0], coords, order=1, mode="nearest")
        vy = ndimage.map_coordinates(V[1], coords, order=1, mode="nearest")
        return np.stack([vx, vy], axis=1)

    def clamp(self, pts):
        pts[:, 0] = np.clip(pts[:, 0], 0, self.W)
        pts[:, 1] = np.clip(pts[:, 1], 0, self.H)
        return pts

    def advect(self, pts, tol=1e-3, dt0=1e-2, max_disp=0.5, growth=1.15, t_max=None, t_start=0.5, log=print):
        """RK4 in time with step control on the largest displacement per step.

        Integration starts at t_start (pixel^2 units): the heat kernel is then at
        least one pixel wide, so the solver never sees sub-pixel structure, where
        v = -grad(rho)/rho is enormous and meaningless. Equivalent to Gaussian
        pre-smoothing with sigma = sqrt(2 t_start).
        """
        pts = self.clamp(np.array(pts, np.float64))
        t, dt, n_acc, n_rej = t_start, dt0, 0, 0
        if t_max is None:
            t_max = -np.log(tol) / (np.pi / max(self.H, self.W)) ** 2 * 4
        V0 = self.velocity(t)
        t0 = time.time()
        while True:
            dev = np.abs(V0[2] - 1).max()
            if dev < tol or t > t_max:
                break
            Vh = self.velocity(t + dt / 2)
            V1 = self.velocity(t + dt)
            k1 = self.sample(V0, pts)
            k2 = self.sample(Vh, pts + dt / 2 * k1)
            k3 = self.sample(Vh, pts + dt / 2 * k2)
            k4 = self.sample(V1, pts + dt * k3)
            step = dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            m = np.abs(step).max()
            if m > max_disp:
                dt *= 0.5
                n_rej += 1
                continue
            pts = self.clamp(pts + step)
            t += dt
            V0 = V1
            n_acc += 1
            dt *= growth if m < 0.5 * max_disp else 1.0
            if n_acc % 50 == 0:
                log(f"  step {n_acc} t={t:.3g} dt={dt:.3g} maxdisp={m:.3f} dev={dev:.4f} {time.time()-t0:.0f}s")
        log(f"  done: {n_acc} steps ({n_rej} rejected), t={t:.4g}, dev={dev:.2e}, {time.time()-t0:.0f}s")
        return pts, {"steps": n_acc, "rejected": n_rej, "t_end": t, "final_dev": float(dev)}

    def corner_mesh(self):
        ys, xs = np.mgrid[0:self.H + 1, 0:self.W + 1]
        return np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float64)

    def run(self, **kw):
        pts, info = self.advect(self.corner_mesh(), **kw)
        X = pts[:, 0].reshape(self.H + 1, self.W + 1)
        Y = pts[:, 1].reshape(self.H + 1, self.W + 1)
        return X, Y, info


def quad_areas(X, Y):
    """Signed area of each warped cell (shoelace on its four corners)."""
    x0, x1, x2, x3 = X[:-1, :-1], X[:-1, 1:], X[1:, 1:], X[1:, :-1]
    y0, y1, y2, y3 = Y[:-1, :-1], Y[:-1, 1:], Y[1:, 1:], Y[1:, :-1]
    return 0.5 * ((x0 * y1 - x1 * y0) + (x1 * y2 - x2 * y1) + (x2 * y3 - x3 * y2) + (x3 * y0 - x0 * y3))


def equalisation_metrics(rho0, X, Y):
    """How uniform the population is after the warp, plus folds and shape stats."""
    A = quad_areas(X, Y)
    folds = int((A <= 0).sum())
    ratio = rho0 / np.maximum(A, 1e-12)  # should be 1 everywhere
    lr = np.log(ratio[A > 0])
    w = rho0[A > 0]  # population-weighted view
    order = np.argsort(lr)
    cw = np.cumsum(w[order]) / w.sum()
    q = lambda p: float(lr[order][np.searchsorted(cw, p)])
    # local Jacobian from corner differences: anisotropy = sigma_max/sigma_min
    dxu = (X[:-1, 1:] - X[:-1, :-1] + X[1:, 1:] - X[1:, :-1]) / 2
    dyu = (Y[:-1, 1:] - Y[:-1, :-1] + Y[1:, 1:] - Y[1:, :-1]) / 2
    dxv = (X[1:, :-1] - X[:-1, :-1] + X[1:, 1:] - X[:-1, 1:]) / 2
    dyv = (Y[1:, :-1] - Y[:-1, :-1] + Y[1:, 1:] - Y[:-1, 1:]) / 2
    a, b, c, d = dxu, dxv, dyu, dyv
    s1 = np.sqrt(((a - d) ** 2 + (b + c) ** 2)) / 2
    s2 = np.sqrt(((a + d) ** 2 + (b - c) ** 2)) / 2
    smax, smin = s2 + s1, np.abs(s2 - s1)
    aniso = smax / np.maximum(smin, 1e-12)
    la = np.log(aniso[A > 0])
    ordera = np.argsort(la)
    cwa = np.cumsum(w[ordera]) / w.sum()
    qa = lambda p: float(np.exp(la[ordera][np.searchsorted(cwa, p)]))
    ys, xs = np.mgrid[0:X.shape[0], 0:X.shape[1]]
    disp = np.hypot(X - xs, Y - ys)
    return {
        "folds": folds,
        "log_ratio_popweighted_p05": q(0.05), "log_ratio_popweighted_p50": q(0.5),
        "log_ratio_popweighted_p95": q(0.95),
        "log_ratio_min": float(lr.min()), "log_ratio_max": float(lr.max()),
        "anisotropy_popweighted_p50": qa(0.5), "anisotropy_popweighted_p95": qa(0.95),
        "displacement_mean_px": float(disp.mean()), "displacement_max_px": float(disp.max()),
    }
