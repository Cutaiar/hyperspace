"""tools/app_driver.py's script for node mode (plan 53 N1): the real app, an APC40 on fake ports.

The chip clicked, the rows on the node, a knob moving the param, its ring following, an LFO's route
resting and coming back, and leaving by the other chip. Run from `hyperspace-python/`:

    uv run python tools/app_driver.py tools/drive_node_mode.py --out <scratch>/run --every 30

Each step's words go to stderr, and a step that doesn't do what it should stops the run. Touches no
`~/Hyperspace`: the driver's home is a fresh one. A fake port proves the app's half: the desk itself
is hand check 541.
"""

import sys

import mido

from hyperspace import devices, node_desk, nodemode
from hyperspace.midi import MidiIO
from hyperspace.routing import Binding

ROLE = "apc40"
K1 = 0x30
CHIP = f"graph.side.node_mode.{ROLE}"


def say(*a):
    print("node mode:", *a, file=sys.stderr, flush=True)


class In:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)


class Out:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


def _desk(panel):
    """An APC40 on fake ports, as `app.main` would have listed it, on deck 1."""
    meta, reg_ = panel.meta, panel.devices
    deck = meta.panel
    inp, out = In(), Out()
    for d in meta.decks:
        d.table.midi_roles = (ROLE,)
    io = MidiIO(deck.reg, deck.table, inp=inp, out=out, learner=deck.learn, role=ROLE)
    desk = devices.MidiDevice(ROLE, {"profile": "apc40"}, reg_.ctx, io=io)
    reg_.devices.append(desk)
    reg_._opened.add(ROLE)              # (open already: its ports are these)
    desk.point(meta.pointer(ROLE), meta.panel_pointer)
    return deck, inp, out


def _node(deck) -> tuple[str, str]:
    """A node to point at, with the modulatable param its K1 will hold."""
    patch = deck.loaded_patch
    for n in ("render:pattern", *sorted(patch._pointable(), reverse=True)):
        params = nodemode.fillable(deck.reg, patch.node_params(n))
        kept = node_desk.NodeDesk._kept(deck.table.node_desk, set(params))     # rows that stay
        free = [p for p in params if p not in {t for _, t in kept}]
        if free and deck.reg[free[0]].modulatable and n.startswith("render:"):
            return n, free[0]
    raise SystemExit("no node to point at")


def _ring(out) -> int | None:
    """The last ring value K1 was sent."""
    got = [m.value for m in out.sent if m.type == "control_change" and m.control == K1]
    return got[-1] if got else None


def _span(deck, pid, d, frames=60):
    """How far `pid` moved over some frames."""
    p = deck.reg[pid]
    seen = []
    for _ in range(frames):
        yield from d.wait(1)
        seen.append(p.eff_norm)
    return max(seen) - min(seen)


def script(d, panel):
    deck, inp, out = _desk(panel)
    yield from d.wait(3)
    node, pid = _node(deck)
    table = deck.table
    say(f"deck's patch {deck.loaded_patch.current!r}, node {node}, K1 will hold {pid}")

    # an LFO's route on the param K1 will hold, and it moves it
    route = Binding("lfo:0", pid, "push", 0.4)
    table.set_routes([*(b for b in table.routes() if b.target != pid), route])
    deck.reg[pid].set_norm(0.5)
    saved = route.to_json()
    deck.reg["lfo.1.sync"].set(0)                   # free-running: no tempo to wait for
    deck.reg["lfo.1.rate"].set_norm(0.9)
    deck.reg["lfo.1.depth"].set_norm(1.0)
    moved = yield from _span(deck, pid, d)
    say(f"the route rides: {pid} moved {moved:.3f} over 60 frames")
    assert moved > 0.01

    # the chip, clicked
    panel.select_graph_node(node)
    yield from d.wait(4)
    yield from d.reveal(CHIP)
    yield from d.click(CHIP)
    yield from d.wait(3)
    assert deck.loaded_patch.node_mode.of(1, "midi") == node, "the chip wrote nothing"
    rows = table.node_rows(ROLE)
    assert rows and rows[0].target == pid and rows[0].source == f"cc:0:{K1}"
    say(f"chip clicked: node_mode saved, {len(rows)} rows on {node}; K1 → {rows[0].target}")

    # a route at rest
    assert table.node_holds(route)
    still = yield from _span(deck, pid, d, 30)
    say(f"the route rests: {pid} moved {still:.6f} over 30 frames")
    assert still == 0.0
    assert any(b is route for b in table.routes()) and route.to_json() == saved

    # the knob moves the param
    p = deck.reg[pid]
    before = p.norm
    want = 0.16 if before > 0.5 else 0.84
    mark = len(out.sent)
    for v in range(int(before * 127), int(want * 127), 4 if want > before else -4):
        inp.queue.append(mido.Message("control_change", channel=0, control=K1, value=v))
        yield from d.wait(1)
    inp.queue.append(mido.Message("control_change", channel=0, control=K1, value=int(want * 127)))
    yield from d.wait(4)
    say(f"K1 turned: {pid} {before:.3f} → {p.norm:.3f}")
    assert abs(p.norm - before) > 0.1

    # the ring follows, a move of the param from the panel's side too
    p.set_norm(0.5)
    yield from d.wait(4)
    ring = _ring(out)
    say(f"ring after the param went to 0.50: {ring} ({len(out.sent) - mark} messages since)")
    assert ring is not None and abs(ring - 0.5 * 127) <= 3

    # leave, by the chip that says so: the route comes back, unedited
    yield from d.wait(2)
    yield from d.click(CHIP)
    yield from d.wait(3)
    assert not table.node_rows(ROLE) and not table.node_holds(route)
    assert deck.loaded_patch.node_mode.of(1, "midi") is None
    back = yield from _span(deck, pid, d)
    say(f"left: no rows, route as saved {route.to_json() == saved}, {pid} moved {back:.3f}")
    assert back > 0.01 and route.to_json() == saved
    say("all good")
