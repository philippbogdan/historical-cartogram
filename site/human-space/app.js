import { paperEndpoints, labelAnchors } from './paper-geometry.js?v=0b3c413bf9ec';
import { createPaperPolygons } from './paper-polygons.js?v=ac34b4ec23b3';
import { advanceMotion } from './motion.js?v=cb51c7b4f78f';

const canvas=document.getElementById('map'),context=canvas.getContext('2d');
const polygonCanvas=document.getElementById('polygons');
let polygonRenderer;
const labels=document.getElementById('labels');
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const pointers=new Map();
let colourMode=0,representation='polygons',data,points,vertices,coasts,groups,labelGroups;
let pressure,frame=0,last=0,holdUntil=0,ready=false;
let progress=0,velocity=0,target=1,playing=false;
let width=1,height=1,dpr=1,fit=1,zoom=1,cx=.5,cy=.5;
let gesture=null,origin=null,dragged=false;
document.querySelectorAll('.selectors input').forEach(input=>input.disabled=true);

function screen(source,i){
  return [width/2+(source[i]+(source[i+2]-source[i])*progress-cx)*fit*zoom,
    height/2+(source[i+1]+(source[i+3]-source[i+1])*progress-cy)*fit*zoom];
}
function trace(source,start,end,close=false){
  for(let i=start;i<end;i+=4){
    const [x,y]=screen(source,i);
    if(i===start)context.moveTo(x,y);else context.lineTo(x,y);
  }
  if(close)context.closePath();
}
function draw(){
  if(!ready)return;
  context.setTransform(dpr,0,0,dpr,0,0);
  polygonCanvas.hidden=representation!=='polygons'||!polygonRenderer;
  context.clearRect(0,0,width,height);
  if(polygonCanvas.hidden){context.fillStyle='#fff';context.fillRect(0,0,width,height);}
  if(representation==='polygons'){
    if(polygonRenderer)polygonRenderer({width,height,dpr,fit,zoom,cx,cy,progress,colourMode});
    else {
    context.lineWidth=Math.max(.45,fit*.00055)*Math.pow(zoom,.35);
    context.lineJoin='round';context.strokeStyle='#000';
    if(colourMode){
      for(const group of groups[colourMode]){
        context.fillStyle=group.fill;context.beginPath();
        for(const i of group.indices)trace(vertices,data.offsets[i]*4,data.offsets[i+1]*4,true);
        context.fill();
      }
    }
    context.beginPath();
    for(let i=0;i<data.sites.length;i++)trace(vertices,data.offsets[i]*4,data.offsets[i+1]*4,true);
    context.stroke();
    }
  }else{
    const radius=Math.max(.65,Math.min(1.1,fit/850))*Math.pow(zoom,.25);
    for(const group of groups[colourMode]){
      context.fillStyle=group.colour;context.beginPath();
      for(const i of group.indices){
        const [x,y]=screen(points,i*4);
        if(x<0||x>width||y<0||y>height)continue;
        context.moveTo(x+radius,y);context.arc(x,y,radius,0,Math.PI*2);
      }
      context.fill();
    }
  }
  context.strokeStyle='#000';context.lineWidth=Math.max(.65,fit*.00077)*Math.pow(zoom,.25);
  context.lineCap='round';context.setLineDash([.6,1.8]);context.beginPath();
  for(const line of coasts)trace(line,0,line.length);
  context.stroke();context.setLineDash([]);
  drawLabels();
}
function drawLabels(){
  labels.classList.toggle('over-polygons',representation==='polygons');
  const boxes=[];
  for(let mode=1;mode<=2;mode++){
    for(const label of labelGroups[mode-1]){
      const el=label.element;
      if(mode!==colourMode){el.hidden=true;continue;}
      const [x,y]=screen(points,label.index*4);
      const size=mode===2?Math.max(14,Math.min(36,fit*.033))*Math.pow(zoom,.1):
        Math.max(12,Math.min(24,11+Math.sqrt(label.count)*.38))*Math.pow(zoom,.14);
      // Small countries appear on zoom, instead of covering their neighbours.
      if(mode===1&&label.count*zoom*zoom<14){el.hidden=true;continue;}
      el.style.fontSize=`${size}px`;
      const w=label.width*size,h=size*(mode===2&&label.name.includes(' ')?2:1.15);
      let placement=null;
      const candidates=[[0,0],[0,1.4],[0,-1.4],[1.4,0],[-1.4,0],[0,2.8],[0,-2.8]];
      for(const [dx,dy] of candidates){
        const px=mode===2?Math.max(w/2+10,Math.min(width-w/2-10,x+dx*size)):x+dx*size,py=y+dy*size;
        const box={left:px-w/2-5,right:px+w/2+5,top:py-h/2-4,bottom:py+h/2+4};
        const blocked=box.left<4||box.right>width-4||box.top<4||box.bottom>height-4||
          (box.left<300&&box.top<102)||boxes.some(b=>box.left<b.right&&box.right>b.left&&box.top<b.bottom&&box.bottom>b.top);
        if(!blocked){placement={px,py,box};break;}
      }
      el.hidden=!placement;
      if(placement){el.style.transform=`translate(${placement.px}px,${placement.py}px) translate(-50%,-50%)`;boxes.push(placement.box);}
    }
  }
}
function requestDraw(){if(!frame)frame=requestAnimationFrame(tick);}
function tick(now){
  frame=0;
  if(ready&&playing&&!document.hidden&&now>=holdUntil){
    const dt=Math.min(.1,Math.max(0,(now-Math.max(last,holdUntil))/1000));
    const next=advanceMotion(progress,velocity,target,dt,pressure);
    progress=next.position;velocity=next.velocity;
    if(progress===target&&velocity===0)playing=false;
  }
  last=now;draw();
  if(ready&&playing&&!document.hidden)requestDraw();
}
function resize(){
  width=innerWidth;height=innerHeight;dpr=Math.min(devicePixelRatio||1,3);
  canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
  fit=Math.min(width-32,height-32);requestDraw();
}
function pause(){playing=false;velocity=0;requestDraw();}
function toggle(){
  if(!ready)return;
  if(playing){pause();return;}
  goTo(Math.abs(progress-target)<.001?1-target:target);
}
function goTo(value){
  if(!ready)return;
  target=value;holdUntil=0;last=performance.now();
  document.querySelector(`input[name="direction"][value="${value}"]`).checked=true;
  if(reducedMotion.matches){progress=value;velocity=0;playing=false;}else playing=true;
  requestDraw();
}
function zoomAt(factor,x,y){
  const next=Math.max(1,Math.min(12,zoom*factor));
  cx+=(x-width/2)/fit*(1/zoom-1/next);
  cy+=(y-height/2)/fit*(1/zoom-1/next);
  zoom=next;
  if(zoom===1){cx=.5;cy=.5;}
  requestDraw();
}
function pointerGeometry(){
  const p=[...pointers.values()];
  return p.length>1?{x:(p[0].x+p[1].x)/2,y:(p[0].y+p[1].y)/2,d:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)}:{...p[0],d:0};
}
canvas.addEventListener('pointerdown',e=>{
  pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});canvas.setPointerCapture(e.pointerId);
  if(pointers.size===1)dragged=false;else dragged=true;
  gesture=pointerGeometry();origin=gesture;
});
canvas.addEventListener('pointermove',e=>{
  if(!pointers.has(e.pointerId))return;
  pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});const next=pointerGeometry();
  const dx=next.x-gesture.x,dy=next.y-gesture.y;
  if(Math.hypot(next.x-origin.x,next.y-origin.y)>4)dragged=true;
  if(dragged){
    cx-=dx/(fit*zoom);cy-=dy/(fit*zoom);
    if(next.d&&gesture.d)zoomAt(next.d/gesture.d,next.x,next.y);
    requestDraw();
  }
  gesture=next;
});
function release(e){
  pointers.delete(e.pointerId);
  if(pointers.size){gesture=pointerGeometry();return;}
  if(!dragged&&e.type==='pointerup')toggle();
  gesture=null;
}
canvas.addEventListener('pointerup',release);canvas.addEventListener('pointercancel',release);
canvas.addEventListener('wheel',e=>{e.preventDefault();zoomAt(Math.exp(-Math.max(-150,Math.min(150,e.deltaY))*.003),e.clientX,e.clientY);},{passive:false});
canvas.addEventListener('dblclick',()=>{zoom=1;cx=.5;cy=.5;requestDraw();});
canvas.addEventListener('keydown',e=>{
  if([' ','Enter','ArrowLeft','ArrowRight','Home','Escape','+','-','='].includes(e.key))e.preventDefault();
  if(e.key===' '||e.key==='Enter')toggle();
  if(e.key==='ArrowLeft')goTo(0);if(e.key==='ArrowRight')goTo(1);
  if(e.key==='Escape')pause();
  if(e.key==='Home'){zoom=1;cx=.5;cy=.5;requestDraw();}
  if(e.key==='+'||e.key==='=')zoomAt(1.4,width/2,height/2);
  if(e.key==='-')zoomAt(1/1.4,width/2,height/2);
});
document.querySelectorAll('input[name="colour"]').forEach(input=>input.addEventListener('change',()=>{
  colourMode=Number(input.value);requestDraw();
}));
document.querySelectorAll('input[name="representation"]').forEach(input=>input.addEventListener('change',()=>{
  representation=input.value;requestDraw();
}));
document.querySelectorAll('input[name="direction"]').forEach(input=>input.addEventListener('click',()=>goTo(Number(input.value))));
const expand=document.getElementById('expand');
expand.addEventListener('click',async()=>{
  try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}
  catch{zoomAt(zoom===1?2:1/zoom,width/2,height/2);}
});
document.addEventListener('fullscreenchange',()=>{
  const label=document.fullscreenElement?'Exit fullscreen':'Expand map';
  expand.setAttribute('aria-label',label);expand.title=label;resize();
});
addEventListener('resize',resize);
document.addEventListener('visibilitychange',()=>{last=performance.now();if(!document.hidden)requestDraw();});
reducedMotion.addEventListener('change',pause);
async function asset(name,type='arrayBuffer'){
  const response=await fetch(new URL(name,import.meta.url));
  if(!response.ok)throw new Error(`Could not load ${name}`);
  return response[type]();
}
try{
  const [paper,raw,mesh,motion]=await Promise.all([asset('paper.json','json'),asset('paper-cells.bin'),asset('warp.bin'),asset('motion.json','json')]);
  data=paper;const warp=new Float32Array(mesh),n=Math.sqrt(warp.length/2)-1;
  try{
    const response=await fetch(new URL('paper-atlas.png',import.meta.url));
    if(!response.ok)throw new Error('Could not load polygon colours');
    const image=await createImageBitmap(await response.blob(),{colorSpaceConversion:'none'});
    polygonRenderer=createPaperPolygons(polygonCanvas,warp,n,image,paper,new Float32Array(raw));image.close();
  }catch(error){console.warn('Using the canvas polygon renderer:',error.message);}
  points=paperEndpoints(paper.sites.flat(),warp,n);
  vertices=paperEndpoints(new Float32Array(raw),warp,n);
  coasts=paper.coastlines.map(line=>paperEndpoints(line.flat(),warp,n));pressure=motion.pressure;
  groups=[0,1,2].map(mode=>{
    const buckets=new Map();paper.country_ids.forEach((country,i)=>{
      const rgb=mode===0?[0,0,0]:paper.countries[country][mode===1?'country':'continental'];
      const colour=`rgb(${rgb.join(',')})`;
      const fill=`rgb(${rgb.map(c=>Math.round(c*.45+255*.55)).join(',')})`;
      if(!buckets.has(colour))buckets.set(colour,{colour,fill,indices:[]});buckets.get(colour).indices.push(i);
    });return [...buckets.values()];
  });
  await document.fonts.load('900 24px Chivo');
  labelGroups=labelAnchors(paper);
  context.font='900 100px Chivo';
  labelGroups.forEach((group,mode)=>group.forEach(label=>{
    const el=document.createElement('span');el.className='map-label';el.hidden=true;
    el.textContent=label.name.toUpperCase();
    if(mode===1)el.style.whiteSpace='pre';
    const words=mode===1?label.name.toUpperCase().split(' '):[label.name.toUpperCase()];
    if(mode===1)el.textContent=words.join('\n');
    label.width=Math.max(...words.map(word=>context.measureText(word).width))/100;
    label.element=el;labels.append(el);
  }));
  document.querySelectorAll('.selectors input').forEach(input=>input.disabled=false);
  ready=true;holdUntil=performance.now()+5000;last=performance.now();resize();
}catch(error){
  console.error(error);canvas.setAttribute('aria-label','The cartogram could not load. Reload the page to try again.');
}
