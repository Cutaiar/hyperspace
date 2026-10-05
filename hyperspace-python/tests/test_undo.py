"""Plan 15 WP1 — undo down to single edits (hyperspace/undo.py).

Every rig is built the way app.main builds it — Library, registry, the
hands' settings, the clock and the LFOs, an Output, attach, the Router
over the home's bindings.json, `Presets`, a `Learn`, a `MidiIO` over
injected ports, the startup preset, and then the `Undo` — on a tmp_path
home, never ~/Hyperspace. `frames` is the app's frame order without the
windows: the clock, the MIDI poll, the macros' follow-up, `undo.tick`,
the feeds, `router.modulate`, `reg.apply`, `view.integrate`.
"""

import ast
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace

import mido
import numpy as np
import pytest
from conftest import opened_last

from hyperspace import hands, lfo, preset, tempo, undo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.ghost import GhostState
from hyperspace.learn import Learn
from hyperspace.library import PRESETS, Library, Marks
from hyperspace.lookback import DreamState
from hyperspace.midi import MidiIO
from hyperspace.overlay import Output
from hyperspace.params import Param, build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Bindings, Router, bindings_path
from hyperspace.view import ViewState

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
DT = 1 / 60
SETTLE = math.ceil(undo.SETTLE_S / DT) + 3      # frames that end a step for sure


class FakeIn:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)


class FakeOut:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


def boot(home, show: str | None = None, *, fx=None, dream=None, ghost=None):
    """app.main's construction order, headless, over `home` (a fresh one
    opens the party show and its startup preset, TUMBLE)."""
    if show:
        opened_last(home, show)
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=True)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, audio, lib.project,
                         dream=dream if dream is not None else DreamState(),
                         fx=fx if fx is not None else FxState(),
                         ghost=ghost if ghost is not None else GhostState())
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    lib.on_load("band", control.scene_loaded)
    control.library = lib
    settings = hands.HandSettings.from_config({})
    hands.register(reg, settings)
    r = SimpleNamespace(t=100.0)
    clock = tempo.Clock(now=lambda: r.t)
    lfos = lfo.LFOs(seed=1)
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    output = Output(None, None)
    output.register(reg)
    lib.attach(reg)
    # the panel's own params, declared as ui.Panel declares them (no imgui)
    from hyperspace.ui import Panel
    Panel._register_panel_params(SimpleNamespace(reg=reg, open=True, cheatsheet=True,
                                                 desk=True, page=1))
    router = Router(reg, Bindings.load(bindings_path(home), legacy_midi=None))
    presets = Presets(lib, reg, router)
    preset.migrate_home(lib, router)
    learn = Learn(reg, router.table, lane=router.lane)
    inp, out = FakeIn(), FakeOut()
    midi = MidiIO(reg, router.table, inp=inp, out=out, learner=learn)
    lib.project.load_startup()
    u = undo.Undo(reg, router.table, marks=Marks(lib),
                  tag=lambda: tuple(s.name for s in audio.chain.spec),
                  on_restore=router.sync_macros)
    undo.install(u)
    r.__dict__.update(lib=lib, reg=reg, view=view, control=control, chain=chain, audio=audio,
                      router=router, table=router.table, presets=presets, clock=clock,
                      lfos=lfos, learn=learn, midi=midi, inp=inp, out=out, undo=u,
                      home=Path(home), settings=settings, output=output)
    return r


@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path / "home")


def frames(r, n: int = 1, *, hand=None, lanes: bool = False) -> None:
    """`n` frames in app.frame's order. `hand(t)` is the hand lanes' vector
    for the frame (None: no tracker feeds)."""
    for _ in range(n):
        r.t += DT
        r.clock.tick(r.t)
        r.midi.poll()
        r.router.follow_macros()
        r.undo.tick(r.t)
        if hand is not None:
            r.router.feed("hand", hand(r.t))
        r.lfos.step(DT, r.t, r.clock)
        r.lfos.publish(r.router)
        r.router.modulate(r.chain if lanes else None)
        r.reg.apply()
        r.view.integrate(DT)


def settle(r) -> None:
    frames(r, SETTLE)


def labels(r) -> list[str]:
    return [s.label for s in r.undo.stack]


def look(r) -> tuple:
    """The loaded preset's whole state, as a save would write it."""
    t = r.table
    return (r.reg.snapshot(part="performance"), [b.to_json() for b in t.routes()],
            [b.to_json() for b in t.desk()], json.dumps(t.macros_doc(), sort_keys=True))


def same_look(a: tuple, b: tuple) -> bool:
    """Two `look`s: the rows, desk and macros equal, the values equal to
    within undo's tolerance — a restore leaves a base that only differs
    in its last bits alone (a performer's round-off, plan 15 §1 row 2)."""
    return (a[1:] == b[1:] and a[0].keys() == b[0].keys()
            and all(undo._same(v, b[0][k]) for k, v in a[0].items()))


def cc(control, value, channel=0):
    return mido.Message("control_change", channel=channel, control=control, value=value)


# ---------------------------------------------------------------- the leaf

def test_undo_imports_nothing_from_the_package():
    """undo.py is a leaf (the rule lfo.py and tempo.py keep): the registry
    and the table arrive as arguments, so any module may import it and no
    boundary test moves. It never calls `Param.modulate` or `feed`."""
    tree = ast.parse((PKG / "undo.py").read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            assert not n.level, f"undo.py imports from the package: {'.' * n.level}{n.module}"
            assert not (n.module or "").startswith("hyperspace"), n.module
        elif isinstance(n, ast.Import):
            assert not any(a.name.startswith("hyperspace") for a in n.names)
        elif isinstance(n, ast.Attribute):
            assert n.attr not in ("modulate", "feed", "_mod", "_base"), n.attr
    assert undo.SETTLE_S == 0.4 and undo.LIMIT == 100
    # with nothing installed the module functions are no-ops
    undo.install(None)
    undo.push("x")
    undo.undo()
    undo.redo()


# ---------------------------------------------------------------- gestures

def test_a_slider_drag_is_one_step_and_undo_sets_only_that_param(rig, monkeypatch):
    """Many base writes inside the settle time are one step, named from
    the difference; the restore calls `Param.set` on that one param."""
    p = rig.reg["view.bright"]
    was = p.base
    for k in range(20):                                # a drag: a write a frame
        p.set(was + 0.02 * (k + 1))
        frames(rig)
    assert len(rig.undo.stack) == 1                    # open already: Ctrl+Z works at once
    settle(rig)
    assert labels(rig) == [f"{p.label} {p.fmt(was)} → {p.fmt(p.base)}"]
    now = p.base
    written: list[str] = []
    real = Param.set
    with monkeypatch.context() as m:
        m.setattr(Param, "set", lambda self, v: (written.append(self.id), real(self, v))[1])
        assert rig.undo.undo() is True
    assert written == ["view.bright"] and p.base == was
    assert rig.undo.status == f"undid {p.label} {p.fmt(was)} → {p.fmt(now)}"
    assert rig.undo.stack == [] and len(rig.undo.redos) == 1
    # a toggle and a typed value are one step each, too
    frames(rig, undo.ABSORB_FRAMES + 1)                # the restore's own frames
    rig.reg["view.points"].toggle()
    settle(rig)
    rig.reg["view.speed"].set(0.77)
    settle(rig)
    assert len(rig.undo.stack) == 2 and labels(rig)[0].startswith(rig.reg["view.points"].label)


def test_a_pause_longer_than_the_settle_time_makes_a_second_step(rig):
    """`SETTLE_S` is the boundary: a pause under it is the same gesture,
    one over it ends the step (fork 17)."""
    p = rig.reg["view.bright"]
    was = p.base
    short = math.floor(undo.SETTLE_S / DT) - 3
    p.set(was + 0.1)
    frames(rig, short)                                 # held still, under the settle time
    p.set(was + 0.2)
    frames(rig)
    assert len(rig.undo.stack) == 1
    frames(rig, SETTLE)                                # …and now over it
    p.set(was + 0.3)
    settle(rig)
    assert len(rig.undo.stack) == 2
    rig.undo.undo()
    assert p.base == pytest.approx(was + 0.2)
    rig.undo.undo()
    assert p.base == was


def test_a_knob_turn_on_the_desk_is_one_step(rig):
    """CC messages through `MidiIO` over injected ports: a sweep of a
    preset-layer knob is one step, and undo puts the value back."""
    row = next(b for b in rig.table.active()
               if b.kind == "cc" and b.op == "abs" and b.feedback == "ring"
               and b.layer == "preset" and undo.watched(rig.reg[b.target]))
    p = rig.reg[row.target]
    was = p.base
    start = round(p.norm * 127)
    sweep = list(range(start, 128))[:24] if start < 100 else list(range(start, 0, -1))[:24]
    for v in sweep:
        rig.inp.queue.append(cc(row.number, v, row.channel or 0))
        frames(rig)
    assert p.base != was
    settle(rig)
    assert len(rig.undo.stack) == 1 and labels(rig)[0].startswith(p.label)
    rig.undo.undo()
    assert p.base == pytest.approx(was)


def test_a_performer_moving_makes_no_step(rig):
    """A hand on `view.speed` — a param whose base moves in its last bits
    when a performer takes it (plan 15 §1 row 2) — entering, moving for
    120 frames and leaving: the stack stays empty. So does an LFO."""
    rig.table.set_routes([Binding("hand:0", "view.speed", "position", 1.0),
                          Binding("lfo:0", "view.bright", "push", 0.4)])
    rig.undo.clear()
    speed = rig.reg["view.speed"]
    speed.set(0.3)
    rig.undo.clear()
    base = speed.base
    seen = []

    def hand(t):
        v = np.full(22, np.nan)
        v[0] = 0.5 + 0.5 * math.sin(t * 5.0)
        return v

    frames(rig, 10)                                    # no hand yet
    for _ in range(120):                               # in the box, moving
        frames(rig, hand=hand)
        seen.append(rig.view.speed)
    frames(rig, 40)                                    # gone: the base shows again
    assert max(seen) - min(seen) > 0.5                 # it really performed
    assert speed.base == pytest.approx(base, rel=1e-9)
    assert rig.undo.stack == [] and rig.undo.redos == []
    # …while a setter under the hand is a step, like any other
    for _ in range(5):
        frames(rig, hand=hand)
    speed.set_norm(0.8)
    for _ in range(SETTLE):
        frames(rig, hand=hand)
    assert len(rig.undo.stack) == 1 and labels(rig)[0].startswith(speed.label)


def test_integrated_state_and_the_clock_are_not_watched(rig):
    """`rot.phase.*` advancing, a tap burst, the panel's page and the
    output's fullscreen switch: none is a step."""
    reg = rig.reg
    for pid in ("rot.phase.XY", "tempo.bpm", "tempo.nudge", "ui.page", "ui.panel",
                "output.fullscreen", "output.monitor", "band.select", "band.sel.thr",
                "preset.select", "fx.select", "desk.shift", "audio.mic", "edit.undo"):
        assert pid in reg and not undo.watched(reg[pid]), pid
    for pid in ("view.bright", "scene.select", "master.gain", "hands.smooth", "ghost.on",
                "output.bg", "camera.yaw", "band.0.thr", "macro.1", "lfo.1.rate"):
        assert undo.watched(reg[pid]), pid
    reg["rot.rate.XY"].set(0.5)
    reg["view.rotate"].set(True)
    settle(rig)
    rig.undo.clear()
    ang, bpm = list(rig.view.ang), reg["tempo.bpm"].base
    for _ in range(5):                                 # a burst at 100 BPM
        reg["tempo.tap"].fire()
        frames(rig, 36)
    reg["ui.page"].set(3)
    reg["output.fullscreen"].set(True)
    reg["band.select"].set(2)
    settle(rig)
    assert rig.view.ang != ang and reg["tempo.bpm"].base != bpm
    assert rig.undo.stack == []


def test_session_params_are_covered(rig):
    """The hands' feel and the master faders undo like the look does."""
    reg = rig.reg
    smooth, gain = reg["hands.smooth"], reg["master.gain"]
    was = (smooth.base, gain.base)
    smooth.step(3)
    settle(rig)
    gain.step(-2)
    settle(rig)
    assert len(rig.undo.stack) == 2 and (smooth.base, gain.base) != was
    rig.undo.undo()
    rig.undo.undo()
    assert (smooth.base, gain.base) == was


def test_undo_of_a_slider_does_not_rerun_a_load(rig):
    """Undoing one slider is one `Param.set`: `desk_serial`, the layer
    that is up, a caught fader and an LFO's running phase are as they
    were (D7: the faders keep their catch)."""
    table, reg = rig.table, rig.reg
    fader = next(b for b in table.active()
                 if b.kind == "cc" and b.op == "abs" and b.feedback != "ring" and b.pickup)
    rig.inp.queue.append(cc(fader.number, round(reg[fader.target].norm * 127),
                            fader.channel or 0))
    frames(rig)
    assert fader.caught
    table.set_layer("global")
    settle(rig)
    rig.undo.clear()
    reg["view.bright"].step(5)
    settle(rig)
    osc = rig.lfos.lfos[0]
    before = (table.desk_serial, table.layer, table.layer_serial, fader.caught, osc.acc,
              osc.x, [id(b) for b in table.bindings])
    assert rig.undo.undo()
    assert (table.desk_serial, table.layer, table.layer_serial, fader.caught, osc.acc,
            osc.x, [id(b) for b in table.bindings]) == before
    x = osc.x
    frames(rig, 3)
    assert fader.caught and osc.x != x                 # still caught; the LFO ran on


# ---------------------------------------------------------------- actions

def test_a_preset_load_is_one_step_by_every_road(rig):
    """An F-key's trigger, `preset.next`, the strip's load and the file
    watch all meet in `Presets.load_doc`: one step each, `load <name>`."""
    reg, lib = rig.reg, rig.lib
    assert lib.current(PRESETS) == "TUMBLE" and rig.undo.stack == []
    reg["preset.load.1"].fire()                        # F2
    settle(rig)
    assert labels(rig) == ["load FACES"]
    reg["preset.next"].fire()                          # QUANT, the pad's B
    settle(rig)
    assert labels(rig) == ["load FACES", "load FIELD"]
    lib.load(PRESETS, "WAKE")                          # the strip's list
    settle(rig)
    assert labels(rig)[2:] == ["load WAKE"]
    # the file watch: the loaded preset's file edited on disk
    path = rig.presets.save_as("MINE")
    settle(rig)
    assert len(rig.undo.stack) == 3                    # a save is no step
    doc = json.loads(path.read_text())
    doc["values"]["view.bright"] = 2.5
    path.write_text(json.dumps(doc))
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
    assert lib.poll(now=1e9)
    settle(rig)
    assert labels(rig)[3:] == ["load MINE"] and reg["view.bright"].base == 2.5
    # a load that fails leaves no step
    path.write_text(json.dumps({**doc, "values": {"view.bright": "fast"}}))
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 10))
    lib.poll(now=2e9)
    settle(rig)
    assert len(rig.undo.stack) == 4


def test_undo_of_a_load_puts_back_the_values_the_routes_the_desk_the_macros_and_the_name(rig):
    """D2 both ways: the earlier state comes back whole — an unsaved edit
    included — and the library says the earlier preset is loaded."""
    reg, lib, pr = rig.reg, rig.lib, rig.lib.project
    reg["view.bright"].step(7)                         # an unsaved edit of TUMBLE
    rig.table.set_macros({"macro.1": {"label": "mine", "subs": [
        {"base": "view.speed", "from": 0.2, "to": 0.9}]}}, reg)
    settle(rig)
    tumble = look(rig)
    assert lib.is_dirty(PRESETS) and pr.active == 0
    reg["preset.load.4"].fire()                        # TRIP: other values, routes, desk
    assert lib.current(PRESETS) == "TRIP" and not lib.is_dirty(PRESETS) and pr.active == 4
    settle(rig)
    # (round-off under a performer may light the dot: plan 15 §1 row 2)
    trip, dirty = look(rig), lib.is_dirty(PRESETS)
    assert all(a != b for a, b in zip(tumble, trip, strict=True))
    serial = rig.table.desk_serial
    assert rig.undo.undo() and rig.undo.status == "undid load TRIP"
    assert same_look(look(rig), tumble)
    assert lib.current(PRESETS) == "TUMBLE" and lib.is_dirty(PRESETS) and pr.active == 0
    assert rig.table.desk_serial == serial             # a restore, not a load
    frames(rig, 5)
    assert same_look(look(rig), tumble) and rig.undo.redos   # nothing re-landed, redo intact
    assert rig.undo.redo() and rig.undo.status == "redid load TRIP"
    assert same_look(look(rig), trip)
    assert lib.current(PRESETS) == "TRIP" and lib.is_dirty(PRESETS) == dirty and pr.active == 4


def test_save_after_undoing_a_load_writes_the_earlier_preset(rig):
    """The marks (fork 2): after undoing a load, Save writes the earlier
    look to the earlier preset's file — never over the later one."""
    reg, lib, presets = rig.reg, rig.lib, rig.presets
    a = presets.save_as("AAA")
    reg["view.shape"].step(2)
    b = presets.save_as("BBB")
    settle(rig)
    rig.undo.clear()
    lib.load(PRESETS, "AAA")
    settle(rig)
    lib.load(PRESETS, "BBB")
    settle(rig)
    b_text = b.read_text()
    assert rig.undo.undo()                             # back on AAA
    assert lib.current(PRESETS) == "AAA" and not lib.is_dirty(PRESETS)
    reg["view.bright"].step(4)
    assert lib.overwrite(PRESETS) == a
    assert json.loads(a.read_text())["name"] == "AAA"
    assert json.loads(a.read_text())["values"]["view.bright"] == reg["view.bright"].base
    assert b.read_text() == b_text


def test_a_show_load_and_its_startup_preset_are_one_step(rig):
    """Nested pushes in one frame are one action: the show and the preset
    it starts on undo together, and the `Project` comes back."""
    reg, lib, pr = rig.reg, rig.lib, rig.lib.project
    reg["master.gain"].step(-3)                        # a session edit
    settle(rig)
    party = (pr.name, list(pr.bank), pr.startup, pr.factory, pr.path, look(rig),
             reg.snapshot(part="session"), lib.current(PRESETS), lib.current("band"))
    last = lib.last_show()
    pr.load("house")
    settle(rig)
    assert labels(rig)[1:] == ["show house"]
    assert pr.name == "house" and lib.current(PRESETS) != "TUMBLE"
    assert rig.undo.undo() and rig.undo.status == "undid show house"
    session = reg.snapshot(part="session")
    assert (pr.name, list(pr.bank), pr.startup, pr.factory, pr.path) == party[:5]
    assert same_look(look(rig), party[5]) and session == party[6]
    assert (lib.current(PRESETS), lib.current("band")) == party[7:]
    assert pr.active == 0 and lib.last_show() != last  # `last_show` is not rewritten
    assert rig.undo.redo()
    assert pr.name == "house" and pr.startup == lib.current(PRESETS)
    # a new show is one step too
    rig.undo.undo()
    pr.new("fresh")
    settle(rig)
    assert labels(rig)[-1] == "new show" and pr.name == "fresh"
    rig.undo.undo()
    assert pr.name == "party" and lib.current(PRESETS) == "TUMBLE"


def test_a_push_and_its_changes_are_one_step(rig):
    """`undo.push`, then changes over the next frames: one entry, under the
    caller's label; a second push in the same frame is the same action;
    an edit not yet ticked is its own step, before the action."""
    reg = rig.reg
    bright, speed = reg["view.bright"], reg["view.speed"]
    was = (bright.base, speed.base)
    bright.step(2)                                     # an edit no tick has seen
    mid = bright.base
    undo.push("the action")
    undo.push("the same action, from the inside")
    bright.step(3)
    frames(rig, 2)
    speed.step(4)                                      # a follow-up, two frames on
    settle(rig)
    assert labels(rig)[1] == "the action" and len(rig.undo.stack) == 2
    assert labels(rig)[0].startswith(bright.label)
    rig.undo.undo()
    assert (bright.base, speed.base) == (mid, was[1])
    rig.undo.undo()
    assert (bright.base, speed.base) == was
    # a second action in a later frame closes the first and opens its own
    undo.push("one")
    bright.step(1)
    frames(rig)
    undo.push("two")
    speed.step(1)
    settle(rig)
    assert labels(rig) == ["one", "two"]


def test_an_action_that_changes_nothing_leaves_no_step(rig):
    """An empty step is dropped when it closes — and skipped by an undo
    that comes before it has."""
    rig.reg["view.bright"].step(2)
    settle(rig)
    undo.push("nothing")
    assert len(rig.undo.stack) == 2
    settle(rig)
    assert len(rig.undo.stack) == 1
    free = next(p.id for p in rig.reg if not any(b.target == p.id for b in rig.table.midi()))
    rig.midi.unbind(free)                              # nothing mapped there: nothing goes
    assert len(rig.undo.stack) == 2
    settle(rig)
    assert len(rig.undo.stack) == 1
    rig.lib.load(PRESETS, "TUMBLE")                    # the same preset… with an edit: a step
    settle(rig)
    assert labels(rig)[1:] == ["load TUMBLE"]
    rig.lib.load(PRESETS, "TUMBLE")                    # …and clean: nothing changes
    settle(rig)
    assert len(rig.undo.stack) == 2
    undo.push("nothing again")
    assert rig.undo.undo() and rig.undo.status == "undid load TUMBLE"
    rig.undo.clear()
    assert rig.undo.undo() is False and rig.undo.status == "nothing to undo"
    assert rig.undo.redo() is False and rig.undo.status == "nothing to redo"


def test_redo_and_a_new_edit_clears_it(rig):
    reg = rig.reg
    p = reg["view.bright"]
    a = p.base
    p.step(4)
    settle(rig)
    b = p.base
    assert rig.undo.undo() and p.base == a
    assert rig.undo.redo() and p.base == b and rig.undo.status.startswith("redid ")
    assert rig.undo.undo() and p.base == a
    assert rig.undo.undo() is False                    # nothing left
    frames(rig, 5)                                     # the restore's frames are no gesture
    assert len(rig.undo.redos) == 1 and rig.undo.stack == []
    reg["view.speed"].step(2)                          # a new edit: the redo is gone
    settle(rig)
    assert rig.undo.redos == [] and rig.undo.redo() is False
    assert p.base == a
    # the triggers the keys fire reach the installed instance
    reg["edit.undo"].fire()
    assert rig.undo.status.startswith("undid ") and rig.undo.stack == []
    reg["edit.redo"].fire()
    assert rig.undo.status.startswith("redid ") and len(rig.undo.stack) == 1


def test_undo_writes_no_file_and_the_dirty_dot_is_honest(rig):
    """A restore writes nothing: no file in the home is made or touched.
    The dirty dots compare the live state with the loaded reference, so
    they relight and go out as the state does."""
    reg, lib = rig.reg, rig.lib
    rig.presets.save_as("MINE")
    settle(rig)
    rig.undo.clear()

    def tree():
        return {p: p.stat().st_mtime_ns for p in sorted(rig.home.rglob("*")) if p.is_file()}

    files = tree()
    assert not lib.is_dirty(PRESETS)
    reg["view.bright"].step(5)
    settle(rig)
    assert lib.is_dirty(PRESETS)
    lib.load(PRESETS, "FACES")
    settle(rig)
    rig.table.remove(rig.table.routes()[0])            # an edit of FACES
    settle(rig)
    assert lib.is_dirty(PRESETS) and labels(rig)[-1] == "routes"
    rig.undo.undo()
    assert not lib.is_dirty(PRESETS) and lib.current(PRESETS) == "FACES"
    rig.undo.undo()
    assert lib.is_dirty(PRESETS) and lib.current(PRESETS) == "MINE"
    rig.undo.undo()
    assert not lib.is_dirty(PRESETS) and lib.current(PRESETS) == "MINE"
    for _ in range(3):
        rig.undo.redo()
    assert lib.is_dirty(PRESETS) and lib.current(PRESETS) == "FACES"
    assert tree() == files


def test_a_scene_pick_undoes_with_its_strips(rig):
    """`scene.select`'s setter lands a whole scene; the watcher makes it
    one step, and the restore's second pass puts the strips back — edited
    ones included."""
    reg, lib = rig.reg, rig.lib
    reg["band.1.thr"].step(6)                          # a strip off its scene
    settle(rig)
    band = reg.snapshot("band")
    scene, cur = reg["scene.select"].base, lib.current("band")
    reg["scene.select"].set(4)
    settle(rig)
    assert len(rig.undo.stack) == 2 and reg.snapshot("band") != band
    assert lib.current("band") != cur
    assert rig.undo.undo()
    assert reg["scene.select"].base == scene and reg.snapshot("band") == band
    assert lib.current("band") == cur and lib.is_dirty("band")
    assert rig.undo.redo() and reg["scene.select"].base == 4
    assert reg.snapshot("band") != band and not lib.is_dirty("band")


def test_the_macros_do_not_re_land_after_an_undo(rig):
    """`Router.sync_macros`: a restore puts the macro's base and its
    subscriber's base back itself; `follow_macros` must not then write
    the subscriber over the value restored."""
    reg, table = rig.reg, rig.table
    table.set_macros({"macro.1": {"subs": [{"base": "view.bright", "from": 0.0, "to": 1.0}]}},
                     reg)
    settle(rig)
    bright, knob = reg["view.bright"], reg["macro.1"]
    bright.set_norm(0.9)                               # off where the macro put it
    settle(rig)
    rig.undo.clear()
    was = (knob.base, bright.base)
    knob.set_norm(0.25)                                # the knob: its subscriber follows
    settle(rig)
    assert bright.norm == pytest.approx(0.25) and len(rig.undo.stack) == 1
    assert rig.undo.undo()
    assert (knob.base, bright.base) == was
    frames(rig, 10)
    assert (knob.base, bright.base) == was and rig.undo.stack == []
    # a subscriber edited on the page, undone: the macros come back too
    table.macros["macro.1"].subs[0].hi = 0.5
    table.macros_serial += 1
    settle(rig)
    assert labels(rig) and table.macros["macro.1"].subs[0].hi == 0.5
    rig.undo.undo()
    frames(rig, 5)
    assert table.macros["macro.1"].subs[0].hi == 1.0 and (knob.base, bright.base) == was


# ---------------------------------------------------------------- the band layout

def three_bands(home) -> None:
    """A user band preset on another layout: three bands, its own strips."""
    doc = {"schema": "hyperspace.preset/1", "group": "band", "name": "THREE",
           "layout": {"bands": [{"f": 80.0, "q": 1.0, "curve": "rect", "name": "LO"},
                                {"f": 900.0, "q": 1.2, "curve": "rect", "name": "MD"},
                                {"f": 7000.0, "q": 0.8, "curve": "rect", "name": "HI"}]},
           "values": {"band.0.thr": 0.3, "band.2.post": 0.5}}
    (home / "band").mkdir(parents=True, exist_ok=True)
    (home / "band" / "three.json").write_text(json.dumps(doc))


def test_a_band_preset_load_with_a_layout_undoes_whole(rig):
    """`Marks.before`: a load that brings its own layout is one step, and
    undoing it puts the layout back first, then the strips, then the name."""
    reg, lib, chain = rig.reg, rig.lib, rig.chain
    curve = chain.layout()["bands"][0]["curve"]
    three_bands(rig.home)
    doc = json.loads((rig.home / "band" / "three.json").read_text())
    for row in doc["layout"]["bands"]:
        row["curve"] = curve
    (rig.home / "band" / "three.json").write_text(json.dumps(doc))
    lib.poll(now=1e9)
    reg["band.4.thr"].step(5)
    settle(rig)
    layout, band, cur = chain.layout(), reg.snapshot("band"), lib.current("band")
    assert chain.n == 6
    lib.load("band", "THREE")
    settle(rig)
    assert chain.n == 3 and "band.4.thr" not in reg and labels(rig)[-1] == "band: THREE"
    assert rig.undo.undo() and rig.undo.status == "undid band: THREE"
    assert chain.n == 6 and chain.layout() == layout and reg.snapshot("band") == band
    assert lib.current("band") == cur
    assert rig.undo.redo()
    assert chain.n == 3 and lib.current("band") == "THREE" and not lib.is_dirty("band")
    assert rig.undo.undo() and rig.undo.undo()         # …and the strip edit before it
    assert chain.n == 6 and reg.snapshot("band") != band and rig.undo.stack == []


def test_strips_are_put_back_only_onto_the_layout_they_were_made_on(rig):
    """The tag (fork 4): after a band is added, an older strip edit is
    left and the rest of that step lands, with a note; with the band
    removed again, it lands."""
    reg, control = rig.reg, rig.control
    thr, bright = reg["band.0.thr"], reg["view.bright"]
    was = (thr.base, bright.base)

    def edit():
        thr.step(5)
        bright.step(5)                                 # the same frame: one gesture
        settle(rig)
        assert len(rig.undo.stack) == 1
        return thr.base

    edited = edit()
    i = control.add_band()
    frames(rig, 3)
    assert rig.undo.undo()
    assert bright.base == was[1]                       # the rest of the step landed
    assert reg["band.0.thr"].base == edited            # the strip was left
    assert "the bands have changed: their strips were left" in rig.undo.status
    control.remove_band(i)
    frames(rig, 3)
    # the same again, the band removed before the undo: the layout is the
    # one the step was made on, so the strip lands too
    reg["band.0.thr"].set(was[0])
    settle(rig)
    rig.undo.clear()
    thr = reg["band.0.thr"]
    edit()
    i = control.add_band()
    frames(rig, 3)
    control.remove_band(i)
    frames(rig, 3)
    assert rig.undo.undo() and "bands" not in rig.undo.status
    assert (reg["band.0.thr"].base, bright.base) == was


def test_a_band_add_remove_or_move_makes_no_step(rig):
    """Tick step 1: the watched ids or the tag changed — not a step (the
    band strip's own 8-second reset undo is untouched beside it)."""
    control, chain = rig.control, rig.chain
    i = control.add_band()
    settle(rig)
    assert chain.n == 7 and rig.undo.stack == []
    control.move_band(0, 3)
    settle(rig)
    assert rig.undo.stack == []
    control.remove_band(i)
    settle(rig)
    assert chain.n == 6 and rig.undo.stack == []
    assert rig.undo.undo() is False
    # …and an edit after it is a step again
    rig.reg["band.2.thr"].step(3)
    settle(rig)
    assert len(rig.undo.stack) == 1


def test_the_stack_is_bounded(rig):
    """`LIMIT` steps are kept; the oldest goes first."""
    p = rig.reg["view.bright"]
    u = rig.undo
    t = rig.t
    first = None
    for k in range(undo.LIMIT + 7):
        p.set(1.0 + 0.001 * k)
        t += 1.0
        u.tick(t)                                      # sees the change
        t += 1.0
        u.tick(t)                                      # a second of quiet: closed
        first = first or u.stack[0].label
    assert len(u.stack) == undo.LIMIT and u.stack[0].label != first
    n = 0
    while u.undo():
        n += 1
    assert n == undo.LIMIT and len(u.redos) == undo.LIMIT
    assert p.base == pytest.approx(1.0 + 0.001 * 6)    # the seven oldest are gone


# ---------------------------------------------------------------- review of PR #82

def test_undoing_a_scene_pick_names_the_band_preset_it_was_on(rig):
    """A scene pick is a watcher step (control.py pushes nothing), and
    putting `scene.select` back adopts that scene: `Marks.mend` then puts
    the strip's own name back, so Save cannot write a user preset's look
    under a factory scene's name. A slider undone after a save-as stays
    on the new name (fork 2)."""
    reg, lib = rig.reg, rig.lib
    reg["band.1.thr"].step(4)
    lib.save_as("band", "Mine")                        # scene 0's strips, edited, as Mine
    settle(rig)
    rig.undo.clear()
    band = reg.snapshot("band")
    reg["scene.select"].set(3)
    settle(rig)
    assert lib.current("band") != "Mine" and len(rig.undo.stack) == 1
    assert rig.undo.undo()
    assert lib.current("band") == "Mine" and not lib.is_dirty("band")
    assert reg.snapshot("band") == band and reg["scene.select"].base == 0
    assert rig.undo.redo() and lib.current("band") != "Mine"
    assert rig.undo.undo() and lib.current("band") == "Mine"
    # a slider, then a save-as, then undo: the value goes back, the name stays
    frames(rig, 3)
    reg["view.bright"].step(3)
    settle(rig)
    rig.presets.save_as("LATER")
    settle(rig)
    assert rig.undo.undo() and lib.current(PRESETS) == "LATER"


def test_an_action_that_changes_nothing_keeps_the_redo(rig):
    """A refused unbind, or a load that fails, leaves no step — and must
    not cost the redo stack either; an action that does change something
    clears it, as a gesture does."""
    reg = rig.reg
    reg["view.bright"].step(3)
    settle(rig)
    assert rig.undo.undo() and len(rig.undo.redos) == 1
    frames(rig, 3)
    rig.midi.unbind("band.0.post")                     # the session's row: refused
    assert rig.learn.refused
    settle(rig)
    assert rig.undo.stack == [] and len(rig.undo.redos) == 1
    assert rig.undo.redo()
    assert rig.undo.undo()
    frames(rig, 3)
    reg["preset.load.2"].fire()                        # a real action: the redo goes
    settle(rig)
    assert rig.undo.redos == [] and labels(rig) == ["load FIELD"]


def test_a_row_that_undo_brings_back_picks_up_afresh(rig):
    """A desk row removed and restored is a new row: its runtime state (a
    fader's catch, its last reading) starts over, while the rows that
    never left keep theirs."""
    table = rig.table
    table.set_desk([*table.desk(), Binding("cc:5:99", "view.bright", "abs", pickup=True)],
                   load=False)
    settle(rig)
    rig.undo.clear()
    row = next(b for b in table.desk() if b.source == "cc:5:99")
    other = table.desk()[0]
    row.caught, row.last_hw, other.caught = True, 0.9, True
    undo.push("unmap")
    table.remove(row)
    settle(rig)
    assert rig.undo.undo()
    back = next(b for b in table.desk() if b.source == "cc:5:99")
    assert back is not row and (back.caught, back.last_hw, back.last_out) == (False, None, None)
    assert next(b for b in table.desk() if b.source == other.source).caught


def test_a_load_right_after_another_action_is_its_own_step(rig):
    """An action at the end of one frame (the panel's ×) and a preset load
    at the start of the next (a key, before the tick) are two steps: a
    load never nests inside an action that is no load."""
    table, lib = rig.table, rig.lib
    routes = [b.to_json() for b in table.routes()]
    undo.push("delete route")
    table.remove(table.routes()[0])
    rig.reg["preset.load.1"].fire()                    # no tick in between
    settle(rig)
    assert labels(rig) == ["delete route", "load FACES"]
    assert rig.undo.undo() and lib.current(PRESETS) == "TUMBLE"
    assert len(table.routes()) == len(routes) - 1
    assert rig.undo.undo() and [b.to_json() for b in table.routes()] == routes


# ---------------------------------------------------------------- an idle app

class _Keys:
    """Nobody at the keyboard."""

    typing = False

    def pressed(self, key):
        return False

    def held(self, key, now):
        return 0.0

    def shift(self):
        return False

    def super(self):
        return False

    def control(self):
        return False


class _Hands:
    """`LeapSource.latest()` over the synthetic hands of tests/fake_hands.py."""

    status, on = "tracking", True

    def __init__(self, clock):
        self.clock, self.seq, self.hands = clock, 0, {}

    def put(self, *hs):
        from hyperspace.hands.core import features
        self.seq += 1
        self.hands = {h.type.name.lower(): (features(h), h.confidence) for h in hs}

    def latest(self):
        return self.seq, self.clock(), self.hands

    def close(self):
        pass


def test_an_idle_app_makes_no_step(tmp_path):
    """The real `app.frame` over the real objects, nobody touching
    anything: every factory preset of the party show loaded in turn, each
    followed by five seconds of frames with the LFOs running and routed,
    the analyzer stepping on a synthetic signal that drives the lane
    routes, two hands moving through the box (and out of it, and back),
    `Registry.apply`, `view.integrate`, and — where a GL context can be
    made — the real renderer drawing every frame (the look-back's and the
    effects' clocks). The undo stack holds the eight loads and nothing
    else: no base moves on its own."""
    import fake_hands

    from hyperspace import app
    from hyperspace.audio import AudioEngine

    renderer = fbo = ctx = None
    try:
        import moderngl

        from hyperspace.render import Renderer
        ctx = moderngl.create_context(standalone=True)
        fbo = ctx.framebuffer(color_attachments=[ctx.texture((320, 200), 4)])
        renderer = Renderer(ctx)
    except Exception:  # noqa: BLE001 — no GL here: the frame runs without the draw
        renderer = None
    if renderer is not None:
        r = boot(tmp_path / "home", fx=renderer.fx.state, dream=renderer.lookback.state,
                 ghost=renderer.ghost.state)
    else:
        r = boot(tmp_path / "home")
    reg, lib, chain = r.reg, r.lib, r.chain
    assert lib.project.name == "party" and lib.current(PRESETS) == "TUMBLE"

    # the audio engine's two per-frame calls over a synthetic signal: a
    # swept tone under a 2 Hz gate, so every band's lane rises and falls
    sr = 48_000.0                                       # Analyser()'s default rate
    hop = round(sr * DT)
    audio = SimpleNamespace(chain=chain, on=True, n=0)

    def audio_step(dt):
        k = np.arange(audio.n, audio.n + hop)
        audio.n += hop
        t = k / sr
        f = 60.0 * 2.0 ** (7.0 * (0.5 + 0.5 * np.sin(t * 0.9)))
        gate = (np.sin(t * 2 * np.pi * 2.0) > 0) * 0.8
        chain.an.feed(np.sin(2 * np.pi * f * t) * gate + 0.02 * np.sin(t * 9000.0))
        chain.step(dt)
    audio.step = audio_step
    audio.publish = lambda router: AudioEngine.publish(audio, router)

    src = _Hands(lambda: r.t)
    hands_io = hands.HandsIO(r.settings, {"out": ""}, source=src, clock=lambda: r.t)
    if renderer is not None:
        renderer.ghost.source, renderer.ghost.router = hands_io, r.router
    reg["ghost.on"].set(True)
    r.undo.clear()

    def move_hands(t):
        hs = []
        if math.sin(t * 0.7) > -0.6:                    # out of the box now and then
            hs.append(fake_hands.hand("right", at=(120 * math.sin(t * 1.3),
                                                   220 + 110 * math.sin(t * 0.9),
                                                   90 * math.sin(t * 1.7))))
        if math.sin(t * 0.5 + 1.0) > -0.3:
            hs.append(fake_hands.hand("left", "fist" if math.sin(t * 2.1) > 0.5 else "open",
                                      at=(-140 + 60 * math.sin(t * 1.1),
                                          200 + 90 * math.cos(t * 0.8), 40 * math.sin(t))))
        src.put(*hs)

    def draw_render(dt):
        if renderer is None:
            return
        fbo.use()
        ctx.viewport = (0, 0, 320, 200)
        renderer.draw(r.view, 320, 200)

    host = app.Host(
        reg=reg, view=r.view, control=r.control, audio=audio, router=r.router,
        clock=r.clock, lfos=r.lfos, keys=_Keys(), mouse=SimpleNamespace(poll=lambda shift: None),
        output=r.output, renderer=renderer if renderer is not None else SimpleNamespace(),
        panel=SimpleNamespace(restart_requested=False),
        reloader=SimpleNamespace(poll=lambda: None, runtime_error=""),
        draw_render=draw_render, draw_panel=lambda dt, fps: None,
        restart=lambda: None, quit=lambda: None, pad=None, midi_io=r.midi,
        hands_io=hands_io, bridge_io=None, dream_io=None, learn=r.learn, undo=r.undo)

    def run(n):
        for _ in range(n):
            r.t += DT
            move_hands(r.t)
            assert app.frame(host, r.t, DT, 60.0), host.reloader.runtime_error

    run(120)                                            # TUMBLE, as launched
    assert labels(r) == [], labels(r)
    bank = [n for n in lib.project.bank if n]
    order = bank[1:] + bank[:1]
    performed: set[str] = set()
    try:
        for name in order:
            reg[f"preset.load.{bank.index(name)}"].fire()
            for _ in range(5):                          # 5 × 60 frames: five seconds
                run(60)
                performed |= {p.id for p in reg if p.modulated}
            assert labels(r)[-1] == f"load {name}", (name, labels(r))
    finally:
        if fbo is not None:
            fbo.release()
            ctx.release()
    assert labels(r) == [f"load {n}" for n in order]
    assert r.undo.redos == []
    # it was not a still life: hands, lanes and LFOs all held params
    table_sources = {b.source.split(":")[0] for b in r.table.routes()}
    assert len(performed) > 20 and "hand" in table_sources
    assert r.view.ang != [0.0] * 6
