# The Kinect demo

`kinect-mirror` shows what the `kinect` device (`hyperspace/kinect.py`) gives
a patch. It is not part of the app; copy it into the library's
`loadable/kinect/`. From `hyperspace-python/`:

```bash
uv run python tools/copy_patches.py kinect
```

It needs a device with the role `room` in the library's `devices.json`:

    { "role": "room", "kind": "kinect", "colors": true }

`colors` is optional: without it channel B's slot 2 is black.
`cloud.colors` (off here: a dark room makes dark points) tints the points with
the colour camera. Stand 1–3 m away, with nothing close in front of the
sensor: an object filling its view at a few centimetres gave no reading over
most of the picture, and on 2026-11-24 the whole depth went blank for 3–6 s
in every 14 (in libfreenect's own library too). The cloud node is the meta
controller's, drawn in every scene, so it has no wire in this file.

| Switch | Look | What it uses |
| --- | --- | --- |
| 1 | All of it | everything below, composited |
| 2 | You around the tesseract | the live point cloud; the depth picture on the faces; the depth as a field that bends the picture (nearer bends more) |
| 3 | A window | the depth made a mask (`matte`, `cut`), plasma inside your outline |
| 4 | Neon trails | the edges of the depth, fed back on themselves |
| 5 | The raw depth | near white, far dark, no reading black |

Channel B's slot 2 (`media.b.slot`) puts the colour camera on the faces.
Bass fattens the points, a mid band bends harder, a high band turns the hue
faster, and two bands spin W. `cloud.scale` is how big you are.
