"""Gastner-Newman diffusion cartogram (M1) on a cylinder (periodic x, A1) or a box.

rho(t) solves the heat equation; walls are no-flux (Neumann), realised by mirror
extension so a plain FFT diagonalises it; x is periodic unless x_boundary="wall".
Points move with v = -grad(rho)/rho until rho is uniform. Pixel units throughout.
Two backends, one interface: numpy (reference, tests) and torch (S1, MPS GPU).
"""
import time
import numpy as np
from scipy import fft, ndimage


def prepare_density(counts, floor, sigma, x_boundary):
    P = np.asarray(counts, np.float64)
    if sigma > 0:
        P = ndimage.gaussian_filter(P, sigma, mode=("reflect", "wrap" if x_boundary == "periodic" else "reflect"))
    rho = P + floor * P.mean()
    return rho / rho.mean()


class _Base:
    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic"):
        assert x_boundary in ("periodic", "wall")
        self.x_boundary = x_boundary
        self.rho0 = prepare_density(counts, floor, sigma, x_boundary)
        self.H, self.W = self.rho0.shape

    def corner_mesh(self):
        """Corner points (H+1) x W (periodic) or (H+1) x (W+1) (wall), as (N, 2) x,y."""
        cols = self.W if self.x_boundary == "periodic" else self.W + 1
        ys, xs = np.mgrid[0:self.H + 1, 0:cols]
        return np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float64)

    def mesh_from_points(self, pts):
        cols = self.W if self.x_boundary == "periodic" else self.W + 1
        X = pts[:, 0].reshape(self.H + 1, cols)
        Y = pts[:, 1].reshape(self.H + 1, cols)
        if self.x_boundary == "periodic":  # close the cylinder: last column = first + W
            X = np.concatenate([X, X[:, :1] + self.W], axis=1)
            Y = np.concatenate([Y, Y[:, :1]], axis=1)
        return X, Y

    def run(self, log=print, **kw):
        pts, info = self.advect(self.corner_mesh(), log=log, **kw)
        X, Y = self.mesh_from_points(pts)
        return X, Y, info


class DiffusionCartogram(_Base):
    """numpy/scipy backend."""

    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic"):
        super().__init__(counts, floor, sigma, x_boundary)
        H, W = self.H, self.W
        ky = np.pi * np.arange(H) / H
        if x_boundary == "periodic":
            self.coef = fft.rfft(fft.dct(self.rho0, type=2, norm="ortho", axis=0), axis=1)
            kx = 2 * np.pi * np.fft.rfftfreq(W)
        else:
            self.coef = fft.dctn(self.rho0, type=2, norm="ortho")
            kx = np.pi * np.arange(W) / W
        self.k2 = ky[:, None] ** 2 + kx[None, :] ** 2

    def rho_at(self, t):
        c = self.coef * np.exp(-self.k2 * t)
        if self.x_boundary == "periodic":
            return fft.idct(fft.irfft(c, n=self.W, axis=1), type=2, norm="ortho", axis=0)
        return fft.idctn(c, type=2, norm="ortho")

    def velocity(self, t):
        """Padded fields (H+2, W+2); padded index j <-> x = j - 0.5. Returns (Vx, Vy, rho)."""
        rho = self.rho_at(t)
        xm = "wrap" if self.x_boundary == "periodic" else "symmetric"
        p = np.pad(rho, 1, mode="symmetric")
        if self.x_boundary == "periodic":
            p[:, 0] = p[:, -2]
            p[:, -1] = p[:, 1]
        gx = (p[1:-1, 2:] - p[1:-1, :-2]) / 2
        gy = (p[2:, 1:-1] - p[:-2, 1:-1]) / 2
        vx, vy = -gx / rho, -gy / rho
        Vx = np.pad(vx, 1, mode="symmetric")
        Vy = np.pad(vy, 1, mode="symmetric")
        Vy[0, :] *= -1
        Vy[-1, :] *= -1  # normal component antisymmetric across the walls -> zero on them
        if self.x_boundary == "periodic":
            for V in (Vx, Vy):
                V[:, 0] = V[:, -2]
                V[:, -1] = V[:, 1]
        else:
            Vx[:, 0] *= -1
            Vx[:, -1] *= -1
        return Vx, Vy, rho

    def sample(self, V, pts):
        x = pts[:, 0] % self.W if self.x_boundary == "periodic" else pts[:, 0]
        coords = [pts[:, 1] + 0.5, x + 0.5]
        vx = ndimage.map_coordinates(V[0], coords, order=1, mode="nearest")
        vy = ndimage.map_coordinates(V[1], coords, order=1, mode="nearest")
        return np.stack([vx, vy], axis=1)

    def clamp(self, pts):
        if self.x_boundary == "wall":
            pts[:, 0] = np.clip(pts[:, 0], 0, self.W)
        pts[:, 1] = np.clip(pts[:, 1], 0, self.H)
        return pts

    def advect(self, pts, tol=1e-3, dt0=1e-2, max_disp=0.5, growth=1.15, t_max=None, t_start=0.5, cap_frac=0.1, log=print):
        """RK4 in time with step control on the largest displacement per step.

        Starts at t_start (pixel^2): the heat kernel is then one pixel wide, so the
        solver never sees sub-pixel structure where v = -grad(rho)/rho is meaningless.
        The displacement cap grows with the smoothing scale, max(max_disp, cap_frac *
        sqrt(2t)), because at late times the field only varies over sqrt(2t) pixels.
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
            cap = max(max_disp, cap_frac * np.sqrt(2 * t))
            if m > cap:
                dt *= 0.5
                n_rej += 1
                continue
            pts = self.clamp(pts + step)
            t += dt
            V0 = V1
            n_acc += 1
            dt *= growth if m < 0.5 * cap else 1.0
            if n_acc % 100 == 0:
                log(f"  step {n_acc} t={t:.3g} dt={dt:.3g} maxdisp={m:.3f} dev={dev:.4f} {time.time()-t0:.0f}s")
        log(f"  done: {n_acc} steps ({n_rej} rejected), t={t:.4g}, dev={dev:.2e}, {time.time()-t0:.0f}s")
        return pts, {"steps": n_acc, "rejected": n_rej, "t_end": float(t), "final_dev": float(dev)}


class TorchDiffusionCartogram(_Base):
    """torch backend (S1): same maths, FFT with mirror extension, grid_sample interpolation."""

    def __init__(self, counts, floor=0.01, sigma=0.0, x_boundary="periodic", device=None):
        super().__init__(counts, floor, sigma, x_boundary)
        import torch
        self.torch = torch
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dev = torch.device(device)
        H, W = self.H, self.W
        rho = torch.tensor(self.rho0, dtype=torch.float32, device=self.dev)
        ext = torch.cat([rho, rho.flip(0)], dim=0)  # even extension in y -> Neumann
        if x_boundary == "wall":
            ext = torch.cat([ext, ext.flip(1)], dim=1)
        self.ext_shape = tuple(ext.shape)
        self.coef = torch.fft.rfft2(ext)
        ky = 2 * np.pi * np.fft.fftfreq(self.ext_shape[0])
        kx = 2 * np.pi * np.fft.rfftfreq(self.ext_shape[1])
        k2 = ky[:, None] ** 2 + kx[None, :] ** 2
        self.k2 = torch.tensor(k2, dtype=torch.float32, device=self.dev)

    def rho_at(self, t):
        c = self.coef * self.torch.exp(-self.k2 * t)
        return self.torch.fft.irfft2(c, s=self.ext_shape)[:self.H, :self.W]

    def velocity(self, t):
        T = self.torch
        rho = self.rho_at(t)
        H, W = self.H, self.W
        # neighbours with the right boundary rule
        up = T.cat([rho[:1], rho[:-1]], 0)
        down = T.cat([rho[1:], rho[-1:]], 0)
        if self.x_boundary == "periodic":
            left, right = T.roll(rho, 1, 1), T.roll(rho, -1, 1)
        else:
            left = T.cat([rho[:, :1], rho[:, :-1]], 1)
            right = T.cat([rho[:, 1:], rho[:, -1:]], 1)
        vx = -(right - left) / 2 / rho
        vy = -(down - up) / 2 / rho
        # padded (2, H+2, W+2)
        V = T.zeros(2, H + 2, W + 2, device=self.dev)
        V[0, 1:-1, 1:-1] = vx
        V[1, 1:-1, 1:-1] = vy
        V[0, 0, 1:-1], V[0, -1, 1:-1] = vx[0], vx[-1]
        V[1, 0, 1:-1], V[1, -1, 1:-1] = -vy[0], -vy[-1]
        if self.x_boundary == "periodic":
            V[:, :, 0] = V[:, :, -2]
            V[:, :, -1] = V[:, :, 1]
        else:
            V[0, :, 0], V[0, :, -1] = -V[0, :, 1], -V[0, :, -2]
            V[1, :, 0], V[1, :, -1] = V[1, :, 1], V[1, :, -2]
        return V, rho

    def sample(self, V, pts):
        T = self.torch
        x = pts[:, 0] % self.W if self.x_boundary == "periodic" else pts[:, 0]
        gx = (x + 1) / (self.W + 2) * 2 - 1
        gy = (pts[:, 1] + 1) / (self.H + 2) * 2 - 1
        grid = T.stack([gx, gy], dim=1).reshape(1, 1, -1, 2)
        out = T.nn.functional.grid_sample(V[None], grid, mode="bilinear", padding_mode="border", align_corners=False)
        return out[0, :, 0, :].T  # (N, 2)

    def clamp(self, pts):
        if self.x_boundary == "wall":
            pts[:, 0] = pts[:, 0].clamp(0, self.W)
        pts[:, 1] = pts[:, 1].clamp(0, self.H)
        return pts

    def advect(self, pts, tol=1e-3, dt0=1e-2, max_disp=0.5, growth=1.15, t_max=None, t_start=0.5, cap_frac=0.1, log=print):
        T = self.torch
        pts = self.clamp(T.tensor(np.asarray(pts), dtype=T.float32, device=self.dev))
        t, dt, n_acc, n_rej = t_start, dt0, 0, 0
        if t_max is None:
            t_max = -np.log(tol) / (np.pi / max(self.H, self.W)) ** 2 * 4
        V0, rho = self.velocity(t)
        t0 = time.time()
        while True:
            dev = (rho - 1).abs().max().item()
            if dev < tol or t > t_max:
                break
            Vh, _ = self.velocity(t + dt / 2)
            V1, rho1 = self.velocity(t + dt)
            k1 = self.sample(V0, pts)
            k2 = self.sample(Vh, pts + dt / 2 * k1)
            k3 = self.sample(Vh, pts + dt / 2 * k2)
            k4 = self.sample(V1, pts + dt * k3)
            step = dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            m = step.abs().max().item()
            cap = max(max_disp, cap_frac * np.sqrt(2 * t))
            if m > cap:
                dt *= 0.5
                n_rej += 1
                continue
            pts = self.clamp(pts + step)
            t += dt
            V0, rho = V1, rho1
            n_acc += 1
            dt *= growth if m < 0.5 * cap else 1.0
            if n_acc % 100 == 0:
                log(f"  step {n_acc} t={t:.3g} dt={dt:.3g} maxdisp={m:.3f} dev={dev:.4f} {time.time()-t0:.0f}s")
        log(f"  done: {n_acc} steps ({n_rej} rejected), t={t:.4g}, dev={dev:.2e}, {time.time()-t0:.0f}s")
        return pts.cpu().numpy().astype(np.float64), {"steps": n_acc, "rejected": n_rej, "t_end": float(t), "final_dev": float(dev)}


def quad_areas(X, Y):
    """Signed area of each warped cell (shoelace on its four corners)."""
    x0, x1, x2, x3 = X[:-1, :-1], X[:-1, 1:], X[1:, 1:], X[1:, :-1]
    y0, y1, y2, y3 = Y[:-1, :-1], Y[:-1, 1:], Y[1:, 1:], Y[1:, :-1]
    return 0.5 * ((x0 * y1 - x1 * y0) + (x1 * y2 - x2 * y1) + (x2 * y3 - x3 * y2) + (x3 * y0 - x0 * y3))


def _wquant(values, weights, ps):
    order = np.argsort(values)
    cw = np.cumsum(weights[order]) / weights.sum()
    return [float(values[order][min(np.searchsorted(cw, p), len(order) - 1)]) for p in ps]


def equalisation_metrics(rho0, X, Y):
    """X1 area error, X2 folds, X3 anisotropy, X4 displacement, all on the warped corner mesh."""
    A = quad_areas(X, Y)
    ok = A > 0
    folds = int((~ok).sum())
    w = rho0[ok]
    lr = np.log(rho0[ok] / A[ok])
    q05, q50, q95 = _wquant(lr, w, [0.05, 0.5, 0.95])
    dxu = (X[:-1, 1:] - X[:-1, :-1] + X[1:, 1:] - X[1:, :-1]) / 2
    dyu = (Y[:-1, 1:] - Y[:-1, :-1] + Y[1:, 1:] - Y[1:, :-1]) / 2
    dxv = (X[1:, :-1] - X[:-1, :-1] + X[1:, 1:] - X[:-1, 1:]) / 2
    dyv = (Y[1:, :-1] - Y[:-1, :-1] + Y[1:, 1:] - Y[:-1, 1:]) / 2
    a, b, c, d = dxu, dxv, dyu, dyv
    s1 = np.sqrt((a - d) ** 2 + (b + c) ** 2) / 2
    s2 = np.sqrt((a + d) ** 2 + (b - c) ** 2) / 2
    aniso = (s2 + s1) / np.maximum(np.abs(s2 - s1), 1e-12)
    a50, a95 = _wquant(np.log(aniso[ok]), w, [0.5, 0.95])
    ys, xs = np.mgrid[0:X.shape[0], 0:X.shape[1]]
    disp = np.hypot(X - xs, Y - ys)
    return {
        "folds": folds, "gate_folds": "PASS" if folds == 0 else "FAIL",
        "log_ratio_popweighted_p05": q05, "log_ratio_popweighted_p50": q50, "log_ratio_popweighted_p95": q95,
        "log_ratio_min": float(lr.min()), "log_ratio_max": float(lr.max()),
        "anisotropy_popweighted_p50": float(np.exp(a50)), "anisotropy_popweighted_p95": float(np.exp(a95)),
        "displacement_mean_px": float(disp.mean()), "displacement_max_px": float(disp.max()),
    }
