"""tools/app_driver.py's script for node mode on a pad (plan 53 N2): the real app, a stand-in pad.

The chip clicked, the rows on the node, a stick moving the param and the view leaving that stick and
no other, an LFO's route resting and coming back, the pad window saying what the stick holds, and
leaving by the other chip. Run from `hyperspace-python/`, once for a pad and once for a Joy-Con, whose
stick would read NaN with the totem off if `PadDevice.quiet_stick` did not stand down:

    uv run python tools/app_driver.py tools/drive_node_mode_pad.py --out <scratch>/pad --every 30
    NODE_PAD=joycon-l uv run python tools/app_driver.py tools/drive_node_mode_pad.py --out <scratch>/joy

Each step's words go to stderr, and a step that doesn't do what it should stops the run. Touches no
`~/Hyperspace`: the driver's home is a fresh one. A stand-in proves the app's half: the pad itself is
hand checks 635-637.
"""

import os
import sys

from hyperspace import devices, gamepad, nodemode, ui_pad
from hyperspace.pads.models import MODELS
from hyperspace.routing import Binding

ROLE = "pad"
CHIP = f"graph.side.node_mode.{ROLE}"
MODEL = MODELS[os.environ.get("NODE_PAD", "x360")]
AT_REST = (0.0, 0.0, 0.0, 0.0, -1.0, -1.0)
RIGHT = (1.0, 0.0, 0.0, 0.0, -1.0, -1.0)
BOTH = (1.0, 1.0, 0.0, 0.0, -1.0, -1.0)


def say(*a):
    print(f"node mode on {MODEL.id}:", *a, file=sys.stderr, flush=True)


class StandIn(gamepad.Pad):
    """A real `Pad` whose stick is where the script puts it."""

    def __init__(self):
        super().__init__()
        self.source, self.model = "usb", MODEL
        self.axes = list(AT_REST)
        self.buttons = [0] * gamepad.N_BUTTONS

    def poll(self, dt=0.0):
        self.prev_buttons, self.prev_hat = self.buttons, self.hat


def _pad(panel):
    """A stand-in pad, as `app.main` would have listed it, on the panel's deck."""
    meta, reg_ = panel.meta, panel.devices
    io = StandIn()
    dev = devices.PadDevice(ROLE, {}, reg_.ctx, io=io)
    reg_.devices.append(dev)
    reg_._opened.add(ROLE)              # (open already: it is this)
    dev.point(meta.pointer(ROLE), meta.panel_pointer)
    panel.pad = io
    return meta.panel, io


def _node(deck) -> tuple[str, str]:
    """A node to point at, and the param the first axis will hold."""
    patch = deck.loaded_patch
    for n in ("render:pattern", *sorted(patch._pointable(), reverse=True)):
        params = nodemode.fillable(deck.reg, patch.node_params(n), routed=True)
        kept = {b.target for b in deck.table.bindings if not b.is_modulator_route}
        free = [p for p in params if p not in kept]
        if free and n.startswith("render:"):
            return n, free[0]
    raise SystemExit("no node to point at")


def _span(deck, pid, d, frames=60):
    """How far `pid` moved over some frames."""
    p = deck.reg[pid]
    seen = []
    for _ in range(frames):
        yield from d.wait(1)
        seen.append(p.eff_norm)
    return max(seen) - min(seen)


def script(d, panel):
    deck, io = _pad(panel)
    yield from d.wait(3)
    node, pid = _node(deck)
    table, reg = deck.table, deck.reg
    say(f"deck's patch {deck.loaded_patch.current!r}, node {node}, the first axis will hold {pid}")

    # an LFO's route on the param the stick will hold, and it moves it
    route = Binding("lfo:0", pid, "push", 0.4)
    table.set_routes([*(b for b in table.routes() if b.target != pid), route])
    reg[pid].set_norm(0.5)
    saved = route.to_json()
    reg["lfo.1.sync"].set(0)                        # free-running: no tempo to wait for
    reg["lfo.1.rate"].set_norm(0.9)
    reg["lfo.1.depth"].set_norm(1.0)
    moved = yield from _span(deck, pid, d)
    say(f"the route rides: {pid} moved {moved:.3f} over 60 frames")
    assert moved > 0.01

    # the view has the stick, before
    yaw = reg["camera.yaw"].base
    io.axes = list(RIGHT)
    yield from d.wait(10)
    io.axes = list(AT_REST)
    assert reg["camera.yaw"].base != yaw, "the view was not on the stick"
    yield from d.wait(2)

    # the chip, clicked
    panel.select_graph_node(node)
    yield from d.wait(4)
    yield from d.reveal(CHIP)
    yield from d.click(CHIP)
    yield from d.wait(3)
    assert deck.loaded_patch.node_mode.of(1, "gamepad") == node, "the chip wrote nothing"
    rows = table.node_rows(ROLE)
    assert rows and rows[0].source == "axis:LX" and rows[0].target == pid
    say(f"chip clicked: node_mode saved, {len(rows)} rows on {node}: "
        + ", ".join(f"{b.source} → {b.target}" for b in rows[:4]))
    assert not any(b is x for b in rows for x in table.bindings)

    # a hot reload of what holds it (HR's real swap): nothing goes
    reloader = panel.reloader
    for name in ("devices", "node_desk"):
        reloader.status, reloader.error = "", ""
        reloader._mtimes[name] = 0.0                # as if the module had just been saved
        for _ in range(4000):
            if reloader.status.startswith("hot:") or reloader.error:
                break
            yield
        assert not reloader.error, f"reloading {name}: {reloader.error}"
        # the swap puts a pad's reader on `gamepad.Pad` (`PadDevice.targets`), as it should a
        # real one; this one is a stand-in with no hardware behind it, so it goes back
        if type(io) is not StandIn:
            io.__class__, io.source, io.model = StandIn, "usb", MODEL
        yield from d.wait(3)
        after = table.node_rows(ROLE)
        say(f"reloaded {name}: {len(after)} rows, the same {[b.source for b in after] == [b.source for b in rows]}")
        assert [(b.source, b.target) for b in after] == [(b.source, b.target) for b in rows]
    rows = table.node_rows(ROLE)

    # a route at rest
    assert table.node_holds(route)
    still = yield from _span(deck, pid, d, 30)
    say(f"the route rests: {pid} moved {still:.6f} over 30 frames")
    assert still == 0.0
    assert any(b is route for b in table.routes()) and route.to_json() == saved

    # the stick moves the param, and the view leaves the axes filled
    p = reg[pid]
    held_second = len(rows) > 1
    p.set_norm(0.5)
    yaw, pitch = reg["camera.yaw"].base, reg["camera.pitch"].base
    io.axes = list(BOTH)
    yield from d.wait(40)
    say(f"stick over: {pid} shows {p.eff_norm:.3f}, base {p.base:.3f}; yaw moved "
        f"{reg['camera.yaw'].base - yaw:.4f}, pitch {reg['camera.pitch'].base - pitch:.4f}")
    assert p.eff_norm > 0.75, "the stick did not reach the param"
    assert reg["camera.yaw"].base == yaw, "the view orbits under a held stick"
    if held_second:
        assert reg["camera.pitch"].base == pitch, "the view orbits under a held stick"
    io.axes = list(AT_REST)
    yield from d.wait(40)
    say(f"let go: {pid} shows {p.eff_norm:.3f}")
    assert abs(p.eff_norm - 0.5) < 0.02, "the look did not come back on release"

    # the pad window says what it holds, in the node mode's own colour
    panel.reg["ui.pad_diagram"].set(True)
    yield from d.wait(3)
    st = ui_pad._state(panel)
    assert len(st.get("filled", ())) == len(rows)
    word = rows[0].words
    said = ui_pad.rows(table, MODEL, ROLE)["axis:LX"]
    say(f"the window: {len(st['filled'])} filled, LX says {word!r}; words on its map: "
        f"{any(word in w for w in st.get('labels', ()))}")
    assert said is rows[0]
    assert not ui_pad._stick_quiet(panel, "axis:LX")
    panel.reg["ui.pad_diagram"].set(False)
    yield from d.wait(2)

    # leave, by the chip that says so: the route comes back, unedited, and the view its stick
    yield from d.click(CHIP)
    yield from d.wait(3)
    assert not table.node_rows(ROLE) and not table.node_holds(route)
    assert deck.loaded_patch.node_mode.of(1, "gamepad") is None
    back = yield from _span(deck, pid, d)
    say(f"left: no rows, route as saved {route.to_json() == saved}, {pid} moved {back:.3f}")
    assert back > 0.01 and route.to_json() == saved
    yaw = reg["camera.yaw"].base
    io.axes = list(RIGHT)
    yield from d.wait(10)
    io.axes = list(AT_REST)
    assert reg["camera.yaw"].base != yaw, "the view did not get its stick back"
    say("all good")
