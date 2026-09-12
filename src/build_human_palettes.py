"""Attach Natural Earth continents to the atlas's existing country IDs."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];out=root/'site/human-space'
raw=(out/'world.json').read_bytes();world=json.loads(raw)
features=json.loads((root/'data/raw/ne_50m_admin_0_countries.geojson').read_text())['features']
continents={f['properties'].get('NAME_EN') or f['properties']['NAME']:f['properties']['CONTINENT'] for f in features}
colours={'Africa':[50,125,82],'Asia':[190,90,52],'Europe':[116,87,167],'North America':[42,122,166],'South America':[173,131,28],'Oceania':[170,65,119],'Antarctica':[95,117,123],'Seven seas (open ocean)':[95,117,123]}
rows=[]
for i,c in enumerate(world['countries']):
    continent=continents[c['name']] if i else None
    rows.append({'name':c['name'],'continent':continent,'country':c['colour'] if i else [115,115,115],'continental':colours[continent] if i else [115,115,115]})
(out/'palettes.json').write_text(json.dumps({'world_sha256':hashlib.sha256(raw).hexdigest(),'countries':rows},separators=(',',':'))+'\n')
print('Mapped',len(rows)-1,'countries to their source continents.')
