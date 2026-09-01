#!/bin/zsh
# After the HYDE chain: the 1 km era (GHS-POP 1975-2030, D6) and the future (SSP2 2020-2100, T5), seams, site.
cd ~/historical-cartogram
P=~/.venv/default/bin/python
while ! grep -q "^FINISHED" /tmp/hc_extras.out 2>/dev/null; do sleep 30; done
while ! grep -q "^ALLDONE" /tmp/hc_ghs_epochs.out 2>/dev/null; do sleep 30; done
$P src/run_timeline_raster.py ghs 2048 60 0.05 all > /tmp/hc_tl_ghs.out 2>&1
$P src/run_timeline_raster.py ssp2 2048 60 0.05 all > /tmp/hc_tl_ssp2.out 2>&1
$P src/timeline_seams.py > /tmp/hc_seams.out 2>&1
$P src/build_site.py time >> /tmp/hc_extras2.out 2>&1
$P src/index.py >> /tmp/hc_extras2.out 2>&1; $P src/gallery.py >> /tmp/hc_extras2.out 2>&1
echo FINISHED2 >> /tmp/hc_extras2.out
