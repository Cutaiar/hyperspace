# Plan 94 — a body skeleton from the Kinect, and a body mask

**Planned, not scheduled** (2026-11-28). Nothing is built. Size M–L: about
2–2.5 weeks of sessions to the body mask (step B6), the network term (B7)
after and separate. Needs plan 93 (the cloud as a show's node, built) and the
hand mask (#526, built). If 94 is taken by the time this is picked up,
renumber it.

This file is the whole of a scoping conversation with the owner (2026-11-28):
what they asked for, what the code has, what was weighed and dropped, what
the outside world offers, and the design they chose. Read all of it before
writing code; the "why not" sections save re-deriving dead ends.

## The ask

The hand mask (`handmask`, #526) is a "hands quad": the polygon both hands'
thumb and index tips make on screen, as a mask. The owner wants the same for
a body seen by the Kinect — a **body quad** — and for that, a skeleton fitted
to the point cloud.

The a-priori assumptions, the owner's:

- **One actor.** A single person standing somewhere in the frustum.
- **Already isolated.** Background and foreground points are filtered out
  (today: the entry's `near` and `far`; see "the floor" below — it is not
  quite enough).
- **The goal:** a well-fitted, very efficient estimate of where that one
  person's skeleton is, every frame.

## The owner's design (2026-11-28)

In their words: an idealised stick-figure skeleton of tubes joined at
joints is **puppeteered**; each cloud or disparity frame that comes in is
**a suggestion** to it, not the answer. The skeleton keeps its own state —
the last pose and a rolling velocity, an inertial vector — so each frame
starts from a prediction and the fit is easy. The fit is error
minimisation, and its terms — penalties, damping, incentives — are
**composable**, so they can be experimented with one at a time to make the
skeleton behave predictably. If there are too many points to fit against,
downsample them to a representative set of centroids and fit the tubes to
those.

A neural network is welcome too — on the depth picture, or on the infrared
picture — but under this design it is **one more suggestion** (a term), not
the architecture. See "networks" for what exists.

## What the code has (read 2026-11-28)

**The sensor** (`hyperspace/kinect.py`, plan 29's device). An Xbox 360 Kinect
(we own two; a model 1414 on the rig) through libfreenect, loaded inside the
device thread. libfreenect gives depth and nothing else: **no skeleton**.
Microsoft's tracker was the Windows-only Kinect SDK, and OpenNI's NiTE is
discontinued; any skeleton is ours.

- `deproject(depth, focal, o)`: the depth picture (640×480 uint16 mm) → N×3
  float32 metres, every `step`-th pixel and row (2 by default: at most 76 800
  points), cropped to `near`/`far`. Frame: the sensor looks along −z, x
  right, y up, the origin `centre` metres in front of it; `mirror` (on) flips
  x. `FOCAL = 575` px until the sensor says (`Telemetry.focal`).
- `KinectDevice._made` runs on the device thread (`kinect-<role>`), about
  30 Hz, and publishes `cloud:<role>` (`devices.PointCloud`) by one
  reference swap. **The fit belongs on this thread** (or one beside it), not
  the frame thread: the frame thread only reads the newest published pose.
- The motor part reads the **accelerometer** (`freenect_get_mks_accel`,
  `Telemetry.accel`): gravity in the sensor's frame, a free floor normal.
- The video stream is one of off, colour or infrared (`VIDEO`, `Options.video`;
  colour and infrared exclude each other; each runs beside depth). Colour
  needs light and a show is dark; the infrared picture is lit by the
  sensor's own projector, so it works in the dark, but it carries the
  projected dot pattern. With colour on, depth is registered to it
  (`_DEPTH_REGISTERED`), else plain millimetres (`_DEPTH_MM`).
- Pictures: `kinect:<role>/depth`, `/color`, `/ir` (`Picture`, made only while
  held).

**Recordings.** `devices.write_clouds` / `read_clouds` (.npz, version 1) and
`CloudDevice` (`kind = "cloud"`, `file = …`) play a recorded cloud back as a
device, on a loop; `tools/cloud_fixture.py`, `tools/drive_cloud.py`,
`tools/kinect_near.py` are beside. **Only points are recorded, not the depth
picture**: the free-space term and any depth network need the picture (B1).
The hands have the same pattern for tracking frames (`hands/tape.py`).

**The cloud node** (plan 93, `graph.PointCloud`, `view.CloudState`). A shape
with only vertices: `zoom` (its scale), `yaw`, `pitch`, `pan`, copies
(`instances`, `inst_*`), turned by `geometry.turn_matrix`; each copy drawn
with `u_model = T(copy) · scale(copy) · R(yaw, pitch)`. **A joint found in the
sensor's frame reaches the screen through this model matrix, then the
scene's eye** — exactly what the body mask must do.

**The hand mask** (#526, `graph.HandMaskNode`, `graph.hand_polygon`,
`masks.MaskPasses.polygon`, `view.HandMaskState`, `params.declare_handmasks`,
`tests/test_graph_handmask.py`). The template for the body mask: a node with
one geometry port, its polygon projected to the frame's pixels, sorted round
its centre, filled with grow / feather / invert, fading with the fainter
hand, passing nothing (and saying why) with no polygon. Register rows
1210–1214, hand checks 980–981. #526 was about 850 lines with tests.

**Off-thread models.** `segment.py` (plan 39 T4) runs a model per node on a
worker (latest frame wins, one reference swap out, errors said on the node,
libraries imported inside the first job). It already uses Apple Vision
(pyobjc-framework-vision, a dependency) and torchvision on MPS. A network
term follows this pattern.

**Puppets.** Plan 59 (`59-world-objects.md`) has a `puppets` registry: "a
source that sets an object's pose each frame"; the hands are puppeted world
objects (plan 60). Whether the body's joints become world objects is open
(Q4); the fit itself does not need it.

## The design

### State

One idealised skeleton, about 15 joints: head, neck, chest/spine, pelvis,
shoulders, elbows, wrists (hands), hips, knees, ankles (feet). Bones are
**tubes** (capsules: a segment and a radius) of fixed length. The pose is a
root (pelvis position and orientation) plus a rotation per joint —
roughly 30–40 degrees of freedom. It keeps between frames: the pose, a
velocity (a rolling window, damped), and the body's measurements.

**Sizing.** Bone lengths and radii come from an idealised human scaled to
the person's height, measured in the first second or so (the isolated
blob's vertical extent along gravity), then refined slowly by the data terms
or frozen. Freeze is the predictable default.

### Each frame

1. **Predict.** Advance the pose by the damped velocity: where the skeleton
   would be if the data said nothing.
2. **Suggestions.** Build what the terms read: the centroids (below), the
   depth picture for free space, any network's joints with confidences.
3. **Settle.** Minimise the sum of the active terms from the prediction, for
   a **fixed budget** of solver iterations (Gauss–Newton or
   Levenberg–Marquardt, 5–10 iterations). A fixed budget is a fixed cost: a
   frame is never late, it is only less settled.
4. **Update** the velocity from how far the pose actually moved, publish the
   pose (joint positions in the sensor's frame, per-joint confidence, the
   fit's residual, the frame id it answers).

### Points to centroids

The cloud is averaged into a voxel grid (4–5 cm cells is the starting
guess): a body comes to about 300–800 centroids, each with a count (its
weight). A data term then measures every centroid against about 15 tubes —
about 10 000 point-to-segment distances an iteration. Estimated at a few ms a
frame in numpy for the whole settle, **not measured**: measure it first (B3)
before reaching for anything faster. No GPU, no k-d tree needed at this size.

### The terms

Every term has one interface: given the pose and the frame's suggestions, it
returns its residuals and their Jacobian with respect to the pose (or the
gradient), times its **weight**. Terms sum; each can be switched off,
reweighted or replaced alone, live, from the pane. The first set:

| Kind | Term | What it does |
|---|---|---|
| Data | **Centroids → tubes** | Each centroid wants to lie on its nearest tube's surface. A robust loss (Huber or Geman–McClure), so stray points cannot drag the body. |
| Data | **Tubes → data** | Each tube wants points along its length (sample points on each tube; each wants a centroid near it). Without it, a limb that drifts into empty air costs nothing. |
| Data | **Free space** | A tube may not sit where the depth picture shows empty space — in front of a measured surface, along the sensor's ray. This is what keeps an arm out of the torso, and what tells front from behind. |
| Data | **Network joint** (B7) | A spring from a joint to a network's estimate, scaled by its confidence. |
| Body | **Joint limits** | Soft walls at each joint's human range. |
| Body | **Collisions** | Tubes may not pass through each other. |
| Body | **Rest pose** | A weak pull to a neutral stance, so a skeleton that sees nothing relaxes rather than freezing in a strange pose. |
| Time | **Prediction** | Stay near the predicted pose; its weight is the inertia. |
| Time | **Speed limit** | Penalise joint speeds a human cannot reach. |

Centroids → tubes alone is nearest-neighbour fitting: it **only explains
the points that are there**. The tubes → data and free-space terms are the
other direction, and they are why this works where plain ICP drifts.

### Predictable by construction

- **Replay.** Every experiment re-runs the same recording, so two sets of
  weights can be compared on the same seconds.
- **Each term's share, live.** The pane shows each term's contribution to
  the total every frame (and a sparkline): which suggestion is winning.
- **Confidence.** The data terms' residual after settling says how well the
  skeleton matches. The body mask fades on it, as the hand mask fades with
  the fainter hand.
- **Lost and found.** A residual high for some frames (or the blob gone)
  marks the fit lost: the skeleton relaxes towards the rest pose and fades,
  then is **re-seeded** — placed upright on the blob's centroid, scaled, and
  settled with many iterations. Fast swings, a back turned and arms crossed
  will lose it; re-seeding is what makes that recoverable. A network (B7),
  when there, is the better seed. A cheaper geometric seed, if wanted: the
  points farthest from the torso by distance along the body's surface
  (geodesic extrema) are the head, hands and feet.
- **Synthetic people.** A posed tube figure drawn into a fake depth picture
  (and deprojected by `deproject` itself) gives exact ground truth. Each
  term gets a test alone — free space alone must push an arm out of the
  torso; the prediction term alone must carry a moving limb through one
  missing frame.

### The floor

`near`/`far` drops the background but not the floor, which touches the feet
and would pull them into it. Before centroids: take the floor plane from the
accelerometer's gravity (its height by the lowest dense band of points along
it, or a RANSAC plane seeded by that normal), drop points within a few cm of
it, then keep the largest connected blob (on the depth picture's grid —
cheap) to honour "one actor".

### Mirror and left/right

`mirror` flips x. The skeleton's left and right are the person's, so the fit
must know whether the cloud is mirrored, and say which convention the
published joints use. With the person's back turned the cloud cannot tell
left from right; the prediction term carries identity through a turn, and a
re-seed may swap them. Expect it, and say it in the hand checks.

## The body mask

A copy of the hand mask: `bodymask[.n]`, a mask node with one port, its
polygon from **four joints**, projected to the frame's pixels and filled by
`masks.MaskPasses.polygon`, with grow / feather / invert, fading with the
fit's confidence, passing nothing with no body (and saying why). Which four
joints is Q1; once the full skeleton exists, any four can be offered as a
choice.

What its port takes is Q2. The joints are in the sensor's frame; they reach
the screen through the cloud node's model matrix (pose and scale, plan 93)
and the scene's eye. The likely answer is that the **cloud node publishes
the skeleton** beside its points and the body mask takes a cloud node, as
the hand mask takes a hands node — then the cloud's pose and the mask always
agree. A separate `body` node is the alternative.

Known follow-ups of #526 apply here too: a cut over a resized picture of
another aspect misplaces a frame-sized mask.

## Networks (researched 2026-11-28)

None is a drop-in; each needs a day's test on our recordings. Under the
design above, a network's joints are a term (B7), and the best use is the
re-seed.

**The dataset nearest our sensor.** ITOP (Haque et al., ECCV 2016): 20
people, 15 action sequences, 15 joints, recorded with Asus Xtion — the same
PrimeSense structured-light design as the 360 Kinect, so the least domain
shift we will find. Its front-view track is a person facing the sensor (our
case); about 40k train / 10k test pictures a view. The metric is mAP at
10 cm. Caveats: only about 45% of its joints are human-validated and scores
count those; the licence is listed as CC BY 4.0 by an aggregator, not
confirmed at the source.

| Model | Input | ITOP front | Licence, weights | For us |
|---|---|---|---|---|
| **A2J** (ICCV 2019), `zhangboshen/A2J` | One depth picture, cropped round the body (needs a centre and box) | 88.0% | MIT; `ITOP_side.pth` / `ITOP_top.pth` on Google Drive and Baidu | **The best candidate.** A plain 2D CNN (ResNet backbone, anchors), no custom CUDA ops, so it should run on MPS (untested). Our isolated blob gives the centre and box. Written for PyTorch 0.4–1.2 on an NVIDIA 1080 Ti: needs a port. No speed stated. Repo last pushed 2022. |
| **SPiKE** (Pattern Recognition 2024), `iballester/SPiKE` | A short sequence of segmented point clouds | 89.19% | MIT; ITOP-side weights on a TU Wien share | Eats exactly our isolated cloud, but needs PointNet++ CUDA layers compiled (`modules/setup.py`): will not run on the Mac as written; a few days to rewrite those ops in plain torch, slower. |
| AdaPose | ? | 93.38% (aggregator only) | ? | No paper or code found; verify before trusting. |
| V2V-PoseNet | Voxels | 88.7% | — | Heavy (3D convolutions); the paper's best result is an ensemble of ten. |
| ORPose-Depth (MICCAI 2019), `CAMMA-public/ORPose-Depth` | Low-res depth | — | Licence `NOASSERTION` | Operating-room data. Skip. |
| Azure Kinect Body Tracking | Time-of-flight depth | — | Windows / Linux, NVIDIA GPU; the product is discontinued | No. |
| Apple Vision 3D body pose (`VNDetectHumanBodyPose3DRequest`, macOS 14+) | A colour image; depth (`AVDepthData`) optional, refines | — | System framework, already a dependency | Built for RGB; on a depth or infrared picture likely to fail. A cheap check only. |

**Infrared.** "Thermal" pose models (OpenThermalPose / OpenThermalPose2,
`IS2AI/OpenThermalPose`, MIT code, YOLOv8/YOLO11-pose weights on Hugging
Face; LLVIP-Pose, ACCV 2024 workshop) are trained on long-wave thermal
cameras — emitted heat. The Kinect's infrared is near-infrared reflected from
its own laser dots: a different picture; those weights do not transfer. Also
note the Ultralytics YOLO code those weights are built on is, as far as we
know, AGPL-3.0: check before shipping anything on it. What does transfer is
LLVIP-Pose's finding that **greyscale-COCO-pretrained models carry over to
infrared**. So the infrared route is: suppress the dot pattern (a blur at
reduced resolution may be enough; Ringaby & Forssén, ICCV 2011, tune a filter
for exactly this), run a standard 2D body-pose model — Apple Vision's 2D body
pose (`VNDetectHumanBodyPoseRequest`, already a dependency, Neural Engine) or
RTMPose (Apache-2.0) — and read each joint's depth from the depth picture to
lift it to 3D. More steps than A2J, but on far better-trained models, and
the infrared picture works in the dark.

Sources: A2J [arXiv 1908.09999](https://arxiv.org/abs/1908.09999),
[code](https://github.com/zhangboshen/A2J); SPiKE
[arXiv 2409.01879](https://arxiv.org/abs/2409.01879),
[code](https://github.com/iballester/SPiKE); ITOP
[arXiv 1603.07076](https://arxiv.org/abs/1603.07076); ITOP front-view
[leaderboard](https://hyper.ai/en/sota/tasks/pose-estimation/benchmark/pose-estimation-on-itop-front-view);
[ORPose-Depth](https://github.com/CAMMA-public/ORPose-Depth);
[OpenThermalPose](https://github.com/IS2AI/OpenThermalPose);
[LLVIP-Pose](https://openaccess.thecvf.com/content/ACCV2024W/AWSS/html/Cormier_Leveraging_Thermal_Imaging_for_Robust_Human_Pose_Estimation_in_Low-Light_ACCVW_2024_paper.html);
[Ringaby & Forssén](https://users.isy.liu.se/cvl/perfo/papers/ringaby_iccv11.pdf);
[Azure Kinect body tracking](https://learn.microsoft.com/en-us/azure/kinect-dk/body-sdk-setup);
[Apple Vision 3D body pose](https://developer.apple.com/documentation/vision/vndetecthumanbodypose3drequest).
Licences checked on GitHub's API 2026-11-28 (A2J, SPiKE, OpenThermalPose
MIT); weight links read from the READMEs, not downloaded.

## What was weighed and dropped

- **A heuristic skeleton first** (PCA torso + geodesic extrema for head,
  hands and feet, then a full model fit "+2–3 weeks" later). The owner
  pointed out that a model fit on downsampled centroids with a predicted
  start is cheap; the estimate was revised down. The extrema survive only as
  a possible re-seed.
- **Raw nearest-neighbour rigid matching against all the points.** Too many
  points, and one-directional (see the terms); centroids and the two-way
  terms replace it.
- **Colour + Apple Vision 2D pose lifted by registered depth.** Two or three
  days and no training, but colour needs light and the show is dark. The
  infrared variant replaces it (above).
- **A network as the architecture.** Kept as a term; the puppet is the
  architecture (the owner's call).

## Build order

Each step a PR; B1 first because every later step is tuned against it.

- **B1 — recordings and synthetic people (~2 days).** Record depth (and the
  infrared picture, for B7) beside the cloud: extend `write_clouds`'s file or
  a sibling format, and let `CloudDevice` play the picture back too. A
  generator of posed tube figures into fake depth pictures, deprojected by
  `kinect.deproject`, with the true joints. **Needs a rig session**: a few
  minutes of one person walking, turning, raising and crossing arms,
  sitting down, leaving and coming back — on the Mac.
- **B2 — isolate and reduce (~1 day).** Floor from gravity, largest blob,
  voxel centroids with counts. Pure numpy, tested on B1.
- **B3 — the skeleton and the settle (3–5 days).** The joint tree, tube
  geometry, forward kinematics, the term interface, the fixed-budget solver;
  centroids → tubes, joint limits, prediction, rest pose. Measure a settle's
  cost on the device thread first.
- **B4 — the rest of the terms and recovery (2–3 days).** Tubes → data, free
  space, collisions, speed limit; sizing; lost detection and re-seed;
  velocity window.
- **B5 — seeing it (~1–2 days).** In the Kinect pane (`ui_kinect.py`): each
  term's weight and live share, the residual, lost/found; a stick-figure
  overlay (the radar, or the depth picture). A way to draw the skeleton as
  geometry in a scene is a nice-to-have.
- **B6 — the body mask (1.5–2 days).** As the hand mask, per Q1–Q2: node,
  params, graph wiring, register rows, hand checks, tests.
- **B7 — a network term (separate; 1 day to test, 3–4 to integrate).** Test
  A2J (port; reproduce ~88% on ITOP's test set; time on MPS; run on B1's
  recordings) and the infrared route; whichever is fast (< ~15 ms) and steady
  becomes a confidence-weighted joint term and the re-seed, on
  `segment.py`'s worker pattern. A2J's port and the ITOP check can run in a
  cloud session if the network allows Zenodo and Google Drive; timing and
  the real-Kinect test need the Mac.

## Questions for the owner

1. **Which four joints make the body quad?** Both hands and both feet is the
   natural pick; with a full skeleton any four can be a choice on the node.
2. **What does the body mask take?** A cloud node that publishes its
   skeleton (recommended: its pose and the mask always agree), or a new
   `body` node.
3. **The published joints' convention** under `mirror`: the person's left,
   or the screen's?
4. **Are the joints world objects** (plan 59's puppets), routable and
   grabbable like the hands, or only the mask's input for now?
5. **Lanes.** Should joint positions and speeds also be control lanes (the
   hands' dance sources are the precedent, plan 24), or the mask only?
</content>
</invoke>
<invoke name="Bash">
<parameter name="command">cd /home/user/hyperspace/hyperspace-python && python3 - <<'EOF'
p='docs/plans/README.md'
s=open(p).read()
anchor=next(l for l in s.splitlines() if l.startswith('- [`93-point-cloud-node.md`]'))
entry='- [`94-body-skeleton.md`](94-body-skeleton.md) — plan 94, **planned, not scheduled** (2026-11-28; size M–L, needs 93 and the hand mask #526): a skeleton for one person seen by the Kinect, and a body mask (the "body quad") as the hand mask is the hands\'. An idealised skeleton of tubes, puppeteered: each frame is a suggestion, the fit a fixed budget of error minimisation over composable terms (centroids → tubes, tubes → data, free space, joint limits, collisions, rest pose, prediction, speed limit) from a predicted start, on downsampled centroids. What the code has, the depth and infrared networks researched (A2J the best candidate, as a term and the re-seed), what was dropped, build order B1–B7, five questions.'
s=s.replace(anchor, anchor+'\n'+entry,1)
open(p,'w').write(s)
EOF
git add docs/plans/94-body-skeleton.md docs/plans/README.md && git commit -q -m "Plan 94: a body skeleton from the Kinect, and a body mask (planned)

The scoping of a body quad for the Kinect, as the hand mask is the hands':
an idealised tube skeleton puppeteered by composable fit terms, the code
it builds on, the depth and infrared networks researched, what was
dropped, the build order and the owner's open questions.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012HeFHyUAHzuE8YKH3wB8Jf" && git push -u origin claude/loving-feynman-yb88e2 2>&1 | tail -2