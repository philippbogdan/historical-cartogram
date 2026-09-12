// Render the same population-cell atlas through the shared deformation.
export function createPolygons(canvas,warp,n,image,units,palettes,edges){
  const gl=canvas.getContext('webgl2',{alpha:false,antialias:true});
  if(!gl)throw new Error('Polygon rendering requires WebGL 2.');
  const vs=`#version 300 es
precision highp float;
layout(location=0) in vec2 uv;
uniform sampler2D warp;
uniform float progress;
uniform vec4 view;
out vec2 source;
void main(){
  vec2 p=clamp(uv*${n}.,vec2(0.),vec2(${n}.-.0001));ivec2 i=ivec2(floor(p));vec2 f=fract(p);
  vec2 a=texelFetch(warp,i,0).rg,b=texelFetch(warp,i+ivec2(1,0),0).rg,c=texelFetch(warp,i+ivec2(1,1),0).rg,d=texelFetch(warp,i+ivec2(0,1),0).rg;
  vec2 target=f.x>=f.y?a*(1.-f.x)+b*(f.x-f.y)+c*f.y:a*(1.-f.y)+c*f.x+d*(f.y-f.x);
  float lat=2.*atan(exp((.5-uv.y)*6.28318530718))-1.57079632679;
  vec2 geography=vec2(uv.x,.28-lat/3.14159265359*.5);
  vec2 position=mix(geography,target*vec2(1.,.56),progress);
  gl_Position=vec4(position*view.xy+view.zw,0.,1.);source=uv;
}`;
  const fs=`#version 300 es
precision highp float;
precision highp int;
in vec2 source;
uniform sampler2D atlas;
uniform sampler2D colours;
uniform int mode;
uniform bool lines;
out vec4 pixel;
ivec3 sampleAt(vec2 p){return ivec3(floor(texture(atlas,clamp(p,vec2(0.),vec2(.999999))).rgb*255.+.5));}
int cellAt(vec2 p){ivec3 c=sampleAt(p);return c.r+c.g*256;}
void main(){
  ivec3 c=sampleAt(source);int id=c.r+c.g*256;
  if(c.b==0){if(lines)discard;pixel=vec4(1.);return;}
  vec3 colour=mode==0?vec3(1.):texelFetch(colours,ivec2(id%128,id/128+(mode-1)*64),0).rgb;
  if(lines)colour=mode==0?vec3(.15):mix(colour,vec3(1.),.8);
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
  const colours=new Uint8Array(units.length*2*3);
  for(let row=0;row<2;row++)units.forEach((u,i)=>colours.set(palettes.countries[u.country][row?'continental':'country'],(row*units.length+i)*3));
  texture(2,128,128,gl.RGB8,gl.RGB,gl.UNSIGNED_BYTE,colours);
  ['warp','atlas','colours'].forEach((name,i)=>gl.uniform1i(gl.getUniformLocation(program,name),i));
  const vertices=new Float32Array((n+1)**2*2),indices=new Uint32Array(n*n*6);let cursor=0;
  for(let y=0;y<=n;y++)for(let x=0;x<=n;x++){const i=y*(n+1)+x;vertices[2*i]=x/n;vertices[2*i+1]=y/n;if(x<n&&y<n){indices.set([i,i+1,i+n+2,i,i+n+2,i+n+1],cursor);cursor+=6;}}
  const vao=gl.createVertexArray();gl.bindVertexArray(vao);
  const vbo=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vbo);gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
  const ebo=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ebo);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);
  const edgeVao=gl.createVertexArray();gl.bindVertexArray(edgeVao);
  const edgeBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferData(gl.ARRAY_BUFFER,edges,gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
  const lines=gl.getUniformLocation(program,'lines');
  const progressLocation=gl.getUniformLocation(program,'progress'),view=gl.getUniformLocation(program,'view'),mode=gl.getUniformLocation(program,'mode');
  return ({width,height,dpr,fit,zoom,cx,cy,progress,colourMode})=>{
    const w=Math.round(width*dpr),h=Math.round(height*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    gl.viewport(0,0,w,h);gl.clearColor(1,1,1,1);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(program);gl.bindVertexArray(vao);
    const k=fit*zoom;gl.uniform4f(view,2*k/width,-2*k/height,-2*cx*k/width,2*cy*k/height);gl.uniform1f(progressLocation,progress);gl.uniform1i(mode,colourMode);
    gl.uniform1i(lines,0);gl.drawElements(gl.TRIANGLES,indices.length,gl.UNSIGNED_INT,0);
    gl.bindVertexArray(edgeVao);gl.uniform1i(lines,1);gl.drawArrays(gl.LINES,0,edges.length/2);
  };
}
