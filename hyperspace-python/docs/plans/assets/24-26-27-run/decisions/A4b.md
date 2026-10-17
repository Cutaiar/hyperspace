# A4b — decisions, hand checks, as-built notes (plan 26: the point-cloud geometry node)

Branch `plan-26-a4b-points`, base `plan-24-26-27-integration` at `3fa2f88` (the merge of
PR #187, A3; B4's contract — `devices.PointCloud`, `DeviceRegistry.clouds`, the `cloud` device,
`tests/fixtures/clouds/knot.npz` — already in). Owner's decisions honoured: 2 (Geometry: draw
calls in the shared camera, no framebuffer of its own), 5 (points get a real depth as
vertex-expanded quads), 16 (the render stack reads params and writes none; it never imports
`devices`), 23 (no preset edited or added; the proof is the B4 fixture through a scratch
config), 24 (every new param moves no picture of today: the node exists only while a `cloud`
device is listed).

**The node kind name for A4's loader: `cloud`** (`graph.CLOUD_KIND`). A4's JSON can name a
node `{"kind": "cloud", "role": "scan"}` → `graph.PointCloud(name, role)`; it is a geometry
(`OUTPUT = GEOMETRY`, `SOLID = True`), wired into any Scene's `geometry`, `geometry.2`, … port.

## 1. Register-row drafts

**1xx — A point cloud is solid geometry in the scene: opaque round dots, depth written, before the see-through shape**
- **Built:** `graph.PointCloud` draws the latest frame of `cloud:<role>` (B4's `DeviceRegistry.clouds`) through the eye (`eye.*`) as one instanced screen-space quad per point (A2's point-quad expansion: `CLOUD_VS` is `render.POINT_VS`'s arithmetic, per-instance position and colour), a hard round dot, alpha 1, depth tested and written. It is `SOLID`, so the scene draws it with the hands (A3's solid path: clear, solids, then the shape painter-sorted and depth-tested against them). The shape's strokes in front of a point lie over it; a point in front of the shape hides the strokes behind it. The dot is a whole number of framebuffer pixels across (A2's rounding). Behind the eye a point is dropped.
- **Other options:** see-through points sorted with the shape (a per-frame CPU sort of N points by depth — plan 29's sensors publish 10⁵ points); soft-edged dots blended (their faint rims would write depth or not — the rim either cuts the shape or is hidden by it); GL point sprites (no real depth size control, A2 replaced them).
- **To reverse:** local to `PointCloud.draw` / `CLOUD_FS`.
- **Rough edge:** the dots' edges are hard (MSAA on output 1 smooths them; plain outputs show stair-steps at 2 px radius). A point is the same size in pixels at any depth (no perspective size).
- **Judge it:** V.A4b.1.

**1xx — The cloud's world transform is one uniform scale about the world origin (`cloud.scale`, default 0.3); not the shape's camera**
- **Built:** `u_model = diag(k, k, k, 1)` with `k = cloud.scale` (0.01–10, log, default 0.3: the fixture knot's ±3 units land at ±0.9 shape radii, the shape's size; a Kinect's metres at 0.3 would make a 2 m person 0.6 radii). The shape's `camera.zoom/pan` and `rot.*` do not move the cloud (they are the shape's transform, decision 4); the eye does.
- **Other options:** fit the cloud's `bounds` into the unit sphere every frame (the scale would breathe with a live sensor's noise); the shape's model matrix (the cloud would tumble with the 4D shape); a full position/rotation (`cloud.pan.*`, `cloud.yaw`) — plan 29's sensor calibration, like the Leap's `units`.
- **To reverse:** one param and one matrix.
- **Rough edge:** no offset or rotation: a sensor's cloud centred away from its origin (a Kinect looking at a person 2 m away) sits off-centre until plan 29 calibrates it.
- **Judge it:** V.A4b.1.

**1xx — `cloud.*` is a session group: size, scale, brightness, the cloud's own colours**
- **Built:** `cloud.size` (radius, logical px, 0.5–12, default 2.0), `cloud.scale` (above), `cloud.bright` (× the colour, 0–2, default 1), `cloud.colors` (toggle, default on: the source's colours; off — or a source with none — white). In `params.SESSION_GROUPS` (the cloud is the room's sensor; a preset load never changes how it is shown), on `ViewState.cloud_*`. Size, scale and brightness are modulatable; the colours toggle is not. Every node reads them (the naming rule's first instance: a second node, `cloud.2`, shares them until A4 registers instance params). No panel row yet (learnable/routable; plan 28's editor or a SYSTEM/CAMERA row later).
- **Other options:** performance params (a preset would carry the look of a sensor it may not have); a hue/tint param instead of a toggle (a look — the creative pass).
- **To reverse:** local to `params.build_registry`'s block and four `ViewState` fields.
- **Rough edge:** no UI row: the owner reaches them through Learn or the routing page only.
- **Judge it:** V.A4b.2.

**1xx — The renderer is handed the device registry; a *listed* `cloud` device adds its node to the default scene**
- **Built:** `Renderer.cloud_source` (one line in `app.main`: `renderer.cloud_source = rig`, beside `renderer.ghost.router`). `graph.cloud_roles(source)` reads the roles of the devices whose `kind` is `cloud` (duck-typed; `graph.py` never imports `devices`), and `Renderer._graph_for` keys the graph on them beside the switches and the wiring; `default_graph(views, wiring, clouds)` adds one `PointCloud` per role (`cloud`, `cloud.2`, … by the naming rule) as the scene's first geometries. A listed device whose file is missing (or not yet polled, or closed) keeps its node, which draws nothing — so copying the recording in later shows it with no graph change. With no `cloud` entry the graph is today's, node for node (every existing golden byte-identical).
- **Other options:** key on the clouds *present* (`clouds.keys()`): the graph would rebuild when a device drops or comes back; key on any device with a `Port(kind="cloud")` (plan 29's Kinect kind would add itself — but asks every device for its ports each frame).
- **To reverse:** local to `cloud_roles` and `_graph_for`.
- **Rough edge:** only devices of kind `cloud` are found: plan 29's sensor kinds must be added to `cloud_roles` (one line) or move it to the ports.
- **Judge it:** V.A4b.1, V.A4b.3.

**1xx — The buffer is uploaded on a new (frame id, publish time); the GL objects live on the renderer**
- **Built:** `_CloudGL` (on `Renderer._cloud_gl`, made on the first cloud drawn) holds the program, the quad corners, and per node a points buffer, a colours buffer (ones when the cloud has no colours) and a vertex array. `upload` writes the read-only float32 points as they are (`buf.write(points)`, no copy) only when `(cloud.frame, cloud.t)` moved — the publish time too, because a re-opened device counts its frames from 0 again. A graph rebuilt for new switches re-uploads nothing; `Renderer.on_reload` releases them (a shader edit in `graph.py` lands on the next frame).
- **Other options:** key on `frame` alone (a re-opened device's frame 0 would be taken for the old frame 0); buffers on the node (released or leaked whenever the graph is rebuilt).
- **To reverse:** local.
- **Rough edge:** a node removed from the graph (its device unlisted) keeps its buffers until the next reload — a few KB for the fixture, more for a sensor.
- **Judge it:** V.A4b.3.

**1xx — The cloud's draw is its own SYSTEM line, named after the node**
- **Built:** the scene's solid path times each solid geometry under its node name, so the SYSTEM page reads `cloud` (then `ghost` when the hands are in the scene) before `scene`. `stats["clouds"]` holds each cloud node's drawn point count this frame; a draw that raises is `stats["cloud_error"]` and the scene goes on.
- **Other options:** the cloud's time inside `scene`'s line (no way to see its cost).
- **To reverse:** set `TIMED = False`.
- **Rough edge:** `cloud_error` is not shown on any page yet (the SYSTEM page shows the device's own line: `scan · cloud · connected · … · frame 7/16 · 144 points · 12 fps`).
- **Judge it:** V.A4b.3.

## 2. Hand-check drafts

**V.A4b.1 The recorded cloud shows in the scene, in the shape's world.** *Headless:* `tests/test_cloud_node.py::test_the_node_draws_the_fixtures_points_where_the_shared_camera_puts_them`, `::test_a_point_in_front_of_the_shape_hides_it_and_one_behind_is_hidden`, goldens `cloud/scene`, `cloud/scene+hands` (legacy6, party-faces). *Setup:* a scratch home: copy `hyperspace-python/tests/fixtures/clouds/knot.npz` to `<home>/clouds/knot.npz` and add to `config.toml`:
```toml
[[devices]]
role = "scan"
kind = "cloud"
file = "clouds/knot.npz"
```
launch, load LEGACY 6. *Pass:* a knot of dots (blue low, warm high) turning slowly about the vertical at about the shape's size, threaded through the tesseract; where a dot is nearer than an edge it hides the edge, where it is behind, the edge draws over it; the knot does not tumble with the shape, nor move with the mouse's zoom/pan; wheeling the eye's field of view (CAMERA → eye) changes both together. *Fail:* dots always on top of the shape (no depth), dots tumbling with the shape (the shape's model matrix), nothing (`cloud_source` not handed over — check the SYSTEM line shows the device `connected`).

**V.A4b.2 The cloud's look.** *Headless:* `tests/test_cloud_node.py::test_the_cloud_params_are_session_and_default_to_a_cloud_at_the_shapes_size`, the colours-off assertion in `::test_the_node_draws_the_fixtures_points_…`. *Setup:* the cloud above; Learn a desk knob each onto Cloud point size, Cloud scale, Cloud brightness; Learn a button onto Cloud colours. Then load another preset. *Pass:* size grows the dots in whole pixels; scale grows the knot about the centre (past ~3× it reaches the eye and the near dots vanish); brightness 0 turns the dots black (they still hide the shape behind them); colours off → white dots; a preset load leaves all four as set. *Fail:* a preset load resets them (not session), fractional-size shimmer.

**V.A4b.3 No cloud, no change; the cloud's cost on SYSTEM.** *Headless:* `tests/test_cloud_node.py::test_a_missing_cloud_draws_nothing_and_raises_nothing`, `::test_the_buffer_is_uploaded_only_when_the_frame_id_moves`, `::test_the_per_node_timer_names_the_cloud`, `::test_a_hot_reload_rebuilds_the_clouds_program_and_the_picture_is_the_same`, `tests/test_golden_frames.py` (544 frames unchanged). *Setup:* the entry above with the file not yet copied in; launch; open SYSTEM; copy the file in. *Pass:* before the copy the picture is exactly as with no entry, the device line says `error: …` and the GPU lines show `cloud 0.00` above `scene`; after the copy (within the retry) the knot appears with no relaunch and the `cloud` line shows a small time. Without any `cloud` entry there is no `cloud` line. *Fail:* an error toast or a stall when the file is missing, a `cloud` line with no entry.

## 3. As-built notes

**At the machine.** Nothing changes unless `config.toml` lists a `cloud` device. With one listed (the B4 fixture copied into the home), the scene shows the recording's points as solid dots in the shape's world, at the shape's size by default, playing at the file's 12 fps. Four `cloud.*` session params set their size, scale, brightness and colours (no panel row; Learn reaches them).

**Code.**
- `hyperspace/graph.py`: the block "point cloud (plan 26 A4b)": `CLOUD_KIND` (= `"cloud"`, the kind name for A4's JSON), `CLOUD_VS` / `CLOUD_FS`, `_CLOUD_CORNERS`, `cloud_roles(source)`, `_CloudGL` (program, corners, per-node buffers; `upload`, `release`), `PointCloud` (geometry, `SOLID`, `role`, `source`, `cloud(frame)`, `draw`), `cloud_nodes(g, roles)`. Outside the block: `Graph.clouds` (one attribute), `default_graph(..., clouds=())` (two lines: the nodes added first, then put first in the scene's geometries), the module docstring's geometry line, imports (`math`, `numpy`, `geometry.eye_matrix` and the eye constants).
- `hyperspace/render.py`: `Renderer.cloud_source` (None), `_graph_for` keyed on `cloud_roles(cloud_source)`, `on_reload` releases `_cloud_gl`; the `cloud_roles` import.
- `hyperspace/app.py`: one line, `renderer.cloud_source = rig`.
- `hyperspace/view.py`: `ViewState.cloud_size`, `cloud_scale`, `cloud_bright`, `cloud_colors`.
- `hyperspace/params.py`: `"cloud"` in `SESSION_GROUPS`; the four `cloud.*` params after the eye's.
- `tools/golden_frames.py`: `CLOUD_FIXTURE`, `CLOUD_CONFIG`, `CLOUDED`; `Rig.devices` / `Rig.list_devices(toml)` (a scratch `config.toml` in the rig's home read by `config.load`, the real `DeviceRegistry` on the pinned clock, polled in `Rig.frame` before the hands); `_shoot(config=)`; manifest `cloud_states`.

**Tests.** New `tests/test_cloud_node.py` (9): the graph with and without listed clouds (no GL), `cloud_roles`, the params; on GL: the fixture's points where the CPU projection through `eye_matrix` puts them, each sampled pixel the colour of a point whose dot covers it and the ground elsewhere, colours off; a missing cloud (file absent) byte-identical to no registry, no node without a cloud device, a raising source draws nothing; upload once per recorded frame and kept across a graph rebuild; depth against the shape (front points hide strokes, the shape over the back ones); the timer's `cloud` line; hot reload. `tests/test_golden_frames.py::test_every_factory_preset_has_every_state_recorded_and_nothing_else`: `cloud_states` asserted, the `cloud/*` keys and the count (+4) — an addition, no existing assertion loosened. 2142 passed, 2 skipped (2133 on the base + 9).

**Goldens.** New (4): `legacy6` and `party-faces`, hands present, `cloud/scene` and `cloud/scene+hands` (frame 1 of the knot after the tool's 8 frames at 60 Hz on the pinned clock). Every one of the 544 existing goldens byte-identical (`tools/golden_frames.py`: "all 548 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)").

**Smoke run.** `HYPERSPACE_FRAMES=240 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES` with the scratch `config.toml` above and the fixture copied in: exit 0, empty `stall.log`. Then 200 frames under the probe below. A screenshot was refused by macOS ("could not create image from display"), so a probe wrapping `Renderer._draw_frame` recorded what the real app drew: every frame the graph's timed lines start `cloud, scene, cover`; `stats["clouds"]` went `{'cloud': 96}` → `112` → … → `144` (the knot's frames 0 → 6 at 12 fps; the point count grows 8 per frame), no `cloud_error`, the GPU line `cloud 0.00 ms`; the window's back buffer at frame 150 had 509 warm-coloured (the knot's upper half) pixels.

**What no person has verified.** Everything visible: the knot's look on the real window and projector, its depth against the shape by eye, the params by hand.

**Rough edges.** Hard-edged dots; constant pixel size; only `cloud`-kind devices are found; a second cloud node shares `cloud.*`; no panel row; buffers of an unlisted node kept until a reload; the scale-only world transform.

## 4. Where the documents and the code differ / deliberately not done

- The dispatch said "the renderer gets a `clouds` source hand-over": the attribute is `Renderer.cloud_source` (the registry), because `clouds` is the registry's own property name and `renderer.clouds.clouds` would read badly.
- The params are in `params.py` / `view.py`, outside the file list the dispatch named ("register them" needs the registry); `ghost.*` lives in `ghost.py`, but the cloud has no state object of its own and `ViewState` already reaches every node as `frame.s`.
- No UI row for `cloud.*` (the OUTPUT page is A4's; a CAMERA/SYSTEM row is a docs-free follow-up).
- A4's JSON loader is not touched: the registration point is the kind name `cloud` and the constructor `PointCloud(name, role)`; A4 (or whoever lands second) maps `{"kind": "cloud", "role": …}` onto it. If A4 names instance params by node (`cloud.2.size`), the second node should read its own.
- `Hands.TIMED` (A3's note) is untouched; the cloud node is always timed (it only draws inside a scene).
