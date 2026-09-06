// Repulsive pressure sets the rate of exponential settling. All geometry uses
// the same collective coordinate, so averaging cannot separate the map layers.
export function pressureAt(position, pressure) {
  const x=Math.max(0,Math.min(1,position))*(pressure.length-1);
  const i=Math.min(pressure.length-2,Math.floor(x)), fraction=x-i;
  return pressure[i]*(1-fraction)+pressure[i+1]*fraction;
}

export function advanceMotion(position,target,seconds,pressure) {
  const steps=Math.max(1,Math.ceil(seconds*240)),dt=seconds/steps;
  for(let i=0;i<steps;i++) {
    const rate=1.3+5.7*Math.sqrt(Math.max(0,pressureAt(position,pressure)));
    position=target+(position-target)*Math.exp(-rate*dt);
  }
  return Math.abs(position-target)<.00025?target:position;
}
