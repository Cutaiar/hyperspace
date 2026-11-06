"""The sticks as dials (gamepad.dial, plan 28): a stick's angle picks one of eight
sectors clockwise from straight up, its distance from centre is how far that sector's
`axis` lane reads: petal (hard sectors, a sticky border) or blend (neighbours crossfade),
each `Deck`'s loadable patch's (`pad.dial.*`), read by a pad from the `Deck` it drives. A
route on a dial lane plays like any other `axis` route, taking its whole stick off the
camera job. The pad node on GRAPH draws the dials."""

import json
import math
from types import SimpleNamespace as NS

import pytest
from conftest import seed
from test_pad_learn import ScriptedPad, rig  # noqa: F401 — the fixture, re-exported
from test_routing import rig as full_rig
from test_undo import boot

import hyperspace.gamepad as gp
from hyperspace import app, lfo, params, patches
from hyperspace.deck import Deck, MetaController
from hyperspace.loadable import LoadedPatch
from hyperspace.params import Registry, build_meta, dial_id, part_of
from hyperspace.routing import Binding, Bindings, Router, is_meta_row, meta_row_refusal


def at(deg: float, r: float = 1.0) -> tuple[float, float]:
    """(x, y) — right and up — of a stick `deg` clockwise from straight up."""
    t = math.radians(deg)
    return r * math.sin(t), r * math.cos(t)


def lane(name: str) -> int:
    return gp.LANES.index(name)


# ---- the clock ----

def test_at_rest_every_lane_is_zero():
    for mode in gp.DIAL_MODES:
        assert gp.dial(0.0, 0.0, mode) == ([0.0] * gp.DIAL, None)
        assert gp.dial(*at(30, gp.DEADZONE * 0.9), mode) == ([0.0] * gp.DIAL, None)


def test_sectors_run_clockwise_from_straight_up():
    for k, deg in enumerate(range(0, 360, 45)):
        vals, sector = gp.dial(*at(deg), "petal")
        assert sector == k and vals[k] == pytest.approx(1.0), gp.COMPASS[k]
    assert gp.COMPASS[gp.dial(1.0, 0.0)[1]] == "E"         # right is three o'clock


def test_the_radius_runs_zero_to_one_past_the_deadzone_and_stops_at_the_rim():
    half = gp.DEADZONE + 0.5 * (1 - gp.DEADZONE)
    assert gp.dial(*at(0, half))[0][0] == pytest.approx(0.5)
    assert gp.dial(1.0, 1.0)[0][1] == pytest.approx(1.0)    # a square gate's corner


def test_petal_gives_the_whole_push_to_one_sector():
    vals, sector = gp.dial(*at(60, 0.8), "petal")
    assert sector == 1 and [v > 0 for v in vals].count(True) == 1


def test_a_petal_border_is_sticky():
    """22.5° is the border between N and NE: held on N, a stick a little
    past it stays N, one well past it is NE — and NE is as sticky back."""
    assert gp.dial(*at(25), "petal", held=0)[1] == 0
    assert gp.dial(*at(25), "petal", held=None)[1] == 1
    assert gp.dial(*at(35), "petal", held=0)[1] == 1
    assert gp.dial(*at(20), "petal", held=1)[1] == 1
    assert gp.dial(*at(-25), "petal", held=0)[1] == 0      # and across the wrap
    assert gp.dial(*at(-35), "petal", held=0)[1] == 7


def test_blend_crossfades_neighbours_and_sums_to_the_radius():
    vals, _ = gp.dial(*at(0), "blend")
    assert vals[0] == pytest.approx(1.0) and sum(vals) == pytest.approx(1.0)
    vals, _ = gp.dial(*at(22.5), "blend")                    # halfway N → NE
    assert vals[0] == pytest.approx(0.5) and vals[1] == pytest.approx(0.5)
    vals, _ = gp.dial(*at(-11.25, 0.6), "blend")             # a quarter into NW
    assert vals[0] > vals[7] > 0 and sum(vals) == pytest.approx(gp.dial(*at(0, 0.6))[0][0])


# ---- the pad ----

def test_the_dial_lanes_follow_the_axes():
    pad = ScriptedPad()
    pad.frame(axes=[0.0, -1.0, 1.0, 0.0, -1.0, -1.0])      # left up, right to the right
    lanes = pad.lanes()
    assert len(lanes) == len(gp.LANES) == len(gp.LANE_RESTS) == len(gp.LANE_LABELS)
    assert lanes[lane("L.N")] == pytest.approx(1.0) and lanes[lane("R.E")] == pytest.approx(1.0)
    assert sum(lanes[6:]) == pytest.approx(2.0)
    pad.frame()
    assert pad.lanes()[6:] == [0.0] * len(gp.DIAL_LANES)


def test_the_mode_is_per_stick():
    pad = ScriptedPad()
    pad.dial_modes = {"L": "blend", "R": "petal"}
    x, y = at(22.5)
    pad.frame(axes=[x, -y, x, -y, -1.0, -1.0])
    lanes = pad.lanes()
    assert lanes[lane("L.N")] == pytest.approx(0.5)          # blend: shared
    assert {lanes[lane("R.N")], lanes[lane("R.NE")]} == {0.0, 1.0}   # petal: one


def test_a_dial_lane_claims_its_whole_stick():
    assert gp.claims({lane("L.SW")}) == {gp.AX_LX, gp.AX_LY}
    assert gp.claims({lane("R.N"), gp.AX_LT}) == {gp.AX_RX, gp.AX_RY, gp.AX_LT}
    assert gp.dialed({lane("R.N"), gp.AX_LX}) == {"R"}


# ---- routes and learn ----

def test_a_dial_route_pushes_its_param_from_the_base(rig):  # noqa: F811
    pad, r = ScriptedPad(), rig.router
    gp.publish(r)                    # the pad's lane names (the pad device does it first)
    rig.table.add(Binding("axis:L.E", "view.inst_amp", "push", 1.0))
    assert gp.claims(r.claimed("axis")) == {gp.AX_LX, gp.AX_LY}
    assert r.describe(rig.table.owner("view.inst_amp")).startswith("left dial E")
    amp = rig.reg["view.inst_amp"]
    base = amp.value
    pad.frame()
    r.pad(pad)
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(base)                  # at rest: the base
    pad.frame(axes=[0.5 + 0.5 * gp.DEADZONE, 0.0, 0.0, 0.0, -1.0, -1.0])   # halfway right
    r.pad(pad)
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(base + 0.5 * (amp.hi - amp.lo))


def test_a_dialed_stick_learns_the_sector_it_points_into(rig):  # noqa: F811
    pad, lrn = ScriptedPad(), rig.learn
    pad.frame()
    lrn.arm("view.inst_amp", "pad")
    x, y = at(135)
    pad.frame(axes=[x, -y, 0.0, 0.0, -1.0, -1.0])            # down-right
    gp.learn_from(pad, lrn, dials=lambda: {"L"})
    assert [(b.source, b.target) for b in rig.table.routes()] == [("axis:L.SE", "view.inst_amp")]


def test_a_stick_that_is_no_dial_still_learns_its_axis(rig):  # noqa: F811
    pad, lrn = ScriptedPad(), rig.learn
    pad.frame()
    lrn.arm("view.inst_amp", "pad")
    pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
    gp.learn_from(pad, lrn)
    assert [b.source for b in rig.table.routes()] == ["axis:LX"]


def test_the_dial_preset_fills_both_clocks(tmp_path):
    seed(tmp_path)                        # the corpus: DIAL among the shipped loadable patches
    r = full_rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings())
    assert LoadedPatch(r.lib, r.reg, router).load("DIAL") == []
    assert router.table.dropped == []
    dialed = {b.source for b in router.table.routes() if b.scheme == "axis"}
    assert dialed == {f"axis:{n}" for n in gp.DIAL_LANES}
    assert router.table.owner("fx.wobble.speed").source == "axis:L.N"
    assert router.table.owner("fx.wobble.amount").source == "axis:L.NE"


# ---- the readings: the patch's ----

def test_the_readings_are_the_patchs_and_swap(rig):  # noqa: F811
    """`pad.dial.left` / `.right` are the patch layer's (group `pad`, persisted), and
    the swap trades them through the params, so it is an edit like any other."""
    reg = rig.reg
    left = reg["pad.dial.left"]
    assert left.persist and part_of(left) == "patch" and not left.modulatable
    assert reg.dial_modes == gp.DIAL_DEFAULT
    left.set(1)
    assert reg.dial_modes == {"L": "blend", "R": "blend"}
    reg["pad.dial.right"].set(0)
    reg["pad.dial.swap"].fire()
    assert reg.dial_modes == {"L": "petal", "R": "blend"}
    assert "pad.dial.left" in reg.snapshot(part="patch")
    assert "pad.dial.left" not in reg.snapshot(part="shared_meta")


def test_the_params_restate_the_pads_readings():
    assert params.DIAL_READINGS == gp.DIAL_MODES
    assert {stick: fresh for stick, _, fresh in params.DIAL_SIDES} == gp.DIAL_DEFAULT
    assert (dial_id("L"), dial_id("R")) == ("pad.dial.left", "pad.dial.right")


def test_config_picks_the_launch_readings():
    """The first enabled gamepad entry's `dial_left` / `dial_right` (plan 27's [[devices]];
    the old [gamepad] table's keys translate) are the launch readings; a value that is no
    reading leaves the default."""
    from hyperspace import config

    entry = {"role": "pad", "kind": "gamepad", **config._kind_defaults("gamepad"),
             "dial_left": "blend", "dial_right": "nonsense"}
    assert app._dial_launch({"devices": [entry]}) == {"L": "blend", "R": "blend"}
    assert app._dial_launch({}) == gp.DIAL_DEFAULT
    assert config._kind_defaults("gamepad")["dial_left"] == "petal"


def test_a_disabled_entry_is_not_read_and_a_later_pads_keys_are_said():
    from hyperspace import config

    pad = {"role": "pad", "kind": "gamepad", **config._kind_defaults("gamepad")}
    off = {**pad, "role": "off", "enabled": False, "dial_left": "blend"}
    cfg = {"devices": [off, pad]}
    assert app._dial_launch(cfg) == gp.DIAL_DEFAULT and not cfg.get("notes")
    cfg = {"devices": [pad, {**pad, "role": "p2", "dial_left": "blend"}]}
    assert app._dial_launch(cfg) == gp.DIAL_DEFAULT
    assert "p2" in cfg["notes"][0] and "first enabled pad only" in cfg["notes"][0]


def test_an_opened_pad_takes_no_reading_from_its_entry():
    """The readings are a deck's, read at `poll`; a live edit of `dial_left` waits for
    the next launch (`config.toml`'s words), so the entry seeds nothing."""
    from hyperspace import config, devices

    dev = devices.make({"role": "pad", "kind": "gamepad", **config._kind_defaults("gamepad"),
                        "dial_left": "blend"})
    dev.open()
    try:
        assert dev.io.dial_modes == gp.DIAL_DEFAULT
    finally:
        dev.close()


def _two_decks(home, launch=None):
    """Two decks as `app.main` builds them: the launch readings on the meta controller's
    registry before any deck's is built."""
    r = boot(home)
    meta_reg = build_meta(r.control, NS(chain=r.chain))
    meta_reg.dial_launch = launch
    first = Deck.build(library=r.lib, control=r.control, audio=NS(chain=r.chain),
                       table=lambda reg: Bindings([]), meta_reg=meta_reg,
                       startup=False, install=False)
    second = Deck.beside(first, lfos=lfo.LFOs(seed=1))
    meta = MetaController(first, second, mix=r.mix)
    r.lib.pointer = meta.panel_pointer
    return NS(lib=r.lib, one=first, two=second, meta=meta)


def _flip(deck, *, left: int, right: int, name: str):
    """A loadable patch of `name` on `deck` with those readings, its path."""
    deck.reg["pad.dial.left"].set(left)
    deck.reg["pad.dial.right"].set(right)
    return deck.loaded_patch.save_as(name)


def test_a_loadable_patch_keeps_its_readings(tmp_path):
    """Saved in its `values` and put back by its load, whatever was set in between; one
    that names none gets the launch readings, not the last one's."""
    t = _two_decks(tmp_path / "home", {"L": "blend", "R": "blend"})
    deck = t.one
    assert deck.reg.dial_modes == {"L": "blend", "R": "blend"}
    plain = deck.loaded_patch.save_as("PLAIN")
    path = _flip(deck, left=0, right=0, name="BOTH PETAL")
    values = json.loads(path.read_text())["values"]
    assert values["pad.dial.left"] == 0 and values["pad.dial.right"] == 0
    deck.reg["pad.dial.left"].set(1)
    assert deck.loaded_patch.load("BOTH PETAL") == []
    assert deck.reg.dial_modes == {"L": "petal", "R": "petal"}
    doc = json.loads(plain.read_text())
    for k in ("pad.dial.left", "pad.dial.right"):
        doc["values"].pop(k)
    (plain.parent / "bare.json").write_text(json.dumps({**doc, "name": "BARE"}))
    assert deck.loaded_patch.load("BARE") == []
    assert deck.reg.dial_modes == {"L": "blend", "R": "blend"}
    assert not deck.loaded_patch.is_dirty()    # an older file is no edit for naming none


def test_a_deck_built_later_starts_on_the_launch_readings(tmp_path):
    t = _two_decks(tmp_path / "home", {"L": "blend", "R": "petal"})
    assert t.two.reg.dial_modes == {"L": "blend", "R": "petal"}
    assert t.one.reg["pad.dial.left"] is not t.two.reg["pad.dial.left"]
    t.two.undo.tick(1.0)
    t.two.undo.tick(2.0)
    assert t.two.undo.stack == []         # starting on them is no edit


def test_a_patch_fragment_may_not_carry_a_reading():
    """A reading is a whole loadable patch's: no node of a patch owns it (row 730)."""
    doc = {"schema": patches.SCHEMA, "name": "x", "nodes": [{"id": "wobble", "kind": "effect"}],
           "values": {"pad.dial.left": 1}}
    assert any("pad.dial.left" in why for why in patches.check(doc))


# ---- a row on the old ids ----

OLD_ROW = {"source": "pad:VIEW", "target": "desk.pad.dial.swap", "op": "fire"}


def test_a_row_learned_on_the_old_ids_moves_with_a_backup(tmp_path):
    """Plan 28 told the performer to Learn a button onto Swap dials, which wrote
    `desk.pad.dial.swap` into `bindings.json`: an old file opens with the row on
    `pad.dial.swap`, noted, the file kept beside itself, written once."""
    path = tmp_path / "bindings.json"
    table = Bindings([Binding.from_json(OLD_ROW)], path=path)
    table.write()
    was = path.read_text()
    assert "desk.pad.dial.swap" in was
    loaded = Bindings.load(path, legacy_midi=None)
    assert not any(b.target.startswith("desk.pad.dial") for b in loaded.bindings)
    row = next(b for b in loaded.bindings if b.target == "pad.dial.swap")
    assert row.source == "pad:VIEW" and row.op == "fire" and is_meta_row(row)
    assert meta_row_refusal(row) is None and row not in loaded.routes()
    assert "pad.dial.swap" in path.read_text() and "desk.pad.dial" not in path.read_text()
    assert [p.read_text() for p in tmp_path.glob("bindings.json.bak-v*")] == [was]
    assert any("desk.pad.dial.swap" in n for n in loaded.notes)
    again = Bindings.load(path, legacy_midi=None)          # the second launch says nothing
    assert again.notes == [] and len(list(tmp_path.glob("bindings.json.bak-v*"))) == 1


def test_the_moved_row_stands_and_swaps_only_the_deck_the_pad_is_on(tmp_path):
    """A meta row may drive a patch param: `meta_refusal` is the other way round. The row
    is on the meta controller's one table and acts through the router of the pad's deck."""
    t = _two_decks(tmp_path / "home")
    row = t.one.table.add(Binding("pad:VIEW", "pad.dial.swap", "fire"))
    assert row is not None and row in t.two.table.bindings
    pad = ScriptedPad()
    pad.frame()
    t.two.router.pad(pad)
    pad.frame(held={gp.VIEW})
    t.two.router.pad(pad)
    assert t.two.reg.dial_modes == {"L": "blend", "R": "petal"}
    assert t.one.reg.dial_modes == gp.DIAL_DEFAULT


# ---- a pad reads the `Deck` it drives ----

class Pad(ScriptedPad):
    """A scripted pad its device can poll: no hardware to read."""

    def poll(self) -> None:
        pass


def _pointed_pads(t, *roles):
    """A pad device per role, each on its own pointer, as `app.main` points them."""
    from hyperspace import devices

    ctx = devices.Context(reg=t.one.reg, table=t.one.table)
    made = [devices.PadDevice(role, None, ctx, io=Pad()) for role in roles]
    for d in made:
        d.point(t.meta.pointer(d.role), t.meta.panel_pointer)
    return made


NEAR_NE = at(30)                      # petal holds one sector; blend shares two


def _reads(dev) -> list[float]:
    """Stick `dev`'s left stick a little past N, polled: its left dial's lanes."""
    dev.io.frame(axes=[NEAR_NE[0], -NEAR_NE[1], 0.0, 0.0, -1.0, -1.0])
    dev.poll(1 / 60, 0.0)
    return dev.io.dials()[:gp.DIAL]


@pytest.mark.parametrize("pad_on, other", [("one", "two"), ("two", "one")])
def test_a_load_on_the_other_deck_changes_nothing_a_pad_reads(tmp_path, pad_on, other):
    """The absolute rule, both ways round: a loadable patch landing on the `Deck` a
    pad is not on leaves that pad's readings, and its lanes, exactly as they were."""
    t = _two_decks(tmp_path / "home")
    here, there = getattr(t, pad_on), getattr(t, other)
    path = _flip(there, left=1, right=0, name="BLEND LEFT")
    assert json.loads(path.read_text())["values"]["pad.dial.left"] == 1
    there.reg["pad.dial.left"].set(0)
    there.reg["pad.dial.right"].set(1)
    (dev,) = _pointed_pads(t, "pad")
    t.meta.point("pad", here)
    before = _reads(dev)
    assert dev.io.dial_modes == gp.DIAL_DEFAULT
    assert there.loaded_patch.load("BLEND LEFT") == []
    assert there.reg.dial_modes == {"L": "blend", "R": "petal"}   # it landed, there
    assert here.reg.dial_modes == gp.DIAL_DEFAULT                 # and not here
    assert _reads(dev) == before and dev.io.dial_modes == gp.DIAL_DEFAULT
    # the same pad moved over reads that deck: its stick's lanes change with it
    t.meta.point("pad", there)
    after = _reads(dev)
    assert dev.io.dial_modes == {"L": "blend", "R": "petal"} and after != before
    assert [v > 0 for v in before].count(True) == 1 and [v > 0 for v in after].count(True) == 2


def test_two_pads_on_two_decks_each_read_their_own(tmp_path):
    t = _two_decks(tmp_path / "home")
    a, b = _pointed_pads(t, "pad", "p2")
    t.meta.point("pad", t.one)
    t.meta.point("p2", t.two)
    t.two.reg["pad.dial.left"].set(1)
    _reads(a), _reads(b)
    assert a.io.dial_modes["L"] == "petal" and b.io.dial_modes["L"] == "blend"


def test_a_reading_is_one_undo_step_on_its_own_deck(tmp_path):
    """Picking a reading, or the swap, is a step the deck's undo takes back, and no
    step on the other deck's."""
    t = _two_decks(tmp_path / "home")
    for d in (t.one, t.two):
        d.undo.tick(1.0)
        d.undo.tick(2.0)
    held = len(t.one.undo.stack)
    t.two.reg["pad.dial.swap"].fire()
    t.two.undo.tick(3.0)
    t.two.undo.tick(9.0)
    assert t.two.reg.dial_modes == {"L": "blend", "R": "petal"}
    assert t.two.undo.undo() is True
    assert t.two.reg.dial_modes == gp.DIAL_DEFAULT
    assert len(t.one.undo.stack) == held and t.one.reg.dial_modes == gp.DIAL_DEFAULT


def test_copy_on_air_to_off_air_brings_the_readings(tmp_path):
    """The one verb that carries a look across carries its readings: they are the look's."""
    t = _two_decks(tmp_path / "home")
    t.meta.on_air.reg["pad.dial.left"].set(1)
    assert t.meta.copy_on_air() == []
    assert t.meta.off_air.reg["pad.dial.left"].text() == "blend"
    assert t.meta.off_air.reg["pad.dial.left"] is not t.meta.on_air.reg["pad.dial.left"]


# ---- the panel: the pad node on GRAPH ----

def _pane(panel, pad):
    """The pad node's details, as GRAPH draws them in its side pane."""
    from imgui_bundle import imgui
    from test_ui_shell import frame

    from hyperspace import graphview, ui_graph, ui_routing
    frame(panel, "graph")
    st = ui_graph._state(panel)
    n = graphview.VNode("device:pad", "device", "pad", ref=NS(kind="gamepad", io=pad))
    imgui.new_frame()
    imgui.begin("side", None)
    ui_graph._node_side(panel, st, st["view"], ui_routing.router_of(panel), n)
    imgui.end()
    imgui.end_frame()


def _spy(monkeypatch):
    from hyperspace.ui import Panel
    faces, rows = [], []
    draw, row = Panel._dial, Panel._row
    monkeypatch.setattr(Panel, "_dial", lambda self, vals, names, *a:
                        faces.append((list(vals), names)) or draw(self, vals, names, *a))
    monkeypatch.setattr(Panel, "_row", lambda self, pid, *a, **kw:
                        rows.append(pid) or row(self, pid, *a, **kw))
    return faces, rows


def test_the_pad_nodes_details_draw_both_clocks(tmp_path, monkeypatch):
    """The pad node's details draw the pad, then both sticks' faces and their readings
    (row 671: SYSTEM keeps only the feel)."""
    from test_ui_shell import build_rig, frame

    faces, rows = _spy(monkeypatch)
    with build_rig(tmp_path) as r:
        seed(r.lib.home)
        pad = ScriptedPad()
        r.panel.pad = pad
        assert [k for k in LoadedPatch(r.lib, r.reg, r.router).load("DIAL")
                if not k.startswith(("env.", "seq."))] == []  # (plan 36 T3: the `/7`'s envelope ids, this rig has none)
        x, y = at(100)
        pad.frame(axes=[x, -y, -x, y, -1.0, -1.0])
        _pane(r.panel, pad)
        left, right = faces[-2:]
        assert left[1][0] == "Wobble speed" and right[1][0] == "4D depth"
        assert left[0][2] > 0 and right[0][6] > 0   # 100°: E on the left, W on the right
        assert {"pad.dial.left", "pad.dial.right"} <= set(rows)
        pad.source = None                        # unplugged: empty faces
        _pane(r.panel, pad)
        assert faces[-1][0] == [0.0] * gp.DIAL
        faces.clear()
        rows.clear()
        frame(r.panel, "system")
        assert "desk.pad.feel" in rows and not any(p.startswith("pad.dial") for p in rows)
        assert faces == []


def test_a_pad_on_the_other_deck_moves_no_face_here(tmp_path, monkeypatch):
    """The panel shows one deck; a pad driving the other says nothing about its dials."""
    from test_ui_shell import build_rig

    from hyperspace import devices

    faces, _ = _spy(monkeypatch)
    with build_rig(tmp_path) as r:
        pad = ScriptedPad()
        r.panel.pad = pad
        x, y = at(100)
        pad.frame(axes=[x, -y, -x, y, -1.0, -1.0])
        ctx = devices.Context(reg=r.reg, table=r.router.table)
        where = NS(deck=NS(reg=r.reg, router=r.router))
        dev = devices.PadDevice("pad", None, ctx, io=pad)
        dev.point(where)
        r.panel.devices = devices.DeviceRegistry(devices=[dev], ctx=ctx)
        assert r.panel.pad_reads_here()
        _pane(r.panel, pad)
        assert any(faces[-1][0]) or any(faces[-2][0])
        where.deck = NS(reg=Registry(), router=None)
        assert not r.panel.pad_reads_here()
        _pane(r.panel, pad)
        assert faces[-1][0] == [0.0] * gp.DIAL and faces[-2][0] == [0.0] * gp.DIAL


def test_picking_a_reading_on_the_pad_node_sets_it(tmp_path, monkeypatch):
    """The readings are enums: the pad node offers their choices, and picking one sets
    it (an enum row is a combo, never a slider, whose write an enum refuses)."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig

    pick = {"pad.dial.left": 1, "pad.dial.right": 0}

    def chosen(label, cur, *a, **kw):
        pid = label.rpartition("##")[2]
        return (pid in pick, pick.get(pid, cur))

    monkeypatch.setattr(imgui, "combo", chosen)
    with build_rig(tmp_path) as r:
        pad = ScriptedPad()
        r.panel.pad = pad
        _pane(r.panel, pad)
        assert r.reg.dial_modes == {"L": "blend", "R": "petal"}


def test_the_stick_feel_is_picked_on_system(tmp_path, monkeypatch):
    """The stick feel stays the meta controller's, on SYSTEM: an enum, so a combo."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig, frame

    monkeypatch.setattr(imgui, "combo", lambda label, cur, *a, **kw: (
        label.endswith("##desk.pad.feel"), 2 if label.endswith("##desk.pad.feel") else cur))
    with build_rig(tmp_path) as r:
        r.panel.pad = ScriptedPad()
        frame(r.panel, "system")
        assert r.reg["desk.pad.feel"].text() == "spring"


def test_the_pad_picture_shows_a_dialed_stick(tmp_path):
    """On the pad's picture a stick a route reads as a dial says so: its X and Y read
    "Left dial · petal" instead of the orbit they no longer drive; the other stick
    keeps its camera job's words."""
    from test_ui_shell import build_rig

    from hyperspace import ui_pad
    with build_rig(tmp_path) as r:
        pad = ScriptedPad()
        r.panel.pad = pad
        r.router.table.add(Binding("axis:L.E", "view.inst_amp", "push", 1.0))
        _pane(r.panel, pad)
        lx, rx = gp.control("axis:LX"), gp.control("axis:RX")
        assert ui_pad.says(r.panel, lx, None) == "Left dial · petal"
        assert ui_pad.says(r.panel, rx, None) == ui_pad.BUILT_IN["axis:RX"]
        said = ui_pad.label(r.panel, lx, None)
        assert "read as a dial (petal)" in said and "Learn pad" in said     # beside the hint
        well = ui_pad.label(r.panel, gp.control("pad:LSTICK"), None)
        assert "read as a dial (petal)" in well and "Learn pad" in well and "free" in well
        r.reg["pad.dial.left"].set(1)
        assert ui_pad.says(r.panel, lx, None) == "Left dial · blend"
        pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
        assert ui_pad._sectors(r.panel, pad, gp.control("pad:LSTICK"))[2] > 0
        assert ui_pad._sectors(r.panel, pad, gp.control("pad:RSTICK")) is None
        # every view says the same: the lanes and the cockpit read through `_says_of`
        says = ui_pad._says_of(r.panel, r.router.table)
        assert says("axis:LX") == ("Left dial · blend", None)
        assert says("axis:RX") == (ui_pad.BUILT_IN["axis:RX"], None)


def test_a_second_pads_dial_route_leaves_the_primarys_stick_alone():
    from hyperspace import ui_pad

    table = Bindings([Binding("axis@p2:L.N", "view.inst_amp", "push", 1.0)])
    assert ui_pad.dialed(table) == set()
    table.add(Binding("axis:R.N", "view.bright", "push", 1.0))
    assert ui_pad.dialed(table) == {"R"}
