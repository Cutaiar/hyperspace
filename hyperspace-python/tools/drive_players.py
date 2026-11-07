"""tools/app_driver.py script: the player screen with a full set of controllers
(stood in: the driver's home lists none), by mouse — at 320 and 240 px in the pane,
a token dragged across, then the large window and a controller dragged between tokens,
each taken back by ⌘Z over the board, and redone (row 800); a controller unplugged since
is refused in words. Each step's words go to stderr; a step that does not do what it
should stops the run. Then a MIDI port and a pad nobody lists, waiting in the tray, each
dragged to a player:
adopted, through the real list in the driver's scratch home (wave 5 CT1).

    uv run python tools/app_driver.py tools/drive_players.py --out <scratch>/run --every 10

The players' file is cut off first; the device list is written, in that scratch home.
"""

import sys
from types import SimpleNamespace as NS

from hyperspace import ui_graph, ui_players
from hyperspace.devicelist import pad_entry
from hyperspace.midiports import PortNames
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
    # the tray: seen on this Mac, in no entry. Each waits until it is dragged
    regs = panel.devices
    regs.get = real                 # the real list from here on
    meta.players.tell = type(meta.players).tell.__get__(meta.players)
    seen = ["Launch Control XL"]
    ui_players.port_names = lambda: PortNames(list(seen), [], "")
    looked = ui_players.loose
    joy = models.MODELS["joycon-l"]
    pads = [ui_players.Held(joy.name, ui_players.glyph_of_model(joy), joy.name, "on", pad_entry(joy))]
    ui_players.loose = lambda panel, st=None: [*looked(panel, st), *pads]
    ui_players._state(panel)["loose_at"] = -1e9
    regs.relist()
    yield from d.park()
    yield from d.wait(60)           # two in the tray; nothing written
    regs.store.sync()
    assert "launch-control-xl" not in regs.store.path.read_text()
    yield from d.move("players.big.tray.0", frames=10)
    yield from d.press(True)
    yield from d.move(head(d, "players.big.p2"), frames=30)
    yield from d.wait(30)           # a new one in the air
    yield from d.press(False)
    seen.clear()
    ui_players._state(panel)["loose_at"] = -1e9
    yield from d.park()
    yield from d.wait(60)           # adopted, and said
    yield from d.move("players.big.tray.0", frames=10)
    yield from d.press(True)
    yield from d.move(head(d, "players.big.p4"), frames=30)
    yield from d.press(False)
    pads.clear()
    ui_players._state(panel)["loose_at"] = -1e9
    yield from d.park()
    yield from d.wait(60)
    yield from d.click("players.big.ctl.launch-control-xl", frames=10)
    yield from d.wait(20)           # picked: its on-or-off chip, for this Mac
    yield from d.click("players.big.here", frames=10)
    yield from d.park()
    yield from d.wait(30)
    assert regs.store.here["launch-control-xl"] is False
    regs.store.sync()
    text = regs.store.path.read_text()
    assert "launch-control-xl" in text and "joycon-l" in text
    print(text)
