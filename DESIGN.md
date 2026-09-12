# Paper cartogram

## Scene

Figure 6 from paper/main.pdf, printed in black ink on white paper, made interactive.
The figure is the entire surface. Three small native radio groups sit at top left.

## Geometry and marks

Use the original M11 Laguerre polygons and square Mercator frame, including cells
that extend across oceans. Draw fine black polygon boundaries and dotted 110m
coastlines. Polygons are the opening representation; dots remain small ink marks
at the corresponding sites. Retain vectors for sharp zoom and fullscreen viewing.

## Colour and type

Monotone is black on white and has no labels. Countries and continents use their
respective hues, with lighter polygon fills so black boundaries and names remain
legible. Every rendered cell has a country assignment; offshore assignments use
nearest country, and oceanic island groups are placed in their geographic continent.
Labels use Chivo at weight 900, uppercase, tight spacing, solid black. Continent
names are larger, with country names revealed progressively on zoom. A fine white knockout keeps names legible over polygon lines. No grey cells,
shadows, panels or legends.

## Movement

The initial view is the still paper figure. Push expands it through the existing
smoothed transport mesh; pull returns it. The interpolation now retains the square
Mercator aspect ratio at both ends. Both directions use the existing slow damped
momentum and stop at the selected endpoint. Zoom, pan and fullscreen apply to the
whole drawing, including labels. Reduced motion uses immediate endpoint changes.
