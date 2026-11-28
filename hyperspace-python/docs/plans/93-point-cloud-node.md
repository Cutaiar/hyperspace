# Plan 93 — the point cloud as a show's node

**Built** 2026-11-28 on `claude/cloud-show-node`. The owner's decisions of
2026-11-28 (plan 92 §7.1) are register row 1201; the build's own choices are
rows 1202–1209, "(rec)", to keep or overturn. Schema move: a loadable patch
`hyperspace.loadable/13`. Plan 92 waits on this landing on `main`.

## Why

Plan 92 (on `claude/zen-maxwell-2wusnm`, §6–§7) makes a frame one world with
scenes as cameras onto it. Before that, the owner wants the **Point cloud**
node to be an ordinary world object: today it is the rig's.

## What the cloud was (read in the code)

- `graph.cloud_name(i)`: one node per listed cloud device (`cloud`,
  `cloud.2` … by the device's place in the list), made by the rig, never
  added or deleted on GRAPH (graphview `NOT_REMOVABLE`) and never in a patch
  (`patches.FIXTURE_NODES`).
- `graph.cloud_wire` / `is_cloud_wire` / `is_fixture_wire`: its
  `cloud → scene.geometry` wire was the meta controller's, standing until the
  loadable patch cut it (`bus.cut`). The builder put `Graph.clouds` (the
  registry's cloud roles, part of the renderer's graph key) into every scene.
- `graph.PointCloud`: round points; its world transform a uniform scale about
  the origin (`cloud.scale`).
- One shared knob set for every cloud (`cloud.size`, `.scale`, `.bright`,
  `.colors` on the one `ViewState`), shown on the first cloud.

## The owner's decisions (2026-11-28, row 1201)

1. The cloud is the show's node: added from the canvas, numbered like every
   node, saved in the frame and in patches, deleted like any node.
2. It names its source device by hand, a pick on its node. Nothing is picked
   or added when a device connects. A node whose device is absent draws
   nothing and says so.
3. It is seen only where it is wired: `cloud.<n> → scene.geometry` is a wire
   like a shape's, no standing meta-controller wire.
4. Its params are numbered as every node's (`params.instance_id`), declared
   and dropped as the frame names them.
5. It is a shape with only vertices: the shape's world pose (position, turn,
   scale) and the shape's copies, sharing the shape's code paths.
6. Old shows still draw as before (a mapping, a backup, an end-to-end test).

## What changes

**The entry.** `{"kind": "cloud"}`, `{"kind": "cloud", "instance": 2,
"device": "kinect"}` (`graph.CloudAt`): a declared kind like a matte
(`DECLARED`, `NODE_KINDS`, `RESERVED`), named `cloud`, `cloud.<n>`. It makes
geometry (`WIRED_MAKES`) and takes nothing. **The device is the entry's
word** (row 1202): a role string, written only when set, the way an effect
entry carries its `slots`. `Wiring.clouds` carries the entries, so the
renderer's graph key moves with an edit to them. The registry's roles are no
longer in the key: the node reads `cloud:<role>` each frame and a device
coming or going rebuilds nothing.

**The build.** `_Build._make` makes a `PointCloud(name, device)` for a
reached cloud. `Graph.clouds`, `build_graph(clouds=…)`, `cloud_wire`,
`cloud_wires`, `is_cloud_wire`, `cloud_nodes` and `cloud_roles` as a key are
gone; `is_fixture_wire` is `is_bus` alone.

**Pose and copies, shared with the shape.** Each cloud has a
`view.CloudState` with the shape's own attribute names: `zoom` (its scale —
`cloud.scale`), `yaw`, `pitch`, `pan`, `instances`, `inst_layout`,
`inst_fit`, `inst_spacing`, `inst_persp`, `inst_motion`, `inst_amp`,
`inst_rate`, `inst_phase`. So the cloud's copies are `Renderer._copies_of`
(`field.field`'s rows, culled through the eye by the cloud's turned box), and
its turn is `geometry._camera` (the shape's yaw-then-pitch turntable), as a
matrix (`geometry.turn_matrix`). Each copy draws the cloud once with
`u_model = T(copy) · scale(copy) · R(yaw, pitch)`, its colour × the copy's
alpha (row 1204). `ViewState.integrate` and `seed_phases` integrate each
cloud's `inst_rate` as the shape's. The plan 59 world offset (the grab's) is
the shape's object only; a cloud has none (row 1205).

**Params.** `params.declare_clouds(r, names)` (as `declare_mattes`): for each
cloud the section names, `size`, `scale`, `bright`, `colors` (today's, the
first keeping `cloud.size` …), then the pose `yaw`, `pitch`, `pan.x`,
`pan.y` and the copies `instances`, `inst_layout`, `inst_motion`,
`inst_amp`, `inst_rate`, `inst_fit`, `inst_spacing`, `inst_persp` — n ≥ 2 is
`cloud.<n>.<key>`. The pose and copy params are declared by the same two
helpers the shape's `camera.*` and `view.inst_*` now go through
(`params._turn_params`, `params._copy_params`), so ranges, tapers and words
stay one set. Group `cloud` stays a patch group (since `/10`). The four
static `cloud.*` params and `ViewState.cloud_*` are gone.

**GRAPH.** The picker's scene ▸ gains **point cloud** (a new instance each
add). Its node menu has **device ▸** with this rig's cloud devices (the
registry's, kinds `cloud` and `kinect`) and **none** — one undo step that
rewrites the entry's `device`. Its words say `no device: pick one on its
menu`, `<role> is not listed on this Mac`, `<role>: waiting for points`, or
the points drawn. It deletes, copies and saves as a patch like any node; its
wire into `scene.geometry` is an ordinary wire (cut like any). The Kinect
title (row 1170) follows the device the node names. The node's description:
"Points from a cloud device you pick on its menu, a shape with only vertices:
wire it into a scene to see it."

**Patches.** `cloud` leaves `FIXTURE_NODES` / `FIXTURE_KINDS` and joins
`MAY_HOLD`: a patch saves its clouds with their device words. No
`hyperspace.patch` bump (row 1207).

## The migration (`graphmigrate.thirteen`, before `/13`)

A loadable patch older than `/13` drew one cloud per listed cloud device in
every scene, unless its `bus.cut` held that cloud's wire. On load, with the
rig's cloud roles (`graph.cloud_roles` of the renderer's `cloud_source`):

- for device i (0-based) whose wire `cloud[.i+1] → scene.geometry` is not
  cut, and a section that names the scene: an entry `{"kind": "cloud",
  "instance": i+1, "device": <role>}` and that wire, first among the scene's
  geometry wires (the solid clouds drew first, before the hands);
- every cloud wire in `bus.cut` is dropped (a cut wire stays cut: no node, no
  wire);
- for each cloud n ≥ 2 made, the file's `cloud.*` values are copied to
  `cloud.<n>.*` (they shared one set). A route or desk row on `cloud.*` stays
  on the first cloud, said in the load's note (row 1206);
- said: `/12 migrated to /13 (plan 93): N point clouds made nodes — save to
  keep it`.

The roles are this Mac's at load (row 1203): a file opened with no cloud
device listed gains no cloud. `tools/migrate_library.py` reads the rig's
roles from the library's device list the same way the app does, so its
resave keeps them. **Backup:** `migrate_library` backs the library up
first, as it does for every move, and the app's first save over a
pre-`/13` loadable patch keeps the old file as `<file>.bak-v12-clouds`
(`routing.backup`; no backup, no write). The test opens an old show end to
end (`tests/test_cloud_node.py`): a `/12` file with no cut, one with the
cloud cut, and one with two devices, each loaded through the library with a
cloud source, built and drawn, then saved and reloaded.

The 61 checked-in `/12` files hold no cloud and no cloud cut; their schema
line moves to `/13` and they resave byte for byte (row 1208).

## Build order

1. Graph: `CloudAt`, the kind tables, `Wiring.clouds`, the builder, the
   retired fixture wire.
2. View and params: `CloudState`, `declare_clouds`, the shared pose and copy
   helpers, the landing declaring clouds.
3. Render: `PointCloud.draw` through the copies and the pose.
4. GRAPH and patches: picker, device pick, words, delete, patches.
5. Migration, the schema bump, the backup, the corpus' schema line, the
   end-to-end test.
6. Docs: DECISIONS, the register, ARCHITECTURE, hand checks.

## Trying it by hand

`loadable/clouds/cloud-test.json` (its README says how to copy it and which
devices to list): three clouds — `cloud` naming the recorded `scan`, wired,
four orbiting copies, turned; `cloud.2` naming the Kinect's `room`, wired,
moved right; `cloud.3` naming none, unwired, to pick and wire on GRAPH.
`tests/test_cloud_test_patch.py` holds it opening with no note.

## Still open

- Row 1209: whether a device that connects should offer itself on a cloud
  node with none picked (the owner said manual for now).
- Plan 92 Q6 is answered by this plan: a cloud is seen where it is wired.

**Restart** after pulling: `ViewState` gains `clouds` and loses `cloud_*`.
