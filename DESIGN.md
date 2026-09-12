# Borderless ink cartogram

## Scene and marks

Figure 6's line drawing brought into continuous motion, filling the viewport.
Black ink on white, no rectangular outline or framed-paper margin. Use the original
Laguerre cell geometry, fine vector boundaries and dotted coastlines. Dots remain
small circular marks at the corresponding sites. Both representations share motion.

## Geography

Use longitude and linear latitude at the geographic endpoint and the previous
wide human-space shape at the expanded endpoint. Omit coastline south of 60 degrees
south and hide polygon fragments there. None of the population sites are south of
that cutoff. Remove outer frame edges explicitly rather than hiding them with CSS.

## Colour and type

Monotone has no labels. Country and continent hues stay attached to their cells;
use lighter polygon fills beneath the black boundaries. Offshore sites receive the
nearest country's colour. Names use uppercase Chivo, weight 900, tight spacing and
solid black ink. A fine white knockout keeps names legible over polygon lines.
Type dimensions scale with the square root of each region's current visible area.
Measure country land footprints through the same deformation, zoom and viewport
clipping. Exclude ocean extensions so tiny islands do not get oversized labels.
Prioritise labels by current area rather than population count. No fixed country
or continent font sizes. Hide labels below a legible size instead of enlarging them.
No grey categories, shadows, explanatory panels or legends.

## Motion and gravity

Restore the slow automatic journey with endpoint holds and critically damped
momentum. Push retains the existing outward cartogram deformation. Pull uses an
attractive softened inverse-square field sourced by the population sites, with
reduced mobility in dense cores so incoming material gathers around the cores.
Switch gravity smoothly without swapping playback direction. Pause stops both
motions. Reduced motion applies the chosen mode immediately.

## Immersion

Normal view fits the wide map without a frame. Fullscreen covers the available
screen and hides the radio selectors. Keep a quiet exit glyph at the top right,
with F and Escape keyboard support. Use native or WebKit fullscreen, and retain
the same immersive layout where the browser cannot enter native fullscreen.
