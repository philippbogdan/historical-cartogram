"""Version active browser assets and modules for cache-safe publication."""
from pathlib import Path
import re
import hashlib

root=Path(__file__).resolve().parents[1]/'site/human-space'
def digest(name):return hashlib.sha256((root/name).read_bytes()).hexdigest()[:12]
def update_import(path,name):
    source=path.read_text()
    source=re.sub(r'(\./'+re.escape(name)+r')(?:\?v=[a-f0-9]+)?',r'\1?v='+digest(name),source)
    path.write_text(source)

for module,dependency in [('paper-polygons.js','paper-geometry.js'),('screen-fabric.js','paper-geometry.js'),
                         ('paper-polygons.js','screen-fabric.js'),('label-area.js','paper-geometry.js'),
                         ('app.js','paper-geometry.js'),('app.js','paper-polygons.js'),
                         ('app.js','label-area.js'),('app.js','label-visibility.js')]:
    update_import(root/module,dependency)
path=root/'app.js';source=path.read_text()
for name in ['paper.json','paper-cells.bin','warp.bin','motion.json','pull.bin','label-regions.json',
             'label-regions.bin','country-colours.json','paper-atlas.png','land-mask.png']:
    source=re.sub("('"+re.escape(name)+r")(?:\?v=[a-f0-9]+)?'",r'\1?v='+digest(name)+"'",source)
path.write_text(source)
path=root.parent/'index.html';source=path.read_text()
for name in ['style.css','app.js']:
    source=re.sub(r'(human-space/'+re.escape(name)+r')\?v=[a-f0-9]+',r'\1?v='+digest(name),source)
path.write_text(source)
