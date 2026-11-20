# Volumetric crowd capture: distilled brief

The goal: a multi-camera rig, built around the OmniVision OV9281 global-shutter
sensor, that reconstructs a dance floor as a low-error volume and tracks each
person in it as a persistent stick figure. Its first consumer is our own
apps: the Hyperspace renderer (which already takes point clouds), lighting,
and later the volumetric LED display (PixelPusher strips, where each strip is
one (x, y) pixel and its LEDs are the z axis).

Source: a Gemini conversation, "Evolution of Xbox Kinect Hardware"
(9 prompts). This brief keeps what we can act on. Gemini's numbers (prices,
latencies, irradiance) are **unverified estimates** unless marked otherwise.
Where Gemini contradicts itself or is likely wrong, this brief says so under
[Corrections](#corrections-and-contradictions-in-the-transcript).

---

## 1. Decisions the transcript reached

| # | Decision | Status |
|---|---|---|
| D1 | Global-shutter camera array, hardware-triggered, is the path. Azure Kinect is out on cost. | Decided by us |
| D2 | Sensor: OV9281, 1 MP (1280×800) monochrome, no IR-cut filter, M12 lens. | Leaning; see Q3 |
| D3 | Sync: one microcontroller (Raspberry Pi Pico) drives a 3.3 V trigger pulse to every camera's TRIG/FSYNC pin. Target ≤1 µs skew. | Leaning |
| D4 | Illumination: 850 nm (not 940 nm) for ~2× sensor efficiency, with an 850 nm bandpass filter on every lens, so stage lights, lasers and screens are invisible to the rig. Switch to 940 nm only if VR headsets or Lighthouse tracking share the room. | Leaning |
| D5 | Host: Mac M3 Max, PyTorch MPS for the GPU stages. | Assumed by Gemini; see Q6 |
| D6 | Tracking is the point; the watertight mesh is secondary. Each person is a fitted stick figure driven by the cloud, carried frame to frame by a velocity prior. | Decided by us |
| D7 | Kinect v1 (360) is ruled out for overlapping views (structured-light patterns blind each other). Kinect v2 is a fallback for statistics only, not meshes. | Gemini's verdict; see C6 |

---

## 2. Pipeline (what we'd actually build)

```
Pico trigger ─► N × OV9281 (+850 nm filter, IR strobe/flood)
                     │ frames (mono 8-bit, same instant)
                     ▼
           [per camera] background model → binary silhouette mask
                     │
                     ▼
           [GPU] space carving into a voxel grid (keep voxels inside every mask)
                     │
        ┌────────────┴─────────────┐
        ▼                          ▼
  Branch A: surface          Branch B: tracking
  density grid → (blur) →    floor clip → voxel downsample (~15k pts)
  Marching Cubes mesh          → 1. predict each person's pose from velocity
                               → 2. claim points by nearest capsule (< 0.35 m)
                               → 3. DBSCAN on unclaimed points → spawn new IDs
                               → 4. fit capsules (bidirectional Chamfer, 6–10 Adam steps)
                               → 5. emit tracks
        │                          │
        └──────────┬───────────────┘
                   ▼
    voxel grid / cloud / mesh / tracks  →  Hyperspace, lighting, LED display
```

### Tracker parameters Gemini proposed (starting values, to be tuned)

- **Stick figure:** 10 capsules, 18 DoF. Root xyz and yaw (4), spine
  pitch/roll and scale (3), four limbs × (2-DoF ball + 1-DoF hinge) (12).
  Radii: torso 0.14 m, limbs 0.06 m. About 40 sample points along the
  skeleton.
- **Velocity prior:** a ring buffer of the last 8 poses, an exponentially
  weighted velocity, damping 0.85.
- **Assignment:** a point goes to the nearest predicted capsule within 0.35 m.
- **Birth:** DBSCAN (eps 0.25 m, min_samples 40) on unclaimed points only. A
  cluster taller than 1.1 m with more than 100 points spawns a new ID.
- **Death:** fewer than 30 claimed points for 15 frames (~0.5 s).
- **Loss:** `mean(cloud→skeleton) + 0.8·mean(skeleton→cloud) + 0.25·‖Θ − Θ̂‖²`.
  The skeleton→cloud term is what stops the limbs collapsing into the torso.
  Add joint limits (hinges ≥ 0).
- **Budget claim:** about 2.5 ms for 15 people on an M3 Max (unverified).

### Calibration

- Intrinsics per camera, then extrinsics from a large rigid ChArUco board
  (800×600 mm) shown to overlapping cameras, solved in OpenCV.
- Output: one 4×4 camera-to-world matrix (and K and distortion) per camera in a
  JSON file.

---

## 3. Software interfaces

### Already in this repo (use, don't reinvent)

- `devices.PointCloud` (`hyperspace-python/hyperspace/devices.py`): N×3
  float32 read-only points, `t`, `frame`, optional colours, `bounds`. It is
  published on the registry as `cloud:<role>` and drawn by the graph's
  `PointCloud` node.
- `devices.CloudDevice`: plays a recorded `.npz` (`CLOUD_FILE_VERSION = 1`,
  `write_clouds`) at its own rate. **This is how we can build and test the
  whole downstream pipeline before buying anything** (see Phase 0).
- `DECISIONS.md` row: "a point cloud is a source type, not a scalar lane …
  the Kinect and the live sensors are plan 29." The capture rig is plan 29's
  sensor.
- The OSC device (UDP, default `0.0.0.0:9000`) is the existing inbound path
  for scalar telemetry.

### To define (proposals, not decided)

| Interface | Shape | Producer → consumer |
|---|---|---|
| **Rig calibration file** | JSON: per camera `serial`, `K` (3×3), `dist`, `T_cam_to_world` (4×4), resolution; world frame and units declared once | calibration tool → carver |
| **Camera frame bundle** | N masks or frames sharing one trigger index (trigger count, not wall clock, is the key) | capture → carver |
| **Voxel grid** | dense uint8/float occupancy, `origin`, `voxel_size`, `dims`, frame id | carver → mesh, tracker, **LED display** |
| **Point cloud** | existing `PointCloud` / `.npz` v1 | carver or Kinect → Hyperspace |
| **Tracks** | per frame: `[id, root_xyz, yaw, vel_xyz, joints (or the 18 params), hand_heights, confidence]` plus a crowd `energy` scalar (0–1) | tracker → Hyperspace, lighting (OSC / Art-Net / sACN / DDP), display |
| **Mesh** (optional) | vertices and normals from Marching Cubes | carver → renderer |

Gemini's telemetry packet is `[id, root_xyz, vel_xyz, hand_heights, total_energy]`
over OSC/UDP as JSON or binary. A decision is needed on whether tracks enter
Hyperspace as a new source type (like `cloud:`), or as OSC scalars through
the existing router (see Q9).

**The LED display link:** the voxel grid *is* the display format. A
PixelPusher volume is a voxel grid of size (strips_x × strips_y × LEDs per
strip). Resampling the occupancy grid (or rasterising the tracks or mesh) into
that grid is the whole adapter. So **the world frame must name its vertical
axis explicitly**. Gemini's code uses Y-up (the floor box is `0 < y < 2.5`,
yaw about Y), while the display's strips run along z.

---

## 4. Buy lists

Prices are Gemini's, unverified, and inconsistent across the transcript (see
C1). Verify every SKU's trigger support before buying more than two units
(Q1).

### Phase 1: two-camera bench (~$130–$180)

| Item | Qty | Est. each | Notes |
|---|---|---|---|
| OV9281 module, UVC, **with an exposed external trigger pin**, M12 mount | 2 | $40–65 | The trigger pin and how to arm it are a gating question (Q1) |
| Raspberry Pi Pico | 1 | $5 | Trigger generator |
| Jumper wire, shared ground | — | ~$5 | |
| 850 nm M12 bandpass filters | 2 | ~$12 | Optional on the bench, cheap, buy now |
| A fast millisecond timer display (phone or monitor) | — | — | Sync check |

### Phase 2: four to six cameras, small floor (~$380–$440 for 4, per Gemini)

| Item | Qty | Est. each |
|---|---|---|
| OV9281 trigger-capable modules (2–4 more) | 2–4 | $40–65 |
| 850 nm M12 bandpass filters | 4–6 | ~$12 |
| 850 nm wide-angle IR floods (e.g. Tendelux DI20 class, 90°) | 2–4 | $25–55 |
| USB: hub and/or active extension cables (see C2: USB 2.0 shared-bandwidth problem) | 4–6 | ~$22 |
| ChArUco board, 800×600 mm, rigid (foam board or dibond print) | 1 | ~$30–60 (my estimate) |
| Mounts for 2.8–3.5 m overhead (clamps or truss) | 4–6 | TBD |

### Phase 3: 8×8 m room (Gemini's BOM, ~$767, and incomplete)

| Item | Qty | Est. each | Total |
|---|---|---|---|
| 30 W 850 nm wide-angle (120°) IR floods, **overhead grid** at 2.8–3.2 m | 8 | $35 | $280 |
| 12 V 30 A PSU (Mean Well LRS-350-12) | 1 | $38 | $38 |
| Global-shutter cameras (OV9281, or 2–3 MP: OV2311 / IMX296 with 6 mm lenses) | 6–8 | $40 | $240+ |
| 850 nm M12 bandpass filters | 6–8 | $12 | $72+ |
| Raspberry Pi Pico | 1 | $5 | $5 |
| Active USB extensions, 10 m | 6–8 | $22 | $132+ |

**Missing from that BOM:** lenses (if not bundled), mounts and truss, trigger
cabling and line drivers for 10 m runs (C5), the host USB topology (C2),
power distribution for the floods, and the calibration board.

### Optional DIY pulsed strobe pod (instead of continuous floods), ~$25–40 each

- An 850 nm COB LED (50–100 W), or 4–6 high-power emitters (Osram Oslon
  Black IR, Luminus SST-10-IR) overdriven to 3–5 A pulsed at under 5% duty and
  under 5 ms.
- A logic-level N-MOSFET low-side driver (IRLZ44N or a gate driver), switched
  by the same trigger, from a 12 V rail.
- **Must be diffused** (≥60° emission) to stay in IEC 62471 exempt or RG1. Never
  use collimated LEDs or bare VCSELs.

### Kinect v2 fallback (only if we pivot), ~$360–$535 for 4 on the Mac

- Used Kinect v2 sensors ($25–40) and 12 V USB 3.0 adapters ($20–40).
- **One USB 3 host controller per sensor.** On a Mac: 3 sensors on the 3 TB
  ports, plus a 4th through a dock with its own PCIe USB controller (e.g.
  ASMedia ASM3142), or a TB PCIe chassis (~$350+) with a StarTech PEXUSB3S44V
  (4 discrete Renesas controllers).
- On Linux: the same card, plus `usbcore.usbfs_memory_mb=512`.
- Power: 12 V at about 2.67 A each.

---

## 5. Open questions and ambiguities

Ordered by how much they block.

1. **Q1: Which exact OV9281 module, and how is its trigger armed?** Gemini
   claims Arducam UVC modules expose TRIG, and arms them with
   `v4l2-ctl --set-ctrl=trigger_mode=1`. That is not a standard UVC control,
   and **v4l2 does not exist on macOS** (our target host). We need a SKU whose
   external trigger is documented, plus a way to enable it from macOS: a vendor
   SDK, a UVC extension unit, or a one-time setting that persists. *This gates
   every purchase beyond two units.*
2. **Q2: Can silhouette carving separate people in a crowd at all?** This is
   the biggest technical risk, and Gemini under-weights it. A visual hull of a
   dense crowd from 4–6 perimeter cameras is one large blob, with phantom
   "ghost" volumes in the gaps no camera can see between bodies. Gemini's only
   mitigation is to mount high (2.8–3.5 m, ~40° down). The tracker's velocity
   prior helps with brief merges, not with a packed floor. **We must test
   this with recorded multi-person data before scaling.** Fallbacks that reuse
   the same cameras:
   - (a) more overhead or top-down views.
   - (b) Paired OV9281s and a static IR speckle projector, for active stereo.
     This is real depth, the same hardware plus a projector, and Gemini's
     option 3.
   - (c) 2D pose detection per view, triangulated across views. Gemini didn't
     raise this; it is a known approach.
3. **Q3: What capture area is the target?** "8 meters squared" was ambiguous
   in the conversation itself, and Gemini answered both readings.
   - **8 m²** (about 2.8×2.8 m): four corner cameras at 2.2 m, about 2 mm/px,
     about $120–160 of lighting.
   - **8×8 m (64 m²)**: an overhead light grid, 6–8 cameras, and about
     6 mm/px with 1 MP sensors (a forearm is 10–12 px). That likely forces
     2–3 MP sensors.
4. **Q4: What resolution do we need, and how does it relate to the LED
   display's?** Gemini defaults to 64³ or 128³ grids. Over 8 m, 64³ is
   125 mm voxels, too coarse for limbs. Tracking wants about 2–3 cm voxels
   (e.g. 400×400×125 over 8×8×2.5 m). The display wants whatever its strip
   grid is. What is the display's strip count and LEDs per strip?
5. **Q5: Lighting plan: continuous floods or a triggered strobe?** Gemini
   recommends both in different answers. Off-the-shelf floods are continuous
   (simple, more heat, more ambient IR). Strobes are triggered (more peak
   power, ~4.5% duty) but are custom hardware. Decide after the Phase 1 tests.
6. **Q6: Host machine?** Gemini assumed a Mac M3 Max (a laptop) for every
   later answer. Is that the venue machine? It shapes:
   - USB topology: a Mac has 3 TB buses.
   - Trigger control: no v4l2 on a Mac (Q1).
   - libfreenect2 (Kinect path): OpenCL is deprecated on macOS.
   - The DBSCAN choice: no cuML; use sklearn on the downsampled points.
   
   Alternative worth pricing: **a Raspberry Pi 5 per 1–2 cameras** doing
   silhouette extraction at the edge and sending masks over Ethernet. This
   solves cable length and USB bandwidth at room scale. Pi-native
   global-shutter cameras with documented external trigger exist.
7. **Q7: Background subtraction under club conditions.** Fog/haze (it
   scatters IR), moving people as the "background", and reflective floors. Does
   the 850 nm bandpass with our own illumination give stable masks? Only a
   test will answer it.
8. **Q8: Frame rate and latency target.** Gemini mixes 30 and 60 fps. What
   end-to-end latency (photon to light, or photon to LED) is acceptable?
9. **Q9: How do tracks enter Hyperspace?**
   - As a new source type next to `cloud:`, or
   - as OSC scalars per ID through the router, or
   - as a separate process feeding both Hyperspace and the lighting desk?
   
   And who owns the world frame and units?
10. **Q10: PixelPusher side.** This was not covered in the transcript. We
    need the display's geometry, its refresh rate, and how the volume is
    addressed (one PixelPusher per N strips, the protocol and port, and
    bandwidth per frame).
11. **Q11: Do we use the two Xbox 360 Kinects we already own?** Gemini rules
    them out for overlapping views. One Kinect looking straight down, or two
    with non-overlapping views, is still a free way to record real depth of
    people and develop the tracker now.

---

## 6. Corrections and contradictions in the transcript

- **C1: Camera price.** OV9281 modules are quoted at $35–45, then $40, then
  $55–65 each. Budget for the high end.
- **C2: USB bandwidth (likely wrong).** The last answer says to use **USB 2.0**
  UVC modules at 150–250 Mbps each, "all four through a single standard USB
  hub." Four × 150–250 Mbps is 600–1000 Mbps. A USB 2.0 bus is 480 Mbps
  nominal (about 300 usable), and USB 2.0 devices on a USB 3.0 hub still share
  that hub's single USB 2.0 path. Uncompressed 1280×800 at 60 fps, 8-bit, is
  about 490 Mbps for one camera.
  - Expect either MJPEG, lower resolution or frame rate, or USB 3 modules.
  - Spread the cameras across host controllers.
  - Earlier answers assumed USB 3, which is consistent with this.
- **C3: Trigger setup is Linux-only.** The `v4l2-ctl` steps are Linux-only,
  but the host is a Mac (Q1, Q6).
- **C4: Code is a sketch.** `compute_capsule_samples_local` is undefined, and
  the forward kinematics are a placeholder. The latency figures (<6 ms grid
  and mesh, ~2.5 ms fit, <8 ms total) are claims, not measurements.
- **C5: Trigger wiring at room scale.** A 3.3 V single-ended trigger in a star
  to cameras 10 m away, with ground offsets between powered devices, is fragile.
  Plan a differential (RS-422) or opto-isolated trigger distribution beyond
  bench scale.
- **C6: Kinect claims are overstated in both directions.**
  - "Kinect v2 can't do surfaces" overstates it: multi-Kinect v2 TSDF capture
    is common, though unsynced.
  - "Kinect v1 is impossible to overlap" ignores the known vibration-motor
    mitigation for structured-light crosstalk.
  
  Neither changes the decision; both are relevant to Q11.
- **C7: Grid resolution.** "Marching Cubes on 64³" is fine for a 2.8 m stage
  and coarse for an 8 m room (Q4).

---

## 7. Timeline (proposed sequencing; Gemini gave phases, not dates)

Each phase has an exit criterion. Durations are rough guesses for one part-time
builder.

| Phase | Work | Exit criterion | Rough effort |
|---|---|---|---|
| **0: Software first, no purchase** | Write the calibration JSON schema, voxel-grid and tracks types. Build the tracker on synthetic or recorded clouds through `CloudDevice`. Record real people with the existing 360 Kinect (Q11). Also synthesise multi-view silhouettes from a simple scene to test carving and the crowd-merge risk (Q2). | A single-person stick figure follows a raised arm or a kick without collapse. Carving of a synthetic 5-person group is measured. | 1–2 weeks |
| **1: Two-camera bench** | Buy 2 trigger-capable OV9281s and a Pico. Wire trigger and ground at 30 Hz. Confirm both cameras freeze the same millisecond. Answer Q1 on the real host. | Same-frame sync is verified; the trigger is armed from the target host. | 1 week (+ shipping) |
| **2: Calibrate and carve** | ChArUco extrinsics written to JSON. Background masks. GPU carving, then Marching Cubes and cloud, into Hyperspace through `cloud:`. | A live carved person in Hyperspace at ≥30 fps. | 1–2 weeks |
| **3: Track** | Velocity prior, capsule claiming, DBSCAN birth and death, batched fitting. Tracks output (Q9). | 2–3 people tracked with stable IDs through a crossing. | 2–3 weeks |
| **4: IR and scale to 4–6** | Bandpass filters, floods or strobes, overhead mounts, robust trigger distribution. Decide Q3, Q5 and Q6. | Stable masks under stage lighting and haze. Crowd separation measured; this is the go/no-go on silhouettes versus the stereo fallback (Q2). | 2–4 weeks |
| **5: Outputs** | Tracks to lighting (OSC, Art-Net, sACN). Voxel grid to the PixelPusher volume (Q10). | The LED volume shows the live crowd. | Depends on the display build |

**Go/no-go gates:** after Phase 1 (is the trigger workable on our host?) and
after Phase 4 (does carving separate a real crowd, or do we add stereo pairs
or pose triangulation?).
