"""Project Natural Earth coastline segments into the atlas source frame."""
from pathlib import Path
import json,math,struct
root=Path(__file__).resolve().parents[1]
world=json.loads((root/'site/human-space/world.json').read_text());lon0=world['projection']['lon0']
features=json.loads((root/'data/raw/ne_50m_coastline.geojson').read_text())['features']
segments=[]
def project(p):
    lon,lat=p[:2];lat=max(-85.0511,min(85.0511,lat))
    return ((lon-lon0)%360)/360,.5-math.log(math.tan(math.pi/4+math.radians(lat)/2))/(2*math.pi)
for feature in features:
    geometry=feature['geometry'];lines=[geometry['coordinates']] if geometry['type']=='LineString' else geometry['coordinates']
    for line in lines:
        for a,b in zip(line,line[1:]):
            if a[1]<-60 or b[1]<-60:continue
            x,y=project(a);xx,yy=project(b)
            if xx-x>.5:xx-=1
            if xx-x<-.5:xx+=1
            for shift in [-1,0,1]:
                left,right=x+shift,xx+shift;start,end=0.,1.
                if right!=left:
                    t0,t1=sorted([(0-left)/(right-left),(1-left)/(right-left)])
                    start=max(start,t0);end=min(end,t1)
                elif not 0<=left<=1:continue
                if end<=start:continue
                ax=left+(right-left)*start;ay=y+(yy-y)*start
                bx=left+(right-left)*end;by=y+(yy-y)*end
                count=max(1,math.ceil(math.hypot(bx-ax,by-ay)*2048))
                for i in range(count):
                    s=i/count;t=(i+1)/count
                    segments.extend([ax+(bx-ax)*s,ay+(by-ay)*s,ax+(bx-ax)*t,ay+(by-ay)*t])
(root/'site/human-space/coastline.bin').write_bytes(struct.pack('<'+'f'*len(segments),*segments))
print(len(segments)//4,'coastline segments')
