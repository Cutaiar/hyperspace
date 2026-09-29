"""Plan 12 — the five party presets, headless.

Each preset is loaded through the real `Presets` (plan 13 WP2: one file,
library/presets/party-*.json, its scene's values and the routes of its
party-* routing preset) over the full registry and a `Router`, and two
fake hands are driven through the real hand chain (`HandsIO`: range → One
Euro → dead zone → follower, the default feel). For every hand row the
axis is swept across its throw and the target has to move the way the plan's
table says: monotonic in the row's sign, exactly the base when the hand is
level (or, for height, at the bottom), the base again once the hand has
left the box, and the base when the hand was never seen — with the audit's
B1 still open, so a `position` row here is only allowed on a param whose
base is where the axis rests.
"""

import itertools
import json
import math

import pytest
from test_routing import rig

from hyperspace.hands import HandSettings, HandsIO
from hyperspace.hands.core import DEFAULT_DOFS, PINCHES, default_range
from hyperspace.library import FACTORY
from hyperspace.params import Kind
from hyperspace.preset import FACTORY_PRESETS, HAND_AXES, PARTY, Presets, hand
from hyperspace.routing import Bindings, Router

DT = 1 / 60
HOLD = 90                # frames: the One Euro and the return spring both settle
SIDE = {"L": "left", "R": "right"}


class DictSource:
    def __init__(self):
        self.seq, self.hands, self.on, self.status = 0, {}, True, "fake"
        self.t = 0.0

    def put(self, hands):
        self.seq += 1
        self.hands = {s: (f, 1.0) for s, f in hands.items()}

    def latest(self):
        return self.seq, self.t, self.hands


class NullOut:
    name = "none"

    def send(self, m):
        pass


def feats(side: str, **u) -> dict:
    """One hand's features at u per axis (rest for the rest)."""
    out = {}
    for axis in HAND_AXES:
        lo, hi = default_range(side, axis)
        v = u.get(axis, 0.0 if axis == "y" else 0.5)
        out[axis] = lo + v * (hi - lo)
    out.update({f"pinch_{f}": 1.0 for f in PINCHES}, grab=0.0, pinch=0.0, grab_angle=0.0,
               pinch_mm=80.0)
    return out


def theme(name: str) -> dict:
    """The preset's values: the party slot's scene over its routing preset's bases."""
    return json.loads((FACTORY / "presets" / f"{name}.json").read_text())["values"]


def load(name: str, tmp_path):
    """The party preset through the one loader, as its F-key loads it."""
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings())
    presets = Presets(r.lib, r.reg, router)
    slot = name.split("-", 1)[1].upper()
    assert presets.load(slot) == [] and presets.notes == [], (name, presets.notes)
    assert router.table.dropped == []
    return r, router


def stage(name: str, tmp_path):
    r, router = load(name, tmp_path)
    src = DictSource()
    io = HandsIO(HandSettings.from_config(), {"enabled": True}, source=src, out=NullOut(),
                 clock=lambda: src.t)
    return r, router, src, io


def hold(r, router, src, io, hands: dict, frames: int = HOLD) -> None:
    for _ in range(frames):
        src.t += DT
        src.put(hands)
        io.poll(DT, None, router)
        router.modulate()
        r.reg.apply()
        r.view.integrate(DT)


def offset(p) -> float:
    """The hand's offset in norm units — effective less the *current* base
    (the integrator moves a live plane's base under the hand), wrapped for
    a circular param."""
    d = p.eff_norm - p.norm
    return math.remainder(d, 1.0) if p.wrap else d


# ---------------------------------------------------------------- the files

def desk_rig(tmp_path):
    """The full registry, a MIDI adapter on fake ports over the live table,
    `Presets`, and the party project open — the F-keys' road."""
    from test_midi import FakeIn, FakeOut

    from hyperspace.midi import MidiIO

    r = rig(tmp_path=tmp_path, full=True)
    inp, out = FakeIn(), FakeOut()
    midi = MidiIO(r.reg, Bindings.factory(), inp=inp, out=out)
    router = Router(r.reg, midi.table)
    presets = Presets(r.lib, r.reg, router)
    r.lib.project.load("party")
    return r, router, presets, midi, inp


def test_the_five_party_presets_load_by_f_key_as_presets(tmp_path):
    """Plan 13 WP5 (§10 exit 15): on the party project F1–F5 load TUMBLE,
    FACES, FIELD, WAKE, TRIP — one step each, the preset's routes and desk
    replacing the last's, nothing noted; TUMBLE's left height keeps its
    push on the drive (decision register row 19 (a): a route may perform a
    session param)."""
    r, router, presets, _midi, _inp = desk_rig(tmp_path)
    for k, slug in enumerate(PARTY):
        r.reg[f"preset.load.{k}"].fire()
        name = slug.split("-", 1)[1].upper()
        assert r.lib.current("presets") == name and r.lib.project.active == k, slug
        assert presets.notes == [] and router.table.dropped == [], (slug, presets.notes)
        assert [b.to_json() for b in router.table.routes()] == \
            [b.to_json() for b in FACTORY_PRESETS[slug].routes()], slug
        want = json.loads((FACTORY / "presets" / f"{slug}.json").read_text())["desk"]
        got = [{k2: v for k2, v in b.to_json().items() if k2 != "layer"}
               for b in router.table.desk()]
        assert got == want, slug
        assert not r.lib.is_dirty("presets"), slug
    r.reg["preset.load.0"].fire()
    assert [b.target for b in router.table.routes() if b.source == hand("L", "y")] \
        == ["master.gain"]


@pytest.mark.parametrize("slug,targets", [("party-wake", "WAKE_KNOBS"),
                                          ("party-trip", "TRIP_KNOBS")])
def test_wake_and_trip_device_knobs_move_their_bases(slug, targets, tmp_path):
    """Plan 12 §6 on WAKE's and TRIP's preset layer: device knob k sets the
    k-th base of the preset's eight — the base, not an offset, whether or
    not a hand also performs it (ARCHITECTURE §3.2) — and the knob is dark
    on the other three party presets (the band strip stays behind SHIFT)."""
    from test_midi import cc

    from hyperspace import preset

    r, _router, presets, midi, inp = desk_rig(tmp_path)
    presets.load(slug.split("-", 1)[1].upper())
    ids = getattr(preset, targets)
    for k, pid in enumerate(ids):
        p = r.reg[pid]
        for value in (0, 127, 64):
            inp.queue.append(cc(0x10 + k, value))
            midi.poll()
            assert p.norm == pytest.approx(value / 127, abs=0.02), (slug, pid, value)
            assert not p.modulated, pid
    presets.load("TUMBLE")
    before = {pid: r.reg[pid].norm for pid in ids}
    inp.queue.append(cc(0x10, 0))
    midi.poll()
    assert {pid: r.reg[pid].norm for pid in ids} == before


def test_hand_lane_numbers_are_the_hands_packages():
    """routing.hand() names the lanes HandsIO publishes on the default dofs."""
    io = HandsIO(HandSettings.from_config(), {"enabled": True}, source=DictSource(),
                 out=NullOut())
    assert list(HAND_AXES) == DEFAULT_DOFS
    for s, side in SIDE.items():
        for axis in HAND_AXES:
            assert hand(s, axis) == f"hand:{io.axis(f'{side}.{axis}')}"


def test_every_party_preset_has_a_preset_a_card_and_only_real_ids(tmp_path):
    """Each preset (library/presets/party-*.json, named by the
    party.hyp.json bank) names only real params, and its performer card
    exists beside the plan."""
    r = rig(tmp_path=tmp_path, full=True)
    ids = set(r.reg.ids())
    doc = json.loads((FACTORY / "projects" / "party.hyp.json").read_text())
    for name in PARTY:
        vals = theme(name)
        assert set(vals) <= ids, (name, set(vals) - ids)
        assert (FACTORY.parents[1] / "docs" / "plans" / "assets" / "12-presets"
                / f"{name}.md").is_file(), name
    for group, file in (("fx", "trip.json"), ("dream", "wake.json")):
        vals = json.loads((FACTORY / group / file).read_text())["values"]
        assert set(vals) <= ids, file
    assert doc["bank"][5:] == [None, None, None]


@pytest.mark.parametrize("name", PARTY)
def test_position_rows_rest_where_their_base_is(name, tmp_path):
    """The B1 rule: a position row's base must equal the value at the axis's
    rest (0.5 on a centred axis, 0 on height), so a hand leaving the box
    lands the same place with or without the fix."""
    r, _ = load(name, tmp_path)
    routes = FACTORY_PRESETS[name].routes()
    for b in routes:
        if b.scheme != "hand" or b.op != "position":
            continue
        p = r.reg[b.target]
        axis = HAND_AXES[b.index % len(HAND_AXES)]
        rest = 0.0 if axis == "y" else 0.5
        assert p.norm == pytest.approx(rest, abs=1e-9), (name, b.target, p.norm)


# ---------------------------------------------------------------- the sweeps

def _hand_rows(name):
    return [b for b in FACTORY_PRESETS[name].routes() if b.scheme == "hand"]


@pytest.mark.parametrize("name", PARTY)
def test_a_hand_never_seen_leaves_every_target_on_its_base(name, tmp_path):
    r, router, src, io = stage(name, tmp_path)
    hold(r, router, src, io, {}, 10)
    for b in _hand_rows(name):
        p = r.reg[b.target]
        assert not p.modulated or offset(p) == pytest.approx(0, abs=1e-6), (name, b.target)


@pytest.mark.parametrize("name", PARTY)
def test_each_hand_axis_moves_its_target_as_the_table_says(name, tmp_path):
    """Sweep every hand row across its axis: at rest the target is the base;
    the ends are on either side of it in the row's sign (a push) or run the
    whole throw from 0 (a position); the move is monotonic; a hand that
    leaves the box brings the base back."""
    for b in _hand_rows(name):
        i = b.index
        s, axis = ("L", "R")[i // len(HAND_AXES)], HAND_AXES[i % len(HAND_AXES)]
        side = SIDE[s]
        readings = []
        for u in (0.0, 0.25, 0.5, 0.75, 1.0):
            r, router, src, io = stage(name, tmp_path)
            p = r.reg[b.target]
            base = p.norm
            hold(r, router, src, io, {side: feats(side, **{axis: u})})
            x = offset(p)
            if p.wrap and readings and readings[-1] > 0 and x == pytest.approx(-0.5, abs=1e-6):
                x = 0.5                     # the far end of a circle, read as +half
            readings.append(x)
            assert p.kind is Kind.CONTINUOUS
        rest = 0 if axis == "y" else 2
        assert readings[rest] == pytest.approx(0, abs=2e-3), (name, b.target, readings)
        sign = 1 if b.value > 0 else -1
        ordered = [sign * x for x in readings]
        assert all(y >= x - 1e-9 for x, y in itertools.pairwise(ordered)), (name, b.target, readings)
        span = ordered[-1] - ordered[0]
        assert span > 0.1, (name, b.target, readings)       # it reads on screen
        if b.op == "position":
            assert abs(readings[-1]) == pytest.approx(1.0 - base, abs=2e-3)
        # the hand at u = 1 leaves the box: the base returns over the spring
        hold(r, router, src, io, {})
        assert offset(p) == pytest.approx(0, abs=2e-3), (name, b.target)


def test_field_height_is_one_gesture_over_three_params(tmp_path):
    """party-field: the right hand's height raises the count, pulls the camera
    back so the grid still fits, and lifts brightness — from one axis."""
    r, router, src, io = stage("party-field", tmp_path)
    n0, z0, b0 = r.view.instances, r.view.zoom, r.view.bright
    hold(r, router, src, io, {"right": feats("right", y=1.0)})
    assert r.view.instances > 60 and r.view.zoom < 0.2 and r.view.bright > b0
    rows = math.ceil(r.view.instances / math.ceil(math.sqrt(r.view.instances)))
    assert r.view.zoom <= 1.0 / (rows * 0.72) * 1.05           # the field fits a 16:9 frame
    hold(r, router, src, io, {})
    assert (r.view.instances, r.view.zoom, r.view.bright) == pytest.approx((n0, z0, b0))


def test_trip_left_height_opens_the_pump_through_lfo_depth(tmp_path):
    """party-trip: LFO 1 (a quarter-note sine) pushes camera.zoom, but its
    depth is 0 until the left hand rises — the chain the plan draws."""
    from hyperspace import lfo, tempo

    r, router, src, io = stage("party-trip", tmp_path)
    clock, lfos = tempo.Clock(now=lambda: src.t), lfo.LFOs()
    lfos[0].sync, lfos[0].shape = r.reg["lfo.1.sync"].value, r.reg["lfo.1.shape"].value
    clock.trigger(0.0)
    zoom = r.reg["camera.zoom"]
    z0 = zoom.norm

    def frames(hands, n):
        seen = []
        for _ in range(n):
            src.t += DT
            src.put(hands)
            io.poll(DT, None, router)
            clock.tick(src.t)
            lfos[0].depth = r.reg["lfo.1.depth"].value
            lfos.step(DT, src.t, clock)
            lfos.publish(router)
            router.modulate()
            r.reg.apply()
            seen.append(zoom.eff_norm - z0)
        return seen

    still = frames({}, 60)
    assert max(abs(x) for x in still) < 1e-9                      # depth 0: no pump
    pumped = frames({"left": feats("left", y=1.0)}, 60)
    assert max(pumped) > 0.03 and min(pumped) < -0.03             # ±0.04 at depth 1
    assert r.reg["lfo.1.depth"].value == pytest.approx(1.0, abs=1e-3)
    gone = frames({}, 90)
    assert abs(gone[-1]) < 1e-6 and r.reg["lfo.1.depth"].value == 0.0
