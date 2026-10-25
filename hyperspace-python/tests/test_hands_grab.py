"""Plan 24 C5 (H1): cause and effect — the grab switch.

`hand:<side>.grab` is a closed fist read from C4's per-finger curls
(`hands.fist`) through a `Gate` — Schmitt + debounce like the pinches —
published as a gate like them, after every older lane, and shown on the
HANDS page. The proof the owner asked for: their intended mapping
(`position` rows from the right hand's yaw / pitch / roll onto
`camera.yaw`, `camera.pitch` and `rot.phase.XY`, each gated by the grab)
is a fixture preset, loaded through a scratch library and played by
synthetic hands on a tape: the shape follows the hand only while it is
closed. No preset in hyperspace/library/ is touched."""

import json
import math
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from conftest import boot_home
from fake_hands import hand

from hyperspace import hands, ui_routing
from hyperspace.hands import Gate, HandSettings, HandsIO, curls, features, fist, skeleton
from hyperspace.hands import core as hc
from hyperspace.hands import tape as T

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "grab-follow" / "grab-follow.json"
FPS = 90.0
ROUTES = {"hand:right.yaw": "camera.yaw", "hand:right.pitch": "camera.pitch",
          "hand:right.roll": "rot.phase.XY"}


# ------------------------------------------------------------- the reading

@pytest.mark.parametrize("side", hands.SIDES)
def test_a_fist_reads_1_an_open_hand_0_and_the_thumb_is_left_out(side):
    assert fist(curls(skeleton(hand(side, "open")))) == 0.0
    assert fist(curls(skeleton(hand(side, "fist")))) == 1.0
    half = fist(curls(skeleton(hand(side, close=0.5))))
    assert 0.45 < half < 0.65                     # between the two thresholds
    c = curls(skeleton(hand(side, "fist")))
    assert fist({**c, "thumb": 0.0}) == 1.0       # thumb out: still a fist
    assert fist({**c, "pinky": 0.0}) == 0.75      # the four fingers' mean
    assert fist({}) is None and fist(None) is None
    assert fist({**c, "ring": math.nan}) is None


def _step(gate, level, t):
    return hc.step_grab(gate, {f: level for f in hc.GRAB_FINGERS}, t)


def test_the_grab_is_a_schmitt_trigger_with_a_debounce():
    g, hold = Gate(), hc.GRAB_HOLD_S
    assert not _step(g, hc.GRAB_CLOSE - 0.01, 0.0)          # nearly a fist: open
    assert not _step(g, hc.GRAB_CLOSE + 0.01, 0.1)          # closes … after the hold
    assert not _step(g, 1.0, 0.1 + hold / 2)
    assert _step(g, 1.0, 0.1 + hold)
    # in the gap between the two thresholds it stays closed: no chatter
    assert _step(g, (hc.GRAB_CLOSE + hc.GRAB_OPEN) / 2, 0.2)
    assert _step(g, hc.GRAB_OPEN, 0.3)
    # one frame open is not a release; a held one is
    assert _step(g, 0.0, 0.4) and _step(g, 1.0, 0.41) and _step(g, 1.0, 0.5)
    assert _step(g, 0.0, 0.6) and not _step(g, 0.0, 0.6 + hold)
    # no reading (no skeleton): the switch holds where it is
    assert not hc.step_grab(g, {}, 0.7) and not hc.step_grab(g, None, 0.8)
    assert hc.GRAB_OPEN < hc.GRAB_CLOSE


# ----------------------------------------------------------------- layout

def test_the_grab_lanes_follow_every_older_lane():
    """`hand:<i>` from an older preset still reads the lane it did: the
    thirty-eight lanes before C5 keep their places, the two grabs follow."""
    names = hands.default_addresses()
    lay = hands.Layout(HandSettings.from_config({}).axes)
    assert names[38:] == ["left.grab", "right.grab"] == [hands.grab_name(s) for s in hands.SIDES]
    assert (lay.grab["left"], lay.grab["right"]) == (38, 39) and lay.n == 40
    assert lay.names[38:] == ["L grab", "R grab"]
    assert names[:38][-1] == "right.flick" and names[14:22][0] == "left.pinch.index"
    # published as gates like the pinches, after them
    assert lay.gates[:8] == [(lay.gate[(s, f)], lay.names[lay.gate[(s, f)]])
                             for s in hands.SIDES for f in hands.PINCHES]
    assert lay.gates[8:] == [(38, "L grab"), (39, "R grab")]
    # a shorter dofs list moves every lane after the axes, the grabs too:
    # the counts are derived, never pinned
    short = hands.Layout(HandSettings.from_config({"dofs": ["x"]}).axes)
    assert short.n == lay.n - 10 and short.grab["right"] == short.n - 1


# ------------------------------------------------------------- the tape

def _frames():
    """The right hand on a tape at 90 fps (k = frame); the left away:

      0–29    open, level
      30–59   open, rolling up to 30°            the grab stays open
      60–64   most of the way closed (0.6)       under GRAB_CLOSE: still open
      65–99   a fist, rolling 30° → 60°          closes after the hold (k 70)
      100–109 loosened to 0.5                    between the thresholds: held
      110     open for one frame                 the debounce: held
      111–114 a fist again
      115–129 open, rolling back to 0°           lets go after the hold (k 120)
      130–139 a fist                             closes again (k 135)
      140–    no hands                           drops at once
    """
    out = []
    for k in range(150):
        hs_ = []
        if k < 140:
            roll = (0.0 if k < 30 else min(30.0, k - 30) if k < 65
                    else 30.0 + min(30.0, k - 65) if k < 115 else max(0.0, 60.0 - 4 * (k - 115)))
            close = (0.0 if k < 60 else 0.6 if k < 65 else 1.0 if k < 100
                     else 0.5 if k < 110 else 0.0 if k == 110 else 1.0 if k < 115
                     else 0.0 if k < 130 else 1.0)
            hs_.append(hand("right", "fist" if close == 1.0 else "open", (80.0, 200.0, 0.0),
                            roll=roll, close=close))
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
    path = tmp_path_factory.mktemp("tape") / "grab.json"
    T.save({"schema": T.TAPE_SCHEMA, "mode": "desktop", "frames": _frames()}, path)
    return path


def _rig(path, cfg=None):
    clock = Clock()
    src = T.TapeSource(T.load(path), clock, loop=False)
    io = HandsIO(HandSettings.from_config(cfg or {}), {"out": ""}, source=src,
                 out=NS(send=lambda m: None), clock=clock)
    return NS(io=io, clock=clock, k=-1)


def _play(r, upto, router=None, after=None):
    while r.k < upto:
        r.k += 1
        r.clock.t = r.k / FPS + 1e-3
        r.io.poll(1 / FPS, None, router)
        if after is not None:
            after(r.k)


def test_the_grab_lane_closes_with_a_fist_and_holds_through_noise(tape_path):
    r = _rig(tape_path)
    seen = []
    _play(r, 149, after=lambda k: seen.append(
        (r.io.lanes()[r.io.layout.grab["right"]], r.io.lanes()[r.io.layout.grab["left"]])))
    right = [v for v, _ in seen]
    on = [k for k in range(1, len(right)) if right[k] == 1.0 and right[k - 1] == 0.0]
    off = [k for k in range(1, len(right)) if right[k] == 0.0 and right[k - 1] == 1.0]
    assert on == [70, 135]                # each after the debounce, nowhere else
    assert off == [120, 140]              # opened (after the hold); the hand left (at once)
    assert all(v == 0.0 for _, v in seen)     # the left hand never came
    # the grab is a switch, not a pinch: the pinches never moved
    assert r.io.lanes()[14:22] == [0.0] * 8


def test_a_palm_only_source_never_grabs():
    """No skeleton, no curls: the grab holds open, it is never guessed."""
    clock = Clock()

    class Palms:
        status, on, seq = "fake", True, 0

        def latest(self):
            self.seq += 1
            return self.seq, clock(), {"right": (features(hand("right", "fist")), 1.0)}

    io = HandsIO(HandSettings.from_config({}), {"out": ""}, source=Palms(),
                 out=NS(send=lambda m: None), clock=clock)
    for k in range(30):
        clock.t = k / FPS
        io.poll(1 / FPS)
    assert io.present["right"] and io.lanes()[io.layout.grab["right"]] == 0.0


# --------------------------------------------- the owner's mapping, through a scratch library

@pytest.fixture()
def show(tmp_path, tape_path):
    """The fixture preset in a scratch library (never the owner's), loaded
    the way a pad or the strip loads a preset, the hand on the tape."""
    home = tmp_path / "home"
    (home / "presets").mkdir(parents=True)
    shutil.copyfile(FIXTURE, home / "presets" / FIXTURE.name)
    app = boot_home(home)
    assert app.presets.load(FIXTURE.stem) == []
    assert app.presets.notes == [] and app.router.table.dropped == []
    return NS(app=app, r=_rig(tape_path))


def test_the_fixture_is_the_owners_grab_mapping():
    rows = json.loads(FIXTURE.read_text())["routes"]
    assert {r["source"]: r["target"] for r in rows} == ROUTES
    assert all(r["op"] == "position" and r["when"] == "hand:right.grab" for r in rows)


def test_the_shape_follows_the_hand_only_while_it_is_closed(show):
    """Open, the rows are shut and the params sit on their bases; a fist
    and the camera and the XY plane follow the hand's pose, the plane
    turning with the roll; open it and they let go to their bases."""
    app, r = show.app, show.r
    reg, router = app.reg, app.router
    assert all(router.table.owner(t).source == s for s, t in ROUTES.items())
    base = {t: reg[t].norm for t in ROUTES.values()}
    seen: dict[str, list[float | None]] = {t: [] for t in ROUTES.values()}

    def frame(k):
        router.modulate(dt=1 / FPS)
        reg.apply()
        for t in ROUTES.values():
            p = reg[t]
            seen[t].append(p.eff_norm if p.modulated else None)

    _play(r, 149, router, frame)
    roll = seen["rot.phase.XY"]
    # 0–69: open (and nearly closed) — rolling the hand moves nothing
    for t in ROUTES.values():
        assert all(v is None for v in seen[t][:70]), t
    # 70–119: closed — every row acts; the plane follows the roll up
    for t in ROUTES.values():
        assert all(v is not None for v in seen[t][70:120]), t
    assert roll[99] > roll[71] + 0.05                   # rolled 30° → 60° while held
    # the hand level in yaw and pitch: the camera sits where the hand says
    assert seen["camera.yaw"][99] == pytest.approx(0.5, abs=0.02)
    assert seen["camera.pitch"][99] == pytest.approx(0.5, abs=0.02)
    # 120–134: opened — let go, whatever the hand does
    for t in ROUTES.values():
        assert all(v is None for v in seen[t][120:135]), t
    # 135–139: closed again; 140–: the hand gone — let go
    assert all(v is not None for v in roll[135:140])
    for t in ROUTES.values():
        assert seen[t][-1] is None and not reg[t].modulated, t
        assert reg[t].norm == pytest.approx(base[t]), t      # no base ever moved


def test_the_routing_page_offers_the_grab_as_a_gate(show):
    app, r = show.app, show.r
    _play(r, 10, app.router)
    gates = dict(ui_routing._gates(app.router))
    assert gates["hand:left.grab"] == "L grab" and gates["hand:right.grab"] == "R grab"
    assert gates["hand:right.pinch.index"] == "R ind"           # the pinches as before
    desc = app.router.describe(app.router.table.owner("rot.phase.XY"))
    assert desc.endswith("while R grab")


# ---------------------------------------------------------------- the page

def test_the_hands_page_shows_the_grab_switches(monkeypatch, tmp_path, tape_path):
    """Each hand's grab on its curl row in the dance column, lit while
    closed, inside the window's width."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig, frame

    import hyperspace.hands.panel as hp
    from hyperspace.app import CONTROL_SIZE

    with build_rig(tmp_path) as rig:
        r = _rig(tape_path)
        _play(r, 99)                       # the right hand a closed fist
        rig.panel.hands = r.io
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        drawn: list[tuple[str, float, float]] = []
        real = hp._grab

        def grab(io, side, v):
            real(io, side, v)
            drawn.append((side, v, imgui.get_item_rect_max().x))

        monkeypatch.setattr(hp, "_grab", grab)
        for _ in range(3):
            drawn.clear()
            frame(rig.panel, "hands")
        assert [(s, v) for s, v, _ in drawn] == [("left", 0.0), ("right", 1.0)]
        assert max(x for *_, x in drawn) <= CONTROL_SIZE[0]


def test_a_short_dofs_list_does_not_run_into_the_dance_column(monkeypatch, tmp_path):
    """With fewer axis rows than the dance column has lines, what follows
    the rows (the selected axis's editor) starts below the column."""
    from imgui_bundle import imgui
    from test_ui_shell import FakeLeap, build_rig, frame

    import hyperspace.hands.panel as hp
    from hyperspace.app import CONTROL_SIZE

    with build_rig(tmp_path) as rig:
        settings = HandSettings.from_config({"dofs": ["x"]})          # two rows
        rig.panel.hand_settings = settings
        rig.panel.hands = HandsIO(settings, {"out": ""}, source=FakeLeap(),
                                  out=NS(send=lambda m: None), clock=lambda: 0.0)
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        at: dict[str, float] = {}
        real_dance, real_editor = hp._dance, hp._editor

        def dance(io, h):
            real_dance(io, h)
            at["column"] = imgui.get_item_rect_max().y

        def editor(*a, **kw):
            at["editor"] = imgui.get_cursor_screen_pos().y
            real_editor(*a, **kw)

        monkeypatch.setattr(hp, "_dance", dance)
        monkeypatch.setattr(hp, "_editor", editor)
        for _ in range(2):
            frame(rig.panel, "hands")
        assert at["editor"] >= at["column"]
