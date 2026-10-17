"""Plan 28 N5 — controllers as nodes; the APC40 as two nodes (decision 12).

Presentation only: the rows, their layers and their homes are what the
table holds (D1, D4–D6, D12); nothing in apc40.py or midi.py is touched.
The desk is a real `devices.MidiDevice` over a stand-in adapter that
carries the APC40 profile (its `LAYOUT` is the device's ports), on the
shell rig's factory table (tests/test_ui_shell.py), so the invariant, the
global and the preset layer are the factory's. The desk template is the
plan 24 C3 fixture (tests/fixtures/desk-templates/), copied into the rig's
scratch library: no preset is edited or added."""

import json
import shutil
from pathlib import Path

import pytest
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import apc40, devices, graphview, ui_graph
from hyperspace.devices import Port
from hyperspace.library import DESK
from hyperspace.preset import TEMPLATE_KEY
from hyperspace.routing import Binding

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "desk-templates"
TEMPLATE = FIXTURES / "desk" / "fixture-shape.json"
PRESET = FIXTURES / "presets" / "templated.json"
SHIFT = "note:0:98"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


class DeskIO:
    """What `MidiDevice` reads of a `midi.MidiIO`: the profile, on, no error."""

    def __init__(self):
        self.profile = apc40
        self.on, self.error, self.last, self.name, self.bindings = True, "", "", "APC40", ()


class FakeDevice(devices.Base):
    def __init__(self, role, kind, schemes, ports, *, connected=True):
        super().__init__(role, io=object() if connected else None)
        self.kind = kind
        self.schemes = self.feeds = schemes
        self._ports = ports

    @property
    def sources(self):
        return self._ports if self.io is not None else ()


def rig_devices(rig, *more, desk=True):
    """A device registry over the rig's table: the APC40 (first MIDI role,
    so it has the two layers) and any `more`."""
    ctx = devices.Context(table=rig.router.table)
    listed = ([devices.MidiDevice("apc40", {"profile": "apc40"}, ctx, io=DeskIO())]
              if desk else []) + list(more)
    return devices.DeviceRegistry(ctx=ctx, devices=listed)


def build(rig, devs, template=None):
    return graphview.build(rig.router.table, rig.reg, rig.router, devs, None, None,
                           template=template)


def node_of(view, pin):
    hit = view.owner(pin)
    return None if hit is None else hit[0]


def desk_cables(view):
    return [c for c in view.cables if c.kind == "setter" and c.ref.is_midi]


# ---------------------------------------------------------------- the two nodes

def test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node(rig):
    """*apc40* holds the preset layer's rows and the invariant ones,
    *apc40 (SHIFT)* the global layer's; each cable leaves the node of the
    layer its row is on. Each port is lit while its layer is up — the
    table's latch, which SHIFT flips (`desk.shift`) — and a cable from a
    layer that is down is dormant."""
    rig.lib.load("presets", "party-trip")
    table = rig.router.table
    devs = rig_devices(rig)
    view = build(rig, devs)
    first, shift = view.node("device:apc40"), view.node("device:apc40/global")
    assert [n.id for n in view.nodes if n.id.startswith("device:apc40")] == \
        ["device:apc40", "device:apc40/global"]
    assert (first.label, shift.label) == ("apc40", "apc40 (SHIFT)")
    assert (first.layer, shift.layer) == ("preset", "global")
    assert first.kind == shift.kind == "device" and not first.grey and not shift.grey
    cables = desk_cables(view)
    layers = {b.layer for b in table.midi()}
    assert layers == {None, "preset", "global"}
    assert len(cables) == len(table.midi())             # every desk row is one cable
    for c in cables:
        b = c.ref
        want = shift if b.layer == "global" else first
        assert node_of(view, c.src_port) is want, (b.source, b.target, b.layer)
        port = view.owner(c.src_port)[1]
        assert port.addr == b.source
        assert port.layer == ("" if b.layer is None else b.layer)
    # a SHIFT-layer pin is tagged, a first-node pin is the address itself
    g = next(c for c in cables if c.ref.layer == "global")
    assert g.src_port == f"out:{g.ref.source}|global"
    p = next(c for c in cables if c.ref.layer == "preset")
    assert p.src_port == f"out:{p.ref.source}"

    # the latch: the preset layer up
    assert table.layer_of() == "preset"
    assert first.up and not shift.up
    assert all(c.dormant for c in cables if c.ref.layer == "global")
    assert all(port.up for port in first.ports)
    # SHIFT latched: the global layer up, the preset layer's ports faint,
    # the invariant ports lit on either layer
    rig.reg["desk.shift"].set(True)
    graphview.refresh(view, rig.reg, rig.router)
    assert shift.up and not first.up
    assert all(port.up for port in shift.ports)
    assert all(port.up == (port.layer == "") for port in first.ports)
    assert all(c.dormant for c in cables if c.ref.layer == "preset")
    # released: back
    rig.reg["desk.shift"].set(False)
    graphview.refresh(view, rig.reg, rig.router)
    assert first.up and not shift.up
    # nothing in the table moved: presentation only
    assert {b.layer for b in table.midi()} == layers


def test_invariant_controls_are_ports_on_the_first_node_only(rig):
    """SHIFT, the bank pads and every other invariant control (the
    controls of the table's layer-None rows) are ports on *apc40* only,
    in its ``invariant`` group, listed first; *apc40 (SHIFT)* carries every
    other control of the layout, in the desk's groups."""
    rig.lib.load("presets", "party-trip")
    table = rig.router.table
    devs = rig_devices(rig)
    desk = devs.get("apc40")
    view = build(rig, devs)
    first, shift = view.node("device:apc40"), view.node("device:apc40/global")
    controls = [p.address for p in desk.sources]
    inv = {a for a in controls if table.is_invariant(Binding(a, ""))}
    assert SHIFT in inv and "note:0:53" in inv              # SHIFT, the first bank pad
    on_first = {p.addr for p in first.ports if p.group == graphview.INVARIANT}
    assert on_first == inv
    assert all(p.layer == "" for p in first.ports if p.group == graphview.INVARIANT)
    assert not inv & {p.addr for p in shift.ports}
    assert {p.addr for p in shift.ports} >= set(controls) - inv
    # the invariant group first; the desk's groups on both nodes
    assert first.ports[0].group == graphview.INVARIANT
    assert {p.group for p in shift.ports} <= set(graphview.DESK_GROUPS) - {graphview.INVARIANT}
    assert {"track knobs", "device knobs", "faders", "clip grid", "buttons"} <= \
        {p.group for p in first.ports}
    # every invariant row's cable leaves the first node
    for c in desk_cables(view):
        if c.ref.layer is None:
            assert node_of(view, c.src_port) is first


# ---------------------------------------------------------------- desk templates

def put_fixtures(lib) -> None:
    for src, group in ((PRESET, "presets"), (TEMPLATE, DESK)):
        (lib.home / group).mkdir(parents=True, exist_ok=True)
        shutil.copy(src, lib.home / group / src.name)


def test_a_templated_desk_is_one_collapsed_node_whose_edits_write_overrides(rig):
    """A preset naming a desk template draws the template as one node whose
    ports are its mapped controls; the live rows still the template's are
    cables inside it — not drawn until it is opened — and an override hangs
    off *apc40*. An edit inside (a cable deleted, a control dragged onto
    another param) goes through the table, so a save writes the preset's
    overrides and the template file is never written."""
    lib, panel = rig.lib, rig.panel
    put_fixtures(lib)
    before = (lib.home / DESK / TEMPLATE.name).read_bytes()
    lib.presets.load("TEMPLATED")
    template = ui_graph.template_of(panel)
    tdoc = json.loads(TEMPLATE.read_text())
    assert template == ("fixture shape", tdoc["desk"])
    devs = rig_devices(rig)
    view = build(rig, devs, template)
    tnodes = [n for n in view.nodes if n.kind == graphview.TEMPLATE]
    assert [n.id for n in tnodes] == ["template:fixture shape"]
    tn = tnodes[0]
    assert graphview.home(tn) == graphview.PRESET
    assert [p.addr for p in tn.ports] == [r["source"] for r in tdoc["desk"]]
    inside = [c for c in view.cables if c.inside == tn.id]
    kept = {("cc:*:16", "view.depth4"), ("cc:*:18", "camera.pitch"),
            ("cc:*:19", "view.pattern"), ("cc:0:48", "view.bright"),
            ("cc:0:7", "view.lines_alpha")}
    assert {(c.ref.source, c.ref.target) for c in inside} == kept
    assert all(node_of(view, c.src_port) is tn for c in inside)
    # the overrides hang off the desk's first node; the overridden D2 and
    # the dark K2 are the template's ports with no cable
    over = {(c.ref.source, c.ref.target): c for c in desk_cables(view) if not c.inside}
    for key in (("cc:*:17", "dream.mix"), ("cc:0:50", "view.pattern_mix")):
        assert node_of(view, over[key].src_port).id == "device:apc40"
    assert not tn.port("out:cc:*:17|template").patched
    assert not tn.port("out:cc:0:49|template").patched

    # on the page: collapsed until opened, then its rows are cables
    panel.devices = devs
    frame(panel, "graph")
    st = ui_graph._state(panel)
    tid = st["view"].node(tn.id)
    assert tid is not None and not ui_graph.is_open(st, tn.id)
    assert not any(ui_graph.drawn_cable(st, c) for c in st["view"].cables if c.inside)
    ui_graph.toggle_open(st, tn.id)
    frame(panel, "graph")
    assert ui_graph.is_open(st, tn.id)
    assert all(ui_graph.drawn_cable(st, c) for c in st["view"].cables if c.inside)

    # edits inside: D1's cable deleted, D3 dragged onto view.speed
    table = rig.router.table
    ed = graphview.Edit(table, rig.reg, rig.router, view, apc40)
    d1 = next(c for c in inside if c.ref.source == "cc:*:16")
    assert ed.disconnect(d1) is None
    landed = ed.connect("out:cc:*:18|template", "base:view.speed")
    assert isinstance(landed, Binding) and landed.layer == "preset"
    view = build(rig, devs, ui_graph.template_of(panel))
    d3 = next(c for c in desk_cables(view) if c.ref is landed)
    assert d3.inside == "" and node_of(view, d3.src_port).id == "device:apc40"
    lib.presets.save_as("TEMPLATED N5")
    saved = json.loads((lib.home / "presets" / "templated-n5.json").read_text())
    assert saved[TEMPLATE_KEY] == "fixture shape"
    assert {"source": "cc:*:16", "dark": True} in saved["desk"]
    assert any(r.get("source") == "cc:*:18" and r.get("target") == "view.speed"
               for r in saved["desk"])
    assert (lib.home / DESK / TEMPLATE.name).read_bytes() == before


def test_a_factory_preset_draws_no_template_node(rig):
    """Every factory preset has a plain desk section: no template node."""
    rig.lib.load("presets", "party-trip")
    assert ui_graph.template_of(rig.panel) is None
    view = build(rig, rig_devices(rig), ui_graph.template_of(rig.panel))
    assert not [n for n in view.nodes if n.kind == graphview.TEMPLATE]
    assert not [c for c in view.cables if c.inside]


# ---------------------------------------------------------------- roles, not serials

def test_a_missing_role_is_a_grey_placeholder_with_dormant_cables(rig):
    """A row naming a role this rig lists no device for — a qualified row
    (``axis@p2``, ``cc@launch``) or a scheme no listed device publishes
    (``hand`` with no hands device) — draws from a grey placeholder named
    by that role, its cables dormant, as ROUTING shows a dormant row.
    When a device of that role is listed, the cable leaves it instead
    (the same node id, so it takes the placeholder's place)."""
    table = rig.router.table
    rig.lib.load("presets", "party-trip")
    free = [p.id for p in rig.reg if p.modulatable and not p.alias
            and table.owner(p.id) is None][:2]
    table.add(Binding("axis@p2:LX", free[0], "push", 0.3))
    table.add(Binding("hand:right.y", free[1], "position"))
    table.bindings.append(Binding("cc@launch:0:7", "view.bright", "abs"))
    devs = rig_devices(rig)
    view = build(rig, devs)
    for role, addr in (("p2", "axis@p2:LX"), ("leap", "hand:right.y"),
                       ("launch", "cc@launch:0:7")):
        n = view.node(f"device:{role}")
        assert n is not None and n.placeholder and n.grey and n.kind == "device", role
        assert n.label == role and n.status == graphview.PLACEHOLDER_STATUS
        c = next(c for c in view.cables if c.addr == addr)
        assert node_of(view, c.src_port) is n and c.dormant, role
    # the keys are no device: still their own grey source node
    assert view.node("source:key") is not None
    # the pad of that role arrives
    p2 = FakeDevice("p2", "gamepad", ("axis@p2",), (
        Port("LX", "left x", bipolar=True, group="sticks", scheme="axis@p2"),))
    view = build(rig, rig_devices(rig, p2))
    n = view.node("device:p2")
    assert not n.placeholder and not n.grey
    c = next(c for c in view.cables if c.addr == "axis@p2:LX")
    assert node_of(view, c.src_port) is n


# ---------------------------------------------------------------- the hands

def test_the_hands_node_groups_axes_pinches_grab_and_dance(rig):
    """The hands device's node folds its ports as the design names them:
    axes, pinches, grab, dance (and presence) — `hands/device.py`'s groups,
    its ``switches`` told apart into the pinches and the grabs."""
    from hyperspace.hands.device import HandsDevice
    hands = HandsDevice("leap", io=rig.panel.hands)
    view = build(rig, rig_devices(rig, hands, desk=False))
    n = view.node("device:leap")
    groups = [p.group for p in n.ports]
    assert {"axes", "pinches", "grab", "dance"} <= set(groups)
    assert "switches" not in groups
    for p in n.ports:
        if ".pinch." in p.addr:
            assert p.group == "pinches", p.addr
        if p.addr.endswith(".grab"):
            assert p.group == "grab", p.addr
    # the order is the device's: the axes first
    assert groups[0] == "axes"
