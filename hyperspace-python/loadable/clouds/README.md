# The point-cloud test patch

`cloud-test` tries plan 93: the point cloud as a show's node, a shape with only
vertices. It is not part of the app; copy it into the library's
`loadable/clouds/`. From `hyperspace-python/`:

```bash
uv run python tools/copy_patches.py clouds
```

It names two devices. Add whichever you have to the library's `devices.json`:

    { "role": "scan", "kind": "cloud", "file": "clouds/knot.npz" }
    { "role": "room", "kind": "kinect" }

`scan` is the recording the tests use, so no sensor is needed: copy
`tests/fixtures/clouds/knot.npz` to `~/Hyperspace/clouds/knot.npz` (a relative
`file` is the machine home's). `room` is the Kinect, as the Kinect demo names it.

Load `clouds/cloud-test`. What each node is for:

| Node | Device | What to check |
| --- | --- | --- |
| `cloud` | `scan` | Wired into the scene: four copies on a grid, orbiting (Field motion), turned by its own Yaw and Pitch. Its knobs (`cloud.*`) are on its node; change Instances, Layout, Spacing, Pan and Scale and watch only the cloud move, never the shape. |
| `cloud.2` | `room` | Wired, moved right, white points (Colours off). With no Kinect listed its node says "room is not listed on this Mac" and draws nothing. |
| `cloud.3` | none | Not wired, no device: its node says "no device: pick one on its menu". Pick `scan` on its menu (device ▸), then wire it into `scene.geometry`: it draws, on the left. |

Then, on GRAPH: add a fourth from the picker (scene ▸ point cloud) and it is
`cloud.4`, with its own `cloud.4.*` knobs; delete one; cut a cloud's wire into
the scene and that cloud goes from the picture. Save, load again: the same.
Plugging a cloud device in picks nothing by itself.
