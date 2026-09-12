# Product

## Register

brand

## Purpose

A borderless, animated population map using Figure 6's original 8,192 Laguerre
cells. Keep fine black ink lines and dots on white, with compact radio selectors
for colour (monotone, countries, continents), representation (dots, polygons),
and gravity (push, pull). The paper is the visual reference, not a fixed frame.

## Behaviour

Open in expanded human space and loop slowly between geography and the selected
force field, with damped momentum and holds. Push spreads dense regions outward.
Pull attracts surrounding material towards dense cores, gathering at their rims.
The gravity selector changes the deformation, not the direction of playback.

Use a wide latitude-proportional geographic view. Omit the Antarctic coastline
and the rectangular frame without dropping any population sites. Tap or Space
pauses/resumes, drag pans, scroll or pinch zooms, Home resets. Reduced motion uses
immediate changes. No headings, panels, data IDs or branding.

## Fullscreen

Like philippbogdan.com/atoms, expand the whole visual and remove the surrounding
controls. The map fills the screen, with pan and zoom available. Support native
and WebKit fullscreen, with the same immersive layout if the API is unavailable.
The corner icon or F toggles fullscreen; Escape exits. Keep the exit icon subdued.

## Colour and labels

Country and continent modes have bold black names attached to their regions.
Size each label from its region's current visible area, following the deformation,
zoom and viewport clipping. Hide colliding labels and type too small to read. No grey fallback:
assign offshore sites to their nearest country for presentation. Keep the original
population allocation intact and document simplifications in the source notes.
