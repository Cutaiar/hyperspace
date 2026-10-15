"""Rig configuration — an optional config.toml in the library home.

The home is ``$HYPERSPACE_HOME`` (default ``~/Hyperspace``, library.py);
a config.toml still sitting in the working directory is copied there on
the first run. Everything has a default, so the file is only for what
differs on this machine. Adapters are enabled here, not in code
(BLUEPRINT §3.6). Three are on by default: the MIDI adapter (it is the one
that also holds Learn) and the gamepad cost nothing when the device is
absent, and the dream worker is part of the show (decision 23 (a),
2026-09-29: torch is a main dependency). The bridge and the hands tracker
are off until asked for, and their modules are never imported until then;
dream.py, too, is imported only when its gate is open.

    [midi]
    enabled = true          # false leaves the adapter out entirely (and hand Learn with it)
    port = "APC40"          # substring of the port name; default from the profile
    profile = "apc40"       # device profile (hyperspace/<profile>.py)
    map = "midi_map.json"   # a pre-plan-09 MIDI map, relative to this file's
                            # folder (the library home when loaded from there);
                            # read once, only when bindings.json does
                            # not exist yet (Bindings.load). Learn writes
                            # <home>/bindings.json (routing.py), not this file

    [output]                # where the render window goes and how it looks
                            # (overlay.py; app.py seeds the output.* params)
    overlay = false         # overlay mode exists at all (decision 21 (a)): false,
                            # the render window is always opaque — no transparent
                            # framebuffer, and T / MASTER select / the panel cannot
                            # float it see-through; true for a laptop demo
    monitor = -1            # which screen the RENDER window opens on, and the one
                            # fullscreen covers: a screen index, or -1 = where it
                            # was last time (else the primary screen)
    control_monitor = -1    # which screen the CONTROL window opens on: an index,
                            # or -1 = where it was last time (else the primary).
                            # "Last time" is <home>/windows.json (placement.py),
                            # written on quit and on restart; delete it to forget.
                            # An index with no such screen is treated as -1, with
                            # a note
    fullscreen = false      # launch fullscreen on that screen
    render = "1080p"        # the render cap: the most pixels a frame is drawn at,
                            # every output showing it scaled — "full" (output 1's
                            # whole framebuffer), "1440p", "1080p", "720p". A 2×
                            # HiDPI screen that looks 1920×1080 is 3840×2160
                            # under "full". output.render on the OUTPUT page
    flip_x = false          # mirror the picture left-right / top-bottom as its
    flip_y = false          # last step, for a Pepper's Ghost glass (plan 23 WP1);
                            # one output. With [[output.screens]], each entry's
                            # own flip_x / flip_y. output.N.flip_x / .flip_y on
                            # the OUTPUT page; never saved in a preset or show
    keep_awake = true       # while the app runs, the Mac does not idle into the
                            # screensaver, display sleep or system sleep (macOS
                            # `caffeinate -d -i`, app.Awake); false lets it
    on_start = false        # launch straight into overlay mode (needs overlay = true)
    passthrough = true      # clicks go to the window underneath (G / pan toggles)
    bg = 0.0                # ground darkness in overlay: 0 see-through, 1 black
    alpha = 1.0             # whole-window opacity
                            # (bg and alpha: a value that is not a number is
                            # the default, with a note — never a dead launch)
                            # [overlay] is the pre-split name of this section:
                            # still read, merged under [output] (which wins),
                            # and noted once on stderr so the file gets renamed

    [[output.screens]]      # optional: a list of render outputs (plan 21), one
                            # window each, MAX_OUTPUTS (4) at most. No list: one
                            # output from monitor / fullscreen above, exactly as
                            # before. With a list, the list wins: [output]
                            # monitor / fullscreen are ignored (one note) and
                            # output 1's entry says; overlay, on_start,
                            # passthrough, bg and alpha stay above and are
                            # output 1's alone (every later output is opaque)
    name = "glass"          # optional: the label on the OUTPUT page and in notes
    monitor = 1             # a screen index, or -1 = a plain window where it was
                            # last. Output 1 always opens (an index no screen has
                            # is -1, with a note). A LATER output whose index no
                            # screen has is NOT opened, with a note (fork F9); a
                            # screen plugged in after the launch is not picked up
                            # until the next launch
    fullscreen = true       # a borderless cover of that screen at its current
                            # mode, never a mode switch (fork F10: the config
                            # says; output.monitor / output.fullscreen on the
                            # OUTPUT page are output 1's only)
    scene = true            # optional launch values of this output's switches:
    hands = true            #   the scene, the ghost hands, and
    through = false         #   "hands through effects" (plan 21 WP2)
    dim = 1.0               #   its own dim, times the master's; under 0.1 is 0.1,
                            #   with a note — the config cannot launch an output black
    flip_x = false          #   mirror this output left-right / top-bottom, its last
    flip_y = false          #   step — for a Pepper's Ghost glass (plan 23 WP1)
                            # Outputs are numbered by their place in the list,
                            # opened or not. Output 1 sets the frame's size and
                            # paces the loop (its swap waits for its screen, the
                            # others' do not — fork F6); a later output of
                            # another shape shows the whole frame, letterboxed

A file that will not parse is not fatal: the defaults stand and
``cfg["error"]`` carries the message; ``cfg["notes"]`` carries requests
like the rename above. The SYSTEM page shows both.

    [[devices]]             # the rig's devices (plan 27, devices.py): one table per
                            # device, polled in this order. No list: the four tables
                            # below ([midi], [gamepad], [hands], [bridge]) are read
                            # as before and become the equivalent entries at load,
                            # with one note per table that asks for the rename.
                            # With a list, the list says and those tables are
                            # ignored (one note each)
    role = "apc40"          # the name rows and the SYSTEM page use; unique; no ":"
    kind = "midi"           # "midi", "gamepad", "hands", "bridge", "midi-out",
                            # "osc", "cloud"; an unknown kind is an
                            # error line on the SYSTEM page, never a dead launch
    enabled = true          # false lists it as `off`: nothing opened, nothing imported
                            # …then the kind's own keys: [midi]'s port / profile /
                            # map, [gamepad]'s usb, [hands]'s whole table,
                            # [bridge]'s out / in / encoding / channel / cc / rate /
                            # send / in_lanes — each with the defaults below.
                            # Today's rig, as a list:
                            #   [[devices]]  role = "pad"     kind = "gamepad"
                            #   [[devices]]  role = "apc40"   kind = "midi"
                            #   [[devices]]  role = "leap"    kind = "hands"   enabled = false
                            #   [[devices]]  role = "bridge"  kind = "bridge"  enabled = false
                            # Several MIDI desks (plan 27 B2): one entry each, its
                            # own `profile` — "apc40", or "generic" (plain CC /
                            # note / pitch, no feedback; it needs a `port`). The
                            # first MIDI entry whose profile is bindings.json's
                            # ("apc40"), else the first listed, owns the
                            # unqualified rows (cc:0:7, as every row before
                            # plan 27); another's carry its role
                            # (cc@launch:0:7), which Learn desk writes for you:
                            #   [[devices]]  role = "launch"  kind = "midi"
                            #                profile = "generic"  port = "Launch Control"
                            # SHIFT (desk.shift) is the first MIDI role's latch;
                            # bindings.json's "profile" never overrides an entry's.
                            # The app watches this file: an edit to the list lands
                            # without a relaunch (a bad edit is a note; the old list
                            # stands). [dream] is a worker, not a device: it stays a table
                            # Sinks (plan 27 B3) send values out: the bridge's out
                            # half, and a "midi-out" entry — a MIDI port of its
                            # own, carrying a hands device's DAW messages and any
                            # sink rows on its role:
                            #   [[devices]]  role = "hands-daw"  kind = "midi-out"
                            #                port = "Hyperspace Hands"  carries = "leap"
                            #   (`port`: an existing port by substring, else a
                            #   virtual one unless virtual = false; `carries`: the
                            #   hands role whose DAW MIDI it sends; encoding /
                            #   channel / cc / rate: its sink rows' wire, as the
                            #   bridge's.) [hands] out — on the old table or on a
                            #   hands entry — becomes this entry at load (one note
                            #   when the file wrote it), unless the list has a
                            #   midi-out carrying that role already. What a sink
                            #   sends is the session's sink rows in bindings.json
                            #   ("param:view.bright" or "lane:3" → "bridge:3"):
                            #   ROUTING's sinks, or right-click → Learn sink ▸.
                            #   [bridge] send becomes those rows the first launch
                            #   the bridge is on with none (one note); then the
                            #   rows say

    [gamepad]               # the Xbox pad polled through GLFW (gamepad.py)
    enabled = true          # false never polls for one
    usb = true              # no pad in GLFW: look for a wired Xbox 360 pad over libusb

    [bridge]                # lanes out / external lanes in over MIDI (bridge.py)
    enabled = false         # true opens the bridge; off, it is never imported
    out = "IAC"             # substring of the virtual port the lanes go out on ("" = none)
    in = ""                 # substring of the port external lanes come in on ("" = none)
    encoding = "pitch"      # "pitch": lane i → pitch bend on channel+i (16 lanes)
                            # "cc14": lane i → CC cc+i (MSB) / cc+i+32 (LSB) on channel
    channel = 0             # 0-based: the first lane's channel (pitch) / the pair channel
    cc = 16                 # cc14: the first lane's MSB controller, 0–31 (32−cc lanes)
    rate = 100              # messages a second per lane at most (0 = every frame)
    send = ["lane:*"]       # what goes out, in lane order: "lane:*", "lane:3", "param:<id>"
                            # — read once, into bindings.json's sink rows (plan 27 B3)
    in_lanes = 16           # size of the `ext` vector the inbound lanes fill

    [dream]                 # the look-back's Deep Dream worker (dream.py, torch)
    enabled = true          # on by default; false keeps torch from ever being imported
    device = "auto"         # "auto" (MPS when there, else CPU), "mps", "cpu"
    precision = "fp32"      # or "fp16": ~10 % faster on VGG, more p99 outliers
    weights_dir = ""        # pretrained weights; "" = <library home>/weights

    [hands]                 # Ultraleap hands (hands/, the `leap` bindings) — the rig;
                            # the performance setup is the HANDS page / `hands` presets.
                            # The defaults are hands/core.py's DEFAULTS, the one table
    enabled = false         # true opens the tracker; off, `leap` is never imported
    mode = "desktop"        # camera looks up from below; "screentop" from above, "hmd"
    dofs = ["x", "y", "z", "roll", "pitch", "yaw"]   # per hand, in axis order; also
                            # grab, pinch, grab_angle, pinch_mm
    out = "Hyperspace Hands"   # MIDI out for a DAW: port substring, else a new
                               # virtual port of that name ("" = none)
    channel = 16            # 1-based: the channel every axis starts on
    cc = 102                # starting CCs: left hand cc…cc+n−1, right cc+n…cc+2n−1
    presence = true         # note on/off to the DAW as a hand enters / leaves
    note = 120              # left hand's presence note, right is note+1
    min_confidence = 0.1
    calibration = "hands.json"   # the box's ranges, relative to the library home
    tape = ""               # a hand tape (tools/hands_tape.py record) to play instead
                            # of the camera, relative to this file; "" = the camera

    [library]               # where the presets live (plan 25)
    path = ""               # "" = the home above, as always. Otherwise a folder —
                            # typically a cloud-synced one (Dropbox, iCloud Drive,
                            # Syncthing…) shared with whoever you trade presets with.
                            # It holds the library: presets/, projects/, the module
                            # groups (fx/, dream/, band/…), hidden.json and trash/.
                            # Machine files stay in the home: this config.toml,
                            # bindings.json, hands.json, windows.json, last_show,
                            # logs and weights/. `~` is expanded; a relative path is
                            # relative to this file's folder. If the folder is
                            # missing at launch it is never created: a warning says
                            # so, the SYSTEM page shows it in red, every save is
                            # refused and only factory presets list — fix the folder
                            # (or the path) and restart. tools/move_library.py copies
                            # an existing library into it.
"""

from __future__ import annotations

import copy
import math
import sys
import tomllib
from pathlib import Path

from . import library, placement

FILE = Path("config.toml")
LEGACY_OUTPUT = "overlay"   # the section [output] was called before the split

DEFAULTS: dict = {
    # midi.map: the legacy midi_map.json, merged once when bindings.json is missing
    "midi": {"enabled": True, "port": None, "profile": "apc40", "map": "midi_map.json"},
    # overlay.py: the render window's placement and look; ground 0 = see-through.
    # overlay: off, the window is opaque and overlay cannot switch on
    # (decision 21 (a), plan 14 WP2). monitor / control_monitor: the screen
    # each window opens on, −1 = where it was last time (placement.py)
    "output": {"overlay": False, "monitor": -1, "control_monitor": -1, "fullscreen": False,
               "on_start": False, "passthrough": True, "bg": 0.0, "alpha": 1.0,
               "keep_awake": True, "render": "1080p",
               "flip_x": False, "flip_y": False},
    # gamepad.py: the Xbox pad — on by default, inert when absent
    "gamepad": {"enabled": True, "usb": True},
    # bridge.py: the analyzer's lanes out to a DAW, external lanes in — off by default
    "bridge": {"enabled": False, "out": "IAC", "in": "", "encoding": "pitch", "channel": 0,
               "cc": 16, "rate": 100, "send": ["lane:*"], "in_lanes": 16},
    # dream.py: the temporal Deep Dream behind the look-back — on by default
    # (decision 23 (a)); a worker that will not start is said on the panel
    "dream": {"enabled": True, "device": "auto", "precision": "fp32", "weights_dir": ""},
    # hands/: Ultraleap hands as MIDI CCs and hand lanes — off by default.
    # Its section is not here: load() fills it from hands/core.py's DEFAULTS,
    # the one table (every key documented there), read at call time so this
    # module imports no adapter
    # library.py: [library] path, the library root (plan 25); "" = the home.
    # load() resolves it to an absolute path
    "library": {"path": ""},
}


# one [[output.screens]] entry's keys and their defaults (plan 21 WP3); the
# switches are outputs.Switches' launch values
SCREEN: dict = {"name": "", "monitor": -1, "fullscreen": False,
                "scene": True, "hands": True, "through": False, "dim": 1.0,
                "flip_x": False, "flip_y": False}
DIM_FLOOR = 0.1          # the config cannot launch an output black (plan 21 fork F4)

# `[[devices]]` (plan 27 B1): the old per-adapter tables, in today's poll
# order, each with the kind and the role its entry gets (None: the MIDI
# profile's name); the keys an entry of that kind carries beyond role /
# kind / enabled are the table's own
DEVICE_TABLES = (("gamepad", "gamepad", "pad"), ("midi", "midi", None),
                 ("hands", "hands", "leap"), ("bridge", "bridge", "bridge"))
DEVICE_KEYS = ("role", "kind", "enabled")
# a `midi-out` entry's own keys and their defaults (plan 27 B3): the port
# (a substring of an existing one, else a virtual port of that name unless
# `virtual` is false), the hands role whose DAW messages it carries, and
# its sink rows' wire — the bridge's encoding / channel / cc / rate
MIDI_OUT: dict = {"port": "", "virtual": True, "carries": "", "encoding": "pitch",
                  "channel": 0, "cc": 16, "rate": 100}
DAW_ROLE = "hands-daw"     # the entry `[hands] out` becomes


def _note(cfg: dict, note: str) -> None:
    cfg.setdefault("notes", []).append(note)
    print(note, file=sys.stderr)


def number(v) -> float | None:
    """A finite number from the file, or None (a bool is not one)."""
    if isinstance(v, bool) or not isinstance(v, int | float):
        return None
    try:
        f = float(v)
    except OverflowError:
        return None
    return f if math.isfinite(f) else None


def _screen(n: int, e: dict, cfg: dict) -> dict:
    """One `[[output.screens]]` entry, every key checked: a value of the
    wrong kind is the default, with a note — never a dead launch."""
    out = dict(SCREEN)
    where = f"config: [[output.screens]] output {n}:"
    for key in e:
        if key not in SCREEN:
            _note(cfg, f"{where} unknown key {key!r} — ignored")
    name = e.get("name", "")
    out["name"] = name if isinstance(name, str) else str(name)
    if "monitor" in e:
        out["monitor"], bad = placement.read("monitor", e["monitor"])
        if bad:
            _note(cfg, f"{where} monitor = {e['monitor']!r} is not a screen index — "
                       "using the last position")
    for key in ("fullscreen", "scene", "hands", "through", "flip_x", "flip_y"):
        if key in e:
            if isinstance(e[key], bool):
                out[key] = e[key]
            else:
                _note(cfg, f"{where} {key} = {e[key]!r} is not true or false — "
                           f"{str(SCREEN[key]).lower()}")
    if "dim" in e:
        d = number(e["dim"])
        if d is None:
            _note(cfg, f"{where} dim = {e['dim']!r} is not a number — 1.0")
        elif d < DIM_FLOOR:
            out["dim"] = DIM_FLOOR
            _note(cfg, f"{where} dim = {d:g} would launch it black — {DIM_FLOOR:g}")
        else:
            out["dim"] = min(d, 1.0)
    return out


def _screens(cfg: dict, file_output) -> None:
    """`[[output.screens]]` (plan 21 WP3), read in place: a list of checked
    entries under ``cfg["output"]["screens"]``, and output 1's monitor and
    fullscreen put in the scalar keys, so everything that reads those for
    the first window reads the list's first entry. No list (or an empty
    one, or not a list — said): no ``screens`` key, and one output exactly
    as before."""
    oc = cfg["output"]
    if "screens" not in oc:
        return
    from .outputs import MAX_OUTPUTS  # moderngl: only when there is a list

    raw = oc.pop("screens")
    if not isinstance(raw, list):
        _note(cfg, f"config: [output] screens = {raw!r} is not a list of [[output.screens]] "
                   "tables — one output, as [output] says")
        return
    entries = []
    for i, e in enumerate(raw):
        if isinstance(e, dict):
            entries.append(e)
        else:
            _note(cfg, f"config: [[output.screens]] entry {i + 1} is not a table ({e!r}) — "
                       "dropped")
    if len(entries) > MAX_OUTPUTS:
        _note(cfg, f"config: [[output.screens]] lists {len(entries)} outputs, {MAX_OUTPUTS} at "
                   f"most — output {MAX_OUTPUTS + 1} on dropped")
        entries = entries[:MAX_OUTPUTS]
    if not entries:
        _note(cfg, "config: [[output.screens]] lists no output — one output, as [output] says")
        return
    out = [_screen(k + 1, e, cfg) for k, e in enumerate(entries)]
    file_output = file_output if isinstance(file_output, dict) else {}
    said = [k for k in ("monitor", "fullscreen") if k in file_output]
    if said:
        _note(cfg, f"config: [[output.screens]] is listed, so [output] {' and '.join(said)} "
                   f"{'is' if len(said) == 1 else 'are'} ignored — output 1's entry says")
    oc["screens"] = out
    oc["monitor"], oc["fullscreen"] = out[0]["monitor"], out[0]["fullscreen"]


def screens(cfg: dict) -> list[dict]:
    """The render outputs, one dict per output with `SCREEN`'s keys: the
    config's list when it has one (`load` checked it), else one output
    from ``[output] monitor`` / ``fullscreen`` with the default switches —
    today's one window. Never raises, never empty."""
    oc = cfg.get("output", {}) if isinstance(cfg, dict) else {}
    oc = oc if isinstance(oc, dict) else {}
    lst = oc.get("screens")
    if isinstance(lst, list):
        got = [{**SCREEN, **e} for e in lst if isinstance(e, dict)]
        if got:
            return got
    return [{**SCREEN, "monitor": oc.get("monitor", -1),
             "fullscreen": bool(oc.get("fullscreen", False)),
             "flip_x": oc.get("flip_x", False) is True,
             "flip_y": oc.get("flip_y", False) is True}]


def _kind_defaults(kind: str) -> dict:
    """The keys an entry of `kind` carries beyond role / kind / enabled,
    with their defaults: the old table's *defaults* (DEFAULTS, the hands'
    own table), less `enabled` — never the file's old table, which a
    `[[devices]]` list says is ignored. A `midi-out` entry's are `MIDI_OUT`."""
    if kind == "midi-out":
        return copy.deepcopy(MIDI_OUT)
    for section, k, _ in DEVICE_TABLES:
        if k != kind:
            continue
        if section == "hands":
            from .hands.core import DEFAULTS as HANDS
            base = HANDS
        else:
            base = DEFAULTS[section]
        return {key: copy.deepcopy(v) for key, v in base.items() if key != "enabled"}
    return {}


def _midi_role(mc: dict) -> str:
    """The MIDI table's role: its profile's name (`apc40`), which is what
    the rows and the desk page already mean by it."""
    prof = mc.get("profile")
    return prof if isinstance(prof, str) and prof and ":" not in prof else "midi"


def _device(n: int, e: dict, cfg: dict, roles: set[str], problems: list[str]) -> dict | None:
    """One `[[devices]]` entry, checked like `_screen`: a missing or bad
    role or kind drops the entry (a note, never a dead launch); `enabled`
    that is not true or false is true; a known kind's own keys are filled
    from its defaults. `problems` collects what was dropped, so a re-read
    while the app runs can refuse the whole edit."""
    where = f"config: [[devices]] entry {n}:"
    role, kind = e.get("role"), e.get("kind")
    if not isinstance(role, str) or not role.strip() or ":" in role:
        problems.append(f"{where} role = {role!r} is not a name without ':' — dropped")
        return None
    role = role.strip()
    if role in roles:
        problems.append(f"{where} role {role!r} is listed twice — the second dropped")
        return None
    if not isinstance(kind, str) or not kind.strip():
        problems.append(f"{where} ({role}) kind = {kind!r} is not a kind — dropped")
        return None
    kind = kind.strip()
    enabled = e.get("enabled", True)
    if not isinstance(enabled, bool):
        _note(cfg, f"{where} ({role}) enabled = {enabled!r} is not true or false — true")
        enabled = True
    roles.add(role)
    own = {k: v for k, v in e.items() if k not in DEVICE_KEYS}
    return {"role": role, "kind": kind, "enabled": enabled, **_kind_defaults(kind), **own}


def _translate(cfg: dict, data: dict) -> list[dict]:
    """No `[[devices]]`: the old tables — the defaults, and what the file
    says — become the equivalent entries in today's poll order, with one
    note per table the file holds, asking for the rename."""
    out = []
    for section, kind, role in DEVICE_TABLES:
        t = cfg[section]
        role = role or _midi_role(t)
        entry = {"role": role, "kind": kind, "enabled": bool(t.get("enabled", True)),
                 **{k: v for k, v in t.items() if k != "enabled"}}
        out.append(entry)
        if isinstance(data.get(section), dict):
            _note(cfg, f"config: [{section}] is now a [[devices]] entry (role = {role!r}, "
                       f"kind = {kind!r}) — see config.py")
    return out


def _daw(cfg: dict, entries: list[dict], wrote_out: set[str]) -> list[dict]:
    """The hands' DAW out as a sink (plan 27 B3): the first enabled hands
    entry whose `out` names a port gets a `midi-out` entry right after it
    — role `DAW_ROLE`, that port, ``carries`` its role — unless the list
    has a midi-out carrying that role already (or the role is taken). One
    note when the file wrote `out` itself (`wrote_out`: the hands roles
    whose table or entry did); the default port is today's behaviour and
    is translated silently."""
    hands = next((e for e in entries if e["kind"] == "hands" and e["enabled"]), None)
    out = hands.get("out") if hands is not None else None
    if hands is None or not isinstance(out, str) or not out.strip():
        return entries
    role = hands["role"]
    if any(e["kind"] == "midi-out" and e.get("carries") == role for e in entries):
        return entries
    if any(e["role"] == DAW_ROLE for e in entries):
        _note(cfg, f"config: [hands] out = {out!r} not sent: the role {DAW_ROLE!r} is taken — "
                   f"add a midi-out entry with carries = {role!r}")
        return entries
    daw = {"role": DAW_ROLE, "kind": "midi-out", "enabled": True,
           **copy.deepcopy(MIDI_OUT), "port": out.strip(), "carries": role}
    k = entries.index(hands)
    if role in wrote_out:
        _note(cfg, f"config: [hands] out is now a [[devices]] entry (role = {DAW_ROLE!r}, "
                   f"kind = 'midi-out', port = {out.strip()!r}, carries = {role!r}) — "
                   "see config.py")
    return [*entries[:k + 1], daw, *entries[k + 1:]]


def _devices(cfg: dict, data: dict, path: Path, problems: list[str]) -> None:
    """The device list (plan 27 B1), read in place as ``cfg["devices"]``:
    the checked `[[devices]]` entries when the file lists them (the old
    tables then ignored, one note each), else the old tables translated
    (`_translate`). The first entry of each old kind is folded back into
    its table, so everything that still reads ``cfg["midi"]`` /
    ``cfg["hands"]`` (the binding file's profile, the hands setup) reads
    what the entry says; a relative `map`, `calibration` or `tape` is
    resolved against the file's folder in both."""
    raw = data.get("devices")
    wrote_out: set[str] = set()
    if raw is None:
        entries = _translate(cfg, data)
        if isinstance(data.get("hands"), dict) and "out" in data["hands"]:
            wrote_out = {e["role"] for e in entries if e["kind"] == "hands"}
    else:
        if not isinstance(raw, list):
            problems.append(f"config: devices = {raw!r} is not a list of [[devices]] tables")
            raw = []
        entries, roles = [], set()
        for i, e in enumerate(raw):
            if not isinstance(e, dict):
                problems.append(f"config: [[devices]] entry {i + 1} is not a table ({e!r}) "
                                "— dropped")
                continue
            got = _device(i + 1, e, cfg, roles, problems)
            if got is not None:
                entries.append(got)
        for section, kind, _ in DEVICE_TABLES:
            if isinstance(data.get(section), dict):
                _note(cfg, f"config: [[devices]] is listed, so [{section}] is ignored — "
                           f"its {kind} entry says")
        wrote_out = {str(e.get("role", "")).strip() for e in raw
                     if isinstance(e, dict) and "out" in e}
    entries = _daw(cfg, entries, wrote_out)
    for e in entries:
        for key in ("map", "calibration", "tape"):
            v = e.get(key)
            if isinstance(v, str) and v and not Path(v).is_absolute():
                e[key] = str(path.parent / v)
    for section, kind, _ in DEVICE_TABLES:
        first = next((e for e in entries if e["kind"] == kind), None)
        if first is None:
            cfg[section]["enabled"] = False
            continue
        cfg[section] = {**cfg[section], **{k: v for k, v in first.items() if k not in DEVICE_KEYS},
                        "enabled": first["enabled"]}
    cfg["devices"] = entries


def devices(cfg: dict) -> list[dict]:
    """The checked device entries `load` put in the config, each with
    `role`, `kind`, `enabled` and the kind's own keys; never raises."""
    lst = cfg.get("devices") if isinstance(cfg, dict) else None
    return [dict(e) for e in lst if isinstance(e, dict)] if isinstance(lst, list) else []


def read_devices(path: Path) -> tuple[list[dict], list[str]]:
    """The device list of `path` as it is now, for the registry's watch:
    (entries, problems) — a file that will not parse, or an entry that
    had to be dropped, is a problem, and the registry keeps its old list.
    An error elsewhere in the file (a scalar where a table should be) is
    not the list's problem and does not block it. Nothing is printed: the
    notes `load` would make are its own."""
    import contextlib
    import io

    try:
        tomllib.loads(path.read_text())
    except (OSError, ValueError) as e:
        return [], [f"config: {e}"]
    with contextlib.redirect_stderr(io.StringIO()):
        cfg = load(path)
    return devices(cfg), list(cfg.get("problems", []))


def load(path: Path | None = None) -> dict:
    """The config, defaults filled in; `path` defaults to the library home's."""
    if path is None:
        path = library.ensure_home() / FILE
    from .hands.core import DEFAULTS as HANDS  # the one [hands] table (audit N1)

    cfg = copy.deepcopy(DEFAULTS)                 # a file may append to a list
    cfg["hands"] = copy.deepcopy(HANDS)
    data: dict = {}
    if path.exists():
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, ValueError) as e:
            cfg["error"] = f"config: {e}"
            data = {}
        bad = []
        for section, values in data.items():
            if section == "devices":
                continue                  # the list of tables: `_devices` reads it
            if isinstance(values, dict):
                cfg.setdefault(section, {}).update(values)
            else:
                # `midi = true` in place of [midi]: the defaults stand and the
                # SYSTEM page says so — the device entries expect a table
                bad.append(f"[{section}] must be a table, not {values!r}")
        if bad:
            cfg["error"] = "config: " + "; ".join(bad)
        legacy = cfg.pop(LEGACY_OUTPUT, None)
        if isinstance(legacy, dict):
            # the pre-split section name: its keys land under [output], a
            # real [output] wins key by key, and the file is asked to catch up
            # — on stderr and on the SYSTEM page (cfg["notes"])
            real = data.get("output")
            real = real if isinstance(real, dict) else {}   # a scalar was reported above
            cfg["output"] = {**DEFAULTS["output"], **legacy, **real}
            note = f"config: [{LEGACY_OUTPUT}] is now [output] — rename the section in {path}"
            cfg["notes"] = [note]
            print(note, file=sys.stderr)
    # the render outputs (plan 21 WP3): with a list, output 1's entry
    # becomes the scalar monitor / fullscreen read below
    _screens(cfg, data.get("output"))
    # the devices (plan 27 B1): `[[devices]]`, or the old tables translated;
    # an entry that had to be dropped is a note here and, for the registry's
    # re-read, a reason to keep the old list (`cfg["problems"]`)
    problems: list[str] = []
    _devices(cfg, data, path, problems)
    for note in problems:
        _note(cfg, note)
    if problems:
        cfg["problems"] = problems
    # the ground and the opacity are numbers: `bg = "x"` stopped the launch
    # in app._make_output; now it is the default, and the SYSTEM page says so
    for key in ("bg", "alpha"):
        v = cfg["output"].get(key, DEFAULTS["output"][key])
        if number(v) is None:
            cfg["output"][key] = DEFAULTS["output"][key]
            _note(cfg, f"config: [output] {key} = {v!r} is not a number — "
                       f"{DEFAULTS['output'][key]}")
    # a screen index is a whole number: `monitor = "left"` is −1 from here
    # on (where the window was last time) and the SYSTEM page says so —
    # whether that screen exists is placement's to say, at the launch
    for key in ("monitor", "control_monitor"):
        cfg["output"][key], note = placement.read(key, cfg["output"].get(key, -1))
        if note:
            cfg.setdefault("notes", []).append(note)
            print(note, file=sys.stderr)
    # [output] render is one of the caps' names: anything else is 1080p, said
    from .overlay import RENDER_DEFAULT, RENDER_NAMES  # params only, no window system

    rc = cfg["output"].get("render", RENDER_DEFAULT)
    if rc not in RENDER_NAMES:
        cfg["output"]["render"] = RENDER_DEFAULT
        _note(cfg, f"config: [output] render = {rc!r} is not one of {', '.join(RENDER_NAMES)} "
                   f"— {RENDER_DEFAULT}")
    # [output] flip_x / flip_y (plan 23 WP1, the one-output form) are
    # switches: anything else is off, said
    for key in ("flip_x", "flip_y"):
        v = cfg["output"].get(key, False)
        if not isinstance(v, bool):
            cfg["output"][key] = False
            _note(cfg, f"config: [output] {key} = {v!r} is not true or false — false")
    # [output] keep_awake is a switch: `keep_awake = "no"` keeps the Mac awake
    # (the show is safer awake), and the SYSTEM page says so
    awake = cfg["output"].get("keep_awake", True)
    if not isinstance(awake, bool):
        cfg["output"]["keep_awake"] = True
        _note(cfg, f"config: [output] keep_awake = {awake!r} is not true or false — "
                   "the Mac is kept awake")
    # [library] path (plan 25): "" is the home; anything else is resolved
    # here — `~` expanded, relative to this file's folder — so app.main gets
    # an absolute path. A leftover `git` key (the old git switch, removed) is said once
    if "git" in cfg["library"]:
        cfg["library"].pop("git")
        note = ("config: [library] git is gone (plan 25) — presets are shared "
                "through [library] path; remove the line")
        _note(cfg, note)
        print(note, file=sys.stderr)
    lp = cfg["library"].get("path", "")
    if not isinstance(lp, str):
        cfg["library"]["path"] = ""
        note = f"config: [library] path = {lp!r} is not text — the library stays in the home"
        _note(cfg, note)
        print(note, file=sys.stderr)
    elif lp.strip():
        q = Path(lp.strip()).expanduser()
        if not q.is_absolute():
            q = path.parent / q
        cfg["library"]["path"] = str(q.resolve())
    else:
        cfg["library"]["path"] = ""
    # the MIDI map lives next to the config unless it says otherwise
    m = cfg["midi"].get("map")
    if m and not Path(m).is_absolute():
        cfg["midi"]["map"] = str(path.parent / m)
    for key in ("calibration", "tape"):
        c = cfg["hands"].get(key)
        if c and not Path(c).is_absolute():
            cfg["hands"][key] = str(path.parent / c)
    return cfg
