"""The player select screen (wave 4 PS, plan 55): a party game's team screen.

Two lanes, ON AIR and OFF AIR, and a token per player, with its number and the
controllers it holds, each drawn as itself (`GLYPHS`: a DualSense's four shapes, a
Joy-Con's pill, the APC40's grid) and lit or struck through by whether it is
there. **The mouse moves people, and nothing else does:** no stick, no pad, no
desk (the owner, 2026-11-04). A move stays until someone moves it back.

- **A duty:** drag a token to the other lane, or click the token and then the lane.
- **A controller:** drag it to another token, or click it and then the token.
- **A new controller:** drag it from the tray to a token, or click it and then the token.

Each is said the moment it happens: on the line under the lanes and in the
footer (`Library.say`). The moves go through `MetaController.move_player` and
`register` and nothing else: where a player's deck is, and what a row does when
it gets there, is plan 55's. They run after the board's draw (`_board`), since
`register` can close and open a device.

**Where it lives.** A section of the side pane (`ui_pane`, folded at first, its
header saying who is where) and the same board large, in a window of its own, over
whatever is drawn (`window`). The footer's chip and the O key open and close the
large one, with the panel folded too. Esc closes it. O has no row in `routing.keymap`, and
if one is learned onto it the row has it and the board does not (`_key_toggles`). Both are the one `_board`; every
size is `lay_out`, a plain function of the width, tested at 240, 320 and large.

**The tray** is what nobody holds. By plan 55's rule every listed controller has a
holder (player 1, unless told), so what can be in it is what the Mac sees and the
device list doesn't: a pad or a MIDI port (`loose`, looked for every `LOOSE_S`, and
for MIDI not at all if ``[midi] enabled = false``). **It waits there until it is dragged
to a player (the owner, 2026-11-06):** that adopts it (`adopt`, `devicelist`), on both
Macs, under a role that rows can name from then on. Nothing is adopted by plugging in.
A token may hold nothing: a player with no controller is drawn dim, as an empty seat,
and takes a controller like any other.

**Ids** for `tests/ui_driver.py`: ``players.lane.on_air``, ``players.lane.off_air``,
``players.p<n>``, ``players.ctl.<role>``, ``players.open`` (the footer's chip),
``players.large`` (the section's chip); the large window's are ``players.big.…``.

Drawn with imgui's draw list, as the desk is, so it draws in a headless test.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from imgui_bundle import imgui

from . import apc40, devicelist, devices, ui
from .midiports import port_names
from .pads import models
from .players import Duty
from .pointer import deck_number

STATE = "_players_ui"     # on the panel: {"sel", "drag", "said", "large", …}
SEL_PLAYER, SEL_CTL, SEL_TRAY = "player", "ctl", "tray"
LANES = (Duty.ON_AIR, Duty.OFF_AIR)
WORDS = {Duty.ON_AIR: "on air", Duty.OFF_AIR: "off air"}

# px at scale 1: the narrowest a pane's body is (`ui_graph.SIDE_MIN`) has two tokens a row
PAD, GAP, HEAD = 5.0, 6.0, 26.0
CARD_MIN = 78.0
BADGE = 30.0
CELL_W, CELL_H = 42.0, 42.0
BESIDE = 440.0           # this wide, the lanes side by side; narrower, one over the other
BIG_W, BIG_H = 980.0, 620.0   # the large window at first, at most
BIG_DESIGN = 520.0       # its scale: its width over this
BIG_MAX = 2.4
DRAG_PX = 4.0            # past this a press on a token is a drag
LOOSE_S = 1.0            # how often the tray looks for a controller nobody lists
OURS = "hyperspace"      # a virtual port of our own is listed as an input too: never loose
KEY = "O"                # opens the board: no row in `routing.keymap` (a test holds it so)
STAYS = " Stays until moved."
HINT = "Drag a player across to change duty. Drag a controller to another player, or a new one from the tray."
TRAY_NONE = "nothing loose"
ADOPT_TIP = ("Seen on this Mac, and nobody holds it. Drag it to a player: it joins the list "
             "both Macs share, as {role}, and rows can name it. Nothing joins by plugging in.")
TRAY_TIP = "Seen on this Mac, and nobody can hold it here: this panel has no device list."
OPEN_TIP = "The player screen, large: who is on air, and what they hold (O)"
LARGE_TIP = "The same board, large, for across the room (O, or the footer's chip)"
STATE_WORDS = {"on": "connected", "lost": "lost", "off": "switched off",
               "error": "error", "gone": "not listed now"}

GREEN = imgui.ImVec4(0.30, 0.86, 0.42, 1.0)
CARD = imgui.ImVec4(0.13, 0.13, 0.15, 1.0)
WHITE = imgui.ImVec4(1, 1, 1, 1)

Rect = tuple[float, float, float, float]
_esc_frame = -1          # the frame the board last took Esc (`took_escape`)


@dataclass(frozen=True)
class Held:
    """A controller as the board draws it."""

    role: str
    glyph: str               # `GLYPHS`' key
    name: str                # in words: "DualSense Edge"
    state: str               # `STATE_WORDS`' key
    entry: dict | None = None    # a loose one's: what adopting it lists (`devicelist`)


@dataclass
class Card:
    number: int
    rect: Rect
    cells: list[tuple[str, Rect]] = field(default_factory=list)


@dataclass
class Board:
    w: float
    h: float
    s: float
    lanes: dict[Duty, Rect]
    cards: dict[int, Card]
    tray: Rect
    tray_cells: list[Rect]


def _wrap(items: int, per_row: int) -> int:
    return max(1, math.ceil(items / max(per_row, 1)))


def _per_row(w: float, cell: float, gap: float) -> int:
    return max(1, int((w + gap) // (cell + gap)))


def lay_out(w: float, duties: dict[int, Duty], holds: dict[int, list[str]], s: float = 1.0,
            tray: int = 0, x: float = 0.0, y: float = 0.0) -> Board:
    """Every rectangle of the board, `w` wide from (`x`, `y`), at scale `s`: nothing
    passes `w`, whatever anyone holds. Lanes side by side from `BESIDE`, else one
    over the other; a lane with nobody in it keeps a token's room to drop into."""
    pad, gap, head = PAD * s, GAP * s, HEAD * s
    beside = w >= BESIDE * s
    lane_w = (w - gap) / 2 if beside else w
    inner = lane_w - 2 * pad
    cols = min(4, _per_row(inner, CARD_MIN * s, gap))
    card_w = (inner - gap * (cols - 1)) / cols
    # two controllers a row at the least: a token stays as short as it can
    cell_w, cell_h = min(CELL_W * s, (card_w - 2 * pad) / 2), CELL_H * s
    per_cell = _per_row(card_w - 2 * pad, cell_w, 0.0)
    empty_h = 2 * pad + BADGE * s + cell_h

    lanes: dict[Duty, Rect] = {}
    cards: dict[int, Card] = {}
    bottoms: dict[Duty, float] = {}
    cursor = y
    for i, duty in enumerate(LANES):
        lane_x = x + i * (lane_w + gap) if beside else x
        top = y if beside else cursor
        row_y = top + head
        who = [n for n, d in sorted(duties.items()) if d == duty]
        for r in range(0, len(who), cols):
            row = who[r:r + cols]
            card_h = max(2 * pad + BADGE * s
                         + _wrap(len(holds.get(n, ())), per_cell) * cell_h for n in row)
            for c, n in enumerate(row):
                cx = lane_x + pad + c * (card_w + gap)
                card = Card(n, (cx, row_y, cx + card_w, row_y + card_h))
                for k, role in enumerate(holds.get(n, ())):
                    gx = cx + pad + (k % per_cell) * cell_w
                    gy = row_y + pad + BADGE * s + (k // per_cell) * cell_h
                    card.cells.append((role, (gx, gy, gx + cell_w, gy + cell_h)))
                cards[n] = card
            row_y += card_h + gap
        if not who:
            row_y += empty_h + gap
        bottoms[duty] = row_y - gap + pad
        lanes[duty] = (lane_x, top, lane_x + lane_w, bottoms[duty])
        cursor = bottoms[duty] + gap
    if beside:
        low = max(bottoms.values())
        lanes = {d: (r[0], r[1], r[2], low) for d, r in lanes.items()}
        cursor = low + gap
    tray_cell = min(CELL_W * s, w - 2 * pad)
    per_tray = _per_row(w - 2 * pad, tray_cell, 0.0)
    tray_h = head + (_wrap(tray, per_tray) * cell_h if tray else 0.0) + pad
    cells = [(x + pad + (k % per_tray) * tray_cell, cursor + head + (k // per_tray) * cell_h,
              x + pad + (k % per_tray + 1) * tray_cell,
              cursor + head + (k // per_tray + 1) * cell_h)
             for k in range(tray)]
    return Board(w, cursor + tray_h - y, s, lanes, cards,
                 (x, cursor, x + w, cursor + tray_h), cells)


# ---------------------------------------------------------------- what is there

def _meta(panel):
    return getattr(panel, "meta", None)


def _state(panel) -> dict:
    return panel.__dict__.setdefault(STATE, {"sel": None, "drag": None, "said": "", "large": False})


def glyph_of_model(model) -> str:
    """Which `GLYPHS` entry a pad's model is drawn as. No model is the Xbox's face,
    as `PadDevice.model` documents."""
    if model is None:
        return "xbox"
    if model.id in ("joycon-l", "joycon-r", "procon"):
        return model.id
    return model.family if model.family in ("xbox", "sony") else "pad"


def _glyph_key(d) -> tuple[str, str]:
    """(`GLYPHS`' key, the words) for a listed device."""
    kind = getattr(d, "kind", "")
    entry = getattr(d, "entry", None) or {}     # an `OffDevice` has only this to say what it is
    if kind == "gamepad":
        model = getattr(d, "model", None)
        if model is None:
            model = models.MODELS.get(models.parse_spec(entry.get("controller", "any")))
        return glyph_of_model(model), (model.name if model is not None else "gamepad")
    if kind == "midi":
        apc = str(entry.get("profile") or "apc40") == "apc40"      # as `MidiDevice.profile`
        return ("apc40", "APC40") if apc else ("midi", "MIDI desk")
    if kind == "hands":
        return "hands", "Ultraleap hands"
    if kind == "bridge":
        return "bridge", "FL Studio bridge"
    return "signal", kind or "controller"       # any other kind that feeds a row


def _state_of(d) -> str:
    try:
        status = str(d.status)
    except Exception:  # noqa: BLE001 — a status line never takes the page down
        return "error"
    for word, state in (("connected", "on"), ("off", "off"), ("error", "error")):
        if status.startswith(word):
            return state
    return "lost"


def held(panel, number: int) -> list[Held]:
    """What player `number` holds, each as the board draws it."""
    regs = getattr(panel, "devices", None)
    out = []
    for role in _meta(panel).players.controllers_of(number):
        d = regs.get(role) if regs is not None else None
        if d is None:
            out.append(Held(role, "unknown", "not listed now", "gone"))
        else:
            out.append(Held(role, *_glyph_key(d), _state_of(d)))
    return out


def _loose_midi(regs, st: dict | None) -> list[Held]:
    """MIDI ports the Mac sees that no entry reads, when this Mac may look. A port a
    listed entry names, on or off, in or out, is that entry's; a virtual one is our own.
    Why it could not look is the board's to say (`st["midi_why"]`)."""
    store = getattr(regs, "store", None)
    if store is None or store.no_midi_look:
        return []
    seen = port_names()
    if st is not None:
        st["midi_why"] = seen.why
    names: list[str] = []
    for d in regs:
        e = getattr(d, "entry", None) or {}
        names += [str(e[k]) for k in ("port", "out", "in") if e.get(k)]
        if getattr(d, "kind", "") == "midi" and not e.get("port") and str(
                e.get("profile") or "apc40") == "apc40":
            names.append(apc40.PORT_MATCH)
    theirs = [n.lower() for n in names]
    out = []
    for port in seen.inputs:
        low = port.lower()
        if OURS in low or any(n in low for n in theirs):
            continue
        apc = apc40.PORT_MATCH.lower() in low
        out.append(Held(port, "apc40" if apc else "midi", port, "on", devicelist.midi_entry(port)))
    return out


def loose(panel, st: dict | None = None) -> list[Held]:
    """What the Mac sees that no entry reads (the module's tray). A pad an entry
    is off for, or is waiting to take, is that entry's: one pad each. Never raises: a
    tray costs nothing if it cannot look."""
    regs = getattr(panel, "devices", None)
    waiting = [d for d in (regs if regs is not None else ())
               if getattr(d, "kind", "") == "gamepad" and _state_of(d) != "on"]

    def spoken_for(model, vid=None, pid=None) -> bool:
        for d in waiting:
            spec = (getattr(d, "entry", None) or {}).get("controller", "any")
            if models.matches(spec, model, vid, pid):
                waiting.remove(d)
                return True
        return False
    claims = getattr(getattr(regs, "ctx", None), "pads", None)
    hub = getattr(claims, "hub", None)
    out: list[Held] = _loose_midi(regs, st) if regs is not None else []
    try:
        if hub is not None:
            for path, r in list(hub.readers.items()):
                if path not in hub.held and not spoken_for(
                        r.model, getattr(r, "vid", None), getattr(r, "pid", None)):
                    out.append(Held(str(r.name), glyph_of_model(r.model), str(r.name), "on",
                                    devicelist.pad_entry(r.model, getattr(r, "vid", None),
                                                         getattr(r, "pid", None))))
        import glfw
        taken = getattr(claims, "taken", {})
        for j in range(glfw.JOYSTICK_1, glfw.JOYSTICK_LAST + 1):
            if j in taken or not glfw.joystick_present(j):
                continue
            vid, pid = models.glfw_ids(glfw.get_joystick_guid(j))
            model = models.by_ids(vid, pid)
            # a pad the hid road reads shows here as well: the hub says if it is free
            if model.road == "hid" and hub is not None:
                continue
            if not spoken_for(model, vid, pid):
                out.append(Held(model.name, glyph_of_model(model), model.name, "on",
                                devicelist.pad_entry(model, vid, pid)))
    except Exception:  # noqa: BLE001 — see the docstring
        return out
    return out


def _tray(panel, st: dict, now: float | None = None) -> list[Held]:
    now = time.monotonic() if now is None else now
    if now - st.get("loose_at", -LOOSE_S) >= LOOSE_S:
        st["loose_at"], st["loose"] = now, loose(panel, st)
    return st.get("loose", [])


def summary(panel) -> str:
    """Who is where, in a line, for a folded header and the footer's chip: the
    players holding a controller, "—" for a lane with none of them."""
    meta = _meta(panel)
    if meta is None:
        return ""
    active = meta.players.active()
    side = {d: " ".join(str(p.number) for p in active if p.duty == d) or "—" for d in LANES}
    return f"on air {side[Duty.ON_AIR]}  ·  off air {side[Duty.OFF_AIR]}"


# ---------------------------------------------------------------- moves and their words

def _deck_no(meta, deck) -> int:
    return deck_number(meta.decks, deck)


def duty_words(number: int, duty: Duty, roles, left: int, reached: int) -> str:
    """What a duty change does, said as it happens."""
    head = f"Player {number} {WORDS[duty]}"
    if not roles:
        return f"{head}: holds no controller yet.{STAYS}"
    them = ", ".join(roles)
    if left == reached:
        return f"{head}: {them} stay on deck {reached}.{STAYS}"
    return f"{head}: {them} now on deck {reached}; rows on deck {left} go quiet.{STAYS}"


def give_words(role: str, number: int, deck: int, reopened: bool, address: str | None,
               no_first_pad: bool) -> str:
    """What giving a controller to a player does, said as it happens."""
    words = f"{role} to player {number}, on deck {deck}"
    if address is not None:
        words += f": its rows are {'the bare ones' if not address else '@' + address}"
    words += ", reopened." if reopened else "."
    if no_first_pad:
        words += " No pad is player 1's: the bare pad rows wait for one."
    return words


def adopt_words(name: str, role: str, number: int, deck: int) -> str:
    """What adopting a controller does, said as it happens."""
    return f"{name} adopted as {role}: on both Macs now. Player {number} holds it here, on deck {deck}."


def _say(panel, st: dict, words: str, warn: str = "") -> None:
    """The line under the lanes and the footer. A move the file did not keep says so,
    in the warning colour, and does not promise it stays (`Players.save`)."""
    error = _meta(panel).players.error or warn
    if error:
        words = f"{words.removesuffix(STAYS).rstrip()} {error}"
    st["said"], st["said_warn"] = words, bool(error)
    lib = getattr(panel, "library", None)
    if lib is not None and hasattr(lib, "say"):
        lib.say(warning=words) if error else lib.say(words)


def move(panel, number: int, duty: Duty) -> None:
    """Player `number` to `duty`, through the meta controller; said."""
    meta = _meta(panel)
    if meta.players.get(number).duty == duty:
        return
    left = _deck_no(meta, meta.deck_of_player(number))
    meta.move_player(number, duty)
    _say(panel, _state(panel), duty_words(number, duty, meta.players.controllers_of(number), left,
                                          _deck_no(meta, meta.deck_of_player(number))))


def give(panel, role: str, number: int) -> None:
    """The controller `role` to player `number`, through the meta controller; said."""
    meta = _meta(panel)
    if meta.players.player_of(role).number == number:
        return
    regs = getattr(panel, "devices", None)
    was = regs.get(role) if regs is not None else None
    meta.register(role, number)
    now = regs.get(role) if regs is not None else None
    pad = isinstance(now, devices.PadDevice)
    pads = [d for d in regs if isinstance(d, devices.PadDevice)] if regs is not None else []
    _say(panel, _state(panel), give_words(
        role, number, _deck_no(meta, meta.deck_of_player(number)),
        now is not was and was is not None, now.qualifier if pad else None,
        bool(pads) and all(d.qualifier for d in pads)))


def adopt(panel, h: Held, number: int) -> None:
    """A controller from the tray to player `number`: into the list both Macs share, then
    held and pointed as any other (`MetaController.register`); said. Held before it's
    applied, so it opens under its right name the first time."""
    meta, regs = _meta(panel), getattr(panel, "devices", None)
    store = getattr(regs, "store", None)
    if store is None or h.entry is None:
        return
    role = store.adopt(h.entry)
    meta.players.hold(role, number)
    regs.relist()
    meta.register(role, number)
    _say(panel, _state(panel), adopt_words(h.name, role, number,
                                           _deck_no(meta, meta.deck_of_player(number))), store.said)


def _clicked_lane(panel, st: dict, duty: Duty) -> None:
    sel = st["sel"]
    if sel is not None and sel[0] == SEL_PLAYER:
        st["sel"] = None                # one click, one move: a later stray click moves nobody
        move(panel, sel[1], duty)
    elif sel is None:
        st["said"], st["said_warn"] = "Click a player first, then the lane.", False


def _clicked_tray(st: dict, h: Held) -> None:
    st["sel"] = None if st["sel"] == (SEL_TRAY, h) else (SEL_TRAY, h)


def _clicked_card(panel, st: dict, number: int) -> None:
    sel = st["sel"]
    if sel is not None and sel[0] == SEL_CTL:
        give(panel, sel[1], number)
        st["sel"] = None
    elif sel is not None and sel[0] == SEL_TRAY:
        st["sel"] = None
        adopt(panel, sel[1], number)
    else:
        st["sel"] = None if sel == (SEL_PLAYER, number) else (SEL_PLAYER, number)


def _clicked_ctl(panel, st: dict, role: str) -> None:
    """A click on a controller: picks it, or lets go of it; with another player's
    controller picked, the click is on this player, as anywhere on their token."""
    sel = st["sel"]
    players = _meta(panel).players
    if sel is not None and sel[0] == SEL_TRAY:
        st["sel"] = None
        adopt(panel, sel[1], players.player_of(role).number)
        return
    if sel is not None and sel[0] == SEL_CTL and sel[1] != role:
        number = players.player_of(role).number
        if players.player_of(sel[1]).number != number:
            give(panel, sel[1], number)
            st["sel"] = None
            return
    st["sel"] = None if sel == (SEL_CTL, role) else (SEL_CTL, role)


# ---------------------------------------------------------------- the glyphs

def _v(x: float, y: float) -> imgui.ImVec2:
    return imgui.ImVec2(x, y)


def _c(r: float, g: float, b: float, a: float = 1.0) -> int:
    return ui.u32(imgui.ImVec4(r, g, b, a))


def _pad_body(dl, x, y, w, h, body: int) -> None:
    """A two-handled pad, filling the box: a bar and two grips."""
    r = h * 0.30
    dl.add_rect_filled(_v(x + w * 0.10, y + h * 0.12), _v(x + w * 0.90, y + h * 0.66), body, r)
    dl.add_circle_filled(_v(x + w * 0.20, y + h * 0.66), h * 0.30, body)
    dl.add_circle_filled(_v(x + w * 0.80, y + h * 0.66), h * 0.30, body)


def _xbox(dl, x, y, w, h, a) -> None:
    _pad_body(dl, x, y, w, h, _c(0.78, 0.80, 0.80, a))
    dl.add_circle_filled(_v(x + w * 0.5, y + h * 0.30), h * 0.11, _c(0.20, 0.70, 0.25, a))
    r = h * 0.075
    fx, fy, d = x + w * 0.74, y + h * 0.40, h * 0.14
    for (ox, oy), col in (((0, d), (0.25, 0.80, 0.30)), ((d, 0), (0.92, 0.25, 0.22)),
                          ((-d, 0), (0.25, 0.45, 0.95)), ((0, -d), (0.95, 0.80, 0.20))):
        dl.add_circle_filled(_v(fx + ox, fy + oy), r, _c(*col, a))
    dl.add_circle_filled(_v(x + w * 0.27, y + h * 0.40), h * 0.11, _c(0.2, 0.2, 0.22, a))


def _sony(dl, x, y, w, h, a) -> None:
    _pad_body(dl, x, y, w, h, _c(0.93, 0.93, 0.95, a))
    dl.add_rect_filled(_v(x + w * 0.36, y + h * 0.14), _v(x + w * 0.64, y + h * 0.42),
                       _c(0.15, 0.15, 0.18, a), 2.0)
    dl.add_line(_v(x + w * 0.38, y + h * 0.14), _v(x + w * 0.62, y + h * 0.14),
                _c(0.25, 0.55, 1.0, a), max(1.5, h * 0.07))
    fx, fy, d, r = x + w * 0.80, y + h * 0.40, h * 0.15, h * 0.075
    t = 1.0 + h * 0.02
    dl.add_triangle(_v(fx, fy - d - r), _v(fx - r, fy - d + r), _v(fx + r, fy - d + r),
                    _c(0.10, 0.60, 0.45, a), t)
    dl.add_circle(_v(fx + d, fy), r, _c(0.90, 0.20, 0.25, a), 0, t)
    dl.add_line(_v(fx - r, fy + d - r), _v(fx + r, fy + d + r), _c(0.25, 0.40, 0.90, a), t)
    dl.add_line(_v(fx + r, fy + d - r), _v(fx - r, fy + d + r), _c(0.25, 0.40, 0.90, a), t)
    dl.add_rect(_v(fx - d - r, fy - r), _v(fx - d + r, fy + r), _c(0.85, 0.35, 0.70, a), 0, t)
    dl.add_circle_filled(_v(x + w * 0.20, y + h * 0.40), h * 0.10, _c(0.25, 0.25, 0.28, a))


def _joycon(col):
    def draw(dl, x, y, w, h, a) -> None:
        pw = h * 0.62
        px = x + (w - pw) / 2
        dl.add_rect_filled(_v(px, y), _v(px + pw, y + h), _c(*col, a), pw * 0.42)
        dl.add_circle_filled(_v(px + pw / 2, y + h * 0.28), pw * 0.24, _c(0.10, 0.10, 0.12, a))
        fx, fy, d = px + pw / 2, y + h * 0.68, pw * 0.20
        for ox, oy in ((0, d), (d, 0), (-d, 0), (0, -d)):
            dl.add_circle_filled(_v(fx + ox, fy + oy), pw * 0.08, _c(0.10, 0.10, 0.12, a))
    return draw


def _procon(dl, x, y, w, h, a) -> None:
    _pad_body(dl, x, y, w, h, _c(0.22, 0.22, 0.25, a))
    fx, fy, d = x + w * 0.76, y + h * 0.40, h * 0.14
    for ox, oy in ((0, d), (d, 0), (-d, 0), (0, -d)):
        dl.add_circle_filled(_v(fx + ox, fy + oy), h * 0.07, _c(0.85, 0.85, 0.88, a))
    dl.add_circle_filled(_v(x + w * 0.24, y + h * 0.40), h * 0.11, _c(0.62, 0.62, 0.66, a))


def _plain_pad(dl, x, y, w, h, a) -> None:
    _pad_body(dl, x, y, w, h, _c(0.55, 0.55, 0.58, a))


def _apc40(dl, x, y, w, h, a) -> None:
    """The desk's clip grid over its faders."""
    dl.add_rect_filled(_v(x, y), _v(x + w, y + h), _c(0.20, 0.20, 0.22, a), 2.0)
    cols, rows = 6, 3
    cw, ch = (w - 4) / cols, h * 0.62 / rows
    for r in range(rows):
        for k in range(cols):
            col = (0.25, 0.85, 0.35) if (r + k) % 3 else (0.95, 0.55, 0.15)
            gx, gy = x + 2 + k * cw, y + 2 + r * ch
            dl.add_rect_filled(_v(gx + 0.5, gy + 0.5), _v(gx + cw - 0.5, gy + ch - 0.5),
                               _c(*col, a), 1.0)
    for k in range(cols):
        fx = x + 2 + (k + 0.5) * cw
        dl.add_line(_v(fx, y + h * 0.72), _v(fx, y + h - 1), _c(0.85, 0.85, 0.88, a), 1.5)


def _midi(dl, x, y, w, h, a) -> None:
    dl.add_rect_filled(_v(x, y + h * 0.1), _v(x + w, y + h * 0.9), _c(0.92, 0.92, 0.94, a), 2.0)
    for k in range(1, 7):
        kx = x + w * k / 7
        dl.add_line(_v(kx, y + h * 0.1), _v(kx, y + h * 0.9), _c(0.2, 0.2, 0.22, a), 1.0)
        if k != 3:
            dl.add_rect_filled(_v(kx - w * 0.04, y + h * 0.1), _v(kx + w * 0.04, y + h * 0.55),
                               _c(0.1, 0.1, 0.12, a))


def _hands(dl, x, y, w, h, a) -> None:
    cx, col, t = x + w / 2, _c(0.30, 0.85, 0.75, a), max(2.0, h * 0.11)
    dl.add_rect_filled(_v(cx - h * 0.26, y + h * 0.46), _v(cx + h * 0.26, y + h), col, h * 0.12)
    for dx, top in ((-0.20, 0.10), (-0.07, 0.0), (0.07, 0.02), (0.20, 0.14)):
        fx = cx + h * dx
        dl.add_line(_v(fx, y + h * 0.5), _v(fx, y + h * top), col, t)
    dl.add_line(_v(cx - h * 0.24, y + h * 0.72), _v(cx - h * 0.50, y + h * 0.42), col, t)


def _bridge(dl, x, y, w, h, a) -> None:
    col, t = _c(0.95, 0.60, 0.20, a), max(1.5, h * 0.08)
    for cy, sgn in ((y + h * 0.32, 1), (y + h * 0.68, -1)):
        lo, hi = (x + w * 0.1, x + w * 0.9) if sgn > 0 else (x + w * 0.9, x + w * 0.1)
        dl.add_line(_v(lo, cy), _v(hi, cy), col, t)
        dl.add_line(_v(hi, cy), _v(hi - sgn * h * 0.22, cy - h * 0.16), col, t)
        dl.add_line(_v(hi, cy), _v(hi - sgn * h * 0.22, cy + h * 0.16), col, t)


def _signal(dl, x, y, w, h, a) -> None:
    col, t = _c(0.65, 0.55, 1.0, a), max(1.5, h * 0.08)
    last = None
    for k in range(25):
        u = k / 24
        p = _v(x + w * u, y + h / 2 - math.sin(u * 2 * math.pi * 1.5) * h * 0.36)
        if last is not None:
            dl.add_line(last, p, col, t)
        last = p


def _unknown(dl, x, y, w, h, a) -> None:
    dl.add_rect(_v(x + w * 0.1, y + h * 0.1), _v(x + w * 0.9, y + h * 0.9),
                _c(0.7, 0.7, 0.72, a), 3.0, 1.5)
    dl.add_circle_filled(_v(x + w * 0.5, y + h * 0.5), h * 0.12, _c(0.7, 0.7, 0.72, a))


GLYPHS = {"xbox": _xbox, "sony": _sony, "joycon-l": _joycon((0.0, 0.70, 0.90)),
          "joycon-r": _joycon((1.0, 0.33, 0.28)), "procon": _procon, "pad": _plain_pad,
          "apc40": _apc40, "midi": _midi, "hands": _hands, "bridge": _bridge, "signal": _signal,
          "unknown": _unknown}


def _draw_held(dl, h: Held, rect: Rect, s: float, lit: bool = False) -> None:
    """One controller in its cell: its glyph, a dot green while it is there and a
    red strike when it is not, its role under it. Told apart by shape as well as
    colour: a struck, faded glyph with a hollow dot reads from across a room."""
    x0, y0, x1, y1 = rect
    label_h = 13.0 * min(s, 1.6)
    gw, gh = min(x1 - x0 - 6 * s, 36 * s), y1 - y0 - label_h - 5 * s
    gx, gy = (x0 + x1 - gw) / 2, y0 + 2 * s
    if lit:
        dl.add_rect(_v(x0 + 0.5, y0 + 0.5), _v(x1 - 0.5, y1 - 0.5), ui.u32(WHITE), 3.0, 2.0)
    on = h.state == "on"
    GLYPHS.get(h.glyph, _unknown)(dl, gx, gy, gw, gh, 1.0 if on else 0.32)
    r = 3.5 * s
    dot = _v(gx + gw - r + 2 * s, gy + r)
    if on:
        dl.add_circle_filled(dot, r, ui.u32(GREEN))
    else:
        dl.add_circle(dot, r, ui.u32(ui.WARN), 0, 1.5)
        if h.state != "off":
            dl.add_line(_v(gx, gy + gh), _v(gx + gw, gy), ui.u32(ui.WARN), max(2.0, 2.0 * s))
    # its role: the largest of the tag sizes that fits it whole, else cut at the smallest
    for px in ui.TAG_SIZES:
        imgui.push_font(ui._FONTS["micro"], px * min(s, 1.6))
        if px == ui.TAG_SIZES[-1] or imgui.calc_text_size(h.role).x <= x1 - x0:
            break
        imgui.pop_font()
    words = ui.fit_text(h.role, x1 - x0)
    w = imgui.calc_text_size(words).x
    dl.add_text(_v((x0 + x1 - w) / 2, y1 - label_h - 1), ui.u32(ui.TEXT if on else ui.FAINT), words)
    imgui.pop_font()


def _accent(number: int) -> imgui.ImVec4:
    """The player's colour: their pads' light (`devices.PLAYER_LIGHTS`), lifted a
    little so pure blue reads on a dark card."""
    r, g, b = devices.PLAYER_LIGHTS[(number - 1) % len(devices.PLAYER_LIGHTS)]
    return imgui.ImVec4(*(0.25 + 0.75 * c / 255 for c in (r, g, b)), 1.0)


def _badge(dl, number: int, x: float, y: float, s: float, dim: bool = False) -> tuple[float, float]:
    """The player's number on their colour, from (`x`, `y`): its centre's y and right edge."""
    accent = _accent(number)
    r = (BADGE / 2 - 1) * s
    cx, cy = x + r, y + r
    dl.add_circle_filled(_v(cx, cy), r, ui.u32(imgui.ImVec4(accent.x, accent.y, accent.z,
                                                            0.35 if dim else 1.0)))
    imgui.push_font(ui._FONTS["num"], 20.0 * s)
    t = str(number)
    size = imgui.calc_text_size(t)
    dl.add_text(_v(cx - size.x / 2, cy - size.y / 2), ui.u32(ui.DIM if dim else WHITE), t)
    imgui.pop_font()
    return cy, cx + r


def _draw_token(dl, card: Card, hold: list[Held], s: float, sel, ghost: bool, target: bool) -> None:
    """A player's token: the number on the player's colour, then what they hold.
    Holding nothing, it is an empty seat. `ghost`: where a dragged token came from."""
    x0, y0, x1, y1 = card.rect
    empty = not hold
    if ghost:
        dl.add_rect(_v(x0, y0), _v(x1, y1), ui.u32(ui.LINE), 6 * s, 1.5)
        return
    dl.add_rect_filled(_v(x0, y0), _v(x1, y1), ui.u32(CARD), 6 * s)
    border = (WHITE if sel == (SEL_PLAYER, card.number) or target
              else (ui.LINE if empty else _accent(card.number)))
    dl.add_rect(_v(x0, y0), _v(x1, y1), ui.u32(border), 6 * s,
                (3.0 if border is WHITE else 1.5) * s)
    cy, right = _badge(dl, card.number, x0 + PAD * s, y0 + PAD * s, s, dim=empty)
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO * min(s, 1.6))
    left = right + 4 * s
    word = imgui.calc_text_size("PLAYER")
    if left + word.x <= x1 - 2:           # whole or not at all: the number is the name
        dl.add_text(_v(left, cy - word.y / 2), ui.u32(ui.FAINT if empty else ui.DIM), "PLAYER")
    if empty:
        room = x1 - x0 - 2 * PAD * s
        hint = "no controller" if imgui.calc_text_size("no controller").x <= room else "empty"
        dl.add_text(_v(x0 + PAD * s, y0 + (PAD + BADGE + 6) * s), ui.u32(ui.FAINT), hint)
    imgui.pop_font()
    for h, (_role, rect) in zip(hold, card.cells, strict=False):
        _draw_held(dl, h, rect, s, lit=sel == (SEL_CTL, h.role))


def _draw_lane(dl, duty: Duty, rect: Rect, deck: int, s: float, target: bool, nobody: bool) -> None:
    x0, y0, x1, y1 = rect
    on = duty == Duty.ON_AIR
    fill = imgui.ImVec4(ui.RED.x, ui.RED.y, ui.RED.z, 0.14) if on else imgui.ImVec4(1, 1, 1, 0.035)
    dl.add_rect_filled(_v(x0, y0), _v(x1, y1), ui.u32(fill), 8 * s)
    edge = WHITE if target else (ui.RED if on else ui.LINE)
    dl.add_rect(_v(x0, y0), _v(x1, y1), ui.u32(edge), 8 * s, (3.0 if target else 2.0) * s)
    imgui.push_font(ui._FONTS["micro"], 16.0 * min(s, 1.8))
    title = "ON AIR" if on else "OFF AIR"
    size = imgui.calc_text_size(title)
    tx, ty = x0 + PAD * s + 2, y0 + (HEAD * s - size.y) / 2
    dl.add_text(_v(tx, ty), ui.u32(ui.RED if on else ui.DIM), title)
    imgui.pop_font()
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO * min(s, 1.6))
    words = f"deck {deck}"
    w = imgui.calc_text_size(words)
    if tx + size.x + w.x + 8 * s < x1:
        dl.add_text(_v(x1 - w.x - PAD * s - 2, ty + (size.y - w.y) / 2), ui.u32(ui.FAINT), words)
    if nobody:
        hint = ui.fit_text("drop a player here", x1 - x0 - 2 * PAD * s)
        dl.add_text(_v(x0 + PAD * s + 2, y0 + (HEAD + 8) * s), ui.u32(ui.FAINT), hint)
    imgui.pop_font()


def _in(r: Rect, x: float, y: float) -> bool:
    return r[0] <= x <= r[2] and r[1] <= y <= r[3]


# ---------------------------------------------------------------- the board

def _button(ident: str, r: Rect, over: bool = True) -> bool:
    """An invisible button on `r`, yielding to whatever is drawn over it next
    (a token over its lane, a controller over its token). True on a click."""
    imgui.set_cursor_screen_pos(_v(r[0], r[1]))
    if over:
        imgui.set_next_item_allow_overlap()
    return imgui.invisible_button(ident, _v(max(r[2] - r[0], 1.0), max(r[3] - r[1], 1.0)))


def _dragging(st: dict, sfx: str, what: tuple) -> None:
    """The item just drawn: a press on it held past `DRAG_PX` picks it up."""
    if (st["drag"] is None and not st.get("no_drag") and imgui.is_item_active()
            and imgui.is_mouse_dragging(0, DRAG_PX)):
        st["drag"] = (sfx, *what)
        st["sel"] = None
        st["drag_seen"] = imgui.get_frame_count()


def _drop_on(bd: Board, what: str, x: float, y: float):
    """What a drag of `what` lands on at the mouse: a lane's duty, or a token's
    number. None: nothing that takes it."""
    if what == SEL_PLAYER:
        return next((d for d, r in bd.lanes.items() if _in(r, x, y)), None)
    return next((n for n, c in bd.cards.items() if _in(c.rect, x, y)), None)


def _draw_carried(hold: dict, drag: tuple, mouse, s: float) -> None:
    """What the mouse carries, over everything."""
    dl = imgui.get_foreground_draw_list()
    if drag[1] == SEL_PLAYER:
        n = drag[2]
        w, h = CARD_MIN * s, (BADGE + 2 * PAD) * s
        x0, y0, x1, y1 = mouse.x - w / 2, mouse.y - h / 2, mouse.x + w / 2, mouse.y + h / 2
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), ui.u32(CARD), 6 * s)
        dl.add_rect(_v(x0, y0), _v(x1, y1), ui.u32(_accent(n)), 6 * s, 2.5 * s)
        _badge(dl, n, x0 + PAD * s, y0 + PAD * s, s)
        return
    h = drag[2] if drag[1] == SEL_TRAY else next(
        (x for hs in hold.values() for x in hs if x.role == drag[2]), None)
    if h is not None:
        w, tall = CELL_W * s, CELL_H * s
        r = (mouse.x - w / 2, mouse.y - tall / 2, mouse.x + w / 2, mouse.y + tall / 2)
        dl.add_rect_filled(_v(r[0], r[1]), _v(r[2], r[3]), ui.u32(CARD), 4 * s)
        _draw_held(dl, h, r, s)


def _on_deck(meta, role: str) -> str:
    p = meta.pointers.get(role)
    return "no deck yet" if p is None else f"on deck {_deck_no(meta, p.deck)}"


def _board(panel, sfx: str, s: float) -> None:
    """The board, at the cursor, as wide as the room; `sfx` keeps the large window's
    ids and drag apart from the pane's."""
    meta = _meta(panel)
    st = _state(panel)
    st["board_seen"] = imgui.get_frame_count()
    hold = {p.number: held(panel, p.number) for p in meta.players}
    duties = {p.number: p.duty for p in meta.players}
    tray = _tray(panel, st)
    origin = imgui.get_cursor_screen_pos()
    room = max(imgui.get_content_region_avail().x, CARD_MIN + 2 * PAD)
    bd = lay_out(room, duties, {n: [h.role for h in hs] for n, hs in hold.items()}, s,
                 len(tray), origin.x, origin.y)
    dl = imgui.get_window_draw_list()

    mouse = imgui.get_mouse_pos()
    win, size = imgui.get_window_pos(), imgui.get_window_size()
    # a part of the board scrolled out of this window is no place to drop
    inside = _in((win.x, win.y, win.x + size.x, win.y + size.y), mouse.x, mouse.y)
    drag = st["drag"] if st["drag"] is not None and st["drag"][0] == sfx else None
    aim = _drop_on(bd, drag[1], mouse.x, mouse.y) if drag is not None and inside else None

    for duty in LANES:
        _draw_lane(dl, duty, bd.lanes[duty], _deck_no(meta, meta.deck_for(duty)), s, aim == duty,
                   not any(d == duty for d in duties.values()))
    for n, card in bd.cards.items():
        _draw_token(dl, card, hold[n], s, st["sel"],
                    ghost=drag is not None and drag[1] == SEL_PLAYER and drag[2] == n,
                    target=aim == n)
    x0, y0, x1, _y1 = bd.tray
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO * min(s, 1.6))
    title = "NOBODY HOLDS" if tray else f"NOBODY HOLDS  ·  {TRAY_NONE}"
    dl.add_text(_v(x0 + PAD * s + 2, y0 + 6 * s), ui.u32(ui.FAINT), ui.fit_text(title, x1 - x0 - 8))
    imgui.pop_font()
    for h, r in zip(tray, bd.tray_cells, strict=False):
        _draw_held(dl, h, r, s, lit=st["sel"] == (SEL_TRAY, h))

    # the buttons, on what was drawn: lane, then token, then controller. A move runs
    # below, past the last of them: `register` can close and open a device
    act = None
    free = st["drag"] is None and not st.get("no_drag")   # a release ending a drag is no click
    for duty in LANES:
        if _button(f"##players{sfx}.lane.{duty.value}", bd.lanes[duty]) and free:
            act = (_clicked_lane, panel, st, duty)
    for n, card in bd.cards.items():
        if _button(f"##players{sfx}.p{n}", card.rect) and free:
            act = (_clicked_card, panel, st, n)
        _dragging(st, sfx, (SEL_PLAYER, n))
        for h, (role, rect) in zip(hold[n], card.cells, strict=False):
            if _button(f"##players{sfx}.ctl.{role}", rect, over=False) and free:
                act = (_clicked_ctl, panel, st, role)
            _dragging(st, sfx, (SEL_CTL, role))
            if imgui.is_item_hovered() and st["drag"] is None:
                ui.tooltip(f"{role}  ·  {h.name}  ·  {STATE_WORDS[h.state]}  ·  "
                           f"{_on_deck(meta, role)}.\nDrag to another player.")
    store = getattr(getattr(panel, "devices", None), "store", None)
    for k, (h, rect) in enumerate(zip(tray, bd.tray_cells, strict=False)):
        hit = _button(f"##players{sfx}.tray.{k}", rect, over=False)
        if store is not None and h.entry is not None:
            if hit and free:
                act = (_clicked_tray, st, h)
            _dragging(st, sfx, (SEL_TRAY, h))
        if imgui.is_item_hovered() and st["drag"] is None:
            ui.tooltip(f"{h.name}. " + (ADOPT_TIP.format(role=store.role_for(h.entry))
                                        if store is not None and h.entry is not None else TRAY_TIP))
    # the room the drawing took, as an item the window scrolls by
    imgui.set_cursor_screen_pos(origin)
    imgui.dummy(_v(room, bd.h))

    if not imgui.is_mouse_down(0):
        st["no_drag"] = False
    drag = st["drag"] if st["drag"] is not None and st["drag"][0] == sfx else None
    if drag is not None:
        st["drag_seen"] = imgui.get_frame_count()
        _draw_carried(hold, drag, mouse, s)
        if not imgui.is_mouse_down(0):
            st["drag"] = None
            aim = _drop_on(bd, drag[1], mouse.x, mouse.y) if inside else None
            if aim is not None and drag[1] == SEL_PLAYER:
                move(panel, drag[2], aim)
            elif aim is not None and drag[1] == SEL_TRAY:
                adopt(panel, drag[2], aim)
            elif aim is not None:
                give(panel, drag[2], aim)
    if act is not None:
        act[0](*act[1:])
    imgui.push_text_wrap_pos(0.0)
    imgui.text_colored(ui.WARN if st.get("said_warn") else ui.TEXT if st["said"] else ui.FAINT,
                       st["said"] or HINT)
    # what stands whatever was last done: the library not there; no MIDI to look at
    for words in (getattr(store, "said", ""), st.get("midi_why", "")):
        if words:
            imgui.text_colored(ui.WARN, words)
    imgui.pop_text_wrap_pos()


def section(panel, dt: float = 0.0) -> None:
    """The side pane's section: the board at its plain size, and the chip that opens
    it large."""
    if _meta(panel) is None:
        imgui.text_disabled("no players here")
        return
    st = _state(panel)
    if ui.lit_chip("large  (O)##players.large", st["large"]):
        st["large"] = not st["large"]
    if imgui.is_item_hovered():
        ui.tooltip(LARGE_TIP)
    _board(panel, "", 1.0)


def footer(panel) -> None:
    """The footer's chip: who is where, at all times, and a click opens the board."""
    if _meta(panel) is None:
        return
    st = _state(panel)
    imgui.same_line()
    if ui.lit_chip(f"players: {summary(panel)}##players.open", st["large"]):
        st["large"] = not st["large"]
    if imgui.is_item_hovered():
        ui.tooltip(OPEN_TIP)


def _row_on_key(panel) -> bool:
    """Does the live table have a row on the key? Asked only when it is pressed."""
    table = getattr(getattr(panel, "router", None), "table", None)
    rows = table.of("key") if table is not None else ()
    return any(b.key_name == KEY for b in rows)


def _key_toggles(panel) -> bool:
    io = imgui.get_io()
    return (not io.want_text_input and not (io.key_ctrl or io.key_super or io.key_alt or io.key_shift)
            and imgui.is_key_pressed(imgui.Key.o, False) and not _row_on_key(panel))


def took_escape() -> bool:
    """Did the board take this frame's Esc? Then GRAPH's own does not act on it
    (`ui_graph.escaped`; `window` runs first in the frame)."""
    return _esc_frame == imgui.get_frame_count()


def _escape(st: dict) -> None:
    """Esc, when nothing else wants it (`ui_graph.escaped`): drops what is carried, then
    lets go of what is picked, then closes the large window. A carried thing stays
    down until the mouse comes up (`no_drag`): the button still holds the press."""
    global _esc_frame
    from . import ui_graph  # (late: ui_graph imports ui_pane, which imports this)
    if not ui_graph.escaped():
        return
    if st["drag"] is not None:
        st["drag"], st["no_drag"] = None, True
    elif st["sel"] is not None:
        st["sel"] = None
    elif st["large"]:
        st["large"] = False
    else:
        return
    _esc_frame = imgui.get_frame_count()


def window(panel) -> None:
    """The board large, in a window of its own over what is drawn, drawn whether or
    not the panel is folded. P or the footer's chip toggles it; Esc lets go of what
    is picked up or selected, then closes it."""
    global _esc_frame
    _esc_frame = -1         # first in every frame: a frame count starts again with a context
    if _meta(panel) is None:
        return
    st = _state(panel)
    # a drag whose board went undrawn (folded, scrolled out, closed) is over: the mouse
    # may have let go unseen, and it must not land when the board is next drawn. Here,
    # first in every frame, so another board drawing cannot hide it
    if st["drag"] is not None and st.get("drag_seen", -1) < imgui.get_frame_count() - 1:
        st["drag"] = None
    # a pick does not outlive its board: unseen, it could only move someone unseen, and
    # Esc on GRAPH is GRAPH's (`_escape` takes only what is on screen)
    if st.get("board_seen", -1) < imgui.get_frame_count() - 1:
        st["sel"] = None
    _escape(st)
    if _key_toggles(panel):
        st["large"] = not st["large"]
    if not st["large"]:
        st["over_big"] = False
        return
    io = imgui.get_io()
    w, h = min(BIG_W, io.display_size.x - 24), min(BIG_H, io.display_size.y - 24)
    imgui.set_next_window_pos(_v(io.display_size.x / 2, io.display_size.y / 2),
                              imgui.Cond_.appearing, _v(0.5, 0.5))
    imgui.set_next_window_size(_v(w, h), imgui.Cond_.appearing)
    opened, shown = imgui.begin("Players##players.window", True, imgui.WindowFlags_.no_collapse)
    try:
        if not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id):
            try:
                imgui.internal.bring_window_to_display_front(imgui.internal.get_current_window())
            except Exception:  # noqa: BLE001, S110 — an imgui without the internal call
                pass
        st["over_big"] = imgui.is_window_hovered(imgui.HoveredFlags_.child_windows)
        if opened:
            room = imgui.get_content_region_avail().x
            _board(panel, ".big", max(1.0, min(BIG_MAX, room / BIG_DESIGN)))
    finally:
        imgui.end()
    st["large"] = bool(shown)


def over(panel) -> bool:
    """Is the mouse over a board, as of the latest draw? ⌘Z there has nothing to take
    back (`Panel.in_meta_section`): a move is on no undo stack, and neither a deck's
    edit nor an analyzer's setting should go back in its place."""
    from . import ui_pane  # (late: ui_pane imports this module)
    return bool(_state(panel).get("over_big")) or ui_pane.where(panel) == "players"
