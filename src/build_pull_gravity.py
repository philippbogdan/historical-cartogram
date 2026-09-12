"""Strong inward flow from the inverse of the existing outward display field.

The same source positions go through either F or its spatial inverse. Pull is
therefore a different deformation, not reverse playback. Keep a small geographic
component so the finite drawing mesh remains positively oriented throughout motion.
"""
import numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
import json,hashlib
from scipy.ndimage import map_coordinates
root=Path(__file__).resolve().parents[1]/'site/human-space'; n=512
warp=np.fromfile(root/'warp.bin',dtype='<f4').astype(float).reshape(n+1,n+1,2)
y,x=np.mgrid[0:n+1,0:n+1]/n
geo=lambda v:.28-(2*np.arctan(np.exp((.5-v)*2*np.pi))-np.pi/2)/np.pi*.5
base=np.stack([x,geo(y)],-1)
query=base.reshape(-1,2).copy();query[:,1]/=.56
_,idx=cKDTree(warp.reshape(-1,2)).query(query,workers=-1)
uv=np.column_stack((idx%(n+1),idx//(n+1)))/n

def evaluate(uv,derivatives=False):
 p=np.clip(uv*n,0,n-1e-6);i=p.astype(int);f=p-i
 a=warp[i[:,1],i[:,0]];b=warp[i[:,1],i[:,0]+1];c=warp[i[:,1]+1,i[:,0]+1];d=warp[i[:,1]+1,i[:,0]]
 mask=(f[:,0]>=f[:,1])[:,None]
 dx=np.where(mask,b-a,c-d);dy=np.where(mask,c-b,d-a)
 value=a+dx*f[:,0,None]+dy*f[:,1,None]
 return (value,dx*n,dy*n) if derivatives else value
for k in range(80):
 value,dx,dy=evaluate(uv,True);r=value-query;error=np.linalg.norm(r,axis=1)
 if error.max()<1e-6:break
 det=dx[:,0]*dy[:,1]-dx[:,1]*dy[:,0]
 delta=np.column_stack(((r[:,0]*dy[:,1]-r[:,1]*dy[:,0])/det,(dx[:,0]*r[:,1]-dx[:,1]*r[:,0])/det))
 delta*=np.minimum(1,.04/np.maximum(np.linalg.norm(delta,axis=1),1e-12))[:,None]
 active=error>1e-8; candidate=np.clip(uv-delta,0,1)
 for step in range(12):
  ce=np.linalg.norm(evaluate(candidate)-query,axis=1);bad=(ce>error)&active
  if not bad.any():break
  delta[bad]*=.5;candidate[bad]=np.clip(uv[bad]-delta[bad],0,1)
 uv[active]=candidate[active]
 if k%10==0:print(k,error.max(),np.quantile(error,[.5,.99]),flush=True)
positions=np.stack([uv[:,0],geo(uv[:,1])],-1).reshape(base.shape)
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

strength=1.0
while minimum_area(base+(positions-base)*strength)<1e-9:
    strength*=.95
strength*=.4
field=(base+(positions-base)*strength).astype('<f4')
(root/'pull.bin').write_bytes(field.tobytes())
paper_raw=(root/'paper.json').read_bytes();paper=json.loads(paper_raw)
uv_sites=np.array(paper['sites']);points=np.stack([uv_sites[:,0],geo(uv_sites[:,1])],axis=1)
target_sites=np.stack([map_coordinates(field[:,:,i],(uv_sites[:,::-1]*n).T,order=1) for i in [0,1]],axis=1)
report={'model':'Attractive inverse of the outward transport field, sampled on the same geographic coordinates',
 'paper_sha256':hashlib.sha256(paper_raw).hexdigest(),
 'warp_sha256':hashlib.sha256((root/'warp.bin').read_bytes()).hexdigest(),
 'pull_sha256':hashlib.sha256(field.tobytes()).hexdigest(),
 'mesh_resolution':n,'inverse_iterations':k+1,'strength':strength,
 'interior_inverse_residual_max':float(error.reshape(n+1,n+1)[1:-1,1:-1].max()),
 'boundary_policy':'Clamp inverse queries outside the outward map to its source edge',
 'minimum_interpolated_triangle_area':minimum_area(field),
 'mean_site_displacement':float(np.linalg.norm(target_sites-points,axis=1).mean())}
(root/'gravity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
