import test from 'node:test';
import assert from 'node:assert/strict';
import {createRegionAreas,labelFontSize} from '../site/human-space/label-area.js';
const source=new Float32Array([0,0,1,0,1,.5,0,.5]);
const data={countries:[{name:'Region'}],country_ids:[0],offsets:[0,4]};
const endpoints=new Float64Array(Array.from({length:4},(_,i)=>{
  const x=source[2*i],y=source[2*i+1];
  return [x,y,2*x,2*y,.5*x,.5*y];
}).flat());
const measure=createRegionAreas(data,source,endpoints);
const frame={width:600,height:400,scale:100,cx:1,cy:.5};

test('Type grows with the region throughout the deformation, including attractive contraction',()=>{
  const a=measure({...frame,progress:0,gravity:0})[0];
  const b=measure({...frame,progress:.5,gravity:0})[0];
  const c=measure({...frame,progress:1,gravity:0})[0];
  const d=measure({...frame,progress:1,gravity:1})[0];
  assert.equal(a,5000);assert.equal(b,11250);assert.equal(c,20000);assert.equal(d,1250);
  assert.equal(labelFontSize(c,4),2*labelFontSize(a,4));
  assert.equal(labelFontSize(d,4),.5*labelFontSize(a,4));
});
test('Only visible area contributes when the region is zoomed or panned off-screen',()=>{
  assert.equal(measure({...frame,progress:0,gravity:0,width:50,height:100,cx:.75,cy:.25})[0],2500);
  assert.equal(measure({...frame,progress:0,gravity:0,width:50,height:100,cx:3,cy:.25})[0],0);
  const normal=measure({...frame,progress:0,gravity:0})[0];
  const zoomed=measure({...frame,progress:0,gravity:0,scale:200})[0];
  assert.equal(zoomed,normal*4);
  assert.equal(labelFontSize(zoomed,4),labelFontSize(normal,4)*2);
});
test('Countries are accumulated independently and empty regions do not inherit another region area',()=>{
  const regions=createRegionAreas({...data,countries:[{},{}],country_ids:[1]},source,endpoints);
  assert.deepEqual([...regions({...frame,progress:0,gravity:0})],[0,5000]);
});

test('Real country footprints shrink Canada and grow India, without treating island ocean cells as land',async()=>{
  const {readFileSync}=await import('node:fs');
  const {createHash}=await import('node:crypto');
  const {paperEndpoints}=await import('../site/human-space/paper-geometry.js');
  const load=name=>readFileSync(new URL(`../site/human-space/${name}`,import.meta.url));
  const floats=name=>{const raw=load(name);return new Float32Array(raw.buffer,raw.byteOffset,raw.byteLength/4);};
  const paper=JSON.parse(load('paper.json')),regions=JSON.parse(load('label-regions.json'));
  const hash=raw=>createHash('sha256').update(raw).digest('hex');
  assert.equal(hash(load('paper.json')),regions.paper_sha256);
  assert.equal(hash(load('label-regions.bin')),regions.geometry_sha256);
  const source=floats('label-regions.bin');
  const measure=createRegionAreas({...regions,countries:paper.countries},source,paperEndpoints(source,floats('warp.bin'),512,floats('pull.bin')));
  const view={gravity:0,width:1280,height:720,scale:1280,cx:.5,cy:.28};
  const geographic=[...measure({...view,progress:0})],human=[...measure({...view,progress:1})];
  const id=name=>paper.countries.findIndex(c=>c.name===name);
  assert.ok(geographic[id('Russia')]>geographic[id('China')]);
  assert.ok(human[id('India')]>geographic[id('India')]*20);
  assert.ok(human[id('Canada')]<geographic[id('Canada')]*.3);
  assert.ok(geographic[id('Nauru')]<geographic[id('India')]/10000);
  assert.ok(geographic.every(a=>a>=-1e-6)&&human.every(a=>a>=-1e-6));
});

test('Holes are subtracted from a footprint rather than counted as extra area',()=>{
  const inner=source.map(v=>v*.5);
  const outerAndHole=new Float32Array([...source,...inner]);
  const sameEndpoints=xy=>Array.from({length:xy.length/2},(_,i)=>[xy[i*2],xy[i*2+1],xy[i*2],xy[i*2+1],xy[i*2],xy[i*2+1]]).flat();
  const measure=createRegionAreas({countries:[{}],country_ids:[0,0],offsets:[0,4,8],signs:[1,-1]},outerAndHole,new Float64Array(sameEndpoints(outerAndHole)));
  assert.equal(measure({...frame,progress:0,gravity:0})[0],3750);
});
