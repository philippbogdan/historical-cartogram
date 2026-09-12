import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {paperEndpoints,labelAnchors} from '../site/human-space/paper-geometry.js';
const asset=name=>readFileSync(new URL(`../site/human-space/${name}`,import.meta.url));
const data=JSON.parse(asset('paper.json'));
const raw=asset('paper-cells.bin'),mesh=asset('warp.bin');
const xy=new Float32Array(raw.buffer,raw.byteOffset,raw.byteLength/4);
const warp=new Float32Array(mesh.buffer,mesh.byteOffset,mesh.byteLength/4);
const hash=b=>createHash('sha256').update(b).digest('hex');

test('Figure 6 contains the original 8192 cells and partitions the whole Mercator square',()=>{
  assert.equal(data.sites_sha256,'6e1b4df7ebdc0fd5de2485acfeec9fc1f7e9dbdec6c7758caa5d3218ee79b155');
  assert.equal(data.sites.length,8192);
  assert.equal(data.offsets.length,8193);
  assert.equal(data.offsets.at(-1)*2,xy.length);
  assert.equal(hash(raw),data.geometry_sha256);
  assert.equal(hash(asset('paper-atlas.png')),data.atlas_sha256);
  assert.ok(Math.abs(data.people_per_cell-999998.5938332108)<1e-7);
  let total=0;
  for(let i=0;i<8192;i++){
    const a=data.offsets[i],b=data.offsets[i+1];let area=0;
    assert.ok(b-a>=3);
    for(let j=a;j<b;j++){
      const next=j+1===b?a:j+1;
      assert.ok(xy[j*2]>=0&&xy[j*2]<=1&&xy[j*2+1]>=0&&xy[j*2+1]<=1);
      area+=xy[j*2]*xy[next*2+1]-xy[next*2]*xy[j*2+1];
    }
    assert.ok(Math.abs(area)>1e-10,`Cell ${i} has no area`);
    total+=Math.abs(area)/2;
  }
  assert.ok(Math.abs(total-1)<1e-7,`Covered area ${total}`);
});

test('Every displayed colour has a named country and continent, with no grey fallback',()=>{
  assert.equal(data.country_ids.length,8192);
  for(const id of data.country_ids){
    const c=data.countries[id];assert.ok(c.name&&c.continent);
    assert.ok(!['Ocean','Seven seas (open ocean)'].includes(c.continent));
    for(const key of ['country','continental'])assert.ok(Math.max(...c[key])-Math.min(...c[key])>=30,c.name);
  }
  const labels=labelAnchors(data);
  for(let mode=0;mode<2;mode++)for(const label of labels[mode]){
    const c=data.countries[data.country_ids[label.index]];
    assert.equal(label.name,mode?c.continent:c.name);
  }
});

test('Paper geometry stays finite and the Mercator-to-cartogram map never folds',()=>{
  assert.equal(hash(mesh),data.warp_sha256);
  const n=Math.sqrt(warp.length/2)-1;
  const points=paperEndpoints(xy,warp,n);
  assert.ok(points.every(Number.isFinite));
  const cross=(a,b)=>a[0]*b[1]-a[1]*b[0];
  const sub=(a,b)=>[a[0]-b[0],a[1]-b[1]];
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){
    const k=y*(n+1)+x;
    for(const ids of [[k,k+1,k+n+2],[k,k+n+2,k+n+1]]){
      const p=ids.map(i=>({a:[(i%(n+1))/n,Math.floor(i/(n+1))/n],b:[warp[2*i],warp[2*i+1]]}));
      const e=sub(p[1].a,p[0].a),f=sub(p[2].a,p[0].a);
      const de=sub(sub(p[1].b,p[0].b),e),df=sub(sub(p[2].b,p[0].b),f);
      const A=cross(de,df),B=cross(de,f)+cross(e,df),C=cross(e,f);
      const values=[C,A+B+C],t=-B/(2*A);
      if(A>0&&t>0&&t<1)values.push(A*t*t+B*t+C);
      assert.ok(Math.min(...values)>0,`Fold at ${x},${y}`);
    }
  }
});
