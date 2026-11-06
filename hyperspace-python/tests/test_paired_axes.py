"""Plan 56: two discrete controls of a pad as one polarised axis, through the
real `Router.pad` with a scripted real `gamepad.Pad`."""

import json
from types import SimpleNamespace as NS

import pytest

import hyperspace.gamepad as gp
from hyperspace import devices, graphview, routing_sources, ui_pad, ui_pad_views
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.learn import (
    BARE_WANTS,
    KEEP_BOTH,
    PAIR_SPRING_WANT,
    PAIR_WANT,
    TAKE_OVER,
    Learn,
    row_for,
    settle_pair,
)
from hyperspace.library import Library
from hyperspace.motion import DEFAULT_ROUTE_FEEL
from hyperspace.pads import models
from hyperspace.pads.models import MODELS
from hyperspace.params import build_registry
from hyperspace.render import ViewState
from hyperspace.routing import (
    SCHEMA,
    Binding,
    Bindings,
    Router,
    Sources,
    is_session_row,
    row_words,
)

UP, DOWN, LEFT, RIGHT = gp.HAT_UP, gp.HAT_DOWN, gp.HAT_LEFT, gp.HAT_RIGHT
AT_REST = [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]


class ScriptedPad(gp.Pad):
    """A real Pad whose frames are scripted."""

    def __init__(self):
        super().__init__()
        self.source = "usb"

    def frame(self, held=(), hat=0) -> None:
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons = [1 if i in held else 0 for i in range(gp.N_BUTTONS)]
        self.hat = hat
        self.axes = list(AT_REST)

    def lose(self) -> None:
        self.source = None
        self.buttons, self.prev_buttons, self.hat, self.prev_hat = [], [], 0, 0


@pytest.fixture()
def rig(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(tmp_path)
    reg = build_registry(ViewState(), control, NS(chain=chain), lib.project)
    path = tmp_path / "bindings.json"
    table = Bindings.load(path, legacy_midi=None)
    router = Router(reg, table)
    return NS(reg=reg, table=table, router=router, path=path,
              learn=Learn(reg, table, lane=router.lane))


def clear_pad_rows(table) -> None:
    for b in table.of("pad", "hat"):
        table.remove(b)


def lane(rig, source: str) -> float:
    scheme, i = rig.router.lane(source)
    return float(rig.router.feeds[scheme][i])


# ---- the lane: each pole, both, none ----

def test_each_pole_moves_the_lane_and_a_release_rests_it(rig):
    pad = ScriptedPad()
    pad.frame()
    rig.router.pad(pad, 0.0)
    assert lane(rig, "pair:UP/DOWN") == 0.5
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.1)
    assert lane(rig, "pair:UP/DOWN") == 1.0
    pad.frame()
    rig.router.pad(pad, 0.2)
    assert lane(rig, "pair:UP/DOWN") == 0.5
    pad.frame(hat=DOWN)
    rig.router.pad(pad, 0.3)
    assert lane(rig, "pair:UP/DOWN") == 0.0
    pad.frame(held={gp.RB})
    rig.router.pad(pad, 0.4)
    assert lane(rig, "pair:UP/DOWN") == 0.5
    assert lane(rig, "pair:RB/LB") == 1.0


def test_both_poles_held_is_the_rest(rig):
    pad = ScriptedPad()
    pad.frame(hat=UP | DOWN, held={gp.LB, gp.RB})
    rig.router.pad(pad, 0.0)
    assert lane(rig, "pair:UP/DOWN") == 0.5
    assert lane(rig, "pair:RB/LB") == 0.5


def test_a_pad_lost_while_held_lets_the_route_go(rig):
    """The lane stops being fed, so the route's offset goes and the base shows."""
    clear_pad_rows(rig.table)            # (the factory `hat:UP` row would step the base too)
    p = rig.reg["view.bright"]
    rig.table.add(Binding("pair:UP/DOWN", p.id, "push", 0.5))
    pad = ScriptedPad()
    pad.frame()
    rig.router.pad(pad, 0.0)
    rig.router.modulate(None, dt=1 / 60)
    rig.reg.apply()
    rest = p.value
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.1)
    rig.router.modulate(None, dt=1 / 60)
    rig.reg.apply()
    assert p.value > rest
    pad.lose()
    assert not pad.on
    rig.router.pad(pad, 0.2)
    assert rig.router.feeds["pair"] is None
    rig.router.modulate(None, dt=1 / 60)
    rig.reg.apply()
    assert p.value == pytest.approx(rest)


def test_a_device_closed_while_held_lets_the_route_go(rig):
    """`Router.pad_lost`, the road a closing device takes with no frame after it."""
    pad = ScriptedPad()
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.0)
    rig.router.pad(pad, 0.0, role="p2")
    assert rig.router.feeds["pair"] is not None
    rig.router.pad_lost()
    assert rig.router.feeds["pair"] is None
    assert rig.router.feeds["pair@p2"] is not None      # the second pad's is its own
    rig.router.pad_lost("p2")
    assert rig.router.feeds["pair@p2"] is None


def test_a_second_pad_is_apart_from_the_first(rig):
    first, second = ScriptedPad(), ScriptedPad()
    first.frame()
    second.frame(hat=UP)
    rig.router.pad(first, 0.0)
    rig.router.pad(second, 0.0, role="p2")
    assert lane(rig, "pair:UP/DOWN") == 0.5
    assert lane(rig, "pair@p2:UP/DOWN") == 1.0
    p = rig.reg["view.speed"]
    rig.table.add(Binding("pair@p2:UP/DOWN", p.id, "step", 1.0))
    was = p.position()
    first.frame(hat=UP)
    second.frame()
    rig.router.pad(first, 0.1)
    rig.router.pad(second, 0.1, role="p2")
    assert p.position() == was          # the first pad's UP is not the second's
    first.frame()
    second.frame(hat=UP)
    rig.router.pad(first, 0.2)
    rig.router.pad(second, 0.2, role="p2")
    assert p.position() == was + 1


def test_a_pole_the_totem_holds_reads_as_not_pressed(rig):
    pad = ScriptedPad()
    pad.frame(hat=DOWN)
    rig.router.pad(pad, 0.0, skip=frozenset({"hat:DOWN"}))
    assert lane(rig, "pair:UP/DOWN") == 0.5


# ---- any two discrete controls ----

def test_a_pair_no_model_has_is_declared_by_its_row(rig):
    rig.table.add(Binding("pair:A/UP", "view.bright", "push", 0.5))
    pad = ScriptedPad()
    pad.frame()
    rig.router.pad(pad, 0.0)
    rig.router.modulate(None, dt=1 / 60)       # the pass reads the row: its lane is there
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.1)
    assert lane(rig, "pair:A/UP") == 0.0
    pad.frame(held={gp.A})
    rig.router.pad(pad, 0.2)
    assert lane(rig, "pair:A/UP") == 1.0


def test_a_row_naming_a_pair_before_the_first_frame_keeps_the_natural_ones(rig):
    assert rig.router.lane("pair:A/UP")[1] >= 0
    pad = ScriptedPad()
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.0)
    assert lane(rig, "pair:UP/DOWN") == 1.0
    assert lane(rig, "pair:A/UP") == 0.0


@pytest.mark.parametrize("addr", ["pair:UP/UP", "pair:UP", "pair:UP/NOPE", "pair:DEADZONE/UP"])
def test_a_pair_that_names_no_two_controls_is_dormant(rig, addr):
    assert rig.router.lane(addr)[1] == -1


def test_the_scheme_is_stated_once():
    assert gp.PAIR_SCHEME == routing_sources.PAIR_SCHEME


# ---- the factory pairs ----

def test_the_factory_pairs_act_exactly_as_they_did(rig):
    """Row 750: `hat:UP/DOWN → view.bright ±3` and `pad:LB/RB → view.shape ±1`
    stay two rows, the same two, stepping once per press."""
    rows = {(b.source, b.target, b.op, b.value) for b in rig.table.bindings}
    assert {("hat:UP", "view.bright", "step", 3), ("hat:DOWN", "view.bright", "step", -3),
            ("pad:LB", "view.shape", "step", -1), ("pad:RB", "view.shape", "step", 1)} <= rows
    assert not rig.table.of("pair")
    pad = ScriptedPad()
    bright, shape = rig.reg["view.bright"], rig.reg["view.shape"]
    pad.frame()
    rig.router.pad(pad, 0.0)
    pos = bright.position()
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.1)
    assert bright.position() == pos + 3
    rig.router.pad(pad, 0.2)                 # held: `prev_hat` still 0, as a frame's scripted
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.3)
    pad.frame()
    rig.router.pad(pad, 0.4)
    pos = bright.position()
    pad.frame(hat=DOWN)
    rig.router.pad(pad, 0.5)
    assert bright.position() == pos - 3
    pad.frame()
    rig.router.pad(pad, 0.6)
    was = shape.base
    pad.frame(held={gp.RB})
    rig.router.pad(pad, 0.7)
    assert shape.base == was + 1
    pad.frame()
    rig.router.pad(pad, 0.8)
    pad.frame(held={gp.LB})
    rig.router.pad(pad, 0.9)
    assert shape.base == was


def test_a_step_row_on_a_pair_acts_as_the_two_rows_it_stands_for(rig):
    """The step model, the neutral default: the same steps, in the same order,
    as `hat:UP +3` and `hat:DOWN −3`, the file's two rows."""
    p = rig.reg["view.bright"]
    script = [{"hat": UP}, {}, {"hat": UP | DOWN}, {"hat": DOWN}, {}, {"hat": DOWN}]

    def run(rows) -> list[int]:
        clear_pad_rows(rig.table)
        for b in rig.table.of("pair"):
            rig.table.remove(b)
        for b in rows:
            rig.table.add(b)
        p.set_position(40)
        pad = ScriptedPad()
        pad.frame()
        rig.router.pad(pad, 0.0)
        out = []
        for k, f in enumerate(script):
            pad.frame(**f)
            rig.router.pad(pad, 0.1 * (k + 1))
            out.append(p.position())
        return out
    two = run([Binding("hat:UP", p.id, "step", 3.0), Binding("hat:DOWN", p.id, "step", -3.0)])
    one = run([Binding("pair:UP/DOWN", p.id, "step", 3.0)])
    assert one == two == [43, 43, 43, 43, 43, 40]      # both together cancel


def test_a_learn_press_lets_a_step_row_be(rig):
    p = rig.reg["view.bright"]
    clear_pad_rows(rig.table)
    rig.table.add(Binding("pair:UP/DOWN", p.id, "step", 1.0))
    pad = ScriptedPad()
    pad.frame()
    rig.router.pad(pad, 0.0)
    was = p.position()
    pad.frame(hat=UP)
    rig.router.pad(pad, 0.1, buttons=False)
    assert p.position() == was


def test_other_button_ops_on_a_pair_are_refused(rig):
    with pytest.raises(ValueError):
        rig.table.add(Binding("pair:UP/DOWN", "view.faces", "toggle"))


# ---- the two shapes' homes, and a save ----

def test_a_step_row_is_the_tables_and_a_route_is_the_presets():
    assert is_session_row(Binding("pair:UP/DOWN", "view.bright", "step", 1.0))
    assert not is_session_row(Binding("pair:UP/DOWN", "view.bright", "push", 0.5))


def test_a_saved_route_on_a_pair_survives_a_save_and_reload(rig, tmp_path):
    p = rig.reg["view.bright"]
    rig.table.add(Binding("pair:UP/DOWN", p.id, "push", 0.25, motion=DEFAULT_ROUTE_FEEL))
    rig.table.add(Binding("pair:UP/DOWN", "view.speed", "step", 2.0))
    rig.table.write()
    saved = [b.to_json() for b in rig.table.routes()]
    assert saved[0]["source"] == "pair:UP/DOWN" and saved[0]["op"] == "push"
    assert set(saved[0]) <= set(Binding.__dataclass_fields__)      # no new key in a file

    back = Bindings.load(rig.path, legacy_midi=None)
    assert any(b.source == "pair:UP/DOWN" and b.op == "step" and b.target == "view.speed"
               for b in back.bindings)
    other = Binding.from_json(json.loads(json.dumps(saved[0])))
    assert (other.source, other.op, other.value) == ("pair:UP/DOWN", "push", 0.25)
    assert other.motion == DEFAULT_ROUTE_FEEL

    # read and acted on again by a fresh router over fresh sources
    back.set_routes([other])
    router = Router(rig.reg, back)
    pad = ScriptedPad()
    pad.frame(hat=UP)
    router.pad(pad, 0.0)
    assert router.feeds["pair"][router.lane("pair:UP/DOWN")[1]] == 1.0
    assert router.lane(other.source)[1] >= 0


def test_an_older_build_reads_a_pair_route_as_dormant_and_keeps_it(rig):
    """What an older build does: no pad publishes the scheme there. Modelled by
    a scheme of the same shape nothing here publishes, the rule it runs on."""
    p = rig.reg["view.bright"]
    data = {"schema": SCHEMA, "bindings": [
        {"source": "elsewhere:UP/DOWN", "target": p.id, "op": "push", "value": 0.5},
        {"source": "elsewhere:UP/DOWN", "target": "view.speed", "op": "step", "value": 1.0}]}
    table = Bindings.from_json(data)
    router = Router(rig.reg, table)
    assert router.lane("elsewhere:UP/DOWN")[1] == -1
    assert [b.source for b in table.bindings] == ["elsewhere:UP/DOWN"] * 2
    was = p.value
    router.modulate(None, dt=1 / 60)
    rig.reg.apply()
    assert p.value == was


# ---- Learn ----

def press(rig, pad, t, **frame) -> None:
    pad.frame(**frame)
    taken = gp.learn_from(pad, rig.learn)
    rig.router.pad(pad, t, buttons=not taken)
    pad.frame()
    gp.learn_from(pad, rig.learn)
    rig.router.pad(pad, t + 0.01)


def test_learn_pair_lands_a_step_row_on_two_presses(rig):
    assert PAIR_WANT in BARE_WANTS and PAIR_SPRING_WANT in BARE_WANTS
    p = rig.reg["view.speed"]
    was = p.position()
    rig.learn.arm(p.id, PAIR_WANT)
    pad = ScriptedPad()
    pad.frame()
    press(rig, pad, 0.0, hat=UP)
    assert rig.learn.learning == p.id          # the + pole: it waits
    assert "+ pole" in rig.learn.last
    press(rig, pad, 0.1, hat=UP)               # the same again is nothing
    assert rig.learn.learning == p.id
    press(rig, pad, 0.2, hat=DOWN)
    assert rig.learn.learning is None
    assert p.position() == was                 # neither learn press stepped it
    # the factory's rows are on those poles: it asks first (row 754)
    assert not rig.table.of("pair")
    settle_pair(rig.learn.pair_ask, TAKE_OVER, rig.reg)
    row = rig.table.of("pair")
    assert [(b.source, b.target, b.op, b.value) for b in row] == [
        ("pair:UP/DOWN", p.id, "step", 1.0)]
    # into the file, as a pad row is
    assert any(r["source"] == "pair:UP/DOWN" for r in json.loads(rig.path.read_text())["bindings"])
    assert not rig.table.of("hat")             # the factory's two rows on those poles went
    press(rig, pad, 0.3, hat=UP)
    assert p.position() == was + 1
    press(rig, pad, 0.4, hat=DOWN)
    assert p.position() == was


def test_learn_pair_spring_lands_a_route_like_a_stick(rig):
    p = rig.reg["view.speed"]
    rig.learn.arm(p.id, PAIR_SPRING_WANT)
    pad = ScriptedPad()
    pad.frame()
    press(rig, pad, 0.0, held={gp.RB})
    press(rig, pad, 0.1, held={gp.A})
    settle_pair(rig.learn.pair_ask, KEEP_BOTH, rig.reg)    # the factory's RB row: row 754
    b = rig.table.owner(p.id)
    assert b is not None and b.source == "pair:RB/A" and b.op == "push"
    assert b.motion == DEFAULT_ROUTE_FEEL
    assert not any(x.source == "pad:RB" and x.target == p.id for x in rig.table.bindings)
    assert any(x.source == "pad:RB" for x in rig.table.bindings)   # a route leaves a button's row


def test_a_stick_does_not_complete_a_pair_learn(rig):
    p = rig.reg["view.speed"]
    rig.learn.arm(p.id, PAIR_WANT)
    assert not rig.learn.accepts("axis:LX")
    assert rig.learn.accepts("hat:UP") and rig.learn.accepts("pad@p2:A")
    assert not rig.learn.accepts("cc:0:7")


def test_a_pair_is_two_controls_of_one_pad(rig):
    rig.learn.arm("view.speed", PAIR_WANT)
    assert rig.learn.learn_pad_button("hat:UP")
    assert rig.learn.learn_pad_button("hat@p2:DOWN")
    assert rig.learn.refused and rig.learn.learning == "view.speed"
    assert rig.learn.learn_pad_button("hat:DOWN")
    assert rig.learn.learning is None
    assert rig.learn.pair_ask.new.source == "pair:UP/DOWN"


def test_a_toggle_has_no_two_directions(rig):
    rig.learn.arm("view.faces", PAIR_WANT)
    rig.learn.learn_pad_button("hat:UP")
    assert rig.learn.learn_pad_button("hat:DOWN")
    assert rig.learn.refused and rig.learn.learning is None
    assert not rig.table.of("pair")


def test_a_button_learn_replaces_a_pair_row_on_its_pole(rig):
    p = rig.reg["view.speed"]
    rig.table.add(Binding("pair:UP/DOWN", p.id, "step", 1.0))
    rig.learn.arm("view.bright")
    assert rig.learn.learn_pad_button("hat:UP")
    assert not rig.table.of("pair")


def test_rearming_forgets_the_first_pole(rig):
    rig.learn.arm("view.speed", PAIR_WANT)
    rig.learn.learn_pad_button("hat:UP")
    rig.learn.arm("view.speed", PAIR_WANT)
    rig.learn.learn_pad_button("hat:LEFT")
    rig.learn.learn_pad_button("hat:RIGHT")
    assert any(b.source == "pair:LEFT/RIGHT" for b in rig.table.bindings)


def test_a_plain_learn_pad_is_one_press_one_row(rig):
    rig.learn.arm("view.speed", "pad")
    assert rig.learn.learn_pad_button("hat:UP")
    assert rig.learn.learning is None
    assert not rig.table.of("pair")


def test_row_for_treats_a_pair_as_centred(rig):
    b = row_for("pair:UP/DOWN", rig.reg["view.speed"])
    assert b.op == "push" and b.motion == DEFAULT_ROUTE_FEEL


# ---- what a model has, and one degree of freedom ----

def test_a_models_natural_pairs():
    assert ("UP", "DOWN") in models.natural_pairs(None)
    assert ("RP", "LP") not in models.natural_pairs(MODELS["xbox"])
    assert ("RP", "LP") in models.natural_pairs(MODELS["edge"])
    assert ("RFN", "LFN") in models.natural_pairs(MODELS["edge"])
    joy = models.natural_pairs(MODELS["joycon-l"])
    assert ("Y", "A") in joy and ("UP", "DOWN") not in joy and ("RB", "LB") not in joy


def test_a_pair_is_one_degree_of_freedom():
    dof = gp.degrees_of_freedom()
    assert ("hat:UP", "hat:DOWN") in dof and ("pad:RB", "pad:LB") in dof
    assert ("hat:UP",) not in dof and ("axis:LX",) in dof and ("pad:MENU",) in dof
    every = [s for d in dof for s in d]
    assert len(every) == len(set(every))
    # six axes, four pairs (D-pad 2, bumpers, face 2 less), the rest alone
    alone = [d for d in dof if len(d) == 1 and d[0].startswith(("pad:", "hat:"))]
    assert len([d for d in dof if len(d) == 2]) == len(models.natural_pairs(None))
    assert len(alone) == len(gp.BUTTONS) + len(gp.HATS) - 2 * len(models.natural_pairs(None))
    assert len(dof) == len(gp.AXES) + len(models.natural_pairs(None)) + len(alone)
    # a pair someone made counts the same, and two controls fold only once
    made = gp.degrees_of_freedom(pairs=(("A", "MENU"), ("A", "B")))
    assert ("pad:A", "pad:MENU") in made and ("pad:A", "pad:B") not in made and ("pad:B",) in made


def test_paired_with():
    assert gp.paired_with("hat:UP") == "hat:DOWN"
    assert gp.paired_with("pad:LB") == "pad:RB"
    assert gp.paired_with("pad:MENU") is None
    assert gp.paired_with("hat:UP", MODELS["joycon-l"]) is None
    assert gp.paired_with("pad:A", MODELS["joycon-r"]) == "pad:Y"


# ---- where a person sees it ----

def test_the_device_node_has_a_pairs_port_group():
    ports = devices.PadDevice("pad").sources
    pairs = {p.address: p for p in ports if p.group == "pairs"}
    assert set(pairs) == {f"pair:{a}/{b}" for a, b in models.natural_pairs(None)}
    assert all(p.bipolar and p.rest == 0.5 and p.kind == "value" for p in pairs.values())
    assert pairs["pair:UP/DOWN"].label == "D-pad up / down"


def test_a_second_pads_ports_are_its_own():
    d = devices.PadDevice("p2")
    d.qualify("p2")
    assert "pair@p2" in d.schemes and "pair@p2" in d.feeds
    assert any(p.address == "pair@p2:UP/DOWN" for p in d.sources)


def test_a_sony_pair_says_its_own_face():
    assert models.pair_label(MODELS["edge"], "RB", "LB") == "R1 / L1"


def test_the_pad_window_lights_both_poles(rig):
    clear_pad_rows(rig.table)
    b = Binding("pair:UP/DOWN", "view.bright", "step", 1.0)
    rig.table.add(b)
    shown = ui_pad.rows(rig.table)
    assert shown["hat:UP"] is b and shown["hat:DOWN"] is b


def test_the_words():
    assert row_words("pair:UP/DOWN") == "pair UP / DOWN"
    assert row_words("pair@p2:RB/LB") == "pair RB / LB"
    assert Binding("pair:UP/DOWN", "x", "step", 3.0).describe() == "pair UP/DOWN steps ±3"


def test_the_lanes_view_has_a_pairs_group():
    pad = ScriptedPad()
    pad.frame(hat=UP)
    groups = dict(ui_pad_views._lane_rows(ui_pad_views.read(pad)))
    row = {s: (v, rest, bip) for s, _, v, rest, bip in groups["pairs"]}
    assert row["pair:UP/DOWN"] == (1.0, 0.5, True) and row["pair:RB/LB"] == (0.5, 0.5, True)


def test_the_pad_window_says_which_pole(rig):
    clear_pad_rows(rig.table)
    b = Binding("pair:UP/DOWN", "view.bright", "step", 1.0)
    rig.table.add(b)
    panel = NS(reg=rig.reg, pad=None)
    up = gp.control("hat:UP")
    assert ui_pad.says(panel, up, b) == "Brightness +1"
    assert ui_pad.says(panel, gp.control("hat:DOWN"), b) == "Brightness -1"
    route = Binding("pair:UP/DOWN", "view.speed", "push", 0.5)
    assert ui_pad.says(panel, up, route).endswith(" +")
    assert ui_pad.says(panel, gp.control("hat:DOWN"), route).endswith(" −")
    assert "one axis with ↓" in ui_pad.label(panel, up, b)
    assert "one axis with" not in ui_pad.label(panel, gp.control("pad:MENU"), None)


def test_the_graphs_device_node_draws_the_pairs_and_a_cable_makes_a_route(rig):
    clear_pad_rows(rig.table)
    devs = devices.DeviceRegistry(devices=[devices.PadDevice("pad", io=ScriptedPad())])
    rig.table.add(Binding("pair:RIGHT/LEFT", "view.speed", "step", 1.0))
    rig.table.add(Binding("pair:A/UP", "view.bright", "push", 0.5))
    view = graphview.build(rig.table, rig.reg, rig.router, devs, None, None)
    node = view.node("device:pad")
    assert "out:pair:UP/DOWN" in [pin for p in node.ports if p.group == "pairs" for pin in p.pins]
    # a step row and a free pair's route, each a cable from the pad's node
    for addr in ("pair:RIGHT/LEFT", "pair:A/UP"):
        cable = next(c for c in view.cables if c.addr == addr)
        assert view.owner(cable.src_port)[0] is node
    e = graphview.Edit(rig.table, rig.reg, rig.router, view)
    got = e.connect("out:pair:RB/LB", "mod:camera.zoom")
    assert isinstance(got, Binding) and (got.source, got.op) == ("pair:RB/LB", "push")
    assert got.motion == DEFAULT_ROUTE_FEEL


def test_two_decks_read_one_lane_and_keep_their_rows(rig):
    """Row 748: the lanes are the source's, the rows the deck's. A free pair one
    deck's row names shifts no lane another deck reads, and a press acts only
    on the table whose router the pad was handed to."""
    src = Sources()
    clear_pad_rows(rig.table)
    p = rig.reg["view.speed"]
    other_table = Bindings.from_json({"schema": SCHEMA, "bindings": []})
    deck_a = Router(rig.reg, rig.table, sources=src)
    deck_b = Router(rig.reg, other_table, sources=src)
    other_table.add(Binding("pair:UP/DOWN", p.id, "step", 1.0))
    pad = ScriptedPad()
    pad.frame()
    deck_a.pad(pad, 0.0)
    natural = deck_b.lane("pair:UP/DOWN")
    assert deck_a.lane("pair:A/X")[1] >= 0
    assert deck_b.lane("pair:UP/DOWN") == natural
    was = p.position()
    pad.frame(hat=UP)
    deck_a.pad(pad, 0.1)
    assert p.position() == was
    assert src.feeds["pair"][natural[1]] == 1.0


# ---- review findings on #372 ----

def test_a_row_naming_a_natural_pair_first_leaves_the_rest_to_merge():
    src = Sources()
    src.resolve("pair:UP/DOWN")
    assert src.labels["pair"] == ["UP / DOWN"]
    gp.publish(src)
    assert len(src.names["pair"]) == len(models.natural_pairs(None))
    assert src.labels["pair"][src.names["pair"]["UP/DOWN"]] == "D-pad up / down"
    assert len(src.rests["pair"]) == len(src.names["pair"])


def test_publishing_again_writes_nothing():
    src = Sources()
    gp.publish(src)
    names, labels = src.names["pair"], src.labels["pair"]
    gp.publish(src)
    assert src.names["pair"] is names and src.labels["pair"] is labels


def test_a_pad_publishes_only_the_pairs_it_has():
    src = Sources()
    gp.publish(src, "axis", MODELS["x360"])
    assert "RP/LP" not in src.names["pair"] and "RFN/LFN" not in src.names["pair"]
    gp.publish(src, "axis", MODELS["edge"])     # another pad comes: its lanes, its words
    assert "RP/LP" in src.names["pair"]
    assert src.labels["pair"][src.names["pair"]["RB/LB"]] == "R1 / L1"


def test_a_scripted_pads_model_is_what_it_publishes():
    pad, src = ScriptedPad(), Sources()
    pad.model = MODELS["joycon-l"]
    pad.publish(src)
    assert set(src.names["pair"]) == {
        f"{a}/{b}" for a, b in models.natural_pairs(MODELS["joycon-l"])}
    assert {"Y/A", "B/X"} <= set(src.names["pair"]) and "UP/DOWN" not in src.names["pair"]


def test_a_second_pads_row_is_not_on_the_windows_controls(rig):
    theirs = Binding("pair@p2:RB/LB", "view.speed", "step", 1.0)
    rig.table.add(theirs)
    shown = ui_pad.rows(rig.table)
    assert shown["pad:RB"] is not theirs and shown["pad:LB"] is not theirs
    assert shown["pad:RB"].target == "view.shape"


def test_a_cable_from_a_pair_onto_a_stepped_param_is_a_step_row(rig):
    clear_pad_rows(rig.table)
    devs = devices.DeviceRegistry(devices=[devices.PadDevice("pad", io=ScriptedPad())])
    view = graphview.build(rig.table, rig.reg, rig.router, devs, None, None)
    e = graphview.Edit(rig.table, rig.reg, rig.router, view)
    p = next(q for q in rig.reg if q.modulatable and q.integer and q.kind.name == "CONTINUOUS")
    got = e.connect("out:pair:UP/DOWN", f"mod:{p.id}")
    assert isinstance(got, Binding) and (got.source, got.op, got.value) == (
        "pair:UP/DOWN", "step", 1.0)
    assert not any(b.source == "pair:UP/DOWN" and b.op == "position" for b in rig.table.bindings)


def test_a_button_learn_on_one_pole_leaves_the_other_moving(rig):
    p = rig.reg["view.speed"]
    clear_pad_rows(rig.table)
    rig.table.add(Binding("pair:UP/DOWN", p.id, "step", 2.0))
    rig.learn.arm("view.bright")
    assert rig.learn.learn_pad_button("hat:UP")
    assert not rig.table.of("pair")
    assert [(b.source, b.target, b.value) for b in rig.table.of("hat")] == [
        ("hat:DOWN", p.id, -2.0), ("hat:UP", "view.bright", 1.0)]
    assert "view.speed keeps" in rig.learn.last
    # the other way about, on a second pad
    rig.table.add(Binding("pair@p2:UP/DOWN", p.id, "step", 2.0))
    rig.learn.arm("view.bright")
    assert rig.learn.learn_pad_button("hat@p2:DOWN")
    assert ("hat@p2:UP", 2.0) in [(b.source, b.value) for b in rig.table.of("hat")]


def test_a_pair_learn_sharing_a_pole_leaves_the_other_moving(rig):
    p = rig.reg["view.speed"]
    clear_pad_rows(rig.table)
    rig.table.add(Binding("pair:UP/DOWN", p.id, "step", 1.0))
    rig.learn.arm("view.bright", PAIR_WANT)
    rig.learn.learn_pad_button("hat:UP")
    rig.learn.learn_pad_button("hat:LEFT")
    settle_pair(rig.learn.pair_ask, TAKE_OVER, rig.reg)    # row 754
    assert [b.source for b in rig.table.of("pair")] == ["pair:UP/LEFT"]
    assert [(b.source, b.value) for b in rig.table.of("hat")] == [("hat:DOWN", -1.0)]


def test_no_window_system_leaves_a_pair_dormant(monkeypatch, rig):
    import sys

    import hyperspace
    monkeypatch.setattr(routing_sources, "_POLES", {})
    monkeypatch.delattr(hyperspace, "gamepad")
    monkeypatch.setitem(sys.modules, "hyperspace.gamepad", None)
    assert routing_sources.pair_poles("UP/DOWN") is None
    assert Sources().resolve("pair:UP/DOWN")[2] == -1
    assert routing_sources._POLES == {}                 # asked again once it is there


def test_a_pair_mixing_a_hat_and_a_button_says_so():
    assert models.pair_label(None, "UP", "A") == "UP / A"
    assert models.pair_label(None, "A", "UP") == "A / UP"


def test_the_hover_names_the_partner_in_the_pads_own_words(rig):
    panel = NS(reg=rig.reg, pad=NS(on=True, model=MODELS["edge"]))
    assert "one axis with R1" in ui_pad.label(panel, gp.control("pad:LB"), None)


def test_the_lanes_view_lists_a_pair_a_row_names(rig):
    clear_pad_rows(rig.table)
    rig.table.add(Binding("pair:A/UP", "view.speed", "step", 2.0))
    says = ui_pad._says_of(NS(reg=rig.reg), rig.table)
    pad = ScriptedPad()
    pad.frame(hat=UP)
    groups = dict(ui_pad_views._lane_rows(ui_pad_views.read(pad), ui_pad_views._routed(says)))
    row = {s: v for s, _, v, _, _ in groups["pairs"]}
    assert row["pair:A/UP"] == 0.0
    assert says("pair:A/UP")[0].endswith("±2")


# ---- a control something else holds is no pole: the one predicate ----

def test_every_road_asks_one_predicate(rig, monkeypatch):
    """`models.control_free` says no to LB: offered nowhere, counted nowhere,
    read nowhere, fired nowhere. What #365's layout will say about SL and SR."""
    real = models.control_free
    monkeypatch.setattr(models, "control_free",
                        lambda m, name, skip=frozenset(): name != "LB" and real(m, name, skip))
    assert ("RB", "LB") not in models.natural_pairs(None)
    assert gp.paired_with("pad:RB") is None
    dof = gp.degrees_of_freedom()
    assert not any("pad:LB" in d for d in dof) and ("pad:RB",) in dof
    clear_pad_rows(rig.table)
    p = rig.reg["view.speed"]
    rig.table.add(Binding("pair:RB/LB", p.id, "step", 1.0))
    assert rig.router.lane("pair:RB/LB")[1] >= 0    # a row names it, though no pad offers it
    pad = ScriptedPad()
    pad.frame()
    rig.router.pad(pad, 0.0)
    was = p.position()
    pad.frame(held={gp.LB})
    rig.router.pad(pad, 0.1)
    assert p.position() == was                      # no step
    assert lane(rig, "pair:RB/LB") == 0.5           # no lane
    pad.frame()
    rig.router.pad(pad, 0.2)
    pad.frame(held={gp.RB})
    rig.router.pad(pad, 0.3)
    assert p.position() == was + 1                  # the free pole still moves it
    assert lane(rig, "pair:RB/LB") == 1.0
    # and Learn pair does not take it for a pole
    rig.learn.arm("view.speed", PAIR_WANT)
    pad.frame()
    pad.frame(held={gp.LB})
    assert gp.learn_from(pad, rig.learn) is False
    assert rig.learn.__dict__.get("pair_first") is None
    views = dict(ui_pad_views._lane_rows(ui_pad_views.read(pad)))
    assert not any(s == "pair:RB/LB" for s, *_ in views["pairs"])


def test_a_layout_holds_its_controls():
    """Fails at #365's merge until `models.control_free` reads `Model.layout`: the
    one line the PR body names. Skipped until the field exists."""
    if "layout" not in models.Model.__dataclass_fields__:
        pytest.skip("no Model.layout on this base (#365)")
    joy = MODELS["joycon-l"]
    assert not models.control_free(joy, "LP") and not models.control_free(joy, "RP")
    assert ("RP", "LP") not in models.natural_pairs(joy)
    assert gp.paired_with("pad:LP", joy) is None
    assert models.control_free(joy, "Y")
