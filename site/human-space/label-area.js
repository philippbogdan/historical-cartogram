import {southLimit} from './paper-geometry.js?v=443f532c9617';

// Clip against one half-plane. The signed area also works for concave regions.
function clip(polygon,axis,bound,keepGreater){
  const result=[];
  let a=polygon.at(-1),insideA=keepGreater?a[axis]>=bound:a[axis]<=bound;
  for(const b of polygon){
    const insideB=keepGreater?b[axis]>=bound:b[axis]<=bound;
    if(insideA!==insideB){
      const t=(bound-a[axis])/(b[axis]-a[axis]);
      result.push(a.map((v,i)=>v+(b[i]-v)*t));
    }
    if(insideB)result.push(b);
    a=b;insideA=insideB;
  }
  return result;
}

function area(polygon){
  let sum=0,a=polygon.at(-1);
  for(const b of polygon){sum+=a[0]*b[1]-b[0]*a[1];a=b;}
  return Math.abs(sum)/2;
}

export function labelFontSize(pixelArea,nameWidth){
  // Text dimensions follow region dimensions: quadruple the area, double the type.
  return .16*Math.sqrt(Math.max(0,pixelArea))/Math.max(1,nameWidth/5.5);
}

export function createRegionAreas(data,source,endpoints){
  const flat=[],offsets=[0];
  for(let cell=0;cell<data.country_ids.length;cell++){
    const polygon=[];
    for(let i=data.offsets[cell];i<data.offsets[cell+1];i++){
      polygon.push([source[i*2+1],...endpoints.subarray(i*6,i*6+6)]);
    }
    // Match the renderer's southern cutoff before measuring any region.
    const visible=clip(polygon,0,southLimit,false);
    for(const vertex of visible)flat.push(...vertex.slice(1));
    offsets.push(flat.length/6);
  }
  const positions=new Float64Array(flat),xy=new Float64Array(flat.length/3);
  const totals=new Float64Array(data.countries.length);
  return ({progress,gravity,scale,width,height,cx,cy})=>{
    const a=1-progress,b=progress*(1-gravity),c=progress*gravity;
    const left=cx-width/(2*scale),right=cx+width/(2*scale);
    const top=cy-height/(2*scale),bottom=cy+height/(2*scale);
    for(let i=0,j=0;i<positions.length;i+=6,j+=2){
      xy[j]=positions[i]*a+positions[i+2]*b+positions[i+4]*c;
      xy[j+1]=positions[i+1]*a+positions[i+3]*b+positions[i+5]*c;
    }
    totals.fill(0);
    for(let cell=0;cell<data.country_ids.length;cell++){
      const start=offsets[cell]*2,end=offsets[cell+1]*2;
      if(end-start<6)continue;
      let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity,sum=0;
      let ax=xy[end-2],ay=xy[end-1];
      for(let j=start;j<end;j+=2){
        const x=xy[j],y=xy[j+1];sum+=ax*y-x*ay;ax=x;ay=y;
        minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);
      }
      if(maxX<=left||minX>=right||maxY<=top||minY>=bottom)continue;
      let visibleArea=Math.abs(sum)/2;
      if(minX<left||maxX>right||minY<top||maxY>bottom){
        let polygon=[];
        for(let j=start;j<end;j+=2)polygon.push([xy[j],xy[j+1]]);
        for(const [axis,bound,greater] of [[0,left,true],[0,right,false],[1,top,true],[1,bottom,false]]){
          if(!polygon.length)break;
          polygon=clip(polygon,axis,bound,greater);
        }
        visibleArea=polygon.length>2?area(polygon):0;
      }
      totals[data.country_ids[cell]]+=visibleArea*scale*scale*(data.signs?.[cell]??1);
    }
    return totals;
  };
}
