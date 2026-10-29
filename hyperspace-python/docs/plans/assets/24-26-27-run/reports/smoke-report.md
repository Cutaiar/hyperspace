# Smoke runs, plans 24/26/27 (integration branch)

Branch `smoke-runs-24-26-27` reset to `origin/plan-24-26-27-integration` at
**14103cb** ("Run assets: A4, A4b and A2b decisions and reports …"). No source
file changed (`git status` clean), no PR. Machine: this Mac, 2026-10-14.

Every run: cwd `hyperspace-python/`, `VIRTUAL_ENV` unset, `HYPERSPACE_FRAMES=120`,
`HYPERSPACE_HOME` = a scratch home under `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/<stream>/home` whose
`config.toml` has no `[library]` section (so the library is the scratch home).
`~/Hyperspace` and `~/My Drive/Hyperspace` were never touched. A wrapper
(`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/run.sh`) ran each command with a 180 s cap (none needed it).

Each stream has two kinds of run:

1. **Gate run** — the prompt's exact command,
   `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES`
   (the `-ApplePersistenceIgnoreState YES` argument gets past macOS's
   "reopen windows?" alert, per-process, as B1/A4 did).
2. **Probe run** — the same app through `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/probe.py` (A4's method:
   wraps `Renderer._draw_frame` without changing the source, calls
   `hyperspace.app.main()`), which saves output 1's picture at frames 60
   and 110, prints the SYSTEM page's device lines (`ui.device_lines` over the
   live registry), the wiring and some param values. For stream C it also
   sets `desk.shift` True at frame 30 and False at frame 80; for stream B
   it sends one OSC `/x 0.5` to 127.0.0.1:9000 at frame 20.

Scratch homes were built by `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/setup.py`. `[dream] enabled = false`
in every home (as A4's smoke run did: no torch import, faster). No
APC40 / pad / Leap was opened by any run: no MIDI entry is listed
anywhere, the hands play a synthetic tape (stream A only), the pad is
absent (A, B) or `enabled = false` (C).

## Summary

| Stream | Gate run | Probe run | Stall log | Verdict |
|---|---|---|---|---|
| A (plan 26), world strokes | exit 0 | exit 0, frames saved | empty | PASS |
| A (plan 26), `view.screen_strokes` true | exit 0 | exit 0, frames saved | empty | PASS (no visible weight change at zoom 0.9) |
| B (plan 27) | exit 0 (twice) | exit 0, frames saved | **one 2.2 s stall** on the first (cold) gate run; none on the re-run or the probe | PASS, with the stall noted |
| C (plan 24) | exit 0 | exit 0 (three probe runs), frames saved | empty | PASS (no fake MIDI port: SHIFT via `desk.shift`) |

No run raised; no run hung.

## Stream A — plan 26: the `graph` section, hands in the scene

### Setup

The show `smoke` (named in `last_show`) starts on `hands-lines`; the preset is
`tests/fixtures/presets/hands-lines.json` copied byte-for-byte into the
scratch home's `presets/` (A4's smoke-run layout: presets in
`<home>/presets/`, the startup choice in the show file's `startup`, the
open show in `<home>/last_show`). The hands play the tests' synthetic tape
(`uv run python tools/hands_tape.py synth <home>/synthetic.json`, 60 frames,
both hands) through a `[[devices]]` hands entry with `out = ""` so no
virtual DAW port is created.

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home/config.toml`

```toml
# smoke run, stream A (plan 26): scratch home, no [library] section
[dream]
enabled = false

[[devices]]
role = "leap"
kind = "hands"
tape = "synthetic.json"
out = ""
```

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home/projects/smoke.hyp.json`

```json
{
 "schema": "hyperspace.project/2",
 "name": "smoke",
 "note": "smoke run stream A: starts on the fixture hands-lines (graph section: hands in the scene as lines)",
 "startup": "hands-lines",
 "bank": [
  "hands-lines"
 ],
 "session": {
  "ghost.on": true
 },
 "modules": {}
}
```

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home/last_show`: `smoke`

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home/presets/hands-lines.json`

```json
{
 "schema": "hyperspace.preset/2",
 "name": "hands-lines",
 "note": "plan 26 A4's proof preset (a test fixture, never a factory preset): the hands drawn in the scene as lines, through the acid effect, with the look-back wired to capture them — party-tracer's look with party-acid's acid, the graph in data",
 "graph": {"nodes": [
  {"kind": "hands", "into": "scene", "draw": "lines"},
  {"kind": "history", "holds": "scene+hands"}
 ]},
 "values": {
  "view.speed": 0.6,
  "view.depth4": 2.2,
  "view.bright": 2.0,
  "view.points": true,
  "view.lines": true,
  "view.faces": false,
  "view.rotate": true,
  "view.plane.XY": false,
  "view.plane.XZ": false,
  "view.plane.YZ": false,
  "view.plane.XW": true,
  "view.plane.YW": true,
  "view.plane.ZW": true,
  "view.pattern_mix": 1.0,
  "view.instances": 1,
  "view.inst_motion": 0,
  "camera.zoom": 0.9,
  "camera.yaw": 0.0,
  "camera.pitch": 0.0,
  "camera.pan.x": 0.0,
  "camera.pan.y": 0.0,
  "dream.on": true,
  "fx.on": true,
  "fx.mix": 1.0,
  "lfo.1.depth": 0.0,
  "rot.rate.XY": 1.0,
  "rot.rate.XZ": 1.0,
  "rot.rate.YZ": 1.0,
  "rot.rate.XW": 1.0,
  "rot.rate.YW": 1.0,
  "rot.rate.ZW": 1.0,
  "pattern.mod.0": 1.0,
  "pattern.mod.1": 1.0,
  "pattern.mod.2": 1.0,
  "pattern.mod.3": 1.0,
  "pattern.mod.4": 1.0,
  "pattern.mod.5": 1.0,
  "view.shape": 7,
  "view.pattern": 9,
  "dream.echoes": 24,
  "dream.gap": 0.066667,
  "dream.fade": 0.7644,
  "dream.echo_mix": 0.7,
  "dream.darken": 0.0,
  "dream.occlude": 0.3,
  "dream.contrast": 1.0,
  "dream.mix": 0.0,
  "dream.res": 2,
  "fx.acid.on": true,
  "fx.acid.bend": 0.04,
  "fx.acid.twist": 0.9,
  "fx.acid.reach": 10.0,
  "fx.acid.breathe": 0.35
 },
 "routes": [],
 "macros": {}
}
```

### Gate run

Exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/A-gate.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-14 22:47:17.372 Python[58182:249881348] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to /var/folders/p1/t1d3rscd2y743z97lqfm65f80000gn/T/org.python.python.savedState
exit=0
```
Stall log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home/stall.log`: empty (0 bytes).

### Probe run

Exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/A-probe.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home uv run python /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/probe.py /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A A
probe: frame 1: device lines: ['leap  ·  hands  ·  connected  ·  42 sources  ·  tape']
probe: frame 60: device lines: ['leap  ·  hands  ·  connected  ·  42 sources  ·  tape']
probe: frame 60: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/frame-60.png (1280x820) mean=11.6 lit>32=0.068
probe: frame 60: wiring=Wiring(hands='scene', blend='over', history='scene+hands', draw='lines', extra=())
probe: frame 60: fx chain=['acid'] ghost.on=True ghost.error='' in_scene=True layer=False
probe: frame 60: gpu_ms={'ghost': 0.428, 'scene': 0.366, 'cover': 0.0, 'readout': 0.0, 'history': 0.005, 'fx': 0.035, 'capture': 0.0, 'output.1': 0.0}
probe: frame 60: zoom=0.9 screen_strokes=False
probe: frame 60: camera.zoom=<TypeError: 'float' object is not callable>, view.screen_strokes=<TypeError: 'bool' object is not callable>, ghost.on=<TypeError: 'bool' object is not callable>, fx.acid.on=<TypeError: 'bool' object is not callable>
probe: frame 110: device lines: ['leap  ·  hands  ·  connected  ·  42 sources  ·  tape']
probe: frame 110: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/frame-110.png (1280x820) mean=12.9 lit>32=0.078
probe: frame 110: wiring=Wiring(hands='scene', blend='over', history='scene+hands', draw='lines', extra=())
probe: frame 110: fx chain=['acid'] ghost.on=True ghost.error='' in_scene=True layer=False
probe: frame 110: gpu_ms={'ghost': 0.448, 'scene': 0.354, 'cover': 0.0, 'readout': 0.0, 'history': 0.177, 'fx': 0.031, 'capture': 0.0, 'output.1': 0.0}
probe: frame 110: zoom=0.9 screen_strokes=False
probe: frame 110: camera.zoom=<TypeError: 'float' object is not callable>, view.screen_strokes=<TypeError: 'bool' object is not callable>, ghost.on=<TypeError: 'bool' object is not callable>, fx.acid.on=<TypeError: 'bool' object is not callable>
exit=0
```


SYSTEM device line: `leap · hands · connected · 42 sources · tape`. Wiring
`Wiring(hands='scene', blend='over', history='scene+hands', draw='lines')`,
fx chain `['acid']`, `in_scene=True`, `layer=False`, no ghost error — the
graph section landed as A4 describes. (The probe's param line printed
TypeErrors in this first run only: a probe bug — `Param.value` is a
property — fixed before the later runs; the renderer state lines above it
are correct.)

**Frame:** `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/frame-110.png` (also `frame-60.png`) — both hands drawn as
dense wire hands (left pale blue-white, right pink) inside the acid-bent
shape, its edges heaving, with soft smeared tracer copies of the hands and
edges behind them: the A4 picture.

### Stroke-space switch (`view.screen_strokes`)

A second home `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/home`, identical except the preset's values carry
`"view.screen_strokes": true` (the param is a performance param in the
`view` group, so it lives in the preset). Same config, show and tape.

Preset diff vs the fixture: one added key, `"view.screen_strokes": true` (file `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/home/presets/hands-lines.json`; otherwise the fixture's content, re-serialised with `json.dump(indent=1)`).


Gate run: exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/A2-gate.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-14 22:47:37.118 Python[59451:249886727] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to /var/folders/p1/t1d3rscd2y743z97lqfm65f80000gn/T/org.python.python.savedState
exit=0
```
Stall log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/home/stall.log`: empty (0 bytes).


Probe run: exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/A2-probe.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/home uv run python /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/probe.py /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2 A
probe: frame 1: device lines: ['leap  ·  hands  ·  connected  ·  42 sources  ·  tape']
probe: frame 60: device lines: ['leap  ·  hands  ·  connected  ·  42 sources  ·  tape']
probe: frame 60: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/frame-60.png (1280x820) mean=11.9 lit>32=0.070
probe: frame 60: wiring=Wiring(hands='scene', blend='over', history='scene+hands', draw='lines', extra=())
probe: frame 60: fx chain=['acid'] ghost.on=True ghost.error='' in_scene=True layer=False
probe: frame 60: gpu_ms={'ghost': 0.148, 'scene': 0.189, 'cover': 0.0, 'readout': 0.0, 'history': 0.0, 'fx': 0.064, 'capture': 0.0, 'output.1': 0.0}
probe: frame 60: zoom=0.9 screen_strokes=True
probe: frame 60: camera.zoom=0.9, view.screen_strokes=True, ghost.on=True, fx.acid.on=True
probe: frame 110: device lines: ['leap  ·  hands  ·  connected  ·  42 sources  ·  tape']
probe: frame 110: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/frame-110.png (1280x820) mean=14.3 lit>32=0.088
probe: frame 110: wiring=Wiring(hands='scene', blend='over', history='scene+hands', draw='lines', extra=())
probe: frame 110: fx chain=['acid'] ghost.on=True ghost.error='' in_scene=True layer=False
probe: frame 110: gpu_ms={'ghost': 0.139, 'scene': 0.178, 'cover': 0.0, 'readout': 0.0, 'history': 0.0, 'fx': 0.063, 'capture': 0.0, 'output.1': 0.0}
probe: frame 110: zoom=0.9 screen_strokes=True
probe: frame 110: camera.zoom=0.9, view.screen_strokes=True, ghost.on=True, fx.acid.on=True
exit=0
```


The probe confirms `camera.zoom=0.9`, `view.screen_strokes=True` on the
renderer's state. **Frame:** `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/frame-110.png` — the same scene (wire
hands in the acid shape, tracers).

**Do the strokes visibly change weight at zoom 0.9?** No, not that I can
see. Comparing `A/frame-110.png` (world space) and `A2/frame-110.png`
(screen space), the shape's edges look the same weight; the two frames
differ by animation time far more than by stroke width. That is what the
code predicts: in `render.py` (~line 1967) the only difference is the width
factor `zoom` (0.9) vs 1.0, an ~11 % change, and widths under 1 px are
drawn at 1 px with the shortfall folded into alpha, so most edges differ
only by a small alpha change. The hands are unaffected in either mode by
design (A4's hand lines are 1 px edges drawn by `ghost.Geometry`; the
comment in `render.py` says so). A zoom far from 1 (e.g. 0.4 or 2) would be
needed to judge the switch by eye; that is the owner's hand check.

## Stream B — plan 27: `[[devices]]` with OSC and a cloud, no APC40

### Setup

The two blocks exactly as `docs/plans/27-device-registry.md` gives them (the
phone/OSC block and the recorded-cloud block), no MIDI entry, no pad, no
hands entry. `tests/fixtures/clouds/knot.npz` copied to
`<home>/clouds/knot.npz`. No preset or show was written: the app opened its
default (party) show, which starts on TUMBLE. (No Leap entry was listed, so
the hands' documented `error: no camera` line did not arise; I did not add
one to avoid opening the tracker service.)

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/home/config.toml`

```toml
# smoke run, stream B (plan 27): scratch home, no [library] section, no MIDI entry
[dream]
enabled = false

[[devices]]
role = "phone"            # the scheme: its sources are phone:x, phone:y, phone:hit
kind = "osc"
port = 9000               # UDP; host = "0.0.0.0" (every interface) is the default
axes = ["/x", "/y"]       # the app's fader / XY addresses → phone:x, phone:y (continuous)
hits = ["/hit"]           # the app's button addresses → phone:hit (a trigger with velocity)

[[devices]]
role = "scan"             # published as cloud:scan
kind = "cloud"
file = "clouds/knot.npz"  # relative to the home (the folder config.toml is in)
```

### Gate run

Exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/B-gate.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-14 22:47:52.745 Python[60434:249890602] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to /var/folders/p1/t1d3rscd2y743z97lqfm65f80000gn/T/org.python.python.savedState
exit=0
```


Stall log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/home/stall.log`: **not empty** — one entry (47 lines,
copy at `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/B-gate-stall.log`), header:

```
=== stall 2026-10-14 22:47:55.266 · preset TUMBLE: no frame for 2.2 s; last completed frame at 2026-10-14 22:47:53.038 ===
```

The main thread was inside a lazy `import numpy.random` (numpy's
`__getattr__` from `geometry.py:808 _is_boundary_face` ←
`geometry.faces` ← `face_triangles` ← `render.py:2019 draw_scene` ←
`graph.py` evaluate ← `Renderer._draw_frame`), i.e. the first frame that
drew TUMBLE's faces paid a cold first import of `numpy.random` (this was the
first app launch after the fresh `.venv` was built, cold disk cache). It
did not recur: a second identical gate run (`B-gate2`, exit 0) and the probe
run added nothing to the stall log, and streams A and C (which ran on the
same venv) have empty stall logs. Likely environmental (cold start), but a
real first-frame hitch: `geometry.py` touching `np.random` lazily on the
render thread costs ~2 s once on a cold machine. Not a plan 24/26/27
regression as far as I can tell (TUMBLE's faces path), but worth a look.


Second gate run, exit code **0**:

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/B-gate2.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-14 22:48:17.517 Python[61659:249895508] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to /var/folders/p1/t1d3rscd2y743z97lqfm65f80000gn/T/org.python.python.savedState
exit=0
```

### Probe run

Exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/B-probe.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/home uv run python /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/probe.py /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B B
probe: frame 1: device lines: ['phone  ·  osc  ·  lost  ·  3 sources  ·  UDP 0.0.0.0:9000', 'scan  ·  cloud  ·  connected  ·  1 source  ·  knot.npz  ·  frame 1/16  ·  96 points  ·  12 fps']
probe: frame 20: sent /x 0.5 to 127.0.0.1:9000
probe: frame 60: device lines: ['phone  ·  osc  ·  connected  ·  3 sources  ·  UDP 0.0.0.0:9000  ·  /x 0.5', 'scan  ·  cloud  ·  connected  ·  1 source  ·  knot.npz  ·  frame 9/16  ·  160 points  ·  12 fps']
probe: frame 60: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/frame-60.png (1280x820) mean=19.3 lit>32=0.237
probe: frame 60: wiring=Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=())
probe: frame 60: fx chain=[] ghost.on=False ghost.error='' in_scene=None layer=False
probe: frame 60: gpu_ms={'cloud': 0.0, 'scene': 1.439, 'cover': 0.0, 'hands': 0.0, 'history': 0.024, 'fx': 0.0, 'capture': 0.0, 'output.1': 0.0}
probe: frame 60: zoom=1.3 screen_strokes=False
probe: frame 60: view.shape=10
probe: frame 60: clouds={'cloud:scan': (160, 8)}
probe: frame 110: device lines: ['phone  ·  osc  ·  connected  ·  3 sources  ·  UDP 0.0.0.0:9000  ·  /x 0.5', 'scan  ·  cloud  ·  connected  ·  1 source  ·  knot.npz  ·  frame 14/16  ·  200 points  ·  12 fps']
probe: frame 110: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/frame-110.png (1280x820) mean=19.1 lit>32=0.240
probe: frame 110: wiring=Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=())
probe: frame 110: fx chain=[] ghost.on=False ghost.error='' in_scene=None layer=False
probe: frame 110: gpu_ms={'cloud': 0.0, 'scene': 1.46, 'cover': 0.0, 'hands': 0.0, 'history': 0.022, 'fx': 0.0, 'capture': 0.0, 'output.1': 0.0}
probe: frame 110: zoom=1.3 screen_strokes=False
probe: frame 110: view.shape=10
probe: frame 110: clouds={'cloud:scan': (200, 13)}
exit=0
```


SYSTEM device lines:

- frame 1: `phone · osc · lost · 3 sources · UDP 0.0.0.0:9000` and
  `scan · cloud · connected · 1 source · knot.npz · frame 1/16 · 96 points · 12 fps`
- after one `/x 0.5` (frame 20) — frames 60 and 110:
  `phone · osc · connected · 3 sources · UDP 0.0.0.0:9000 · /x 0.5` and
  `scan · cloud · connected · … · frame 14/16 · 200 points · 12 fps`

So the OSC device bound UDP 9000 and reads `lost` until the first message,
then `connected` — as `osc.py`'s docstring documents ("`lost` before the
first one and after a silence"). Note against the brief's wording ("osc and
cloud as connected/running"): with no phone sending, the osc line reads
`lost` at launch; that is the documented behaviour, not an error. The
cloud device plays the fixture at 12 fps and loops (frame count advancing,
point count growing 96 → 160 → 200). `rig.clouds` held `cloud:scan`. Nothing
raised.

**Frame:** `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/frame-110.png` (also `frame-60.png`) — the TUMBLE
polytope (white edges, faint coloured faces) with the recorded knot drawn
inside it as a dotted orange-and-blue point loop: the cloud reaches the scene.

## Stream C — plan 24: fader rows, SHIFT, the palette fold

### Fake MIDI ports

C2's report (§Concerns 1) says: "The app cannot take the tests' fake MIDI
ports" — the tests inject them by filling `r.inp.queue` on a `MidiIO`
built in-process (`tests/test_midi.py` `push`/`shift`), with no hook in the
windowed app. So this run lists **no MIDI device** (the only entry is the
pad, `enabled = false`), and SHIFT is exercised through the desk's own
state: the `desk.shift` param (`routing.SHIFT_PARAM`, the latch's toggle
that `Bindings.set_layer` sits behind), set True at frame 30 and False at
frame 80 by the probe. That is the same latch the APC40's SHIFT note
toggles, but no MIDI message, LED or fader pickup was involved.

### Setup

The preset is C2's fixture `tests/fixtures/desk-faders/faders.json` (FADERS:
the eight track faders S1–S8 on the preset layer) with the palette fold
switched on and mixed up: `fx.on` true, `fx.mix` 1.0, and C6's fixture
palette `tests/fixtures/palettes/fx/sunset.json`'s values merged in with
`fx.palette.mix` 0.8. The show `smoke` starts on it.

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home/config.toml`

```toml
# smoke run, stream C (plan 24): scratch home, no [library] section, no MIDI device listed
[dream]
enabled = false

[[devices]]
role = "pad"
kind = "gamepad"
enabled = false
```

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home/projects/smoke.hyp.json`

```json
{
 "schema": "hyperspace.project/2",
 "name": "smoke",
 "note": "smoke run stream C: starts on the C2 fixture FADERS with the palette fold mixed in",
 "startup": "FADERS",
 "bank": [
  "FADERS"
 ],
 "session": {},
 "modules": {}
}
```

`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home/last_show`: `smoke`


`/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home/presets/FADERS.json`

```json
{
 "schema": "hyperspace.preset/2",
 "name": "FADERS",
 "note": "plan 24 C2 fixture: a preset whose desk binds the eight track faders S1-S8 on the preset layer (the mechanism only: no factory preset has fader rows in this run). Device knob 1 keeps a row so knobs and faders are seen side by side",
 "values": {
  "view.points_alpha": 0.5,
  "view.lines_alpha": 0.75,
  "view.pattern_mix": 0.25,
  "view.bmp_alpha": 1.0,
  "view.inst_amp": 0.25,
  "dream.mix": 0.5,
  "fx.on": true,
  "fx.mix": 1.0,
  "fx.palette.on": true,
  "fx.palette.mix": 0.8,
  "fx.palette.mode": 1,
  "fx.palette.anchors": 4,
  "fx.palette.a1_hue": 270.0,
  "fx.palette.a1_sat": 0.9,
  "fx.palette.a1_val": 0.1,
  "fx.palette.a2_hue": 320.0,
  "fx.palette.a2_sat": 0.85,
  "fx.palette.a2_val": 0.5,
  "fx.palette.a3_hue": 25.0,
  "fx.palette.a3_sat": 0.9,
  "fx.palette.a3_val": 0.9,
  "fx.palette.a4_hue": 50.0,
  "fx.palette.a4_sat": 0.2,
  "fx.palette.a4_val": 1.0
 },
 "routes": [],
 "desk": [
  {
   "source": "cc:*:16",
   "target": "view.depth4",
   "op": "abs",
   "feedback": "ring"
  },
  {
   "source": "cc:0:7",
   "target": "view.points_alpha",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:1:7",
   "target": "view.lines_alpha",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:2:7",
   "target": "view.pattern_mix",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:3:7",
   "target": "view.bmp_alpha",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:4:7",
   "target": "view.bright",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:5:7",
   "target": "view.speed",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:6:7",
   "target": "view.inst_amp",
   "op": "abs",
   "ring": 0
  },
  {
   "source": "cc:7:7",
   "target": "dream.mix",
   "op": "abs",
   "ring": 0
  }
 ],
 "macros": {},
 "modules": {}
}
```

### Gate run

Exit code **0**.

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/C-gate.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-14 22:48:29.123 Python[62334:249898240] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to /var/folders/p1/t1d3rscd2y743z97lqfm65f80000gn/T/org.python.python.savedState
exit=0
```
Stall log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home/stall.log`: empty (0 bytes).

### Probe runs

Three probe runs (the second and third only fixed the probe's printing of the desk rows; the app was identical). All exit code **0**. First probe run:

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/C-probe.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home uv run python /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/probe.py /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C C
probe: frame 1: device lines: ['pad  ·  gamepad  ·  off  ·  0 sources']
probe: frame 30: desk.shift set True -> layer=global desk.shift=True
probe: frame 60: device lines: ['pad  ·  gamepad  ·  off  ·  0 sources']
probe: frame 60: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-60.png (1280x820) mean=11.7 lit>32=0.009
probe: frame 60: wiring=Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=())
probe: frame 60: fx chain=['palette'] ghost.on=False ghost.error='' in_scene=None layer=False
probe: frame 60: gpu_ms={'scene': 0.295, 'cover': 0.0, 'hands': 0.0, 'history': 0.0, 'fx': 0.066, 'capture': 0.0, 'output.1': 0.0}
probe: frame 60: zoom=1.0 screen_strokes=False
probe: frame 60: desk.shift=True, view.points_alpha=0.5, view.lines_alpha=0.75, view.pattern_mix=0.25, view.bmp_alpha=1.0, view.inst_amp=0.25, dream.mix=0.5, fx.on=True, fx.palette.on=True, fx.palette.mix=0.8
probe: frame 60: table.layer=global layer_serial=1
probe: rows: 'Bindings' object has no attribute 'rows'
probe: frame 80: desk.shift set False -> layer=preset desk.shift=False
probe: frame 110: device lines: ['pad  ·  gamepad  ·  off  ·  0 sources']
probe: frame 110: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-110.png (1280x820) mean=11.7 lit>32=0.009
probe: frame 110: wiring=Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=())
probe: frame 110: fx chain=['palette'] ghost.on=False ghost.error='' in_scene=None layer=False
probe: frame 110: gpu_ms={'scene': 0.313, 'cover': 0.0, 'hands': 0.0, 'history': 0.0, 'fx': 0.063, 'capture': 0.0, 'output.1': 0.0}
probe: frame 110: zoom=1.0 screen_strokes=False
probe: frame 110: desk.shift=False, view.points_alpha=0.5, view.lines_alpha=0.75, view.pattern_mix=0.25, view.bmp_alpha=1.0, view.inst_amp=0.25, dream.mix=0.5, fx.on=True, fx.palette.on=True, fx.palette.mix=0.8
probe: frame 110: table.layer=preset layer_serial=2
probe: rows: 'Bindings' object has no attribute 'rows'
exit=0
```


Third probe run (the desk rows that are not on the global layer):

Log `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/C-probe3.log` (last 30 lines):

```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home uv run python /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/probe.py /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C C
probe: frame 1: device lines: ['pad  ·  gamepad  ·  off  ·  0 sources']
probe: frame 30: desk.shift set True -> layer=global desk.shift=True
probe: frame 60: device lines: ['pad  ·  gamepad  ·  off  ·  0 sources']
probe: frame 60: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-60.png (1280x820) mean=11.7 lit>32=0.009
probe: frame 60: wiring=Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=())
probe: frame 60: fx chain=['palette'] ghost.on=False ghost.error='' in_scene=None layer=False
probe: frame 60: gpu_ms={'scene': 0.294, 'cover': 0.0, 'hands': 0.0, 'history': 0.0, 'fx': 0.059, 'capture': 0.0, 'output.1': 0.0}
probe: frame 60: zoom=1.0 screen_strokes=False
probe: frame 60: desk.shift=True, view.points_alpha=0.5, view.lines_alpha=0.75, view.pattern_mix=0.25, view.bmp_alpha=1.0, view.inst_amp=0.25, dream.mix=0.5, fx.on=True, fx.palette.on=True, fx.palette.mix=0.8
probe: frame 60: table.layer=global layer_serial=1
probe: frame 60: active desk rows: [('cc:0:14', 'master.gain', None), ('cc:0:15', 'output.dim', None), ('cc:*:16', 'view.depth4', 'preset'), ('cc:0:7', 'view.points_alpha', 'preset'), ('cc:1:7', 'view.lines_alpha', 'preset'), ('cc:2:7', 'view.pattern_mix', 'preset'), ('cc:3:7', 'view.bmp_alpha', 'preset'), ('cc:4:7', 'view.bright', 'preset'), ('cc:5:7', 'view.speed', 'preset'), ('cc:6:7', 'view.inst_amp', 'preset'), ('cc:7:7', 'dream.mix', 'preset')]
probe: frame 80: desk.shift set False -> layer=preset desk.shift=False
probe: frame 110: device lines: ['pad  ·  gamepad  ·  off  ·  0 sources']
probe: frame 110: saved /Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-110.png (1280x820) mean=11.7 lit>32=0.009
probe: frame 110: wiring=Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=())
probe: frame 110: fx chain=['palette'] ghost.on=False ghost.error='' in_scene=None layer=False
probe: frame 110: gpu_ms={'scene': 0.346, 'cover': 0.0, 'hands': 0.0, 'history': 0.0, 'fx': 0.057, 'capture': 0.0, 'output.1': 0.0}
probe: frame 110: zoom=1.0 screen_strokes=False
probe: frame 110: desk.shift=False, view.points_alpha=0.5, view.lines_alpha=0.75, view.pattern_mix=0.25, view.bmp_alpha=1.0, view.inst_amp=0.25, dream.mix=0.5, fx.on=True, fx.palette.on=True, fx.palette.mix=0.8
probe: frame 110: table.layer=preset layer_serial=2
probe: frame 110: active desk rows: [('cc:0:14', 'master.gain', None), ('cc:0:15', 'output.dim', None), ('cc:*:16', 'view.depth4', 'preset'), ('cc:0:7', 'view.points_alpha', 'preset'), ('cc:1:7', 'view.lines_alpha', 'preset'), ('cc:2:7', 'view.pattern_mix', 'preset'), ('cc:3:7', 'view.bmp_alpha', 'preset'), ('cc:4:7', 'view.bright', 'preset'), ('cc:5:7', 'view.speed', 'preset'), ('cc:6:7', 'view.inst_amp', 'preset'), ('cc:7:7', 'dream.mix', 'preset')]
exit=0
```


What it shows: FADERS loaded from the scratch library (its values are live:
`view.points_alpha=0.5`, `view.lines_alpha=0.75`, `view.pattern_mix=0.25`,
`view.inst_amp=0.25`, `dream.mix=0.5`); its eight `cc:<n>:7` fader rows and
the `cc:*:16` knob row sit on the **preset** layer in the live table, with
`master.gain` / `output.dim` (`cc:0:14`, `cc:0:15`) unlayered. SHIFT
latched: `table.layer` went `preset → global` (serial 1) and released
`global → preset` (serial 2), `desk.shift` reading True/False to match; the
preset's values were untouched by the latch (no fader moved — there is no
desk to move one). `fx.palette.on=True`, `fx.palette.mix=0.8`, fx chain
`['palette']`. SYSTEM device line: `pad · gamepad · off · 0 sources`.
Nothing raised.

**Frame:** `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-110.png` (also `frame-60.png`) — the tesseract
wireframe recoloured by the sunset gradient map: a deep-violet ground
instead of black and edges in magenta through orange (the palette fold is
visibly on at mix 0.8).

## Contradictions with the docs / concerns

1. **Stream B's first gate run left a 2.2 s stall** in `stall.log`
   (first-frame lazy `numpy.random` import from `geometry.py:808`, TUMBLE's
   faces). Not reproduced on a re-run or in the probe; probably the cold
   first launch on a fresh `.venv`. The gate wants an empty stall log, so
   it is noted rather than waved through.
2. **The OSC line reads `lost` at launch**, not `connected`, until a
   message arrives — as `osc.py` documents; the brief's "osc … connected"
   holds only after traffic (shown with one `/x 0.5`).
3. **Stream C could not use fake MIDI ports**: the windowed app has no
   way to take them (C2's report says the same). SHIFT was latched and
   released through `desk.shift`; the fader rows were checked in the live
   table, not moved by a desk. The real-desk path (SHIFT note, pickup,
   LEDs) stays the owner's hand check.
4. **`view.screen_strokes` at zoom 0.9 makes no visible difference** by
   eye (an ~11 % width factor, mostly sub-pixel). Not a bug; a zoom far
   from 1 is needed to see it.
5. No hands `error: no camera` line was observed: stream B listed no hands
   entry and stream A played a tape (`connected · tape`).

## Files

- Scratch homes: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/home`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/home`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/home`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/home`
- Frames: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/frame-60.png`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A/frame-110.png`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/frame-60.png`,
  `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/A2/frame-110.png`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/frame-60.png`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B/frame-110.png`,
  `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-60.png`, `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/C/frame-110.png`
- Logs: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/*.log`; B's stall entry `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/logs/B-gate-stall.log`
- Tools (not committed): `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/tools/setup.py`, `probe.py`, `run.sh`, `report.py`
