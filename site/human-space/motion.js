// Repulsive pressure sets the rate of exponential settling. All geometry uses
// the same collective coordinate, so averaging cannot separate the map layers.
export function pressureAt(position, pressure) {
  const x=Math.max(0,Math.min(1,position))*(pressure.length-1);
  const i=Math.min(pressure.length-2,Math.floor(x)), fraction=x-i;
  return pressure[i]*(1-fraction)+pressure[i+1]*fraction;
}

// Preserve collective velocity when the destination changes. Each short step
// uses the closed-form critically damped response for the local pressure.
export function advanceMotion(position,velocity,target,seconds,pressure) {
  const steps=Math.max(1,Math.ceil(seconds*240)),dt=seconds/steps;
  for(let i=0;i<steps;i++) {
    const frequency=7+Math.sqrt(Math.max(0,pressureAt(position,pressure)));
    const speedLimit=.32;
    const offset=position-target,combined=velocity+frequency*offset;
    const decay=Math.exp(-frequency*dt);
    const desiredVelocity=Math.max(-speedLimit,Math.min(speedLimit,(velocity-frequency*combined*dt)*decay));
    const previousVelocity=velocity;
    // Bound acceleration as well as speed, so leaving either endpoint glides.
    velocity+=Math.max(-1.6*dt,Math.min(1.6*dt,desiredVelocity-velocity));
    position+=(previousVelocity+velocity)*.5*dt;
    if(position<0||position>1){position=Math.max(0,Math.min(1,position));velocity=0;}
  }
  if(Math.abs(position-target)<.00025&&Math.abs(velocity)<.001)return {position:target,velocity:0};
  return {position,velocity};
}
