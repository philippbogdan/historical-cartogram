import { endpoints } from './geometry.js';
import { advanceMotion } from './motion.js?v=cb51c7b4f78f';

const canvas=document.getElementById('map');
const context=canvas.getContext('2d',{alpha:false});
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const pointers=new Map();
let points,pressure,frame=0,last=0,holdUntil=0,ready=false;
let progress=1,velocity=0,target=0,playing=!reducedMotion.matches;
let width=1,height=1,dpr=1,fit=1,zoom=1,cx=.5,cy=.28;
let gesture=null,origin=null,dragged=false;

function draw(){
  if(!ready)return;
  context.setTransform(dpr,0,0,dpr,0,0);
  context.fillStyle='#fff';context.fillRect(0,0,width,height);
  context.fillStyle='#000';context.beginPath();
  const scale=fit*zoom;
  const radius=Math.max(.65,Math.min(1.05,fit/1100))*Math.pow(zoom,.25);
  for(let i=0;i<points.length;i+=4){
    const x=width/2+(points[i]+(points[i+2]-points[i])*progress-cx)*scale;
    const y=height/2+(points[i+1]+(points[i+3]-points[i+1])*progress-cy)*scale;
    if(x<-radius||x>width+radius||y<-radius||y>height+radius)continue;
    context.moveTo(x+radius,y);context.arc(x,y,radius,0,Math.PI*2);
  }
  context.fill();
}

function requestDraw(){if(!frame)frame=requestAnimationFrame(tick);}
function tick(now){
  frame=0;
  if(ready&&playing&&!document.hidden&&now>=holdUntil){
    const dt=Math.min(.1,Math.max(0,(now-Math.max(last,holdUntil))/1000));
    const next=advanceMotion(progress,velocity,target,dt,pressure);
    progress=next.position;velocity=next.velocity;
    if(progress===target&&velocity===0){target=1-target;holdUntil=now+3200;}
  }
  last=now;draw();
  if(ready&&playing&&!document.hidden)requestDraw();
}
function resize(){
  width=innerWidth;height=innerHeight;dpr=Math.min(devicePixelRatio||1,3);
  canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
  fit=Math.min(width*.92,height*.88/.56);
  requestDraw();
}
function pause(){playing=false;velocity=0;requestDraw();}
function toggle(){
  if(!ready)return;
  if(reducedMotion.matches){progress=progress<.5?1:0;target=1-progress;velocity=0;requestDraw();return;}
  playing=!playing;velocity=0;holdUntil=0;last=performance.now();requestDraw();
}
function goTo(value){
  if(!ready)return;
  target=value;holdUntil=0;last=performance.now();
  if(reducedMotion.matches){progress=value;velocity=0;playing=false;}
  else playing=true;
  requestDraw();
}
function zoomAt(factor,x,y){
  const next=Math.max(1,Math.min(12,zoom*factor));
  cx+=(x-width/2)/fit*(1/zoom-1/next);
  cy+=(y-height/2)/fit*(1/zoom-1/next);
  zoom=next;
  if(zoom===1){cx=.5;cy=.28;}
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
canvas.addEventListener('dblclick',()=>{zoom=1;cx=.5;cy=.28;requestDraw();});
canvas.addEventListener('keydown',e=>{
  if([' ','Enter','ArrowLeft','ArrowRight','Home','Escape','+','-','='].includes(e.key))e.preventDefault();
  if(e.key===' '||e.key==='Enter')toggle();
  if(e.key==='ArrowLeft')goTo(0);if(e.key==='ArrowRight')goTo(1);
  if(e.key==='Escape')pause();
  if(e.key==='Home'){zoom=1;cx=.5;cy=.28;requestDraw();}
  if(e.key==='+'||e.key==='=')zoomAt(1.4,width/2,height/2);
  if(e.key==='-')zoomAt(1/1.4,width/2,height/2);
});
addEventListener('resize',resize);
document.addEventListener('visibilitychange',()=>{last=performance.now();if(!document.hidden){holdUntil=last+1000;requestDraw();}});
reducedMotion.addEventListener('change',()=>{pause();});

async function asset(name,type='arrayBuffer'){
  const response=await fetch(new URL(name,import.meta.url));
  if(!response.ok)throw new Error(`Could not load ${name}`);
  return response[type]();
}
try{
  const [world,raw,motion]=await Promise.all([asset('world.json','json'),asset('warp.bin'),asset('motion.json','json')]);
  const warp=new Float32Array(raw),n=world.projection.meshResolution;
  if(warp.length!==2*(n+1)**2||!Array.isArray(motion.pressure))throw new Error('Incomplete map data');
  points=new Float64Array(world.units.flatMap(u=>endpoints(u.uv,warp,n)));pressure=motion.pressure;
  ready=true;holdUntil=performance.now()+3200;last=performance.now();resize();
}catch(error){
  console.error(error);
  canvas.setAttribute('aria-label','The cartogram could not load. Reload the page to try again.');
}
