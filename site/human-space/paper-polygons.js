import {screenFabric} from './screen-fabric.js?v=992e1095c99a';
import {isFrameEdge, southLimit} from './paper-geometry.js?v=443f532c9617';
// GPU colour fills with the original Figure 6 vector boundaries.
export function createPaperPolygons(canvas,warp,n,image,data,sourceVertices,pull,landImage){
  const edges=new Float32Array(sourceVertices.length*2);let edgeCursor=0;
  for(let i=0;i<data.sites.length;i++){
    const a=data.offsets[i],b=data.offsets[i+1];
    for(let j=a;j<b;j++){
      const next=j+1===b?a:j+1;const segment=[sourceVertices[j*2],sourceVertices[j*2+1],sourceVertices[next*2],sourceVertices[next*2+1]];
      if(isFrameEdge(...segment))continue;edges.set(segment,edgeCursor);edgeCursor+=4;
    }
  }
  const gl=canvas.getContext('webgl2',{alpha:false,antialias:true});
  if(!gl)throw new Error('Polygon rendering requires WebGL 2.');
  const vs=`#version 300 es
precision highp float;
layout(location=0) in vec2 uv;
layout(location=1) in vec2 extension;
uniform sampler2D warp;
uniform sampler2D pullField;
uniform float gravity;
uniform float progress;
uniform vec4 view;
out vec2 source;
vec2 field(sampler2D tex){
  vec2 p=clamp(uv*${n}.,vec2(0.),vec2(${n}.-.0001));ivec2 i=ivec2(floor(p));vec2 f=fract(p);
  vec2 a=texelFetch(tex,i,0).rg,b=texelFetch(tex,i+ivec2(1,0),0).rg,c=texelFetch(tex,i+ivec2(1,1),0).rg,d=texelFetch(tex,i+ivec2(0,1),0).rg;
  return f.x>=f.y?a*(1.-f.x)+b*(f.x-f.y)+c*f.y:a*(1.-f.y)+c*f.x+d*(f.y-f.x);
}
void main(){
  float lat=2.*atan(exp((.5-uv.y)*6.28318530718))-1.57079632679;
  vec2 geography=vec2(uv.x,.28-lat/3.14159265359*.5);
  vec2 target=mix(field(warp)*vec2(1.,.56),field(pullField),gravity);
  vec2 position=mix(geography,target,progress)+extension;
  gl_Position=vec4(position*view.xy+view.zw,0.,1.);source=uv;
}`;
  const fs=`#version 300 es
precision highp float;
precision highp int;
in vec2 source;
uniform sampler2D atlas;
uniform sampler2D colours;
uniform sampler2D land;
uniform sampler2D regionColours;
uniform int mode;
uniform bool lines;
uniform bool extended;
uniform bool dots;
out vec4 pixel;
ivec3 sampleAt(vec2 p){return ivec3(floor(texture(atlas,clamp(p,vec2(0.),vec2(.999999))).rgb*255.+.5));}
int cellAt(vec2 p){ivec3 c=sampleAt(p);return c.r+c.g*256;}
void main(){
  if(!extended&&source.y>${southLimit})discard;
  vec3 landSample=texture(land,clamp(source,vec2(0.),vec2(.999999))).rgb;
  if(!lines&&(extended||landSample.r<.5)){
    pixel=vec4(217./255.,236./255.,246./255.,1.);return;
  }
  ivec3 c=sampleAt(source);int id=c.r+c.g*256;
  int region=max(0,int(floor(landSample.g*255.+.5))-1);
  vec3 colour=mode==0||dots?vec3(1.):texelFetch(regionColours,ivec2(region,mode-1),0).rgb;
  if(mode!=0)colour=mix(colour,vec3(1.),.55);
  if(lines)colour=vec3(0.);
  pixel=vec4(colour,1.);
}`;
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
  const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  function texture(slot,w,h,internal,format,type,data){
    const t=gl.createTexture();gl.activeTexture(gl.TEXTURE0+slot);gl.bindTexture(gl.TEXTURE_2D,t);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,internal,w,h,0,format,type,data);
  }
  gl.pixelStorei(gl.UNPACK_ALIGNMENT,1);gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.NONE);
  texture(0,n+1,n+1,gl.RG32F,gl.RG,gl.FLOAT,warp);
  texture(1,image.width,image.height,gl.RGB8,gl.RGB,gl.UNSIGNED_BYTE,image);
  const colours=new Uint8Array(data.sites.length*2*3);
  for(let row=0;row<2;row++)data.country_ids.forEach((country,i)=>colours.set(data.countries[country][row?'continental':'country'],(row*data.sites.length+i)*3));
  texture(2,128,128,gl.RGB8,gl.RGB,gl.UNSIGNED_BYTE,colours);
  texture(3,n+1,n+1,gl.RG32F,gl.RG,gl.FLOAT,pull);
  texture(4,landImage.width,landImage.height,gl.RGB8,gl.RGB,gl.UNSIGNED_BYTE,landImage);
  const regionColours=new Uint8Array(256*2*3);
  for(let row=0;row<2;row++)data.countries.forEach((country,i)=>regionColours.set(country[row?'continental':'country'],(row*256+i)*3));
  texture(5,256,2,gl.RGB8,gl.RGB,gl.UNSIGNED_BYTE,regionColours);
  ['warp','atlas','colours','pullField','land','regionColours'].forEach((name,i)=>gl.uniform1i(gl.getUniformLocation(program,name),i));
  const vertices=new Float32Array((n+1)**2*2),indices=new Uint32Array(n*n*6);let cursor=0;
  for(let y=0;y<=n;y++)for(let x=0;x<=n;x++){const i=y*(n+1)+x;vertices[2*i]=x/n;vertices[2*i+1]=y/n;if(x<n&&y<n){indices.set([i,i+1,i+n+2,i,i+n+2,i+n+1],cursor);cursor+=6;}}
  const vao=gl.createVertexArray();gl.bindVertexArray(vao);
  const vbo=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vbo);gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
  const ebo=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ebo);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);
  const edgeVao=gl.createVertexArray();gl.bindVertexArray(edgeVao);
  const edgeBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferData(gl.ARRAY_BUFFER,edges.subarray(0,edgeCursor),gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
  const fabric=screenFabric(data,sourceVertices,n);
  function fabricVao(data){
    const vao=gl.createVertexArray();gl.bindVertexArray(vao);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,16,0);
    gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,2,gl.FLOAT,false,16,8);
    return vao;
  }
  const fabricFill=fabricVao(fabric.fill),fabricLines=fabricVao(fabric.lines);
  const extended=gl.getUniformLocation(program,'extended');
  const gravityLocation=gl.getUniformLocation(program,'gravity');
  const dotsLocation=gl.getUniformLocation(program,'dots');
  const lines=gl.getUniformLocation(program,'lines');
  const progressLocation=gl.getUniformLocation(program,'progress'),view=gl.getUniformLocation(program,'view'),mode=gl.getUniformLocation(program,'mode');
  return ({width,height,dpr,fit,zoom,cx,cy,progress,colourMode,gravity,immersive,representation})=>{
    const w=Math.round(width*dpr),h=Math.round(height*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    gl.viewport(0,0,w,h);gl.clearColor(1,1,1,1);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(program);gl.bindVertexArray(vao);
    const k=fit*zoom;gl.uniform4f(view,2*k/width,-2*k/height,-2*cx*k/width,2*cy*k/height);gl.uniform1f(progressLocation,progress);gl.uniform1f(gravityLocation,gravity);gl.uniform1i(mode,colourMode);
    gl.uniform1i(dotsLocation,representation==='dots');
    if(immersive){
      gl.uniform1i(extended,1);gl.uniform1i(lines,0);gl.bindVertexArray(fabricFill);gl.drawArrays(gl.TRIANGLES,0,fabric.fill.length/4);
      if(representation==='polygons'){gl.uniform1i(lines,1);gl.bindVertexArray(fabricLines);gl.drawArrays(gl.LINES,0,fabric.lines.length/4);}
    }
    gl.uniform1i(extended,0);gl.bindVertexArray(vao);
    gl.uniform1i(lines,0);gl.drawElements(gl.TRIANGLES,indices.length,gl.UNSIGNED_INT,0);
    if(representation==='polygons'){gl.bindVertexArray(edgeVao);gl.uniform1i(lines,1);gl.drawArrays(gl.LINES,0,edgeCursor/2);}
  };
}
