# Product

## Register

brand

## Purpose

A borderless population map using Figure 6's original 8,192 Laguerre cells.
Open in normal geography with countries, polygons and push selected. Keep compact
radio selectors for colour, representation and gravity. Water is light blue.
Countries have distinct shades within geographic subregion hue families.

## Behaviour

Hold the geographic view briefly, then loop slowly between geography and the
selected force field. Push expands dense areas. Pull uses the inverse outward
field at the selected moderated strength. Both motions keep damped momentum.

Use linear latitude in geography. Omit Antarctica without dropping population
sites. Tap or Space pauses/resumes, drag pans, scroll or pinch zooms, Home resets.
Reduced motion uses immediate endpoint changes. No explanatory panels or data IDs.

## Labels

Place each label at the geometric centroid of its currently deformed country
border shape. Continent centroids combine the corresponding country footprints.
Do not move labels to avoid collisions. Fade smaller overlapping labels out.
Size text from visible land area, including zoom and clipping. Keep a quick
exponentially smoothed fade on appearance/disappearance, including when paused.

## Fullscreen

The visual occupies the screen and selectors disappear. Continue outer ocean
cells beyond the viewport so no moving cutoff or white strip is exposed.
Native/WebKit fullscreen and the immersive fallback share the same appearance.
F toggles, Escape exits, and the corner exit control stays subdued.

## Publication

The canonical experience is philippbogdan.com/humeter. Its static bundle is
published through the existing personal-website repository and deployment.
