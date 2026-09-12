"""Export Figure 6's original Laguerre cells as zoomable browser geometry.

Colour attribution uses the country containing each site, or its nearest country
when offshore. This is a presentation simplification, not a population reallocation.
"""
from pathlib import Path
import colorsys
import hashlib
import json
import numpy as np
from pysdot import PowerDiagram
from pysdot.domain_types import ConvexPolyhedraAssembly
import shapely
from shapely import STRtree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site/human-space'
SOURCE = ROOT / 'experiments/M11_power_8192_2048/sites.npz'
z = np.load(SOURCE)
W, H = int(z['W']), int(z['H'])
domain = ConvexPolyhedraAssembly()
domain.add_box([0, 0], [W, H])
diagram = PowerDiagram(positions=z['pos'], weights=z['weights'], domain=domain)
offsets, xy = diagram.cell_polyhedra()
xy = np.asarray(xy) / W
rings, ends = [], [0]
for a, b in zip(offsets[:-1], offsets[1:]):
    ring = xy[a:b]
    parts = []
    for p, q in zip(ring, np.roll(ring, -1, axis=0)):
        count = max(1, int(np.ceil(np.linalg.norm(q-p)*512)))
        parts.append(p + (q-p)*np.arange(count)[:, None]/count)
    dense = np.concatenate(parts)
    rings.append(dense)
    ends.append(ends[-1]+len(dense))
vertices = np.concatenate(rings).astype('<f4')
(OUT/'paper-cells.bin').write_bytes(vertices.tobytes())

features = json.loads((ROOT/'data/raw/ne_50m_admin_0_countries.geojson').read_text())['features']
geometries = [shapely.geometry.shape(f['geometry']) for f in features]
tree = STRtree(geometries)
sites = z['pos']/W
lon = (sites[:, 0]*360-168+180)%360-180
lat = np.rad2deg(2*np.arctan(np.exp((.5-sites[:, 1])*2*np.pi))-np.pi/2)
locations = shapely.points(lon, lat)
assigned = tree.nearest(locations)
inside = tree.query(locations, predicate='within')
assigned[inside[0]] = inside[1]
offshore = sorted(set(range(len(sites)))-set(inside[0].tolist()))
palettes = json.loads((OUT/'palettes.json').read_text())['countries']
by_name = {p['name']: p for p in palettes}
rows = []
short_names = {"People's Republic of China": 'China', 'United States of America': 'United States',
               'Democratic Republic of the Congo': 'DR Congo', 'Republic of the Congo': 'Congo',
               'United Republic of Tanzania': 'Tanzania'}
island_continents = {'South Georgia and the South Sandwich Islands': 'South America',
                    'British Indian Ocean Territory': 'Asia', 'Saint Helena': 'Africa',
                    'Seychelles': 'Africa', 'Mauritius': 'Africa', 'Maldives': 'Asia',
                    'French Southern and Antarctic Lands': 'Antarctica',
                    'Heard Island and McDonald Islands': 'Antarctica'}
continent_colours = {p['continent']: p['continental'] for p in palettes if p['continent']}
continent_colours['Antarctica'] = [55, 135, 172]
for f in features:
    p = f['properties']
    name = p.get('NAME_EN') or p['NAME']
    palette = by_name.get(name, {'country': [55, 135, 172], 'continental': [55, 135, 172], 'continent': p['CONTINENT']})
    colour = palette['country']
    h, s, v = colorsys.rgb_to_hsv(*(c/255 for c in colour))
    colour = [round(c*255) for c in colorsys.hsv_to_rgb(h, max(.42, s), v)]
    continent = island_continents.get(name, palette['continent'])
    rows.append({'name': short_names.get(name, name), 'continent': continent,
                 'country': colour, 'continental': continent_colours[continent]})

# The same 110m source and seam splitting used by paper/figures/fig6_power.py.
coasts = []
coast_source = ROOT/'data/raw/ne_110m_coastline.geojson'
for feature in json.loads(coast_source.read_text())['features']:
    g = feature['geometry']
    parts = [g['coordinates']] if g['type']=='LineString' else g['coordinates']
    for part in parts:
        ll = np.asarray(part)
        u = ((ll[:, 0]+168)%360)/360
        phi = np.deg2rad(np.clip(ll[:, 1], -85.05112878, 85.05112878))
        v = .5-np.log(np.tan(np.pi/4+phi/2))/(2*np.pi)
        for line in np.split(np.column_stack((u, v)), np.where(np.abs(np.diff(u))>.5)[0]+1):
            if len(line)<2:
                continue
            dense = []
            for a, b in zip(line[:-1], line[1:]):
                count = max(1, int(np.ceil(np.linalg.norm(b-a)*512)))
                dense.extend((a+(b-a)*np.arange(count)[:, None]/count).tolist())
            dense.append(line[-1].tolist())
            coasts.append(dense)

metadata = {'source': 'paper/figures/fig6_power.py',
            'sites_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'geometry_sha256': hashlib.sha256(vertices.tobytes()).hexdigest(),
            'warp_sha256': hashlib.sha256((OUT/'warp.bin').read_bytes()).hexdigest(),
            'country_assignment': 'Containing country, nearest country for offshore sites; presentation only.',
            'offshore_sites': offshore, 'offsets': ends, 'sites': sites.tolist(),
            'countries': rows, 'country_ids': assigned.tolist(), 'coastlines': coasts,
            'people_per_cell': float(z['total'])/len(sites),
            'source_size': [W, H], 'lon0': -168,
            'animation': 'Existing smoothed transport mesh; Figure 6 is the undeformed endpoint. Mesh seam differs by 0.046875 degrees.'}
(OUT/'paper.json').write_text(json.dumps(metadata, separators=(',', ':'))+'\n')
print(f'Exported {len(sites)} original cells, {len(vertices)} vertices, {len(offshore)} offshore colour assignments.')
