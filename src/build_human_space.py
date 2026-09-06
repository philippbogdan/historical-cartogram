"""Build the compact, self-contained population fabric from local source data.

Run build_human_units.py first. Source rasters remain local; the deliverable contains
only a display mesh, population units, a geographic atlas and attributed metadata.
"""
import hashlib
import json
import time
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import Affine
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import Polygon, mapping
from pysdot import PowerDiagram
from pysdot.domain_types import ScaledImage

from hc import prep, hyde
from warp_vectors import frame_clip

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site/human-space'
WORK = ROOT / 'work/human-space'
RAW = ROOT / 'data/raw'
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
t0 = time.monotonic()


def log(*args):
    print(*args, f'({time.monotonic()-t0:.1f}s)', flush=True)


z = np.load(WORK / 'cells.npz')
N = len(z['masses'])
W = int(z['W'])
grid = prep.Grid('mercator', W, lon0=float(z['lon0']))
mass = z['masses']
assert mass.min() > .998 * mass.mean() and mass.max() < 1.002 * mass.mean(), 'Unequal population units'
polygons = [Polygon(z['xy'][a:b]) for a,b in zip(z['offsets'][:-1], z['offsets'][1:])]
assert all(p.is_valid for p in polygons)
area = np.array([p.area for p in polygons])
assert abs(area.sum() / W**2 - 1) < 1e-9, 'Population cells must cover the entire geographic frame'
log('Population cells verified', float(mass.min()), float(mass.max()))

# An explicitly softened version of the existing wall-frame artwork. A small
# geographic component restores strict monotonicity after filtering numerical noise.
# All rendered layers sample this exact same mesh, including the population units.
mesh = np.load(ROOT / 'experiments/e036_hero_ocean0.2_s30_share0.999_ocean0.2/mesh_repaired.npz')
resolution = 512
x = gaussian_filter(mesh['X'][::4,::4].astype(float) / 4096, 3., mode='nearest')[::2,::2]
y = gaussian_filter(mesh['Y'][::4,::4].astype(float) / 4096, 3., mode='nearest')[::2,::2]
yy, xx = np.mgrid[0:resolution+1, 0:resolution+1] / resolution
geography_share = .04
x = x * (1-geography_share) + xx*geography_share
y = y * (1-geography_share) + yy*geography_share
warp = np.stack([x,y],-1).astype('<f4')
warp.tofile(OUT / 'warp.bin')


def determinants(points):
    a,b,c,d = points[:-1,:-1],points[:-1,1:],points[1:,1:],points[1:,:-1]
    def cross(u,v): return u[...,0]*v[...,1]-u[...,1]*v[...,0]
    return np.concatenate([cross(b-a,c-a).ravel(),cross(c-a,d-a).ravel()])


def screen_source(uv):
    lat = 2*np.arctan(np.exp((.5-uv[...,1])*2*np.pi))-np.pi/2
    return np.stack([uv[...,0], .28-lat/np.pi*.5],-1)


source = screen_source(np.stack([xx,yy],-1))
target = warp.copy(); target[...,1] *= .56
folds = {}
for t in np.linspace(0,1,21):
    det = determinants(source*(1-t)+target*t)
    folds[str(round(float(t),2))] = int((det<=0).sum())
assert not any(folds.values()), f'Folded display mesh: {folds}'
log('Display mesh has positive triangles throughout the morph')


def transform(pts):
    uv = np.asarray(pts, float)/W
    tx = map_coordinates(warp[...,0],[uv[:,1]*resolution,uv[:,0]*resolution],order=1,mode='nearest')
    ty = map_coordinates(warp[...,1],[uv[:,1]*resolution,uv[:,0]*resolution],order=1,mode='nearest')
    return np.stack([tx,ty],-1)


# Atlas IDs are categorical, not colours: red/green encode a population cell;
# blue encodes a country. The browser supplies the chosen colour lens.
texture_size = 4096
scale = texture_size/W
transform_raster = Affine.scale(W/texture_size)
cell_ids = rasterize([(mapping(p),i) for i,p in enumerate(polygons)],out_shape=(texture_size,texture_size),transform=transform_raster,dtype='uint16')
gj = json.loads((RAW/'ne_50m_admin_0_countries.geojson').read_text())
features = []
countries = [{'name':'Ocean','colour':[232,239,240]}]
colours = {
    'Northern America':[119,156,188], 'Central America':[202,158,108], 'Caribbean':[209,155,129],
    'South America':[192,172,102], 'Northern Europe':[155,139,183], 'Western Europe':[165,139,177],
    'Southern Europe':[189,136,158], 'Eastern Europe':[194,144,169], 'Northern Africa':[204,156,132],
    'Western Africa':[165,181,113], 'Eastern Africa':[131,177,130], 'Middle Africa':[142,178,118],
    'Southern Africa':[115,169,141], 'Western Asia':[189,137,147], 'Central Asia':[184,151,170],
    'Southern Asia':[100,174,177], 'Eastern Asia':[127,174,153], 'South-Eastern Asia':[125,182,160],
    'Australia and New Zealand':[151,149,184], 'Melanesia':[155,157,192], 'Micronesia':[142,155,185],
    'Polynesia':[149,158,193]}
for f in gj['features']:
    props,g = f['properties'],f['geometry']
    if props.get('NAME') == 'Antarctica': continue
    base = np.array(colours.get(props.get('SUBREGION'),[170,177,179]),float)
    shift = ((len(countries)*.61803398875)%1-.5)*20
    cid = len(countries)
    countries.append({'name':props.get('NAME_EN') or props['NAME'], 'colour':np.clip(base+shift,0,255).astype(int).tolist()})
    for poly in g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]:
        for rings in frame_clip(poly, grid):
            p = Polygon(rings[0],rings[1:])
            if not p.is_empty: features.append((mapping(p),cid))
country_ids = rasterize(features,out_shape=(texture_size,texture_size),transform=transform_raster,dtype='uint8')
atlas = np.stack([(cell_ids%256).astype('uint8'),(cell_ids//256).astype('uint8'),country_ids],-1)
Image.fromarray(atlas).save(OUT/'atlas.png',optimize=True)
log('Geographic atlas exported')

# Shared cell edges sampled along the same source fabric. Raster IDs alone lose
# the smallest cells at global scale, so boundaries and dots remain vector data.
edges = {}
for poly in polygons:
    ring = np.array(poly.exterior.coords)
    for a,b in zip(ring[:-1],ring[1:]):
        ka,kb = tuple(np.round(a,7)),tuple(np.round(b,7))
        key = (ka,kb) if ka<kb else (kb,ka)
        edges[key]=(a,b)
segments=[]
for a,b in edges.values():
    count=max(1,int(np.ceil(np.linalg.norm(b-a)/2)))
    pts=np.linspace(a,b,count+1)/W
    segments.append(np.stack([pts[:-1],pts[1:]],1).reshape(-1,2))
edges_uv=np.vstack(segments).astype('<f4');edges_uv.tofile(OUT/'edges.bin')
log('Vector fabric exported',len(edges_uv),'vertices')

# Aggregate secondary measures over exactly the same source cells. All economic
# per-person ratios use 2015 in both numerator and denominator.
pd = PowerDiagram(positions=z['sites'],weights=z['weights'])


def integrate_counts(a,bounds):
    projected,_ = prep.to_grid(a,bounds,grid)
    projected=np.maximum(projected,0)
    pd.set_domain(ScaledImage([0,0],[W,W],projected))
    values=pd.integrals()
    assert abs(values.sum()-projected.sum()) < max(1.,projected.sum()*1e-8)
    return values


measures_cache = WORK/'measures.npz'
if measures_cache.exists():
    cache=np.load(measures_cache)
    gdp,pop2015,personyears=[cache[k] for k in ['gdp','pop2015','personyears']]
else:
    ds=netCDF4.Dataset(RAW/'lenses/GDP_PPP_1990_2015_5arcmin_v2.nc')
    a=np.ma.filled(ds['GDP_PPP'][-1],0).astype(float)
    a=np.maximum(np.nan_to_num(a),0)
    if ds['latitude'][0] < ds['latitude'][-1]: a=a[::-1]
    gdp=integrate_counts(a,(-180,-90,180,90))
    ds.close()
    p15=np.load(ROOT/'data/derived/ghs_2015_lonlat_f10.npz')
    pop2015=integrate_counts(p15['counts'],p15['bounds'])
    log('GDP and matched-year population integrated')
    H=hyde.Hyde(str(RAW/'hyde33/population_base.nc'))
    years=list(H.years)
    previous=H.counts(0)
    accumulated=np.zeros(previous.shape,dtype=float)
    for i in range(1,len(years)):
        current=H.counts(i)
        accumulated += (previous+current)*.5*(years[i]-years[i-1])
        previous=current
    personyears=integrate_counts(accumulated,H.bounds)
    np.savez_compressed(measures_cache,gdp=gdp,pop2015=pop2015,personyears=personyears)
    log('Historical person-years integrated')

world_gdp_person=gdp.sum()/pop2015.sum()
world_gdp_history=gdp.sum()/personyears.sum()
uv=z['positions']/W
locations=[]
cityfile=RAW/'ne_10m_populated_places_simple.geojson'
if cityfile.exists():
    cities=json.loads(cityfile.read_text())['features']
    for c in cities:
        p=c['properties'];lon,lat=c['geometry']['coordinates'][:2]
        if float(p.get('pop_max') or 0)>1500000:
            u,v=grid.xy(lon,lat)
            locations.append({'name':p.get('name') or p.get('nameascii'), 'uv':[float(u/W),float(v/W)],'population':float(p.get('pop_max') or 0)})
locations.sort(key=lambda p:-p['population'])
units=[]
for i,(u,v) in enumerate(uv):
    tx,ty=np.clip(np.array([u,v])*texture_size,0,texture_size-1).astype(int)
    cid=int(country_ids[ty,tx])
    if not cid:
        # A population centroid can sit in a bay. Find the closest mapped land
        # within this cell for its geographic label, never invent an ocean nation.
        r=12
        patch=country_ids[max(0,ty-r):min(texture_size,ty+r+1),max(0,tx-r):min(texture_size,tx+r+1)]
        valid=patch[patch>0]
        if len(valid): cid=int(np.bincount(valid).argmax())
    ratio=float(gdp[i]/pop2015[i]/world_gdp_person) if pop2015[i]>1 and gdp[i]>0 else None
    historical=float(gdp[i]/personyears[i]/world_gdp_history) if personyears[i]>1 and gdp[i]>0 else None
    ring=np.array(polygons[i].exterior.coords)
    dense=[]
    for a,b in zip(ring[:-1],ring[1:]):
        count=max(1,int(np.ceil(np.linalg.norm(b-a)/2)))
        dense.extend(np.linspace(a,b,count,endpoint=False))
    dense=np.array(dense)
    src=screen_source(dense/W)
    dst=transform(dense); dst[:,1]*=.56
    def polygon_area(p): return abs(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))*.5
    expansion=polygon_area(dst)/polygon_area(src)
    units.append({'id':i,'uv':[round(float(u),8),round(float(v),8)],'country':cid,'people':round(float(mass[i])), 'expansion':round(float(expansion),4),
                  'output':round(float(gdp[i]/pop2015[i])) if pop2015[i]>1 and gdp[i]>0 else None,
                  'ratio':round(ratio,5) if ratio is not None else None,
                  'history':round(historical,5) if historical is not None else None})

places=[]
for name,lon,lat in [('Bengal',90.1,23.5),('The Nile',31.2,29.9),('Java',109.8,-7.1),('Europe',8.5,49.0)]:
    u,v=grid.xy(lon,lat)
    distance=np.sum((uv-np.array([u,v])/W)**2,axis=1)
    places.append({'name':name,'unit':int(distance.argmin())})

meta={'version':1,'unitCount':N,'peopleTotal':float(mass.sum()),'peoplePerUnit':float(mass.mean()),
      'projection':{'lon0':grid.lon0,'source':'Mercator population grid, displayed with linear latitude at the geographic endpoint','meshResolution':resolution},
      'countries':countries,'units':units,'places':places,'cities':locations[:90],
      'sources':{'population':'GHS-POP R2023A, 2025 projection, aggregated to a 2048 x 2048 Mercator count grid',
                 'gdp':'Kummu, Taka and Guillaume (2018), GDP PPP 2015, 5 arcminutes, constant 2011 international dollars',
                 'denominator':'GHS-POP 2015, matching the GDP year',
                 'history':'HYDE 3.3, trapezoidal integral from 10,000 BC to 2023; reconstructed population, not individual biographies',
                 'boundaries':'Natural Earth 1:50m, public domain'},
      'display':{'oceanBuffer':.2,'geographyShare':geography_share,'smoothKmApprox':120,'note':'The display preserves ocean space and a little geography. Equal population units need not have perfectly equal displayed areas.'}}
meta['labels']=[]
for name,lon,lat in [('CANADA',-106,58),('UNITED STATES',-101,37),('BRAZIL',-51,-13),('RUSSIA',91,59),('CHINA',105,36),('INDIA',79,23),('AUSTRALIA',135,-25),('NIGERIA',8,9),('EGYPT',30,27),('INDONESIA',115,-4),('EUROPE',12,50),('SOUTH AFRICA',25,-29)]:
    u,v=grid.xy(lon,lat)
    meta['labels'].append({'name':name,'uv':[float(u/W),float(v/W)]})
(OUT/'world.json').write_text(json.dumps(meta,separators=(',',':'),allow_nan=False))
report={'unit_count':N,'population_total':float(mass.sum()),'unit_population_min':float(mass.min()),'unit_population_max':float(mass.max()),
        'unit_mass_max_relative_error':float(np.max(abs(mass/mass.mean()-1))), 'partition_area_relative_error':float(abs(area.sum()/W**2-1)),
        'folded_display_triangles_by_progress':folds,'geography_share':geography_share,'gdp_year':2015,'gdp_denominator_year':2015,
        'gdp_total':float(gdp.sum()),'personyears_total':float(personyears.sum()),'missing_gdp_units':int(sum(u['ratio'] is None for u in units)),
        'assets':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [OUT/'world.json',OUT/'warp.bin',OUT/'atlas.png',OUT/'edges.bin']}}
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
log('Completed',json.dumps({k:v for k,v in report.items() if k not in ['assets','folded_display_triangles_by_progress']}))
