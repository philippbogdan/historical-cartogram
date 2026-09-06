"""Coarse-grained Coulomb pressure along the atlas's admissible deformation.

Each equal-population group contributes equal positive charge. Deposit the groups
as a smooth density, convolve with a softened inverse-square force, and project
that force onto the existing geographic-to-human-space displacement. This drives
collective timing; it does not replace the atlas with unconstrained particle paths.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates
from scipy.signal import fftconvolve

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'site/human-space'
world_bytes=(OUT/'world.json').read_bytes();warp_bytes=(OUT/'warp.bin').read_bytes()
world=json.loads(world_bytes);n=world['projection']['meshResolution']
warp=np.frombuffer(warp_bytes,dtype='<f4').reshape(n+1,n+1,2)
uv=np.array([u['uv'] for u in world['units']]);p=np.clip(uv*n,0,n-1e-6)
i=np.floor(p).astype(int);f=p-i;x,y=f[:,0,None],f[:,1,None]
a=warp[i[:,1],i[:,0]];b=warp[i[:,1],i[:,0]+1]
c=warp[i[:,1]+1,i[:,0]+1];d=warp[i[:,1]+1,i[:,0]]
end=np.where(x>=y,a*(1-x)+b*(x-y)+c*y,a*(1-y)+c*x+d*(y-x))*[1,.56]
lat=2*np.arctan(np.exp((.5-uv[:,1])*2*np.pi))-np.pi/2
start=np.stack([uv[:,0],.28-lat/np.pi*.5],axis=1)
displacement=end-start
W,H=256,145;step=1/(W-1);cloud_sigma=1.5;softening=2*step
ky,kx=np.mgrid[-H+1:H,-W+1:W]*step
r3=(kx*kx+ky*ky+softening**2)**1.5
kernels=[kx/r3,ky/r3]
pressures=[]
for t in np.linspace(0,1,65):
    points=(start*(1-t)+end*t)/step
    points=np.clip(points,[0,0],[W-1.000001,H-1.000001]);ij=np.floor(points).astype(int);f=points-ij
    density=np.zeros((H,W))
    for dx,dy,weight in [(0,0,(1-f[:,0])*(1-f[:,1])),(1,0,f[:,0]*(1-f[:,1])),(0,1,(1-f[:,0])*f[:,1]),(1,1,f[:,0]*f[:,1])]:
        np.add.at(density,(ij[:,1]+dy,ij[:,0]+dx),weight/len(points))
    density=gaussian_filter(density,cloud_sigma,mode='constant')
    forces=np.stack([map_coordinates(fftconvolve(density,k,mode='same'),points[:,::-1].T,order=1,mode='nearest') for k in kernels],axis=1)
    pressures.append(float(np.mean(np.sum(forces*displacement,axis=1))))
# Average adjacent states as well as neighbouring population clouds.
pressure=gaussian_filter1d(pressures,1.2,mode='nearest')
assert pressure[0]>0 and np.isfinite(pressure).all()
# Only the outward component supplies expansion pressure. Keep the signed values
# for provenance instead of presenting confinement as free Coulomb dynamics.
positive=np.maximum(pressure,0);normalised=positive/max(positive)
report={'model':'Softened inverse-square repulsion projected onto the atlas deformation',
        'world_sha256':hashlib.sha256(world_bytes).hexdigest(),'warp_sha256':hashlib.sha256(warp_bytes).hexdigest(),
        'groups':len(points),'density_grid':[W,H],'cloud_sigma':cloud_sigma*step,'softening':softening,
        'signed_pressure':pressure.tolist(),'pressure':normalised.tolist()}
(OUT/'motion.json').write_text(json.dumps(report,indent=2)+'\n')
print('Initial/final pressure',pressure[0],pressure[-1], 'range',min(pressure),max(pressure))
print('Normalised samples',normalised[::8])
