import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {inflateSync} from 'node:zlib';
import {createRegionAreas} from '../site/human-space/label-area.js';
import {fadeLabel} from '../site/human-space/label-visibility.js';
import {screenFabric} from '../site/human-space/screen-fabric.js';
import {southLimit} from '../site/human-space/paper-geometry.js';
const load=name=>readFileSync(new URL(`../site/human-space/${name}`,import.meta.url));
const paper=JSON.parse(load('paper.json')),colours=JSON.parse(load('country-colours.json'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const fill=c=>c.map(v=>Math.round(v*.45+255*.55));

test('Every country has a distinct regional shade, including India and Pakistan after lightening',()=>{
 assert.equal(colours.paper_sha256,hash(load('paper.json')));
 assert.equal(colours.countries.length,paper.countries.length);
 assert.equal(new Set(colours.countries.map(c=>c.colour.join(','))).size,colours.countries.length);
 assert.equal(new Set(colours.countries.map(c=>fill(c.colour).join(','))).size,colours.countries.length);
 colours.countries.forEach((c,i)=>assert.equal(c.name,paper.countries[i].name));
 const india=colours.countries.find(c=>c.name==='India'),pakistan=colours.countries.find(c=>c.name==='Pakistan');
 assert.equal(india.region,'Southern Asia');assert.equal(pakistan.region,india.region);
 for(const c of [india,pakistan])assert.ok(c.colour[2]>c.colour[0]+50);
 assert.ok(Math.hypot(...fill(india.colour).map((v,i)=>v-fill(pakistan.colour)[i]))>40);
});

test('Centroids follow border geometry and do not shift when the viewport clips a region',()=>{
 const source=new Float32Array([0,0,1,0,1,.5,0,.5]);
 const endpoints=new Float64Array([0,0,0,0,0,0,1,0,2,0,.5,0,1,.5,2,1,.5,.25,0,.5,0,1,0,.25]);
 const measure=createRegionAreas({countries:[{}],country_ids:[0],offsets:[0,4]},source,endpoints);
 const frame={width:600,height:400,scale:100,cx:1,cy:.5,gravity:0};
 assert.deepEqual([...measure({...frame,progress:0}).centroids],[.5,.25]);
 assert.deepEqual([...measure({...frame,progress:1}).centroids],[1,.5]);
 assert.deepEqual([...measure({...frame,progress:0,width:30,cx:.9}).centroids],[.5,.25]);
});

test('Label fades use fast exponential smoothing and remain independent of frame rate',()=>{
 const first=fadeLabel(0,true,.016);
 assert.ok(first>.3&&first<.5);
 assert.ok(fadeLabel(1,false,.016)>.5);
 const two=fadeLabel(fadeLabel(0,true,.016),true,.016);
 assert.ok(Math.abs(two-fadeLabel(0,true,.032))<1e-12);
 assert.equal(fadeLabel(0,true,.18),1);assert.equal(fadeLabel(1,false,.18),0);
 assert.equal(fadeLabel(.2,true,0,true),1);
});

test('Fullscreen continues the fabric beyond every side instead of exposing the moving cutoff',()=>{
 const source=new Float32Array([0,0,1,0,1,1,0,1]);
 const fabric=screenFabric({country_ids:[0],offsets:[0,4]},source,512);
 assert.ok(fabric.fill.length>10000);
 const extents=[Infinity,-Infinity,Infinity,-Infinity];
 for(let i=0;i<fabric.fill.length;i+=4){
  assert.ok(fabric.fill[i]>=0&&fabric.fill[i]<=1);
  assert.ok(fabric.fill[i+1]>=0&&fabric.fill[i+1]<=southLimit+1e-7);
  extents[0]=Math.min(extents[0],fabric.fill[i+2]);extents[1]=Math.max(extents[1],fabric.fill[i+2]);
  extents[2]=Math.min(extents[2],fabric.fill[i+3]);extents[3]=Math.max(extents[3],fabric.fill[i+3]);
 }
 assert.deepEqual(extents,[-4,4,-4,4]);
});

test('Pull is the requested tuned strength, distinctly stronger than the original version',()=>{
 const g=JSON.parse(load('gravity.json'));
 assert.equal(g.strength,.38);
 assert.ok(g.mean_site_displacement>.033&&g.mean_site_displacement<.041);
 assert.ok(g.interior_inverse_residual_max<1e-7);
});

function decodePNG(buffer){
 const width=buffer.readUInt32BE(16),height=buffer.readUInt32BE(20),chunks=[];
 assert.equal(buffer[24],8);assert.equal(buffer[25],2);
 for(let p=8;p<buffer.length;){const n=buffer.readUInt32BE(p);if(buffer.toString('ascii',p+4,p+8)==='IDAT')chunks.push(buffer.subarray(p+8,p+8+n));p+=12+n;}
 const raw=inflateSync(Buffer.concat(chunks)),stride=width*3,out=Buffer.alloc(height*stride);
 const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
 for(let y=0;y<height;y++){
  const type=raw[y*(stride+1)];
  for(let x=0;x<stride;x++){
   const i=y*stride+x,a=x>=3?out[i-3]:0,b=y?out[i-stride]:0,c=y&&x>=3?out[i-stride-3]:0;
   const predictor=[0,a,b,Math.floor((a+b)/2),paeth(a,b,c)][type];
   out[i]=(raw[y*(stride+1)+1+x]+predictor)&255;
  }
 }
 return {width,height,pixels:out};
}
test('The water mask distinguishes sea and the actual India/Pakistan border regions',()=>{
 const raw=load('land-mask.png'),metadata=JSON.parse(load('label-regions.json'));
 assert.equal(hash(raw),metadata.land_mask_sha256);
 const {width,height,pixels}=decodePNG(raw);
 const sample=(lon,lat)=>{const u=((lon+168)%360+360)%360/360,v=.5-Math.log(Math.tan(Math.PI/4+lat*Math.PI/360))/(2*Math.PI);const i=(Math.floor(v*height)*width+Math.floor(u*width))*3;return [...pixels.subarray(i,i+3)];};
 assert.deepEqual(sample(-35,0),[0,0,0]);
 for(const [name,lon,lat] of [['India',77.2,28.6],['Pakistan',73,33.7],['Australia',133,-25]]){
  const pixel=sample(lon,lat);assert.equal(pixel[0],255);assert.equal(pixel[1]-1,paper.countries.findIndex(c=>c.name===name));
 }
});

test('The United States label excludes Alaska while area and continent moments retain it',async()=>{
 const {paperEndpoints}=await import('../site/human-space/paper-geometry.js');
 const floats=name=>{const b=load(name);return new Float32Array(b.buffer,b.byteOffset,b.byteLength/4);};
 const regions=JSON.parse(load('label-regions.json')),source=floats('label-regions.bin');
 const measure=createRegionAreas({...regions,countries:paper.countries},source,paperEndpoints(source,floats('warp.bin'),512,floats('pull.bin')));
 const result=measure({width:1280,height:720,scale:1280,cx:.5,cy:.28,progress:0,gravity:0});
 const id=paper.countries.findIndex(c=>c.name==='United States');
 const longitude=result.labelCentroids[id*2]*360-168;
 const latitude=(.28-result.labelCentroids[id*2+1])*360;
 assert.ok(longitude>-102&&longitude<-95,longitude);
 assert.ok(latitude>37&&latitude<42,latitude);
 assert.ok(result.centroids[id*2]<result.labelCentroids[id*2]);
 assert.ok(result.centroids[id*2+1]<result.labelCentroids[id*2+1]);
 assert.ok(result[id]>10000);
});
