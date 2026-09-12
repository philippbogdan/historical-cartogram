export function fadeLabel(opacity,visible,seconds,reducedMotion=false){
  const target=visible?1:0;
  if(reducedMotion)return target;
  const next=target+(opacity-target)*Math.exp(-Math.max(0,seconds)/.035);
  return Math.abs(next-target)<.01?target:next;
}
