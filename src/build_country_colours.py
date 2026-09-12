"""Distinct country shades within the earlier regional hue families."""
from pathlib import Path
import colorsys
import hashlib
import json
import numpy as np
import shapely
from shapely import STRtree
from render_hero import FAMILY

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'site/human-space'
raw=(OUT/'paper.json').read_bytes();paper=json.loads(raw)
features=json.loads((ROOT/'data/raw/ne_50m_admin_0_countries.geojson').read_text())['features']
shapes=[shapely.geometry.shape(f['geometry']) for f in features]
tree=STRtree(shapes)
neighbours=[set(tree.query(g.buffer(.08)).tolist())-{i} for i,g in enumerate(shapes)]
families=dict(FAMILY);families['Southern Asia']=.58
families.update({'Seven seas (open ocean)':.63,'Antarctica':.61})
counts=np.bincount(paper['country_ids'],minlength=len(features))
colours=[None]*len(features);fills=[None]*len(features);used=set()
def rgb(h,l,s):return tuple(round(c*255) for c in colorsys.hls_to_rgb(h%1,l,s))
def fill(c):return tuple(round(v*.45+255*.55) for v in c)
def distance(a,b):return sum((x-y)**2 for x,y in zip(a,b))**.5
groups={}
for i,f in enumerate(features):groups.setdefault(f['properties']['SUBREGION'],[]).append(i)
for region,ids in groups.items():
    h=families[region]
    ids.sort(key=lambda i:(-counts[i],paper['countries'][i]['name']))
    candidates=[rgb(h+dh,l,s) for dh in [0,-.035,.035,-.0175,.0175]
                for l in [.43,.32,.55,.67,.60] for s in [.72,.52,.88]]
    chosen=[]
    for rank,i in enumerate(ids):
        eligible=[c for c in candidates if fill(c) not in used]
        if not eligible:raise RuntimeError('Colour candidate space exhausted')
        if rank==0:colour=eligible[0]
        else:
            adjacent=[fills[j] for j in neighbours[i] if fills[j] is not None]
            def score(c):
                f=fill(c)
                return min(distance(f,x) for x in chosen)+2*min([distance(f,x) for x in adjacent] or [0])
            colour=max(eligible,key=score)
        colours[i]=colour;fills[i]=fill(colour);chosen.append(fills[i]);used.add(fills[i])
assert len(set(colours))==len(features)==len(used)
rows=[{'name':paper['countries'][i]['name'],'region':features[i]['properties']['SUBREGION'],'colour':c}
      for i,c in enumerate(colours)]
(OUT/'country-colours.json').write_text(json.dumps({'paper_sha256':hashlib.sha256(raw).hexdigest(),
    'method':'Regional hue families with distinct lightness, saturation and hue; neighbouring shades separated after the polygon white mix.',
    'countries':rows},separators=(',',':'))+'\n')
for row in rows:
    if row['name'] in ['India','Pakistan','Bangladesh','Nepal']:print(row)
