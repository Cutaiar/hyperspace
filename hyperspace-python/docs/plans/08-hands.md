# Plan 08 — Ultraleap hands as the performing surface

**After plan 07.** The hands become the main way to perform: two hands in
an enclosed box over an Ultraleap camera, six degrees of freedom each. The
APC40 stays on presets, scenes and master controls. Code: `hyperspace/hands.py`,
`tools/hands_probe.py`, `tests/test_hands.py`; small hooks in `midi.py`
(`MidiIO.inject`), `routing.py` (`hand:<i>` lanes), `ui_routing.py`,
`config.py` (`[hands]`) and `app.py`.

## Shape

```
Ultraleap service ──(leap bindings, SDK thread)──▶ LeapSource.latest()
                                                        │ once per render frame
                                                   HandsIO.poll
             ┌───────────────┬──────────────────────────┼─────────────────────┐
     MidiIO.inject      MIDI out port            Router.feed("hand")    presence notes
  (Learn, bindings.json,  ("Hyperspace Hands",    (float lanes for        (note 120/121
   same table as APC40)    virtual — for a DAW)    mod/replace routes)     on/off)
```

Each hand axis is a 7-bit CC on MIDI channel 16 (0-based 15), CC 102–107
for the left hand and 108–113 for the right with the default six DOFs.
Those are in MIDI's undefined range, clear of every APC40 number, and on a
channel the APC40 never uses. The APC's device-knob rows match any channel,
which is why the hands don't use CC 16–23.

## Degrees of freedom: what Ultraleap reports, and how it becomes 0–127

LeapC (through the `leap` Python bindings) reports per hand, per frame:
`palm.position` / `palm.velocity` in **mm** (origin at the camera, +y up
away from it, +z toward the performer in desktop mode); `palm.normal` and
`palm.direction` as **unit vectors**, plus `palm.orientation` as a
quaternion; `grab_strength` / `pinch_strength` in **0–1**; `grab_angle` in
**radians** (0 open … π fist); `pinch_distance` in **mm**; `confidence` in
0–1; `type` left/right.

| DOF (config name) | Derived from | Unit | Default range → 0…127 |
|---|---|---|---|
| `x` | palm.position.x | mm | left −220…20, right −20…220 |
| `y` (height) | palm.position.y | mm | 100…350 |
| `z` (depth) | palm.position.z | mm | −100…100 |
| `roll` | atan2(n.x, −n.y) | degrees | −90…90 (thumb up = up, both hands) |
| `pitch` | atan2(d.y, −d.z) | degrees | −60…60 (fingers up = up) |
| `yaw` | atan2(d.x, −d.z) | degrees | −45…45 (fingers outward = up, both hands) |
| `grab` | grab_strength | 0–1 | 0…1 |
| `pinch` | pinch_strength | 0–1 | 0…1 |
| `grab_angle` | grab_angle | rad → degrees | 0…180 |
| `pinch_mm` | pinch_distance | mm | 15…100 |

The default is the palm's rigid-body pose, `x y z roll pitch yaw`. Any
six (or any count, if the CCs fit) can go in `[hands] dofs`. The mapping,
per axis, per tracking frame:

1. `u = (v − lo) / (hi − lo)`, flipped if `invert`. The ranges come from
   `<home>/hands.json`, written by the calibration sweep; the table above
   is only the fallback.
2. **One Euro filter** on u. Its cutoff is `min_cutoff` (1 Hz) at rest and
   rises by `beta · |speed|` (β = 4 per u/s), so a still hand doesn't
   shimmer and a fast gesture doesn't lag. Tuning for the box:
   `min_cutoff` down if held poses shimmer, `beta` up if fast moves feel
   late.
3. Clamp to [0, 1], then `round(u · 127)` with **hysteresis**: the value
   moves only once u is 0.5 + 0.35 steps past the last one sent, so a hand
   resting on a step boundary doesn't toggle between two values. A CC goes
   out only when its value changes.

When a hand leaves (or drops below `min_confidence`), its CCs hold their
last value, its presence note goes off, and its `hand:<i>` lanes read NaN,
so mod/replace routes let go and the base value returns. On re-entry the
filter starts fresh, so the first value is where the hand actually is.

**7-bit vs float.** 127 steps is coarse for a slow, large visual move
(a rotation rate, say). For those params, route the `hand:<i>` lane (float
u, the same axis) on the ROUTING page instead of learning the CC. Use the
CCs for things MIDI Learn, the APC40 workflow and a DAW should see.

## Performing with it

- **Map by Learn:** right-click a panel control → Learn, then move the one
  axis you want. All six axes of a hand move at once, so during Learn only
  the axis that has travelled furthest since Learn began (≥ 25 % of its
  range) is forwarded. A learned hand row gets no soft pickup (the hand
  owns the value) and no APC LED feedback.
- **Map in a DAW:** set `out = "Hyperspace Hands"` (a virtual CoreMIDI port
  is created; verified it opens and is visible to other apps). For the
  DAW's own learn, `tools/hands_probe.py --out "Hyperspace Hands" --solo
  right.pitch` sends just that axis.

## Install (the SDK is not on this machine yet)

1. Install **Ultraleap Hand Tracking** for macOS (Gemini ≥ 5.17). It lands
   at `/Applications/Ultraleap Hand Tracking.app`, and the SDK is in
   `Contents/LeapSDK`.
2. The bindings ship precompiled only for Python 3.8, and this project is
   on 3.12, so build the cffi module from source:
   ```
   git clone https://github.com/ultraleap/leapc-python-bindings
   cd leapc-python-bindings
   uv pip install build cffi
   uv run python -m build leapc-cffi
   uv pip install leapc-cffi/dist/leapc_cffi-0.0.1.tar.gz
   uv pip install -e leapc-python-api
   ```
   (If the SDK is elsewhere, set `LEAPSDK_INSTALL_LOCATION`.)
3. `[hands] enabled = true` in `~/Hyperspace/config.toml`; set `mode` to
   `"screentop"` if the camera looks down from the box's lid.
4. `uv run python tools/hands_probe.py` shows each axis live (native value,
   u, the CC value). Then run `--calibrate 30` and sweep each hand through
   every axis, end to end. That writes `hands.json` (2nd–98th percentile
   per axis). Flip `invert` there by hand if a direction feels backwards.

## Not yet verified (needs the camera and the box)

- [ ] Bindings build against the installed Gemini on Apple Silicon / 3.12.
- [ ] Listener callback names beyond `on_tracking_event` / `on_connection_event` /
      `on_device_event` (the lost-events only update the status text).
- [ ] Angle signs in the box's actual mounting. The formulas assume the
      desktop frame; with `screentop` the SDK should re-express coordinates,
      but check roll/pitch/yaw directions in the probe.
- [ ] Filter/hysteresis tuning by feel; latency end to end.
- [ ] Cross-talk: how independently yaw/pitch can be held without moving
      x/y. If yaw is hard to isolate, `grab` is the natural swap-in.
