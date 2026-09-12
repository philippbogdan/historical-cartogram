import {isFrameEdge,southLimit} from './paper-geometry.js?v=443f532c9617';

// Continue the outer ocean cells past the viewport instead of exposing a cut edge.
export function screenFabric(data,source,n){
  const fill=[],lines=[],seen=new Set(),reach=4;
  const vertex=(uv,offset)=>[...uv,...offset];
  function strip(a,b,offset){
    const p=vertex(a,[0,0]),q=vertex(b,[0,0]),r=vertex(b,offset),s=vertex(a,offset);
    fill.push(...p,...q,...r,...p,...r,...s);
  }
  const u=new Set([0,1]);
  for(let i=0;i<n;i++){u.add(i/n);u.add((i+(southLimit*n)%1)/n);}
  const xs=[...u].sort((a,b)=>a-b);
  for(let i=1;i<xs.length;i++){
    strip([xs[i-1],0],[xs[i],0],[0,-reach]);
    strip([xs[i-1],southLimit],[xs[i],southLimit],[0,reach]);
  }
  for(let i=0;i<Math.ceil(southLimit*n);i++){
    const a=i/n,b=Math.min((i+1)/n,southLimit);
    strip([0,a],[0,b],[-reach,0]);strip([1,a],[1,b],[reach,0]);
  }
  for(const [x,y,dx,dy] of [[0,0,-reach,-reach],[1,0,reach,-reach],[0,southLimit,-reach,reach],[1,southLimit,reach,reach]]){
    const p=[x,y,0,0],q=[x,y,dx,0],r=[x,y,dx,dy],s=[x,y,0,dy];
    fill.push(...p,...q,...r,...p,...r,...s);
  }
  function extend(x,y,dx,dy){
    const key=[x,y,dx,dy].map(v=>v.toFixed(7)).join(',');
    if(seen.has(key))return;seen.add(key);
    lines.push(x,y,0,0,x,y,dx,dy);
  }
  for(let cell=0;cell<data.country_ids.length;cell++){
    const a=data.offsets[cell],b=data.offsets[cell+1];
    for(let j=a;j<b;j++){
      const k=j+1===b?a:j+1;
      const x=source[j*2],y=source[j*2+1],xx=source[k*2],yy=source[k*2+1];
      if(isFrameEdge(x,y,xx,yy))continue;
      if((y<southLimit)!==(yy<southLimit))extend(x+(xx-x)*(southLimit-y)/(yy-y),southLimit,0,reach);
      for(const [u,v] of [[x,y],[xx,yy]]){
        if(v>southLimit)continue;
        if(u<1e-7)extend(0,v,-reach,0);
        if(u>1-1e-7)extend(1,v,reach,0);
        if(v<1e-7)extend(u,0,0,-reach);
      }
    }
  }
  return {fill:new Float32Array(fill),lines:new Float32Array(lines)};
}
