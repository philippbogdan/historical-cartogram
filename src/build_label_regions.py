"""Country footprints for label sizing, independent of ocean-spanning cells."""
from pathlib import Path
import hashlib
import json
import numpy as np
from shapely.geometry import Polygon, box
from shapely.affinity import translate
from rasterio.features import rasterize
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'site/human-space'
source=(ROOT/'data/raw/ne_50m_admin_0_countries.geojson').read_bytes()
features=json.loads(source)['features']
paper_raw=(OUT/'paper.json').read_bytes()
paper=json.loads(paper_raw)
assert len(features)==len(paper['countries'])
vertices=[];offsets=[0];countries=[];signs=[];centroidWeights=[]
south=.5-np.log(np.tan(np.pi/4-np.pi/6))/(2*np.pi)
frame=box(0,0,1,south)

def project(ring):
    ll=np.asarray(ring)
    u=np.unwrap(((ll[:,0]+168)%360)/360*2*np.pi)/(2*np.pi)
    phi=np.deg2rad(np.clip(ll[:,1],-85.05112878,85.05112878))
    v=.5-np.log(np.tan(np.pi/4+phi/2))/(2*np.pi)
    return np.column_stack((u,v))

for country,feature in enumerate(features):
    geometry=feature['geometry']
    parts=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
    for rings in parts:
        exterior=project(rings[0]);holes=[]
        for ring in rings[1:]:
            hole=project(ring)
            hole[:,0]+=round(exterior[:,0].mean()-hole[:,0].mean())
            holes.append(hole)
        shape=Polygon(exterior,holes).buffer(0).simplify(.00008,preserve_topology=True)
        for shift in (-1,0,1):
            clipped=translate(shape,xoff=shift).intersection(frame)
            if clipped.is_empty:continue
            polygons=[clipped] if clipped.geom_type=='Polygon' else list(clipped.geoms)
            for polygon in polygons:
                if polygon.geom_type!='Polygon':continue
                for ring,sign in [(polygon.exterior,1)]+[(h,-1) for h in polygon.interiors]:
                    points=np.asarray(ring.coords)
                    dense=[]
                    for a,b in zip(points[:-1],points[1:]):
                        count=max(1,int(np.ceil(np.linalg.norm(b-a)*512)))
                        dense.extend(a+(b-a)*np.arange(count)[:,None]/count)
                    if len(dense)<3:continue
                    vertices.extend(dense);offsets.append(len(vertices));countries.append(country);signs.append(sign)
                    latitude=np.rad2deg(2*np.arctan(np.exp((.5-np.asarray(dense)[:,1])*2*np.pi))-np.pi/2)
                    alaska=paper['countries'][country]['name']=='United States' and latitude.min()>50
                    centroidWeights.append(0 if alaska else 1)

binary=np.asarray(vertices,dtype='<f4').tobytes()
(OUT/'label-regions.bin').write_bytes(binary)
record={'source':'Natural Earth 50m country footprints; sea excluded; holes subtracted',
        'source_sha256':hashlib.sha256(source).hexdigest(),
        'paper_sha256':hashlib.sha256(paper_raw).hexdigest(),
        'geometry_sha256':hashlib.sha256(binary).hexdigest(),
        'offsets':offsets,'country_ids':countries,'signs':signs,
        'centroid_weights':centroidWeights,'centroid_exclusions':{'United States':'Alaska, for the country label only'}}
(OUT/'label-regions.json').write_text(json.dumps(record,separators=(',',':'))+'\n')
# Use the identical footprints for the water/land background.
xy=np.asarray(vertices)*2048
shapes=[];rings=[];owner=0
for a,b,sign,country in zip(offsets[:-1],offsets[1:],signs,countries):
    if sign==1:
        if rings:shapes.append(({'type':'Polygon','coordinates':rings},owner))
        rings=[];owner=country+1
    ring=xy[a:b].tolist();ring.append(ring[0]);rings.append(ring)
if rings:shapes.append(({'type':'Polygon','coordinates':rings},owner))
mask=rasterize(shapes,out_shape=(2048,2048),dtype='uint8')
encoded=np.stack(((mask>0).astype('uint8')*255,mask,np.zeros_like(mask)),axis=-1)
Image.fromarray(encoded).save(OUT/'land-mask.png',optimize=True)
record['land_mask_sha256']=hashlib.sha256((OUT/'land-mask.png').read_bytes()).hexdigest()
(OUT/'label-regions.json').write_text(json.dumps(record,separators=(',',':'))+'\n')
print(f'{len(countries)} rings, {len(vertices)} vertices, {len(binary)} bytes')
