#!/bin/zsh
# Runs after the full timeline: the three frames that were skipped, extras, the globe through time, the site.
cd ~/historical-cartogram
P=~/.venv/default/bin/python
while ! grep -q "^done" /tmp/hc_timeline_full.out; do sleep 30; done
$P src/run_timeline.py 2048 60 0.05 "-10000,-3000,0" base > /tmp/hc_timeline_fix.out 2>&1
for y in -03000 +00000 +01500; do $P src/timeline_extras.py uncertainty t_base_$y >> /tmp/hc_extras.out 2>&1; done
for y in -03000 +00000 +01000 +01500 +01800 +01900; do $P src/timeline_extras.py cities t_base_$y >> /tmp/hc_extras.out 2>&1; done
$P src/timeline_extras.py blend 2048 1900 1950 0.5 >> /tmp/hc_extras.out 2>&1
$P src/timeline_extras.py blend 2048 0 100 0.5 >> /tmp/hc_extras.out 2>&1
$P src/run_globe_timeline.py 1024 "-10000,-3000,-1000,0,500,1000,1500,1700,1800,1900,1950,2000,2023" > /tmp/hc_globe_tl.out 2>&1
$P src/build_site.py time >> /tmp/hc_extras.out 2>&1
$P src/build_site.py pages >> /tmp/hc_extras.out 2>&1
$P src/index.py >> /tmp/hc_extras.out 2>&1; $P src/gallery.py >> /tmp/hc_extras.out 2>&1
echo FINISHED >> /tmp/hc_extras.out
