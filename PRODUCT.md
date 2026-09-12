# Product

## Register

brand

## Purpose

An interactive version of Figure 6 in the cartogram paper. The actual 8,192 Laguerre
cells are the hero, drawn in black on white on the original square Mercator frame.
The visual fills the screen, with compact native radio selectors for colour
(monotone, countries, continents), representation (dots, polygons) and direction
(push, pull). A small fullscreen icon expands the drawing.

## Behaviour

Open on the still Figure 6 polygon drawing. Push expands the same geometry into
human space. Pull returns it to geography. Preserve slow damped momentum when
reversing direction, then stop at the selected endpoint. Tap or Space pauses or
resumes, drag pans, scroll or pinch zooms, Home resets. Reduced motion changes
endpoints immediately. No headings, explanatory panels, data IDs or branding.

## Colour and labels

Country and continent modes have bold black names attached to their regions.
Hide colliding labels and reveal smaller countries on zoom. No grey fallback:
assign offshore sites to their nearest country for presentation. Keep the original
population allocation intact and document this simplification in the source notes.
