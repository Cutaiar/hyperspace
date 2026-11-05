"""tools/app_driver.py script: the player screen with a rig's worth of controllers
(stood in: the driver's home lists none), by mouse — at 320 and 240 px in the pane,
a token dragged across, then the large window and a controller dragged between tokens.

    uv run python tools/app_driver.py tools/drive_players.py --out <scratch>/run --every 10

Nothing is written: the players' file is cut off first.
"""

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
    yield from d.click("players.open", frames=10)
    yield from d.park()
    yield from d.wait(60)         # large
    yield from d.move("players.big.ctl.osc", frames=10)
    yield from d.press(True)
    yield from d.move(head(d, "players.big.p4"), frames=30)
    yield from d.wait(30)         # a controller in the air
    yield from d.press(False)
    yield from d.park()
    yield from d.wait(60)
