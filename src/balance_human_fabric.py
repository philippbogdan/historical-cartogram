"""Construct population cells in human space, then carry their exact identities home.

This chooses the cell shapes in the space where people should look evenly spread.
It avoids stretching geographically round cells into long cartogram streaks.
"""
from pathlib import Path
import json, time
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from pysdot import PowerDiagram
from pysdot.domain_types import ScaledImage, ConvexPolyhedraAssembly
from shapely.geometry import Polygon
from rasterio.features import rasterize
from rasterio.transform import Affine
from PIL import Image
import matplotlib.tri as mtri
import netCDF4
from hc import prep, hyde

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/human-space';OUT=ROOT/'site/human-space';RAW=ROOT/'data/raw'
t0=time.monotonic()
def log(*a):print(*a,f'({time.monotonic()-t0:.1f}s)',flush=True)
old=np.load(WORK/'cells.npz');P=old['P'];W=P.shape[1];N=len(old['masses']);n=512
measure_resolution=4096
measure_scale=(measure_resolution/W)**2
warp=np.fromfile(OUT/'warp.bin',dtype='<f4').reshape(n+1,n+1,2).astype(float)
grid=prep.Grid('mercator',W,lon0=float(old['lon0']))

def forward(uv):
    p=np.clip(np.asarray(uv)*n,0,n-1e-8)
    i=np.floor(p).astype(int);f=p-i
    a=warp[i[:,1],i[:,0]];b=warp[i[:,1],i[:,0]+1];c=warp[i[:,1]+1,i[:,0]+1];d=warp[i[:,1]+1,i[:,0]]
    fx,fy=f[:,0,None],f[:,1,None]
    return np.where(fx>=fy,a*(1-fx)+b*(fx-fy)+c*fy,a*(1-fy)+c*fx+d*(fy-fx))

def push(a):
    """Conservative adaptive quadrature, with at most 2000 people per sample.

    Fixed quadrature undersamples a source pixel containing millions of people.
    Every measure uses the same adaptive geographic sampling pattern.
    """
    R=measure_resolution
    result=np.zeros(R*R)
    need=np.maximum(4,2**np.ceil(np.log2(np.maximum(np.sqrt(P/2000),1)))).astype(int)
    for samples in np.unique(need[a>0]):
        ry,cx=np.nonzero((need==samples)&(a>0))
        sy,sx=np.meshgrid((np.arange(samples)+.5)/samples,(np.arange(samples)+.5)/samples,indexing='ij')
        offsets=np.stack([sx.ravel(),sy.ravel()],1)
        batch=max(1,250000//(samples*samples))
        for r0 in range(0,len(ry),batch):
            rows,cols=ry[r0:r0+batch],cx[r0:r0+batch]
            points=(np.stack([cols,rows],1)[:,None,:]+offsets[None,:,:]).reshape(-1,2)/W
            mass=np.repeat(a[rows,cols]/samples**2,samples*samples)
            q=np.clip(forward(points)*R-.5,0,R-1.000001)
            ij=np.floor(q).astype(int);f=q-ij
            for ox,oy,weight in [(0,0,(1-f[:,0])*(1-f[:,1])),(1,0,f[:,0]*(1-f[:,1])),(0,1,(1-f[:,0])*f[:,1]),(1,1,f[:,0]*f[:,1])]:
                np.add.at(result,(ij[:,1]+oy)*R+ij[:,0]+ox,mass*weight)
    result=result.reshape(R,R)
    assert abs(result.sum()/a.sum()-1)<1e-11
    return result

pushed_path=WORK/'pushed_measures_fine.npz'
if pushed_path.exists():
    pushed=np.load(pushed_path);Q,G,P15,PY=[pushed[k] for k in ['population','gdp','pop2015','history']]
else:
    Q=push(P);log('Population pushed conservatively')
    ds=netCDF4.Dataset(RAW/'lenses/GDP_PPP_1990_2015_5arcmin_v2.nc')
    g=np.maximum(np.nan_to_num(np.ma.filled(ds['GDP_PPP'][-1],0).astype(float)),0)
    if ds['latitude'][0]<ds['latitude'][-1]:g=g[::-1]
    G=push(np.maximum(prep.to_grid(g,(-180,-90,180,90),grid)[0],0));ds.close();log('GDP pushed')
    p15=np.load(ROOT/'data/derived/ghs_2015_lonlat_f10.npz')
    P15=push(np.maximum(prep.to_grid(p15['counts'],p15['bounds'],grid)[0],0));log('Matched population pushed')
    H=hyde.Hyde(str(RAW/'hyde33/population_base.nc'));previous=H.counts(0);acc=np.zeros(previous.shape)
    for i in range(1,len(H.years)):
        current=H.counts(i);acc+=(previous+current)*.5*(H.years[i]-H.years[i-1]);previous=current
    PY=push(np.maximum(prep.to_grid(acc,H.bounds,grid)[0],0));log('History pushed')
    np.savez_compressed(pushed_path,population=Q,gdp=G,pop2015=P15,history=PY)

def balance(pos,weights,density):
    pd=PowerDiagram(positions=pos,weights=weights,domain=ScaledImage([0,0],[W,W],density))
    target=density.sum()/measure_scale/N
    for it in range(100):
        der=pd.der_integrals_wrt_weights(stop_if_void=True)
        if der.error:raise ValueError('Empty starting cell')
        residual=der.v_values-target
        if abs(residual).max()<.1:return pd
        A=csr_matrix((der.m_values,der.m_columns,der.m_offsets),shape=(N,N))
        dw=np.zeros(N);dw[1:]=spsolve(A[1:,1:],residual[1:])
        assert np.isfinite(dw).all()
        before=np.linalg.norm(residual);step=1
        if it==0:log('Initial balance',float(der.v_values.min()),float(der.v_values.max()),'Newton max',float(abs(dw).max()))
        for back in range(35):
            trial=weights-step*dw;pd.set_weights(trial);m=pd.integrals()
            if m.min()>1e-12 and np.linalg.norm(m-target)<before:
                weights=trial;break
            step*=.5
        else:raise ValueError('No Newton descent')
        if it%10==0:log('Balance',it,'error',round(float(abs(m-target).max()),2))
    raise ValueError('Population balance did not converge')

cache_path=WORK/'balanced_cells_fine.npz'
if cache_path.exists():
    cached=np.load(cache_path);pos,weights=cached['pos'],cached['weights']
else:
    baseline=WORK/'balanced_cells.npz'
    if baseline.exists():
        previous=np.load(baseline);pos,weights=previous['pos'],previous['weights']
    else:
        rng=np.random.default_rng(20250905)
        chosen=rng.choice(Q.size,size=N,replace=False,p=Q.ravel()/Q.sum())
        pos=np.stack([chosen%measure_resolution+rng.random(N),chosen//measure_resolution+rng.random(N)],1)*W/measure_resolution
        density=np.maximum(Q,Q.mean()*1e-3)*measure_scale
        for lloyd in range(5):
            pd=balance(pos,np.zeros(N),density);weights=pd.get_weights().copy()
            log('Lloyd',lloyd,'balanced')
            if lloyd<4:pos=pd.centroids()
    for floor in [4e-5,1e-6]:
        pd=balance(pos,weights,np.maximum(Q,Q.mean()*floor)*measure_scale);weights=pd.get_weights().copy()
        log('Fine population balance',floor)
    np.savez_compressed(cache_path,pos=pos,weights=weights)

from refine_human_fabric import calibrate
weights,masses,source_check=calibrate(P,warp,pos,weights,Q)
np.savez_compressed(cache_path,pos=pos,weights=weights)
pd=PowerDiagram(positions=pos,weights=weights,domain=ScaledImage([0,0],[W,W],Q*measure_scale))
centres=pd.centroids()/W
log('Source population range',float(masses.min()),float(masses.max()))
assert np.max(abs(masses/masses.mean()-1))<.002
values=[]
for density in [G,P15,PY]:
    pd.set_domain(ScaledImage([0,0],[W,W],density*measure_scale));v=pd.integrals();values.append(v)
    assert abs(v.sum()/density.sum()-1)<1e-8
gdp,pop2015,personyears=values

# Invert precisely the same piecewise affine mesh rendered by the browser.
yy,xx=np.mgrid[0:n+1,0:n+1];uv=np.stack([xx.ravel(),yy.ravel()],1)/n
aa=(yy[:-1,:-1]*(n+1)+xx[:-1,:-1]).ravel()
triangles=np.vstack([np.stack([aa,aa+1,aa+n+2],1),np.stack([aa,aa+n+2,aa+n+1],1)])
target=warp.reshape(-1,2)
tri=mtri.Triangulation(target[:,0],target[:,1],triangles)
finder=tri.get_trifinder();nearest=cKDTree(target)
def inverse(points):
    points=np.array(points,float);original=points.copy();ids=finder(points[:,0],points[:,1])
    # Clipping can leave an outer-boundary point a few ulps outside its triangle.
    # Move only those boundary samples inward, without snapping them to a vertex.
    for epsilon in [1e-10,1e-9,1e-8,1e-7,1e-6]:
        missing=ids<0
        if not missing.any():break
        points[missing]=original[missing]*(1-epsilon)+np.array([.5,.5])*epsilon
        ids=finder(points[:,0],points[:,1])
    assert (ids>=0).all()
    k=triangles[ids];a,b,c=target[k[:,0]],target[k[:,1]],target[k[:,2]]
    e1,e2,q=b-a,c-a,points-a
    cross=lambda a,b:a[:,0]*b[:,1]-a[:,1]*b[:,0]
    det=cross(e1,e2);s=cross(q,e2)/det;t=cross(e1,q)/det
    return uv[k[:,0]]*(1-s[:,None]-t[:,None])+uv[k[:,1]]*s[:,None]+uv[k[:,2]]*t[:,None]

source_centres=inverse(centres)
roundtrip=float(np.max(np.linalg.norm(forward(source_centres)-centres,axis=1)))
assert roundtrip<1e-7
log('Inverse constructed, roundtrip',roundtrip)
boundary=np.vstack([warp[0],warp[1:,-1],warp[-1,-2::-1],warp[-2:0:-1,0]])
frame=Polygon(boundary*W)
assert frame.is_valid, 'The displayed outer boundary must not cross itself'
domain=ConvexPolyhedraAssembly();domain.add_box([0,0],[W,W]);pd.set_domain(domain)
offsets,xy=pd.cell_polyhedra()
polys=[Polygon(xy[a:b]) for a,b in zip(offsets[:-1],offsets[1:])]
target_labels=rasterize([(p,i) for i,p in enumerate(polys)],out_shape=(4096,4096),transform=Affine.scale(W/4096),dtype='uint16')
atlas=np.array(Image.open(OUT/'atlas.png'))
for r0 in range(0,4096,64):
    ry,cx=np.mgrid[r0:r0+64,0:4096]
    loc=forward(np.stack([cx.ravel()+.5,ry.ravel()+.5],1)/4096)*4096
    col,row=np.clip(loc.astype(int),0,4095).T
    ids=target_labels[row,col].reshape(64,4096)
    atlas[r0:r0+64,:,0]=ids%256;atlas[r0:r0+64,:,1]=ids//256
Image.fromarray(atlas).save(OUT/'atlas.png',optimize=True)

edge_set={};expansions=[]
def geo(uv):
    lat=2*np.arctan(np.exp((.5-uv[:,1])*2*np.pi))-np.pi/2
    return np.stack([uv[:,0],.28-lat/np.pi*.5],1)
def area(p):return abs(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))*.5
for poly in polys:
    clipped=poly.intersection(frame)
    pieces=list(clipped.geoms) if clipped.geom_type=='MultiPolygon' else [clipped]
    src_area=0.;dst_area=0.
    for piece in pieces:
        if piece.is_empty:continue
        ring=np.array(piece.exterior.coords)/W;dense=[]
        for a,b in zip(ring[:-1],ring[1:]):
            count=max(1,int(np.ceil(np.linalg.norm(b-a)*W/1.5)))
            pts=np.linspace(a,b,count+1)
            dense.extend(pts[:-1])
            key=tuple(sorted([tuple(np.round(a,8)),tuple(np.round(b,8))]))
            edge_set[key]=pts
        src=inverse(np.array(dense));src_area+=area(geo(src));dst_area+=piece.area/W**2*.56
    expansions.append(dst_area/src_area if src_area>0 else 1.)
edges=[]
for pts in edge_set.values():
    source=inverse(pts);edges.append(np.stack([source[:-1],source[1:]],1).reshape(-1,2))
np.vstack(edges).astype('<f4').tofile(OUT/'edges.bin')

meta=json.loads((OUT/'world.json').read_text())
for i,u in enumerate(meta['units']):
    u['uv']=source_centres[i].tolist();u['people']=round(float(masses[i]));u['expansion']=round(expansions[i],4)
    u['ratio']=float(gdp[i]/pop2015[i]/(gdp.sum()/pop2015.sum())) if pop2015[i]>0 and gdp[i]>0 else None
    u['history']=float(gdp[i]/personyears[i]/(gdp.sum()/personyears.sum())) if personyears[i]>0 and gdp[i]>0 else None
    u['output']=round(float(gdp[i]/pop2015[i])) if pop2015[i]>0 and gdp[i]>0 else None
    col,row=np.clip(source_centres[i]*4096,0,4095).astype(int);cid=int(atlas[row,col,2])
    if not cid:
        patch=atlas[max(0,row-12):row+13,max(0,col-12):col+13,2];valid=patch[patch>0]
        if len(valid):cid=int(np.bincount(valid).argmax())
    u['country']=cid
for place,(lon,lat) in zip(meta['places'],[(90.1,23.5),(31.2,29.9),(109.8,-7.1),(8.5,49.0)]):
    u,v=grid.xy(lon,lat);place['unit']=int(np.sum((source_centres-np.array([u,v])/W)**2,axis=1).argmin())
meta['sources']['cells']='Capacity-constrained cells on the conservatively transported 2025 population; five centroidal relaxations, then pulled back through the display mesh.'
meta['sources']['quadrature']='Adaptive source-pixel sampling with at most 2000 people per sample, accumulated on a 4096 by 4096 human-space grid.'
meta['sources']['capacity']='Cell capacities are then calibrated by direct geometric integration of the original source pixels. The quadrature is not the final population check.'
(OUT/'source-population-check.json').write_text(json.dumps(source_check,indent=2))
(OUT/'world.json').write_text(json.dumps(meta,separators=(',',':'),allow_nan=False))
report=json.loads((OUT/'verification.json').read_text())
report.update({'unit_population_min':float(masses.min()),'unit_population_max':float(masses.max()),'unit_mass_max_relative_error':float(np.max(abs(masses/masses.mean()-1))),
               'population_total':float(masses.sum()),'source_population_total':float(P.sum()),'conservative_transport_relative_error':float(abs(Q.sum()/P.sum()-1)),
               'unit_centre_roundtrip_max':roundtrip,'cell_construction':'Balanced in human space; pulled back to geography','centroidal_iterations':5,'measure_resolution':measure_resolution,'quadrature_max_people_per_sample':2000,
               'source_capacity_check':'source-population-check.json','source_capacity_max_relative_error':source_check['max_relative_capacity_error']})
import hashlib
report['assets']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [OUT/'world.json',OUT/'warp.bin',OUT/'atlas.png',OUT/'edges.bin',OUT/'source-population-check.json']}
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
np.savez_compressed(WORK/'fabric.npz',source_centres=source_centres,target_centres=centres,masses=masses,positions=pos,weights=weights)
log('Balanced fabric ready',len(edge_set),'edges')
