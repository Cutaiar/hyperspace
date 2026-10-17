"""The ROUTING page — one page over the loaded preset (plan 13 §3.3,
decision register row 13).

Top to bottom: the **head** (the loaded preset's name, its dirty dot,
save / as… over it — a factory one gets a user shadow, `Library.overwrite`
— and the desk's layer, PRESET or GLOBAL, SHIFT's latch; then what the
last learn did, a refusal in the warning colour, and the notes of the
last load: the desk rows it dropped for sitting on an invariant control,
the routes the referee refused); then, in one scrolling child, the
**routes**, the **desk** (the preset layer: one line per row — the
control in Akai's words, its target, its op, × — and one dimmed line per
preset-layer control the preset leaves dark), the **macros** (each knob
with its label and its base / depth subscribers) and the **session**
(the invariant and global-layer MIDI rows, read-only: bindings.json's,
never learned or edited here, D5).

Every edit here changes the live table — the routes, the desk, the
macros — and so the loaded preset's dirty dot (`Presets.signature`);
**no file is written**. Only a save (this head's, the PRESETS page's
strip, ⇧F) writes the preset. New desk rows come from Learn (right-click
a control, then move a knob or button — midi.py's `_learned`).

The routes. Rows are the router's `push` / `position` routes from
`lane:i` (and `ext:i` / `hand:<name>` when the bridge / hands feed them), two lines each:

  [on] source        target ▾        feel   op ▾        ×
       depth ──────── rest  × scale ▾   ▮▮▮▯▯│ live
       atk ───── rel ─────          (a feel of the row's own only)

The feel chip (motion.py) cycles auto → follow → spring → still: auto is
the source's own feel (the pad's, for a stick), still is none at all, and
follow / spring are the row's own, with their two knobs on a third line —
attack and release about rest, or a spring's Hz and damping ratio.

The target is a searchable combo over every modulatable param, grouped
by registry group; depth is signed — ±1 in norm units for `push` (1 puts
a lane at the asymptote on the param's end stop), a fraction of the
throw for `position`; `rest` (push rows only) is the source reading that
pushes nothing — normally the source's own, what its adapter publishes
in `Router.rests`, shown dimmed; dragging it makes the row's own number,
"auto" gives it back; scale names the rig's attenuator — a **session**
param (the drive fader, `master.gain`) — or none, never a performance
param (decision register row 18 (a)): a macro scales a route as its depth
subscriber, shown read-only as a "× macro.N" chip (plan 13 §2.4). A
route whose target is a session param (TUMBLE's left height on the
drive) carries a dim "session" mark: it leans on that control while its
source is live and never changes its setting (row 19 (a)). The live bar is the
source's normalized reading (white) with a red hairline at the target's
effective norm, so a route can be read working. Edits land on the table
at once (the router reads it every frame) — nothing here is copied.

The macros (`macro.1–8`, plan 13 §2.4): each knob is the panel's
ordinary compact slider, so a performer can own one (right-click: Learn,
Route a lane here…) and its readout shows `base → effective` while it
does, beside its label (editable) and its subscribers. A macro does
nothing of its own; it acts through them: a **base** subscriber sets a
param's base to from + m · (to − from) along its fader whenever the
macro's base moves — a performance param's only, which is all its picker
offers (`base_targets`, D9: a preset never moves a session base); a **depth** subscriber runs a route at depth ×
(from + m · (to − from)), one frame behind whatever moves the macro. A
param two macros base-subscribe is marked on both lines — the last write
wins (§2.4). An edit of a subscriber re-lands the base subscribers
(`macros_serial`).

One performer per target: the table's referee (`routing.Owned`) refuses
a row on a target another enabled row performs, and the refusal is a
question — the Replace / Keep prompt, an imgui modal the panel draws
before anything else, on every page and with the panel hidden (`modal`,
first thing in `Panel.draw`): "Brightness is already performed by R
height positions — Replace / Keep". Two things raise it: an edit here
(`add_route`, a row's target combo, a row's checkbox waking onto a taken
target, "Route a lane here…") holds the question in the page's state
with what *Replace* would do to the table (`ask`); a hand learn the MIDI
(`learn.Learn`) had to hold (`panel.learn.pending`) is the same question,
answered through its `resolve_pending`. `_question` is whichever is up; `prompt`
reads it, `answer` settles it; *Replace* changes the loaded preset's
routes and writes no file. Every
Replace — here, `_wake`, `_retarget`, the adapter's — is one call,
`Bindings.replace_owner`, which removes whoever owns the target *when the
answer comes*, so a row that landed while the question was up goes too
and exactly one owner remains. The owner is named the way its adapter
names it (`Router.describe`). Rows a preset had to drop for the same
reason (`table.dropped`) are listed under the header until the next edit.

The filter (plan 17 WP5): one text field on the counts line, left of
`+ route`. While it holds text, only the lines that match are drawn — in
every section (and a line a widget is in use on, until it is let go:
`_shown`) — the counts read "3 of 41 rows" in red and a × beside the
field clears it. Lower-case; every typed word must be somewhere in what
the line says (`matches`): a route's sentence, source, target and the
target's label; a desk, dark or session line's glyph, Akai's name,
source and (mapped) target and label; a macro's id, label and
subscribers — a macro that matches is drawn whole. The text is UI state
(`_state(panel)["find"]`): not a param, not saved, not in a preset, not
an undo step, gone at restart; a preset load leaves it. A hidden line
keeps its place in the unfiltered list as its imgui id, so a × removes
the row it is on. Section titles are always drawn.

The routing presets are gone (plan 13 WP5): the preset holds the routes,
and the ones that shipped are presets on the PRESETS strip.

The panel reaches the router through `panel.router`, which app.py is
meant to set; until it does, the table is found through the MIDI
adapter (it shares it) and a Router is made over it — everything works
but the bridge's `ext` feeds, which that router never sees. Right-click
on any widget elsewhere offers "Route a lane here…" (`ctx_item`): a
`lane:<selected band>` → that param `push` route at depth 0.5, and the
page opens on it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace

from imgui_bundle import imgui

from . import apc40, motion, ui, ui_presets, undo
from .bands import CEIL
from .library import PRESETS
from .modifiers import KINDS as MOD_KINDS
from .modifiers import PARAMS as MOD_PARAMS
from .modifiers import Modifier
from .motion import Motion
from .params import Kind, Param, part_of
from .routing import (
    SAVE_PARAM,
    SHIFT_PARAM,
    Binding,
    Macro,
    Owned,
    Router,
    Sub,
    base_refusal,
    factory_desk,
)

NAMING = "routing.preset"  # the head's save as… name field (ui_presets._name_field)
DEPTH_MOD = 1.0           # ±, the depth slider's throw
# the op chip cycles push ↔ position; what each one's depth means
OP_CHIP = {"push": "push", "position": "pos"}
NEXT_OP = {"push": "position", "position": "push"}
DEPTH_TIP = {"push": " — 1 is the full throw at a lane's asymptote",
             "position": " — a fraction of the target's throw; 1 is all of it"}
BAR_W = 56.0
SRC_W = 84.0             # the source combo: a lane's number and name
DEPTH_W = 112.0
REST_W = 44.0            # the push row's rest field
AUTO = "auto"            # the chip that gives a push row its source's rest back
GATE_W = 62.0            # the pinch-gate combo on line 2
MACRO_LABEL_W = 22.0     # a knob's number beside it; the section says "macros"
MACRO_NAME_W = 96.0      # a macro's editable label
SUB_W = 58.0             # a subscriber's from / to fields
CONTROL_W = 56.0         # the desk and session lines' control column: a glyph (plan 14 WP7)
INDENT = 18.0            # a subscriber line under its macro
PROMPT = "replace##routing"   # the Replace / Keep modal's popup id
PROMPT_W = 360.0
FIND_W = 120.0           # the filter field on the counts line
# the feel chip (motion.py) cycles auto → follow → spring → still → auto:
# auto is the source's own feel (Router.feel_of), still turns even that off
FEEL_CYCLE = (None, "follow", "spring", "off")
FEEL_CHIP = {None: "auto", "follow": "follow", "spring": "spring", "off": "still"}
FEEL_W = 112.0           # each of the feel line's two knobs
NO_MATCH = "no row matches"


# ---- state on the panel ----

def _state(panel) -> dict:
    st = getattr(panel, "_routing_state", None)
    if st is None:
        st = panel._routing_state = {"error": "", "filter": "", "prompt": None}
    # the page's filter (plan 17 WP5); "filter" is the param combo's find
    # field. setdefault: a state dict from before a hot reload has no key
    st.setdefault("find", "")
    # a line in use is not filtered away under the hand (`_shown`): the
    # lines drawn last frame, this frame's, and whether a widget is in use
    st.setdefault("kept", set())
    st.setdefault("drawn", set())
    st.setdefault("hold", False)
    return st


# ---- the filter: which lines the page draws ----

def matches(panel, router, text: str, *hay: str) -> bool:
    """Does a line that says `hay` pass the filter `text`? Lower-case;
    `text` is split on spaces and every word must be a substring of some
    string in `hay`. An empty filter passes everything. Pure: nothing is
    read from `panel` or `router` (what a line says is its caller's —
    `route_hay`, `control_hay`, `macro_hay`)."""
    words = text.lower().split()
    if not words:
        return True
    said = "\n".join(h for h in hay if h).lower()
    return all(w in said for w in words)


def _shown(panel, router, key, hay, *args) -> bool:
    """Is this line drawn? Every line while the filter is empty (nothing is
    asked of the line then: `hay(panel, router, *args)` is not called);
    else a line that `matches` — and a line that was drawn last frame, for
    as long as a widget is in use or a popup is open (`st["hold"]`, set
    where the field is drawn), so a row being edited does not vanish under
    the hand the moment the edit stops it matching (a macro's label
    retyped, a target picked, a depth dragged). `key` names the line
    across frames."""
    st = _state(panel)
    if not st["find"].strip():
        return True
    hit = (matches(panel, router, st["find"], *hay(panel, router, *args))
           or (st["hold"] and key in st["kept"]))
    if hit:
        st["drawn"].add(key)
    return hit


def _label(panel, pid: str | None) -> str:
    p = panel.reg.get(pid) if pid else None
    return p.label if p is not None else ""


# ---- the picked desk control: its line is framed, and scrolled to ----

def goto(panel, source: str) -> None:
    """Scroll the rows' child to the line of the control `source` names
    and mark it. Clears the filter (WP5), so the line is never hidden.

    It does not change the page (plan 17 fork 2): with ROUTING open the
    rows scroll on this frame's draw; if not, when ROUTING is next opened
    while that control is still picked (`Learn.control`). The line is the
    control's row on the layer that is up — a preset row in the desk
    section, its "unmapped — dark" line for a dark preset control, an
    invariant or global row in the session section. A control dark on the
    global layer has no line: nothing scrolls."""
    st = _state(panel)
    st["goto"] = source
    st["find"] = ""
    st["unfind"] = True         # …over the field's own edit buffer too (`_find_field`)


def _pick_row(panel) -> Binding | None:
    """The picked desk control (`Learn.control`) as a row to compare lines
    with (`Binding.overlaps`), or None; a `goto` for a control no longer
    picked is dropped."""
    st = _state(panel)
    source = getattr(getattr(panel, "learn", None), "control", None)
    if st.get("goto") is not None and st["goto"] != source:
        st["goto"] = None
    st["marked"] = 0            # lines framed this draw (the tests read it)
    if source is None:
        st["mark"] = None
    elif getattr(st.get("mark"), "source", None) != source:
        st["mark"] = Binding(source, "", "abs")
    return st.get("mark")


def is_line_of(table, b: Binding, mark: Binding | None, section: str) -> bool:
    """Is the line of row `b`, in `section` ("desk": a preset row or a dark
    line; "session": an invariant or global row), the picked control's
    line? Its control must be the picked one, on the layer that is up: a
    desk line while the preset layer is up and the control is not
    invariant; an invariant row always; a global row while SHIFT is on."""
    if mark is None or not b.overlaps(mark):
        return False
    if section == "session":
        return b.layer is None or b.layer == table.layer
    return table.layer == "preset" and not table.is_invariant(mark)


def _mark_line(panel, table, b: Binding, section: str, y0: float) -> None:
    """After a desk or session line is drawn (`y0`: where it began): the
    picked control's line gets the red frame for as long as it is picked,
    and a pending `goto` scrolls the rows' child to it, once. The scroll
    is the child's (`##routes`): the page itself never scrolls."""
    st = _state(panel)
    if not is_line_of(table, b, st.get("mark"), section):
        return
    start = imgui.get_cursor_screen_pos()       # the next line's start: this line's left edge
    y1 = start.y - imgui.get_style().item_spacing.y
    x1 = start.x + imgui.get_content_region_avail().x - 1
    # the frame stands a little left of the line's first letter: the
    # child's clip is widened that much for it (and only across: a line
    # scrolled half out of the child is still cut at the child's edge)
    pos, dl = imgui.get_window_pos(), imgui.get_window_draw_list()
    imgui.push_clip_rect(imgui.ImVec2(pos.x - 6, pos.y),
                         imgui.ImVec2(pos.x + imgui.get_window_width(),
                                      pos.y + imgui.get_window_height()), False)
    dl.add_rect(imgui.ImVec2(start.x - 5, y0 - 1), imgui.ImVec2(x1, y1 + 1),
                ui.u32(ui.RED), 4.0, 1.5)
    imgui.pop_clip_rect()
    st["marked"] = st.get("marked", 0) + 1
    if st.get("goto") is not None:
        imgui.set_scroll_here_y(0.3)
        st["goto"] = None


def route_hay(panel, router: Router, b: Binding) -> tuple[str, ...]:
    """What a route says: its sentence in its adapter's words, its source,
    its target and the target's label."""
    return (router.describe(b), b.source, b.target, _label(panel, b.target))


def control_hay(panel, router: Router, b: Binding, mapped: bool = True) -> tuple[str, ...]:
    """What a desk, dark or session line says: the glyph, Akai's name, the
    source, and — a mapped line — the target and its label (a dark line's
    `b` is the factory's row: its target is not this preset's)."""
    table = router.table
    hay = (control_glyph(table, b), control_name(table, b), b.source)
    return (*hay, b.target, _label(panel, b.target)) if mapped else hay


def macro_hay(panel, router: Router, p: Param) -> tuple[str, ...]:
    """What a macro says: its id, its label, and each subscriber's param
    (and its label) or route (as the subscriber's combo names it)."""
    m = router.table.macros.get(p.id)
    hay = [p.id, m.label if m is not None else ""]
    routes = router.table.routes() if m is not None and m.subs else []
    for s in (m.subs if m is not None else []):
        if s.depth is not None:
            hay += [s.depth[0], s.depth[1]]
            hay += [router.describe(r) for r in routes if (r.source, r.target) == s.depth]
        else:
            hay += [s.base, _label(panel, s.base)]
    return tuple(hay)


def _session_rows(table) -> tuple[list[Binding], list[Binding]]:
    """The session's MIDI rows: (invariant, global layer)."""
    midi = table.midi()
    return [b for b in midi if b.layer is None], [b for b in midi if b.layer == "global"]


def found(panel, router: Router) -> tuple[int, int]:
    """(lines the filter leaves, lines there are) over the whole page: the
    routes, the desk's rows and its dark controls, the macros, the
    session's rows."""
    text, table = _state(panel)["find"], router.table
    hays = [route_hay(panel, router, b) for b in table.routes()]
    hays += [control_hay(panel, router, b) for b in table.desk()]
    hays += [control_hay(panel, router, f, mapped=False) for f in unmapped(table)]
    hays += [mod_hay(panel, router, m) for m in table.modifiers]
    hays += [macro_hay(panel, router, p) for p in panel.reg.group("macro")]
    inv, glob = _session_rows(table)
    hays += [control_hay(panel, router, b) for b in (*inv, *glob)]
    hays += [sink_hay(panel, router, b) for b in table.sinks(enabled=False)]
    return sum(matches(panel, router, text, *h) for h in hays), len(hays)


def router_of(panel) -> Router | None:
    """The app's router, or one over the MIDI adapter's (shared) table."""
    r = getattr(panel, "router", None)
    if r is None and panel.midi is not None:
        r = panel.router = Router(panel.reg, panel.midi.table)
    return r


def add_route(panel, target: str, source: str | None = None, depth: float = 0.5,
              op: str = "push") -> Binding | None:
    """A new `push` row from the selected band's lane (or `source`) to
    target, into the loaded preset (no file written); it rests where its
    source does. None when the target already has a performer — the
    prompt is up, and *Replace* puts the row in."""
    router = router_of(panel)
    src = source or f"lane:{panel.control.selb}"
    b = Binding(src, target, op, depth)
    try:
        router.table.add(b)
    except Owned as e:
        ask(panel, e.existing, b, lambda: router.table.replace_owner(b))
        return None
    return b


# ---- the prompt: one performer per target, so a second one asks ----

def ask(panel, old: Binding, new: Binding, commit: Callable[[], object]) -> None:
    """Hold the question: `old` performs the target now, `new` asks for it,
    `commit` is what *Replace* does to the table (the loaded preset's
    routes; no file). Until it is answered the table is untouched. Every commit goes
    through `Bindings.replace_owner`, which reads the target's owner at
    that moment — `old` is who to name, not who to remove."""
    _state(panel)["prompt"] = (old, new, commit)


def _wake(router: Router, b: Binding) -> Binding | None:
    """Replace, for a row waking onto a taken target: the owner goes, `b`
    comes on. Returns the row removed."""
    return router.table.replace_owner(b)


def _retarget(router: Router, b: Binding, picked: str) -> Binding | None:
    """Replace, for a row moved onto a taken target: the owner goes, `b`
    now points at `picked`. Returns the row removed."""
    return router.table.replace_owner(b, target=picked)


def _question(panel) -> tuple[Binding, Binding, Callable[[bool], object]] | None:
    """(old, new, settle) — the question up now and how to settle it:
    the page's own first (settle(True) commits), else a learn the referee
    refused (`panel.learn.pending`; settle is its `resolve_pending`).
    None when nothing asks."""
    st = _state(panel)
    held = st["prompt"]
    if held is not None:
        old, new, commit = held

        def settle(replace_it: bool) -> None:
            st["prompt"] = None
            if replace_it:
                commit()
        return old, new, settle
    lrn = panel.learn
    if lrn is not None and lrn.pending is not None:
        new, old = lrn.pending
        return old, new, lrn.resolve_pending
    return None


def prompt(panel) -> tuple[Binding, Binding] | None:
    """(old, new) of the question up now, or None."""
    q = _question(panel)
    return None if q is None else (q[0], q[1])


def answer(panel, replace_it: bool) -> None:
    """*Replace* (True) or *Keep* (False) for whatever `prompt` shows;
    Replace changes the loaded preset's routes — no file is written."""
    q = _question(panel)
    if q is None:
        return
    if replace_it:
        # one undo step for the swap (undo.py, plan 15); a held learn's own
        # push inside `resolve_pending` is this same frame's and is ignored
        undo.push(f"replace {q[0].target}")
    q[2](replace_it)


def modal(panel) -> None:
    """The Replace / Keep modal, drawn by the panel every frame — before
    anything else it draws, so a question shows on any page, with the
    panel hidden or collapsed; a learn can come from anywhere. A question
    withdrawn while the modal was up (a new learn armed) closes it."""
    st = _state(panel)
    q = _question(panel)
    st["modal"] = False                 # did the modal draw this frame (tests read it)
    if q is None:
        if imgui.is_popup_open(PROMPT):                  # stale: the question went away
            opened, _ = imgui.begin_popup_modal(PROMPT, None, imgui.WindowFlags_.no_title_bar)
            if opened:
                imgui.close_current_popup()
                imgui.end_popup()
        return
    old, new, _ = q
    router = router_of(panel)           # a question exists only over a table: never None
    if not imgui.is_popup_open(PROMPT):
        imgui.open_popup(PROMPT)
    vp = imgui.get_main_viewport()
    imgui.set_next_window_pos(vp.get_center(), imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5))
    imgui.set_next_window_size(imgui.ImVec2(PROMPT_W, 0))
    opened, _ = imgui.begin_popup_modal(
        PROMPT, None, imgui.WindowFlags_.no_saved_settings | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_title_bar)
    st["modal"] = opened
    if not opened:
        return
    p = panel.reg.get(new.target)
    label = p.label if p is not None else new.target
    who, asks = router.describe(old), router.describe(new)
    ui._micro("one performer per parameter")
    imgui.text_wrapped(f"{label} is already performed by {who}.")
    imgui.text_disabled(f"{asks} asks for it.")
    imgui.spacing()
    if ui.chip("Replace"):
        answer(panel, True)
        imgui.close_current_popup()
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{who} lets go; {asks}")
    imgui.same_line()
    if ui.chip("Keep"):
        answer(panel, False)
        imgui.close_current_popup()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Leave the table as it is")
    imgui.end_popup()


def ctx_item(panel, p: Param) -> None:
    """The context menu's line: route the selected band's lane to this param."""
    real = panel._real(p)
    if router_of(panel) is None:
        return
    if not real.modulatable:
        imgui.text_disabled("not modulatable")
        return
    if imgui.menu_item_simple("Route a lane here…"):
        add_route(panel, real.id)
        panel.reg["ui.page"].set(ui.PAGE_KEYS.index("routing"))


# ---- the rows ----

def source_schemes(router: Router) -> list[str]:
    """The continuous schemes the combo offers after the analyzer's lanes,
    in order (plan 27 B2: no fixed list here): the router's — the device
    registry's `continuous_schemes`, `lfo` then each listed device's feeds
    — then any other scheme a performer row names, so a preset's row on a
    device this rig lacks still shows its source."""
    out = [sc for sc in router.schemes() if sc != "lane"]
    for b in router.table.routes():
        # its Router key, qualifier and all (``axis@p2``, plan 27 B6)
        if b.head != "lane" and b.head not in out:
            out.append(b.head)
    return out


def _sources(panel, router: Router) -> list[tuple[str, str]]:
    """(source, label) the combo offers: every analyzer lane as "i NAME"
    (the names the audio engine publishes each frame, `AudioEngine.publish`),
    then each continuous scheme the registry lists (`source_schemes`) that
    is around — its device has published labels, it is being fed this
    frame, or a row names it — one
    entry per lane, labelled as the adapter says ("lfo LFO 1") or by
    index, and addressed by name where the adapter publishes names
    (`Router.address`: ``hand:right.roll``, decision register row 20).
    Nothing here knows what a scheme is: the bridge publishes its ext
    lanes' labels like any device (plan 27 B3), and a scheme no device
    publishes offers the lanes its rows name."""
    labels = getattr(router, "labels", {})
    # the lanes as the engine published them (AudioEngine.publish, each
    # frame); until it has — a panel with no frame loop behind it — the
    # chain's own names, so the combo always offers the lanes
    lanes = labels.get("lane") or panel.audio.chain.band_names
    out = [(f"lane:{i}", f"{i} {name}") for i, name in enumerate(lanes)]
    for scheme in source_schemes(router):
        names = labels.get(scheme) or []
        vec = router.feeds.get(scheme)
        used = any(b.head == scheme for b in router.table.bindings)
        if not (names or vec is not None or used):
            continue
        named = [b.index + 1 for b in router.table.bindings if b.head == scheme]
        n = len(names) or (len(vec) if vec is not None else 0) or max(named, default=0)
        # a lane published with an empty label is no lane (the `mod`
        # scheme's index 0 and a removed modifier's place)
        out += [(router.address(scheme, i), f"{scheme} {names[i] if i < len(names) else i}")
                for i in range(n) if not (i < len(names) and names[i] == "")]
    return out


def _gates(router: Router) -> list[tuple[str, str]]:
    """(address, label) for every switch an adapter offers as a gate — by
    name where the adapter publishes names (``hand:right.pinch.index``)."""
    return [(router.address(scheme, i), lb)
            for scheme, lanes in getattr(router, "gates", {}).items()
            for i, lb in lanes]


def _at(router: Router, addrs, addr: str | None) -> int:
    """Where `addr` is among `addrs`: the same string, else the same lane
    (a numeric ``hand:7`` from an older preset is the entry that names its
    lane ``hand:right.y``); −1 when none."""
    if addr in addrs:
        return addrs.index(addr)
    if addr is None:
        return -1
    lane = router.lane(addr)
    if lane[1] < 0:
        return -1
    return next((k for k, a in enumerate(addrs) if a is not None and router.lane(a) == lane), -1)


def _gate_combo(router: Router, b: Binding, gates: list[tuple[str, str]], width: float) -> None:
    """Which switch has to be held for this row to act, or none; a pick
    writes the switch's address (its name, where it has one)."""
    labels = ["no gate"] + [lb for _, lb in gates]
    addrs: list[str | None] = [None] + [a for a, _ in gates]
    cur = _at(router, addrs, b.when)
    if cur < 0:                        # a gate no adapter is offering now
        labels, addrs = labels + [b.when], addrs + [b.when]
        cur = len(addrs) - 1
    imgui.set_next_item_width(width)
    if imgui.begin_combo("##gate", labels[cur], imgui.ComboFlags_.no_arrow_button):
        for i, lb in enumerate(labels):
            sel, _ = imgui.selectable(lb, i == cur)
            if sel:
                b.when = addrs[i]
        imgui.end_combo()
    if imgui.is_item_hovered():
        imgui.set_tooltip("A pinch switch that must be held for this route to act — "
                          "the same hand movement can then mean two things")


def _live(panel, router: Router, b: Binding) -> float | None:
    """The source's normalized reading this frame, None while it isn't live."""
    scheme, i = router.lane(b.source)      # a number, or a name (`Router.names`)
    if scheme == "lane":
        a = panel.audio
        if not getattr(a, "on", False) or not 0 <= i < a.chain.n:
            return None
        return float(a.chain.lanes[i]) / CEIL
    vec = router.feeds.get(scheme)
    if vec is None or not 0 <= i < len(vec):
        return None
    u = float(vec[i])
    return None if math.isnan(u) else u     # NaN: a hand out of view


def _targets(panel) -> list[Param]:
    return [p for p in panel.reg if p.modulatable and not p.alias]


def _scales(panel, target: str | None = None) -> list[Param]:
    """What a row's scale may be: a continuous **session** param
    (master.gain on the rate routes; decision register row 18 (a)) — a
    macro scales a route as a depth subscriber (plan 13 §2.4), shown on the
    row as a chip, and a performance param is no attenuator a preset could
    carry — less the row's own target: a row scaled by what it pushes
    strobes (the push grows the scale grows the push, then clamps and lets
    go, every frame)."""
    reg = panel.reg
    return [q for q in reg if q.kind is Kind.CONTINUOUS and not q.alias
            and part_of(q) == "session" and q.id != target]


SESSION_MARK = "session"
SESSION_TIP = ("a session control: this route leans on it while its source is live; "
               "the setting itself is never changed")


def is_session_target(panel, b: Binding) -> bool:
    """Does the route perform a session param (decision register row 19 (a))?"""
    p = panel.reg.get(b.target)
    return p is not None and part_of(p) == "session"


def _depth_chips(router: Router, b: Binding) -> list[str]:
    """"× macro.N" for each macro whose depth subscriber names this route."""
    return [f"× {mid}" for mid, _ in router.table.depth_subs(b)]


def _param_combo(panel, label: str, current: str | None, width: float,
                 candidates, none: str | None = None) -> str | None | bool:
    """A searchable combo over params, grouped: returns the id picked, None
    for the `none` entry, or False when nothing changed. `candidates` is a
    list of params or a thunk for one — called only while the combo is
    open, so a closed row never walks the registry."""
    st = _state(panel)
    imgui.set_next_item_width(width)
    shown = current if current is not None else (none or "—")
    if not imgui.begin_combo(label, shown):
        return False
    if callable(candidates):
        candidates = candidates()
    picked: str | None | bool = False
    if imgui.is_window_appearing():
        st["filter"] = ""
        imgui.set_keyboard_focus_here()
    imgui.set_next_item_width(-1)
    _, st["filter"] = imgui.input_text_with_hint("##find", "find", st["filter"])
    needle = st["filter"].lower()
    if none is not None:
        sel, _ = imgui.selectable(none, current is None)
        if sel:
            picked = None
    group = None
    for p in candidates:
        if needle and needle not in p.id.lower() and needle not in p.label.lower():
            continue
        if p.group != group:
            group = p.group
            ui._micro(group or "misc")
        sel, _ = imgui.selectable(f"{p.id}##{p.id}", p.id == current)
        if imgui.is_item_hovered() and p.tip:
            imgui.set_tooltip(p.tip)
        if sel:
            picked = p.id
    imgui.end_combo()
    return picked


def _row(panel, router: Router, b: Binding, k: int) -> bool:
    """One route, two lines; returns True when the row asked to be deleted.
    The source combo's list is the one `page` built for this draw (the
    state's "sources"), else built here."""
    reg, st = panel.reg, _state(panel)
    imgui.push_id(k)
    p = reg.get(b.target)
    # line 1: on · source · target · op · ×
    changed, on = imgui.checkbox("##on", b.enabled)
    if changed:
        try:
            router.table.enable(b, on)      # waking a row asks the referee
        except Owned as e:
            ask(panel, e.existing, b, lambda: _wake(router, b))
        except ValueError as e:
            st["error"] = f"routing: {e}"
    if imgui.is_item_hovered():
        imgui.set_tooltip("Enabled — a dormant row keeps its settings and owns nothing")
    imgui.same_line()
    sources = st.get("sources") or _sources(panel, router)
    labels = [lb for _, lb in sources]
    cur = _at(router, [s for s, _ in sources], b.source)
    imgui.set_next_item_width(SRC_W)
    if cur < 0:
        labels, cur = labels + [b.source], len(labels)
    if imgui.begin_combo("##src", labels[cur], imgui.ComboFlags_.no_arrow_button):
        for i, lb in enumerate(labels):
            sel, _ = imgui.selectable(lb, i == cur)
            if sel and i < len(sources):
                router.table.move_route(b, source=sources[i][0])   # its subscribers too
        imgui.end_combo()
    imgui.same_line()
    sp = imgui.get_style().item_spacing.x
    op_w = ui.chip_w("push")
    feel_w = ui.chip_w("spring")
    session = is_session_target(panel, b)
    mark_w = imgui.calc_text_size(SESSION_MARK).x + sp if session else 0.0
    picked = _param_combo(panel, "##target", b.target,
                          -(feel_w + op_w + ui.chip_w("×") + 3 * sp + mark_w),
                          lambda: _targets(panel))
    if picked:
        cur = router.table.owner(picked)
        if cur is None or cur is b or not b.is_performer:
            router.table.move_route(b, target=picked)
        else:                               # the referee, on a retarget
            ask(panel, cur, replace(b, target=picked),
                lambda picked=picked: _retarget(router, b, picked))
    if p is None:
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"{b.target}: no such param — the row is dormant")
    elif not p.modulatable and imgui.is_item_hovered():
        imgui.set_tooltip(f"{b.target} is not modulatable — the row is dormant")
    if session:                             # row 19 (a): a route may lean on a session control
        imgui.same_line()
        imgui.text_colored(ui.DIM, SESSION_MARK)
        if imgui.is_item_hovered():
            imgui.set_tooltip(SESSION_TIP)
    imgui.same_line()
    _feel_chip(router, b, feel_w)
    imgui.same_line()
    label = OP_CHIP.get(b.op, "push")
    if ui.lit_chip(f"{label}##op", b.op != "push", ui.DIM, imgui.ImVec2(op_w, 0)):
        b.op = NEXT_OP.get(b.op, "push")
    if imgui.is_item_hovered():
        imgui.set_tooltip("push: depth × (source − rest) added to the base\n"
                          "pos:  depth × source is the position across the whole\n"
                          "      control, along its curve, while the source is live\n"
                          "click to switch")
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("×"))
    imgui.push_style_color(imgui.Col_.text, ui.DIM)
    kill = ui.chip("×")
    imgui.pop_style_color()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Delete this route")
    # line 2: depth · rest · scale · live
    imgui.dummy(imgui.ImVec2(18, 0))
    imgui.same_line()
    imgui.set_next_item_width(DEPTH_W)
    lo, hi, fmt = -DEPTH_MOD, DEPTH_MOD, "%+.2f"
    span = (hi - lo) or 1.0
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    changed, v = panel._track(
        lambda: imgui.slider_float("##depth", float(b.value), lo, hi, fmt),
        (float(b.value) - lo) / span, -lo / span if lo < 0 < hi else 0.0, knob=False,
    )
    imgui.pop_font()
    if changed:
        b.value = v
    if imgui.is_item_hovered():
        imgui.set_tooltip("Depth, signed" + DEPTH_TIP.get(b.op, DEPTH_TIP["push"])
                          + "\nctrl-click to type")
    imgui.same_line()
    if b.op == "push":
        auto = b.rest is None
        rest = router.rest_of(b.source) if auto else float(b.rest)
        imgui.set_next_item_width(REST_W)
        imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
        if auto:                                    # the source's own: shown, dimmed
            imgui.push_style_color(imgui.Col_.text, ui.DIM)
        changed, v = imgui.slider_float("##rest", rest, 0.0, 1.0, "%.2f")
        if auto:
            imgui.pop_style_color()
        imgui.pop_font()
        if changed:
            b.rest = v                              # dragged: the row's own number
        if imgui.is_item_hovered():
            imgui.set_tooltip("Rest — the source reading that pushes nothing"
                              + (" (the source's own)" if auto else " (this row's own)")
                              + "\ndrag to set the row's own; ctrl-click to type")
        imgui.same_line()
        if not auto:
            imgui.push_style_color(imgui.Col_.text, ui.DIM)
            if ui.chip(AUTO):
                b.rest = None
            imgui.pop_style_color()
            if imgui.is_item_hovered():
                imgui.set_tooltip("Back to the source's own rest")
            imgui.same_line()
    gates = _gates(router)
    gate_w = GATE_W if gates else 0.0
    for chip in _depth_chips(router, b):          # read-only: the macro's subscriber
        imgui.text_colored(ui.DIM, chip)
        if imgui.is_item_hovered():
            imgui.set_tooltip("A macro's depth subscriber scales this route "
                              "(plan 13 §2.4); edited with the macro, not here")
        imgui.same_line()
    scale = _param_combo(panel, "##scale", b.scale,
                         -(BAR_W + gate_w + sp * (2 if gate_w else 1)),
                         lambda: _scales(panel, b.target), none="× 1")
    if scale is not False:
        b.scale = scale
    if imgui.is_item_hovered():
        imgui.set_tooltip("A session param whose live value multiplies the depth — "
                          "master.gain, the drive fader, on the rate routes. Never the "
                          "row's own target, never a performance param: a macro scales "
                          "a route through its depth subscriber.")
    if gates:
        imgui.same_line()
        _gate_combo(router, b, gates, gate_w)
    imgui.same_line()
    _live_bar(panel, router, b, p)
    if b.motion is not None and b.motion.on:      # line 3: the row's own feel
        _feel_line(b)
    imgui.pop_id()
    return kill


def next_feel(m: Motion | None) -> Motion | None:
    """The feel chip's next step along FEEL_CYCLE, keeping the knobs."""
    mode = None if m is None else m.mode
    i = FEEL_CYCLE.index(mode) if mode in FEEL_CYCLE else -1
    nxt = FEEL_CYCLE[(i + 1) % len(FEEL_CYCLE)]
    if nxt is None:
        return None
    return Motion(nxt) if m is None else replace(m, mode=nxt)


def _feel_chip(router: Router, b: Binding, width: float) -> None:
    """The row's feel, as a chip that cycles FEEL_CYCLE: lit while the row
    has a feel of its own, dim on auto (the source's) and still."""
    mode = None if b.motion is None else b.motion.mode
    if ui.lit_chip(f"{FEEL_CHIP.get(mode, 'auto')}##feel", mode in ("follow", "spring"),
                   ui.DIM, imgui.ImVec2(width, 0)):
        b.motion = next_feel(b.motion)
    if imgui.is_item_hovered():
        src = router.source_feel(b.scheme)
        auto = ("the source's own: " + (src.describe() if src.on else "none")
                + (" (the pad's, on the settings page)" if b.scheme == "axis" else ""))
        now = (auto if b.motion is None else
               "still: the reading as it comes" if not b.motion.on else b.motion.describe())
        imgui.set_tooltip("Feel: how the reading travels before it acts\n"
                          "follow  the analyzer's envelope: attack away from rest,\n"
                          "        release back toward it, so a stick let go glides home\n"
                          "spring  a damped spring toward the reading, rings below 1\n"
                          f"now: {now}\n"
                          "click to cycle auto, follow, spring, still")


def _feel_line(b: Binding) -> None:
    """Two knobs for the row's own feel: attack / release, or Hz / damping."""
    m = b.motion
    imgui.dummy(imgui.ImVec2(18, 0))
    imgui.same_line()
    if m.mode == "follow":
        knobs = (("atk", 0.0, motion.ATK_MAX, "atk %.3f s", False,
                  "Attack: seconds to go 63 % of the way away from rest"),
                 ("rel", 0.0, motion.REL_MAX, "rel %.3f s", False,
                  "Release: seconds to go 63 % of the way back toward rest"))
    else:
        knobs = (("hz", motion.HZ_MIN, motion.HZ_MAX, "%.2f Hz", True,
                  "Spring frequency: low is lazy, high is tight"),
                 ("damp", 0.0, motion.DAMP_MAX, "damp %.2f", False,
                  ("Damping ratio: 1 arrives fastest with no overshoot,\n"
                   "below 1 overshoots and rings, above 1 creeps")))
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    for j, (k, lo, hi, fmt, log, tip) in enumerate(knobs):
        if j:
            imgui.same_line()
        imgui.set_next_item_width(FEEL_W)
        flags = imgui.SliderFlags_.logarithmic if log else 0
        changed, v = imgui.slider_float(f"##{k}", float(getattr(m, k)), lo, hi, fmt, flags)
        if changed:
            b.motion = m = replace(m, **{k: min(max(v, lo), hi)})
        if imgui.is_item_hovered():
            imgui.set_tooltip(tip + "\nctrl-click to type")
    imgui.pop_font()


def _live_bar(panel, router: Router, b: Binding, p: Param | None) -> None:
    """Source reading (white fill) and target effective norm (red hairline)."""
    u = _live(panel, router, b) if b.enabled else None
    h = imgui.get_frame_height()
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0, x1, y1 = pos.x, pos.y + 3, pos.x + BAR_W, pos.y + h - 3
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1),
                ui.u32(ui.LINE), 4.0)
    if u is not None:
        w = (x1 - x0 - 2) * min(max(u, 0.0), 1.0)
        dl.add_rect_filled(imgui.ImVec2(x0 + 1, y0 + 1), imgui.ImVec2(x0 + 1 + w, y1 - 1),
                           ui.u32(imgui.ImVec4(0.92, 0.92, 0.92, 0.85)), 3.0)
    if p is not None and p.modulated:
        x = x0 + 1 + (x1 - x0 - 2) * p.eff_norm
        dl.add_line(imgui.ImVec2(x, y0), imgui.ImVec2(x, y1), ui.u32(ui.RED), 2.0)
        panel.ghosts += 1
    imgui.dummy(imgui.ImVec2(BAR_W, h))
    if imgui.is_item_hovered():
        src = "not live" if u is None else f"{u:.2f}"
        tgt = "—" if p is None else (f"{p.text()} → {panel._eff_text(p)}" if p.modulated
                                     else p.text())
        imgui.set_tooltip(f"source {src}  ·  target {tgt}")


# ---- the head: the loaded preset, the layer, the last learn, the load's notes ----

def _presets(panel):
    """The library's `Presets` (preset.py), or None on a panel without one."""
    lib = panel.library
    if lib is None or lib.reg is None or PRESETS not in lib.kinds:
        return None
    return getattr(lib, "presets", None)


def _save_as(panel, name: str) -> None:
    ui_presets._guard(panel, panel.library.save_as, PRESETS, name)
    ui_presets.invalidate(panel, PRESETS)


def head(panel, router: Router) -> None:
    """The loaded preset · its dirty dot · the layer up · save · as…; then
    the last learn and the last load's notes. The preset strip's own
    save / as… (ui_presets), over the same preset — a factory one gets a
    user shadow (`Library.overwrite`)."""
    lib, table, st = panel.library, router.table, _state(panel)
    pr = _presets(panel)
    imgui.push_id("head")
    if pr is None or not ui_presets._name_field(panel, NAMING, lambda n: _save_as(panel, n)):
        _preset_line(panel, pr, table)
    imgui.pop_id()
    _learn_line(panel)
    if st["error"]:
        imgui.text_colored(ui.WARN, st["error"])
    if lib is not None and lib.error and PRESETS in lib.error:
        imgui.text_colored(ui.WARN, lib.error)          # a preset that would not load
    # the desk rows the last load dropped (an invariant control, D6), on
    # one line so a file full of them never pushes the page off the window
    notes = getattr(pr, "desk_notes", None) or []    # (a Presets from before a hot reload)
    if notes:
        more = f"  (+{len(notes) - 1} more)" if len(notes) > 1 else ""
        imgui.text_colored(ui.WARN, f"desk: {notes[0]}{more}")
        if len(notes) > 1 and imgui.is_item_hovered():
            imgui.set_tooltip("\n".join(notes))
    # what the referee refused from the last preset (one owner per target)
    # and what a migration dropped or moved, until the next edit
    for b, why in table.dropped:
        imgui.text_colored(ui.WARN, f"dropped {b.source} → {b.target}: {why}")
    for note in table.notes:
        imgui.text_disabled(note)
    # a loop no delay breaks (plan 28 N0): the cable the patch keeps off, while it stands
    for note in getattr(router, "patch_notes", ()):
        imgui.text_colored(ui.WARN, note)


def _preset_line(panel, pr, table) -> None:
    lib = panel.library
    cur = pr.current if pr is not None else None
    ui._micro("preset")
    imgui.same_line()
    imgui.text(cur or ("—" if pr is not None else "no preset library"))
    if imgui.is_item_hovered():
        imgui.set_tooltip("The loaded preset: its routes, its desk and its macros are "
                          "this page. A learn or an edit here changes it — the dot — "
                          "and writes nothing until save" if cur else "no preset loaded")
    edited = pr is not None and cur is not None and ui_presets.dirty(panel, PRESETS)
    rects = ui_presets._state(panel)["rects"]
    rects.pop("head.dot", None)
    if edited:
        imgui.same_line(0, 4)
        rects["head.dot"] = ui.dirty_dot("edited since it loaded — save writes it")
    glob = table.layer == "global"
    layer = f"desk layer: {'global' if glob else 'preset'}"
    word = ui_presets.save_label(lib, PRESETS) if lib is not None else "save"
    sp = imgui.get_style().item_spacing.x
    imgui.same_line(imgui.get_content_region_avail().x
                    - ui.chip_w(word, "as…") - ui._micro_width(layer) - sp)
    ui._micro(layer, ui.RED if glob else ui.DIM)
    if imgui.is_item_hovered():
        imgui.set_tooltip("The desk's layer — SHIFT latches it (desk.shift). Global: "
                          "the session's controls, never learned (a learn is refused); "
                          "preset: the loaded preset's desk. A preset load drops to it.")
    imgui.same_line()
    # the preset strip's own save chip: "save copy" on a factory preset,
    # lit while there is something to save (plan 19 WP5)
    if lib is None:
        imgui.begin_disabled()
        ui.chip(word)
        imgui.end_disabled()
    elif ui_presets.save_chip(panel, PRESETS, word, edited, key="head"):
        ui_presets._guard(panel, lib.overwrite, PRESETS)
        ui_presets.invalidate(panel, PRESETS)
    imgui.same_line()
    imgui.begin_disabled(pr is None)
    if ui.chip("as…"):
        ui_presets._begin_naming(panel, NAMING, cur or "")
    imgui.end_disabled()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Save the live state as a new user preset")


def _learn_line(panel) -> None:
    """What the armed learn waits for, or what the last one did — a
    refusal (the global layer, an invariant control) in the warning colour."""
    lrn = panel.learn
    if lrn is None:
        return
    refused = getattr(lrn, "refused", False)
    if lrn.learning and not (refused and lrn.last):
        imgui.text_colored(ui.RED, f"learning {lrn.learning} — {panel._learn_hint()}")
    elif lrn.last:
        # a refusal leaves the learn armed (plan 17 fork 6): the reason, and that it still waits
        still = f" — still learning {lrn.learning}" if lrn.learning and refused else ""
        imgui.push_style_color(imgui.Col_.text, ui.WARN if refused else ui.FAINT)
        imgui.text_wrapped(f"learn: {lrn.last}{still}")
        imgui.pop_style_color()


# ---- the desk: the loaded preset's layer ----

def control_name(table, b: Binding) -> str:
    """The control a MIDI row names, in Akai's words where the table's
    profile has them ("track knob 3"), else the row's own ("MIDI CC 48 ch1")."""
    name = apc40.control_name(b.source) if table.profile == "apc40" else None
    return name or b.describe()


def control_glyph(table, b: Binding) -> str:
    """What a desk or session row prints first: the control's glyph on the
    on-screen desk ("D3", plan 14 WP7), else the row's own name."""
    g = apc40.glyph(b.source) if table.profile == "apc40" else None
    return g or b.describe()


def _control_cell(table, b: Binding, color=None) -> None:
    """The glyph, and Akai's name and the row's source on hover."""
    if color is None:
        imgui.text(control_glyph(table, b))
    else:
        imgui.text_colored(color, control_glyph(table, b))
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{control_name(table, b)}  ·  {b.describe()}")


def _op_text(b: Binding) -> str:
    if b.op == "set":
        return f"set {b.value:g}"
    if b.op == "step":
        return f"step {b.value:+g}"
    return b.op


def _column(names: list[str]) -> float:
    """The control column: CONTROL_W, or the widest name and a gap."""
    sp = imgui.get_style().item_spacing.x
    widest = max((imgui.calc_text_size(n).x for n in names), default=0.0)
    return max(CONTROL_W, widest + 2 * sp)


def preset_controls(table) -> list[Binding]:
    """One factory row per control the profile's map puts on a layer — the
    controls a preset may map (the invariant ones are the session's)."""
    seen: set[str] = set()
    out = []
    inv = table.invariant_rows()
    for f in factory_desk(table.profile):
        if f.layer is None or f.source in seen or table.is_invariant(f, inv):
            continue
        seen.add(f.source)
        out.append(f)
    return out


# `unmapped`'s last answer, against the signature it was worked out for
_DARK: dict = {}


def _dark_signature(table) -> tuple:
    """Everything `unmapped` reads: the profile (its factory map), the MIDI
    roles (`is_primary`), and each row's source (scheme, device, channel,
    number — all `overlaps` compares), layer and enabled flag (which rows
    are invariant, which are the desk). The target too, though no answer
    reads it — cheap, and safe. Field values, never row identity."""
    return (table.profile, tuple(getattr(table, "midi_roles", ())),
            tuple((b.source, b.layer, b.enabled, b.target) for b in table.bindings))


def unmapped(table) -> list[Binding]:
    """The preset-layer controls the loaded preset leaves dark (D8).
    A pairwise scan of the table (~10 ms on the rig), so the ROUTING page
    draw remembers the last answer until the table's signature changes."""
    sig = _dark_signature(table)
    if _DARK.get("sig") != sig:
        rows = table.desk()
        _DARK["rows"] = [f for f in preset_controls(table)
                         if not any(b.overlaps(f) for b in rows)]
        _DARK["sig"] = sig
    return list(_DARK["rows"])


def desk_target(p: Param) -> bool:
    """Can a desk control be put on this param? Not on a file path (a knob
    cannot set one), not on SHIFT's own param, and not on the desk's SAVE
    (plan 24 C1: a learned toggle or key would latch it on, and every bank
    pad's tap would then make a new preset). One rule for the desk rows'
    target combo and for the menu's "Learn desk" (`Panel._desk_target`)."""
    return p.kind is not Kind.TEXT and p.id not in (SHIFT_PARAM, SAVE_PARAM)


def _desk_targets(panel) -> list[Param]:
    return [p for p in panel.reg if desk_target(p)]


def _desk_edited(table, b: Binding | None = None) -> None:
    """A desk row changed on the page: the MIDI adapter redraws the desk —
    only redraws: no base moved, so the faders keep their catch (a
    `desk_serial` bump would read as a preset load)."""
    if b is not None:
        b.last_out = None
    table.redraw_serial = getattr(table, "redraw_serial", 0) + 1


def desk(panel, router: Router) -> None:
    """The preset layer: control · target ▾ · op · ×, a line a row, then a
    dimmed line per preset control this preset leaves dark."""
    table = router.table
    rows = table.desk()
    ui._micro("desk  ·  preset layer")
    if imgui.is_item_hovered():
        imgui.set_tooltip("The loaded preset's own controls on the APC40 (SHIFT off). "
                          "A control the preset leaves unmapped is dark and does nothing.")
    imgui.same_line()
    # (the click is the on-screen desk's, once it has one: plan 17 WP4's
    # `ui_desk.click`.) The longest wording that fits beside the title; the
    # whole of it on hover
    full = ("new rows: right-click a param → Learn desk"
            + (", or click a control" if hasattr(ui.ui_desk, "click") else ""))
    room = imgui.get_content_region_avail().x
    short = full.replace("right-click a param → ", "")
    said = next((t for t in (full, short, short.replace("new rows:", "new:"))
                 if imgui.calc_text_size(t).x <= room),
                ui.fit_text(short.replace("new rows:", "new:"), room))
    imgui.text_colored(ui.FAINT, said)
    if said != full and imgui.is_item_hovered():
        imgui.set_tooltip(full)
    sp = imgui.get_style().item_spacing.x
    op_w = imgui.calc_text_size("step +10").x
    dark = unmapped(table)
    col = _column([control_glyph(table, b) for b in (*rows, *dark)])
    dead = None
    drawn = 0
    for k, b in enumerate(rows):                 # k: its place unfiltered — the imgui id
        if not _shown(panel, router, ("desk", id(b)), control_hay, b):
            continue
        drawn += 1
        y0 = imgui.get_cursor_screen_pos().y
        imgui.push_id(f"desk{k}")
        _control_cell(table, b)
        imgui.same_line(col)
        picked = _param_combo(panel, "##target", b.target, -(op_w + ui.chip_w("×") + 2 * sp),
                              lambda: _desk_targets(panel))
        if picked:
            b.target = picked
            _desk_edited(table, b)
        if b.target not in panel.reg and imgui.is_item_hovered():
            imgui.set_tooltip(f"{b.target}: no such param — the control does nothing")
        imgui.same_line()
        imgui.text_disabled(_op_text(b))
        imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("×"))
        imgui.push_style_color(imgui.Col_.text, ui.DIM)
        if ui.chip("×"):
            dead = b
        imgui.pop_style_color()
        if imgui.is_item_hovered():
            imgui.set_tooltip("Take this control out of the preset — it goes dark")
        imgui.pop_id()
        _mark_line(panel, table, b, "desk", y0)
    if dead is not None:
        undo.push(f"unmap {control_glyph(table, dead)}")     # one undo step (undo.py)
        table.remove(dead)
        _desk_edited(table)
    for f in dark:
        if not _shown(panel, router, ("dark", f.source), control_hay, f, False):
            continue
        drawn += 1
        y0 = imgui.get_cursor_screen_pos().y
        _control_cell(table, f, ui.FAINT)
        imgui.same_line(col)
        imgui.text_colored(ui.FAINT, "unmapped — dark")
        _mark_line(panel, table, f, "desk", y0)
    if not drawn and (rows or dark):
        imgui.text_disabled(NO_MATCH)
    elif not rows:
        imgui.text_disabled("an empty desk — every preset control is dark")


# ---- the macros ----

def _macro(table, mid: str) -> Macro:
    return table.macros.setdefault(mid, Macro())


def _macros_edited(table) -> None:
    """A subscriber changed: the router re-lands the base subscribers."""
    table.macros_serial += 1


def shared_bases(table) -> dict[str, list[str]]:
    """{param: [macro ids]} for every param more than one macro
    base-subscribes (plan 13 §2.4: the last write wins; the page marks it)."""
    by: dict[str, list[str]] = {}
    for mid, m in table.macros.items():
        for s in m.subs:
            if s.base is not None and mid not in by.setdefault(s.base, []):
                by[s.base].append(mid)
    return {pid: sorted(mids) for pid, mids in by.items() if len(mids) > 1}


def base_targets(panel) -> list[Param]:
    """What a base subscriber may set: a persisted, non-alias
    **performance** param — never a session one, which a preset never
    moves (plan 13 D9; `routing.base_refusal`) — and not a macro."""
    return [q for q in panel.reg if q.kind not in (Kind.TRIGGER, Kind.TEXT)
            and q.group != "macro" and base_refusal(q.id, panel.reg) is None]


def _route_combo(router: Router, s: Sub, width: float) -> bool:
    """The route a depth subscriber scales, over the table's performer rows."""
    routes = router.table.routes()

    def name(r: Binding) -> str:
        return f"{router.describe(r)} → {r.target}"
    cur = next((r for r in routes if (r.source, r.target) == s.depth), None)
    shown = name(cur) if cur is not None else f"{s.depth[0]} → {s.depth[1]} (no route)"
    imgui.set_next_item_width(width)
    changed = False
    if imgui.begin_combo("##route", shown):
        for i, r in enumerate(routes):
            sel, _ = imgui.selectable(f"{name(r)}##r{i}", r is cur)
            if sel:
                s.depth, changed = (r.source, r.target), True
        imgui.end_combo()
    return changed


def _sub(panel, router: Router, mid: str, s: Sub, shared: dict[str, list[str]]) -> bool:
    """One subscriber line; True when it asked to be removed."""
    table, sp = router.table, imgui.get_style().item_spacing.x
    imgui.dummy(imgui.ImVec2(INDENT, 0))
    imgui.same_line()
    others = [m for m in shared.get(s.base, []) if m != mid] if s.base is not None else []
    mark = "shared" if others else ""
    right = 2 * SUB_W + ui.chip_w("×") + 3 * sp + (imgui.calc_text_size(mark).x + sp
                                                  if mark else 0.0)
    kind = "depth" if s.depth is not None else "base"
    imgui.text_disabled(f"{kind:<5}")
    imgui.same_line()
    edited = False
    if s.depth is not None:
        edited = _route_combo(router, s, -right)
        lo, hi, fmt = -DEPTH_MOD, DEPTH_MOD, "%+.2f"
        tip = "× the route's depth at the macro's 0 / 1 — a range may cross zero"
    else:
        picked = _param_combo(panel, "##base", s.base, -right, lambda: base_targets(panel))
        if picked:
            s.base, edited = picked, True
        lo, hi, fmt = 0.0, 1.0, "%.2f"
        tip = "the param's fader position at the macro's 0 / 1 — from > to runs the other way"
    imgui.same_line()
    imgui.set_next_item_width(SUB_W)
    changed, v = imgui.slider_float("##from", float(s.lo), lo, hi, "from " + fmt)
    if changed:
        s.lo, edited = v, True
    if imgui.is_item_hovered():
        imgui.set_tooltip(tip)
    imgui.same_line()
    imgui.set_next_item_width(SUB_W)
    changed, v = imgui.slider_float("##to", float(s.hi), lo, hi, "to " + fmt)
    if changed:
        s.hi, edited = v, True
    if imgui.is_item_hovered():
        imgui.set_tooltip(tip)
    if mark:
        imgui.same_line()
        imgui.text_colored(ui.WARN, mark)
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"{s.base} is set by {', '.join(others)} too — "
                              "the last write wins")
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("×"))
    imgui.push_style_color(imgui.Col_.text, ui.DIM)
    kill = ui.chip("×")
    imgui.pop_style_color()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Remove this subscriber")
    if edited:
        _macros_edited(table)
    return kill


def macros(panel, router: Router) -> None:
    """The eight macro knobs, each the panel's compact slider — so Learn,
    "Route a lane here…" and the `base → effective` readout under a
    performer come for free — with its label and its subscribers."""
    ms = panel.reg.group("macro")
    if not ms:
        return
    table = router.table
    ui._micro("macros")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Knobs that do nothing on their own: a base subscriber sets a "
                          "param as the knob turns, a depth subscriber scales a route")
    shared = shared_bases(table)
    sp = imgui.get_style().item_spacing.x
    routes = table.routes()
    drawn = 0
    for k, p in enumerate(ms):                   # a macro that matches is drawn whole
        if not _shown(panel, router, ("macro", p.id), macro_hay, p):
            continue
        drawn += 1
        imgui.push_id(f"macro{k}")
        m = table.macros.get(p.id)
        panel._label_cell(str(k + 1), width=MACRO_LABEL_W)
        imgui.set_next_item_width(MACRO_NAME_W)
        changed, text = imgui.input_text_with_hint("##label", "label", m.label if m else "")
        if changed:
            _macro(table, p.id).label = text
        imgui.same_line()
        panel._slider(p.id, -(ui.chip_w("+ base", "+ depth") + sp))
        imgui.same_line()
        if ui.chip("+ base"):
            q = panel.reg.get("view.bright") or base_targets(panel)[0]
            # from = to = where the param sits: adding it moves nothing
            _macro(table, p.id).subs.append(Sub(base=q.id, lo=q.norm, hi=q.norm))
            _macros_edited(table)
        if imgui.is_item_hovered():
            imgui.set_tooltip("A param whose base this knob sets")
        imgui.same_line()
        imgui.begin_disabled(not routes)
        if ui.chip("+ depth"):
            r = routes[0]
            _macro(table, p.id).subs.append(Sub(depth=(r.source, r.target), lo=0.0, hi=1.0))
            _macros_edited(table)
        imgui.end_disabled()
        if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            imgui.set_tooltip("A route whose depth this knob scales" if routes
                              else "no routes to scale")
        if m is not None:
            dead = None
            for j, s in enumerate(m.subs):
                imgui.push_id(j)
                if _sub(panel, router, p.id, s, shared):
                    dead = j
                imgui.pop_id()
            if dead is not None:
                undo.push(f"delete subscriber of {m.label or p.id}")   # one undo step
                m.subs.pop(dead)
                _macros_edited(table)
        imgui.pop_id()
    if not drawn:
        imgui.text_disabled(NO_MATCH)


# ---- the modifiers (plan 28 N1) ----
#
# One block per modifier, under the routes:
#
#   mod 2  combine   [mod 1 smooth ▾] [0 sub ▾]        ▮▮▮▯▯ 0.42   ×
#          how ▾   balance ─────────
#
# The kind is fixed once added (a combo of `KINDS` beside "+ modifier"
# picks the next one's); each input is a combo over the route sources
# (`modifier_sources`: `_sources` plus every modifier's own lane); the
# params are the panel's own widgets over `mod.<n>.<p>` (so Learn, "Route
# a lane here…" and the base → effective readout come with them); the bar
# is the live output. Every edit is the loaded preset's (its dirty dot,
# one undo step); nothing is written.

MOD_KIND_W = 96.0        # the "+ modifier" kind combo
MOD_IN_W = 150.0         # an input's source combo
MOD_ID_W = 52.0          # "mod 2" beside the block


def mod_hay(panel, router: Router, m: Modifier) -> tuple[str, ...]:
    """What the filter searches on a modifier: its id, kind and inputs."""
    return (m.id, f"mod {m.n}", m.kind, *m.inputs)


def modifier_sources(panel, router: Router, mid: str | None = None) -> list[tuple[str, str]]:
    """(address, label) an input may read: every route source (`_sources`)
    and every modifier's output lane but `mid`'s own — a modifier reading
    itself is a loop (N0 refuses one with no delay in it)."""
    out = [(a, lb) for a, lb in _sources(panel, router) if not a.startswith("mod:")]
    out += [(m.address, f"mod {m.n} {m.kind}") for m in router.table.modifiers
            if m.id != mid]
    return out


def add_modifier(panel, kind: str, inputs=(), **params: float) -> Modifier:
    """"+ modifier": a new `kind` node into the loaded preset, its params
    declared (`Bindings.add_modifier`); one undo step."""
    router = router_of(panel)
    undo.push(f"add modifier {kind}")
    return router.table.add_modifier(kind, inputs, panel.reg, **params)


def set_modifier_input(panel, mid: str, k: int, source: str) -> None:
    """Input `k` of modifier `mid` reads `source` from now on: the
    modifier replaced whole (`Bindings.set_modifiers`, its params at their
    bases), one undo step."""
    table = router_of(panel).table
    m = table.modifier(mid)
    if m is None or not 0 <= k < len(m.inputs) or m.inputs[k] == source:
        return
    undo.push(f"modifier input {mid}")
    table.set_modifier_input(mid, k, source, panel.reg)


def remove_modifier(panel, mid: str) -> None:
    """The ×: the modifier and its params go; a route on its lane stays,
    dormant. One undo step."""
    router = router_of(panel)
    undo.push(f"delete modifier {mid}")
    router.table.remove_modifier(mid, panel.reg)


def modifier_output(router: Router, mid: str) -> float | None:
    """The modifier's output lane this frame; None while it is dormant."""
    m = router.table.modifier(mid)
    vec = router.feeds.get("mod")
    if m is None or vec is None or not 0 <= m.n < len(vec):
        return None
    u = float(vec[m.n])
    return None if math.isnan(u) else u


def _input_combo(panel, router: Router, m: Modifier, k: int,
                 srcs: list[tuple[str, str]], width: float) -> None:
    addrs = [a for a, _ in srcs]
    labels = [lb for _, lb in srcs]
    cur = _at(router, addrs, m.inputs[k]) if m.inputs[k] else -1
    shown = labels[cur] if cur >= 0 else (m.inputs[k] or "pick a source")
    imgui.set_next_item_width(width)
    if imgui.begin_combo(f"##in{k}", shown):
        for i, lb in enumerate(labels):
            sel, _ = imgui.selectable(f"{lb}##{i}", i == cur)
            if sel:
                set_modifier_input(panel, m.id, k, addrs[i])
        imgui.end_combo()
    if imgui.is_item_hovered():
        imgui.set_tooltip("What this modifier reads — an analyzer lane, a device's lane, "
                          "an LFO, or another modifier's output")


def _mod_bar(router: Router, m: Modifier) -> None:
    """The live output: a filled bar and its number; "dormant" while an
    input is not live."""
    u = modifier_output(router, m.id)
    h = imgui.get_frame_height()
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0, x1, y1 = pos.x, pos.y + 3, pos.x + BAR_W, pos.y + h - 3
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), ui.u32(ui.LINE), 4.0)
    if u is not None:
        w = (x1 - x0 - 2) * min(max(u, 0.0), 1.0)
        dl.add_rect_filled(imgui.ImVec2(x0 + 1, y0 + 1), imgui.ImVec2(x0 + 1 + w, y1 - 1),
                           ui.u32(imgui.ImVec4(0.92, 0.92, 0.92, 0.85)), 3.0)
    imgui.dummy(imgui.ImVec2(BAR_W, h))
    imgui.same_line()
    imgui.text_disabled("dormant" if u is None else f"{u:.2f}")
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{m.address}: what a route on this modifier reads"
                          + (" — a trigger, 1 while it fires" if m.out == "trigger" else ""))


def modifiers(panel, router: Router) -> None:
    """The MODIFIERS strip: "+ modifier" with its kind, then each modifier
    — its inputs, its params, its live output, ×. A route reads one by
    picking ``mod <n>`` in its source combo."""
    table, reg = router.table, panel.reg
    st = _state(panel)
    st.setdefault("mod_kind", "smooth")
    ui._micro("modifiers")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Nodes between a source and a route: curve, scale, smooth, "
                          "combine two, a threshold that fires, a one-frame delay")
    sp = imgui.get_style().item_spacing.x
    imgui.same_line(imgui.get_content_region_avail().x
                    - (MOD_KIND_W + ui.chip_w("+ modifier") + sp))
    imgui.set_next_item_width(MOD_KIND_W)
    if imgui.begin_combo("##modkind", st["mod_kind"]):
        for kind in MOD_KINDS:
            sel, _ = imgui.selectable(kind, kind == st["mod_kind"])
            if sel:
                st["mod_kind"] = kind
        imgui.end_combo()
    imgui.same_line()
    if ui.chip("+ modifier"):
        add_modifier(panel, st["mod_kind"])
    if imgui.is_item_hovered():
        imgui.set_tooltip("A new modifier of this kind; pick its input, then route its "
                          "output (mod <n>) like any source")
    mods = table.modifiers
    if not mods:
        imgui.text_disabled("no modifiers — routes read their sources as they are")
        return
    dead = None
    drawn = 0
    for m in mods:
        if not _shown(panel, router, ("mod", m.id), mod_hay, m):
            continue
        drawn += 1
        imgui.push_id(f"mod{m.id}")
        panel._label_cell(f"mod {m.n}", width=MOD_ID_W)
        imgui.text_colored(ui.DIM, m.kind)
        srcs = modifier_sources(panel, router, m.id)
        for k in range(len(m.inputs)):
            imgui.same_line()
            _input_combo(panel, router, m, k, srcs, MOD_IN_W)
        imgui.same_line()
        _mod_bar(router, m)
        imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("×"))
        imgui.push_style_color(imgui.Col_.text, ui.DIM)
        if ui.chip("×"):
            dead = m.id
        imgui.pop_style_color()
        if imgui.is_item_hovered():
            imgui.set_tooltip("Remove this modifier — a route on it goes dormant")
        specs = MOD_PARAMS[m.kind]
        if specs:
            imgui.dummy(imgui.ImVec2(MOD_ID_W, 0))
            width = (imgui.get_content_region_avail().x - MOD_ID_W) / len(specs) - sp
            for s in specs:
                pid = f"{m.id}.{s.key}"
                if pid not in reg:
                    continue
                imgui.same_line()
                if s.kind == "toggle":
                    panel._check(pid, s.label)
                elif s.kind == "enum":
                    panel._combo(pid, width)
                else:
                    panel._slider(pid, width)
        imgui.pop_id()
        imgui.separator()
    if dead is not None:
        remove_modifier(panel, dead)
    if not drawn:
        imgui.text_disabled(NO_MATCH)


# ---- the session's rows, read-only ----

def session(panel, router: Router) -> None:
    """The invariant and global-layer MIDI rows: bindings.json's, shown so a
    preset mapping one of them (dropped at load, in the head's notes) can
    be seen; never learned or edited here (D5, D6)."""
    table = router.table
    inv, glob = _session_rows(table)
    ui._micro("session")
    imgui.same_line()
    imgui.text_disabled("the session's — edit bindings.json")
    col = _column([control_glyph(table, b) for b in (*inv, *glob)])
    had = bool(inv or glob)
    inv, glob = ([b for b in rows if _shown(panel, router, ("session", id(b)), control_hay, b)]
                 for rows in (inv, glob))
    if had and not (inv or glob):
        imgui.text_disabled(NO_MATCH)
    for title, rows in (("invariant · both layers", inv), ("global layer · SHIFT on", glob)):
        if not rows:
            continue
        imgui.text_colored(ui.DIM, title)
        for b in rows:
            y0 = imgui.get_cursor_screen_pos().y
            _control_cell(table, b, ui.FAINT)
            imgui.same_line(col)
            op = _op_text(b)
            imgui.text_colored(ui.FAINT, b.target + ("" if op in ("abs", "toggle") else f"  {op}"))
            _mark_line(panel, table, b, "session", y0)


# ---- the sinks (plan 27 B3) ----

def sink_hay(panel, router: Router, b: Binding) -> tuple[str, ...]:
    """What the filter searches on a sink row: its source, the param's
    label, its port and the row's words."""
    pid = b.source.partition(":")[2] if b.scheme == "param" else None
    return (b.source, b.target, _label(panel, pid) if pid else "", router.describe(b))


def sinks(panel, router: Router) -> None:
    """The sink rows: what goes *out* — a param's effective value or a
    lane to a sink port (``param:view.bright → bridge:3``), the session's
    (bindings.json; sinks are rig). A row's checkbox and its × write the
    file now; a new one comes from a param's right-click → Learn sink ▸."""
    table = router.table
    rows = table.sinks(enabled=False)
    ui._micro("sinks")
    imgui.same_line()
    imgui.text_disabled("the session's — out to a sink · right-click a param: Learn sink")
    if not rows:
        imgui.text_disabled("nothing goes out")
        return
    shown = [b for b in rows if _shown(panel, router, ("sink", id(b)), sink_hay, b)]
    if not shown:
        imgui.text_disabled(NO_MATCH)
    dead = None
    for k, b in enumerate(rows):
        if not any(b is x for x in shown):
            continue
        imgui.push_id(f"sink{k}")
        changed, on = imgui.checkbox("##on", b.enabled)
        if changed:
            b.enabled = on
            table.write()
        imgui.same_line()
        (imgui.text if b.enabled else imgui.text_disabled)(router.describe(b))
        imgui.same_line()
        if ui.chip("×"):
            dead = b
        if imgui.is_item_hovered():
            imgui.set_tooltip("Stop sending this — bindings.json is written now")
        imgui.pop_id()
    if dead is not None:
        table.remove(dead)
        table.write()


# ---- the page ----

def _find_w(on: bool) -> float:
    """What the counts line's right side takes: the field, its × while it
    holds text, and `+ route`."""
    sp = imgui.get_style().item_spacing.x
    return FIND_W + sp + ui.chip_w("+ route") + (ui.chip_w("×") + sp if on else 0.0)


def _find_field(panel) -> None:
    """The filter, on the counts line and flush right, leaving `+ route`
    its place: the field and, while it holds text, the × that empties it.
    Emptying it is one state write — `_state(panel)["find"] = ""`. Drawn
    before the rows: it starts the frame's set of drawn lines."""
    st = _state(panel)
    on = bool(st["find"].strip())               # spaces alone filter nothing
    imgui.same_line(imgui.get_content_region_avail().x - _find_w(on))
    imgui.set_next_item_width(FIND_W)
    _, st["find"] = imgui.input_text_with_hint("##rows", "filter", st["find"])
    if st.get("unfind"):
        # a desk click cleared the filter (`goto`); a field that had the
        # keyboard at that moment writes its edit buffer back on the frame
        # it lets go of it — the clear holds until it has
        st["find"] = ""
        st["unfind"] = imgui.is_item_active()
    # a widget in use other than this field holds the lines it is on (`_shown`)
    st["hold"] = not imgui.is_item_active() and (
        imgui.is_any_item_active() or imgui.is_popup_open("", imgui.PopupFlags_.any_popup))
    st["kept"], st["drawn"] = st["drawn"], set()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Show only the lines that say every word typed: a glyph (d3), "
                          "a param (kaleido), a source (lfo 1)")
    imgui.same_line()
    if on:
        imgui.push_style_color(imgui.Col_.text, ui.DIM)
        if ui.chip("×##find"):
            st["find"] = ""
        imgui.pop_style_color()
        if imgui.is_item_hovered():
            imgui.set_tooltip("Clear the filter — every row is shown")
        imgui.same_line()


def page(panel, dt: float) -> None:
    router = router_of(panel)
    ui._micro("routing")
    if router is None:
        imgui.separator()
        imgui.text_disabled("no router attached")
        return
    head(panel, router)
    imgui.separator()
    rows = router.table.routes()
    _pick_row(panel)            # the picked desk control: `_mark_line` frames and scrolls to it
    chain = panel.audio.chain
    live = "live" if getattr(panel.audio, "on", False) else "no source — lanes idle"
    st = _state(panel)
    if st["find"].strip():                      # filtered: say so, in red
        n, m = found(panel, router)
        imgui.text_colored(ui.RED, f"{n} of {m} rows")
        if imgui.is_item_hovered():
            imgui.set_tooltip("The filter hides the rest — × beside it shows every row")
    else:
        # the counts give way to the field: the longest wording that fits
        # beside it, the whole of it on hover
        full = f"{len(rows)} routes  ·  {chain.n} lanes  ·  {live}"
        room = (imgui.get_content_region_avail().x - _find_w(False)
                - imgui.get_style().item_spacing.x)
        shown = next((t for t in (full, f"{len(rows)} routes  ·  {chain.n} lanes")
                      if imgui.calc_text_size(t).x <= room), f"{len(rows)} routes")
        imgui.text_disabled(shown)
        if shown != full and imgui.is_item_hovered():
            imgui.set_tooltip(full)
    _find_field(panel)
    if ui.chip("+ route"):
        pid = f"pattern.mod.{panel.control.selb}"
        add_route(panel, pid if pid in panel.reg else _targets(panel)[0].id)
    if imgui.is_item_hovered():
        imgui.set_tooltip("A new route from the selected band's lane — or right-click "
                          "any control: Route a lane here…")
    # the routes, the desk, the macros and the session scroll together if
    # they must; the head and the counts stay put
    if imgui.begin_child("##routes", imgui.ImVec2(0, 0)):
        ui._micro("routes")
        dead, drawn = None, 0
        # the source combo's list, once a draw: the same for every row (once
        # a row, it scanned the whole table per scheme ~20 times a frame)
        st["sources"] = _sources(panel, router) if rows else None
        for k, b in enumerate(rows):            # k: its place unfiltered — the imgui id
            if not _shown(panel, router, ("route", id(b)), route_hay, b):
                continue
            drawn += 1
            if _row(panel, router, b, k):
                dead = b
            imgui.separator()
        st["sources"] = None                    # this draw's only
        if dead is not None:
            # one undo step (undo.py, plan 15): the row and the depth
            # subscribers that go with it come back with a Ctrl+Z
            undo.push(f"delete route {dead.source} → {dead.target}")
            router.table.remove(dead)
        if not rows:
            imgui.text_disabled("no routes — the lanes drive nothing")
        elif not drawn:
            imgui.text_disabled(NO_MATCH)
        imgui.spacing()
        modifiers(panel, router)                # plan 28 N1: between the routes and the desk
        imgui.separator()
        desk(panel, router)
        imgui.separator()
        macros(panel, router)
        imgui.separator()
        session(panel, router)
        imgui.separator()
        sinks(panel, router)
        # every line is drawn: a control with no line (dark on the global
        # layer) has nothing to scroll to
        st["goto"] = None
    imgui.end_child()
