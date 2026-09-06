import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { advanceMotion } from '../site/human-space/motion.js';

const assets=new URL('../site/human-space/',import.meta.url);
const model=JSON.parse(readFileSync(new URL('motion.json',assets)));
const pressure=model.pressure;
const world=JSON.parse(readFileSync(new URL('world.json',assets)));
function run(from,to,seconds,hz) {
  let p=from;
  for(let elapsed=0;elapsed<seconds-1e-10;) {
    const dt=Math.min(1/hz,seconds-elapsed);
    p=advanceMotion(p,to,dt,pressure);elapsed+=dt;
  }
  return p;
}

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

test('Expansion releases most movement immediately and then settles',()=>{
  const early=run(0,1,.5,120),late=run(0,1,1.5,120);
  assert.ok(early>.75&&early<.95,'Most movement should happen in the first half second, with a visible settling tail');
  assert.ok(late>.99&&late<1,'Settling must slow before the final endpoint');
  assert.equal(run(0,1,3,120),1);
});

test('Expansion, collapse and interrupted targets stay bounded without jitter or overshoot',()=>{
  for(const from of [0,.1,.47,.9,1])for(const to of [0,1]) {
    let p=from;
    for(let i=0;i<480;i++) {
      const next=advanceMotion(p,to,1/120,pressure);
      assert.ok(Number.isFinite(next)&&next>=0&&next<=1);
      assert.ok(Math.abs(next-to)<=Math.abs(p-to));
      p=next;
    }
    assert.equal(p,to);
  }
  const interrupted=run(0,1,.15,120);
  assert.equal(run(interrupted,0,3,120),0);
});

test('Motion timing is consistent across display refresh rates',()=>{
  for(const to of [0,1])for(const seconds of [.1,.3,.7,1.2]) {
    const reference=run(1-to,to,seconds,120);
    for(const hz of [24,30,60,90,144])assert.ok(Math.abs(run(1-to,to,seconds,hz)-reference)<.003);
  }
});
