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

  [on] source        target ▾            op ▾           ×
       depth ──────── rest  × scale ▾   ▮▮▮▯▯│ live

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

from . import apc40, ui, ui_presets, undo
from .bands import CEIL
from .library import PRESETS
from .params import Kind, Param, part_of
from .routing import SHIFT_PARAM, Binding, Macro, Owned, Router, Sub, base_refusal, factory_desk

NAMING = "routing.preset"  # the head's save as… name field (ui_presets._name_field)
DEPTH_MOD = 1.0           # ±, the depth slider's throw
# the op chip cycles push ↔ position; what each one's depth means
OP_CHIP = {"push": "push", "position": "pos"}
NEXT_OP = {"push": "position", "position": "push"}
DEPTH_TIP = {"push": " — 1 is the full throw at a lane's asymptote",
             "position": " — a fraction of the target's throw; 1 is all of it"}
N_EXT = 16                # ext lanes offered once any ext source is around
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


# ---- state on the panel ----

def _state(panel) -> dict:
    st = getattr(panel, "_routing_state", None)
    if st is None:
        st = panel._routing_state = {"error": "", "filter": "", "prompt": None}
    return st


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

SOURCE_ORDER = ("hand", "lfo", "ext")   # the fed schemes, after the analyzer's lanes


def _sources(panel, router: Router) -> list[tuple[str, str]]:
    """(source, label) the combo offers: every analyzer lane as "i NAME"
    (the names the audio engine publishes each frame, `AudioEngine.publish`),
    then each fed scheme (SOURCE_ORDER) that is around — its adapter has
    published labels, it is being fed this frame, or a row names it — one
    entry per lane, labelled as the adapter says ("lfo LFO 1") or by
    index, and addressed by name where the adapter publishes names
    (`Router.address`: ``hand:right.roll``, decision register row 20).
    Nothing here knows what a scheme is; the ext lanes are the one case
    with a fixed count (N_EXT) since the bridge publishes no labels."""
    labels = getattr(router, "labels", {})
    # the lanes as the engine published them (AudioEngine.publish, each
    # frame); until it has — a panel with no frame loop behind it — the
    # chain's own names, so the combo always offers the lanes
    lanes = labels.get("lane") or panel.audio.chain.band_names
    out = [(f"lane:{i}", f"{i} {name}") for i, name in enumerate(lanes)]
    for scheme in SOURCE_ORDER:
        names = labels.get(scheme) or []
        vec = router.feeds.get(scheme)
        used = any(b.scheme == scheme for b in router.table.bindings)
        if not (names or vec is not None or used):
            continue
        n = len(names) or (len(vec) if vec is not None else 0) or (N_EXT if scheme == "ext" else 0)
        out += [(router.address(scheme, i), f"{scheme} {names[i] if i < len(names) else i}")
                for i in range(n)]
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
    """One route, two lines; returns True when the row asked to be deleted."""
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
    sources = _sources(panel, router)
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
    session = is_session_target(panel, b)
    mark_w = imgui.calc_text_size(SESSION_MARK).x + sp if session else 0.0
    picked = _param_combo(panel, "##target", b.target,
                          -(op_w + ui.chip_w("×") + 2 * sp + mark_w),
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
    imgui.pop_id()
    return kill


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
    if pr is not None and cur is not None and ui_presets.dirty(panel, PRESETS):
        imgui.same_line(0, 2)
        imgui.text_colored(ui.RED, "●")
        if imgui.is_item_hovered():
            imgui.set_tooltip("edited since it loaded — save writes it")
    glob = table.layer == "global"
    layer = f"desk layer: {'global' if glob else 'preset'}"
    sp = imgui.get_style().item_spacing.x
    imgui.same_line(imgui.get_content_region_avail().x
                    - ui.chip_w("save", "as…") - ui._micro_width(layer) - sp)
    ui._micro(layer, ui.RED if glob else ui.DIM)
    if imgui.is_item_hovered():
        imgui.set_tooltip("The desk's layer — SHIFT latches it (desk.shift). Global: "
                          "the session's controls, never learned (a learn is refused); "
                          "preset: the loaded preset's desk. A preset load drops to it.")
    imgui.same_line()
    factory = cur is not None and lib.is_factory(PRESETS, cur)
    imgui.begin_disabled(cur is None)
    if ui.chip("save"):
        ui_presets._guard(panel, lib.overwrite, PRESETS)
        ui_presets.invalidate(panel, PRESETS)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("Write the live state over the loaded preset"
                          + (" — a factory preset: saved as your own copy of it"
                             if factory else ""))
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


def unmapped(table) -> list[Binding]:
    """The preset-layer controls the loaded preset leaves dark (D8)."""
    rows = table.desk()
    return [f for f in preset_controls(table) if not any(b.overlaps(f) for b in rows)]


def _desk_targets(panel) -> list[Param]:
    return [p for p in panel.reg if p.kind is not Kind.TEXT and p.id != SHIFT_PARAM]


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
    # (the click is the on-screen desk's, once it has one: plan 17 WP4's `ui_desk.click`)
    imgui.text_colored(ui.FAINT, "new rows: right-click a param → Learn desk"
                       + (", or click a control" if hasattr(ui.ui_desk, "click") else ""))
    sp = imgui.get_style().item_spacing.x
    op_w = imgui.calc_text_size("step +10").x
    dark = unmapped(table)
    col = _column([control_glyph(table, b) for b in (*rows, *dark)])
    dead = None
    for k, b in enumerate(rows):
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
    if dead is not None:
        undo.push(f"unmap {control_glyph(table, dead)}")     # one undo step (undo.py)
        table.remove(dead)
        _desk_edited(table)
    for f in dark:
        _control_cell(table, f, ui.FAINT)
        imgui.same_line(col)
        imgui.text_colored(ui.FAINT, "unmapped — dark")
    if not rows:
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
    for k, p in enumerate(ms):
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


# ---- the session's rows, read-only ----

def session(panel, router: Router) -> None:
    """The invariant and global-layer MIDI rows: bindings.json's, shown so a
    preset mapping one of them (dropped at load, in the head's notes) can
    be seen; never learned or edited here (D5, D6)."""
    table = router.table
    inv = [b for b in table.midi() if b.layer is None]
    glob = [b for b in table.midi() if b.layer == "global"]
    ui._micro("session")
    imgui.same_line()
    imgui.text_disabled("the session's — edit bindings.json")
    col = _column([control_glyph(table, b) for b in (*inv, *glob)])
    for title, rows in (("invariant · both layers", inv), ("global layer · SHIFT on", glob)):
        if not rows:
            continue
        imgui.text_colored(ui.DIM, title)
        for b in rows:
            _control_cell(table, b, ui.FAINT)
            imgui.same_line(col)
            op = _op_text(b)
            imgui.text_colored(ui.FAINT, b.target + ("" if op in ("abs", "toggle") else f"  {op}"))


# ---- the page ----

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
    chain = panel.audio.chain
    live = "live" if getattr(panel.audio, "on", False) else "no source — lanes idle"
    imgui.text_disabled(f"{len(rows)} routes  ·  {chain.n} lanes  ·  {live}")
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("+ route"))
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
        dead = None
        for k, b in enumerate(rows):
            if _row(panel, router, b, k):
                dead = b
            imgui.separator()
        if dead is not None:
            # one undo step (undo.py, plan 15): the row and the depth
            # subscribers that go with it come back with a Ctrl+Z
            undo.push(f"delete route {dead.source} → {dead.target}")
            router.table.remove(dead)
        if not rows:
            imgui.text_disabled("no routes — the lanes drive nothing")
        imgui.spacing()
        desk(panel, router)
        imgui.separator()
        macros(panel, router)
        imgui.separator()
        session(panel, router)
    imgui.end_child()
