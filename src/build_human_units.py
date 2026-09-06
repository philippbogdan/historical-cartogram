"""Rebuild equal-population cells, verifying real people independently of the numerical floor.
Run before build_human_space.py. Intermediate cache is under work/human-space.
"""
import json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import get_lonlat
from hc import prep
from pysdot import OptimalTransport, PowerDiagram
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from pysdot.domain_types import ScaledImage, ConvexPolyhedraAssembly

t = time.monotonic()
root = Path(__file__).resolve().parents[1]
(root / 'work/human-space').mkdir(parents=True, exist_ok=True)
z = np.load(root / 'experiments/M11_power_8192_2048/sites.npz')
grid = prep.Grid('mercator', 2048, lon0=-168)
counts, bounds = get_lonlat(10)
P, dropped = prep.to_grid(counts, bounds, grid)
P = np.maximum(P, 0)
domain = ScaledImage([0, 0], [grid.W, grid.H], P)
pd = PowerDiagram(positions=z['pos'], weights=z['weights'], domain=domain)
m = pd.integrals()
print('real masses', np.percentile(m, [0,1,5,50,95,99,100]), 'total', m.sum(), P.sum(), flush=True)
weights = z['weights'].copy()
for floor in [2e-4, 4e-5, 8e-6, 1e-6]:
    im = np.maximum(P, floor * P.mean())
    eq = PowerDiagram(positions=z['pos'], weights=weights, domain=ScaledImage([0, 0], [grid.W, grid.H], im))
    target = im.sum()/len(m)
    for it in range(80):
        der = eq.der_integrals_wrt_weights(stop_if_void=True)
        assert not der.error
        residual = der.v_values - target
        if np.max(np.abs(residual)) < 0.05: break
        A = csr_matrix((der.m_values, der.m_columns, der.m_offsets), shape=(len(m),len(m)))
        delta = np.zeros(len(m)); delta[1:] = spsolve(A[1:,1:], residual[1:])
        assert np.isfinite(delta).all()
        before = np.linalg.norm(residual)
        step = 1.
        for backtrack in range(30):
            trial = weights - step*delta
            eq.set_weights(trial)
            mass = eq.integrals()
            if mass.min() > target*1e-4 and np.linalg.norm(mass-target) < before:
                weights = trial; break
            step *= .5
        else: raise RuntimeError('line search did not improve')
        if it%5 == 0: print('solve',floor,it,'max error',float(np.max(abs(mass-target))),'step',step,flush=True)
    else: raise RuntimeError('no convergence')
    pd.set_weights(weights)
    print('floor',floor,'corrected real masses', np.percentile(pd.integrals(), [0,50,100]), time.monotonic()-t, flush=True)
box = ConvexPolyhedraAssembly(); box.add_box([0,0],[grid.W,grid.H])
geo = PowerDiagram(positions=z['pos'], weights=weights, domain=box)
offsets, xy = geo.cell_polyhedra()
np.savez_compressed(root / 'work/human-space/cells.npz', offsets=offsets, xy=xy, positions=pd.centroids(), weights=weights, sites=z['pos'], masses=pd.integrals(), P=P, W=grid.W, H=grid.H, lon0=grid.lon0)
print('geometry',len(xy), time.monotonic()-t, flush=True)
