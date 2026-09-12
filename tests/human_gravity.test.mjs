import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {geography} from '../site/human-space/geometry.js';
import {paperEndpoints,isFrameEdge,populationCoasts,southLimit} from '../site/human-space/paper-geometry.js';
const asset=name=>readFileSync(new URL(`../site/human-space/${name}`,import.meta.url));
const floats=name=>{const b=asset(name);return new Float32Array(b.buffer,b.byteOffset,b.byteLength/4);};
const paper=JSON.parse(asset('paper.json')),gravity=JSON.parse(asset('gravity.json'));
const warp=floats('warp.bin'),pull=floats('pull.bin');
const n=512,hash=b=>createHash('sha256').update(b).digest('hex');

test('Pull is a separate attractive field with greater local concentration',()=>{
  assert.equal(hash(asset('paper.json')),gravity.paper_sha256);
  assert.equal(hash(asset('pull.bin')),gravity.pull_sha256);
  assert.equal(pull.length,warp.length);
  assert.ok(pull.every(Number.isFinite));
  const sites=paper.sites.filter((_,i)=>i%8===0);
  const points=paperEndpoints(sites.flat(),warp,n,pull);
  let before=0,after=0,pairs=0,movement=0;
  for(let i=0;i<sites.length;i++){
    const k=i*6;movement+=Math.hypot(points[k+4]-points[k],points[k+5]-points[k+1]);
    for(let j=0;j<i;j++){
      const l=j*6,d=Math.hypot(points[k]-points[l],points[k+1]-points[l+1]);
      if(d<.045&&d>.004){
        before+=d;after+=Math.hypot(points[k+4]-points[l+4],points[k+5]-points[l+5]);pairs++;
      }
    }
  }
  assert.ok(pairs>1000);
  assert.ok(after/before<.95,`Neighbourhood ratio ${after/before}`);
  assert.ok(movement/sites.length>.005,'Pull must move sites beyond the geographic endpoint');
});

test('The frame and Antarctic coast disappear without excluding population sites',()=>{
  assert.equal(isFrameEdge(0,0,0,.5),true);
  assert.equal(isFrameEdge(.2,1,.8,1),true);
  assert.equal(isFrameEdge(.2,.4,.2,.6),false);
  const visible=populationCoasts(paper.coastlines);
  assert.ok(visible.flat().length<paper.coastlines.flat().length);
  assert.ok(visible.every(line=>line.every(point=>point[1]<=southLimit)));
  assert.ok(paper.sites.every(point=>point[1]<southLimit));
  const original=geography([.5,.5]);
  assert.deepEqual(original,[.5,.28]);
});

// The determinant is quadratic over the triangle of geography/push/pull weights.
function minimum(C,B,D,A,E,F){
  const values=[C,C+B+A,C+D+E];
  function edge(a,b,c){if(a>0){const t=-b/(2*a);if(t>0&&t<1)values.push(a*t*t+b*t+c);}}
  edge(A,B,C);edge(E,D,C);edge(A+E-F,B-D+F-2*E,C+D+E);
  const det=4*A*E-F*F;
  if(A>0&&det>0){
    const u=(-2*E*B+F*D)/det,v=(F*B-2*A*D)/det;
    if(u>0&&v>0&&u+v<1)values.push(C+B*u+D*v+A*u*u+E*v*v+F*u*v);
  }
  return Math.min(...values);
}
test('Both gravity modes and every eased blend preserve the orientation of all mesh triangles',()=>{
  const sub=(a,b)=>[a[0]-b[0],a[1]-b[1]],cross=(a,b)=>a[0]*b[1]-a[1]*b[0];
  const point=i=>({g:geography([i%(n+1)/n,Math.floor(i/(n+1))/n]),p:[warp[i*2],warp[i*2+1]*.56],r:[pull[i*2],pull[i*2+1]]});
  let smallest=Infinity;
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){
    const k=y*(n+1)+x;
    for(const ids of [[k,k+1,k+n+2],[k,k+n+2,k+n+1]]){
      const [a,b,c]=ids.map(point),e=sub(b.g,a.g),f=sub(c.g,a.g);
      const ep=sub(sub(b.p,a.p),e),fp=sub(sub(c.p,a.p),f);
      const er=sub(sub(b.r,a.r),e),fr=sub(sub(c.r,a.r),f);
      const m=minimum(cross(e,f),cross(ep,f)+cross(e,fp),cross(er,f)+cross(e,fr),cross(ep,fp),cross(er,fr),cross(ep,fr)+cross(er,fp));
      smallest=Math.min(smallest,m);
      assert.ok(m>0,`Fold at ${x},${y}`);
    }
  }
  assert.ok(smallest>1e-12);
});
