"""Export the active standalone experience into a static website directory."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

parser=argparse.ArgumentParser()
parser.add_argument('destination',type=Path)
parser.add_argument('--base',default='/humeter/')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]/'site'
target=args.destination
assets=target/'human-space';assets.mkdir(parents=True,exist_ok=True)
names=['app.js','style.css','icon.svg','geometry.js','paper-geometry.js','paper-polygons.js',
       'motion.js','label-area.js','label-visibility.js','screen-fabric.js','paper.json',
       'paper-cells.bin','paper-atlas.png','warp.bin','motion.json','pull.bin','gravity.json',
       'label-regions.json','label-regions.bin','country-colours.json','land-mask.png',
       'chivo.woff2','OFL.txt','SOURCES.md']
manifest={}
for name in names:
    source=root/'human-space'/name
    shutil.copy2(source,assets/name)
    content=source.read_bytes()
    manifest[name]={'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
html=(root/'index.html').read_text().replace('<head>','<head>\n  <base href="'+args.base+'">',1)
(target/'index.html').write_text(html)
(target/'bundle.json').write_text(json.dumps({'source':'https://github.com/philippbogdan/historical-cartogram',
    'files':manifest},indent=2)+'\n')
print(f'Exported {len(names)} assets to {target}')
