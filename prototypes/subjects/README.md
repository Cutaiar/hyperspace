# Subjects prototype

A browser prototype for what the subject could be when it is not a
polytope: a vector source (an SVG), shown flat or lifted into 3D, with a
material on top. Open `index.html` from any static server
(`python3 -m http.server` in this folder); three.js loads from jsDelivr.

- **Sources.** `sources/flow-mark.svg` and `sources/flow-wordmark.svg`
  are the Wispr Flow mark and wordmark, taken as-is from wisprflow.ai's
  own SVGs (the mark's round backdrop removed). Both are embedded in the
  page; *Load SVG…* or a paste adds any other filled SVG.
- **Flat ↔ 3D.** A filled path whose area matches a stadium for its
  bounding box is read as a pill and built as a capsule; every other path
  is extruded with a rounded bevel. The Depth slider squashes z (and the
  normals with it), so 0 is the flat vector and 1 the full capsule.
- **Looks.** Clay, Chrome, Glass and Pearl are three.js physical
  materials; Toon, Halftone, Plasma and Wireframe are shaders of their
  own. Every look shares one vertex transform (`SUBJECT_GLSL`).
- **Textures.** Checker, Stripes, Aurora, Grid or an image. They are mapped
  across the whole subject or per part (around and along each capsule).
- **Motion.** Each capsule has a gain slot (`uGain`), ordered left to
  right. A demo voice or an audio file's log-spaced bands drive the gains,
  so the bars move like the waveform they draw.

`demo.mp4` walks through it: the capsules moving to the demo voice, the
morph to flat and back, every look, a texture per part, and the wordmark
in chrome. It was recorded headless on a stepped clock, so it plays at an
even 30 fps.

In the Python app (plan 28, stacked): the mark is now two shapes in the
catalog, Flow mark and Flow capsules (`hyperspace-python/hyperspace/geometry.py`,
`docs/plans/28-catalog-and-scenes.md`). Still to port: the solid
materials, and the bar gains as routable params so audio can drive them.
