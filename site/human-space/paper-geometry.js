import { geography, sampleWarp } from './geometry.js';

export const southLimit=.5-Math.log(Math.tan(Math.PI/4-Math.PI/6))/(2*Math.PI);

export function isFrameEdge(x,y,xx,yy){
  return (x<1e-7&&xx<1e-7)||(x>1-1e-7&&xx>1-1e-7)||
    (y<1e-7&&yy<1e-7)||(y>1-1e-7&&yy>1-1e-7);
}

export function paperEndpoints(source, warp, n, pull) {
  const result=new Float64Array(source.length*3);
  for(let i=0;i<source.length;i+=2){
    const uv=[source[i],source[i+1]],a=geography(uv),b=sampleWarp(uv,warp,n);
    const c=pull?sampleWarp(uv,pull,n):a;
    result.set([a[0],a[1],b[0],b[1]*.56,c[0],c[1]],i*3);
  }
  return result;
}

export function populationCoasts(lines){
  const result=[];
  for(const line of lines){
    let part=[];
    for(const p of line){
      if(p[1]<=southLimit)part.push(p);
      else{if(part.length>1)result.push(part);part=[];}
    }
    if(part.length>1)result.push(part);
  }
  return result;
}

// Snap each label to one of its own sites, keeping it attached to its region.
export function labelAnchors(data) {
  return [1,2].map(mode=>{
    const buckets=new Map();
    data.sites.forEach((site,i)=>{
      const country=data.countries[data.country_ids[i]];
      const name=mode===1?country.name:country.continent;
      if(!buckets.has(name))buckets.set(name,[]);
      buckets.get(name).push(i);
    });
    return [...buckets].map(([name,ids])=>{
      const center=[0,1].map(c=>ids.reduce((sum,i)=>sum+data.sites[i][c],0)/ids.length);
      let best=ids[0],distance=Infinity;
      for(const i of ids){
        const d=(data.sites[i][0]-center[0])**2+(data.sites[i][1]-center[1])**2;
        if(d<distance){distance=d;best=i;}
      }
      return {name,index:best,count:ids.length};
    }).sort((a,b)=>b.count-a.count);
  });
}
