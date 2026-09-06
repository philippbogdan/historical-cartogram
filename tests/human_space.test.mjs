import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const assets = `${root}site/human-space/`;
const world = JSON.parse(readFileSync(`${assets}world.json`));
const report = JSON.parse(readFileSync(`${assets}verification.json`));
const raw = readFileSync(`${assets}warp.bin`);
const warp = new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
const n = world.projection.meshResolution;

test('The population units actually contain the advertised amount of humanity', () => {
  const source=JSON.parse(readFileSync(`${assets}source-population-check.json`));
  assert.ok(source.source_triangles > world.unitCount, 'The source check must integrate finer geography than the displayed groups');
  assert.ok(source.max_relative_capacity_error < .0001, 'Capacities must agree with the original source pixels');
  assert.ok(Math.abs(source.integrated_population/source.source_population-1)<1e-8);
  assert.equal(world.unitCount, world.units.length);
  assert.equal(new Set(world.units.map(u => u.id)).size, world.unitCount);
  let sum = 0;
  for (const u of world.units) {
    assert.ok(u.people >= 998000 && u.people <= 1002000, `Cell ${u.id} has ${u.people} people`);
    assert.ok(u.uv.length === 2 && u.uv.every(v => Number.isFinite(v) && v >= 0 && v <= 1));
    assert.ok(Number.isInteger(u.country) && world.countries[u.country]);
    sum += u.people;
  }
  assert.ok(Math.abs(sum - world.peopleTotal) <= world.unitCount, 'Integer rounding cannot hide lost population');
  assert.ok(Math.abs(report.population_total - world.peopleTotal) < 1, 'Reported total must agree with the actual delivered units');
  assert.ok(Math.abs(source.population_min-Math.min(...world.units.map(u=>u.people)))<1);
  assert.ok(Math.abs(source.population_max-Math.max(...world.units.map(u=>u.people)))<1);
});

test('Every displayed triangle stays positively oriented for the entire continuous journey', () => {
  assert.equal(warp.length, 2 * (n + 1) ** 2);
  assert.ok(warp.every(Number.isFinite));
  const cross = (a,b) => a[0]*b[1]-a[1]*b[0];
  const sub = (a,b) => [a[0]-b[0],a[1]-b[1]];
  const point = id => {
    const row = Math.floor(id / (n + 1)), col = id % (n + 1);
    const lat = 2 * Math.atan(Math.exp((.5 - row/n) * 2 * Math.PI)) - Math.PI/2;
    return { a: [col/n,.28-lat/Math.PI*.5], b: [warp[id*2],warp[id*2+1]*.56] };
  };
  let smallest = Infinity;
  for (let row=0;row<n;row++) for (let col=0;col<n;col++) {
    const id = row*(n+1)+col;
    for (const ids of [[id,id+1,id+n+2],[id,id+n+2,id+n+1]]) {
      const [p,q,r]=ids.map(point), e=sub(q.a,p.a), f=sub(r.a,p.a);
      const de=sub(sub(q.b,p.b),e), df=sub(sub(r.b,p.b),f);
      const A=cross(de,df), B=cross(de,f)+cross(e,df), C=cross(e,f);
      const values=[C,A+B+C];
      if (A>0) { const t=-B/(2*A); if(t>0&&t<1) values.push(A*t*t+B*t+C); }
      const min=Math.min(...values);
      assert.ok(min>0, `Triangle ${ids.join(',')} folds during the morph`);
      smallest=Math.min(smallest,min);
    }
  }
  assert.ok(smallest>1e-12, 'Triangles need numerical room above a singularity');
});

test('Colour meanings remain attached to the same units and use compatible years', () => {
  assert.equal(report.gdp_year, report.gdp_denominator_year);
  for (const u of world.units) {
    for (const key of ['ratio','history']) assert.ok(u[key]===null || Number.isFinite(u[key]) && u[key]>=0);
    assert.ok(u.output===null || Number.isFinite(u.output) && u.output>=0);
  }
  for (const key of ['ratio','history']) {
    const values=world.units.map(u=>u[key]).filter(v=>v!==null);
    assert.ok(values.some(v=>v<1) && values.some(v=>v>1), `${key} must encode an actual comparison`);
  }
});

test('Every shipped data file matches the measured artifact and loads from a project subpath', () => {
  for (const [name,expected] of Object.entries(report.assets)) {
    const contents=readFileSync(`${assets}${name}`);
    assert.equal(contents.length,expected.bytes,name);
    assert.equal(createHash('sha256').update(contents).digest('hex'),expected.sha256,name);
  }
  const html=readFileSync(`${root}site/index.html`,'utf8');
  for (const [,url] of html.matchAll(/(?:src|href)="(human-space\/[^"]+)"/g)) assert.ok(existsSync(`${root}site/${url}`),url);
  assert.ok(!/(?:src|href)="\//.test(html), 'Root-relative URLs break a repository Pages site');
  assert.ok(existsSync(`${assets}OFL.txt`));
});
