# Plan 08 — Ultraleap hands as the performing surface

**After plan 07.** The hands are the main way to perform: two hands in an
enclosed box over an Ultraleap camera, six axes each. The APC40 stays on
presets, scenes and master controls. The goal is **few controls, each
completely predictable**, not many. The 12 axes are shaped as analog
signals, and there are no gesture vocabularies to teach.

Code: `hyperspace/hands.py` (source, setup, adapter), `hand_signal.py`
(the pure signal chain), `ui_hands.py` (the HANDS page),
`tools/hands_probe.py`, `tests/test_hands.py`. Small hooks in
`routing.py` (`hand:<i>` sources, `Router.drive`), `params.py`
(`Param.glide`), `midi.py` (`MidiIO.learn_source`), `ui.py`, `config.py`
and `app.py`.

![HANDS page with two synthetic hands](assets/08-hands/hands.png)

## Shape

```
Ultraleap service ─(leap bindings, SDK thread)─▶ LeapSource.latest()
                                                      │ once per render frame
                                                 HandsIO.poll(dt)
                     per axis: norm → One Euro → dead zone/curve → attack/decay
                               → rest spring / catch glide → y ∈ [0, 1]
               ┌──────────────────────────────┴──────────────────────────────┐
     Router.feed("hand") + drive              MIDI out port ("Hyperspace Hands")
  hand:<i> in the routing table: Learn         per axis: 7-bit CC · 14-bit CC ·
  binds a param (abs, float, no detents);      pitch bend · channel pressure,
  ROUTING page mod/replace; presence lanes     rate-limited; presence notes
```

**Inside Hyperspace nothing goes through MIDI.** A learned hand drives
its param at float precision (`Param.glide`: no 7-bit steps, no fader
detents), and it never shares a channel with the APC40. MIDI encodings
only exist for the DAW port.

## What Ultraleap reports

LeapC (through the `leap` Python bindings) reports, per hand per frame:
- `palm.position` / `palm.velocity` in **mm**. The origin is the camera,
  +y points away from it, and +z points toward the performer in desktop
  mode.
- `palm.normal` and `palm.direction` as **unit vectors**, plus
  `palm.orientation` as a quaternion.
- `grab_strength` / `pinch_strength` in **0–1**.
- `grab_angle` in **radians**.
- `pinch_distance` in **mm**.
- `confidence` in 0–1, and `type` left/right.

| Axis | Derived from | Unit | Default range | Shaped |
|---|---|---|---|---|
| `x` | palm.position.x | mm | left −220…20, right −20…220 | centred |
| `y` (height) | palm.position.y | mm | 100…350 | from the bottom |
| `z` (depth) | palm.position.z | mm | −100…100 | centred |
| `roll` | atan2(n.x, −n.y) | ° | ±90 (thumb up = up, both hands) | centred |
| `pitch` | atan2(d.y, −d.z) | ° | ±60 (fingers up = up) | centred |
| `yaw` | atan2(d.x, −d.z) | ° | ±45 (fingers outward = up, both hands) | centred |

`grab`, `pinch` (0–1), `grab_angle` (°) and `pinch_mm` (mm) are
available through `[hands] dofs`, but the default stays the palm pose.

## The analog chain (per axis, `hand_signal.py`)

1. **Range.** `u = (v − lo) / (hi − lo)`. The ranges come from the box's
   calibration (`<home>/hands.json`); the table above is only the
   fallback. `invert` flips u.
2. **One Euro filter.** Its cutoff is `Steadiness` at rest and rises by
   `Response` × speed, so a still hand doesn't shimmer and a fast one
   doesn't lag.
3. **Dead zone.** On a *centred* axis it's a flat band at neutral, so a
   level hand reads exactly neutral. Otherwise it sits at the bottom, so
   "off" is easy to hit. The remaining throw is stretched so both ends
   are still reachable.
4. **Curve.** The exponent 4^c on the distance from neutral (or from the
   bottom). + gives fine control near neutral, − the reverse.
5. **Attack / decay.** A one-pole slew with separate rise and fall times,
   the envelope you'd put on a CV.
6. **On exit.** `hold` keeps the last value. `return` springs to `Rest`
   over `Return` seconds (within about 2 %), with `Bounce` from a
   critically damped glide up to a ringing spring.
   **Catch:** a returning hand is glided onto over `Catch` seconds
   rather than jumped to.
7. **To MIDI.** `cc` and `pressure` are 0–127. `cc14` (MSB on n, LSB on
   n + 32, n ≤ 31) and `pitch` are 0–16383. Each holds its last value
   with hysteresis, so a still hand sends nothing, and each is limited
   to `MIDI rate` messages a second per axis. The newest value always
   lands once the limit allows.

The HANDS page flags any output that can't be sent as set: a 14-bit
number over 31, two axes on the same CC (including an LSB), or two bend
or pressure axes on one channel.

## Setups, the page and the box

- **A setup** is every per-axis and global setting above. They're
  registry params in the `hands` group, so the library's preset strip
  saves and loads setups, a project carries one, and a setting can itself
  be Learned onto an APC40 knob. They're registered even with the tracker
  off, so setups still edit and save offline.
- **The HANDS page** has five parts:
  - the preset strip, the tracker/port status and the last message out
  - the box from above: palms as dots (left white, right red), size = height
  - twelve live rows: output bar, a red hairline where the hand is, a
    tick at the rest value, and the MIDI out and value
  - the selected axis's editor, with its transfer curve drawn and the
    hand's live point on it, plus **mirror** (copy the feel to the other
    hand) and **solo** (only this axis to the DAW, for a DAW's learn)
  - feel & calibration: a 20 s sweep writes the box's ranges
- **Learn:** right-click → Learn MIDI, then move one axis. The axis that
  moved furthest wins, and the param follows it in floats. A panel edit
  stands until the hand moves again. Unbind is in the same menu, and it
  leaves the axis's routes alone.
- **Rig** settings (tracking mode, which features, the port, presence
  notes) are `[hands]` in config.toml. **Box** ranges are `hands.json`.
  **Performance** settings are a setup. Each lives where it changes.

## Install (the SDK is not on this machine yet)

1. Install **Ultraleap Hand Tracking** for macOS (Gemini ≥ 5.17). This is
   the one step that needs a person: the download, the licence, your
   admin password, any macOS prompts, and the camera plugged in.
2. The bindings are prebuilt only for Python 3.8, so build them for 3.12:
   ```
   git clone https://github.com/ultraleap/leapc-python-bindings
   cd leapc-python-bindings
   uv pip install build cffi
   uv run python -m build leapc-cffi
   uv pip install leapc-cffi/dist/leapc_cffi-0.0.1.tar.gz
   uv pip install -e leapc-python-api
   ```
   (Set `LEAPSDK_INSTALL_LOCATION` if the SDK isn't in
   `/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK`.)
3. Set `[hands] enabled = true`, plus `mode = "screentop"` if the camera
   looks down from the lid.
4. Open the HANDS page and run **calibrate 20 s**, sweeping every axis
   end to end. You can also run `uv run python tools/hands_probe.py
   --calibrate 20` from a terminal.

## Not yet verified (needs the camera and the box)

- [ ] The bindings build against the installed Gemini on Apple Silicon / 3.12.
- [ ] The listener's lost-event names (they only change the status text).
- [ ] Angle signs in the box's actual mounting; check them on the page.
- [ ] The default feel: Steadiness 1 Hz, Response 4, Catch 150 ms, return
      500 ms / bounce 0.15, dead zone 0.04 on centred axes. Tune by hand
      and save the result as the factory setup.
- [ ] How independently yaw and pitch can be held without moving x and y.
- [ ] End-to-end latency, hand to pixels and hand to DAW.
- [ ] Oscillators (an `lfo:` source is already reserved in routing):
      deferred on purpose.
