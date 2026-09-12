"""A coarse-grained attractive field for the population illustration.

Equal-population sites source a softened inverse-square field. Dense cores have
lower mobility, so incoming material gathers around their rims rather than all
collapsing into point singularities. This is a visual flow, not an OT solution.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.signal import fftconvolve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'site/human-space'
raw = (OUT/'paper.json').read_bytes()
paper = json.loads(raw)
sites = np.array(paper['sites'])

def geography(uv):
    lat = 2*np.arctan(np.exp((.5-uv[..., 1])*2*np.pi))-np.pi/2
    return np.stack((uv[..., 0], .28-lat/np.pi*.5), axis=-1)

W, H = 256, 145
step = 1/(W-1)
source = geography(sites)
p = np.clip(source/step, [0, 0], [W-1.000001, H-1.000001])
ij = np.floor(p).astype(int)
f = p-ij
density = np.zeros((H, W))
for dx, dy, weight in [(0, 0, (1-f[:, 0])*(1-f[:, 1])), (1, 0, f[:, 0]*(1-f[:, 1])),
                       (0, 1, (1-f[:, 0])*f[:, 1]), (1, 1, f[:, 0]*f[:, 1])]:
    np.add.at(density, (ij[:, 1]+dy, ij[:, 0]+dx), weight/len(sites))
density = gaussian_filter(density, 2.0, mode='constant')
ky, kx = np.mgrid[-H+1:H, -W+1:W]*step
denominator = (kx*kx+ky*ky+(2.5*step)**2)**1.5
force = np.stack([-fftconvolve(density, k/denominator, mode='same') for k in (kx, ky)])
sampled_density = map_coordinates(density, p[:, ::-1].T, order=1)
core = float(np.quantile(sampled_density, .65))
mobility = 1/(1+(density/core)**4)
force *= mobility
force = np.stack([gaussian_filter(component, .8) for component in force])
force *= .09/np.max(np.linalg.norm(force, axis=0))

def velocity(points):
    q = (points/step)[..., ::-1].reshape(-1, 2).T
    return np.stack([map_coordinates(component, q, order=1, mode='nearest').reshape(points.shape[:-1])
                     for component in force], axis=-1)

n = 512
y, x = np.mgrid[0:n+1, 0:n+1]/n
base = geography(np.stack((x, y), axis=-1))
positions = base.copy()
dt = .025
for _ in range(100):
    v = velocity(positions)
    positions += dt*velocity(positions+v*dt/2)

# A finite drawing mesh must stay usable through the whole eased interpolation.
def minimum_area(target):
    smallest = np.inf
    def cross(a, b): return a[..., 0]*b[..., 1]-a[..., 1]*b[..., 0]
    for index in (0, 1):
        a=base[:-1, :-1];ta=target[:-1, :-1]
        b=base[:-1, 1:] if index==0 else base[1:, 1:]
        c=base[1:, 1:] if index==0 else base[1:, :-1]
        tb=target[:-1, 1:] if index==0 else target[1:, 1:]
        tc=target[1:, 1:] if index==0 else target[1:, :-1]
        e=b-a;f=c-a;de=tb-ta-e;df=tc-ta-f
        A=cross(de, df);B=cross(de, f)+cross(e, df);C=cross(e, f)
        t=np.clip(-B/np.where(A!=0, 2*A, 1), 0, 1)
        values=np.minimum(C, A+B+C)
        values=np.where(A>0, np.minimum(values, A*t*t+B*t+C), values)
        smallest=min(smallest, float(values.min()))
    return smallest

strength = 1.0
while minimum_area(base+(positions-base)*strength)<1e-10:
    strength *= .95
target = (base+(positions-base)*strength).astype('<f4')
(OUT/'pull.bin').write_bytes(target.tobytes())
report = {'model': 'Attractive softened inverse-square flow with low mobility in dense cores',
          'paper_sha256': hashlib.sha256(raw).hexdigest(),
          'pull_sha256': hashlib.sha256(target.tobytes()).hexdigest(),
          'grid': [W, H], 'mesh_resolution': n, 'steps': 100, 'step_seconds': dt,
          'core_density': core, 'softening': 2.5*step, 'strength': strength,
          'minimum_interpolated_triangle_area': minimum_area(target)}
(OUT/'gravity.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
