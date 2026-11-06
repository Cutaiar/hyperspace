"""Plan 28 N5 — controllers as nodes; the APC40 as two nodes (decision 12).

Presentation only: the rows, their layers and their homes are what the
table holds (D1, D4–D6, D12); nothing in apc40.py or midi.py is touched.
The desk is a real `devices.MidiDevice` over a stand-in adapter that
carries the APC40 profile (its `LAYOUT` is the device's ports), on the
shell rig's factory table (tests/test_ui_shell.py), so the invariant, the
global and the patch layer are the factory's. (Plan 24 C3's desk templates are
retired, plan 44 D3.) Every loadable patch is the corpus's or made here in the rig's
scratch library: no loadable patch is edited or added."""


import pytest
from conftest import seed
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import apc40, devices, graphview, ui_graph, ui_routing
from hyperspace.devices import Port
from hyperspace.routing import Binding

SHIFT = "note:0:98"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the loadable patches the tests load by slug)
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
    """A device registry over the meta controller's table: the APC40 (first MIDI role,
    so it has the two layers) and any `more`."""
    ctx = devices.Context(table=rig.router.table)
    listed = ([devices.MidiDevice("apc40", {"profile": "apc40"}, ctx, io=DeskIO())]
              if desk else []) + list(more)
    return devices.DeviceRegistry(ctx=ctx, devices=listed)


def build(rig, devs):
    return graphview.build(rig.router.table, rig.reg, rig.router, devs, None, None)


def node_of(view, pin):
    hit = view.owner(pin)
    return None if hit is None else hit[0]


def desk_cables(view):
    return [c for c in view.cables if c.kind == "setter" and c.ref.is_midi]


# ---------------------------------------------------------------- the two nodes

def test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node(rig):
    """*apc40* holds the patch layer's rows and the invariant ones,
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

    # the latch: the patch layer up
    assert table.layer_of() == "preset"
    assert first.up and not shift.up
    assert all(c.dormant for c in cables if c.ref.layer == "global")
    assert all(port.up for port in first.ports)
    # SHIFT latched: the global layer up, the patch layer's ports faint,
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


def test_a_drag_from_the_shift_node_into_base_is_refused_whatever_the_latch(rig):
    """D5: the global layer is never a Learn target, so a cable dragged
    from an *apc40 (SHIFT)* port onto a param's `base` stub is refused in
    words — the hover's `refusal` and the drop's `connect` agree — with
    SHIFT latched or not, and the table is unchanged."""
    rig.lib.load("presets", "party-trip")
    table = rig.router.table
    view = build(rig, rig_devices(rig))
    shift = view.node("device:apc40/global")
    port = next(p for p in shift.ports if p.addr.startswith("cc:"))
    src = port.pins[0]
    assert src == f"out:{port.addr}|global"
    pid = next(p.id for p in rig.reg if ui_routing.route_target(p) and not p.alias
               and not any(b.target == p.id for b in table.bindings))
    ed = graphview.Edit(table, rig.reg, rig.router, view, apc40)
    for latched in (False, True):
        rig.reg["desk.shift"].set(latched)
        rows = list(table.bindings)
        why = ed.refusal(src, f"base:{pid}")
        res = ed.connect(src, f"base:{pid}")
        assert isinstance(res, graphview.Refusal) and "SHIFT node" in res, latched
        assert why == res
        assert table.bindings == rows and all(a is b for a, b in zip(table.bindings, rows))
    rig.reg["desk.shift"].set(False)
    # the same control from the first node is the desk learn, as before
    first = f"out:{port.addr}"
    assert view.owner(first) is not None
    assert ed.refusal(first, f"base:{pid}") is None


def test_a_shadowed_layered_row_leaves_the_invariant_port_on_the_first_node(rig):
    """A global-layer row on an invariant control (D6: it never acts) is
    drawn off from that control's port on *apc40*: the SHIFT node gains no
    invariant control."""
    rig.lib.load("presets", "party-trip")
    table = rig.router.table
    row = Binding(SHIFT, "view.bright", "toggle", layer="global")
    table.bindings.append(row)
    view = build(rig, rig_devices(rig))
    c = next(c for c in desk_cables(view) if c.ref is row)
    assert c.off and c.dormant and "invariant" in c.label
    assert node_of(view, c.src_port).id == "device:apc40"
    assert view.owner(c.src_port)[1].group == graphview.INVARIANT
    assert SHIFT not in {p.addr for p in view.node("device:apc40/global").ports}


# ---------------------------------------------------------------- desk templates
# (plan 44 D3: retired — no library held one; a loadable patch names none)

def test_a_corpus_loadable_draws_no_template_node(rig):
    """Every corpus loadable patch has a plain desk section: no template node."""
    rig.lib.load("presets", "party-trip")
    assert not hasattr(ui_graph, "template_of") and not hasattr(graphview, "TEMPLATE")
    view = build(rig, rig_devices(rig))
    assert not [n for n in view.nodes if n.kind == "template"]
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
    free = [p.id for p in rig.reg if ui_routing.route_target(p) and not p.alias
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
