import { endpoints, interpolate, ease } from './geometry.js';
import { advanceMotion } from './motion.js?v=90a7a4942cb2';

const $ = id => document.getElementById(id);
const canvas = $('map'), stage = $('map-stage'), overlay = $('labels');
const hud = overlay.getContext('2d');
const range = $('transformation');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const controls=[...document.querySelectorAll('.experience button,.colour-section button')].filter(b=>b.id!=='retry');
controls.forEach(b=>b.disabled=true);
const state = { t: 0, lens: 0, dots: false, selected: -1, zoom: 1, cx: .5, cy: .28, follow: false };
let pressure, gl, world, warp, n, program, uniforms, meshVAO, meshIndexCount, edgesVAO, edgeCount, dotsVAO;
let unitPositions, labels, textures = [], width = 1, height = 1, dpr = 1, fit = 1;
let ready = false, dirty = true, raf = 0, leg = null, cameraLeg = null, pointers = new Map(), lastPointer = null;
let selectionBox = { width: 0, height: 0 };
let paper = [244 / 255, 248 / 255, 249 / 255];

const vertexSource = `#version 300 es
precision highp float;
layout(location=0) in vec2 a_uv;
uniform sampler2D u_warp;
uniform int u_resolution;
uniform float u_progress;
uniform vec4 u_view;
uniform float u_pointSize;
out vec2 v_uv;
flat out int v_id;
vec2 warpAt(vec2 uv) {
  float n=float(u_resolution);
  vec2 p=clamp(uv*n,vec2(0.),vec2(n-.0001));
  ivec2 i=ivec2(floor(p)); vec2 f=fract(p);
  vec2 a=texelFetch(u_warp,i,0).rg,b=texelFetch(u_warp,i+ivec2(1,0),0).rg;
  vec2 c=texelFetch(u_warp,i+ivec2(1,1),0).rg,d=texelFetch(u_warp,i+ivec2(0,1),0).rg;
  return f.x>=f.y ? a*(1.-f.x)+b*(f.x-f.y)+c*f.y : a*(1.-f.y)+c*f.x+d*(f.y-f.x);
}
void main(){
  float lat=2.*atan(exp((.5-a_uv.y)*6.28318530718))-1.57079632679;
  vec2 source=vec2(a_uv.x,.28-lat/3.14159265359*.5);
  vec2 target=warpAt(a_uv)*vec2(1.,.56);
  vec2 p=mix(source,target,u_progress);
  gl_Position=vec4(p*u_view.xy+u_view.zw,0.,1.);
  gl_PointSize=u_pointSize;
  v_uv=a_uv;v_id=gl_VertexID;
}`;

const fragmentSource = `#version 300 es
precision highp float;
precision highp int;
in vec2 v_uv;
flat in int v_id;
uniform sampler2D u_atlas;
uniform sampler2D u_palette;
uniform sampler2D u_units;
uniform vec3 u_paper;
uniform int u_mode;
uniform int u_lens;
uniform int u_selected;
uniform bool u_dots;
uniform float u_progress;
out vec4 colour;
ivec3 atlas(vec2 uv){return ivec3(floor(texture(u_atlas,clamp(uv,vec2(0.),vec2(.999999))).rgb*255.+.5));}
vec3 heat(float value){
  if(value<.001)return vec3(.69,.71,.71);
  float v=clamp((value*255.-1.)/254.,0.,1.);
  vec3 blue=vec3(.263,.498,.667),mid=vec3(.929,.941,.918),red=vec3(.729,.325,.298);
  return v<.5 ? mix(blue,mid,v*2.) : mix(mid,red,(v-.5)*2.);
}
void main(){
  ivec3 a=atlas(v_uv); int id=a.r+a.g*256; int country=a.b;
  if(u_mode==2){id=v_id;}
  vec4 unit=texelFetch(u_units,ivec2(id%128,id/128),0);
  if(u_mode==2)country=int(floor(unit.b*255.+.5));
  vec3 region=texelFetch(u_palette,ivec2(country,0),0).rgb;
  vec3 base=u_lens==0?region:heat(u_lens==1?unit.r:unit.g);
  if(u_mode==2){
    float d=length(gl_PointCoord-vec2(.5));
    float alpha=1.-smoothstep(.35,.5,d);
    if(id==u_selected)base=vec3(.13,.27,.44);
    colour=vec4(base*.77,alpha*.95);return;
  }
  if(u_mode==1){
    if(country==0)discard;
    float alpha=.28;
    if(id==u_selected)alpha=.8;
    colour=vec4(.18,.26,.29,alpha);return;
  }
  if(country==0){colour=vec4(u_paper,1.);return;}
  if(u_dots)base=mix(u_paper,base,u_lens==0?.29:.52);
  else base=mix(u_paper,base,.86);
  vec2 dx=dFdx(v_uv)*.65,dy=dFdy(v_uv)*.65;
  bool boundary=atlas(v_uv+dx).b!=country||atlas(v_uv-dx).b!=country||atlas(v_uv+dy).b!=country||atlas(v_uv-dy).b!=country;
  if(boundary)base=mix(base,u_paper,.7);
  if(id==u_selected)base=mix(base,vec3(.99,.77,.29),.62);
  colour=vec4(base,1.);
}`;

function compile(type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source); gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
  return shader;
}

function makeTexture(slot, internal, w, h, format, type, data) {
  const texture = gl.createTexture(); textures[slot] = texture;
  gl.activeTexture(gl.TEXTURE0 + slot); gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, format, type, data);
}

function makeVAO(data) {
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  return vao;
}

function makeRenderer(atlasImage, edgeData) {
  gl = canvas.getContext('webgl2', { alpha: false, antialias: true, preserveDrawingBuffer: true });
  if (!gl) throw new Error('This interactive map needs a browser with WebGL 2 enabled.');
  program = gl.createProgram();
  gl.attachShader(program, compile(gl.VERTEX_SHADER, vertexSource));
  gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource)); gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  uniforms = Object.fromEntries(['warp','atlas','palette','units','resolution','progress','view','pointSize','paper','mode','lens','selected','dots'].map(k => [k,gl.getUniformLocation(program,`u_${k}`)]));
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
  makeTexture(0, gl.RG32F, n + 1, n + 1, gl.RG, gl.FLOAT, warp);
  makeTexture(1, gl.RGB8, atlasImage.width, atlasImage.height, gl.RGB, gl.UNSIGNED_BYTE, atlasImage);
  const palette = new Uint8Array(256 * 3);
  world.countries.forEach((c, i) => palette.set(c.colour, i * 3));
  makeTexture(2, gl.RGB8, 256, 1, gl.RGB, gl.UNSIGNED_BYTE, palette);
  const unitData = new Uint8Array(128 * 64 * 4);
  const encode = ratio => ratio === null || ratio <= 0 ? 0 : Math.round(1 + 254 * Math.max(0, Math.min(1, (Math.log2(ratio) + 2) / 4)));
  world.units.forEach((u, i) => unitData.set([encode(u.ratio),encode(u.history),u.country,255], i * 4));
  makeTexture(3, gl.RGBA8, 128, 64, gl.RGBA, gl.UNSIGNED_BYTE, unitData);
  ['warp','atlas','palette','units'].forEach((k,i) => gl.uniform1i(uniforms[k], i));
  gl.uniform1i(uniforms.resolution, n);
  const mesh = new Float32Array((n+1)*(n+1)*2);
  for (let row=0;row<=n;row++) for (let col=0;col<=n;col++) {
    const k=2*(row*(n+1)+col);mesh[k]=col/n;mesh[k+1]=row/n;
  }
  meshVAO=makeVAO(mesh);
  const indices=new Uint32Array(n*n*6);let cursor=0;
  for (let row=0;row<n;row++) for (let col=0;col<n;col++) {
    const a=row*(n+1)+col,b=a+1,d=a+n+1,c=d+1;
    indices.set([a,b,c,a,c,d],cursor);cursor+=6;
  }
  meshIndexCount=indices.length;
  const ebo=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ebo);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);
  edgesVAO=makeVAO(edgeData);edgeCount=edgeData.length/2;
  dotsVAO=makeVAO(new Float32Array(world.units.flatMap(u=>u.uv)));
  gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  gl.disable(gl.DEPTH_TEST);
  const swatch=document.createElement('canvas');swatch.width=swatch.height=1;
  const colourContext=swatch.getContext('2d');colourContext.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--paper');colourContext.fillRect(0,0,1,1);
  paper=[...colourContext.getImageData(0,0,1,1).data].slice(0,3).map(v=>v/255);
}

function currentCentre() {
  if (state.follow && state.selected >= 0) {
    const p=interpolate(unitPositions[state.selected], state.t);
    if(width<600){
      const targetY=Math.min(height-32,Math.max(height/2,selectionBox.height+32));
      p[1]-=(targetY-height/2)/(fit*state.zoom);
    }
    return p;
  }
  return [state.cx, state.cy];
}

function screen(p) {
  const [cx,cy]=currentCentre(),scale=fit*state.zoom;
  return [width/2+(p[0]-cx)*scale,height/2+(p[1]-cy)*scale];
}

function resize() {
  width=stage.clientWidth;height=stage.clientHeight;dpr=Math.min(devicePixelRatio||1,2);
  canvas.width=overlay.width=Math.round(width*dpr);canvas.height=overlay.height=Math.round(height*dpr);
  fit=Math.min((width-18)/1.02,(height-40)/.56);
  if(ready&&state.selected>=0)updateSelection();
  requestRender();
}

function render() {
  if (!ready) return;
  gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(...paper,1);gl.clear(gl.COLOR_BUFFER_BIT);
  gl.useProgram(program);
  const [cx,cy]=currentCentre(), k=fit*state.zoom;
  gl.uniform4f(uniforms.view,2*k/width,-2*k/height,-2*cx*k/width,2*cy*k/height);
  gl.uniform1f(uniforms.progress,state.t);gl.uniform1i(uniforms.lens,state.lens);
  gl.uniform1i(uniforms.selected,state.selected);gl.uniform1i(uniforms.dots,state.dots?1:0);
  gl.uniform3f(uniforms.paper,...paper);
  gl.uniform1f(uniforms.pointSize,(state.dots?2.8:1.8)*dpr*Math.pow(state.zoom,.36));
  textures.forEach((tex,i)=>{gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,tex);});
  gl.uniform1i(uniforms.mode,0);gl.bindVertexArray(meshVAO);gl.drawElements(gl.TRIANGLES,meshIndexCount,gl.UNSIGNED_INT,0);
  if (!state.dots) {
    gl.uniform1i(uniforms.mode,1);gl.bindVertexArray(edgesVAO);gl.drawArrays(gl.LINES,0,edgeCount);
  }
  if (state.dots || state.zoom>2) {
    gl.uniform1i(uniforms.mode,2);gl.bindVertexArray(dotsVAO);gl.drawArrays(gl.POINTS,0,world.unitCount);
  }
  drawLabels();
  stage.dataset.progress=state.t.toFixed(4);
  stage.dataset.selectedUnit=state.selected;
  stage.dataset.unitCount=world.unitCount;
  stage.dataset.lens=state.lens;
  stage.dataset.zoom=state.zoom.toFixed(3);
}

function drawLabels() {
  hud.setTransform(dpr,0,0,dpr,0,0);hud.clearRect(0,0,width,height);
  const boxes=[];
  if(state.selected>=0)boxes.push([0,0,selectionBox.width+20,selectionBox.height+24]);
  const drawLabel=(label,city=false)=>{
    const [x,y]=screen(interpolate(label.position,state.t));
    const size=city?10:(width<600?8.5:10.5);
    hud.font=`${city?400:550} ${size}px Chivo, sans-serif`;
    const tw=hud.measureText(label.name).width;
    const b=[x-tw/2-4,y-size/2-5,x+tw/2+4,y+size/2+5];
    if(b[0]<5||b[2]>width-5||b[1]<6||b[3]>height-28)return;
    if(boxes.some(o=>b[0]<o[2]&&b[2]>o[0]&&b[1]<o[3]&&b[3]>o[1]))return;
    boxes.push(b);hud.textAlign='center';hud.textBaseline='middle';
    hud.lineWidth=3;hud.strokeStyle=`rgba(${paper.map(v=>Math.round(v*255)).join(',')},.78)`;
    hud.strokeText(label.name,x,y);hud.fillStyle=city?'#3c535d':'#364c54';hud.fillText(label.name,x,y);
  };
  labels.filter(l=>!l.city).forEach(l=>drawLabel(l));
  if(state.zoom>1.9)labels.filter(l=>l.city).forEach(l=>drawLabel(l,true));
  if(state.selected>=0){
    const p=unitPositions[state.selected],pos=screen(interpolate(p,state.t));
    if(!state.follow && state.t>.03){
      const origin=screen([p[0],p[1]]);
      hud.beginPath();hud.setLineDash([2,4]);hud.moveTo(...origin);hud.lineTo(...pos);
      hud.strokeStyle='rgba(34,70,100,.4)';hud.lineWidth=1;hud.stroke();hud.setLineDash([]);
      hud.beginPath();hud.arc(...origin,3,0,Math.PI*2);hud.stroke();
    }
    hud.beginPath();hud.arc(...pos,9,0,Math.PI*2);hud.fillStyle='rgba(250,208,107,.3)';hud.fill();
    hud.lineWidth=2;hud.strokeStyle='#254b67';hud.stroke();
    hud.beginPath();hud.arc(...pos,2.5,0,Math.PI*2);hud.fillStyle='#254b67';hud.fill();
  }
}

function requestRender(){dirty=true;if(!raf)raf=requestAnimationFrame(tick);}

function updateProgress(t){
  state.t=Math.max(0,Math.min(1,t));range.value=Math.round(state.t*1000);
  range.style.setProperty('--progress',`${state.t*100}%`);
  range.setAttribute('aria-valuetext',`${Math.round(state.t*100)}% transformed${state.t===0?', geography':state.t===1?', human space':''}`);
  requestRender();
}

function tick(now){
  raf=0;
  if(leg){
    if(now>=leg.start){
      const elapsed=Math.min(.1,Math.max(0,(now-leg.last)/1000));
      leg.last=now;
      updateProgress(advanceMotion(state.t,leg.to,elapsed,pressure));
      if(state.t===leg.to){
        if(leg.loop)leg={to:1-leg.to,start:now+1400,last:now+1400,loop:true};
        else leg=null;
      }
    }
  }
  if(cameraLeg){
    const u=Math.min(1,(now-cameraLeg.start)/cameraLeg.duration),q=ease(u);
    state.zoom=cameraLeg.from+(cameraLeg.to-cameraLeg.from)*q;
    dirty=true;if(u>=1)cameraLeg=null;
  }
  if(dirty){dirty=false;render();}
  if((leg||cameraLeg)&&!raf)raf=requestAnimationFrame(tick);
}

function playbackUI(playing){
  $('play').setAttribute('aria-pressed',String(playing));
  $('play').setAttribute('aria-label',reducedMotion.matches?'Step to the other view':playing?'Pause animation':'Play the transformation');
  $('play-text').textContent=reducedMotion.matches?'Change view':playing?'Pause':'Watch it unfold';
  $('play-icon').innerHTML=playing?'<path d="M6 5h4v14H6zm8 0h4v14h-4Z"/>':'<path d="m9 5 11 7-11 7Z"/>';
}

function pause(){leg=null;playbackUI(false);}
function goTo(t){
  if(!ready)return;pause();
  if(reducedMotion.matches)updateProgress(t);
  else {const now=performance.now();leg={to:t,start:now,last:now,loop:false};requestRender();}
}
function togglePlay(){
  if(!ready)return;
  if(reducedMotion.matches){pause();updateProgress(state.t<.5?1:0);return;}
  if(leg?.loop){pause();return;}
  const to=state.t>.999?0:1;
  const now=performance.now();leg={to,start:now,last:now,loop:true};
  playbackUI(true);requestRender();
}

function detachCamera(){
  if(state.follow){[state.cx,state.cy]=currentCentre();state.follow=false;}
  cameraLeg=null;
}

function changeZoom(factor,px=width/2,py=height/2){
  if(!ready)return;detachCamera();
  const old=state.zoom,next=Math.max(1,Math.min(18,old*factor));
  state.cx+=(px-width/2)/fit*(1/old-1/next);
  state.cy+=(py-height/2)/fit*(1/old-1/next);
  state.zoom=next;
  if(next===1){state.cx=.5;state.cy=.28;}
  requestRender();
}

function resetView(){detachCamera();state.zoom=1;state.cx=.5;state.cy=.28;requestRender();}

function selectUnit(id,follow=false){
  if(!ready)return;
  if(id<0){detachCamera();state.selected=-1;$('selection').hidden=true;document.querySelectorAll('#places button').forEach(b=>b.setAttribute('aria-pressed','false'));requestRender();return;}
  state.selected=id;
  $('selection-more').open=false;
  follow=follow||width<600;
  if(follow){
    state.follow=true;
    if(reducedMotion.matches)state.zoom=3;
    else cameraLeg={from:state.zoom,to:3,start:performance.now(),duration:850};
  }
  updateSelection();requestRender();
}

function comparison(ratio){
  const fractions=[[.2,'a fifth'],[.25,'a quarter'],[1/3,'a third'],[.5,'half'],[.75,'three quarters']];
  for(const [value,label] of fractions)if(Math.abs(ratio/value-1)<=.1)return `About ${label} of the world average.`;
  if(ratio>=.95&&ratio<=1.05)return 'About the world average.';
  if(ratio<1)return `About ${new Intl.NumberFormat('en-GB',{maximumSignificantDigits:1}).format(ratio*100)}% of the world average.`;
  return `About ${new Intl.NumberFormat('en-GB',{maximumSignificantDigits:2}).format(ratio)}× the world average.`;
}

function updateSelection(){
  const u=world.units[state.selected];if(!u)return;
  $('selection').hidden=false;
  $('selection-place').textContent=u.country?world.countries[u.country].name:'Coastal population';
  let text;
  const more=$('selection-more');
  more.hidden=state.lens!==1;
  if(state.lens===0){
    const number=new Intl.NumberFormat('en-GB',{maximumSignificantDigits:u.expansion>=10?1:2});
    text=u.expansion>=.9&&u.expansion<=1.1?'About the same size in both views.':u.expansion>1?`About ${number.format(u.expansion)}× its geographic size.`:`About ${new Intl.NumberFormat('en-GB',{maximumSignificantDigits:1}).format(100*u.expansion)}% of its geographic size.`;
  }else{
    const ratio=state.lens===1?u.ratio:u.history;
    text=ratio===null?'No estimate for this area.':comparison(ratio);
    if(state.lens===1){
      $('selection-value').textContent=u.output===null?'No estimate for this area.':`$${u.output.toLocaleString('en-GB')} per person in 2015, adjusted for purchasing power (constant 2011 international dollars).`;
    }
  }
  $('selection-detail').textContent=text;
  selectionBox={width:$('selection').offsetWidth,height:$('selection').offsetHeight};
  document.querySelectorAll('#places button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.unit)===state.selected)));
}

function nearestUnit(px,py,limit=32){
  let best=-1,distance=limit*limit;
  for(let i=0;i<unitPositions.length;i++){
    const [x,y]=screen(interpolate(unitPositions[i],state.t));
    const d=(x-px)**2+(y-py)**2;if(d<distance){best=i;distance=d;}
  }
  return best;
}

function setLens(lens){
  state.lens=lens;
  document.querySelectorAll('[data-lens]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.lens)===lens)));
  $('colour-legend').hidden=lens===0;
  $('lens-description').hidden=lens===0;
  $('lens-description').textContent=['','Economic output per person, 2015.','Economic output compared with where people have lived throughout history.'][lens];
  $('legend-meaning').textContent=lens===1?'Blue: less output per person. Red: more. Grey: no estimate.':'Blue: a smaller share of output than of lived years. Red: a larger share. Grey: no estimate.';
  $('selection-more').open=false;
  if(state.selected>=0)updateSelection();requestRender();
}

function setDots(dots){
  state.dots=dots;$('dots').setAttribute('aria-pressed',String(dots));$('cells').setAttribute('aria-pressed',String(!dots));
  $('unit-key').textContent=`1 ${dots?'dot':'cell'} ≈ 1 million people`;
  document.querySelector('.key-cell').classList.toggle('dots',dots);requestRender();
}

function wireControls(){
  $('play').addEventListener('click',togglePlay);
  $('to-geography').addEventListener('click',()=>goTo(0));$('to-human').addEventListener('click',()=>goTo(1));
  range.addEventListener('input',()=>{pause();updateProgress(Number(range.value)/1000);});
  $('cells').addEventListener('click',()=>setDots(false));$('dots').addEventListener('click',()=>setDots(true));
  document.querySelectorAll('[data-lens]').forEach(b=>b.addEventListener('click',()=>setLens(Number(b.dataset.lens))));
  $('zoom-in').addEventListener('click',()=>changeZoom(1.5));$('zoom-out').addEventListener('click',()=>changeZoom(1/1.5));$('zoom-reset').addEventListener('click',resetView);
  $('clear-selection').addEventListener('click',()=>selectUnit(-1));
  $('selection-more').addEventListener('toggle',()=>{selectionBox={width:$('selection').offsetWidth,height:$('selection').offsetHeight};requestRender();});
  world.places.forEach(place=>{
    const button=document.createElement('button');button.textContent=place.name;button.dataset.unit=place.unit;button.setAttribute('aria-pressed','false');
    button.addEventListener('click',()=>selectUnit(place.unit,true));$('places').append(button);
  });
  document.querySelector('.about-link').addEventListener('click',()=>{$('reading-the-map').open=true;});
  canvas.addEventListener('wheel',e=>{e.preventDefault();const r=canvas.getBoundingClientRect();changeZoom(Math.exp(-Math.max(-150,Math.min(150,e.deltaY))*.004),e.clientX-r.left,e.clientY-r.top);},{passive:false});
  canvas.addEventListener('pointerdown',e=>{
    const r=canvas.getBoundingClientRect();pointers.set(e.pointerId,{x:e.clientX-r.left,y:e.clientY-r.top});
    lastPointer={x:e.clientX,y:e.clientY,moved:false};canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');
  });
  canvas.addEventListener('pointermove',e=>{
    if(!pointers.has(e.pointerId))return;
    const r=canvas.getBoundingClientRect(),next={x:e.clientX-r.left,y:e.clientY-r.top},previous=pointers.get(e.pointerId);
    if(pointers.size===2){
      const other=[...pointers.entries()].find(([id])=>id!==e.pointerId)[1];
      const before=Math.hypot(previous.x-other.x,previous.y-other.y),after=Math.hypot(next.x-other.x,next.y-other.y);
      if(before>1)changeZoom(after/before,(next.x+other.x)/2,(next.y+other.y)/2);
    }else{
      detachCamera();state.cx-=(next.x-previous.x)/(fit*state.zoom);state.cy-=(next.y-previous.y)/(fit*state.zoom);
    }
    pointers.set(e.pointerId,next);if(Math.hypot(e.clientX-lastPointer.x,e.clientY-lastPointer.y)>5)lastPointer.moved=true;requestRender();
  });
  const endPointer=e=>{
    if(e.type==='pointerup'&&pointers.size===1&&!lastPointer?.moved){
      const r=canvas.getBoundingClientRect(),id=nearestUnit(e.clientX-r.left,e.clientY-r.top);
      if(id>=0)selectUnit(id);
    }
    pointers.delete(e.pointerId);if(!pointers.size){canvas.classList.remove('dragging');lastPointer=null;}
  };
  canvas.addEventListener('pointerup',endPointer);canvas.addEventListener('pointercancel',endPointer);
  canvas.addEventListener('keydown',e=>{
    if(['+','=','-','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Enter',' ','Escape'].includes(e.key))e.preventDefault();
    if(e.key==='+'||e.key==='=')changeZoom(1.5);
    else if(e.key==='-')changeZoom(1/1.5);
    else if(e.key===' ')togglePlay();
    else if(e.key==='Escape')selectUnit(-1);
    else if(e.key==='Enter'){const id=nearestUnit(width/2,height/2,Infinity);if(id>=0)selectUnit(id);}
    else if(e.key.startsWith('Arrow')){
      detachCamera();const d=.06/state.zoom;
      if(e.key==='ArrowLeft')state.cx-=d;if(e.key==='ArrowRight')state.cx+=d;if(e.key==='ArrowUp')state.cy-=d;if(e.key==='ArrowDown')state.cy+=d;requestRender();
    }
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden){pause();cameraLeg=null;}});
  reducedMotion.addEventListener('change',()=>{pause();cameraLeg=null;requestRender();});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();pause();showError(new Error('The graphics connection was interrupted. Reload to redraw the map.'));});
  new ResizeObserver(resize).observe(stage);
  document.fonts.ready.then(requestRender);
}

function showError(error){
  ready=false;$('loading').hidden=true;$('load-error').hidden=false;stage.setAttribute('aria-busy','false');
  $('error-detail').textContent=error.message.includes('WebGL')||error.message.includes('graphics')?error.message:'Check the connection, then try loading the map again.';
  controls.forEach(b=>b.disabled=true);range.disabled=true;console.error(error);
}

async function fetchAsset(name,type){
  const response=await fetch(new URL(name,import.meta.url));
  if(!response.ok)throw new Error(`Map asset ${name} returned ${response.status}`);
  return type==='json'?response.json():type==='image'?createImageBitmap(await response.blob()):response.arrayBuffer();
}

$('retry').addEventListener('click',()=>location.reload());
try {
  const [metadata,warpBuffer,atlasImage,edgeBuffer,motion]=await Promise.all([
    fetchAsset('world.json','json'),fetchAsset('warp.bin'),fetchAsset('atlas.png','image'),fetchAsset('edges.bin'),fetchAsset('motion.json','json')
  ]);
  world=metadata;warp=new Float32Array(warpBuffer);n=world.projection.meshResolution;
  pressure=motion.pressure;
  if(!Array.isArray(pressure)||pressure.length<2||!pressure.every(p=>Number.isFinite(p)&&p>=0))throw new Error('Incomplete motion data');
  if(warp.length!==(n+1)*(n+1)*2||world.unitCount!==world.units.length)throw new Error('Incomplete map data');
  unitPositions=world.units.map(u=>endpoints(u.uv,warp,n));
  labels=[...world.labels.map(l=>({...l,position:endpoints(l.uv,warp,n),city:false})),...world.cities.map(l=>({...l,position:endpoints(l.uv,warp,n),city:true}))];
  makeRenderer(atlasImage,new Float32Array(edgeBuffer));atlasImage.close();ready=true;
  wireControls();resize();playbackUI(false);updateProgress(0);
  $('loading').hidden=true;stage.setAttribute('aria-busy','false');controls.forEach(b=>b.disabled=false);range.disabled=false;
} catch(error){showError(error);}
