"""tools/app_driver.py script: the player screen with a full set of controllers
(stood in: the driver's home lists none), by mouse — at 320 and 240 px in the pane,
a token dragged across, then the large window and a controller dragged between tokens,
each taken back by ⌘Z over the board, and redone (row 800); a controller unplugged since
is refused in words. Each step's words go to stderr; a step that does not do what it
should stops the run.

    uv run python tools/app_driver.py tools/drive_players.py --out <scratch>/run --every 10

Nothing is written: the players' file is cut off first.
"""

import sys
from types import SimpleNamespace as NS

from hyperspace import ui_graph
from hyperspace.pads import models
from hyperspace.ui import PAGE_KEYS


def dev(kind, status="connected", model=None):
    return NS(kind=kind, status=status, model=models.MODELS.get(model), entry={})


FAKES = {"edge": dev("gamepad", model="edge"), "apc40": dev("midi"),
         "leap": dev("hands", "lost"), "xbox": dev("gamepad", model="xbox"),
         "joyl": dev("gamepad", model="joycon-l"), "joyr": dev("gamepad", "lost", model="joycon-r"),
         "osc": dev("osc")}


def head(d, key):
    x0, y0, _x1, _y1 = d.rect(key)
    return x0 + 8, y0 + 8


def lane(d, key):
    x0, y0, x1, _y1 = d.rect(key)
    return (x0 + x1) / 2, y0 + 5


def press(d, panel, trigger, check, wants):
    """⌘Z through its trigger, over the board; two frames for the meta controller's tick."""
    panel.reg[trigger].fire()
    yield from d.wait(2)
    print(f"{trigger}: {panel.meta.undo.status}", file=sys.stderr)
    assert check(), f"{trigger}: {panel.meta.undo.status}"
    assert wants in panel.meta.undo.status, f"{trigger}: {panel.meta.undo.status}"


def script(d, panel):
    meta = panel.meta
    real = panel.devices.get
    panel.devices.get = lambda role: FAKES.get(role) or real(role)
    meta.players.tell(list(FAKES), ("edge", "apc40"))
    meta.players.tell = lambda *a, **k: None
    meta.players.path = None
    panel.render_watch = None     # the banner a covered render window raises sits on the footer
    for role, n in (("xbox", 2), ("joyl", 3), ("joyr", 3)):
        meta.players.held[role] = n
    meta.move_player(3, "off_air")
    st = ui_graph._state(panel)
    panel.reg["ui.page"].set(PAGE_KEYS.index("players"))
    st["side_w"] = 320.0
    yield from d.park()
    yield from d.wait(60)         # 320 px
    st["side_w"] = 240.0
    yield from d.wait(60)         # 240 px
    st["side_w"] = 320.0
    yield from d.wait(20)
    yield from d.move(head(d, "players.p2"), frames=10)
    yield from d.press(True)
    yield from d.move(lane(d, "players.lane.off_air"), frames=30)
    yield from d.wait(30)         # a token in the air
    yield from d.press(False)
    yield from d.park()
    yield from d.wait(60)         # what the move did, said
    duty = meta.players.get(2).duty
    assert duty.value == "off_air", duty
    yield from d.move(lane(d, "players.lane.off_air"), frames=10)
    yield from d.wait(30)         # past the settle time, over the board
    yield from press(d, panel, "edit.undo", lambda: meta.players.get(2).duty.value == "on_air",
                     "undid player 2 to off air")
    yield from d.wait(60)         # the line under the lanes says what ⌘Z did
    yield from press(d, panel, "edit.redo", lambda: meta.players.get(2).duty.value == "off_air",
                     "redid player 2 to off air")
    yield from d.wait(60)
    yield from d.click("players.open", frames=10)
    yield from d.park()
    yield from d.wait(60)         # large
    yield from d.move("players.big.ctl.osc", frames=10)
    yield from d.press(True)
    yield from d.move(head(d, "players.big.p4"), frames=30)
    yield from d.wait(30)         # a controller in the air
    yield from d.press(False)
    yield from d.wait(60)         # who holds it, said; the mouse still over the board
    assert meta.players.player_of("osc").number == 4
    FAKES["osc"].status = "lost"
    yield from press(d, panel, "edit.undo", lambda: meta.players.player_of("osc").number == 4,
                     "not undone: osc unplugged")
    yield from d.wait(60)         # refused, in words
    FAKES["osc"].status = "connected"
    yield from press(d, panel, "edit.undo", lambda: meta.players.player_of("osc").number != 4,
                     "undid osc to player 4")
    yield from d.wait(60)
    tuned = panel.reg["hands.smooth"]    # a setting of another section: not the board's to take
    tuned.step(3)
    yield from d.wait(40)
    was = tuned.base
    yield from press(d, panel, "edit.undo", lambda: tuned.base == was,
                     "nothing to undo on the player screen")
    yield from d.wait(60)         # refused, in the warning colour
    yield from d.park()
    yield from d.wait(30)
