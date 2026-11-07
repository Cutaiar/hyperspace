"""Plan 55: players and duties. A row acts only on the `Deck` its player is on,
and no patch can affect another by way of a controller.

Two players, two fake pads, two decks with different patches: each moves only
its own deck, across a duty change mid-press, and a chase, a turn, the totem and
the poi follow the player. Every player on air is what the app did before.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_deck import _compare, _walk
from test_meta_controller import _pointed
from test_totem import FakePad
from test_undo import boot

from hyperspace import app, devicelist, devices, gamepad, graphview, osc, poi, routing, totem, undo
from hyperspace.deck import KEYS, MOUSE, Deck, MetaController
from hyperspace.hotreload import MODULES
from hyperspace.learn import SAVE_PARAM
from hyperspace.params import CHASE_LABEL
from hyperspace.players import FILE, SCHEMA, Duty, Players, qualifier_of
from hyperspace.routing import TURN_GRACE_S, TURN_OP, Binding
from hyperspace.routing_sources import Layered, Sources

DT = 1 / 60
PX, PY = "camera.pan.x", "camera.pan.y"
ONE_STICK, TWO_STICK = "axis:LX", "axis@p2:LX"
YAW, GRAB = "hand:right.room.yaw", "hand:right.grab"


class Stick(FakePad):
    """A pad with motion sensors, a left stick to push, and its axes' names."""

    def __init__(self):
        super().__init__()
        self.x = 0.5

    def lanes(self):
        return [self.x, 0.5, 0.5, 0.5, 0.0, 0.0]

    def poll(self):
        pass

    def publish(self, router, scheme="axis"):
        gamepad.publish(router, scheme)

    def press(self, *buttons):
        self.was, self.held = self.held, {getattr(gamepad, b) for b in buttons}


class Hands(devices.Base):
    """A hand's lanes, as the hands device feeds them: no presses, one scheme."""

    kind = "hands"
    schemes = feeds = ("hand",)

    def __init__(self, role="hands"):
        super().__init__(role)
        self.io = object()
        self.yaw, self.grab = 0.0, 0.0

    def feed(self, sources):
        sources.names.setdefault("hand", {YAW.partition(":")[2]: 0, GRAB.partition(":")[2]: 1})
        sources.feed("hand", [self.yaw, self.grab])


@pytest.fixture()
def rig(tmp_path):
    """Two decks, player 1's pad, player 2's pad and the hands (player 1's), all on
    air, as the app builds them: one registry over one set of sources."""
    p = _pointed(boot(tmp_path / "home"))
    one = p.one
    ctx = devices.Context(reg=one.reg, table=one.table)
    p.pad1, p.pad2 = Stick(), Stick()
    first = devices.PadDevice("pad", None, ctx, io=p.pad1)
    second = devices.PadDevice("p2", None, ctx, io=p.pad2)
    second.qualify("p2")
    p.hands = Hands()
    p.devs = devices.DeviceRegistry(devices=[first, second, p.hands], ctx=ctx)
    p.devs.point(p.meta.pointer, p.meta.panel_pointer)
    one.router.use(p.devs)
    p.now = 0.0

    def frame(n=1):
        for _ in range(n):
            p.pad1.motion.step((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), DT)
            p.pad2.motion.step((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), DT)
            p.now += DT
            p.devs.poll(DT, p.now, router=one.router)
            p.devs.feed(one.sources)
            for d in p.meta.decks:             # app.frame's pass: both, each on its own rows
                d.router.modulate(None, DT, p.now)
                d.reg.apply()
    p.frame = frame
    yield p
    undo.install(None)


def _routes(deck, *rows):
    deck.table.set_routes([*deck.table.routes(), *(Binding(s, t, "push", 1.0) for s, t in rows)])


def _two_patches(rig):
    """Deck 1 and deck 2 differ: each names player 1 on one param, player 2 on the other."""
    _routes(rig.one, (ONE_STICK, PX), (TWO_STICK, PY))
    _routes(rig.two, (ONE_STICK, PY), (TWO_STICK, PX))
    rig.frame()


def _pans(deck):
    return deck.reg[PX].value, deck.reg[PY].value


def _pan_bases(deck):
    return deck.reg[PX].base, deck.reg[PY].base


# ---------------------------------------------------------------- who holds what

def test_a_patch_names_a_player_and_bare_is_player_1():
    assert [qualifier_of(n) for n in (1, 2, 3, 4)] == ["", "p2", "p3", "p4"]
    players = Players()
    assert [p.number for p in players] == [1, 2, 3, 4]
    assert all(p.duty == Duty.ON_AIR for p in players)
    for role in ("pad", "apc40", "hands", "edge", "p1", "p5", "bridge"):
        assert players.player_of(role).number == 1, role
    assert [players.player_of(f"p{n}").number for n in (2, 3, 4)] == [2, 3, 4]


def test_the_list_publishes_what_it_did_under_the_default_players():
    """Plan 27 B6 to the letter with nobody registered: first pad bare, the rest by role."""
    pads = [{"role": r, "kind": "gamepad", "enabled": True, "usb": False}
            for r in ("pad", "p2", "edge")]
    want = {"pad": "", "p2": "p2", "edge": "edge"}
    assert devices.qualifiers_of(pads, None) == want
    assert devices.qualifiers_of(pads, Players()) == want
    # a first enabled pad called p2 keeps the bare rows, as it does today
    off = [{"role": "pad", "kind": "gamepad", "enabled": False},
           {"role": "p2", "kind": "gamepad", "enabled": True}]
    players = Players()
    assert devices.qualifiers_of(off, players) == devices.qualifiers_of(off, None)
    assert players.player_of("p2").number == 1


def test_a_player_s_pad_publishes_under_the_player_whatever_its_role():
    players = Players()
    players.hold("edge", 2)
    pads = [{"role": "pad", "kind": "gamepad", "enabled": True, "usb": False},
            {"role": "edge", "kind": "gamepad", "enabled": True, "usb": False},
            {"role": "spare", "kind": "gamepad", "enabled": True, "usb": False}]
    players.hold("spare", 2)
    made = {d.role: d for d in devices.make_all(pads, devices.Context(players=players))}
    assert made["edge"].qualifier == "p2" and "axis@p2" in made["edge"].feeds
    assert made["edge"].wants[-1] == "p2"           # "Learn p2" is what its rows say
    assert made["spare"].qualifier == "spare"       # a second of the kind: no two on one lane
    assert players.controllers_of(2) == ("edge", "spare")
    assert players.controllers_of(1) == ("pad",)
    assert [p.number for p in players.active()] == [1, 2]


def _pad(role):
    return {"role": role, "kind": "gamepad", "enabled": True, "usb": False}


def _swap_step(players, pads):
    made = devices.make_all(pads, devices.Context(players=players))
    assert not [d for d in made if isinstance(d, devices.RefusedDevice)]
    names = [d.qualifier for d in made]
    assert len(names) == len(set(names))        # no two on one lane
    return {d.role: d.qualifier for d in made}


def test_swapping_two_pads_collides_at_no_step():
    """Finding 2: the first step used to refuse a working pad."""
    players, pads = Players(), [_pad("pad"), _pad("p2")]
    assert _swap_step(players, pads) == {"pad": "", "p2": "p2"}
    players.hold("pad", 2)
    assert _swap_step(players, pads) == {"pad": "pad", "p2": "p2"}   # p2 need not reopen
    players.hold("p2", 1)
    assert _swap_step(players, pads) == {"pad": "p2", "p2": ""}


def test_a_role_spelled_as_a_player_s_name_never_answers_for_another_player():
    players = Players()
    players.hold("a", 2)
    players.hold("p3", 2)                        # player 2's second, spelled as player 3
    got = _swap_step(players, [_pad("pad"), _pad("a"), _pad("p3"), _pad("p2")])
    assert got == {"pad": "", "a": "a", "p3": "p3-pad", "p2": "p2"}


def _swapped(rig):
    """Roles `pad` and `p2`, each held by the other's player."""
    players = rig.meta.players
    players.hold("pad", 2)
    players.hold("p2", 1)
    ctx = devices.Context(reg=rig.one.reg, table=rig.one.table, players=players)
    pads = [_pad("pad"), _pad("p2")]
    made = {d.role: d for d in devices.make_all(pads, ctx)}
    made["pad"].io, made["p2"].io = rig.pad1, rig.pad2
    made["pad"].open = made["p2"].open = lambda: None
    devs = devices.DeviceRegistry(devices=list(made.values()), ctx=ctx)
    devs.point(rig.meta.pointer, rig.meta.panel_pointer)
    rig.one.router.use(devs)
    rig.devs = devs
    return devs


def test_at_p2_is_player_2_even_with_a_primary_spelled_p2(rig):
    """Finding 1: `axis@p2` followed player 1's pad, and the pad feeding it drove nothing."""
    devs = _swapped(rig)
    prim = devs.primaries()
    assert "axis" not in prim
    assert rig.one.sources.resolve("axis@p2:LX", prim)[0] == "axis@p2"
    _routes(rig.one, (TWO_STICK, PX), (ONE_STICK, PY))
    rig.frame()
    rest = _pans(rig.one)
    rig.pad1.x = 1.0                             # role `pad`: player 2's
    rig.frame()
    assert rig.one.reg[PX].value != rest[0] and rig.one.reg[PY].value == rest[1]
    rig.pad1.x, rig.pad2.x = 0.5, 1.0            # role `p2`: player 1's
    rig.frame()
    assert rig.one.reg[PX].value == rest[0] and rig.one.reg[PY].value != rest[1]


def test_a_pair_step_on_at_p2_fires_from_player_2_s_pad_only(rig):
    _swapped(rig)
    p = rig.one.reg["view.bright"]
    rig.one.table.add(Binding("pair@p2:A/B", "view.bright", "step", 1.0))
    rig.frame()
    was = p.value
    rig.pad2.press("A")                          # role `p2`: player 1's, the bare pad
    rig.frame()
    assert p.value == was
    rig.pad2.press()
    rig.pad1.press("A")                          # role `pad`: player 2's
    rig.frame()
    assert p.value != was


def test_the_readers_ask_who_publishes_a_player_s_name(rig):
    """Finding 6: drawn on player 2's pad, and that pad's state said, whatever its role."""
    devs = _swapped(rig)
    one = rig.one
    _routes(one, (TWO_STICK, PX))
    view = graphview.build(one.table, one.reg, one.router, devs, None, None)
    pin = _cable(view, PX).src_port
    assert [n.id for n in view.nodes if any(q.id == pin for q in n.ports)] == ["device:pad"]
    wanted = {w.role: w.state for w in devices.wants(one.table, devs)}
    assert wanted["pad"] == devices.CONNECTED and "p2" not in wanted
    devs.get("pad").io = None                    # player 2's pad lost, player 1's still there
    wanted = {w.role: w.state for w in devices.wants(one.table, devs)}
    assert wanted["pad"] == devices.LOST and "p2" not in wanted


def test_a_primary_called_p2_keeps_its_alias_while_nobody_else_is_p2():
    """Plan 27 B6's rule stands where it collides with nothing."""
    d = devices.PadDevice("p2", io=Stick())
    assert devices.DeviceRegistry(devices=[d]).primaries()["axis"] == "p2"


def test_a_list_change_that_changes_a_player_moves_the_pointer(rig):
    """Finding 3: `p2` off air; disable `pad`, `p2` is the primary, so player 1's, on air."""
    meta, one, two = rig.meta, rig.one, rig.two
    meta.move_player(2, Duty.OFF_AIR)
    assert meta.pointer("p2").deck is two
    meta.players.tell(("pad", "p2"), ("p2",))    # what the re-read list tells it
    meta.reseat()
    assert meta.players.player_of("p2").number == 1 and meta.pointer("p2").deck is one


def test_a_reseat_leaves_a_controller_mapped_elsewhere_alone(rig):
    meta, two = rig.meta, rig.two
    meta.point("p2", two)
    meta.reseat()
    assert meta.pointer("p2").deck is two


def test_main_reseats_on_a_list_change():
    import inspect
    assert "device_reg.listeners.append(lambda: meta.reseat())" in inspect.getsource(app.main)


def test_only_a_controller_is_held(tmp_path):
    players = Players()
    devices.make_all([{"role": "pad", "kind": "gamepad", "enabled": True, "usb": False},
                      {"role": "pic", "kind": "cloud", "enabled": True, "path": "x"}],
                     devices.Context(players=players))
    assert players.known == ("pad",)


def test_a_number_outside_one_to_four_is_refused():
    players = Players()
    with pytest.raises(ValueError, match="no player 5"):
        players.get(5)
    with pytest.raises(ValueError, match="no player 0"):
        players.hold("pad", 0)
    with pytest.raises(ValueError):
        players.move(1, "backstage")


# ---------------------------------------------------------------- where it is remembered

def test_nobody_moved_writes_nothing_and_a_move_writes_only_what_differs(tmp_path):
    players = Players.load(tmp_path)
    assert not (tmp_path / FILE).exists()
    players.move(1, Duty.ON_AIR)                     # no change
    assert not (tmp_path / FILE).exists()
    players.move(2, Duty.OFF_AIR)
    players.hold("edge", 3)
    doc = json.loads((tmp_path / FILE).read_text())
    assert doc == {"schema": SCHEMA, "duties": {"2": "off_air"}, "controllers": {"edge": 3}}
    notes = []
    again = Players.load(tmp_path, notes)
    assert again.get(2).duty == Duty.OFF_AIR and again.player_of("edge").number == 3
    assert notes == [f"players: player 2 off air, as left ({FILE})"]


@pytest.mark.parametrize("text", [
    "not json", "[]", '{"schema": "players/9"}',
    json.dumps({"schema": SCHEMA, "duties": {"7": "on_air"}}),
    json.dumps({"schema": SCHEMA, "duties": {"2": "backstage"}}),
    json.dumps({"schema": SCHEMA, "controllers": {"pad": 9}})])
def test_a_file_that_cannot_be_read_is_set_aside_and_everyone_is_on_air(tmp_path, text):
    (tmp_path / FILE).write_text(text)
    notes = []
    players = Players.load(tmp_path, notes)
    assert all(p.duty == Duty.ON_AIR for p in players) and not players.held
    assert not (tmp_path / FILE).exists()
    assert (tmp_path / f"{FILE}.bad").read_text() == text
    assert "could not be read" in notes[0]


def test_a_write_that_fails_is_said_and_the_move_stands(tmp_path):
    players = Players(tmp_path / "no such folder" / FILE)
    players.move(2, Duty.OFF_AIR)
    assert players.get(2).duty == Duty.OFF_AIR
    assert "not remembered" in players.error and players.notes


def test_a_player_off_air_at_launch_starts_there(rig, tmp_path):
    players = Players.load(tmp_path)
    players.move(2, Duty.OFF_AIR)
    meta = MetaController(rig.one, rig.two, Players.load(tmp_path))
    assert meta.pointer("p2").deck is rig.two and meta.pointer("pad").deck is rig.one
    assert meta.pointer(KEYS).deck is rig.one and meta.pointer(MOUSE).deck is rig.one


def test_a_patch_carries_no_player(rig):
    """Remembered by the meta controller on this Mac: nothing of it in a saved loadable patch."""
    rig.meta.move_player(2, Duty.OFF_AIR)
    for deck in rig.meta.decks:
        text = deck.loaded_patch.save_as("saved with a player off air").read_text()
        assert "off_air" not in text and '"players"' not in text


# ---------------------------------------------------------------- a duty, as a Deck

def test_a_duty_means_a_deck_until_the_crossfader_says_otherwise(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    assert meta.deck_for(Duty.ON_AIR) is one and meta.deck_for("off_air") is two
    meta.move_player(2, Duty.OFF_AIR)
    assert meta.pointer("p2").deck is two and meta.pointer("pad").deck is one
    assert meta.pointer("hands").deck is one
    meta.move_player(2, Duty.ON_AIR)
    assert meta.pointer("p2").deck is one


def test_moving_a_player_moves_everything_it_holds_and_nothing_else(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    meta.register("hands", 2)
    assert meta.players.player_of("hands").number == 2
    meta.move_player(2, Duty.OFF_AIR)
    assert meta.pointer("hands").deck is two and meta.pointer("p2").deck is two
    assert meta.pointer("pad").deck is one
    assert meta.panel is one and meta.on_air is one
    assert meta.pointer(KEYS).deck is one and meta.pointer(MOUSE).deck is one


def test_registering_goes_to_that_player_s_deck_and_tells_the_list(rig):
    told = []
    rig.meta.on_players.append(lambda: told.append(1))
    rig.meta.move_player(3, Duty.OFF_AIR)
    rig.meta.register("hands", 3)
    assert rig.meta.pointer("hands").deck is rig.two and told == [1]


def test_an_off_air_player_stays_with_the_off_air_deck_when_on_air_moves(rig):
    """What D5c does as the fader passes the middle."""
    meta, one, two = rig.meta, rig.one, rig.two
    meta.move_player(2, Duty.OFF_AIR)
    meta.on_air_pointer.deck = two
    meta.place_players()
    assert meta.off_air is one
    assert meta.pointer("p2").deck is one and meta.pointer("pad").deck is two


def test_main_builds_the_players_before_the_devices_and_moves_none():
    import inspect
    src = inspect.getsource(app.main)
    assert src.index("Players.load(home") < src.index("_open_devices(cfg")
    assert "players=players" in src and "MetaController(deck, deck2, players, mix=mix)" in src
    assert "move_player(" not in src
    assert "meta.on_players.append" in src and "on.learn.mapped" in src


def test_the_new_module_is_watched_and_a_leaf(rig):
    from hyperspace import players as mod
    assert "players" in MODULES
    assert MODULES.index("players") < MODULES.index("deck")
    assert "from ." not in Path(mod.__file__).read_text()
    targets = rig.meta.targets()
    assert (rig.meta.players, "players", "Players") in targets
    assert sum(cls == "Player" for *_, cls in targets) == 4


# ---------------------------------------------------------------- a row, on its player's Deck

def test_each_player_moves_only_the_deck_it_is_on(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    _two_patches(rig)
    rest_one, rest_two = _pans(one), _pans(two)
    meta.move_player(2, Duty.OFF_AIR)
    rig.pad1.x, rig.pad2.x = 1.0, 0.0
    rig.frame()
    # deck 1: player 1 moves pan.x, player 2's row on pan.y is dormant
    assert one.reg[PX].value > rest_one[0] and one.reg[PY].value == rest_one[1]
    # deck 2: player 2 moves pan.x, player 1's row on pan.y is dormant
    assert two.reg[PX].value < rest_two[0] and two.reg[PY].value == rest_two[1]
    # letting go of one moves nothing of the other's
    was = two.reg[PX].value
    rig.pad1.x = 0.5
    rig.frame()
    assert one.reg[PX].value == rest_one[0] and two.reg[PX].value == was


def test_a_controller_with_every_player_on_air_drives_deck_1_and_only_deck_1(rig):
    """The default: on air is deck 1. Deck 2's rows wait for a player."""
    one, two = rig.one, rig.two
    _two_patches(rig)
    rest_two = _pans(two)
    rig.pad1.x = rig.pad2.x = 1.0
    rig.frame()
    assert one.reg[PX].modulated and one.reg[PY].modulated
    assert _pans(two) == rest_two and not two.reg[PX].modulated


def test_coming_back_to_a_deck_starts_afresh(rig):
    meta, one = rig.meta, rig.one
    _two_patches(rig)
    rig.pad2.x = 1.0
    rig.frame()
    out = one.reg[PY].value
    meta.move_player(2, Duty.OFF_AIR)
    rig.frame()
    assert one.reg[PY].value != out and not one.reg[PY].modulated
    meta.move_player(2, Duty.ON_AIR)
    rig.frame()
    assert one.reg[PY].value == pytest.approx(out)


def test_a_gate_and_a_modifier_on_a_player_elsewhere_read_nothing(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    one.table.set_routes([*one.table.routes(),
                          Binding("lfo:0", PX, "push", 1.0, when="axis@p2:LT")])
    rig.frame()
    gate = next(b for b in one.table.routes() if b.when)
    rig.pad2.lanes = lambda: [0.5, 0.5, 0.5, 0.5, 1.0, 0.0]
    rig.frame()
    assert one.router.gated(gate) is True
    meta.move_player(2, Duty.OFF_AIR)
    rig.frame()
    assert one.router.gated(gate) is False
    assert one.router._reading("axis@p2:LT", None) is None
    assert two.router._reading("axis@p2:LT", None) == 1.0


def test_the_hands_go_with_whoever_holds_them(rig):
    """A hand is a scheme no one qualifies: its rows act where its holder is."""
    meta, one, two = rig.meta, rig.one, rig.two
    _routes(one, ("hand:right.grab", PX))
    _routes(two, ("hand:right.grab", PX))
    rig.frame()
    rest_one, rest_two = one.reg[PX].value, two.reg[PX].value
    rig.hands.grab = 1.0
    rig.frame()
    assert one.reg[PX].value != rest_one and two.reg[PX].value == rest_two
    meta.register("hands", 2)
    meta.move_player(2, Duty.OFF_AIR)
    rig.frame()
    assert one.reg[PX].value == rest_one and two.reg[PX].value != rest_two


def test_the_bridge_goes_with_whoever_holds_it(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    ctx = rig.devs.ctx
    bridge = devices.BridgeDevice("bridge", None, ctx, io=SimpleNamespace(
        reconnect=lambda: None, receive=lambda src: src.feed("ext", [1.0]),
        publish=lambda _src: None, send_values=lambda _values: None))
    rig.devs.devices.append(bridge)
    rig.devs._opened.add("bridge")
    rig.devs.point(meta.pointer, meta.panel_pointer)
    _routes(one, ("ext:0", PX))
    _routes(two, ("ext:0", PY))
    rig.frame()
    assert one.reg[PX].modulated and not two.reg[PY].modulated
    meta.register("bridge", 4)
    meta.move_player(4, Duty.OFF_AIR)
    rig.frame()
    assert two.reg[PY].modulated and not one.reg[PX].modulated


def test_the_analyzer_and_a_deck_s_own_lanes_are_nobody_s(rig):
    away = rig.one.sources.away_from(rig.two.router)
    assert {"axis", "axis@p2", "pair", "motion", "touch", "hand"} <= away
    assert "lane" not in away and "lfo" not in away and "env" not in away
    assert rig.one.sources.away_from(rig.one.router) == frozenset()


def test_a_view_hides_a_read_and_not_a_write():
    shared = {"axis": 1, "lane": 2}
    v = Layered({}, shared, frozenset({"axis"}))
    assert v.get("axis") is None and "axis" not in v and "lane" in v
    assert list(v) == ["lane"] and len(v) == 1
    with pytest.raises(KeyError):
        v["axis"]
    v["axis"] = 3
    assert shared["axis"] == 3


def test_a_view_pops_and_defaults_as_it_writes():
    """Finding 5: the inherited ones read first, so a hidden scheme stayed, or was overwritten."""
    shared = {"axis": 1}
    v = Layered({}, shared, frozenset({"axis"}))
    assert v.setdefault("axis", 9) == 1 and shared["axis"] == 1
    assert v.pop("axis", None) == 1 and "axis" not in shared
    assert v.pop("axis", None) is None
    with pytest.raises(KeyError):
        v.pop("axis")
    own = {}
    w = Layered(own, shared)
    assert w.setdefault("lfo", 5) == 5 and own == {"lfo": 5} and "lfo" not in shared
    assert w.pop("lfo") == 5 and not own


def test_the_hide_set_is_kept_until_a_pointer_moves_or_the_list_changes(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    src = one.sources
    got = src.away_from(two.router)
    assert src.away_from(two.router) is got      # no rebuild per cable
    assert "axis@p2" in got
    meta.move_player(2, Duty.OFF_AIR)
    assert "axis@p2" not in src.away_from(two.router)
    assert "axis@p2" in src.away_from(one.router)
    moved = src.away_from(two.router)
    rig.devs.apply(rig.devs.entries)             # an empty list: every device gone
    assert src.away_from(two.router) is not moved
    assert src.away_from(two.router) == frozenset()


def test_sources_with_no_registry_or_a_bare_one_hide_nothing():
    src = Sources()
    assert src.away_from(object()) == frozenset()
    src.use(SimpleNamespace(continuous_schemes=tuple))
    assert src.away_from(object()) == frozenset()


def test_a_listed_device_with_no_pointer_holds_nothing():
    d = devices.PadDevice("pad", io=Stick())
    assert devices.DeviceRegistry(devices=[d]).holders() == {}


def _cable(view, target):
    return next(c for c in view.cables
                if isinstance(c.ref, Binding) and c.ref.target == target)


def test_a_row_on_a_player_with_no_controller_is_dormant_and_drawn(rig):
    one = rig.one
    _routes(one, ("axis@p3:LX", PX))
    rig.frame()
    rest = one.reg[PX].value
    rig.frame()
    assert one.reg[PX].value == rest and not one.reg[PX].modulated
    assert any(w.role == "p3" and w.state == devices.MISSING
               for w in devices.wants(one.table, rig.devs))
    view = graphview.build(one.table, one.reg, one.router, rig.devs, None, None)
    node = view.node("device:p3")
    assert node is not None and node.placeholder
    assert _cable(view, PX).dormant


def test_a_row_on_a_player_on_the_other_deck_is_drawn_dormant_too(rig):
    meta, one = rig.meta, rig.one
    _routes(one, (TWO_STICK, PX))
    rig.pad2.x = 1.0
    rig.frame()
    live = graphview.build(one.table, one.reg, one.router, rig.devs, None, None)
    assert not _cable(live, PX).dormant
    meta.move_player(2, Duty.OFF_AIR)
    rig.frame()
    away = graphview.build(one.table, one.reg, one.router, rig.devs, None, None)
    assert _cable(away, PX).dormant


# ---------------------------------------------------------------- mid-press, a chase, a turn

def test_a_duty_change_mid_press_lets_go_on_the_deck_left(rig):
    """Through `routing.let_go_lost`: nothing stuck on deck 1, nothing fired on deck 2."""
    meta, one, two = rig.meta, rig.one, rig.two
    row = "pad@p2:VIEW"
    one.table.add(Binding(row, "view.lines", "momentary", layer="preset"))
    two.table.add(Binding(row, "view.lines", "momentary", layer="preset"))
    two_was = two.reg["view.lines"].value
    rig.pad2.press("VIEW")
    rig.frame()
    was = one.reg["view.lines"]
    assert was.value is True and was.__dict__["_pressed_by"] == {row}
    meta.move_player(2, Duty.OFF_AIR)
    rig.pad2.was = rig.pad2.held                # still down, the press already seen
    rig.frame()
    assert one.reg["view.lines"].value is False and not was.__dict__["_pressed_by"]
    assert two.reg["view.lines"].value == two_was
    rig.pad2.press()                            # the release has nothing to end on deck 2
    rig.frame()
    assert two.reg["view.lines"].value == two_was and one.reg["view.lines"].value is False
    rig.pad2.press("VIEW")                      # a new press acts there
    rig.frame()
    assert two.reg["view.lines"].value is True and one.reg["view.lines"].value is False


def test_an_osc_press_ends_on_the_deck_it_was_made_on(rig):
    """The press road D5a left: it knew its registry, and only asked when lost."""
    one, two = rig.one, rig.two
    source = "phone:hit"
    one.table.row_schemes = (*one.table.row_schemes, "phone")   # what its device tells the table
    for d in (one, two):
        d.table.add(Binding(source, "view.lines", "momentary", layer="preset"))
    d = osc.OscDevice("phone", {"hits": ["hit"]}, rig.devs.ctx, io=SimpleNamespace())
    d.heard, d.now = 0.0, 0.0                   # connected, for all it is asked here
    d.hits = [("hit", 1.0)]
    d.act(one.router)
    assert one.reg["view.lines"].value is True
    d.hits = []
    d.act(two.router)
    assert one.reg["view.lines"].value is False and not d._pressed
    assert not one.reg["view.lines"].__dict__["_pressed_by"]


def test_an_osc_device_closed_after_a_move_takes_its_lanes_with_it(rig):
    """Finding 5, where it was live: `close` pops through a router's views."""
    one, two = rig.one, rig.two
    one.sources.feed("phone", [0.5])
    rig.devs.holders()["phone"] = rig.meta.pointer("p2")
    rig.meta.move_player(2, Duty.OFF_AIR)
    router = one.router
    assert "phone" not in router.feeds
    d = osc.OscDevice("phone", {}, rig.devs.ctx, io=SimpleNamespace(close=lambda: None))
    d._router = router
    d.close()
    assert "phone" not in one.sources.feeds and "phone" not in two.router.feeds


def test_a_chase_follows_the_player_s_deck(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    _two_patches(rig)
    row = "pad@p2:VIEW"
    for d in (one, two):
        d.table.add(Binding(row, "deck.chase", "momentary", layer="preset"))
    meta.move_player(2, Duty.OFF_AIR)
    bases_one = _pan_bases(one)
    steps_one = len(one.undo.stack)
    rig.pad2.x = 1.0
    rig.pad2.press("VIEW")
    rig.frame()
    assert two.reg.chasing and not one.reg.chasing
    rig.frame(3)
    pushed = two.reg[PX].value
    rig.pad2.press()
    rig.frame()
    assert not two.reg.chasing
    rig.pad2.x = 0.5                            # the look stays, on deck 2
    rig.frame()
    assert two.reg[PX].base == pytest.approx(pushed) and two.reg[PX].value == pytest.approx(pushed)
    assert _pan_bases(one) == bases_one
    assert len(one.undo.stack) == steps_one
    assert [s.label for s in two.undo.stack].count(CHASE_LABEL) == 1


def test_a_chase_held_when_the_player_moves_ends_on_the_deck_it_held(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    _two_patches(rig)
    row = "pad@p2:VIEW"
    for d in (one, two):
        d.table.add(Binding(row, "deck.chase", "momentary", layer="preset"))
    rig.pad2.press("VIEW")
    rig.frame()
    assert one.reg.chasing
    meta.move_player(2, Duty.OFF_AIR)
    rig.pad2.was = rig.pad2.held
    rig.frame()
    assert not one.reg.chasing and not two.reg.chasing


def _turning(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    for d in (one, two):
        d.table.set_routes([*d.table.routes(), Binding(YAW, "camera.yaw", TURN_OP, 1.0, when=GRAB)])
    rig.hands.grab = 1.0
    meta.register("hands", 2)
    return meta, one, two


def test_a_turn_acts_on_the_deck_its_player_is_on_and_does_not_jump_on_the_other(rig):
    meta, one, two = _turning(rig)
    rig.hands.yaw = 0.25
    rig.frame()                                 # its first frame only reads
    y1, y2 = one.reg["camera.yaw"].base, two.reg["camera.yaw"].base
    rig.hands.yaw = 0.30
    rig.frame()
    y1b = one.reg["camera.yaw"].base
    assert y1b != y1 and two.reg["camera.yaw"].base == y2      # on air: deck 1 only
    meta.move_player(2, Duty.OFF_AIR)
    rig.hands.yaw = 0.60                        # a long way, between frames
    rig.frame()
    assert one.reg["camera.yaw"].base == y1b    # dormant at once
    assert two.reg["camera.yaw"].base == y2     # its first frame there only reads
    rig.hands.yaw = 0.62
    rig.frame()
    assert one.reg["camera.yaw"].base == y1b and two.reg["camera.yaw"].base != y2


def test_the_turn_left_behind_closes_its_undo_step_on_its_own_deck(rig):
    meta, one, _two = _turning(rig)
    rig.hands.yaw = 0.25
    rig.frame()
    rig.hands.yaw = 0.30
    rig.frame()
    assert one.router.__dict__["_turn_held"]
    meta.move_player(2, Duty.OFF_AIR)
    rig.frame(round((TURN_GRACE_S + 0.1) / DT))
    assert not one.router.__dict__["_turn_held"]
    assert one.undo._kept is None


# ---------------------------------------------------------------- mapping moves it

def test_mapping_a_controller_on_the_other_deck_moves_it_there(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    two.learn.mapped = lambda b: rig.devs.mapped(two, b)
    meta.point_panel(two)
    two.learn.arm("view.lines", "pad")
    two.learn.learn_pad_button("pad@p2:VIEW")
    meta.point_panel(one)
    assert meta.pointer("p2").deck is two and meta.pointer("pad").deck is one
    assert meta.players.player_of("p2").duty == Duty.ON_AIR       # the player did not move
    rig.frame()
    meta.move_player(2, Duty.ON_AIR)            # no change of duty: where it is stands…
    meta.place_players()                        # …until the players are placed
    assert meta.pointer("p2").deck is one


def test_the_same_axis_learned_again_on_the_other_deck_moves_it_too(rig):
    """Finding 7: it said "learned", and the pad stayed away with the row dead."""
    meta, two = rig.meta, rig.two
    two.learn.mapped = lambda b: rig.devs.mapped(two, b)
    _routes(two, (TWO_STICK, PX))
    two.learn.arm(PX)
    two.learn.learn_source(TWO_STICK)
    assert meta.pointer("p2").deck is two
    assert len([b for b in two.table.routes() if b.target == PX]) == 1


def test_a_learn_that_makes_no_row_moves_nothing(rig):
    two = rig.two
    seen = []
    two.learn.mapped = seen.append
    two.learn.arm("view.lines", "hand:left")     # not this pad's to complete
    assert two.learn.learn_pad_button("pad@p2:VIEW") is False
    two.learn.arm(SAVE_PARAM)                    # refused on any button
    assert two.learn.learn_pad_button("pad@p2:VIEW") is False
    assert seen == [] and rig.meta.pointer("p2").deck is rig.one


def test_each_learn_road_says_what_it_made(rig):
    one = rig.one
    seen = []
    one.learn.mapped = seen.append
    one.learn.arm("view.lines", "pad")
    one.learn.learn_pad_button("pad:VIEW")
    assert [b.source for b in seen] == ["pad:VIEW"]
    one.learn.arm(PX)
    one.learn.learn_source("hand:right.grab")
    assert seen[-1].source == "hand:right.grab"


def test_controller_of_finds_a_row_s_device(rig):
    one = rig.one
    of = rig.devs.controller_of
    assert of(one.table, Binding("pad@p2:A", "view.lines", "toggle")).role == "p2"
    assert of(one.table, Binding("axis:LX", PX, "push", 1.0)).role == "pad"
    assert of(one.table, Binding(GRAB, PX, "push", 1.0)).role == "hands"
    assert of(one.table, Binding("lfo:0", PX, "push", 1.0)) is None


# ---------------------------------------------------------------- the totem's angle, the poi's home

@pytest.fixture()
def shared(rig):
    state, swing = totem.TotemState(), poi.PoiState()
    totem.register(rig.one.reg, state)
    poi.register(rig.one.reg, swing, {})
    app._share_experiments(rig.one.reg, rig.two.reg, poi_cfg={})
    rig.state, rig.swing = state, swing
    return rig


def _turn(pad, reg, state, frames=30):
    for _ in range(frames):
        pad.frame(gyro=(0.0, 0.0, 200.0))
        totem.step(state, pad, reg, DT, "pad")


def test_a_turn_on_deck_2_does_not_jump_deck_1s_phase(shared):
    """The bug: one `ang` across decks. Turn on 2, point back to 1, and 1 jumped."""
    one, two, state = shared.one, shared.two, shared.state
    one.reg["rot.phase.XY"].set(0.3)
    two.reg["rot.phase.XY"].set(-0.7)
    state.on = True
    pad = FakePad()
    _turn(pad, two.reg, state)
    turned = two.reg["rot.phase.XY"].base
    assert turned != pytest.approx(-0.7) and one.reg["rot.phase.XY"].base == 0.3
    _turn(pad, one.reg, state, frames=1)        # pointed back
    assert one.reg["rot.phase.XY"].base == pytest.approx(0.3)   # adopted: nothing jumps
    assert two.reg["rot.phase.XY"].base == turned
    assert state.on_reg is one.reg
    _turn(pad, one.reg, state)
    assert one.reg["rot.phase.XY"].base != pytest.approx(0.3)
    assert two.reg["rot.phase.XY"].base == turned


def test_every_phase_stays_on_its_deck(shared):
    one, two, state = shared.one, shared.two, shared.state
    for i, n in enumerate(totem.PLANES):
        one.reg[f"rot.phase.{n}"].set(0.1 * i)
        two.reg[f"rot.phase.{n}"].set(-0.1 * i)
    state.on = True
    pad = FakePad()
    _turn(pad, two.reg, state)
    _turn(pad, one.reg, state, frames=1)
    for i, n in enumerate(totem.PLANES):
        assert one.reg[f"rot.phase.{n}"].base == pytest.approx(0.1 * i)


def test_the_tilt_goes_back_to_the_deck_it_was_added_to(shared):
    one, two, state = shared.one, shared.two, shared.state
    state.on = True
    pad = FakePad()
    tilted = (0.5, 0.86, 0.0)
    pad.frame(accel=(0.0, 1.0, 0.0))
    totem.step(state, pad, two.reg, DT, "pad")
    for _ in range(40):
        pad.frame(accel=tilted)
        totem.step(state, pad, two.reg, DT, "pad")
    assert any(state.pan_out)
    p1, p2 = one.reg[PX].base, two.reg[PX].base
    assert p2 != 0.0
    pad.frame(accel=(0.0, 1.0, 0.0))
    totem.step(state, pad, one.reg, DT, "pad")
    assert two.reg[PX].base == pytest.approx(0.0, abs=1e-9)     # given back where it was added
    assert one.reg[PX].base == p1


def test_switching_off_on_the_other_deck_gives_the_pan_back_where_it_was(shared):
    one, two, state = shared.one, shared.two, shared.state
    state.on = True
    pad = FakePad()
    pad.frame(accel=(0.0, 1.0, 0.0))
    totem.step(state, pad, two.reg, DT, "pad")
    for _ in range(40):
        pad.frame(accel=(0.5, 0.86, 0.0))
        totem.step(state, pad, two.reg, DT, "pad")
    assert two.reg[PX].base != 0.0
    one.reg["totem.on"].set(False)              # the panel on deck 1
    assert two.reg[PX].base == pytest.approx(0.0, abs=1e-9) and one.reg[PX].base == 0.0


def test_a_reset_of_the_other_deck_leaves_the_angles_alone(shared):
    one, two, state = shared.one, shared.two, shared.state
    state.on = True
    two.reg["rot.phase.XY"].set(0.5)
    pad = FakePad()
    _turn(pad, two.reg, state)
    turned = two.reg["rot.phase.XY"].base
    one.reg["rot.phase.XY"].set(0.3)
    one.reg["totem.reset"].fire()               # the panel on deck 1
    assert one.reg["rot.phase.XY"].base == 0.0
    _turn(pad, two.reg, state, frames=1)
    assert two.reg["rot.phase.XY"].base == pytest.approx(turned, abs=0.1)
    assert one.reg["rot.phase.XY"].base == 0.0


def test_the_pad_device_carries_the_totem_to_the_player_s_deck(shared):
    meta, one, two, state = shared.meta, shared.one, shared.two, shared.state
    one.reg["rot.phase.XY"].set(0.3)
    two.reg["rot.phase.XY"].set(-0.7)
    state.on = True
    shared.frame()
    assert state.driving is not None and state.on_reg is one.reg
    meta.move_player(1, Duty.OFF_AIR)
    shared.frame()
    assert state.on_reg is two.reg
    assert two.reg["rot.phase.XY"].base == pytest.approx(-0.7)
    assert one.reg["rot.phase.XY"].base == pytest.approx(0.3)
    meta.move_player(1, Duty.ON_AIR)
    shared.frame()
    assert state.on_reg is one.reg and one.reg["rot.phase.XY"].base == pytest.approx(0.3)


def test_the_pad_with_the_camera_job_is_the_first_on_its_deck(rig, monkeypatch):
    """Finding 8: with everyone on air the first pad's alone, as ever; a player off
    air has a stick that orbits; the only pad given to player 2 keeps its job."""
    meta, one, two = rig.meta, rig.one, rig.two
    steered = []
    monkeypatch.setattr(gamepad, "steer",
                        lambda pad, router, *a, scheme="axis", **k: steered.append((pad, router, scheme)))
    rig.frame()
    assert steered == [(rig.pad1, one.router, "axis")]
    steered.clear()
    meta.move_player(2, Duty.OFF_AIR)
    rig.frame()
    assert steered == [(rig.pad1, one.router, "axis"), (rig.pad2, two.router, "axis@p2")]
    steered.clear()
    meta.move_player(1, Duty.OFF_AIR)
    rig.frame()
    assert steered == [(rig.pad1, two.router, "axis")]         # one on a deck


def test_the_only_pad_given_to_player_2_steers_and_it_is_said(rig, monkeypatch):
    players = rig.meta.players
    players.hold("pad", 2)
    ctx = devices.Context(reg=rig.one.reg, table=rig.one.table, players=players)
    (d,) = devices.make_all([_pad("pad")], ctx)
    assert d.qualifier == "p2"
    d.io = rig.pad1
    devs = devices.DeviceRegistry(devices=[d], ctx=ctx)
    assert any("no pad is player 1's" in n for n in devs.notes)
    devs.point(rig.meta.pointer, rig.meta.panel_pointer)
    rig.one.router.use(devs)
    steered = []
    monkeypatch.setattr(gamepad, "steer", lambda pad, *a, **k: steered.append(pad))
    devs.poll(DT, 0.0, router=rig.one.router)
    assert steered == [rig.pad1]
    _routes(rig.one, (ONE_STICK, PX))
    wanted = {w.role: w.state for w in devices.wants(rig.one.table, devs)}
    assert wanted["player 1"] == devices.MISSING and "pad" not in wanted


def test_the_steering_second_pad_reads_its_own_lanes(rig):
    rig.meta.move_player(2, Duty.OFF_AIR)
    rig.pad2.axis = lambda i: 1.0 if i == gamepad.AX_LX else 0.0
    was, one_was = rig.two.reg["camera.yaw"].base, rig.one.reg["camera.yaw"].base
    rig.frame(5)
    assert rig.two.reg["camera.yaw"].base != was
    assert rig.one.reg["camera.yaw"].base == one_was


def _swing(pad, reg, state, frames=30):
    for _ in range(frames):
        pad.frame(gyro=(0.0, 0.0, 200.0))
        poi.step(state, pad, reg, DT, "pad")


def test_the_poi_leaves_a_deck_at_home_and_writes_only_the_next(shared):
    one, two, swing = shared.one, shared.two, shared.swing
    one.reg[PX].set(0.25)
    two.reg[PX].set(-0.25)
    two_zoom, one_zoom = two.reg["camera.zoom"].base, one.reg["camera.zoom"].base
    swing.on = True
    pad = FakePad()
    _swing(pad, two.reg, swing)
    assert swing.on_reg is two.reg
    assert one.reg[PX].base == 0.25 and two.reg[PX].base != -0.25
    _swing(pad, one.reg, swing, frames=1)       # pointed back
    assert swing.on_reg is one.reg
    assert two.reg[PX].base == pytest.approx(-0.25)             # home
    assert two.reg["camera.zoom"].base == pytest.approx(two_zoom)
    assert swing.pan_home[0] == pytest.approx(0.25)             # this deck's home, not that one's
    _swing(pad, one.reg, swing)
    assert two.reg[PX].base == pytest.approx(-0.25)
    one.reg["poi.on"].set(False)
    assert one.reg[PX].base == pytest.approx(0.25)
    assert one.reg["camera.zoom"].base == pytest.approx(one_zoom)


def test_a_poi_whose_sensors_dropped_still_leaves_its_deck_at_home(shared):
    """Finding 4: `driving` was None by then, so the old deck stayed displaced and
    its homes went to the new one."""
    one, two, swing = shared.one, shared.two, shared.swing
    one.reg[PX].set(0.25)
    two.reg[PX].set(-0.25)
    zoom = one.reg["camera.zoom"].base
    swing.on = True
    pad = FakePad()
    _swing(pad, one.reg, swing)
    assert one.reg[PX].base != 0.25
    pad.on = False
    poi.step(swing, pad, one.reg, DT, "pad")     # the sensors go quiet
    assert swing.driving is None and swing.on_reg is one.reg
    pad.on = True
    _swing(pad, two.reg, swing, frames=1)        # back, on the other deck
    assert one.reg[PX].base == pytest.approx(0.25)
    assert one.reg["camera.zoom"].base == pytest.approx(zoom)
    assert swing.pan_home[0] == pytest.approx(-0.25) and swing.on_reg is two.reg


def test_switching_the_poi_off_on_the_other_deck_sends_home_where_it_swung(shared):
    one, two, swing = shared.one, shared.two, shared.swing
    two.reg[PX].set(-0.25)
    swing.on = True
    pad = FakePad()
    _swing(pad, two.reg, swing)
    one.reg["poi.on"].set(False)
    assert two.reg[PX].base == pytest.approx(-0.25)


def test_the_poi_owns_the_pan_only_on_its_own_deck(shared):
    one, two, swing, state = shared.one, shared.two, shared.swing, shared.state
    swing.on = True
    assert poi.owns_pan(one.reg) and poi.owns_pan(two.reg)      # before it has a deck
    _swing(FakePad(), two.reg, swing, frames=1)
    assert poi.owns_pan(two.reg) and not poi.owns_pan(one.reg)
    state.on = True
    pad = FakePad()
    pad.frame(accel=(0.0, 1.0, 0.0))
    totem.step(state, pad, one.reg, DT, "other")
    for _ in range(40):
        pad.frame(accel=(0.5, 0.86, 0.0))
        totem.step(state, pad, one.reg, DT, "other")
    assert one.reg[PX].base != 0.0              # the totem's tilt on the deck the poi is not on


# ---------------------------------------------------------------- every player on air: as before

def _run_sticks(r, *, players):
    """One rig through a corpus loadable patch and pushed sticks, with or without the players."""
    second = Deck.beside(r.deck)
    ctx = devices.Context(reg=r.deck.reg, table=r.deck.table)
    pad = Stick()
    d = devices.PadDevice("pad", None, ctx, io=pad)
    devs = devices.DeviceRegistry(devices=[d], ctx=ctx)
    if players:
        meta = MetaController(r.deck, second)
        devs.point(meta.pointer, meta.panel_pointer)
    r.deck.router.use(devs)
    out = []
    router = r.deck.router
    _routes(r.deck, (ONE_STICK, PX), ("axis:RY", PY))
    for k in range(40):
        pad.motion.step((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), DT)
        pad.x = 0.5 + 0.5 * ((k % 10) / 10)
        devs.poll(DT, k * DT, router=router)
        devs.feed(r.deck.sources)
        router.modulate(None, DT, k * DT)
        r.deck.reg.apply()
        # (`preset.select` reads the deck off air's slot once there are two decks: a pad's
        # light, row 700, nothing of this deck's)
        out.append({p.id: repr(p.value) for p in r.deck.reg
                    if p.group not in ("ui", "panel") and p.id != "preset.select"})
    return out


def test_every_player_on_air_is_to_the_bit_what_no_players_was(tmp_path):
    plain = _run_sticks(boot(tmp_path / "a"), players=False)
    undo.install(None)
    pointed = _run_sticks(boot(tmp_path / "b"), players=True)
    undo.install(None)
    assert pointed == plain


def test_every_corpus_loadable_lands_as_before_with_players_and_a_list(tmp_path):
    """D5a's walk, its proof extended: a registry whose controllers are all player
    1's, on air, on deck 1."""
    home = tmp_path / "home"
    plain = _walk(boot(home))
    r = boot(home)
    p = _pointed(r)
    pad = devices.PadDevice("pad", None, devices.Context(reg=r.deck.reg, table=r.deck.table),
                            io=Stick())
    devs = devices.DeviceRegistry(devices=[pad, Hands()], ctx=pad.ctx)
    devs.point(p.meta.pointer, p.meta.panel_pointer)
    r.deck.router.use(devs)
    assert r.deck.sources.away_from(r.deck.router) == frozenset()
    undo.install(r.undo)
    _compare(_walk(r), plain, exact=True)


def test_let_go_lost_is_the_one_door_the_pad_goes_through(rig, monkeypatch):
    seen = []
    real = routing.let_go_lost
    monkeypatch.setattr(routing, "let_go_lost", lambda reg, lost: (seen.append(reg), real(reg, lost)))
    rig.one.table.add(Binding("pad@p2:VIEW", "view.lines", "momentary", layer="preset"))
    rig.pad2.press("VIEW")
    rig.frame()
    rig.meta.move_player(2, Duty.OFF_AIR)
    rig.frame()
    assert seen == [rig.one.reg]


# ---------------------------------------------------------------- the list both Macs share (CT1)

class Counted(devices.Base):
    """A controller that says when it is opened and closed."""

    kind = "counted"
    feeds = ()
    log: list[str] = []

    def open(self):
        self.io = object()
        Counted.log.append(f"open {self.role}")

    def close(self):
        self.io = None
        Counted.log.append(f"close {self.role}")

    @property
    def status(self):
        return "connected" if self.io is not None else "lost"


@pytest.fixture()
def listed(tmp_path, monkeypatch):
    """A real registry over a real list, in a scratch library, on stand-in controllers."""
    Counted.log = []
    real = devices.kinds
    monkeypatch.setattr(devices, "kinds", lambda: {**real(), "gamepad": Counted, "midi": Counted})
    root, home = tmp_path / "Drive", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    seed = [{"role": "pad", "kind": "gamepad"}, {"role": "apc40", "kind": "midi"}]
    store = devicelist.DeviceList(root, home, seed=seed)
    ctx = devices.Context(players=Players(home / FILE))
    reg = devices.DeviceRegistry(store.checked()[0], ctx, store=store)
    reg.open_all()
    Counted.log.clear()
    return SimpleNamespace(root=root, store=store, reg=reg, players=ctx.players)


def _lands(root, raw):
    (root / devicelist.FILE).write_text(json.dumps({"schema": devicelist.SCHEMA, "devices": raw}))


def test_the_registry_watches_the_list_not_config_toml(listed):
    r = listed
    _lands(r.root, [*r.store.raw, {"role": "xbox", "kind": "gamepad", "controller": "xbox"}])
    assert r.reg.watch()
    assert [d.role for d in r.reg] == ["pad", "apc40", "xbox"]
    assert Counted.log == ["open xbox"], "what was there is not touched"
    assert not r.reg.watch()


def test_a_list_that_will_not_read_closes_nothing(listed):
    r = listed
    (r.root / devicelist.FILE).write_text('{"schema": "devices/1", "dev')
    assert not r.reg.watch()
    assert [d.role for d in r.reg] == ["pad", "apc40"] and not Counted.log
    assert r.reg.get("pad").io is not None


def test_the_drive_going_away_closes_nothing(listed):
    r = listed
    (r.root / devicelist.FILE).unlink()
    r.root.rmdir()
    for _ in range(3):
        assert not r.reg.watch()
    assert [d.role for d in r.reg] == ["pad", "apc40"] and not Counted.log
    assert "isn't there" in r.store.said


def test_a_bad_entry_from_the_other_mac_is_said_and_the_old_list_stands(listed):
    r = listed
    _lands(r.root, [*r.store.raw, {"role": "no:colon", "kind": "gamepad"}])
    assert not r.reg.watch()
    assert [d.role for d in r.reg] == ["pad", "apc40"] and not Counted.log
    assert any("the old list stands" in n for n in r.reg.notes)


def test_adopting_opens_only_the_new_one_and_a_change_from_the_other_mac_keeps_it(listed):
    r = listed
    role = r.store.adopt({"role": "xbox", "kind": "gamepad", "controller": "xbox"})
    r.players.hold(role, 2)
    assert r.reg.relist()
    assert Counted.log == ["open xbox"]
    assert [d.role for d in r.reg] == ["pad", "apc40", "xbox"]
    # the other Mac's copy, from before the adopt, lands with its own new one
    _lands(r.root, [{"role": "pad", "kind": "gamepad"}, {"role": "apc40", "kind": "midi"},
                    {"role": "edge", "kind": "gamepad", "controller": "edge"}])
    assert r.reg.watch()
    assert {d.role for d in r.reg} == {"pad", "apc40", "xbox", "edge"}, "the adopt stands"
    assert "close xbox" not in Counted.log
    assert not r.reg.watch(), "and nobody takes turns"


def test_the_first_look_for_midi_is_before_any_frame_unless_this_mac_said_no(tmp_path, monkeypatch):
    looks = []
    monkeypatch.setattr(app, "port_names", lambda: looks.append(1))
    cfg = {"devices": [], "notes": []}
    app._open_devices(cfg, devices.Context(), None)
    assert looks == [1]
    app._open_devices({**cfg, "no_midi_look": True}, devices.Context(), None)
    assert looks == [1]
