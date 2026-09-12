import { sampleWarp } from './geometry.js';

export function paperEndpoints(source, warp, n) {
  const result=new Float64Array(source.length*2);
  for(let i=0;i<source.length;i+=2){
    const x=source[i],y=source[i+1],b=sampleWarp([x,y],warp,n);
    result.set([x,y,b[0],b[1]],i*2);
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
