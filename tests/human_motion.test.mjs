import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { advanceMotion } from '../site/human-space/motion.js';

const assets=new URL('../site/human-space/',import.meta.url);
const model=JSON.parse(readFileSync(new URL('motion.json',assets)));
const pressure=model.pressure;
const world=JSON.parse(readFileSync(new URL('world.json',assets)));
function runState(from,to,seconds,hz,velocity=0) {
  let state={position:from,velocity};
  for(let elapsed=0;elapsed<seconds-1e-10;) {
    const dt=Math.min(1/hz,seconds-elapsed);
    state=advanceMotion(state.position,state.velocity,to,dt,pressure);elapsed+=dt;
  }
  return state;
}
function run(from,to,seconds,hz){return runState(from,to,seconds,hz).position;}

test('Repulsion timing belongs to the delivered population and geometry',()=>{
  for(const name of ['world','warp']) {
    const extension=name==='world'?'json':'bin';
    assert.equal(createHash('sha256').update(readFileSync(new URL(`${name}.${extension}`,assets))).digest('hex'),model[`${name}_sha256`]);
  }
  assert.equal(model.groups,world.unitCount);
  assert.ok(model.cloud_sigma>0&&model.softening>0);
  assert.ok(pressure.length>=32&&pressure.every(p=>Number.isFinite(p)&&p>=0&&p<=1));
  assert.ok(model.signed_pressure[0]>model.signed_pressure.at(-1));
});

test('Expansion gives the viewer time to follow the release and settling',()=>{
  const early=run(0,1,.5,120),late=run(0,1,4.25,120);
  assert.ok(run(0,1,.1,120)<.25,'The first movement should be gentle enough to follow');
  assert.ok(early>.1&&early<.18,'The capped peak speed should leave most movement ahead');
  assert.equal(late,1,'The short settling tail should finish within 4.25 seconds');
  assert.equal(run(0,1,8,120),1);
});

test('Expansion, collapse and interrupted targets stay bounded without jitter or overshoot',()=>{
  for(const from of [0,.1,.47,.9,1])for(const to of [0,1]) {
    let p=from,velocity=0;
    for(let i=0;i<1200;i++) {
      const result=advanceMotion(p,velocity,to,1/120,pressure);
      const next=result.position;velocity=result.velocity;
      assert.ok(Number.isFinite(next)&&next>=0&&next<=1);
      assert.ok(Math.abs(next-to)<=Math.abs(p-to));
      p=next;
    }
    assert.equal(p,to);
  }
  const interrupted=run(0,1,.15,120);
  assert.equal(run(interrupted,0,8,120),0);
});

test('Motion timing is consistent across display refresh rates',()=>{
  for(const to of [0,1])for(const seconds of [.1,.3,.7,1.2]) {
    const reference=run(1-to,to,seconds,120);
    for(const hz of [24,30,60,90,144])assert.ok(Math.abs(run(1-to,to,seconds,hz)-reference)<.003);
  }
});

test('A direction change preserves momentum before turning smoothly',()=>{
  const moving=runState(0,1,.7,120);
  assert.ok(moving.velocity>0);
  const reversed=runState(moving.position,0,.002,120,moving.velocity);
  assert.ok(reversed.position>moving.position,'The groups should carry briefly before reversing');
  assert.ok(reversed.velocity>0&&reversed.velocity<moving.velocity,'The opposing force should decelerate existing motion');
  assert.equal(runState(moving.position,0,9,120,moving.velocity).position,0);
  const stopped=advanceMotion(moving.position,0,moving.position,.1,pressure);
  assert.equal(stopped.position,moving.position);
  assert.equal(stopped.velocity,0);
});

 test('Both directions finish promptly with a restrained peak speed',()=>{
  for(const from of [0,1]){
    let state={position:from,velocity:0};
    for(let i=0;i<510;i++){
      state=advanceMotion(state.position,state.velocity,1-from,1/120,pressure);
      assert.ok(Math.abs(state.velocity)<=.320001);
    }
    assert.equal(state.position,1-from);
  }
});

test('Departures glide with bounded acceleration instead of jumping to cruising speed',()=>{
  for(const from of [0,1]){
    let state={position:from,velocity:0};
    for(let i=0;i<60;i++){
      const next=advanceMotion(state.position,state.velocity,1-from,1/120,pressure);
      assert.ok(Math.abs(next.velocity-state.velocity)<=1.60001/120);
      state=next;
    }
  }
});
