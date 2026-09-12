# Ink and water cartogram

Use fine black polygon edges and small ink dots, with light-blue water (#d9ecf6)
and white land in dots/monotone views. Polygon fills follow actual country border
shapes. Country shades share their subregion's hue but differ visibly in lightness,
saturation and hue; South Asia is blue. Continent mode retains one colour per
continent. Country colours must remain distinct after the white mix used for fills.

Open in normal geography with countries, polygons and push selected, then begin
the slow loop. Pull is the inverse of the outward deformation at 0.38 strength,
about 3.6 times the initial mild pull by average site displacement. It is an
illustrative flow, not a new optimal-transport solve.

Labels use black uppercase Chivo at weight 900. Their centre is the area-weighted
geometric centroid of the deformed country border, not a population site or a
collision offset. Holes subtract area and moment. Label size follows visible land
area; sea extensions do not inflate labels. Overlapping or unreadably small labels
fade away at their centroid. Opacity uses a 35 ms exponential time constant and
settles in about 160 ms. Reduced motion skips the fade.

Fullscreen extends the outer ocean cells beyond every screen edge and hides the
selectors. Do not reveal the moving southern cutoff or zoom excessively merely to
hide it. Keep shared pan/zoom and the same deformation for borders, dots and labels.
