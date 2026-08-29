"""Shared GPU helpers: spectral Poisson solve with the domain's boundary rules, and continuous
mass deposition through a warped corner mesh (quad splat). torch on MPS when available."""
import numpy as np
import torch


def device():
    return torch.device("mps" if torch.backends.mps.is_available() else "cpu")


class Spectral:
    """Neumann walls in y (mirror extension), periodic or mirrored x. Solves -lap(u) = f, zero mean."""

    def __init__(self, H, W, x_boundary="periodic", dev=None):
        self.H, self.W, self.x_boundary = H, W, x_boundary
        self.dev = dev or device()
        self.ext_shape = (2 * H, W if x_boundary == "periodic" else 2 * W)
        ky = 2 * np.pi * np.fft.fftfreq(self.ext_shape[0])
        kx = 2 * np.pi * np.fft.rfftfreq(self.ext_shape[1])
        self.k2 = torch.tensor(ky[:, None] ** 2 + kx[None, :] ** 2, dtype=torch.float32, device=self.dev)

    def ext(self, a):
        e = torch.cat([a, a.flip(0)], 0)
        return torch.cat([e, e.flip(1)], 1) if self.x_boundary == "wall" else e

    def inv_neg_laplacian(self, f, smooth_px=0.0):
        S = torch.fft.rfft2(self.ext(f - f.mean()))
        if smooth_px > 0:
            S = S * torch.exp(-self.k2 * smooth_px ** 2 / 2)
        S = torch.where(self.k2 > 0, S / torch.clamp(self.k2, min=1e-30), torch.zeros_like(S))
        return torch.fft.irfft2(S, s=self.ext_shape)[:self.H, :self.W]


def quad_areas_t(X, Y):
    x0, x1, x2, x3 = X[:-1, :-1], X[:-1, 1:], X[1:, 1:], X[1:, :-1]
    y0, y1, y2, y3 = Y[:-1, :-1], Y[:-1, 1:], Y[1:, 1:], Y[1:, :-1]
    return 0.5 * ((x0 * y1 - x1 * y0) + (x1 * y2 - x2 * y1) + (x2 * y3 - x3 * y2) + (x3 * y0 - x0 * y3))


def deposit(mass, X, Y, periodic=True, ss=2.0, kmax=12):
    """Splat per-cell `mass` (H, W) through the closed corner mesh X, Y ((H+1), (W+1)) onto the
    (H, W) grid; big cells are supersampled ~ss samples per output pixel per axis."""
    H, W = mass.shape
    A = quad_areas_t(X, Y).abs()
    k = torch.clamp(torch.ceil(ss * torch.sqrt(A)), 1, kmax).to(torch.int64)
    acc = torch.zeros(H * W, device=mass.device)
    for kk in torch.unique(k).tolist():
        ii, jj = torch.nonzero(k == kk, as_tuple=True)
        x00, x01, x10, x11 = X[ii, jj], X[ii, jj + 1], X[ii + 1, jj], X[ii + 1, jj + 1]
        y00, y01, y10, y11 = Y[ii, jj], Y[ii, jj + 1], Y[ii + 1, jj], Y[ii + 1, jj + 1]
        m = mass[ii, jj] / (kk * kk)
        for a in range(kk):
            for b in range(kk):
                u, v = (a + 0.5) / kk, (b + 0.5) / kk
                x = (1 - u) * (1 - v) * x00 + u * (1 - v) * x01 + (1 - u) * v * x10 + u * v * x11
                y = (1 - u) * (1 - v) * y00 + u * (1 - v) * y10 + (1 - u) * v * y01 + u * v * y11 if False else (1 - u) * (1 - v) * y00 + u * (1 - v) * y01 + (1 - u) * v * y10 + u * v * y11
                px = torch.floor(x).to(torch.int64)
                px = px % W if periodic else px.clamp(0, W - 1)
                py = torch.floor(y).to(torch.int64).clamp(0, H - 1)
                acc.index_put_((py * W + px,), m, accumulate=True)
    return acc.reshape(H, W)


def corner_mesh_from_potential(psi_grad_sign, psi, periodic=True):
    """Map T(x) = x + sign * grad(psi)(x) evaluated at cell corners; psi lives on cell centres.
    Returns closed X, Y ((H+1), (W+1)) tensors."""
    H, W = psi.shape
    p = torch.cat([psi[:1], psi, psi[-1:]], 0)
    p = torch.cat([p[:, -1:], p, p[:, :1]], 1) if periodic else torch.cat([p[:, :1], p, p[:, -1:]], 1)
    cols = W + 1
    a, b = p[0:H + 1, 0:cols], p[0:H + 1, 1:cols + 1]
    d, e = p[1:H + 2, 0:cols], p[1:H + 2, 1:cols + 1]
    gx = ((b - a) + (e - d)) / 2
    gy = ((d - a) + (e - b)) / 2
    ys, xs = torch.meshgrid(torch.arange(H + 1, device=psi.device, dtype=psi.dtype), torch.arange(cols, device=psi.device, dtype=psi.dtype), indexing="ij")
    X = xs + psi_grad_sign * gx
    Y = ys + psi_grad_sign * gy
    if periodic:
        X[:, -1] = X[:, 0] + W
        Y[:, -1] = Y[:, 0]
    else:
        X[:, 0], X[:, -1] = 0.0, float(W)
    Y[0, :], Y[-1, :] = 0.0, float(H)
    return X, Y
