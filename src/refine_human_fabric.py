"""Calibrate population capacities against source pixels, without raster resampling.

Each source pixel is split along the browser mesh diagonal. Its two triangles
carry half the pixel's population. Within a mesh triangle the display map is
affine, so intersecting its image with a population cell integrates the original
piecewise-constant population exactly, up to floating-point polygon arithmetic.
"""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import shapely
from shapely import STRtree
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from pysdot import PowerDiagram
from pysdot.domain_types import ScaledImage, ConvexPolyhedraAssembly

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/human-space'

def calibrate(P,warp,pos,weights,Q):
    W=P.shape[1];n=warp.shape[0]-1;N=len(pos)
    fingerprint=hashlib.sha256(P.tobytes()+warp.tobytes()+pos.tobytes()).hexdigest()
    cache=WORK/'source_capacities.npz';report_path=WORK/'source_capacities.json'
    if cache.exists() and report_path.exists():
        saved=np.load(cache);report=json.loads(report_path.read_text())
        if report['input_sha256']==fingerprint:
            return saved['weights'],saved['masses'],report
    t0=time.monotonic()
    def log(*a):print('Source integration:',*a,f'({time.monotonic()-t0:.1f}s)',flush=True)
    def forward(points):
        p=np.clip(points*n/W,0,n-1e-8);ij=np.floor(p).astype(int);f=p-ij
        a=warp[ij[:,1],ij[:,0]];b=warp[ij[:,1],ij[:,0]+1];c=warp[ij[:,1]+1,ij[:,0]+1];d=warp[ij[:,1]+1,ij[:,0]]
        x,y=f[:,0,None],f[:,1,None]
        return np.where(x>=y,a*(1-x)+b*(x-y)+c*y,a*(1-y)+c*x+d*(y-x))*W
    rows,cols=np.nonzero(P>0)
    a=forward(np.stack([cols,rows],1));b=forward(np.stack([cols+1,rows],1))
    c=forward(np.stack([cols+1,rows+1],1));d=forward(np.stack([cols,rows+1],1))
    coords=np.concatenate([np.stack([a,b,c],1),np.stack([a,c,d],1)])
    pieces=shapely.polygons(coords);areas=shapely.area(pieces)
    assert (areas>0).all()
    density=np.tile(P[rows,cols]/2,2)/areas
    tree=STRtree(pieces)
    log('Indexed',len(pieces),'source triangles')
    box=ConvexPolyhedraAssembly();box.add_box([0,0],[W,W])
    geometric=PowerDiagram(positions=pos,weights=weights,domain=box)
    approx_density=np.maximum(Q,Q.mean()*1e-6)*(Q.shape[0]/W)**2
    approx=PowerDiagram(positions=pos,weights=weights,domain=ScaledImage([0,0],[W,W],approx_density))
    def integrate(w):
        geometric.set_weights(w);off,xy=geometric.cell_polyhedra()
        masses=np.zeros(N)
        for i,(start,end) in enumerate(zip(off[:-1],off[1:])):
            cell=shapely.Polygon(xy[start:end])
            selected=tree.query(cell,predicate='intersects')
            overlaps=shapely.area(shapely.intersection(pieces[selected],cell))
            masses[i]=np.dot(overlaps,density[selected])
        assert abs(masses.sum()/P.sum()-1)<1e-8, 'Geometric integration must conserve the source population'
        return masses
    target=P.sum()/N
    masses=integrate(weights)
    log('Initial population range',float(masses.min()),float(masses.max()))
    iterations=0
    while np.max(abs(masses-target))>50:
        if iterations>=25:raise RuntimeError('Source population capacities did not converge')
        approx.set_weights(weights);der=approx.der_integrals_wrt_weights(stop_if_void=True)
        assert not der.error
        A=csr_matrix((der.m_values,der.m_columns,der.m_offsets),shape=(N,N))
        residual=masses-target;dw=np.zeros(N);dw[1:]=spsolve(A[1:,1:],residual[1:])
        assert np.isfinite(dw).all()
        error=np.linalg.norm(residual);step=1.
        for back in range(20):
            trial=weights-step*dw
            candidate=integrate(trial)
            if candidate.min()>0 and np.linalg.norm(candidate-target)<error:
                weights=trial;masses=candidate;break
            step*=.5
        else:raise RuntimeError('No source-mass descent')
        iterations+=1;log('Iteration',iterations,'max population error',float(np.max(abs(masses-target))))
    report={'method':'Exact intersection of transported source-pixel triangles with population cells',
            'input_sha256':fingerprint,'source_pixels':len(rows),'source_triangles':len(pieces),
            'source_population':float(P.sum()),'integrated_population':float(masses.sum()),
            'population_min':float(masses.min()),'population_max':float(masses.max()),
            'max_relative_capacity_error':float(np.max(abs(masses/target-1))),
            'iterations':iterations,'seconds':time.monotonic()-t0}
    np.savez_compressed(cache,weights=weights,masses=masses)
    report_path.write_text(json.dumps(report,indent=2))
    log('Capacities verified against original population')
    return weights,masses,report

if __name__=='__main__':
    P=np.load(WORK/'cells.npz')['P']
    z=np.load(WORK/'balanced_cells_fine.npz')
    warp=np.fromfile(ROOT/'site/human-space/warp.bin','<f4').reshape(513,513,2).astype(float)
    Q=np.load(WORK/'pushed_measures_fine.npz')['population']
    weights,masses,report=calibrate(P,warp,z['pos'],z['weights'],Q)
    np.savez_compressed(WORK/'balanced_cells_fine.npz',pos=z['pos'],weights=weights)
    print(json.dumps(report),flush=True)
