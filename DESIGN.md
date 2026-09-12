# Ink cartogram

## Scene

A person looks directly at a pointillist population map, like a sheet of white paper printed
with fine ink. The map occupies the viewport with two small native radio groups at the top left.

## Marks

Default to black circular dots on pure white. One persistent dot per population group.
Country mode uses the existing country palette; continent mode uses a shared colour for each
Natural Earth continent. Polygon mode fills the same population cells with fine boundaries,
or uses black outlines on white in monotone. The colour group is left of the representation
group. Native radios and small plain labels are the only interface.

## Composition and motion

Centre the complete human-space map with a small margin. Fit the whole shape on phones and
landscape screens. Begin in human space, hold, then move slowly to geography and back.
Retain the shared damped momentum. Pause and zoom are direct gestures on the canvas, with
keyboard equivalents and an accessible description. Reduced-motion users start on a still map.

## Coastline

A thick black coastline follows the same deformation in both dots and polygons. Use rounded
joins and caps, with a three-pixel stroke at the default zoom. Keep national borders separate
from this coastline layer.
