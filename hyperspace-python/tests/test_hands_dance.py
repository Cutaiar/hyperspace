"""Plan 24 C4 (H2): inputs that reward dancing — `hand:*.curl.<digit>`,
`hand:*.spread`, `hand:*.energy`, `hand:*.flick`, `hands:gap`,
`hands:twist` — routable sources beside the twelve axes, which stay.

The shaping in signal.py (`unit`, `Smooth`, `Flick`), the geometry in
core.py, the layout (the new `hand` lanes after the switches, the `hands`
scheme with its own rests), and the proof the owner asked for: a fixture
preset that routes every new source onto a param, loaded through a scratch
library and played by synthetic hands on a tape — each param moves.
No preset in hyperspace/library/ is touched."""

import math
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from conftest import boot_home
from fake_hands import hand

from hyperspace import hands, ui_routing
from hyperspace.hands import HandSettings, HandsIO, curls, features, skeleton, spread
from hyperspace.hands import core as hc
from hyperspace.hands import signal as hs
from hyperspace.hands import tape as T

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "dance-sources" / "dance-sources.json"
FPS = 90.0

# the twenty-two lanes every rig had before C4, in their places
OLD = ([f"{s}.{a}" for s in hands.SIDES for a in hands.DEFAULTS["dofs"]]
       + ["left.present", "right.present"]
       + [f"{s}.pinch.{f}" for s in hands.SIDES for f in hands.PINCHES])
NEW = [f"{s}.{k}" for s in hands.SIDES for k in
       (*(f"curl.{d}" for d in hc.DIGITS), "spread", "energy", "flick")]


# ---------------------------------------------------------------- shaping

def test_unit_maps_a_range_onto_0_1_clamped():
    assert hs.unit(15.0, 10.0, 20.0) == 0.5
    assert hs.unit(0.0, 10.0, 20.0) == 0.0 and hs.unit(99.0, 10.0, 20.0) == 1.0
    assert hs.unit(5.0, 5.0, 5.0) == 0.0


def test_smooth_starts_on_the_reading_slews_and_forgets_on_none():
    sm = hs.Smooth()
    assert sm.step(0.01, 0.8, 0.05, 0.05) == 0.8          # first sight: no glide in
    y = sm.step(0.05, 0.0, 0.05, 0.05)
    assert y == pytest.approx(0.8 * math.exp(-1.0))       # one time constant down
    assert sm.step(0.01, None, 0.05, 0.05) is None        # the hand left
    assert sm.step(0.01, 0.3, 0.05, 0.05) == 0.3          # and comes back afresh


def test_a_flick_spikes_to_its_strength_holds_its_peak_and_decays():
    fl = hs.Flick()
    kw = {"on": 1500.0, "off": 700.0, "full": 3000.0, "decay_s": 0.15, "ceiling": 10000.0}
    assert fl.step(0.01, 1400.0, **kw) == 0.0             # under the threshold
    assert fl.step(0.01, 2400.0, **kw) == pytest.approx(0.8)
    assert fl.step(0.01, 2700.0, **kw) == pytest.approx(0.9)   # the same move, faster
    peak = fl.y
    assert fl.step(0.15, None, **kw) == pytest.approx(peak * math.exp(-1.0))  # τ = 0.15 s
    # still above `off`: the same hit — nothing new fires however fast
    y = fl.step(0.01, 1000.0, **kw)
    assert y < peak and fl.hit
    fl.step(0.01, 500.0, **kw)                            # under `off`: re-armed
    assert not fl.hit
    assert fl.step(0.01, 1600.0, **kw) == pytest.approx(1600 / 3000)  # a second hit
    fl.reset()
    assert (fl.y, fl.hit) == (0.0, False)
    assert hs.Flick().step(0.01, 50000.0, **kw) == 0.0    # a tracking jump, not a hand


# --------------------------------------------------------------- geometry

@pytest.mark.parametrize("side", hands.SIDES)
def test_an_open_hand_is_uncurled_and_a_fist_is_curled(side):
    assert curls(skeleton(hand(side, "open"))) == {d: 0.0 for d in hc.DIGITS}
    assert curls(skeleton(hand(side, "fist"))) == {d: 1.0 for d in hc.DIGITS}
    assert curls({"digits": []}) == {} and curls(None) == {}


@pytest.mark.parametrize("side", hands.SIDES)
def test_spread_is_the_fan_and_a_fist_does_not_fan(side):
    assert spread(skeleton(hand(side))) == 0.0                     # fingers together
    half = spread(skeleton(hand(side, spread=2.0)))
    assert 0.3 < half < 0.6
    assert spread(skeleton(hand(side, spread=3.0))) == 1.0
    assert spread(skeleton(hand(side, "fist", spread=3.0))) == 0.0
    assert spread({"digits": []}) is None


def test_twist_reads_level_for_mirror_hands_and_up_for_a_clockwise_wheel():
    left, right = features(hand("left")), features(hand("right"))
    assert hc.twist(left, right) == 0.5
    # a clap: both thumbs up, palms facing — still mirror images
    assert hc.twist(features(hand("left", roll=90)), features(hand("right", roll=90))) == 0.5
    # a wheel turned clockwise as the performer sees it: the right thumb
    # rises, the left thumb drops — 45° each, 90° apart: the top of the range
    wheel = hc.twist(features(hand("left", roll=-45)), features(hand("right", roll=45)))
    assert wheel == pytest.approx(1.0)
    assert hc.twist(features(hand("left", roll=20)), features(hand("right", roll=-20))) == \
        pytest.approx(0.5 - 40 / 180)
    assert hc.twist({"roll": 0.0}, {}) is None


def test_gap_is_the_palms_distance():
    a = features(hand("left", at=(-80.0, 200.0, 0.0)))
    b = features(hand("right", at=(80.0, 200.0, 0.0)))
    assert hc.gap(a, b) == pytest.approx((160 - 60) / 540)
    assert hc.gap(a, {"x": 1.0}) is None


# ----------------------------------------------------------------- layout

def test_the_new_lanes_follow_the_switches_and_no_older_lane_moves():
    """`hand:<i>` from an older preset still reads the lane it did: the
    twenty-two come first, unchanged, then each hand's eight dance lanes."""
    names = hands.default_addresses()
    assert names[:22] == OLD and names[22:] == NEW
    lay = hands.Layout(HandSettings.from_config({}).axes)
    assert lay.n == 38 == len(lay.names) and lay.addresses == names
    assert lay.names[22:30] == ["L curl thu", "L curl ind", "L curl mid", "L curl rin",
                                "L curl pin", "L spread", "L energy", "L flick"]
    assert all(lay.dance[(s, k)] == names.index(f"{s}.{k}")
               for s in hands.SIDES for k in hands.DANCE)
    assert lay.pair_addresses == hands.pair_addresses() == ["gap", "twist"]
    assert lay.pair_index == {"gap": 0, "twist": 1} and lay.pair_names == ["gap", "twist"]


class Router:
    def __init__(self):
        self.labels, self.names, self.gates, self.rests, self.fed = {}, {}, {}, {}, {}

    def feed(self, scheme, values):
        self.fed[scheme] = values


def test_the_hands_scheme_is_published_like_the_hand_one():
    r = _rig()
    router = Router()
    _play(r, 1, router)
    lay = r.io.layout
    assert router.labels["hands"] is lay.pair_names and router.names["hands"] is lay.pair_index
    assert router.gates["hands"] == []                    # no switches among them
    assert router.rests["hands"] == [0.0, 0.5]            # gap closed, twist level
    assert router.rests["hand"][22:] == [0.0] * 16        # the dance lanes rest at 0
    assert len(router.fed["hand"]) == 38 and len(router.fed["hands"]) == 2
    # a source that is not live: both schemes let go
    r.io.source = NS(on=False, status="lost", latest=lambda: (0, 0.0, {}))
    _play(r, 2, router)
    assert router.fed["hand"] is None and router.fed["hands"] is None


# ------------------------------------------------- the tape and the scratch library

def _frames():
    """Two hands on a tape, frame by frame at 90 fps (k = frame):

      0–29   both open and still, 160 mm apart, level; the right fanned (spread 2)
      30–39  the right hand away
      40–79  the right back as a fist, rolling up to 40°; the left fans
             its fingers out over 40–59 and rises 6 mm a frame
      80–81  the right hand flicks: 30 mm out and back
      82–94  both still, but for the left hand flicking 25 mm down and up at 90
      95–99  the left hand away
      100–109 the left back as a fist, still
      110–   no hands

    A grip that changes in one frame would be a flick, so the fists come
    in from out of view (a returning hand measures no speed on its first
    frame)."""
    out = []
    for k in range(120):
        hs_ = []
        if k < 110:
            ly = 200.0 + 6.0 * (min(max(k, 40), 80) - 40) - (25.0 if k == 90 else 0.0)
            sp = 1.0 + 0.1 * (min(max(k, 40), 60) - 40)
            if not 95 <= k < 100:
                grip = "fist" if k >= 100 else "open"
                hs_.append(hand("left", grip, (-80.0, ly, 0.0), spread=sp))
            if k < 30:
                hs_.append(hand("right", "open", (80.0, 200.0, 0.0), spread=2.0))
            elif k >= 40:
                rx = 110.0 if k == 80 else 80.0
                roll = min(40.0, 2.0 * (k - 40))
                hs_.append(hand("right", "fist", (rx, 200.0, 0.0), roll=roll))
        out.append({"t": k / FPS, "hands": {
            h.type.name.lower(): {"features": features(h), "confidence": 1.0,
                                  "skeleton": skeleton(h)} for h in hs_}})
    return out


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture(scope="module")
def tape_path(tmp_path_factory):
    """The tape through the tape machinery: saved, then loaded by the source."""
    path = tmp_path_factory.mktemp("tape") / "dance.json"
    T.save({"schema": T.TAPE_SCHEMA, "mode": "desktop", "frames": _frames()}, path)
    return path


def _rig(path=None):
    clock = Clock()
    src = T.TapeSource(T.load(path) if path else
                       {"schema": T.TAPE_SCHEMA, "mode": "desktop", "frames": _frames()},
                       clock, loop=False)
    io = HandsIO(HandSettings.from_config({}), {"out": ""}, source=src,
                 out=NS(send=lambda m: None), clock=clock)
    return NS(io=io, clock=clock, k=-1)


def _play(r, upto, router=None, after=None):
    """Render frames on the tape's own clock, one tracking frame each,
    up to and including frame `upto`; `after` runs after each."""
    while r.k < upto:
        r.k += 1
        r.clock.t = r.k / FPS + 1e-3       # past the saved (1e-4-rounded) frame time
        r.io.poll(1 / FPS, None, router)
        if after is not None:
            after(r.k)


ROUTES = {                    # the fixture's rows: source → the param it positions
    "hand:left.curl.thumb": "rot.rate.XY", "hand:left.curl.index": "rot.rate.XZ",
    "hand:left.curl.middle": "rot.rate.YZ", "hand:left.curl.ring": "rot.rate.XW",
    "hand:left.curl.pinky": "rot.rate.YW", "hand:right.curl.thumb": "rot.rate.ZW",
    "hand:right.curl.index": "pattern.mod.0", "hand:right.curl.middle": "pattern.mod.1",
    "hand:right.curl.ring": "pattern.mod.2", "hand:right.curl.pinky": "pattern.mod.3",
    "hand:left.spread": "pattern.mod.4", "hand:right.spread": "pattern.mod.5",
    "hand:left.energy": "view.inst_amp", "hand:right.energy": "view.speed",
    "hand:left.flick": "view.bright", "hand:right.flick": "dream.mix",
    "hands:gap": "camera.zoom", "hands:twist": "camera.yaw",
}


@pytest.fixture()
def show(tmp_path, tape_path):
    """The fixture preset in a scratch library (never the owner's), loaded
    the way a pad or the strip loads a preset, the hands on the tape."""
    home = tmp_path / "home"
    (home / "presets").mkdir(parents=True)
    shutil.copyfile(FIXTURE, home / "presets" / FIXTURE.name)
    app = boot_home(home)
    assert app.presets.load(FIXTURE.stem) == []
    assert app.presets.notes == [] and app.router.table.dropped == []
    return NS(app=app, r=_rig(tape_path))


def test_the_fixture_routes_every_new_source_once():
    import json

    rows = json.loads(FIXTURE.read_text())["routes"]
    assert {r["source"]: r["target"] for r in rows} == ROUTES
    assert {r["source"] for r in rows} == {f"hand:{n}" for n in NEW} | {
        f"hands:{n}" for n in hands.PAIR}
    assert all(r["op"] == "position" for r in rows)


def test_every_new_source_moves_its_param_through_a_scratch_library(show):
    """Each row is a `position` at depth 1: the param's effective value is
    the source's reading. Every one moves, the bases never do, and when
    the hands leave every row lets go."""
    app, r = show.app, show.r
    reg, router = app.reg, app.router
    assert len(router.table.routes()) == len(ROUTES)
    assert all(router.table.owner(t).source == s for s, t in ROUTES.items())
    base = {t: reg[t].norm for t in ROUTES.values()}
    seen: dict[str, list[float | None]] = {s: [] for s in ROUTES}

    def frame(k):
        router.modulate(dt=1 / FPS)
        reg.apply()
        for s, t in ROUTES.items():
            p = reg[t]
            seen[s].append(p.eff_norm if p.modulated else None)

    _play(r, 119, router, frame)
    eff = lambda s, k: seen[s][k]
    # 0–29: open, still, level, 160 mm apart; the right fanned
    for s in ROUTES:
        if s.startswith("hand:") and s != "hand:right.spread":
            assert eff(s, 29) == pytest.approx(0.0, abs=0.01), s
    assert eff("hand:right.spread", 29) == pytest.approx(spread(skeleton(
        hand("right", spread=2.0))), abs=1e-3)
    assert eff("hands:gap", 29) == pytest.approx((160 - 60) / 540, abs=1e-3)
    assert eff("hands:twist", 29) == pytest.approx(0.5, abs=1e-3)
    # 30–39: the right away — its rows and the pair's let go, the left's hold on
    for s in ROUTES:
        if s.startswith(("hand:right.", "hands:")):
            assert eff(s, 35) is None, s
        else:
            assert eff(s, 35) is not None, s
    # 79: the right a fist, rolled 40°; the left fanned and rising
    for d in hc.DIGITS:
        assert eff(f"hand:right.curl.{d}", 79) == pytest.approx(1.0, abs=1e-3)
        assert eff(f"hand:left.curl.{d}", 79) < 0.2
    assert eff("hand:left.spread", 79) == pytest.approx(1.0, abs=0.01)    # still settling
    assert eff("hand:right.spread", 79) == pytest.approx(0.0, abs=1e-3)   # a fist
    # 540 mm/s, the energy still falling (decay 0.5 s) from the fan's faster tips
    assert eff("hand:left.energy", 79) == pytest.approx((540 - 60) / 940, abs=0.05)
    assert eff("hand:right.energy", 79) < 0.3
    assert eff("hand:left.flick", 79) == eff("hand:right.flick", 79) == 0.0
    assert eff("hands:twist", 79) == pytest.approx(0.5 + 40 / 180, abs=1e-3)
    # the gap grows ~5 mm a frame: its smoothing (τ 0.05 s) runs ~20 mm behind
    gap = (math.dist((-80.0, 200.0 + 6 * 39), (80.0, 200.0)) - 60) / 540
    assert eff("hands:gap", 79) == pytest.approx(gap, abs=0.05)
    assert eff("hands:gap", 79) > eff("hands:gap", 29) + 0.15
    # 80–81: the right flicks (2700 mm/s), a hit; then it decays at τ = 0.15 s
    hit = eff("hand:right.flick", 81)
    assert hit == pytest.approx(2700 / 3000, abs=0.02)
    later = eff("hand:right.flick", 81 + 27)                       # 0.3 s on
    assert later == pytest.approx(hit * math.exp(-0.3 / 0.15), rel=0.02)
    assert eff("hand:left.flick", 81) == 0.0
    # 81–89: the left still (its last step up was frame 80) — its energy
    # falls at the decay, 0.5 s
    assert eff("hand:left.energy", 89) == pytest.approx(
        eff("hand:left.energy", 80) * math.exp(-9 / FPS / 0.5), rel=0.02)
    # 90–91: the left flicks (25 mm in a frame: 2250 mm/s) — one hit, not two
    assert eff("hand:left.flick", 89) == 0.0
    assert eff("hand:left.flick", 91) == pytest.approx(2250 / 3000, abs=0.02)
    assert eff("hand:left.flick", 92) < eff("hand:left.flick", 91)
    # 100–109: the left back as a fist, and no flick for its return
    for d in hc.DIGITS:
        assert eff(f"hand:left.curl.{d}", 109) == pytest.approx(1.0, abs=1e-3)
    assert eff("hand:left.flick", 109) == 0.0 and eff("hand:left.energy", 109) == 0.0
    # every row moved its param at some point …
    for s, ys in seen.items():
        vals = [y for y in ys if y is not None]
        assert max(vals) - min(vals) > 0.1, s
    # … and none is left holding one once the hands are gone; no base moved
    for s, t in ROUTES.items():
        assert seen[s][-1] is None and not reg[t].modulated, s
        assert reg[t].norm == pytest.approx(base[t]), t


def test_the_routing_page_offers_the_new_sources_by_name(show):
    app, r = show.app, show.r
    _play(r, 50, app.router)
    panel = NS(audio=NS(chain=NS(band_names=["sub"])))
    srcs = dict(ui_routing._sources(panel, app.router))
    assert srcs["hands:gap"] == "hands gap" and srcs["hands:twist"] == "hands twist"
    assert srcs["hand:right.curl.index"] == "hand R curl ind"
    assert srcs["hand:left.flick"] == "hand L flick"
    table = app.router.table
    assert app.router.describe(table.owner("camera.yaw")) == "twist positions"
    assert app.router.describe(table.owner("view.speed")) == "R energy positions"


def test_the_twelve_axes_presence_and_pinches_are_where_they_were(tape_path):
    """The first twenty-two lanes of a frame are the axes, presence and
    switches, in the places and with the values they always had."""
    r = _rig(tape_path)
    _play(r, 50)
    lanes, lay = r.io.lanes(), r.io.layout
    assert lanes[:12] == [st.y for st in r.io.state]       # both hands in: every axis live
    assert (lay.presence["left"], lay.presence["right"]) == (12, 13)
    assert lanes[12:14] == [1.0, 1.0]
    assert [lay.gate[(s, f)] for s in hands.SIDES for f in hands.PINCHES] == list(range(14, 22))
    assert lanes[14:22] == [1.0 if r.io.gates[s][f].on else 0.0
                            for s in hands.SIDES for f in hands.PINCHES]


def test_a_palm_only_source_reads_nan_curls_but_still_has_energy():
    """No skeleton (a palm-only tracker, the boundary test's): the curls
    and the spread read NaN — no reading, not a fake 0 — while energy and
    flick watch the palm, and the pair still reads."""
    clock = Clock()

    class Palms:
        status, on = "fake", True
        seq = 0

        def latest(self):
            self.seq += 1
            x = 3.0 * self.seq
            return self.seq, clock(), {
                "left": ({**features(hand("left", at=(-80.0 + x, 200.0, 0.0)))}, 1.0),
                "right": ({**features(hand("right", at=(80.0, 200.0, 0.0)))}, 1.0)}

    io = HandsIO(HandSettings.from_config({}), {"out": ""}, source=Palms(),
                 out=NS(send=lambda m: None), clock=clock)
    for k in range(20):
        clock.t = k / FPS
        io.poll(1 / FPS)
    lanes, lay = io.lanes(), io.layout
    assert all(math.isnan(lanes[lay.dance[("left", f"curl.{d}")]]) for d in hc.DIGITS)
    assert math.isnan(lanes[lay.dance[("left", "spread")]])
    assert lanes[lay.dance[("left", "energy")]] == pytest.approx((270 - 60) / 940, abs=0.01)
    assert lanes[lay.dance[("right", "energy")]] == pytest.approx(0.0)
    assert lanes[lay.dance[("left", "flick")]] == 0.0
    assert not any(math.isnan(v) for v in io.pair_lanes())


def test_the_hands_page_shows_every_new_source(monkeypatch, tmp_path):
    """The HANDS page draws a bar per dance source, live, beside the box,
    inside the window — and still does not scroll."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig, frame

    import hyperspace.hands.panel as hp
    from hyperspace.app import CONTROL_SIZE

    with build_rig(tmp_path) as rig:
        r = _rig()
        _play(r, 79)
        rig.panel.hands = r.io
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        drawn: list[tuple[str, float, float]] = []
        real = hp._dance_bar

        def bar(address, v, h, **kw):
            x = imgui.get_cursor_screen_pos().x
            drawn.append((address, v, x + hp.DANCE_BAR_W))
            real(address, v, h, **kw)

        monkeypatch.setattr(hp, "_dance_bar", bar)
        for _ in range(3):
            drawn.clear()
            frame(rig.panel, "hands")
        got = {a: v for a, v, _ in drawn}
        assert set(got) == {f"hand:{n}" for n in NEW} | {"hands:gap", "hands:twist"}
        assert got["hand:right.curl.index"] == pytest.approx(1.0, abs=1e-3)
        assert max(x for *_, x in drawn) <= CONTROL_SIZE[0]
