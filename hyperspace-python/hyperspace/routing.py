"""Routing — the one binding table every source drives the registry through.

Keys, the gamepad, a MIDI controller and the analyzer's lanes used to be
three tables and a special case: KEYMAP / PADMAP / HATMAP in app.py,
midi_map.json, and `planedrive` computed inside the chain. They are one
table now — a list of `Binding` rows, each "this source does this op to
this param" — persisted as one JSON file (`bindings.json`). app.py's
`Keys` / gamepad's `Pad` and midi.py's `MidiIO` are the *adapters*: they
poll hardware and look up the rows of their scheme. The analyzer is a
source like any other, read by the `Router` once per frame.

Sources are one string, ``scheme:address``:

  key:<NAME>       a GLFW key by constant name without KEY_ ("R", "F1",
                   "LEFT_BRACKET", "1"); with modifiers in front,
                   "SHIFT+B", "SUPER+Z", "CONTROL+SHIFT+Z" (MODIFIERS:
                   SHIFT, SUPER, CONTROL). A press fires the rows whose
                   modifiers are exactly the held ones that some row on
                   that key names — so "B" and "SHIFT+B" are two controls,
                   "SUPER+Z" and "SHIFT+SUPER+Z" are two more, and a
                   modifier no row on the key names is ignored. R, F1–F8
                   and ⇧F1–F8 are rows since plan 11, undo and redo since
                   plan 15 (LOOP_KEY_ROWS). Still app.py's own, outside the
                   table: Cmd+R, Esc / Q, and the relative writers — ↑/↓,
                   the mouse, and the pad's sticks and triggers while no
                   route names them (they nudge camera params directly)
  pad:<NAME>       a gamepad button by gamepad.py's name ("A", "LB", "LSTICK")
  hat:<DIR>        the d-pad: UP DOWN LEFT RIGHT
  axis:<NAME>      a gamepad axis as a continuous lane in [0, 1]: LX LY RX
                   RY (sticks, resting 0.5, up and right high) and LT RT
                   (triggers, resting 0). A route on one takes it off its
                   default camera job (app.py)
  cc:<ch>:<n>      MIDI control change n on 0-based channel ch, or * for any
  note:<ch>:<n>    MIDI note n
  pitch:<ch>       MIDI pitch bend
  lane:<i>         analyzer lane i — continuous, held every frame it is live
  ext:<i>          an external MIDI lane (WP4c)
  lfo:<i>          LFO i's output in [0, 1], resting at 0.5 (lfo.py)
  hand:<name>      an Ultraleap hand lane by name (hands/core.py `Layout`,
                   decision register row 20): an axis's output in [0, 1]
                   as `[hands] dofs` spells it (``hand:left.x`` …
                   ``hand:right.yaw``), a hand's presence
                   (``hand:left.present``), a pinch switch
                   (``hand:right.pinch.index`` … ``.pinky``; the `when`
                   gates). Resolved through the map the adapter publishes
                   (`Router.names`): a name the rig lacks is dormant.
                   NaN while that hand is out of the box or was never
                   seen, and a NaN reading is not live
  hand:<i>         the hand lane at index i on the rig's layout (axes,
                   then presence, then switches) — still read, so an
                   older saved preset plays; nothing writes it any more
  param:<id>       a param's effective value, as a *sink row*'s source
                   (plan 27 B3): ``{"source": "param:view.bright",
                   "target": "bridge:3", "op": "send"}`` sends it out on a
                   sink port (``<role>:<channel>``); ``lane:<i>`` and
                   ``lane:*`` are a sink row's other sources. The
                   session's rows (bindings.json), never performers
                   (`SINK_OP`, `sink_values`)

Numeric addresses are 0-based (``lfo:0`` is "LFO 1", ``hand:0`` the first
axis); param ids are 1-based (``lfo.1.depth``, ``macro.1``).

Ops — what a row does to its target. The first group is the *scene-
setters*: they write the param's base, the value a performer works from
and returns to. The last two are the *performer* ops:

  fire       fire a trigger
  toggle     flip a toggle, next enum choice, or fire a trigger
  step       move `value` detents (signed)
  set        set `value`: an enum choice, a toggle state, a fader's norm
  abs        an absolute MIDI control's position → set_norm (cc / pitch,
             with soft pickup); a trigger fires on the rising half. MIDI
             only: a continuous source never sets the base
  rel/rel64  a relative encoder's delta → step
  momentary  note-on (a pad button's press) sets a toggle on, note-off
             (its release) sets it off
  push       the performer adds to the base: every frame the source is
             live the row calls ``param.modulate(depth · scale · (u −
             rest))`` — `value` the signed depth in norm units, u the
             source's normalized reading, `rest` where the source sits
             idle so that an idle source pushes nothing — the source's
             own, as its adapter publishes it (`Router.rests`: a lane 0,
             a hand axis its configured rest value, an LFO 0.5) unless
             the row overrides it with a number — and `scale` the live
             value of the param the row's `scale` names (an attenuator
             on the depth; 1 when it names none)
  position   the performer *is* the fader: while live the target sits at
             position ``depth · scale · u`` of its throw (clamped to
             [0, 1]), along its own taper and without detents; the base
             returns when the source stops. Depth 1 is the whole control
             whatever its units or curve — what a learned hand is

Both go through the same modulate(): position's offset is ``clamp(depth ·
scale · u) − base_norm``, so range, wrap and dormancy are push's. Rows to
unknown or unmodulatable params, or with an unknown scale param, are
dormant no-ops.

Either op's reading first travels with the row's *feel* (`motion`,
motion.py): ``follow`` — the analyzer's own asymmetric envelope, attack
away from the source's rest and release back toward it — or ``spring``,
a damped spring (Hz, damping ratio). A row with no feel of its own takes
its source's (`Router.feel_of`): for the pad's `axis` lanes the session's
`desk.pad.*`, which the sticks' default camera job reads too
(`Router.felt`); none for every other source. A row's follower starts
where it moves nothing and is dropped the frame the row stops acting.

One performer per parameter — the model (plan 09)::

                       scene-setters (write the BASE, never prompt)
    panel · keys · pad buttons · APC40 · presets · mouse/stick (relative, on base)
                                   │
                                   ▼
   Param ─── base ──────────────────────────────▶ effective = base + offset
                                   ▲
                                   │  ONE route row, ONE per-frame path: Router.modulate
              performer ───────────┘
    lane:<i> · hand:<name> · ext:<i> · lfo:<i>   op = push | position
                                                  depth · scale (a session param: master.gain)
                                                  rest (push; the source's, or a number) · when (a gate)

   chaining:  hand:right.y ──position──▶ lfo.1.depth   lfo:0 ──push──▶ view.bright
              lane:0 ──push──▶ macro.2   hand:left.y ──position──▶ fx.mix  × macro.2 (depth sub)

A *performer* is an enabled row whose source is a continuous scheme
(`is_continuous`: anything but a key, pad, D-pad or MIDI row — which
continuous schemes this rig has is the device registry's, `Router.schemes`)
and whose op is in MOD_OPS. A target has at most one:
`Bindings.add` / `bind` raise `Owned(existing, new)` when another enabled
performer already has it (`Bindings.owner`), and the caller asks — the
panel's Replace / Keep prompt (ui_routing.py), which a hand learn reaches
through `learn.Learn.pending` — before `replace_owner` swaps them. The prompt
names the owner as its adapter does (`Router.describe`: "R height
positions", from `labels` / `gates`). A preset or file with two rows on
one target keeps the first and lists the rest in `Bindings.dropped` until
the next edit. Disabled rows don't own. Layering is chaining, never
stacking: a hand owns an LFO's depth, the LFO owns brightness. Scene-
setters never prompt and are never blocked — an APC knob turned on a
hand-owned param moves the value the hand returns to.

Gating (`when`): any row may name a second *fed* source address — one an
adapter hands in with `feed` (hand, ext, lfo), which is where switch-like
lanes live; the analyzer's own lanes are not switches at all, so a row
gated on one stays shut. A gate has to read on (≥ 0.5) before the row
acts at all — a pinch switch over a hand axis, so the same movement means
one thing pinched and nothing open. A gated-off row stops modulating and
apply() writes the base back. A gate whose source is not live holds the
row shut, never open: nothing should start moving because a camera was
unplugged. Gates don't exempt a row from the referee: two rows on one
target with different pinches are still two performers.

Lane normalization: ``u = lane / CEIL`` — the analyzer's lanes are in
[0, CEIL) (bands.CEIL, the fader asymptote), so a lane at the asymptote
reads u = 1.0 and nominal (1.0) reads 1 / CEIL. u is not clamped; the
target param clamps to its own range in apply(). `master.gain` stays the
analyzer's output gain param; it reaches a route as a `scale`, which is
how the drive fader keeps its meaning on the rotation routes without
also scaling the pattern inputs the reference fed raw.

Frame order (app.py) is fixed: input adapters (keys, pad, MIDI) →
``hands.poll`` (feeds `hand`) → ``output.apply`` → ``mouse.poll`` →
``audio.step`` (the analyzer) → bridge (feeds `ext`) → ``Router.modulate``
(the modulation patch in dependency order, plan 28 N0: the LFOs step
inside it and feed `lfo`, every live performer row calls modulate, and a
param the pass itself reads lands at once) → ``reg.apply()`` (the rest) →
``integrate`` → ``draw`` → ``panel.draw``. A lane may modulate the
analyzer's own params: the analyzer ran before the pass, so the offset
lands in apply() and the next step() reads it, a frame late. The readers
outside the pass are that and ``output.apply`` (step 5, before it).

Legacy 6 — the parity anchor. The reference drove the planes with
``PLANEDRIVE[plane] = dir · out[i] · DRIVE · gain`` in place of the
constant 1, and its shaders read ``u_bands[i] = out[i]`` (``u_mod[i]``
here). As routes: lane
i → ``rot.rate.<plane>`` *push* with depth ``dir · ROT_DEPTH`` scaled by
``master.gain`` on a base of 0 (u = out / CEIL and ROT_DEPTH is the depth
that puts CEIL · DRIVE · 8 on the plane at the drive fader's 8×, so the
offset is ``dir · out · DRIVE · gain`` in rate units: a gated band stops
its plane at exactly 0.0); and lane i → ``pattern.mod.i`` *push* at
PATTERN_DEPTH on a base of 1 — no longer the reference's ``out`` raw on
0 (plan 22 B3: the inputs mean one thing each now, and at depth 1 a loud
band pinned them all). ``rot.rate`` spans ±ROT_RATE_MAX = ±(CEIL ·
DRIVE · 8) — the largest drive the reference could produce — so nothing
clamps at any gain, and the effective rate is the reference's number to
round-off *while the source is live* (a value passes through the
registry's normalized space and back: within an ulp of the range, the
same float32 the GPU sees; params.py says why the range is that wide).
`preset.legacy6_values` gives the preset ``legacy6`` its bases (zeros
for the rates — a push reproduces "audio replaces the constant" only on
0 — and the pattern inputs' 1, as designed). Where the reference spun at 1× the moment the
source stopped, the planes now stop: the base is 0 and the parity anchor
is the driven value, not the idle one (plan 09, inside the relaxed bar).
The house presets carry the same routes on WP0's bases of 1, so a plane
keeps its un-driven spin and a lane rides on top.

The file (``bindings.json``, schema ``hyperspace.bindings/3``) holds the
**session's controls** (plan 13 §2.2): the keys, the pad, and the
invariant and global-layer MIDI rows — never a performer row, a
preset-layer row, the macros or any values; those are the loaded
preset's (preset.py), and the table holds them in memory only
(`is_session_row`, `to_json`):

  {"schema": "hyperspace.bindings/3", "profile": "apc40",
   "bindings": [{"source": "key:RIGHT", "target": "view.shape",
                 "op": "step", "value": 1},
                {"source": "cc:*:16", "target": "band.sel.trim", "op": "abs",
                 "feedback": "ring", "layer": "global"},
                {"source": "note:0:98", "target": "desk.shift", "op": "toggle"}, …]}

Schema 3 (plan 13 WP3) adds a MIDI row's `layer` — absent: invariant,
the session's control; "global": the SHIFT layer; "preset": the loaded
preset's desk (`Bindings.dispatch` / `active`, `set_desk`, the latch
`desk.shift`) — and the macros' subscribers (`Macro`, `Sub`; the base
ones followed by `Router.follow_macros`, the depth ones multiplied in by
`Router.modulate`). A `scale` is kept only on a session param
(`master.gain`, the drive fader; decision register row 18 (a)); `scale:
"macro.N"` becomes a depth subscriber on load, and one on any other
param is dropped with a note (`migrate_scales`). An older file's
MIDI rows are sorted into the layers once (`sort_layers`).

Rows carry only what differs from the defaults. `Bindings.load` reads
the file, or builds the factory table when there is none — and if an old
``midi_map.json`` (midi.py's version-1 file) is present, its rows replace
the factory MIDI part and the merged table is written once, with a note.
A schema-1 file migrates the same way (`migrate_v1`, the op rename only:
``mod`` → push, ``span`` → position, a lane-scheme ``abs`` → position at
depth 1, ``replace`` dropped; then `referee`, a second owner dropped —
each dropped row named on stderr). Whatever the schema, every load runs
`remap_factory`: the three APC40 buttons plan 09 WP4 gave to the clock,
the crossfader plan 15 WP3 gave to the master dim
and the B / ⇧B keys are brought up to date where the factory rows still
stand, each change noted. A changed file is backed up (`backup`) and
written back once — except a file that still holds a preset's part
(every file before plan 13 WP5: performer rows, preset-layer rows,
`macros`, `values`), which keeps that part in `Bindings.carried` and is
left for the first-launch migration (`preset.migrate_home`) to move into
presets and only then rewrite. A schema this code doesn't know is left
alone and reported, like a file that won't parse. `bindings_path(home)`
says where the file lives; the app always passes the library home, and
the working-directory default is for tests.

The routing presets — this file format with only modulation rows, once a
library document kind of their own — are gone since plan 13 WP5
(decision 10): the factory ones are full presets
(``library/presets/legacy6.json`` …, generated by preset.py) and a
user's ``<home>/bindings/*.json`` were made presets once, the files left
as they were and no longer read. The factory session table is exported
to ``hyperspace/bindings.default.json`` (`write_factory`).
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np

from . import apc40, envelope, lfo, modifiers, motion
from . import patch as patchmod
from .bands import BANDS, CEIL
from .modifiers import Modifier, ModState
from .motion import OFF, Follower, Motion
from .params import (
    DRIVE,
    F_KEYS,
    PERFORMANCE_GROUPS,
    PLANES,
    ROT_RATE_MAX,
    SESSION_GROUPS,
    Kind,
    Param,
    Registry,
    part_of,
)

SCHEMA = "hyperspace.bindings/3"
SCHEMA_V1 = "hyperspace.bindings/1"
SCHEMA_V2 = "hyperspace.bindings/2"
SCHEMA_VERSIONS = (1, 2, 3)        # what a load reads (the library's routing kind too)
FILE = "bindings.json"
LEGACY_MIDI_FILE = Path("midi_map.json")
# the factory session table as a file (`write_factory`): what a fresh
# bindings.json holds — outside library/, since it is no group's preset
FACTORY_FILE = Path(__file__).with_name("bindings.default.json")

# the modulator banks (modbank.py, plan 31 B) the modulation patch knows,
# by scheme: voice n is the node ``<scheme>:<n-1>`` (its kind the scheme),
# and its knob params ``<scheme>.<n>.<knob>`` (the class's KNOBS) and the
# bank-wide ones (SHARED) feed it. Known here by class, so a bare router
# (no bank handed in) still draws an LFO route's source as an LFO. A new
# kind is one entry here, its scheme in patch.KINDS, and its instance
# handed to `Router.use_bank`
BANKS: dict[str, type] = {lfo.LFOs.SCHEME: lfo.LFOs,
                          envelope.Envelopes.SCHEME: envelope.Envelopes}

# the schemes no device feeds — the analyzer, the LFOs, the envelopes and
# the sequencer's trigger lanes (plan 31) — in offer order; devices.py's
# BUILTIN_SCHEMES, restated (routing never imports devices), the two held
# equal by tests/test_plan31_wiring.py
BUILTIN_LANES = ("lane", "lfo", "env", "seq")

MIDI_SCHEMES = ("cc", "note", "pitch")
# the row kinds the table dispatches itself (plan 27 B2): the keys
# (`Router.keys`), the pad's buttons and D-pad (`Router.pad`) and MIDI
# (midi.MidiIO). Every other scheme is a **continuous** source — a lane
# some device feeds (`lane`, `lfo`, `hand`, `axis`, a new device's role) —
# so a preset row naming a device this rig lacks is still a performer,
# dormant until its device feeds (decision 11). Which continuous schemes
# exist, and in what order a page offers them, is the device registry's
# (`Router.schemes`, devices.DeviceRegistry.continuous_schemes): there is
# no fixed list of them here
ROW_SCHEMES = ("key", "pad", "hat", *MIDI_SCHEMES)
# a source's device qualifier (plan 27 B2 for MIDI, B6 for every scheme):
# ``cc@<role>:<ch>:<n>``, ``pitch@<role>:<ch>``, ``pad@<role>:A``,
# ``axis@<role>:LX`` — the row of a device other than the first one listed
# that publishes the scheme. An unqualified source is that first device's
# (MIDI: `Bindings.midi_roles`, the profile-matching rule B2 built; any
# other scheme: `Bindings.primaries`, the first enabled device of its kind
# in list order), so every row written before plan 27 means what it meant.
# The qualifier adds no ``:`` (a role has none). For a continuous scheme
# the qualified head (``axis@p2``) is its own Router key — its own feed,
# labels, rests and names — so two pads never overwrite each other
QUALIFIER = "@"


def base_scheme(scheme: str) -> str:
    """A scheme without its device qualifier: ``cc@launch`` → ``cc``,
    ``axis@p2`` → ``axis`` (plan 27 B6: any scheme takes one); a scheme
    with none is returned as it is."""
    head, at, _ = scheme.partition(QUALIFIER)
    return head if at else scheme


def qualified(scheme: str, role: str) -> str:
    """`scheme` under the device qualifier `role` (``axis`` + ``p2`` →
    ``axis@p2``); "" leaves it bare — the primary device's (plan 27 B6)."""
    return f"{scheme}{QUALIFIER}{role}" if role else scheme


def is_continuous(scheme: str) -> bool:
    """Is `scheme` a continuous source — read by the Router as a lane,
    driven through a performer row — rather than a row kind the table
    dispatches (`ROW_SCHEMES`)? Open-ended: a scheme no device of this rig
    publishes is continuous too, its rows dormant (decision 11)."""
    return base_scheme(scheme) not in ROW_SCHEMES
MOD_OPS = ("push", "position")                 # the performer ops: the Router's rows
# `hold` is a button row's op (plan 15 WP4, fork 13): the target fires
# once the button has been down HOLD_S, and a shorter press does nothing —
# the adapter times it (midi.py a note, `Router.pad` a pad button or the
# D-pad); `act` ignores it, so a key row with it does nothing
HOLD_S = 0.6       # midi.HOLD_S is the note's; tests hold the two equal
# a *sink row* (plan 27 B3): a value going *out* of the app — a param's
# effective norm (``param:<id>``) or an analyzer lane (``lane:<i>``, or
# ``lane:*`` for every lane from the row's channel on) sent to a sink port,
# ``<role>:<channel>`` (a device's `sinks`: the bridge's lane k, a
# `midi-out`'s lane k). Its op is `SINK_OP`; it is the session's (sinks are
# rig, D1 / D9: bindings.json keeps it), never a performer, never asks
# Replace / Keep, and nothing in the modulation pass reads it — the sink
# device does, after `reg.apply()` (`sink_values`)
SINK_OP = "send"
SINK_SCHEMES = ("param", "lane")
OPS = ("fire", "toggle", "step", "set", "abs", "rel", "rel64", "momentary", "hold", *MOD_OPS,
       SINK_OP)
# the APC40's two layers (plan 13 §3): a MIDI row's `layer` is None — the
# control is invariant, the session's, one meaning on both layers — or one
# of these. The table's `layer` says which is up; SHIFT latches it.
LAYERS = ("preset", "global")
SHIFT_SOURCE = f"note:0:{apc40.N_SHIFT}"     # always invariant: it is the latch
SHIFT_PARAM = "desk.shift"
# the desk's SAVE (plan 24 C1): held, a bank pad's tap saves into its slot
# (midi.MidiIO._save_tap); a momentary row on apc40.SAVE, track 8's clip stop
SAVE_PARAM = "desk.save"
# knob smoothing (plan 18 WP2): how long a value from one of the desk's
# absolute knobs or faders takes to arrive (midi.py's glide). One session
# param for the whole desk. SLEW_MAX_S stays under undo.SETTLE_S by more
# than a slow frame, so one knob turn is still one undo step
# (tests/test_undo.py pins the two together). A bare table has it off —
# the adapter is then the one from before the glide, to the bit;
# SLEW_DEFAULT_S is what the app sets on its table before the show's
# session values land (app.main), so a show that saved the number keeps it.
SLEW_PARAM = "desk.slew"
SLEW_MAX_S = 0.25
SLEW_DEFAULT_S = 0.08
MACRO_PREFIX = "macro."

# midi_map.json's `mode` → op
MODE_TO_OP = {"abs": "abs", "rel": "rel", "rel64": "rel64", "trigger": "toggle",
              "momentary": "momentary", "set": "set", "step": "step"}
# schema 1's performer ops → schema 2's (migrate_v1); the value-replacing
# op has no twin but a push on a base of 0, which a file can't ask for, so
# it is dropped — its name is kept only to recognise it and say so
V1_TO_OP = {"mod": "push", "span": "position", "abs": "position"}
V1_REPLACE = "replace"     # schema 1's op, kept only to recognise it; not in OPS
# key modifiers a row may name in front of the key ("SHIFT+B",
# "CONTROL+SHIFT+Z"); each is a pair of GLFW keys the adapter reports as
# one state (app.Keys.shift / super / control)
MODIFIERS = ("SHIFT", "SUPER", "CONTROL")

# plan 09 WP4 gives three APC40 buttons to the clock (apc40.DEFAULT_MAP):
# TAP TEMPO taps it, NUDGE ± nudges it, and METRONOME fires the global
# LFO trigger; the theme cycle TAP TEMPO used to do moves to QUANT; and
# the keyboard gets B / ⇧B. A file written before that — at either
# schema — carries the old factory rows and lacks the new ones, so every
# table load runs `remap_factory`: it swaps exactly the old factory rows
# — (source, target, op, value) → (target, op, value) — adds the new rows
# only where nothing uses the source, notes each change, and the file is
# written back once. A row the user put on one of those sources is never
# touched, and a second load finds nothing to do. Named here rather than
# read from DEFAULT_MAP so the remap says the same thing whatever the map
# of the day (test_routing pins the two together).
#
# plan 15 WP3 (decision 28) gives the crossfader to the master dim: the
# old factory row on the overlay's ground is swapped the same way, and a
# crossfader row the owner changed is left alone.
#
# plan 19 WP2 gives clip rows 4 and 5 to the bank (slots 9–24,
# apc40.BANK_PADS; invariant, D6 extended). A session file since plan 13
# WP5 has no row on those pads, so the sixteen are added (APC_NEW_ROWS) —
# only where nothing uses the pad: a row the owner put there is left alone
# and that pad does what the owner's row says. A file from before plan
# 13's migration still holds the sixteen shape pads, which are swapped by
# name (BANK_REMAP, in APC_REMAP); a row on one of them the owner changed
# matches no key, keeps the pad, and gets no bank row.
_FAR_PADS = tuple((k, f"note:{ch}:{n}") for k, (n, ch) in enumerate(apc40.BANK_PADS)
                  if k >= F_KEYS)         # (slot, source) of clip rows 4 and 5
# the shape those pads set before plan 19: pad k of row 4 shape k, of row 5 shape 8 + k
BANK_REMAP: dict[tuple[str, str, str, float], tuple[str, str, float]] = {
    (source, "view.shape", "set", float(k - F_KEYS)): ("preset.select", "set", float(k))
    for k, source in _FAR_PADS}
APC_REMAP: dict[tuple[str, str, str, float], tuple[str, str, float]] = {
    (f"note:0:{apc40.N_TAP}", "theme.next", "toggle", 1.0): ("tempo.tap", "toggle", 1.0),
    (f"note:0:{apc40.N_NUDGE_P}", "view.shape", "step", 1.0): ("tempo.nudge", "step", 1.0),
    (f"note:0:{apc40.N_NUDGE_M}", "view.shape", "step", -1.0): ("tempo.nudge", "step", -1.0),
    (f"cc:0:{apc40.CC_XFADE}", "overlay.bg", "abs", 1.0): ("output.dim", "abs", 1.0),
    **BANK_REMAP,
}
# Plan 24 C1 made the render toggles on scene launch 1–4 invariant
# (apc40.TOGGLES): every preset saved before holds their four factory rows
# in its desk, and every factory file still does (decision 23: no library
# file is rewritten; `preset.file_desk`). The session's invariant rows do
# the same job, so those exact rows drop quietly (in RETIRED_DESK_ROWS).
TOGGLE_DESK_ROWS: frozenset[tuple[str, str, str, float]] = frozenset(
    (f"note:0:{n}", pid, "toggle", 1.0) for pid, n in zip(apc40.TOGGLES, apc40.N_SCENE))
# Plan 24 C2 (decision 17, amending D6) frees the track faders S1–S8 for
# the presets: the audio strip that was invariant on them (the bands'
# post-drive on 1–6, master.dyn and master.trim on 7–8) moves to the SHIFT
# layer. A session file from before holds those eight rows with no layer;
# `remap_factory` gives each exact row the global layer, with a note (the
# file is backed up and written back once). A fader row the owner changed
# matches no key and stays invariant: that fader is the owner's on both
# layers, and a preset's row on it drops with D6's note.
FADER_SHIFT_ROWS: frozenset[tuple[str, str, str, float]] = frozenset(
    (f"cc:{ch}:{apc40.CC_FADER}", pid, "abs", 1.0)
    for ch, pid in zip(apc40.TRACK_FADERS, apc40.SHIFT_FADERS))
# which plan moved or added each source, for the note `remap_factory`
# writes; a source not named here is plan 09's
APC_REMAP_PLAN = {f"cc:0:{apc40.CC_XFADE}": "plan 15",
                  f"note:0:{apc40.N_OVERDUB}": "plan 15",
                  **{f"note:{k}:{apc40.N_CLIPSTOP}": "plan 15" for k in range(8)},
                  **{source: "plan 19" for _k, source in _FAR_PADS},
                  **{source: "plan 24" for source, *_ in TOGGLE_DESK_ROWS},
                  **{source: "plan 24" for source, *_ in FADER_SHIFT_ROWS},
                  f"note:{apc40.SAVE[1]}:{apc40.SAVE[0]}": "plan 24"}
# Factory preset-layer rows a later plan took for the session, as (source,
# target, op, value): plan 19's sixteen shape pads. Every preset saved
# before it holds them in its `desk`; `Bindings.set_desk` drops such a row
# without a note (plan 19 fork 4 — a note means something the owner mapped
# was dropped), while any other row on those pads keeps the note. Emptying
# this set brings the note back for all of them.
#
# …and the four render toggles plan 24 C1 made invariant (TOGGLE_DESK_ROWS).
RETIRED_DESK_ROWS: frozenset[tuple[str, str, str, float]] = \
    frozenset(BANK_REMAP) | TOGGLE_DESK_ROWS
# rows added when nothing uses the note: (source, target, op, value, only
# when the theme cycle was remapped away)
APC_NEW_ROWS = (
    (f"note:0:{apc40.N_METRO}", "lfo.trigger", "toggle", 1.0, False),
    (f"note:0:{apc40.N_QUANT}", "preset.next", "toggle", 1.0, True),
    (f"note:0:{apc40.N_OVERDUB}", "preset.home", "toggle", 1.0, False),   # plan 15 WP2
    # plan 19 WP2: clip rows 4 and 5 load the bank's slots 9–24
    *[(source, "preset.select", "set", float(k), False) for k, source in _FAR_PADS],
    # plan 24 C1: the render toggles, invariant now (a session file never
    # held them: they were the preset layer's), and SAVE on track 8's clip stop
    *[(source, pid, op, value, False) for source, pid, op, value in sorted(TOGGLE_DESK_ROWS)],
    (f"note:{apc40.SAVE[1]}:{apc40.SAVE[0]}", SAVE_PARAM, "momentary", 1.0, False),
)
# plan 15 WP4's clip-stop SAVE AS bar, retired 2026-10-09: an empty bank
# pad held saves into its own slot (`Param.held` on `preset.select`), and
# the row is free.
# `remap_factory` drops these exact rows from a table, with a note; a row
# the owner put on a clip-stop button is kept
RETIRED_ROWS: frozenset[tuple[str, str, str, float]] = frozenset(
    (f"note:{k}:{apc40.N_CLIPSTOP}", "preset.save_new", "hold", 1.0) for k in range(8))
# the keys WP4 added, likewise only where the key is free
# the keys plan 11 moved out of app.py's loop into the table (audit R2;
# decision register row 7): R resets the camera, F1–F8 load the preset
# bank's slots 1–8 (param ids are 0-based), ⇧F1–F8 save the live state
# as them. Cmd+R (restart), Esc / Q and ↑ / ↓ stay in the loop.
# Plan 15 WP1 adds undo and redo, on both ⌘ and Ctrl (fork 1): ⌘Z / Ctrl+Z
# fire `edit.undo`, ⌘⇧Z / Ctrl+⇧Z fire `edit.redo` — a chord fires only
# its own row (`Router.keys`).
# Plan 15 WP2 adds Home (fn ← on a laptop; fork 7): it fires `preset.home`,
# which loads the preset the show starts on.
# F_KEYS (params): the F-key rows are the bank's first eight slots
LOOP_KEY_ROWS = (
    ("R", "camera.reset", "fire"),
    *[(f"F{k + 1}", f"preset.load.{k}", "fire") for k in range(F_KEYS)],
    *[(f"SHIFT+F{k + 1}", f"preset.save.{k}", "fire") for k in range(F_KEYS)],
    ("SUPER+Z", "edit.undo", "fire"), ("SHIFT+SUPER+Z", "edit.redo", "fire"),
    ("CONTROL+Z", "edit.undo", "fire"), ("CONTROL+SHIFT+Z", "edit.redo", "fire"),
    ("HOME", "preset.home", "fire"),
)
# plan 13 WP2: the theme bank became the preset bank. A row a file wrote
# before it that targets a theme param — a factory key or APC40 row, or
# one the user learned — is rewritten to the preset param of the same
# slot (`remap_factory`, noted, the file written back once)
THEME_TO_PRESET = {
    "theme.select": "preset.select", "theme.next": "preset.next",
    "theme.prev": "preset.prev",
    **{f"theme.{w}.{k}": f"preset.{w}.{k}" for w in ("load", "save") for k in range(F_KEYS)},
}
# the pad's factory rows as they were before 2026-10-14 → the owner's
# layout (`padmap`): A faces, X previous preset, Y lines, START held saves
# a new preset; and B / X off the bank onto the preset list (2026-10-14,
# `preset.list.*`). Exact rows only — a row the owner learned onto a
# button is kept (`remap_factory`). One pass applies one key, so every
# older form maps straight to the newest: X's points and bank rows, B's
# bank row and its theme row from before plan 13 (ahead of THEME_TO_PRESET).
# Later the same day: the right-stick click resets the 4D spin
# (`rot.reset_w`) and BACK is let go — it hid the panel, and the desk
# diagram filled the window: None drops the row. START keeps its
# hold-to-save. That row was dropped here too for one night: a file
# written before `padmap` gained it never gained it either (no pad row
# was ever added to an existing file), which read as a pad whose buttons
# the map could not find. PAD_NEW_ROWS adds it instead.
PAD_REMAP: dict[tuple[str, str, str, float], tuple[str, str, float] | None] = {
    ("pad:RSTICK", "camera.reset", "fire", 1.0): ("rot.reset_w", "fire", 1.0),
    ("pad:VIEW", "ui.panel", "toggle", 1.0): None,
    ("pad:A", "view.rotate", "toggle", 1.0): ("view.faces", "toggle", 1.0),
    ("pad:X", "view.points", "toggle", 1.0): ("preset.list.prev", "fire", 1.0),
    ("pad:X", "preset.prev", "fire", 1.0): ("preset.list.prev", "fire", 1.0),
    ("pad:B", "preset.next", "fire", 1.0): ("preset.list.next", "fire", 1.0),
    ("pad:B", "theme.next", "fire", 1.0): ("preset.list.next", "fire", 1.0),
    ("pad:Y", "view.faces", "toggle", 1.0): ("view.lines", "toggle", 1.0),
    ("pad:MENU", "ui.cheatsheet", "toggle", 1.0): None,
}
# Pad rows added where nothing uses the button, as (source, target, op,
# value) — the pad's APC_NEW_ROWS. Until 2026-10-14 a row `padmap` gained
# reached a fresh table only (`Bindings.factory`), so every pad already
# carrying a bindings.json stayed on the layout of the day it was written:
# START's hold-to-save was added, never arrived, and was taken back out as
# a mapping fault. A row the owner put on the button is left alone, and a
# second load finds the source taken.
PAD_NEW_ROWS = (
    ("pad:MENU", "preset.save_new", "hold", 1.0),
)
KEY_NEW_ROWS = (
    ("key:B", "tempo.tap", "fire", 1.0),
    ("key:SHIFT+B", "lfo.trigger", "fire", 1.0),
    *[(f"key:{k}", pid, op, 1.0) for k, pid, op in LOOP_KEY_ROWS],
)

# the legacy rate route: a push on a base of 0 lands the reference's
# drive — a lane at full drive (out = CEIL, gain 8) reaches rot.rate's end
# stop when depth · (CEIL · 8 / CEIL) · 2 · ROT_RATE_MAX = CEIL · DRIVE · 8
# →  depth = DRIVE · CEIL / (2 · ROT_RATE_MAX) = 1/16
ROT_DEPTH = DRIVE * CEIL / (2 * ROT_RATE_MAX)
# the factory's depth on lane i → pattern.mod.i (plan 22 B3). A push moves
# the input by depth · u of its 0–2.6 range, and u = out / CEIL with CEIL
# also 2.6, so on the input's own scale the offset is depth · out: a band at
# nominal (out 1) lifts its input by 0.35, a hard transient near the
# asymptote (out ≈ 2.5) by ≈ 0.87 — to ≈ 1.9 on the base of 1, short of the
# 2.6 end with room for a macro to double it. At depth 1 (the reference's
# u_bands = out) a nominal band already put an input at 2.0 and anything
# loud pinned every input at 2.6 on every pattern. The FACES page's
# "+ SUB" offer routes at this depth too (ui_patterns)
PATTERN_DEPTH = 0.35


class Owned(Exception):
    """The target already has a performer — `existing` is that row, `new`
    the one that asked. The caller decides: `Bindings.replace_owner(new)`
    or leave the table alone."""

    def __init__(self, existing: Binding, new: Binding | None = None):
        self.existing, self.new = existing, new
        super().__init__(f"{existing.target} is already performed by {existing.describe()}")


# ---------------------------------------------------------------- binding

@dataclass
class Binding:
    source: str                  # "scheme:address", see the module docstring
    target: str                  # param id
    op: str = "fire"
    value: float = 1.0           # set: the value · step: the detents · push/position: the depth
    enabled: bool = True
    scale: str | None = None     # push/position: a param whose value multiplies the depth
    # a source address ("hand:left.pinch.index") that must read on for this row to apply:
    # a pinch switch gating an axis, so the same hand move means two things
    when: str | None = None
    # push: where the source sits idle — the reading that pushes nothing.
    # None is the source's own rest, resolved every frame from what its
    # adapter publishes (Router.rests / rest_of); a number overrides it
    rest: float | None = None
    # push / position: the feel the reading travels with before it acts
    # (motion.py) — follow (attack / release about rest) or spring. None is
    # the source's own feel (`Router.feel_of`: the pad's for `axis` lanes,
    # none elsewhere); Motion("off") turns that off for this row
    motion: Motion | None = None
    # MIDI controls only (midi.py); other sources ignore them
    pickup: bool = True
    feedback: str | None = None  # "ring" | "led" | None
    on: int = 1                  # led velocity when lit
    off: int = 0                 # led velocity when dark
    ring: int = 2                # ring style for "ring" feedback (profile-defined)
    # the desk layer (plan 13 §3.1): None = invariant, the session's control
    # with one meaning on both layers; "global" = SHIFT up; "preset" = the
    # loaded preset's own. MIDI rows only
    layer: str | None = None
    # runtime, never persisted
    caught: bool = field(default=False, repr=False, compare=False)
    last_hw: float | None = field(default=None, repr=False, compare=False)
    last_out: int | None = field(default=None, repr=False, compare=False)
    lit: bool = field(default=False, repr=False, compare=False)

    _RUNTIME = ("caught", "last_hw", "last_out", "lit")

    def __post_init__(self):
        if self.motion is not None and not isinstance(self.motion, Motion):
            self.motion = Motion.from_json(self.motion)   # a file's dict

    # ---- the source, taken apart ----

    @property
    def scheme(self) -> str:
        """The source's scheme without its device qualifier (``cc@launch:0:7``
        → ``cc``, ``axis@p2:LX`` → ``axis``; `device` holds the role)."""
        return base_scheme(self.head)

    @property
    def head(self) -> str:
        """The source before its first ``:``, qualifier and all
        (``axis@p2``): the Router key a continuous row reads its lane
        under (plan 27 B6)."""
        return self.source.split(":", 1)[0]

    @property
    def device(self) -> str:
        """The row's device qualifier — the role after ``@`` — or "" for
        an unqualified row, the scheme's primary device's
        (`Bindings.role_of`). Any scheme takes one (plan 27 B6)."""
        _, at, role = self.head.partition(QUALIFIER)
        return role if at else ""

    @property
    def parts(self) -> list[str]:
        return self.source.split(":")[1:]

    @property
    def bare(self) -> str:
        """The source without its device qualifier (``cc@launch:0:7`` →
        ``cc:0:7``): the control as a device's own profile names it."""
        if not self.device:
            return self.source
        _, _, rest = self.source.partition(":")
        return f"{self.scheme}:{rest}"

    @property
    def key(self) -> str:
        """What identifies the control: the source string."""
        return self.source

    @property
    def is_midi(self) -> bool:
        return self.scheme in MIDI_SCHEMES

    @property
    def kind(self) -> str | None:
        """MIDI: "cc" | "note" | "pitch"; None for any other source."""
        return self.scheme if self.is_midi else None

    @property
    def channel(self) -> int | None:
        """MIDI channel, 0-based; None matches any."""
        if not self.is_midi:
            return None
        ch = self.parts[0] if self.parts else "*"
        return None if ch == "*" else int(ch)

    @property
    def number(self) -> int:
        """MIDI cc number or note; 0 for pitch and for other sources."""
        if not self.is_midi or self.scheme == "pitch" or len(self.parts) < 2:
            return 0
        return int(self.parts[1])

    @property
    def key_name(self) -> str:
        """A key source's GLFW name without its modifiers ("SHIFT+B" → "B")."""
        return self.parts[0].rsplit("+", 1)[-1] if self.parts else ""

    @property
    def modifiers(self) -> frozenset[str]:
        """The modifiers a key row needs held ({"SHIFT"}); empty for the bare key."""
        if self.scheme != "key" or not self.parts:
            return frozenset()
        return frozenset(self.parts[0].upper().split("+")[:-1])

    @property
    def index(self) -> int:
        """A lane-like source's index (lane:3 → 3); −1 when not numeric."""
        try:
            return int(self.parts[0])
        except (IndexError, ValueError):
            return -1

    @property
    def is_sink(self) -> bool:
        """A sink row (plan 27 B3): a param or a lane sent out to a sink
        port — `target` is ``<role>:<channel>``, not a param id."""
        return self.op == SINK_OP

    @property
    def sink(self) -> tuple[str, int]:
        """A sink row's port as (role, channel); ("", -1) when the target
        names none."""
        got = parse_sink(self.target) if self.is_sink else None
        return got if got is not None else ("", -1)

    @property
    def is_performer(self) -> bool:
        """An enabled push / position row from a continuous source — what
        owns a target. A disabled row keeps its settings and owns nothing."""
        return self.enabled and is_continuous(self.scheme) and self.op in MOD_OPS

    @staticmethod
    def midi_source(kind: str, channel: int | None, number: int = 0, role: str = "") -> str:
        """A MIDI row's source; `role` qualifies it for a MIDI device other
        than the first listed (``cc@launch:0:7``, plan 27 B2)."""
        ch = "*" if channel is None else str(int(channel))
        head = f"{kind}{QUALIFIER}{role}" if role else kind
        return f"{head}:{ch}" if kind == "pitch" else f"{head}:{ch}:{int(number)}"

    def matches(self, kind: str, channel: int, number: int) -> bool:
        if self.kind != kind:
            return False
        if self.channel is not None and self.channel != channel:
            return False
        return kind == "pitch" or self.number == number

    def overlaps(self, other: Binding) -> bool:
        """Two MIDI rows on one physical control: the same device (the same
        qualifier, plan 27 B2), the same kind and number on the same
        channel, or either one on any channel."""
        if not (self.is_midi and other.kind == self.kind and other.device == self.device):
            return False
        if None not in (self.channel, other.channel) and self.channel != other.channel:
            return False
        return self.kind == "pitch" or self.number == other.number

    @property
    def control(self) -> tuple[str, int, int] | None:
        """The physical control a MIDI row names, for feedback: (kind,
        channel, number), an any-channel row drawn on channel 0."""
        return (self.kind, self.channel or 0, self.number) if self.is_midi else None

    # ---- files ----

    def to_json(self) -> dict:
        d = asdict(self)
        for k in self._RUNTIME:
            d.pop(k)
        # only what differs from the defaults keeps the file readable
        for k in ("value", "enabled", "scale", "when", "rest", "motion", "pickup",
                  "feedback", "on", "off", "ring", "layer"):
            if d[k] == self.__dataclass_fields__[k].default:
                d.pop(k)
        if self.motion is not None:
            d["motion"] = self.motion.to_json()
        # a performer never picks up (plan 09 d.4: hands grab, they never
        # yield) — the field rides on the dataclass but never on the file
        if is_continuous(self.scheme):
            d.pop("pickup", None)
        return d

    @classmethod
    def from_json(cls, d: dict) -> Binding:
        if "source" not in d and "kind" in d:        # midi_map.json version 1
            return cls.from_midi_v1(d)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_midi_v1(cls, d: dict) -> Binding:
        """A midi.py version-1 row: {param, kind, number, channel, mode, …}."""
        src = cls.midi_source(d["kind"], d.get("channel"), d.get("number", 0))
        b = cls(src, d["param"], MODE_TO_OP.get(d.get("mode", "abs"), "abs"))
        for f in ("value", "pickup", "feedback", "on", "off", "ring"):
            if f in d:
                setattr(b, f, d[f])
        return b

    def describe(self, name: str | None = None, gate: str | None = None) -> str:
        """One line for the row: "MIDI CC 48 ch1", "lane 2 pushes +0.5 ×
        master.gain", "hand 7 positions while hand:18". `name` stands in
        for a lane-scheme source's "scheme index" and `gate` for the
        `when` address when the caller knows the adapter's labels —
        `Router.describe` does; here the row knows only its strings."""
        s = self.scheme
        if self.is_sink:
            addr = ":".join(self.parts)
            if self.source == "lane:*":
                what = "every lane"
            else:                        # "lane 3 HIGH", as the ext / LFO rows read
                what = f"{s} {addr}" + (f" {name}" if name else "")
            return f"{what} → {self.target}"
        if self.is_midi:
            ch = "any ch" if self.channel is None else f"ch{self.channel + 1}"
            on = f" on {self.device}" if self.device else ""
            if s == "pitch":
                return f"MIDI pitch bend {ch}{on}"
            what = "CC" if s == "cc" else "note"
            extra = "" if self.op in ("abs", "toggle") else f" {self.op}"
            return f"MIDI {what} {self.number} {ch}{on}{extra}"
        addr = ":".join(self.parts)
        on = f" on {self.device}" if self.device else ""     # a second pad's (plan 27 B6)
        if s == "hat":
            return f"d-pad {addr}{on}"
        lane = is_continuous(s)
        who = (name if name and lane else f"{s} {addr}") + on
        if lane and self.op in MOD_OPS:
            by = f" × {self.scale}" if self.scale else ""
            when = f" while {gate or self.when}" if self.when else ""
            if self.op == "push":
                return f"{who} pushes {self.value:+.3g}{by}{when}"
            depth = "" if self.value == 1.0 else f" {self.value:.3g}"
            return f"{who} positions{depth}{by}{when}"
        return who


_SHIFT = Binding(SHIFT_SOURCE, SHIFT_PARAM, "toggle")    # the latch's control


def _macro_n(mid: str) -> int:
    tail = mid[len(MACRO_PREFIX):]
    return int(tail) if tail.isdigit() else 0


# ------------------------------------------------------------------- ops

def act(reg: Registry, b: Binding) -> None:
    """A discrete row fires: keys, pad buttons and MIDI buttons share this.
    A `hold` row does nothing here: only midi.py times a press."""
    p = reg.get(b.target)
    if p is None or not b.enabled:
        return
    op = b.op
    if op == "step":
        p.step(int(b.value))
    elif op == "toggle":
        p.cycle(1) if p.kind is Kind.ENUM else p.toggle()
    elif op == "fire":
        p.fire()
    elif op == "set":
        land(p, b.value)


def land(p: Param, value: float) -> None:
    """`set` by kind: a fader's norm, a toggle's state, an enum's choice."""
    if p.kind is Kind.CONTINUOUS:
        p.set_norm(float(value))
    elif p.kind is Kind.TOGGLE:
        p.set(bool(value))
    elif p.kind is Kind.ENUM:
        p.set(int(value))
    else:
        p.fire()


# --------------------------------------------------------------- the table

# ---- sink rows (plan 27 B3) ----

def sink_target(role: str, channel: int) -> str:
    """A sink port's address, what a sink row's `target` holds:
    ``bridge:3``."""
    return f"{role}:{int(channel)}"


def parse_sink(target: str) -> tuple[str, int] | None:
    """``<role>:<channel>`` → (role, channel), or None when `target` is not
    one (a role is a name without ``:``, the channel a whole number ≥ 0)."""
    role, colon, ch = str(target).partition(":")
    if not colon or not role or ":" in ch or not ch.isdigit():
        return None
    return role, int(ch)


def sink_refusal(b: Binding) -> str | None:
    """Why a sink row cannot stand, or None: its source must be a param
    (``param:<id>``) or a lane (``lane:<i>``, ``lane:*``), its target a
    sink port (``<role>:<channel>``)."""
    scheme, _, addr = b.source.partition(":")
    if scheme not in SINK_SCHEMES or not addr:
        return (f"a sink row sends a param or a lane (param:<id>, lane:<i>), "
                f"not {b.source!r}")
    if scheme == "lane" and addr != "*" and not addr.isdigit():
        return f"{b.source!r} is not a lane (lane:<i> or lane:*)"
    if parse_sink(b.target) is None:
        return f"{b.target!r} is not a sink port (<role>:<channel>)"
    return None


def sink_rows_from_send(role: str, send: Iterable, lanes: int | None = None
                        ) -> tuple[list[Binding], list[str]]:
    """The bridge's old ``[bridge] send`` list as sink rows on `role`
    (plan 27 B3), translated once: (rows, what could not be). Slot k of the
    list — "lane:*", "lane:3", "param:view.bright" in lane order, the stars
    expanded — becomes the row on ``<role>:<k>``. A star is one row,
    ``lane:*`` on its first channel, and takes `lanes` channels (the
    default band layout's count when None) before the next entry, as the
    old list did on a rig with that many bands (`sink_values`: a row on a
    channel a star also fills wins it)."""
    n = len(BANDS) if lanes is None else int(lanes)
    rows: list[Binding] = []
    bad: list[str] = []
    k = 0
    for spec in send if isinstance(send, list | tuple) else [send]:
        spec = str(spec)
        b = Binding(spec, sink_target(role, k), SINK_OP)
        why = sink_refusal(b)
        if why is not None:
            bad.append(f"{spec!r}: {why}")
            continue
        rows.append(b)
        k += n if spec == "lane:*" else 1
    return rows, bad


def sink_values(rows: Iterable[Binding], reg: Registry, analyzer=None,
                lanes: int = 0) -> dict[int, float]:
    """This frame's readings for one sink, channel → u in [0, 1] (the
    device clamps and quantises): what its enabled rows send, read after
    `reg.apply()`. ``param:<id>`` is the param's **effective** norm
    (`eff_norm`: base + this frame's modulation; 0 for a trigger or an id
    the registry lacks, as the bridge always sent); ``lane:<i>`` the
    analyzer's lane as a route reads it, ``lane / CEIL`` (0 with no
    analyzer running); ``lane:*`` every lane from its channel on — the
    analyzer's count, or `lanes` (the count last seen) while none runs, so
    the lanes fall to 0 once. A row on a channel a star also fills wins
    it."""
    out: dict[int, float] = {}
    rows = [b for b in rows if b.enabled and b.is_sink]
    if not rows:
        return out
    n_live = analyzer.n if analyzer is not None else int(lanes)

    def lane(i: int) -> float:
        if analyzer is None or not 0 <= i < analyzer.n:
            return 0.0
        return float(analyzer.lanes[i]) / CEIL

    for b in rows:                       # the stars first: an explicit row wins its channel
        if b.source == "lane:*":
            k = b.sink[1]
            for i in range(n_live):
                out[k + i] = lane(i)
    for b in rows:
        if b.source == "lane:*":
            continue
        k = b.sink[1]
        if k < 0:
            continue
        scheme, _, addr = b.source.partition(":")
        if scheme == "lane":
            out[k] = lane(int(addr)) if addr.isdigit() else 0.0
        elif scheme == "param":
            p = reg.get(addr)
            out[k] = 0.0 if p is None or p.kind is Kind.TRIGGER else float(p.eff_norm)
    return out


def bindings_path(home: Path | str | None = None) -> Path:
    """Where the table lives: <home>/bindings.json, home = the working
    directory unless told otherwise (WP2's library home goes here)."""
    return Path(home if home is not None else ".") / FILE


def keymap() -> list[Binding]:
    """The keyboard table app.py used to hold (ui.CHEATSHEET is the human list)."""
    rows = [
        ("RIGHT", "view.shape", "step", 1), ("LEFT", "view.shape", "step", -1),
        ("SPACE", "view.rotate", "toggle"), ("P", "view.points", "toggle"),
        ("L", "view.lines", "toggle"), ("F", "view.faces", "toggle"),
        ("H", "ui.panel", "toggle"), ("SLASH", "ui.cheatsheet", "toggle"),
        ("LEFT_BRACKET", "view.bright", "step", -3), ("RIGHT_BRACKET", "view.bright", "step", 3),
        ("COMMA", "view.speed", "step", -4), ("PERIOD", "view.speed", "step", 4),
        ("M", "audio.mic", "toggle"), ("K", "audio.play", "toggle"),
        ("0", "audio.restart", "fire"),
        ("T", "overlay.on", "toggle"), ("G", "overlay.passthrough", "toggle"),
        ("B", "tempo.tap", "fire"), ("SHIFT+B", "lfo.trigger", "fire"),
        *[(str(p + 1), f"view.plane.{n}", "toggle") for p, n in enumerate(PLANES)],
        *LOOP_KEY_ROWS,
    ]
    return [Binding(f"key:{k}", pid, op, *arg) for k, pid, op, *arg in rows]


def padmap() -> list[Binding]:
    """Xbox-layout gamepad buttons and the d-pad. B / X step the preset
    list — the PRESETS page's drop-down, by name, a new save included
    (`Project.walk`), not the bank the desk walks — A / Y the faces and
    lines; the left-stick click resets the camera, the right-stick click
    the 4D spin; START (``pad:MENU``) held HOLD_S saves the live state as
    a new preset, and BACK (``pad:VIEW``) is free — Learn pad puts
    anything on it (2026-10-14, the owner's layout — PAD_REMAP moves an
    older file's, PAD_NEW_ROWS adds what it never held)."""
    rows = [
        ("pad:A", "view.faces", "toggle"), ("pad:B", "preset.list.next", "fire"),
        ("pad:X", "preset.list.prev", "fire"), ("pad:Y", "view.lines", "toggle"),
        ("pad:MENU", "preset.save_new", "hold"),
        ("pad:LB", "view.shape", "step", -1), ("pad:RB", "view.shape", "step", 1),
        ("pad:LSTICK", "camera.reset", "fire"), ("pad:RSTICK", "rot.reset_w", "fire"),
        ("hat:UP", "view.bright", "step", 3), ("hat:DOWN", "view.bright", "step", -3),
        ("hat:LEFT", "view.speed", "step", -4), ("hat:RIGHT", "view.speed", "step", 4),
    ]
    return [Binding(src, pid, op, *arg) for src, pid, op, *arg in rows]


def legacy6_routes() -> list[Binding]:
    """The reference's band → plane table and shader inputs, as routes.

    The rate rows push dir · ROT_DEPTH · gain · u with u = out / CEIL, which
    on a base of 0 is dir · out · DRIVE · gain on the plane in rate units.
    The pattern rows push PATTERN_DEPTH · u on their base of 1: the input
    rises by PATTERN_DEPTH · out (plan 22 B3 — the reference fed out raw).
    """
    rows = [Binding(f"lane:{i}", f"rot.rate.{b.pl}", "push", b.dir * ROT_DEPTH,
                    scale="master.gain") for i, b in enumerate(BANDS)]
    rows += [Binding(f"lane:{i}", f"pattern.mod.{i}", "push", PATTERN_DEPTH)
             for i in range(len(BANDS))]
    return rows


def save_refusal(b: Binding) -> str | None:
    """Why `b` may not drive the desk's SAVE (plan 24 C1), or None: only a
    `momentary` row may — anything that could leave `desk.save` on (a
    toggle, a set, a key or pad row that fires) would turn every bank pad's
    tap into a new preset until something turned it off."""
    if b.target == SAVE_PARAM and b.op != "momentary":
        return f"{SAVE_PARAM} takes only a momentary row (held, never latched)"
    return None


def _drop_save_latches(rows: list[Binding]) -> tuple[list[Binding], list[str]]:
    """`rows` less any row `save_refusal` refuses, with a note for each."""
    kept, notes = [], []
    for b in rows:
        why = save_refusal(b)
        if why is None:
            kept.append(b)
        else:
            notes.append(f"dropped {b.source} → {b.target} ({b.op}): {why}")
    return kept, notes


def save_missing(rows: Iterable[Binding]) -> str | None:
    """Plan 24 C1: a table with no row on the desk's SAVE because the owner's
    own row holds its control (track 8's clip stop: `remap_factory` adds
    SAVE only where nothing uses the note) — the line that says so on the
    SYSTEM page, so SAVE's absence is never silent. None when SAVE is there
    or its control is free (a table with no APC40 rows)."""
    rows = list(rows)
    if any(b.target == SAVE_PARAM for b in rows):
        return None
    save = Binding(f"note:{apc40.SAVE[1]}:{apc40.SAVE[0]}", SAVE_PARAM, "momentary")
    mine = next((b for b in rows if b.is_midi and b.overlaps(save)), None)
    if mine is None:
        return None
    return (f"SAVE not added: {save.source} is yours ({mine.target}) — the two-handed "
            "save needs track 8's clip stop free")


def referee(rows: Iterable[Binding]) -> tuple[list[Binding], list[tuple[Binding, str]]]:
    """First performer per target wins: (kept, [(dropped row, why)]).

    What a preset or a file gets instead of a prompt — the loader asks
    nothing, so the rule is fixed: table order decides.
    """
    kept: list[Binding] = []
    dropped: list[tuple[Binding, str]] = []
    owners: dict[str, Binding] = {}
    for b in rows:
        if b.is_performer:
            cur = owners.get(b.target)
            if cur is not None:
                dropped.append((b, f"{b.target} is already performed by {cur.describe()}"))
                continue
            owners[b.target] = b
        kept.append(b)
    return kept, dropped


def migrate_v1(rows: Iterable[Binding]) -> tuple[list[Binding], list[str]]:
    """Schema 1 → 2: the performer ops renamed (`mod` → push with the
    source's own rest, `span` → position, a lane-scheme `abs` → position
    at depth 1), `replace` dropped. Returns (rows, a note per row dropped);
    `referee` then settles second owners, and `remap_factory` — run on
    every table load, not only here — brings the factory rows up to date."""
    out: list[Binding] = []
    notes: list[str] = []
    for b in rows:
        if not is_continuous(b.scheme):
            out.append(b)
            continue
        op = V1_TO_OP.get(b.op)
        if op is None:
            why = f"no such op in {SCHEMA}"
            if b.op == V1_REPLACE:
                why += " — a push on a base of 0 is the additive twin"
            notes.append(f"dropped {b.source} → {b.target} ({b.op}): {why}")
            continue
        if b.op == "abs":            # a learned hand: the whole throw (pickup is
            b.value = 1.0            # not a performer's field — to_json drops it)
        b.op = op
        out.append(b)
    return out, notes


def _write_new(path: Path, data: bytes) -> None:
    """Write a file that must not exist yet — exclusive, so a backup never
    lands on a file that appeared since its name was chosen."""
    with open(path, "xb") as f:
        f.write(data)


# `Bindings.error` while the file is owed a backup that cannot be made
NOT_REWRITTEN = "bindings: not rewritten — no backup could be made"


def backup(path: Path, schema: str) -> Path | None:
    """The file as it is, kept beside itself before the loader rewrites it
    (a migration or a factory remap, audit R12): ``<file>.bak-v<schema>``
    the first time, and ``<file>.bak-v<schema>-<stamp>`` when that name is
    taken — so the oldest state and the one about to go are both kept, and
    nothing already there, this loader's or a copy the owner made by hand
    under any ``.bak-*`` name, is ever overwritten. A copy that cannot be
    made never stops the load. Returns the path written."""
    bak = path.with_name(f"{path.name}.bak-v{schema}")
    if bak.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        bak = path.with_name(f"{path.name}.bak-v{schema}-{stamp}")
        n = 1
        while bak.exists():
            n += 1
            bak = path.with_name(f"{path.name}.bak-v{schema}-{stamp}-{n}")
    try:
        _write_new(bak, path.read_bytes())
    except OSError as e:
        print(f"backup: no backup of {path}: {e}", file=sys.stderr)
        return None
    print(f"backup: {path.name} kept as {bak.name} before the rewrite", file=sys.stderr)
    return bak


def remap_factory(rows: Iterable[Binding]) -> tuple[list[Binding], list[str]]:
    """The factory rows plan 09 WP4 and plan 15 WP3 moved, on a table of
    any schema: the old APC40 factory rows swapped for the new (APC_REMAP —
    the clock's three buttons, the crossfader's master dim), the METRONOME /
    QUANT / OVERDUB notes, the clip-stop row's eight (plan 15 WP4: save-as,
    held), the bank's sixteen pads on clip rows 4 and 5 (plan 19 WP2) and
    the B / ⇧B and loop keys (Home among them)
    added where nothing uses the source (APC_NEW_ROWS, KEY_NEW_ROWS); the
    clip-stop SAVE AS bar dropped (RETIRED_ROWS, 2026-10-09: a held empty
    bank pad saves now); and,
    since plan 13 WP2, any row on a ``theme.*`` param moved to the
    ``preset.*`` param of the same slot (THEME_TO_PRESET); the pad's four
    old factory rows (and B / X's bank rows) moved to the layout of
    2026-10-14 (PAD_REMAP); the track faders' eight invariant audio rows
    moved to the SHIFT layer (FADER_SHIFT_ROWS, plan 24 C2).
    Idempotent: a second pass finds every old row gone
    and every source taken. Returns (rows, a note per change).

    Plan 19's swap (the sixteen old shape pads, BANK_REMAP) also clears
    the row's layer and gives it the factory row's light: the pad is
    invariant now, and a file from between plan 13's WP3 and WP5 has those
    rows on the preset layer. An APC40 row is added only where no MIDI row
    of the table is on its control (`Binding.overlaps`: an any-channel row
    the owner wrote by hand holds every track's pad)."""
    out: list[Binding] = []
    notes: list[str] = []
    moved_theme = False
    for b in rows:
        if (b.source, b.target, b.op, float(b.value)) in RETIRED_ROWS:
            notes.append(f"removed {b.source} → {b.target} (the clip-stop SAVE AS bar is "
                         "retired: hold an empty bank pad to save into it; the row is free)")
            continue
        hit = APC_REMAP.get((b.source, b.target, b.op, float(b.value)))
        if hit is not None:
            target, op, value = hit
            plan = APC_REMAP_PLAN.get(b.source, "plan 09")
            notes.append(f"remapped {b.source}: {b.target} → {target} (the APC40 map "
                         f"of {plan})")
            moved_theme = moved_theme or b.target == "theme.next"
            b = replace(b, target=target, op=op, value=value)
            if plan == "plan 19":
                b = replace(b, layer=None, feedback="led", on=apc40.GREEN, off=0)
        elif ((b.source, b.target, b.op, float(b.value)) in FADER_SHIFT_ROWS
              and b.layer is None):
            notes.append(f"moved {b.source} → {b.target} to the SHIFT layer (the APC40 "
                         "map of plan 24: the track faders are the presets')")
            b = replace(b, layer="global")
        elif (b.source, b.target, b.op, float(b.value)) in PAD_REMAP:
            hit = PAD_REMAP[(b.source, b.target, b.op, float(b.value))]
            if hit is None:
                notes.append(f"removed {b.source} → {b.target} (the pad layout of "
                             "2026-10-14: the button is free)")
                continue
            target, op, value = hit
            notes.append(f"remapped {b.source}: {b.target} → {target} (the pad layout "
                         "of 2026-10-14)")
            b = replace(b, target=target, op=op, value=value)
        elif b.target in THEME_TO_PRESET:
            target = THEME_TO_PRESET[b.target]
            notes.append(f"remapped {b.source}: {b.target} → {target} (the preset bank "
                         "of plan 13)")
            b = replace(b, target=target)
        out.append(b)
    used = {b.source for b in out}
    midi = [b for b in out if b.is_midi]
    for source, target, op, value, only_if_moved in APC_NEW_ROWS:
        new = Binding(source, target, op, value, feedback="led")
        if (source in used or (only_if_moved and not moved_theme)
                or any(b.overlaps(new) for b in midi)):
            continue
        out.append(new)
        notes.append(f"added {source} → {target} (the APC40 map of "
                     f"{APC_REMAP_PLAN.get(source, 'plan 09')})")
    for source, target, op, value in PAD_NEW_ROWS:
        if source in used:
            continue
        out.append(Binding(source, target, op, value))
        notes.append(f"added {source} → {target} (the pad layout of 2026-10-14)")
    # a key row is taken by its chord, however its modifiers are ordered:
    # "key:SUPER+SHIFT+Z" holds ⌘⇧Z as "key:SHIFT+SUPER+Z" does
    chords = {(b.key_name, b.modifiers) for b in out if b.scheme == "key"}
    for source, target, op, value in KEY_NEW_ROWS:
        new = Binding(source, target, op, value)
        if source in used or (new.key_name, new.modifiers) in chords:
            continue
        out.append(new)
        notes.append(f"added {source} → {target} (the keys of plans 09, 11 and 15)")
    return out, notes


# ---------------------------------------------------------------- macros
#
# One macro concept (plan 13 D10, §2.4; decision register rows 12, 12b): a
# macro is a knob, `macro.1–8`, an ordinary param, with a list of
# subscribers. A *base* subscriber is a scene-setter: whenever the macro's
# base moves (a knob, the panel, a restore — never an offset) it sets its
# param's base to `from + m · (to − from)` along the param's own fader
# (`Router.follow_macros`). A *depth* subscriber scales one route: its row's
# depth is multiplied by `from + m · (to − from)` with m the macro's
# effective value, this frame's (`Router.modulate` runs the macro's node
# first, plan 28 N0) — so a performer riding
# a macro moves its depth subscribers only. Polarity is per subscriber; a
# depth range may cross zero, flipping the route partway through the throw.

@dataclass
class Sub:
    """One subscriber: `base` names a param, or `depth` names a route by
    (source, target); `lo` / `hi` are the file's `from` / `to`."""
    base: str | None = None
    depth: tuple[str, str] | None = None
    lo: float = 0.0
    hi: float = 1.0

    def at(self, m: float) -> float:
        return self.lo + m * (self.hi - self.lo)

    def to_json(self) -> dict:
        d: dict = ({"base": self.base} if self.depth is None else
                   {"depth": {"source": self.depth[0], "target": self.depth[1]}})
        return {**d, "from": self.lo, "to": self.hi}

    @classmethod
    def from_json(cls, d: dict) -> Sub:
        lo, hi = float(d.get("from", 0.0)), float(d.get("to", 1.0))
        if "depth" in d:
            dep = d["depth"]
            return cls(depth=(str(dep["source"]), str(dep["target"])), lo=lo, hi=hi)
        return cls(base=str(d["base"]), lo=lo, hi=hi)


@dataclass
class Macro:
    label: str = ""
    subs: list[Sub] = field(default_factory=list)

    def to_json(self) -> dict:
        d: dict = {"label": self.label} if self.label else {}
        return {**d, "subs": [s.to_json() for s in self.subs]}

    @classmethod
    def from_json(cls, d: dict) -> Macro:
        return cls(str(d.get("label", "")), [Sub.from_json(s) for s in d.get("subs", [])])

    @property
    def empty(self) -> bool:
        return not self.label and not self.subs


def is_macro(pid: str | None) -> bool:
    return bool(pid) and pid.startswith(MACRO_PREFIX) and pid[len(MACRO_PREFIX):].isdigit()


def macros_of(doc: dict | None) -> dict[str, Macro]:
    """A file's `macros` key as {id: Macro}."""
    return {mid: Macro.from_json(m) for mid, m in (doc or {}).items()}


def is_session_id(pid: str | None) -> bool:
    """Does `pid` name a session param (params.SESSION_GROUPS, plan 13 §4)?
    By its group prefix, so a param this registry lacks (a band a layout
    has not built yet) is still classed."""
    return bool(pid) and pid.partition(".")[0] in SESSION_GROUPS


def base_refusal(pid: str, reg: Registry | None = None) -> str | None:
    """Why a macro's base subscriber may not name `pid`, or None when it
    may (plan 13 D9, review of PR #67). A base subscriber is a scene-setter
    a preset carries, so it names a **performance** param — persisted, not
    an alias — never a session one (a preset never moves a session base).
    With a registry the param's own group and flags decide; an id it lacks,
    or no registry, is judged by its group prefix, so a param this build
    has not made yet is kept when its group is a performance one."""
    p = reg.get(pid) if reg is not None else None
    if p is None:
        group = pid.partition(".")[0]
        if group in SESSION_GROUPS:
            return "a session param, never a preset's (plan 13 D9)"
        return None if group in PERFORMANCE_GROUPS else "not part of a preset"
    if part_of(p) == "session":
        return "a session param, never a preset's (plan 13 D9)"
    if p.alias:
        return "an alias, not part of a preset"
    if part_of(p) != "performance" or not p.persist:
        return "not part of a preset"
    return None


def settle_bases(doc: dict | None, reg: Registry | None = None
                 ) -> tuple[dict[str, Macro], list[str]]:
    """A file's `macros` key as {id: Macro}, each base subscriber that may
    not be one (`base_refusal`) dropped with a note. Depth subscribers are
    untouched: a route may perform a session param (decision register row
    19 (a)), and its depth subscriber with it."""
    macros = macros_of(doc)
    notes: list[str] = []
    for mid, m in macros.items():
        keep = []
        for s in m.subs:
            why = base_refusal(s.base, reg) if s.base is not None else None
            if why is None:
                keep.append(s)
            else:
                notes.append(f"dropped {mid}'s base subscriber {s.base}: {why}")
        m.subs = keep
    return macros, notes


def migrate_scales(rows: Iterable[Binding], macros: dict[str, Macro]) -> list[str]:
    """A route's `scale` settled (decision register row 18 (a)): it is the
    rig's attenuator, so it names a **session** param — the legacy6 rate
    rows' `master.gain`, the drive fader — and is kept only then.
    `scale: "macro.N"` becomes a depth subscriber of macro.N `from 0, to 1`
    (unless an identical one is there) and the row loses the field (plan 13
    §2.4); a `scale` naming any other param — a performance one, which a
    preset load could move under the route — is dropped, the depth left as
    it is. Edits `rows` and `macros` in place; returns a note per row."""
    notes: list[str] = []
    for b in rows:
        if b.scale is None or is_session_id(b.scale):
            continue
        if not is_macro(b.scale):
            notes.append(f"dropped the scale {b.scale} of {b.source} → {b.target}: a route's "
                         "scale is a session param (decision register row 18 (a)); a macro "
                         "attenuates a route as its depth subscriber")
            b.scale = None
            continue
        m = macros.setdefault(b.scale, Macro())
        sub = Sub(depth=(b.source, b.target), lo=0.0, hi=1.0)
        if sub not in m.subs:
            m.subs.append(sub)
        notes.append(f"moved {b.source} → {b.target} × {b.scale} to a depth subscriber "
                     f"of {b.scale} (plan 13 §2.4)")
        b.scale = None
    return notes


# ---------------------------------------------------------------- the desk

def factory_desk(profile: str = "apc40") -> list[Binding]:
    """The profile's default MIDI map with its layers (plan 13 §3.2)."""
    return [Binding.from_json(d) for d in apc40.DEFAULT_MAP] if profile == "apc40" else []


def sort_layers(rows: Iterable[Binding], profile: str = "apc40"
                ) -> tuple[list[Binding], list[str]]:
    """Give an older file's MIDI rows their layers, once (plan 13 §3.2, §6):
    a row identical to a factory row in (source, target, op, value) takes
    that row's layer; any other row on an invariant factory control stays
    invariant; any other row goes to the preset layer. Then the factory's
    global rows and SHIFT are added where the file has no row on that
    control for that layer. A profile with no factory map keeps every row
    invariant. Returns (rows, notes)."""
    rows = list(rows)
    factory = factory_desk(profile)
    if not factory:
        return rows, []
    layer_of = {(f.source, f.target, f.op, float(f.value)): f.layer for f in factory}
    invariant = [f for f in factory if f.layer is None]
    n = 0
    notes: list[str] = []
    # SHIFT is the layer latch now (it was unused before plan 13): a row a
    # user put on its note would keep the latch off the desk for good
    shift = [b for b in rows if b.is_midi and b.overlaps(_SHIFT) and b.target != SHIFT_PARAM]
    for b in shift:
        notes.append(f"dropped {b.source} → {b.target}: SHIFT is the desk's layer latch "
                     "(plan 13 D4)")
    rows = [b for b in rows if not any(b is x for x in shift)]
    for b in rows:
        if not b.is_midi:
            continue
        key = (b.source, b.target, b.op, float(b.value))
        if key in layer_of:
            b.layer = layer_of[key]
        elif any(b.overlaps(f) for f in invariant):
            b.layer = None
        else:
            b.layer = "preset"
        n += 1
    if n:
        notes.insert(0, f"sorted {n} MIDI rows into the desk's layers (plan 13 §3.2)")
    for f in factory:
        if f.layer != "global" and f.source != SHIFT_SOURCE:
            continue
        if any(b.is_midi and b.layer == f.layer and b.overlaps(f) for b in rows):
            continue
        rows.append(f)
        where = "the global layer" if f.layer else "invariant"
        notes.append(f"added {f.source} → {f.target} ({where}, plan 13 §3.2)")
    return rows, notes


PICKUP_TOL = 1.5 / 127   # a knob "reaches" the value within this (midi.py)


def led_lit(b: Binding, p: Param) -> bool:
    """Is a note row's LED on for `p`'s state now — the device's light and
    the on-screen desk's (ui_desk.py) from one rule."""
    if p.kind is Kind.TOGGLE:
        return bool(p.value) if b.op != "set" else bool(p.value) == bool(b.value)
    if p.kind is Kind.ENUM:
        return p.value == int(b.value) if b.op == "set" else b.lit
    if p.kind is Kind.CONTINUOUS and b.op == "set":
        return abs(p.norm - float(b.value)) <= PICKUP_TOL
    if p.kind is Kind.TRIGGER:
        # the press echo, or a light the param carries itself (a trigger
        # declared with `lit=`: the METRONOME LED blinking on the beat)
        return b.lit or bool(p.get())
    return b.lit


def led_level(b: Binding, p: Param) -> int:
    """A note row's light as a level (plan 19 WP2, fork 5). 2: lit
    (`led_lit`). 1: a `set` row on an enum whose param says that choice
    holds something (`Param.has` — only the bank's `preset.select` does)
    and is not the one selected: a bank pad whose slot is filled. 0: off.
    The device's light (midi.py: the profile's `filled_of` at level 1) and
    the on-screen desk's (ui_desk.py) from one rule."""
    if led_lit(b, p):
        return 2
    has = getattr(p, "has", None)        # (a Param from before a hot reload has none)
    if b.op == "set" and p.kind is Kind.ENUM and has is not None and has(int(b.value)):
        return 1
    return 0


def register_desk(reg: Registry, table: Bindings) -> None:
    """`desk.shift`: the layer latch as a toggle over the table — on while
    the global layer is up — so SHIFT is a row like any other (a note row
    toggles it, its LED reads it) and a page or key row can reach it too.
    Never saved, never performed. `desk.save`: the desk's SAVE held (plan
    24 C1) — a momentary row sets it, and while it is on a bank pad's tap
    saves instead of loading (midi.py); never saved, never performed. And
    `desk.slew`: the table's knob smoothing (plan 18 WP2), a session param
    a show keeps and no preset may name. The first table a registry meets
    keeps each."""
    if SHIFT_PARAM not in reg:
        reg.toggle(SHIFT_PARAM, "Shift", lambda: table.layer == "global",
                   lambda v: table.set_layer("global" if v else "preset"), group="desk",
                   persist=False, modulatable=False,
                   tip="The APC40's SHIFT, latched: on, the desk shows the global layer "
                       "(the band strip, the hand feel, BPM, the band scenes); off, the "
                       "loaded preset's. Loading a preset turns it off.")
    if SAVE_PARAM not in reg:
        # held by the hand on SAVE, never saved: a reconnect lets go of it
        # (midi.MidiIO._enter), so a lost note-off cannot leave it down
        held = [False]
        reg.toggle(SAVE_PARAM, "Save", lambda: held[0],
                   lambda v: held.__setitem__(0, bool(v)), group="desk",
                   persist=False, modulatable=False,
                   tip="The APC40's SAVE (track 8's clip stop): hold it and tap a bank "
                       "pad to save the live state into that slot. An empty slot gets a "
                       "new preset; a filled one gets a new preset too (TRIP → TRIP 2) "
                       "and the old one stays in the preset list. Nothing is ever "
                       "overwritten. SAVE alone does nothing.")
    if SLEW_PARAM not in reg:
        reg.continuous(SLEW_PARAM, "Knob smoothing",
                       lambda: getattr(table, "slew", 0.0),
                       lambda v: setattr(table, "slew", min(max(float(v), 0.0), SLEW_MAX_S)),
                       lo=0.0, hi=SLEW_MAX_S, group="desk", modulatable=False,
                       fmt=lambda v: "off" if v <= 0 else f"{v * 1000:.0f} ms",
                       tip="How long a value from a desk knob or fader takes to arrive. "
                           "Off: it jumps a detent at a time, as before. One setting for "
                           "every knob and fader; buttons and the cue knob are not smoothed.")
    _register_pad_feel(reg, table)


def declare_modifiers(reg: Registry, mods: Iterable[Modifier]) -> None:
    """The modifiers' params on `reg` (plan 28 N1), the way `fx.declare`
    adds an effect's: every ``mod.*`` param dropped, then ``mod.<n>.<p>``
    for each modifier's kind (`modifiers.PARAMS`), group ``mod`` — a
    performance group, so preset content — modulatable, a view onto the
    modifier's `params`. A route onto one of a modifier that went away
    goes dormant, as for a deleted band."""
    reg.remove_prefix(modifiers.PREFIX)
    g = modifiers.GROUP
    for m in mods:
        for sp in modifiers.PARAMS[m.kind]:
            pid, label = modifiers.param_id(m.id, sp.key), f"mod {m.n} {sp.label}"
            vals, k = m.params, sp.key
            tip = f"{m.kind} {m.n}: {sp.tip}" if sp.tip else ""
            if sp.kind == "toggle":
                reg.toggle(pid, label, lambda v=vals, k=k: v[k] >= 0.5,
                           lambda x, v=vals, k=k: v.__setitem__(k, 1.0 if x else 0.0),
                           group=g, tip=tip)
            elif sp.kind == "enum":
                reg.enum(pid, label, lambda v=vals, k=k: round(v[k]),
                         lambda x, v=vals, k=k: v.__setitem__(k, float(int(x))),
                         list(sp.choices), group=g, tip=tip)
            else:
                reg.continuous(pid, label, lambda v=vals, k=k: v[k],
                               lambda x, v=vals, k=k: v.__setitem__(k, float(x)),
                               lo=sp.lo, hi=sp.hi, group=g, tip=tip)


PAD_FEEL = "desk.pad"     # the pad's feel: PAD_FEEL + ".feel" / ".attack" / …


def _register_pad_feel(reg: Registry, table: Bindings) -> None:
    """The pad's feel as five session params over `table.pad_feel`: the
    motion an `axis` lane travels with when its row names none, and the
    sticks' default camera job's (motion.py). Off, a stick is as it reads."""
    if f"{PAD_FEEL}.feel" in reg:
        return

    def get(k):
        return lambda: getattr(getattr(table, "pad_feel", OFF), k)

    def put(k, lo, hi):
        def set_(v):
            v = min(max(float(v), lo), hi)
            table.pad_feel = replace(getattr(table, "pad_feel", OFF), **{k: v})
        return set_

    reg.enum(f"{PAD_FEEL}.feel", "Stick feel",
             lambda: motion.MODES.index(getattr(table, "pad_feel", OFF).mode),
             lambda i: setattr(table, "pad_feel",
                               replace(getattr(table, "pad_feel", OFF),
                                       mode=motion.MODES[int(i) % len(motion.MODES)])),
             list(motion.MODES), group="desk", modulatable=False,
             tip="How the gamepad's sticks and triggers travel once read — their "
                 "routes (a row with no feel of its own) and their camera job. "
                 "off: as the hardware reads. follow: the analyzer's envelope — "
                 "attack away from rest, release back toward it, so a stick let go "
                 "glides home. spring: a damped spring toward the stick.")
    def ms(v):
        return f"{v * 1000:.0f} ms"
    reg.continuous(f"{PAD_FEEL}.attack", "Stick attack", get("atk"),
                   put("atk", 0.0, motion.ATK_MAX), lo=0.0, hi=motion.ATK_MAX,
                   group="desk", modulatable=False, fmt=ms,
                   tip="follow: how long a stick takes moving away from rest (63 %).")
    reg.continuous(f"{PAD_FEEL}.release", "Stick release", get("rel"),
                   put("rel", 0.0, motion.REL_MAX), lo=0.0, hi=motion.REL_MAX,
                   group="desk", modulatable=False, fmt=ms,
                   tip="follow: how long a stick takes going back toward rest (63 %) — "
                       "long, and the spring's snap becomes a glide.")
    reg.continuous(f"{PAD_FEEL}.hz", "Stick spring", get("hz"),
                   put("hz", motion.HZ_MIN, motion.HZ_MAX), lo=motion.HZ_MIN,
                   hi=motion.HZ_MAX, log=True, group="desk", modulatable=False,
                   fmt=lambda v: f"{v:.2f} Hz",
                   tip="spring: its natural frequency — low is lazy, high is tight.")
    reg.continuous(f"{PAD_FEEL}.damp", "Stick damping", get("damp"),
                   put("damp", 0.0, motion.DAMP_MAX), lo=0.0, hi=motion.DAMP_MAX,
                   group="desk", modulatable=False, fmt=lambda v: f"ζ {v:.2f}",
                   tip="spring: the damping ratio. 1 arrives fastest without "
                       "overshoot; below 1 it overshoots and rings; above, it creeps.")


def legacy_planedrive(lanes, gain: float = 1.0) -> np.ndarray:
    """The reference's PLANEDRIVE from six lanes — what the legacy6 routes
    must land on rot.rate.* (tests/test_core.py computes it from the
    offline driver's `out`; offline.py itself ends at the lanes)."""
    drive = np.ones(6)
    for i, b in enumerate(BANDS[: len(lanes)]):
        drive[b.plane] = b.dir * lanes[i] * DRIVE * gain
    return drive


def dumps_doc(d: dict) -> str:
    """A bindings document as file text: one row per line, so a diff reads
    as a binding."""
    rows = ",\n".join("  " + json.dumps(b) for b in d["bindings"])
    text = f'{{\n "schema": {json.dumps(d["schema"])},\n'
    text += f' "profile": {json.dumps(d["profile"])},\n'
    if d.get("sinks_seeded"):            # plan 27 B3: the sinks' `send` lists translated
        text += f' "sinks_seeded": {json.dumps(d["sinks_seeded"])},\n'
    text += f' "bindings": [\n{rows}\n ]'
    return text + "\n}\n"


def is_session_row(b: Binding) -> bool:
    """A row `bindings.json` keeps (plan 13 §2.2): anything but a performer
    row (push / position, disabled ones too) and a preset-layer MIDI row —
    those are the loaded preset's. A sink row (plan 27 B3, `SINK_OP`) is
    the session's: sinks are rig (D1 / D9)."""
    return b.op not in MOD_OPS and not (b.is_midi and b.layer == "preset")


@dataclass
class Carried:
    """What an older `bindings.json` held that is a preset's now (plan 13
    §6): its performer rows (the referee's refusals after them, so nothing
    is lost and the first still wins), its preset-layer MIDI rows (None:
    the file had none), its macros and its `values`. `Bindings.load` keeps
    it; `preset.migrate_home` moves it into presets and then rewrites the
    file without it."""
    routes: list[dict]
    desk: list[dict] | None
    macros: dict
    values: dict

    @property
    def empty(self) -> bool:
        return not (self.routes or self.desk or self.macros or self.values)


class Bindings:
    """The whole table: rows of every scheme, one file, indexed for the adapters.

    In memory the table holds the session's controls and the loaded
    preset's performer rows, preset layer and macros; the file
    (`to_json`, `write`) holds only the session's (`is_session_row`)."""

    # knob smoothing in seconds (`desk.slew`, register_desk; midi.py reads
    # it): the session's — a show keeps it, bindings.json never does. On
    # the class, so a table from before a hot reload has it too
    slew: float = 0.0
    # the pad's feel (`pad.feel` …, register_desk): the motion an `axis`
    # lane travels with when its row names none, and the sticks' default
    # camera job's (app.py). The session's, on the class like `slew`
    pad_feel: Motion = OFF
    # no backup, no rewrite (plan 19 fork 12): the schema number the file
    # was read at while a load changed the table in memory (a migration, a
    # factory remap) and the copy of the file as it was could not be made.
    # The file is then left as it is; `write` tries the copy again before
    # anything is written over it, and the next launch tries the lot again.
    # None once the copy exists (or was never needed)
    unbacked: str | None = None
    # what the launch did to the file, in one line, for the SYSTEM page
    # (`announce`; app.py adds it to the page's notes). `notes` holds the
    # rows one by one until the next edit — and the startup preset's load
    # is an edit (`set_routes`), so they are gone before the first frame;
    # this line stays for the session. "" when the load wrote nothing
    said: str = ""
    # the MIDI devices' roles (plan 27 B2; the device registry sets them,
    # `DeviceRegistry.midi_roles`: the desk of this table's profile first,
    # then `[[devices]]` order): an unqualified MIDI row is the first
    # one's, another device's rows carry its role (``cc@launch:0:7``).
    # Empty — a bare table, the tests' — every unqualified row is the
    # one desk's, as before
    midi_roles: tuple[str, ...] = ()
    # every other scheme's primary device (plan 27 B6; the registry sets
    # it, `DeviceRegistry.primaries`): scheme → the role of the first
    # enabled device of its kind in list order, whose rows are unqualified
    # (``pad:A`` is the first pad's; a second pad's carry its role,
    # ``pad@p2:A``). Empty — a bare table — names no role
    primaries: dict[str, str] = {}  # noqa: RUF012 — never mutated: replaced whole
    # the schemes delivered as rows, never read as lanes (`_check`): the
    # table's own kinds, and any a device of this rig adds (`Router.use`)
    row_schemes: tuple[str, ...] = ROW_SCHEMES
    # the loaded preset's modifiers (plan 28 N1, `modifiers.Modifier`), in
    # id order: a tuple, always replaced whole (`set_modifiers`,
    # `add_modifier`, `remove_modifier`), so a table from before a hot
    # reload reads the class's empty one. The preset's, never the file's:
    # `to_json` writes rows only, and `is_session_row` is about rows
    modifiers: tuple[Modifier, ...] = ()
    modifiers_serial: int = 0    # bumped by every change: the Router's lanes follow

    def __init__(self, bindings: Iterable[Binding] = (), *, path: Path | None = None,
                 profile: str = "apc40"):
        self.bindings: list[Binding] = list(bindings)
        self.path = path
        self.profile = profile
        # the preset content an older file carried (`Carried`), until the
        # first-launch migration moves it into presets; None once it has
        # (or for a file that never had any)
        self.carried: Carried | None = None
        self.error = ""
        # what the referee refused from the last preset or file, (row, why),
        # for the ROUTING page to show until the next edit
        self.dropped: list[tuple[Binding, str]] = []
        # from_json read a schema-1 file: `notes` names every row it dropped
        # or remapped (Bindings.load prints them, the ROUTING page shows them
        # next to `dropped` until the next edit), so the file can be checked
        self.migrated = False
        self.notes: list[str] = []
        # the schema number the file was read at ("1", "2", "3"), for the
        # backup's name; `changed` — the loader moved something (the desk's
        # layers sorted, a macro `scale` moved to a subscriber) and the
        # file is written back once
        self.read_at = "3"
        self.changed = False
        # the macros' subscribers (plan 13 §2.4), {"macro.N": Macro}
        self.macros: dict[str, Macro] = {}
        self.macros_serial = 0        # bumped by set_macros: Router.follow_macros re-lands
        # the sink roles whose old `send` list has been translated into sink
        # rows (plan 27 B3, devices.DeviceRegistry._seed_sinks): kept in the
        # file, so deleting every row of a role never brings the list back
        self.sinks_seeded: list[str] = []
        # the desk (plan 13 §3): which layer is up — runtime, never saved,
        # a fresh start is on the preset layer — and two counters the MIDI
        # adapter watches: a layer change or a desk replacement redraws
        # every ring and LED, and a replacement clears the faders' catch
        self.layer = "preset"
        # the other MIDI roles' layers (plan 27 B2: the latch is per role —
        # `layer` is the first role's, SHIFT's, `desk.shift`); a role with
        # no latch of its own stays on the preset layer
        self.layers: dict[str, str] = {}
        self.layer_serial = 0
        self.desk_serial = 0
        # an edit of a desk row in place (the ROUTING page): a redraw only,
        # never the faders' catch cleared — no base moved
        self.redraw_serial = 0

    # ---- construction ----

    @classmethod
    def factory(cls, profile: str = "apc40", path: Path | None = None) -> Bindings:
        """Keys, pad and the device profile's default MIDI map — its preset
        layer too, the fresh preset's desk, which the file never keeps. No
        performer rows: those are the loaded preset's (plan 13 §2.2; the
        house presets carry the legacy6 lane rows)."""
        return cls([*keymap(), *padmap(), *factory_desk(profile)], path=path, profile=profile)

    @classmethod
    def load(cls, path: Path | None, profile: str = "apc40",
             legacy_midi: Path | None = LEGACY_MIDI_FILE) -> Bindings:
        """The file at `path`, else the factory table — with an old
        midi_map.json's rows in place of the factory MIDI part, written once.
        A schema-1 file is migrated the same way: noted on stderr, written
        back once, and from then on the file rules. Whatever the schema,
        the factory rows plan 09 moved are brought up to date on every load
        (`remap_factory`) — a change is noted and written back once, and a
        table already current is left alone. The file as it was is copied
        beside itself first (`backup`); **if that copy cannot be made the
        file is not rewritten** (plan 19 fork 12): the table in memory is
        the changed one, `error` says so, and the next launch tries again.

        A file that still holds a preset's part — performer rows,
        preset-layer MIDI rows, `macros`, `values` (every file before plan
        13 WP5) — keeps it in memory and in `carried`, and is **not**
        rewritten here, whatever else changed: `preset.migrate_home` moves
        that part into presets first and only then backs the file up and
        rewrites it, so a crash in between loses nothing."""
        if path is not None and path.exists():
            try:
                data = json.loads(path.read_text())
                t = cls.from_json(data, path=path)
                t.profile = t.profile or profile
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
                t = cls.factory(profile, path)
                t.error = f"bindings: {e}"
                return t
            t.bindings, remapped = remap_factory(t.bindings)
            t.notes += remapped
            carried = Carried(
                routes=[b.to_json() for b in [*t.routes(), *(b for b, _ in t.dropped)]],
                desk=[b.to_json() for b in t.desk()] or None,
                macros=t.macros_doc(), values=dict(data.get("values") or {}))
            if not carried.empty or "values" in data or "macros" in data:
                t.carried = carried              # preset.migrate_home writes the file
            elif t.migrated or t.changed or remapped:
                bak = backup(path, t.read_at)
                if bak is None:                          # no backup, no rewrite
                    t.unbacked, t.error = t.read_at, NOT_REWRITTEN
                    t.announce(path, written=False)
                else:
                    t.announce(path, kept=bak)
                    t.write()
            missing = save_missing(t.bindings)
            if missing is not None:          # said every launch, never written: the row is yours
                print(f"bindings: {path}: {missing}", file=sys.stderr)
                t.said = f"{t.said} · {missing}" if t.said else missing
            return t
        t = cls.factory(profile, path)
        if legacy_midi is not None and legacy_midi.exists():
            try:
                data = json.loads(legacy_midi.read_text())
                rows = [Binding.from_json(b) for b in data.get("bindings", [])]
                t.profile = data.get("profile", profile)
                n = len(rows)
                rows, _ = sort_layers(rows, t.profile)     # the desk's layers, plan 13 §3.2
                t.bindings = [b for b in t.bindings if not b.is_midi] + rows
                # a knob the old map had off the factory's is a preset's row
                # now: kept for the migration, like a newer file's — with the
                # lane rows the factory table shipped then, the routes this
                # rig played — and the file is left for the migration to write
                # (written now, it would hold the session's rows only, and a
                # launch whose migration stopped would lose the knobs)
                fresh = sorted(json.dumps(b.to_json(), sort_keys=True)
                               for b in factory_desk(t.profile) if b.layer == "preset")
                desk = [b.to_json() for b in t.desk()]
                if sorted(json.dumps(d, sort_keys=True) for d in desk) != fresh:
                    t.carried = Carried(routes=[b.to_json() for b in legacy6_routes()],
                                        desk=desk or None, macros={}, values={})
                    return t
                print(f"bindings: migrated {n} rows from {legacy_midi}"
                      + (f" into {path}" if path is not None else ""), file=sys.stderr)
                t.write()
            except (OSError, ValueError, TypeError, KeyError) as e:
                t.error = f"bindings: {legacy_midi}: {e}"
        return t

    def announce(self, path: Path, *, written: bool = True, kept: Path | None = None) -> None:
        """A migration's notes on stderr, one line per row, then the sum —
        or, `written` False, that the file was left as it was. The sum, with
        the backup's name (`kept`), is also `said`: the SYSTEM page's line."""
        for note in self.notes:
            print(f"bindings: {path}: {note}", file=sys.stderr)
        dropped = sum(n.startswith("dropped") for n in self.notes)
        changed = len(self.notes) - dropped
        tail = ", ".join(f"{n} rows {what}" for n, what in ((dropped, "dropped"),
                                                              (changed, "changed")) if n)
        verb = "migrated" if self.migrated or self.read_at != "3" else "updated"
        what = f"migrated {path} to {SCHEMA}" if verb == "migrated" else f"updated {path}"
        if not written:
            what = (f"{path} not rewritten — no backup could be made; the changes above "
                    "are in memory only and the next launch tries again")
        tail = f" ({tail})" if tail else ""
        print(f"bindings: {what}{tail}", file=sys.stderr)
        if not written:
            self.said = (f"{path.name} NOT rewritten{tail}: no backup could be made — "
                         "in memory only, the next launch tries again")
        else:
            self.said = (f"{path.name} {verb}{tail}"
                         + (f", the old file kept as {kept.name}" if kept is not None else "")
                         + " — each change is on stderr")

    @classmethod
    def from_json(cls, data: dict, path: Path | None = None, *, desk: bool = True) -> Bindings:
        """A file's dict. Schema 1 (or none) goes through `migrate_v1`; a
        schema this code doesn't know raises ValueError, like a file that
        won't parse — never rewritten. A schema-2 file with two owners on a
        target keeps the first, the rest in `dropped` — the referee, not a
        prompt, since nobody is asking.

        Schema 3 adds `layer` on MIDI rows and the `macros` key. An older
        file's MIDI rows get their layers once (`sort_layers`; a file with
        no MIDI rows gets none added, and `desk=False` — an old routing
        preset read by the migration, whose MIDI rows are never read —
        skips the sort), and on any schema a row's `scale` is settled
        (`migrate_scales`: a macro's a depth subscriber, a performance
        param's dropped); either sets `changed`, noted, so `load` writes
        the file back once (or leaves it to the migration, `load`)."""
        schema = data.get("schema")
        if schema not in (SCHEMA, SCHEMA_V2, SCHEMA_V1, None):
            raise ValueError(f"unknown schema {schema!r}")
        rows = [Binding.from_json(b) for b in data.get("bindings", [])]
        notes: list[str] = []
        migrated = schema in (SCHEMA_V1, None)
        if migrated:
            rows, notes = migrate_v1(rows)
        profile = data.get("profile", "apc40")
        changed = False
        if desk and schema != SCHEMA and any(b.is_midi for b in rows):
            rows, sorted_notes = sort_layers(rows, profile)
            notes += sorted_notes
            changed = bool(sorted_notes)
        macros = macros_of(data.get("macros"))
        moved = migrate_scales(rows, macros)
        notes += moved
        changed = changed or bool(moved)
        # a hand-edited row that would latch SAVE on (plan 24 C1): dropped,
        # said, and the file written back once without it
        rows, latched = _drop_save_latches(rows)
        notes += latched
        changed = changed or bool(latched)
        t = cls(rows, path=path, profile=profile)
        t.macros = macros
        seeded = data.get("sinks_seeded")
        t.sinks_seeded = [str(r) for r in seeded] if isinstance(seeded, list) else []
        t.bindings, t.dropped = referee(t.bindings)
        if migrated:
            notes += [f"dropped {b.source} → {b.target}: {why}" for b, why in t.dropped]
        t.migrated, t.notes, t.changed = migrated, notes, changed
        t.read_at = "1" if schema is None else schema.rpartition("/")[2]
        return t

    def to_json(self) -> dict:
        """The file's dict: the session's controls only (`is_session_row`)
        — never a performer row, a preset-layer row, the macros or any
        values; those are the loaded preset's (plan 13 §2.2)."""
        d = {"schema": SCHEMA, "profile": self.profile,
             "bindings": [b.to_json() for b in self.bindings if is_session_row(b)]}
        seeded = getattr(self, "sinks_seeded", None)      # a table from before a hot reload
        if seeded:
            d["sinks_seeded"] = list(seeded)
        return d

    def dumps(self) -> str:
        """The file text: one row per line, so a diff reads as a binding."""
        return dumps_doc(self.to_json())

    def write(self) -> None:
        """The session's controls to the file (`to_json`). While the load
        owes the file a backup (`unbacked`) that copy is made first, and
        nothing is written without it — the file stays as the owner had
        it, `error` says so."""
        if self.path is None:
            return
        if self.unbacked is not None and self.path.exists():
            bak = backup(self.path, self.unbacked)
            if bak is None:
                self.error = NOT_REWRITTEN
                return
            self.said = f"{self.path.name} updated, the old file kept as {bak.name}"
        self.unbacked = None
        try:
            self.path.write_text(self.dumps())
            self.error = ""
        except OSError as e:
            self.error = f"bindings: {e}"

    # ---- queries ----

    def of(self, *schemes: str) -> list[Binding]:
        return [b for b in self.bindings if b.scheme in schemes]

    def midi(self) -> list[Binding]:
        return self.of(*MIDI_SCHEMES)

    def mods(self) -> list[Binding]:
        """The enabled performer rows, in table order — the Router's pass."""
        return [b for b in self.bindings if b.op in MOD_OPS and b.enabled]

    def routes(self) -> list[Binding]:
        """Every performer row, disabled ones too — what the matrix lists
        and a preset saves."""
        return [b for b in self.bindings if b.op in MOD_OPS]

    def sinks(self, role: str | None = None, *, enabled: bool = True) -> list[Binding]:
        """The sink rows (plan 27 B3), in table order: those on `role`'s
        ports (None: every sink), only the enabled ones unless `enabled`
        is False."""
        return [b for b in self.bindings
                if b.is_sink and (role is None or b.sink[0] == role)
                and (b.enabled or not enabled)]

    def owner(self, pid: str) -> Binding | None:
        """The one performer on `pid`, or None — the referee's question."""
        return next((b for b in self.bindings if b.is_performer and b.target == pid), None)

    def route(self, kind: str, channel: int, number: int) -> list[Binding]:
        return [b for b in self.bindings if b.matches(kind, channel, number)]

    def for_param(self, pid: str, schemes: tuple[str, ...] = MIDI_SCHEMES) -> Binding | None:
        return next((b for b in self.bindings if b.target == pid and b.scheme in schemes), None)

    def routes_to(self, pid: str) -> list[Binding]:
        return [b for b in self.bindings if b.op in MOD_OPS and b.target == pid]

    # ---- the desk's devices (plan 27 B2) ----

    def primary_role(self) -> str:
        """The first MIDI role listed — whose rows are unqualified — or ""
        when the table has been told none."""
        roles = getattr(self, "midi_roles", ())
        return roles[0] if roles else ""

    def is_primary(self, role: str | None) -> bool:
        """Is `role` the first MIDI role (None, "" and any role of a table
        told none are)?"""
        roles = getattr(self, "midi_roles", ())
        return not role or not roles or role == roles[0]

    def role_of(self, b: Binding) -> str:
        """The role a row belongs to: its qualifier, else — a MIDI row —
        the first MIDI role's, or — any other row (plan 27 B6) — its
        scheme's primary device's (`primaries`; "" when told none)."""
        if b.device:
            return b.device
        if b.is_midi:
            return self.primary_role()
        return getattr(self, "primaries", {}).get(b.scheme, "")

    def serves(self, role: str | None, b: Binding) -> bool:
        """Is MIDI row `b` the device of `role`'s? An unqualified row is the
        first role's (and so is one qualified with that role's name); any
        other qualified row is its qualifier's only."""
        q = b.device
        if self.is_primary(role):
            return not q or q == role or q == self.primary_role()
        return q == role

    # ---- the desk: two layers under a latched SHIFT (plan 13 §3) ----

    def invariant_rows(self) -> list[Binding]:
        """The enabled MIDI rows with no layer: the session's controls."""
        return [b for b in self.bindings if b.is_midi and b.layer is None and b.enabled]

    def is_invariant(self, b: Binding, rows: list[Binding] | None = None) -> bool:
        """Is `b`'s control invariant — SHIFT (the first role's latch), or
        the control of an enabled layer-None row on the same device
        (`rows`, when the caller has them)? A layered row on such a control
        never acts and never lights (D6)."""
        if not b.is_midi:
            return False
        if self.is_primary(b.device) and Binding(b.bare, "").overlaps(_SHIFT):
            return True
        inv = self.invariant_rows() if rows is None else rows
        return any(x is not b and b.overlaps(x) for x in inv)

    @staticmethod
    def _controls(rows: Iterable[Binding], shift: bool = True) -> tuple[set, set, set]:
        """An index of `rows`' controls for `_on`: (kind, channel, number)
        of the one-channel rows, (kind, number) of the any-channel rows,
        (kind, number) of every row — SHIFT's with them for the first
        role's desk. `rows` are one device's (the qualifier is not in it)."""
        exact: set = set()
        wild: set = set()
        every: set = set()
        for x in (*rows, *((_SHIFT,) if shift else ())):
            k = (x.kind, x.number)
            every.add(k)
            if x.channel is None:
                wild.add(k)
            else:
                exact.add((x.kind, x.channel, x.number))
        return exact, wild, every

    @staticmethod
    def _on(b: Binding, index: tuple[set, set, set]) -> bool:
        """Does `b`'s control overlap one in the index (`Binding.overlaps`)?"""
        exact, wild, every = index
        k = (b.kind, b.number)
        if b.channel is None:
            return k in every
        return k in wild or (b.kind, b.channel, b.number) in exact

    def dispatch(self, kind: str, channel: int, number: int,
                 role: str | None = None) -> list[Binding]:
        """The rows a MIDI message from the device of `role` (None: the
        first MIDI role) goes to now: the invariant rows on its control,
        else the enabled rows of the layer that is up **on that device**
        (plan 27 B2: the latch is per role) — nothing else (D8: no
        fall-through; a control the up layer does not map does nothing)."""
        rows = [b for b in self.route(kind, channel, number)
                if b.enabled and self.serves(role, b)]
        inv = [b for b in rows if b.layer is None]
        if inv:
            return inv
        if (self.is_primary(role) and kind == "note" and channel == 0
                and number == _SHIFT.number):
            return []
        layer = self.layer_of(role)
        return [b for b in rows if b.layer == layer]

    def active(self, role: str | None = None) -> list[Binding]:
        """The MIDI rows of the device of `role` (None: the first MIDI
        role) that show on it now: every invariant row, and the up layer's
        rows on controls that are not invariant."""
        rows = [b for b in self.midi() if self.serves(role, b)]
        index = self._controls([b for b in rows if b.layer is None and b.enabled],
                               shift=self.is_primary(role))     # once a frame: an index,
        layer = self.layer_of(role)                             # not a pairwise scan
        return [b for b in rows
                if b.layer is None or (b.layer == layer and not self._on(b, index))]

    def layer_of(self, role: str | None = None) -> str:
        """The layer up on the device of `role`: the first role's is
        `layer` (SHIFT's, `desk.shift`); another role's is its own, the
        preset layer until something latches it."""
        if self.is_primary(role):
            return self.layer
        return self.__dict__.setdefault("layers", {}).get(role, "preset")

    def set_layer(self, layer: str, role: str | None = None) -> None:
        if layer not in LAYERS:
            raise ValueError(f"no layer {layer!r}; one of {', '.join(LAYERS)}")
        if self.is_primary(role):
            if layer != self.layer:
                self.layer = layer
                self.layer_serial += 1
            return
        layers = self.__dict__.setdefault("layers", {})
        if layers.get(role, "preset") != layer:
            layers[role] = layer
            serials = self.__dict__.setdefault("layer_serials", {})
            serials[role] = serials.get(role, 0) + 1

    def layer_serial_of(self, role: str | None = None) -> int:
        """How many times the layer up on the device of `role` has changed:
        the first role's is `layer_serial` (SHIFT's), another role's its
        own count — so a desk redraws and re-arms its faders' pickup only
        when **its** latch flips (D7, per desk), never on another's."""
        if self.is_primary(role):
            return self.layer_serial
        return self.__dict__.setdefault("layer_serials", {}).get(role, 0)

    def toggle_layer(self, role: str | None = None) -> str:
        """SHIFT's press: the other layer on that device. Returns the one
        now up."""
        self.set_layer("global" if self.layer_of(role) == "preset" else "preset", role)
        return self.layer_of(role)

    def drop_layer(self) -> None:
        """Back to the preset layer (D4) on every device — what a preset
        load does."""
        self.set_layer("preset")
        for role in list(self.__dict__.setdefault("layers", {})):
            self.set_layer("preset", role)

    def desk(self) -> list[Binding]:
        """The preset layer's rows — what a preset's `desk` holds."""
        return [b for b in self.bindings if b.is_midi and b.layer == "preset"]

    def set_desk(self, rows: Iterable[Binding | dict], *, load: bool = True) -> list[str]:
        """Replace every preset-layer row with `rows` (layer forced to
        "preset"), dropping with a note each row that is not a MIDI control
        and each on an invariant control (D6) — but one of
        `RETIRED_DESK_ROWS` on an invariant control goes without a note:
        it is a factory row of an older desk (plan 19: the sixteen shape
        pads every earlier preset holds), nothing the owner mapped. Drop
        to the preset layer
        (D4) and ask the adapter to redraw the desk and clear the faders'
        catch (`desk_serial`). Returns the notes; the file is not written —
        the desk is the loaded preset's.

        ``load=False`` is an undo's restore (undo.py, plan 15): the same
        replacement and the same dropping rules, but only a redraw is
        asked for (`redraw_serial`) — the layer that is up stays up and no
        fader's catch is cleared, because nothing was loaded."""
        keep = [b for b in self.bindings if not (b.is_midi and b.layer == "preset")]
        inv = [b for b in keep if b.is_midi and b.layer is None and b.enabled]
        notes: list[str] = []
        new: list[Binding] = []
        for r in rows:
            b = replace(r) if isinstance(r, Binding) else Binding.from_json(r)
            b.layer = "preset"
            if not b.is_midi:
                notes.append(f"dropped {b.source} → {b.target}: not a desk control")
            elif save_refusal(b) is not None:
                notes.append(f"dropped {b.source} → {b.target} ({b.op}): {save_refusal(b)}")
            elif self.is_invariant(b, inv):
                if (b.source, b.target, b.op, float(b.value)) in RETIRED_DESK_ROWS:
                    continue
                notes.append(f"dropped {b.source} → {b.target}: that control is "
                             "invariant, the session's (plan 13 D6)")
            else:
                new.append(b)
        self.bindings = keep + new
        if load:
            self.desk_serial += 1
            self.drop_layer()
        else:
            self.redraw_serial = getattr(self, "redraw_serial", 0) + 1
        return notes

    # ---- the macros' subscribers (plan 13 §2.4) ----

    def macros_doc(self) -> dict:
        """{id: {"label", "subs"}} for every macro that has either — the
        file's `macros` key."""
        return {mid: m.to_json() for mid, m in sorted(self.macros.items(),
                                                     key=lambda kv: _macro_n(kv[0]))
                if not m.empty}

    def set_macros(self, doc: dict | None, reg: Registry | None = None) -> list[str]:
        """Replace every macro's label and subscribers with `doc`'s (the
        `macros` key's shape); the router re-lands the base subscribers on
        its next `follow_macros`. A base subscriber on anything but a
        performance param — a session one above all (D9) — is dropped
        (`settle_bases`, judged against `reg` when given). Returns a note
        per subscriber dropped."""
        self.macros, notes = settle_bases(doc, reg)
        self.macros_serial += 1
        return notes

    def depth_subs(self, b: Binding) -> list[tuple[str, Sub]]:
        """(macro id, subscriber) for every depth subscriber naming `b`'s route."""
        key = (b.source, b.target)
        return [(mid, s) for mid, m in self.macros.items() for s in m.subs
                if s.depth == key]

    def move_route(self, b: Binding, *, source: str | None = None,
                   target: str | None = None) -> None:
        """Re-point a route's source or target, its depth subscribers with
        it — a subscriber names its route by (source, target), so an edit
        that moved only the row would leave the macro behind."""
        old = (b.source, b.target)
        if source is not None:
            b.source = source
        if target is not None:
            b.target = target
        self._follow_route(old, (b.source, b.target))

    def _follow_route(self, old: tuple[str, str], new: tuple[str, str] | None) -> None:
        """The route `old` moved to `new` (None: it is gone). While another
        route still has `old`'s pair its subscribers stay; otherwise they
        follow it, or go with it."""
        if old == new or any(x.op in MOD_OPS and (x.source, x.target) == old
                             for x in self.bindings):
            return
        for m in self.macros.values():
            if new is None:
                m.subs = [s for s in m.subs if s.depth != old]
            else:
                for s in m.subs:
                    if s.depth == old:
                        s.depth = new

    # ---- edits ----

    def _lane_only(self, b: Binding) -> bool:
        """Is `b`'s source read only as a lane — continuous, and not a
        scheme some device of this rig delivers as rows (`row_schemes`)?"""
        return is_continuous(b.scheme) and b.scheme not in getattr(self, "row_schemes", ())

    def _check(self, b: Binding) -> None:
        """The referee: a performer joining the table (or waking up) must
        find its target free, or held by itself. A continuous source has
        no other op — `abs` is MIDI's, the one path is Router.modulate. (A
        scheme a device delivers as rows — `row_schemes`, which the device
        registry extends through `Router.use` — is not continuous here.)"""
        if b.is_sink:                # a value going out: no referee (plan 27 B3)
            why = sink_refusal(b)
            if why is not None:
                raise ValueError(why)
            return
        if self._lane_only(b) and b.op not in MOD_OPS:
            raise ValueError(f"{b.op!r} is not an op for a {b.scheme} source; "
                             f"one of {', '.join(MOD_OPS)}")
        why = save_refusal(b)
        if why is not None:
            raise ValueError(why)
        if not b.is_performer:
            return
        cur = next((x for x in self.bindings
                    if x is not b and x.is_performer and x.target == b.target), None)
        if cur is not None:
            raise Owned(cur, b)

    def bind(self, b: Binding, *, write: bool = True) -> list[Binding]:
        """A control drives one param; a param keeps one control per role.

        Drops every row on the same physical control (`Binding.overlaps`:
        an any-channel row on that knob included, so learning ``cc:0:16``
        where the preset has ``cc:*:16`` leaves one row, not two), and the
        param's previous binding in the same role: a knob (any cc or pitch
        binding) when learning a knob, or a button of the same op and value
        when learning a button — so a param's step buttons survive a knob
        learn. Only rows of `b`'s own layer go: a preset-layer learn never takes
        an invariant or a global row with it, nor the reverse (plan 13
        D5, D6). A continuous source's row (a hand learn) is a performer
        like any route: `add` — `Owned` if the target is taken. The file
        is written unless `write` is False (a knob Learn: the row is the
        loaded preset's, plan 13 §3.3). Returns the rows dropped.
        """
        why = save_refusal(b)
        if why is not None:
            raise ValueError(why)
        if not b.is_midi:
            self.add(b)
            if write:
                self.write()
            return []

        def same_role(x: Binding) -> bool:
            # one control per param *per desk* (plan 27 B2): a knob learned
            # on a second desk leaves the param's knob on the APC40 alone
            if x.target != b.target or not x.is_midi or self.role_of(x) != self.role_of(b):
                return False
            if b.scheme == "note":
                return x.scheme == "note" and x.op == b.op and x.value == b.value
            return x.scheme in ("cc", "pitch")

        # the layers are apart (plan 13 D5, D6): a row only ever replaces
        # rows of its own layer
        def apart(x: Binding) -> bool:
            return x.layer != b.layer

        gone = [x for x in self.bindings
                if not apart(x) and (x.overlaps(b) or same_role(x))]
        self.bindings = [x for x in self.bindings if not any(x is g for g in gone)]
        self.bindings.append(b)
        self.dropped, self.notes = [], []
        if write:
            self.write()
        return gone

    def unbind(self, pid: str) -> list[Binding]:
        """Right-click → Unbind: the loaded preset's desk rows on `pid` go
        (plan 13 §3.3) — the preset is edited, not saved, so no file is
        written; a session row (invariant or global) stays, it is edited in
        `bindings.json`. Returns the rows removed."""
        gone = [b for b in self.bindings
                if b.target == pid and b.is_midi and b.layer == "preset"]
        self.bindings = [b for b in self.bindings if not any(b is g for g in gone)]
        if gone:
            self.dropped, self.notes = [], []
            self.redraw_serial += 1
        return gone

    def add(self, b: Binding) -> Binding:
        """A route (or any row) added at runtime — the routing matrix's
        edit. Raises `Owned` when the target has another performer."""
        self._check(b)
        self.bindings.append(b)
        self.dropped, self.notes = [], []
        return b

    def replace_owner(self, new: Binding, *, target: str | None = None) -> Binding | None:
        """The prompt's *Replace*, and the one way a performer takes a
        taken target: whoever performs it *now* goes — read here, at
        commit, not when the question was asked, so a row that landed
        while the prompt was up goes too — and `new` performs it. A row
        not yet in the table is added (a new route, a learn); a row already
        in it is retargeted to `target` when one is given and woken if it
        slept. Returns the row removed (None when the target was free).
        Raises only for what the referee can't allow whatever goes: a bad
        op on a continuous source (`ValueError`), or a second owner still
        standing after the swap (`Owned`)."""
        pid = new.target if target is None else target
        if self._lane_only(new) and new.op not in MOD_OPS:
            self._check(new)                     # says why, before anything moves
        cur = self.owner(pid)
        if cur is new:
            return None
        if cur is not None:
            self.remove(cur)
        if any(x is new for x in self.bindings):
            old = (new.source, new.target)
            new.target, new.enabled = pid, True
            self._check(new)
            self._follow_route(old, (new.source, new.target))
        else:
            new.target = pid
            self.add(new)
        self.dropped, self.notes = [], []
        return cur

    def enable(self, b: Binding, on: bool = True) -> None:
        """A row's checkbox. Waking a row is joining the table as far as
        the referee is concerned — `Owned` if its target was taken while
        it slept; the row stays off."""
        if on and not b.enabled:
            b.enabled = True
            try:
                self._check(b)
            except (Owned, ValueError):
                b.enabled = False
                raise
        b.enabled = on
        self.dropped, self.notes = [], []

    def remove(self, b: Binding) -> None:
        """Take a row out; a route's depth subscribers go with it unless
        another route has the same (source, target)."""
        self.bindings = [x for x in self.bindings if x is not b]
        if b.op in MOD_OPS:
            self._follow_route((b.source, b.target), None)
        self.dropped, self.notes = [], []

    def set_routes(self, routes: Iterable[Binding]) -> None:
        """Replace every performer row, keeping the input bindings. Two
        rows on one target: the first stays, the rest go to `dropped`."""
        kept, self.dropped = referee(routes)
        self.notes = []
        self.bindings = [b for b in self.bindings if b.op not in MOD_OPS] + kept

    # ---- the modifiers (plan 28 N1) ----

    def modifier(self, mid: str) -> Modifier | None:
        return next((m for m in self.modifiers if m.id == mid), None)

    def modifiers_doc(self, reg: Registry | None = None) -> list[dict]:
        """The preset's ``modifiers`` list: each modifier's entry, its
        params at their **bases** in `reg` (a performer riding one never
        reaches the file), else as the modifier holds them."""
        out = []
        for m in self.modifiers:
            bases = {}
            if reg is not None:
                for s in modifiers.PARAMS[m.kind]:
                    p = reg.get(modifiers.param_id(m.id, s.key))
                    if p is not None:
                        bases[s.key] = float(p.base)
            out.append(m.to_json(bases))
        return out

    def set_modifiers(self, doc, reg: Registry | None = None) -> list[str]:
        """Replace every modifier with `doc`'s (the preset's list of
        entries, or Modifier objects), and — given `reg` — their params
        ``mod.<n>.<p>`` with them (`declare_modifiers`). An entry this
        build cannot read, or a second one with an id already taken, is
        dropped; returns a note for each."""
        notes: list[str] = []
        mods: dict[str, Modifier] = {}
        for d in doc or ():
            try:
                m = d if isinstance(d, Modifier) else Modifier.from_json(d)
            except (ValueError, TypeError) as e:
                notes.append(f"dropped a modifier: {e}")
                continue
            if m.id in mods:
                notes.append(f"dropped a second {m.id}")
                continue
            mods[m.id] = m
        self.modifiers = tuple(sorted(mods.values(), key=lambda m: m.n))
        self.modifiers_serial = self.modifiers_serial + 1
        if reg is not None:
            declare_modifiers(reg, self.modifiers)
        return notes

    def add_modifier(self, kind: str, inputs: Iterable[str] = (),
                     reg: Registry | None = None, **params: float) -> Modifier:
        """A new modifier of `kind` under the next free id (`next_id`)."""
        m = Modifier(modifiers.next_id(x.id for x in self.modifiers), kind, tuple(inputs),
                     dict(params))
        bases = self.modifiers_doc(reg)            # the others keep their bases
        self.set_modifiers([*bases, m], reg)
        return self.modifier(m.id)

    def set_modifier_input(self, mid: str, k: int, source: str | None,
                           reg: Registry | None = None) -> list[str]:
        """Input `k` of modifier `mid` reads `source` ("" / None: none):
        the modifier replaced whole (`set_modifiers`, every modifier's
        params at their bases in `reg`). The callers push the undo step
        (ROUTING's input combo, the GRAPH page's cable). Returns its notes."""
        docs = self.modifiers_doc(reg)
        for d in docs:
            if d["id"] == mid:
                ins = list(d["in"])
                ins[k] = source or None
                d["in"] = ins
        return self.set_modifiers(docs, reg)

    def remove_modifier(self, mid: str, reg: Registry | None = None) -> None:
        """Take a modifier out, its params with it; a route on its lane
        stays, dormant, until it is removed or the id comes back."""
        self.set_modifiers([d for d in self.modifiers_doc(reg) if d["id"] != mid], reg)


# ---------------------------------------------------------------- router

_NO_LANES: dict = {}      # `Router.lane`'s cache before its first miss; never written


class Router:
    """The adapters' lookup and the per-frame modulation pass over one table.

    `devices` is the rig's device registry (devices.DeviceRegistry, plan 27
    B2), handed in as an argument — this module imports nothing above it —
    and asked which continuous schemes there are and in what order a page
    offers them (`schemes`); None (a bare router, the tests') offers what
    has been fed or labelled."""

    def __init__(self, reg: Registry, table: Bindings, devices=None):
        self.reg = reg
        self.table = table
        self.devices = None
        if devices is not None:
            self.use(devices)
        self.feeds: dict[str, np.ndarray | None] = {}   # ext/lfo/hand vectors, per frame
        self.labels: dict[str, list[str]] = {}          # scheme → lane names, from the adapter
        # scheme → the lanes an adapter offers as gates, [(index, label)]:
        # switch-like lanes a row's `when` can wait on. The adapter says
        # which of its lanes those are; nothing here knows about hands.
        self.gates: dict[str, list[tuple[int, str]]] = {}
        # scheme → where each lane sits idle, published like `labels`: what
        # a push row with no rest of its own uses, every frame (a hand axis
        # its configured rest value, a presence lane 0, an LFO 0.5); the
        # analyzer's lanes, and any scheme that publishes nothing, rest at 0
        self.rests: dict[str, list[float]] = {}
        # `names` (scheme → {address name: lane}) and the resolved-address
        # cache are made on first use, so a Router from before a hot reload
        # has them too
        self._codes: dict[str, int | None] = {}
        register_desk(reg, table)
        # follow_macros: each macro's base as last acted on, and the table's
        # macros_serial as last seen — a start acts on nothing (the bases
        # the project landed stand) until a macro's base moves
        self._macro_bases: dict[str, float] = {}
        self._macros_seen = table.macros_serial
        self._note_macro_bases()

    # ---- the device registry (plan 27 B2) ----

    def use(self, devices) -> None:
        """Ask `devices` (anything with `continuous_schemes()`, and
        optionally `row_schemes()` and `midi_roles()`) from now on: which
        schemes are lanes and in what order (`schemes`), which a device
        delivers as rows (the referee's `row_schemes`), which MIDI role an
        unqualified row means (`Bindings.midi_roles`). Called again
        whenever the device list changes."""
        self.devices = devices
        self.follow_devices()

    def follow_devices(self) -> None:
        """Re-read the registry's row schemes and MIDI roles into the table
        (the registry's listener calls it when the list changes)."""
        devs = self.__dict__.get("devices")
        if devs is None:
            return
        rows = getattr(devs, "row_schemes", None)
        if rows is not None:
            self.table.row_schemes = tuple(dict.fromkeys((*ROW_SCHEMES, *rows())))
        roles = getattr(devs, "midi_roles", None)
        if roles is not None:
            self.table.midi_roles = tuple(roles())
        prim = getattr(devs, "primaries", None)
        if prim is not None:
            self.table.primaries = dict(prim())
            self.__dict__.pop("_lanes", None)     # an ``axis@pad`` address may mean another key

    def schemes(self) -> tuple[str, ...]:
        """The continuous schemes a route can read, in the order a page
        offers them: the registry's (`continuous_schemes`: the analyzer's
        `lane` and the LFOs' `lfo` first, then each listed device's feeds
        in list order), then any other scheme that has been fed or
        labelled this run. With no registry, `BUILTIN_LANES` (the
        analyzer, the LFOs, the envelopes, the sequencer) and then whatever
        has been fed or labelled."""
        devs = self.__dict__.get("devices")
        out = list(devs.continuous_schemes()) if devs is not None else [*BUILTIN_LANES]
        for s in (*self.labels, *self.feeds):
            if s not in out and is_continuous(s):
                out.append(s)
        return tuple(out)

    @property
    def names(self) -> dict[str, dict[str, int]]:
        """scheme → {address name: lane index}, published like `labels`
        by an adapter whose lanes have names (the hands: ``"right.roll"``
        → its lane, decision register row 20), by plain assignment of a
        **new** dict whenever its layout changes — the resolved addresses
        are cached against that dict's identity. A row naming
        ``hand:right.roll`` reads the lane this map gives; a name the map
        lacks, or any name while no map is published, is dormant — never
        another lane. A numeric address (``hand:7``) is the lane at that
        index whatever the map says."""
        d = self.__dict__.get("_names")
        if d is None:
            d = self.__dict__["_names"] = {}
        return d

    def lane(self, source: str) -> tuple[str, int]:
        """(scheme, lane index) that a source address names — its number,
        or its name through `names` — with −1 for an address that names no
        lane (a name the adapter's map lacks, no map yet, garbage), which
        every reader treats as dormant. Cached per address until the
        scheme's map is republished, so the per-frame pass parses nothing."""
        d = self.__dict__
        hit = d.get("_lanes", _NO_LANES).get(source)
        if hit is None or self.names.get(hit[0]) is not hit[1]:
            hit = self._resolve_lane(source)
        return hit[0], hit[2]

    def _resolve_lane(self, source: str) -> tuple[str, dict | None, int]:
        """`lane`'s cache miss: (scheme, the map it was resolved against, index)."""
        cache = self.__dict__.get("_lanes")
        if cache is None or len(cache) > 4096:       # addresses typed at the page, say
            cache = self.__dict__["_lanes"] = {}
        scheme, _, addr = source.partition(":")
        base, at, role = scheme.partition(QUALIFIER)
        if at and role and getattr(self.table, "primaries", {}).get(base) == role:
            scheme = base        # qualified with the primary's own role: its lanes (B6)
        m = self.names.get(scheme)
        try:
            i = int(addr)
        except ValueError:
            i = -1 if m is None else m.get(addr, -1)
        hit = cache[source] = (scheme, m, i)
        return hit

    def address(self, scheme: str, i: int) -> str:
        """Lane `i` of `scheme` as a row should name it: by its published
        name when the scheme has one (``hand:right.roll``), else by index."""
        m = self.names.get(scheme)
        if not m:
            return f"{scheme}:{i}"
        inv = self.__dict__.setdefault("_inverse", {})    # scheme → (map, {lane: name})
        hit = inv.get(scheme)
        if hit is None or hit[0] is not m:                 # the page asks per row per frame
            hit = inv[scheme] = (m, {k: n for n, k in m.items()})
        name = hit[1].get(i)
        return f"{scheme}:{name}" if name is not None else f"{scheme}:{i}"

    def _note_macro_bases(self) -> None:
        for p in self.reg.group("macro"):
            self._macro_bases[p.id] = float(p.base)

    def sync_macros(self) -> None:
        """Mark the macros as they stand — every macro's base and the
        table's `macros_serial` — as acted on, so the next `follow_macros`
        lands nothing. An undo's restore calls it (undo.py, plan 15): it
        has just put the macros' bases and their subscribers' bases back
        itself, and a re-landing would write the subscribers over the
        values restored."""
        self._macros_seen = self.table.macros_serial
        self._note_macro_bases()

    def follow_macros(self, force: bool = False) -> list[str]:
        """The macros' base subscribers, a scene-setter step (plan 13 §2.4,
        decision register row 12b): once a frame, before the hands and the
        modulation pass, every macro whose **base** moved since the last
        call — a knob, the panel, a restore; never a performer's offset —
        sets each base subscriber's param base to `from + m · (to − from)`
        along that param's fader, without snapping to a detent. Through the
        ordinary base setter, so a performer on the target keeps its offset
        on top. Two macros on one param: the later in id order wins. A
        `set_macros` (or `force`) re-lands every macro. Returns the ids
        written."""
        if self.table.macros_serial != self._macros_seen:
            self._macros_seen, force = self.table.macros_serial, True
        written: list[str] = []
        for mid in sorted(self.table.macros, key=_macro_n):
            p = self.reg.get(mid)
            if p is None:
                continue
            m = float(p.base)
            if not force and self._macro_bases.get(mid) == m:
                continue
            self._macro_bases[mid] = m
            for s in self.table.macros[mid].subs:
                if s.base is None:
                    continue
                q = self.reg.get(s.base)
                if q is None:
                    continue
                q = self.reg.real(q)
                if q.kind in (Kind.TRIGGER, Kind.TEXT):
                    continue
                q.set(q._value_of_norm(min(1.0, max(0.0, s.at(m)))))
                written.append(q.id)
        return written

    def describe(self, b: Binding) -> str:
        """`Binding.describe` with the adapter's names in place of the
        addresses — "R height positions while R ind", "LFO 1 pushes +0.5 ×
        macro.1" — from `labels` / `gates` where a scheme has published
        them — a named address (``hand:right.roll``) through `lane`;
        otherwise the row's own "hand right.y positions while
        hand:right.pinch.index"."""
        scheme, i = self.lane(b.source)
        names = self.labels.get(scheme) or []
        name = names[i] if 0 <= i < len(names) else None
        gate = None
        if b.when is not None:
            scheme, k = self.lane(b.when)
            gate = next((lb for j, lb in self.gates.get(scheme) or [] if j == k), None)
        return b.describe(name, gate)

    # ---- discrete adapters ----

    def keys(self, keys) -> None:
        """One frame of keyboard rows; `keys` is anything with
        pressed(glfw_key) — an edge, asked once per key — and shift() /
        super() / control() for the modifier state (app.Keys; a keys
        object without one of them reads as "not held").

        Rows on one key are settled together, and a press fires only its
        own chord: a row fires when its modifiers **equal** the held
        modifiers that some row on this key names. So ``key:B`` taps and
        ``key:SHIFT+B`` triggers, neither hearing the other's press;
        ``key:SUPER+Z`` undoes and ``key:SHIFT+SUPER+Z`` redoes, and ⌘⇧Z
        fires the second alone (plan 15, fork 1). A held modifier no row
        on the key names changes nothing.
        """
        by_code: dict[int, list[Binding]] = {}
        for b in self.table.of("key"):
            code = self._code(b)
            if code is not None:
                by_code.setdefault(code, []).append(b)
        held: frozenset[str] | None = None
        for code, rows in by_code.items():
            if not keys.pressed(code):
                continue
            if held is None:
                held = frozenset(m for m in MODIFIERS
                                 if getattr(keys, m.lower(), bool)())
            used = frozenset().union(*(b.modifiers for b in rows))
            chord = held & used
            for b in rows:
                if b.modifiers == chord:
                    act(self.reg, b)

    def pad(self, pad, now: float | None = None, *, buttons: bool = True,
            role: str = "") -> None:
        """One frame of the gamepad (`pad` a gamepad.Pad): its axes fed as
        the `axis` lanes (None while no pad is on, so their routes let go),
        then its pad / hat rows — unless `buttons` is False (the frame's
        press completed a learn). A press acts as a note-on does
        (`act`); a `momentary` row lets its toggle go on the release; a
        `hold` row fires once its button has been down HOLD_S (`now`, a
        monotonic clock; a shorter press does nothing). The axes' names,
        labels and rests are the pad's to publish (`pad.publish`, plan 27
        B2: gamepad.publish), not this table's.

        `role` is the pad's qualifier (plan 27 B6): "" for the primary pad
        — the unqualified rows and the `axis` lanes, as ever — or a second
        pad's role, whose lanes are ``axis@<role>`` and whose rows are
        those qualified with it (``pad@p2:A``); each pad hears only its own."""
        axis = qualified("axis", role)
        publish = getattr(pad, "publish", None)
        if publish is not None:
            publish(self, axis) if role else publish(self)
        self.feed(axis, pad.lanes() if pad.on else None)
        # source → press time (None once fired), one dict per pad
        holds = (self.__dict__.setdefault("_pad_holds", {}) if not role else
                 self.__dict__.setdefault("_pad_holds_of", {}).setdefault(role, {}))
        if not pad.on:
            holds.clear()
            self.felt(axis, None, 0.0)       # the camera job's followers start afresh
            return
        now = time.monotonic() if now is None else now
        # each pad hears its own rows: a second pad those qualified with its
        # role; the primary the bare ones and — as a desk's `serves` — any
        # qualified with the primary's own role (``pad@pad:A``)
        own = role or getattr(self.table, "primaries", {}).get("pad", "")
        for b in self.table.of("pad", "hat"):
            code = self._code(b)
            if code is None or not b.enabled or not (
                    b.device == role or (not role and own and b.device == own)):
                continue
            hat = b.scheme == "hat"
            down = bool(pad.hat & code) if hat else pad.down(code)
            pressed = pad.hat_pressed(code) if hat else pad.pressed(code)
            released = pad.hat_released(code) if hat else pad.released(code)
            if b.op == "hold":
                key = (b.source, b.target)
                if pressed and buttons:
                    holds[key] = now
                elif not down:
                    holds.pop(key, None)
                elif holds.get(key) is not None and now - holds[key] >= HOLD_S:
                    holds[key] = None            # once per press
                    p = self.reg.get(b.target)
                    if p is not None:
                        p.fire()
                continue
            if b.op == "momentary":
                p = self.reg.get(b.target)
                if p is None:
                    continue
                if pressed and buttons:
                    p.set(True) if p.kind is Kind.TOGGLE else p.toggle()
                elif released and p.kind is Kind.TOGGLE:
                    p.set(False)
                continue
            if pressed and buttons:
                act(self.reg, b)

    def claimed(self, scheme: str) -> set[int]:
        """The lanes of `scheme` an enabled route reads — a pad axis with
        one is off its default camera job (gamepad.steer). A named address
        resolves through what the scheme's device has published."""
        return {i for b in self.table.mods() for s, i in [self.lane(b.source)]
                if s == scheme and i >= 0}

    def _code(self, b: Binding) -> int | None:
        """The key / button / hat constant a source names; None if there is none."""
        src = b.source
        if src not in self._codes:
            self._codes[src] = _resolve(b.scheme, ":".join(b.parts))
        return self._codes[src]

    # ---- continuous sources ----

    def feed(self, scheme: str, values) -> None:
        """An adapter hands in this frame's vector for `ext` / `lfo` sources
        (None: not live, its rows let go)."""
        self.feeds[scheme] = None if values is None else np.asarray(values, dtype=float)

    def gated(self, b: Binding) -> bool:
        """Is this row allowed to act this frame?

        A row with no `when` always is. One with `when` waits on that
        source address reading on (≥ 0.5) — a pinch switch, say, so the
        same hand movement can mean two different things. A gate whose
        source is not live holds the row shut rather than open: nothing
        should start moving because a camera was unplugged. Only fed
        sources gate — the analyzer's lanes are not switches and are not
        in `feeds`, so a row gated on one stays shut in both passes
        rather than working in one and not the other. A named gate
        (``hand:right.pinch.index``) is found through `lane`; one the
        adapter's map lacks holds the row shut.
        """
        if b.when is None:
            return True
        scheme, i = self.lane(b.when)
        vec = self.feeds.get(scheme)
        if vec is None or not 0 <= i < len(vec):
            return False
        u = float(vec[i])
        return not math.isnan(u) and u >= 0.5

    def rest_of(self, source: str) -> float:
        """Where `source` rests right now, from its adapter's `rests` — 0
        when the adapter published none (the analyzer's lanes, an unknown
        address). What a push row without a rest of its own is centred on."""
        scheme, i = self.lane(source)
        rests = self.rests.get(scheme) or []
        return float(rests[i]) if 0 <= i < len(rests) else 0.0

    # ---- motion (motion.py): the feel a reading travels with ----

    def source_feel(self, scheme: str) -> Motion:
        """A scheme's own feel: the pad's (`table.pad_feel`) for `axis`,
        none for every other source — the analyzer's lanes have theirs in
        the chain already, a hand has its own smoothing. One feel for every
        pad (plan 27 B6): ``axis@p2`` travels with it too."""
        return getattr(self.table, "pad_feel", OFF) if base_scheme(scheme) == "axis" else OFF

    def feel_of(self, b: Binding) -> Motion:
        """The motion row `b` runs on its reading: its own, or its source's."""
        return b.motion if b.motion is not None else self.source_feel(b.scheme)

    def felt(self, scheme: str, values, dt: float) -> list[float] | None:
        """`values` — an adapter's lanes for `scheme` — through the scheme's
        own feel, one follower per lane: what the pad's default camera job
        reads (app.py). None while that feel is off or `values` is None,
        and the followers are dropped, so the next one starts where the
        source is."""
        m = self.source_feel(scheme)
        felt = self.__dict__.setdefault("_felt", {})
        if values is None or not m.on:
            felt.pop(scheme, None)
            return None
        rests = self.rests.get(scheme) or []
        fs = felt.get(scheme)
        if fs is None or len(fs) != len(values):
            fs = felt[scheme] = [Follower(v) for v in values]
        return [f.step(v, dt, m, rests[i] if i < len(rests) else 0.0)
                for i, (f, v) in enumerate(zip(fs, values))]

    def _move(self, b: Binding, m: Motion, u: float, p: Param, depth: float,
              dt: float, movers: dict) -> float:
        """Row `b`'s reading `u` after its motion. A row's follower starts
        where it moves nothing — a push row at its rest, a position row at
        the base — so a source going live glides in from the base."""
        rest = b.rest if b.rest is not None else self.rest_of(b.source)
        key = (b.source, b.target)
        f = movers.get(key)
        if f is None:
            if b.op == "push":
                seed = rest
            else:
                seed = min(1.0, max(0.0, p.norm / depth)) if depth > 0 else u
            f = movers[key] = Follower(seed)
        return f.step(u, dt, m, rest)

    # ---- the modulation patch (plan 28 N0): the table as a graph, in order ----

    def use_bank(self, bank, clock) -> None:
        """A modulator bank (modbank.Bank: the LFOs, plan 31 B) and the
        clock it steps on: from now on its voices step inside `modulate`,
        each at its node of the patch, after the knob params it reads have
        landed (decision 7), and it feeds its scheme. Its scheme must be in
        `BANKS`. A bare router (the tests') steps no bank, and whatever
        feeds the scheme feeds it."""
        banks = self.__dict__.setdefault("banks", {})
        banks[bank.SCHEME] = bank
        self.clock = clock

    def use_lfos(self, lfos, clock) -> None:
        """The LFO bank (lfo.LFOs) and its clock: `use_bank`, and `lfos`
        named for the callers that read the bank off the router."""
        self.lfos = lfos
        self.use_bank(lfos, clock)

    def use_sequencer(self, seq, envs, clock=None) -> None:
        """The step sequencer (sequencer.Sequencer, plan 31 S) and the
        envelope bank its lanes fire (envelope.Envelopes): from now on it
        steps inside `modulate`, after every bank's `begin` — so a global
        ``lfo.trigger`` held for this frame has moved the clock's epoch and
        the grid re-aligns on the same frame — and before the plan, so the
        envelope nodes later in it see this frame's fires, stamped at each
        step's exact time. It feeds ``seq:<i>``, trigger lanes resting at 0
        (decision 10), which a route can take to any trigger param. `clock`
        None: the one `use_bank` gave."""
        self.sequencer, self.seq_envs = seq, envs
        if clock is not None:
            self.clock = clock

    def _step_sequencer(self, t: float, clock) -> None:
        """The sequencer's frame (`use_sequencer`): its fires and stop
        releases go to the envelope bank by id — one the bank lacks (a lane
        pointed at a removed extra) is a no-op — and its pulses are fed."""
        seq = self.__dict__.get("sequencer")
        if seq is None or clock is None:
            return
        envs = self.__dict__.get("seq_envs")

        # each note holds a gate-mode envelope for `seq.gate` of a step at
        # this frame's bpm and span (a one-shot ignores it), so a pattern
        # of gate envelopes plays notes rather than one held sustain
        gate = seq.gate_seconds(clock) if hasattr(seq, "gate_seconds") else None

        def fire(lane, env, at, velocity):
            if envs is not None:
                envs.fire(env, at=at, velocity=velocity, gate=gate)

        def release(lane, env, at):
            if envs is not None:
                envs.release(env, at=at)

        seq.step(t, clock, fire, release)
        seq.publish(self)                        # its lanes as trigger kinds too

    def bank(self, scheme: str):
        """The bank handed in for `scheme`, or None."""
        return self._banks().get(scheme)

    def _banks(self) -> dict:
        """The banks handed in, by scheme, in the order they came."""
        return self.__dict__.get("banks") or {}

    def _patch_key(self) -> tuple:
        """What the patch is made of — the performer rows (each by identity
        and the fields that make edges), the macros' subscribers, the
        modifiers (N1, when the table has them), each bank's ids (plan 31
        B) and the
        registry's add / remove serial — compared each frame, so the patch
        is rebuilt only when one of them changes, never per frame."""
        t = self.table
        rows = tuple((id(b), b.source, b.target, b.op, b.enabled, b.scale, b.when)
                     for b in t.bindings if b.op in MOD_OPS)
        subs = tuple((mid, id(s), s.depth, s.base) for mid, m in t.macros.items() for s in m.subs)
        mods = (getattr(t, "modifiers_serial", 0),
                *((getattr(m, "id", ""), getattr(m, "kind", ""),
                   tuple(getattr(m, "inputs", ()))) for m in _modifiers_of(t)))
        banks = tuple((scheme, tuple(b.ids())) for scheme, b in self._banks().items())
        return (id(t), rows, t.macros_serial, subs, mods, banks,
                getattr(self.reg, "serial", 0))

    def build_patch(self) -> patchmod.Patch:
        """The modulation graph of this table (patch.py's nodes and edges):
        every bank voice (when the router steps the bank: each LFO, by id)
        and modifier first, in their
        order; then per route, in table order, its source, its gate, its
        `scale`, its macros' depth subscribers and its target, with a `mod`
        edge for the row — one cable per route, ``(source, target)`` — and
        a `when` / `depth` edge for each of the rest; the macros' base
        subscribers as `base` edges; each voice's knob params (and the
        bank-wide ones, ``lfo.trigger``) and each modifier's own params, where the patch
        holds them, into their node. A switched-off row's edges are drawn
        disabled. No loop is cut here (`patch` does that)."""
        g = patchmod.Patch()
        t = self.table
        for scheme, bank in self._banks().items():
            for n in bank.ids():
                g.add(f"{scheme}:{n - 1}", scheme)
        mods = _modifiers_of(t)
        for m in mods:
            g.add(_modifier_node(m), "modifier", delay=getattr(m, "kind", "") == "delay")

        def source(addr: str) -> str:
            scheme, i = self.lane(addr)
            if scheme in BANKS and i >= 0:
                return g.add(f"{scheme}:{i}", scheme).id
            return g.add(addr, "source").id

        def param(pid: str) -> str:
            return g.add(pid, "macro" if is_macro(pid) else "param").id

        for m in mods:
            for inp in getattr(m, "inputs", ()):
                if inp:                                  # "" is an input not chosen yet
                    g.link(source(inp), _modifier_node(m), "in")
        for b in t.routes():
            cable, on = (b.source, b.target), b.enabled
            src = source(b.source)
            gate = source(b.when) if b.when is not None else None
            scale = param(b.scale) if b.scale is not None else None
            subs = [param(mid) for mid, _ in t.depth_subs(b)]
            dst = param(b.target)
            g.link(src, dst, "mod", cable, on)
            if gate is not None:
                g.link(gate, dst, "when", cable, on)
            if scale is not None:
                g.link(scale, dst, "depth", cable, on)
            for mid in subs:
                g.link(mid, dst, "depth", cable, on)
        for mid in sorted(t.macros, key=_macro_n):
            for s in t.macros[mid].subs:
                if s.base is not None:
                    g.link(param(mid), param(s.base), "base")
        voices = [(n.id, n.kind) for n in g.nodes.values() if n.kind in BANKS]
        for nid, scheme in voices:
            cls = BANKS[scheme]
            n = int(nid.split(":")[1]) + 1
            for k in cls.KNOBS:
                if f"{scheme}.{n}.{k}" in g.nodes:
                    g.link(f"{scheme}.{n}.{k}", nid, k)
            for pid, port in cls.SHARED.items():
                if pid in g.nodes:
                    g.link(pid, nid, port)
        for m in mods:
            prefix = f"{getattr(m, 'id', '')}."
            for nid, node in list(g.nodes.items()):
                if node.kind == "param" and nid.startswith(prefix):
                    g.link(nid, _modifier_node(m), nid[len(prefix):])
        return g

    @property
    def patch(self) -> patchmod.Patch:
        """The table's modulation patch as `modulate` runs it: `build_patch`,
        with every loop that passes through no delay modifier broken at its
        last cable in table order — that cable's edges disabled and a note
        in `patch_notes` (ROUTING's head shows it), the row itself left in
        the table and the file as it is. Cached: rebuilt when `_patch_key`
        moves (the table, the banks' ids, the registry's params), with the
        evaluation plan `modulate` walks."""
        d = self.__dict__
        key = self._patch_key()
        if d.get("_patch_seen") != key:
            self._rebuild_patch(key)
        return d["_patch"]

    @property
    def patch_notes(self) -> list[str]:
        """One note per cable the patch keeps off to break a loop."""
        self.patch                                   # noqa: B018 — current
        return self.__dict__["_patch_notes"]

    @property
    def patch_cut(self) -> set[tuple[str, str]]:
        """The cables, ``(source, target)``, kept off to break a loop."""
        self.patch                                   # noqa: B018 — current
        return self.__dict__["_patch_cut"]

    def _rebuild_patch(self, key: tuple) -> None:
        g = self.build_patch()
        t = self.table
        rank: dict[tuple[str, str], int] = {}
        for k, b in enumerate(t.bindings):
            if b.op in MOD_OPS:
                rank[(b.source, b.target)] = k
        mods = _modifiers_of(t)
        mod_ids = {_modifier_node(m): getattr(m, "id", "") for m in mods}
        mod_rank = {node: modifiers.number(mid) or 0 for node, mid in mod_ids.items()}
        cut: set[tuple[str, str]] = set()
        cut_in: set[tuple[str, str]] = set()     # (input address, modifier node) kept off
        notes: list[str] = []
        while True:
            loops = patchmod.cycles(g)
            if not loops:
                break
            loop = loops[0]
            said = " → ".join([*loop, loop[0]])
            hops = set(zip(loop, [*loop[1:], loop[0]], strict=True))
            on_loop = [e for e in patchmod.ordering(g) if (e.src, e.dst) in hops]
            cables = {e.cable for e in on_loop if e.cable is not None}
            if cables:
                # the loop's last cable in table order
                off = max(cables, key=lambda c: rank.get(c, -1))
                g.edges = [replace(e, enabled=False) if e.cable == off else e for e in g.edges]
                cut.add(off)
                notes.append(f"loop: {said} needs a delay — "
                             f"{off[0]} → {off[1]} is off until it has one")
                continue
            # a loop of modifiers alone (`in` edges carry no cable): the last
            # modifier's input on it, in modifier id order, is kept off — that
            # modifier is dormant until the loop has a delay
            ins = [e for e in on_loop if e.port == "in" and e.dst in mod_rank]
            last = max(ins, key=lambda e: mod_rank[e.dst]) if ins else on_loop[-1]
            g.edges = [replace(e, enabled=False) if e is last else e for e in g.edges]
            cut_in.add((last.src, last.dst))
            who = mod_ids.get(last.dst, last.dst)
            notes.append(f"loop: {said} needs a delay — {who}'s input {last.src} "
                         f"is off until it has one")
        # the evaluation plan: per node in order, what `modulate` does there
        banks = self._banks()
        reads = {e.src for e in patchmod.ordering(g)}
        by_target: dict[str, list] = {}
        for b in t.mods():
            if (b.source, b.target) not in cut:
                by_target.setdefault(b.target, []).append((b, tuple(t.depth_subs(b))))
        # a delay closing a loop runs before its input (`patch.ordering`):
        # it emits that input's lane as it stands — last frame's value
        live = [e for e in g.edges if e.enabled and e.port == "in"]
        ordered = {id(e) for e in patchmod.ordering(g)}
        early = {e.dst for e in live if id(e) not in ordered}
        dormant = {node for _, node in cut_in}
        plan: list[tuple] = []
        for node in patchmod.order(g):
            if node.kind in banks:
                i = int(node.id.split(":")[1])
                if i + 1 in banks[node.kind]:          # a gap, or past the last: no voice
                    plan.append(("bank", node.kind, i))
            elif node.kind == "modifier" and node.id in mod_ids:
                plan.append(("modifier", mod_ids[node.id], node.id in early,
                             node.id in dormant))
            elif node.kind in ("param", "macro"):
                rows = by_target.get(node.id, [])
                land = node.id in reads
                if rows or land:
                    plan.append(("param", node.id, rows, land))
        d = self.__dict__
        d["_patch"], d["_plan"], d["_patch_seen"] = g, plan, key
        d["_patch_notes"], d["_patch_cut"] = notes, cut | cut_in

    # ---- the modifiers (plan 28 N1): their output lanes, ``mod:<n>`` ----

    def _reading(self, address: str, lanes) -> float | None:
        """A source address's reading this frame, as a modifier reads its
        input: the analyzer's lane (`lanes`, already normalised) for
        ``lane:``, else the scheme's fed vector; None while it is not
        live — not fed, no such lane, a name the map lacks, NaN."""
        if not address:
            return None
        scheme, i = self.lane(address)
        vec = lanes if scheme == "lane" else self.feeds.get(scheme)
        if vec is None or not 0 <= i < len(vec):
            return None
        u = float(vec[i])
        return None if math.isnan(u) else u

    def _step_modifier(self, mid: str, dt: float, lanes=None, *, early: bool = False,
                       cut: bool = False) -> float | None:
        """Step one modifier (`modifiers.step`) on its inputs' readings and
        write its output into its ``mod`` lane — the vector
        `_publish_modifiers` publishes. One call per node: N0's patch
        evaluation calls it in dependency order. An input that is not live
        leaves the node dormant — its lane NaN, so a route on it lets go
        like a route on that source would — and its memory starts afresh
        when the input comes back. Returns the output (None: dormant).

        `early` (plan 28 N0): a delay that closes a loop, run before its
        input — it emits that input's lane as it stands, last frame's
        value, so the loop is exactly one frame late. `cut`: a modifier
        whose input `patch` keeps off to break a loop with no delay: dormant."""
        m = self.table.modifier(mid)
        vec = self.feeds.get(modifiers.SCHEME)
        if m is None or vec is None or not 0 <= m.n < len(vec):
            return None
        states = self.__dict__.setdefault("_mod_states", {})
        reads = [self._reading(a, lanes) for a in m.inputs]
        if early and m.kind == "delay" and not cut:
            # a delay closing a loop runs before its input (plan 28 N0): its
            # input's lane as it stands is last frame's value — the loop's
            # one frame; not stepped yet (the loop's first frame), its rest
            out = reads[0] if reads[0] is not None else modifiers.REST
            vec[m.n] = out
            return float(out)
        if cut or any(u is None for u in reads):
            states.pop(mid, None)
            vec[m.n] = math.nan
            return None
        hit = states.get(mid)
        if hit is None or hit[0] != m.kind:
            hit = states[mid] = (m.kind, ModState())
        out = modifiers.step(m, tuple(reads), hit[1], dt)
        if not math.isfinite(out):
            # a non-finite output (an input that read ±inf): not live, and
            # its memory is dropped, so the next finite reading starts afresh
            states.pop(mid, None)
            vec[m.n] = math.nan
            return None
        vec[m.n] = out
        return float(out)

    def _publish_modifiers(self) -> None:
        """The ``mod`` scheme's labels, rests, gates and signal kinds, as
        an adapter publishes its lanes' — once the table's modifiers
        change. No modifiers: the scheme is not offered at all."""
        mods = self.table.modifiers
        if not mods:
            for d in (self.feeds, self.labels, self.rests, self.gates, self.lane_kinds):
                d.pop(modifiers.SCHEME, None)
            return
        n = max(m.n for m in mods) + 1
        labels, kinds = [""] * n, [modifiers.VALUE] * n
        for m in mods:
            labels[m.n] = f"{m.n} {m.kind}"
            kinds[m.n] = m.out
        sc = modifiers.SCHEME
        self.labels[sc], self.rests[sc] = labels, [modifiers.REST] * n
        self.lane_kinds[sc] = kinds
        # a threshold's fire is a switch a row's `when` can wait on
        self.gates[sc] = [(m.n, f"mod {m.n} {m.kind}") for m in mods
                          if m.out == modifiers.TRIGGER]
        old = self.feeds.get(sc)
        vec = np.full(n, math.nan)
        if old is not None:                  # last frame's outputs stand until stepped
            vec[:min(n, len(old))] = old[:n]
        self.feed(sc, vec)                   # written in place per node after this

    @property
    def lane_kinds(self) -> dict[str, list[str]]:
        """scheme → each lane's signal kind, "value" or "trigger" (decision
        10), published like `labels` by a source that has triggers: today
        the ``mod`` lanes, where a threshold's output is a trigger. A
        trigger lane is still read as a value (1 while it fires, else 0)."""
        d = self.__dict__.get("_lane_kinds")
        if d is None:
            d = self.__dict__["_lane_kinds"] = {}
        return d

    def _sync_modifiers(self) -> None:
        """Once the table's modifiers change (`modifiers_serial`, and on the
        first pass): their lanes republished (`_publish_modifiers`) and a
        removed modifier's memory dropped. The pass then steps each one at
        its node, in dependency order (plan 28 N0) — `_step_modifier`."""
        serial = getattr(self.table, "modifiers_serial", 0)
        if self.__dict__.get("_mods_seen") == serial and (
                not self.table.modifiers or modifiers.SCHEME in self.feeds):
            return
        self.__dict__["_mods_seen"] = serial
        self._publish_modifiers()
        live = {m.id for m in self.table.modifiers}
        states = self.__dict__.setdefault("_mod_states", {})
        for mid in [k for k in states if k not in live]:
            del states[mid]

    def modulate(self, analyzer=None, dt: float | None = None,
                 now: float | None = None) -> None:
        """The frame's modulation pass — the one path a continuous source
        has to a param — over the patch **in dependency order** (plan 28
        N0, decision 7). Every bank begins first (`use_bank`: a held global
        trigger lands), then the sequencer steps (`use_sequencer`: its
        fires queued on the envelopes, its pulses fed); at a voice's node — an LFO's — it steps (`now`
        the frame's time, the clock's when None) and its lane is fed; at a
        modifier's, `_step_modifier`; at a param's, every enabled performer
        row on it whose source is live calls modulate on it — depth =
        value × scale × Π depth subscribers, the follower, push /
        position — and a param that a later node reads (a `scale`, a macro
        behind a depth subscriber, an LFO's knob) is landed **now**
        (`Param.apply` under the frame's mark), so its reader sees this
        frame's value. Every other param lands in `reg.apply()` as before.
        `analyzer` is the live one, or None while no audio source runs
        (its lanes are then not a source). `dt` is the frame's, for the
        rows' motion (`feel_of`); None, a 60 Hz frame. A row that does not
        act this frame — its source not live, its gate shut — loses its
        follower, and starts afresh. A cable `patch` keeps off to break a
        loop does not run."""
        dt = 1 / 60 if dt is None else dt
        self._sync_modifiers()                   # plan 28 N1: the ``mod:<n>`` lanes
        self.patch                                   # noqa: B018 — the cached plan, current
        plan = self.__dict__["_plan"]
        begin = getattr(self.reg, "begin_frame", None)
        mark = begin() if begin is not None else None
        banks = self._banks()
        fed: dict[str, np.ndarray] = {}
        clock = self.__dict__.get("clock")
        t = now if now is not None else getattr(clock, "t", 0.0)
        for scheme, bank in banks.items():
            bank.begin(t, clock)
            bank.publish(self)                   # names, rests; each lane as its voice steps
            fed[scheme] = self.feeds[scheme]
        # plan 31 W1: after every `begin` (a held global trigger has moved
        # the epoch), before the plan (the envelopes step at their nodes)
        self._step_sequencer(t, clock)
        movers = self.__dict__.setdefault("_movers", {})
        moved: set = set()
        lanes = None if analyzer is None else analyzer.lanes / CEIL
        # each row's lane — a number, or a name through `names` — from the
        # cache `lane` keeps; a miss or a republished map resolves again
        names = self.names
        cache = self.__dict__.get("_lanes", _NO_LANES)
        for step in plan:
            kind = step[0]
            if kind == "bank":
                lane = fed.get(step[1])
                if lane is not None:
                    i = step[2]
                    lane[i] = banks[step[1]].step_one(i, dt, t, clock)
                continue
            if kind == "modifier":
                self._step_modifier(step[1], dt, lanes, early=step[2], cut=step[3])
                continue
            for b, subs in step[2]:
                hit = cache.get(b.source)
                if hit is None or names.get(hit[0]) is not hit[1]:
                    hit = self._resolve_lane(b.source)
                    cache = self.__dict__["_lanes"]
                scheme, _, i = hit
                vec = lanes if scheme == "lane" else self.feeds.get(scheme)
                if vec is None or not 0 <= i < len(vec):
                    continue
                u = float(vec[i])
                if math.isnan(u):    # this lane's source is out of view
                    continue
                if not self.gated(b):
                    continue         # gate open: apply() writes the base back
                p = self.reg.get(b.target)
                if p is None:
                    continue
                depth = b.value
                if b.scale is not None:
                    sp = self.reg.get(b.scale)
                    if sp is None:
                        continue
                    depth *= float(sp.value)
                # the macros' depth subscribers on this route: × from + m·(to − from),
                # m the macro's effective value — this frame's: its node ran first
                dormant = False
                for mid, s in subs:
                    mp = self.reg.get(mid)
                    if mp is None:
                        dormant = True
                        break
                    depth *= s.at(float(mp.value))
                if dormant:
                    continue
                m = self.feel_of(b)
                if m.on:
                    u = self._move(b, m, u, p, depth, dt, movers)
                    moved.add((b.source, b.target))
                if b.op == "push":
                    # centred where the source rests — the row's own number, or
                    # the source's as published this frame: idle adds nothing
                    rest = b.rest if b.rest is not None else self.rest_of(b.source)
                    x = depth * (u - rest)
                else:
                    # position: the source is the fader — the offset that lands
                    # it (p.norm is the base while modulated, the object before)
                    if p.kind is Kind.TEXT or not p.modulatable:
                        continue
                    x = min(1.0, max(0.0, depth * u)) - p.norm
                p.modulate(x)
            if step[3]:              # something later in the pass reads it: land it now
                q = self.reg.get(step[1])
                if q is not None and q._base is not None:
                    q.apply(mark)
        for key in [k for k in movers if k not in moved]:
            del movers[key]


def _modifiers_of(table) -> list:
    """The table's modifiers (plan 28 N1's `Bindings.modifiers`: a list, or
    a dict by id) — none on a table from before N1."""
    mods = getattr(table, "modifiers", None) or ()
    return list(mods.values() if isinstance(mods, dict) else mods)


def _modifier_node(m) -> str:
    """A modifier's node: its output lane's address, ``mod.3`` → ``mod:3``
    — what a route's source names."""
    mid = str(getattr(m, "id", ""))
    head, dot, n = mid.partition(".")
    return f"{head}:{n}" if dot else f"mod:{mid}"


def _resolve(scheme: str, name: str) -> int | None:
    """key:NAME → glfw.KEY_NAME; pad:NAME → gamepad.NAME; hat:DIR → gamepad.HAT_DIR.
    Imported here so the table itself never needs a window system."""
    try:
        if scheme == "key":
            import glfw
            return getattr(glfw, f"KEY_{name.rsplit('+', 1)[-1]}")   # SHIFT+B → KEY_B
        from . import gamepad
        return getattr(gamepad, f"HAT_{name}" if scheme == "hat" else name)
    except (ImportError, AttributeError):
        return None


# --------------------------------------------------------------- factory file

def write_factory(path: Path = FACTORY_FILE) -> Path:
    """Export the factory session table — the file a fresh `bindings.json`
    would be (`python -m hyperspace.routing`); test_routing guards it
    against drift. Outside the library tree: it is no group's preset."""
    path.write_text(Bindings.factory().dumps())
    return path


if __name__ == "__main__":
    print(write_factory())


