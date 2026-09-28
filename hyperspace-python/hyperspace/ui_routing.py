"""Routing matrix — the lanes → params half of the binding table (WP5b).

The ROUTING page. Rows are the router's `push` / `position` routes from
`lane:i` (and `ext:i` / `hand:i` when the bridge / hands feed them), two lines each:

  [on] source        target ▾            op ▾           ×
       depth ──────── rest  × scale ▾   ▮▮▮▯▯│ live

The target is a searchable combo over every modulatable param, grouped
by registry group; depth is signed — ±1 in norm units for `push` (1 puts
a lane at the asymptote on the param's end stop), a fraction of the
throw for `position`; `rest` (push rows only) is the source reading that
pushes nothing — normally the source's own, what its adapter publishes
in `Router.rests`, shown dimmed; dragging it makes the row's own number,
"auto" gives it back; scale names an attenuator param or none — the eight
macro knobs first, since that is what they are for. The live bar is the
source's normalized reading (white) with a red hairline at the target's
effective norm, so a route can be read working. Edits land on the table
at once (the router reads it every frame) — nothing here is copied.

The macros (`macro.1–8`, plan 09 decision 7) sit in a strip at the head
of the rows' scroll, two lines of four compact sliders: ordinary registry
widgets, so a performer can own one (right-click: Learn, Route a lane
here…) and its readout shows `base → effective` while it does. A macro
does nothing of its own; a route that names it as its scale runs at
depth × the macro, one frame behind whatever moves the macro — chaining,
not stacking. They are routing-layer state (params.ROUTING_GROUPS): a
theme or project never carries them, a routing preset saved here does.

One performer per target: the table's referee (`routing.Owned`) refuses
a row on a target another enabled row performs, and the refusal is a
question — the Replace / Keep prompt, an imgui modal the panel draws
before anything else, on every page and with the panel hidden (`modal`,
first thing in `Panel.draw`): "Brightness is already performed by R
height positions — Replace / Keep". Two things raise it: an edit here
(`add_route`, a row's target combo, a row's checkbox waking onto a taken
target, "Route a lane here…") holds the question in the page's state
with what *Replace* would do to the table (`ask`); a hand learn the MIDI
adapter had to hold (`midi.pending`) is the same question, answered
through `midi.resolve_pending`. `_question` is whichever is up; `prompt`
reads it, `answer` settles it, and *Replace* writes the file. Every
Replace — here, `_wake`, `_retarget`, the adapter's — is one call,
`Bindings.replace_owner`, which removes whoever owns the target *when the
answer comes*, so a row that landed while the question was up goes too
and exactly one owner remains. The owner is named the way its adapter
names it (`Router.describe`). Rows a preset had to drop for the same
reason (`table.dropped`) are listed under the header until the next edit.

The strip under the title is the preset strip's look over routing
preset *files* (routing.preset_files): prev / next / the list load
through `Router.load_preset`, save / as… write through
`Router.save_preset` into the user library's bindings/ folder, reset is
the factory default. The library's own strip can't do this — bindings/
is a folder without a registry group, so `is_dirty` has nothing to
compare — hence the dirty dot here is the routes against a snapshot
taken at the last load or save.

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

from . import ui, ui_presets
from .bands import CEIL
from .params import Kind, Param
from .routing import FACTORY_DIR, Binding, Owned, Router, preset_files

KEY = "bindings"          # the name-field / listing key on the panel's preset state
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
MACRO_COLS = 4           # the macro strip: eight knobs, two lines of four
MACRO_LABEL_W = 22.0     # a knob's number beside it; the section says "macros"
PROMPT = "replace##routing"   # the Replace / Keep modal's popup id
PROMPT_W = 360.0


# ---- state on the panel ----

def _state(panel) -> dict:
    st = getattr(panel, "_routing_state", None)
    if st is None:
        st = panel._routing_state = {"current": None, "snap": None, "error": "",
                                     "names": None, "filter": "", "prompt": None}
    return st


def router_of(panel) -> Router | None:
    """The app's router, or one over the MIDI adapter's (shared) table."""
    r = getattr(panel, "router", None)
    if r is None and panel.midi is not None:
        r = panel.router = Router(panel.reg, panel.midi.map.table)
    return r


def _home(panel):
    lib = panel.library
    return lib.home if lib is not None else None


def _sig(router: Router) -> list[dict]:
    """The performer rows as they would be written: the page's record of
    what a preset loaded and of what is on disk."""
    return [b.to_json() for b in router.table.routes()]


def dirty(panel, router: Router) -> bool:
    st = _state(panel)
    return st["snap"] is not None and _sig(router) != st["snap"]


def files(panel) -> dict:
    """name → path of the routing preset files, re-listed on the strip's
    poll cadence (a glob per frame would be wasteful, never wrong)."""
    st, now = _state(panel), imgui.get_time()
    hit = st["names"]
    if hit is None or now - hit[0] >= ui_presets.LIST_POLL:
        st["names"] = hit = (now, preset_files(_home(panel)))
    return hit[1]


def names(panel) -> list[str]:
    return sorted(files(panel), key=str.lower)


def _factory(panel, name: str | None) -> bool:
    p = files(panel).get(name)
    return p is not None and FACTORY_DIR in p.parents


def invalidate(panel) -> None:
    _state(panel)["names"] = None


# ---- preset actions (what the strip's buttons do; tests call these) ----

def load(panel, router: Router, name: str) -> None:
    st = _state(panel)
    try:
        missing = router.load_preset(name, _home(panel))
    except (OSError, ValueError, KeyError) as e:
        st["error"] = f"routing: {e}"
        return
    st["current"], st["snap"], st["error"] = name, _sig(router), ""
    if missing and panel.library is not None:
        panel.library.report(missing, f"routing preset {name}")


def step(panel, router: Router, n: int) -> str | None:
    """prev / next by name order; from nothing, the first or the last."""
    listing = names(panel)
    if not listing:
        return None
    cur = _state(panel)["current"]
    k = listing.index(cur) if cur in listing else (-1 if n > 0 else 0)
    name = listing[(k + n) % len(listing)]
    load(panel, router, name)
    return name


def save_as(panel, router: Router, name: str) -> None:
    st, home = _state(panel), _home(panel)
    if home is None:
        st["error"] = "routing: no library to save into"
        return
    try:
        path = router.save_preset(name, home)
    except OSError as e:
        st["error"] = f"routing: {e}"
        return
    st["current"], st["snap"], st["error"] = path.name[:-5], _sig(router), ""
    invalidate(panel)


def add_route(panel, target: str, source: str | None = None, depth: float = 0.5,
              op: str = "push") -> Binding | None:
    """A new `push` row from the selected band's lane (or `source`) to
    target; it rests where its source does. None when the target already
    has a performer — the prompt is up, and *Replace* puts the row in."""
    router = router_of(panel)
    src = source or f"lane:{panel.control.selb}"
    b = Binding(src, target, op, depth)
    try:
        router.table.add(b)
    except Owned as e:
        ask(panel, e.existing, b, lambda: router.table.replace_owner(b))
        return None
    _write(panel, router)
    return b


def _write(panel, router: Router) -> None:
    """The table to its file, and the page's record of what is on disk
    with it, so `_save_edits` doesn't write the same table again."""
    router.table.write()
    _state(panel)["saved"] = _sig(router)


# ---- the prompt: one performer per target, so a second one asks ----

def ask(panel, old: Binding, new: Binding, commit: Callable[[], object]) -> None:
    """Hold the question: `old` performs the target now, `new` asks for it,
    `commit` is what *Replace* does to the table (the file is written
    after). Until it is answered the table is untouched. Every commit goes
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
    the page's own first (settle(True) commits; the page then writes), else
    a hand learn the MIDI adapter is holding (`midi.pending`; settle is its
    `resolve_pending`, which writes for itself). None when nothing asks."""
    st = _state(panel)
    held = st["prompt"]
    if held is not None:
        old, new, commit = held

        def settle(replace_it: bool) -> None:
            st["prompt"] = None
            if replace_it:
                commit()
        return old, new, settle
    m = panel.midi
    if m is not None and m.pending is not None:
        new, old = m.pending
        return old, new, m.resolve_pending
    return None


def prompt(panel) -> tuple[Binding, Binding] | None:
    """(old, new) of the question up now, or None."""
    q = _question(panel)
    return None if q is None else (q[0], q[1])


def answer(panel, replace_it: bool) -> None:
    """*Replace* (True) or *Keep* (False) for whatever `prompt` shows;
    Replace lands in the file at once."""
    q = _question(panel)
    if q is None:
        return
    q[2](replace_it)
    if replace_it:
        _write(panel, router_of(panel))


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


# ---- the strip ----

def strip(panel, router: Router) -> None:
    """◀ name ● ▶ · save · as… · reset — over the routing preset files."""
    st = _state(panel)
    imgui.push_id("strip.routing")
    if ui_presets._name_field(panel, KEY, lambda n: save_as(panel, router, n)):
        imgui.pop_id()
        return
    cur = st["current"]
    listing = names(panel)
    factory = _factory(panel, cur)
    is_dirty = dirty(panel, router)
    imgui.begin_disabled(not listing)
    if imgui.arrow_button("prev", imgui.Dir.left):
        step(panel, router, -1)
    imgui.same_line(0, 2)
    label = ui_presets._elide(cur) if cur else "—"
    imgui.push_style_color(imgui.Col_.button, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text, ui.DIM if factory or cur is None else
                           imgui.ImVec4(0.92, 0.92, 0.92, 1))
    if imgui.button(f"{label}##name", imgui.ImVec2(ui_presets.name_w(), 0)):
        imgui.open_popup("list")
    imgui.pop_style_color(2)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{cur}  ·  {'factory' if factory else 'user'} routing preset — "
                          "click for the list" if cur else
                          "the routes as loaded from the project's bindings.json")
    if is_dirty:
        imgui.same_line(0, 0)
        imgui.text_colored(ui.RED, "●")
        if imgui.is_item_hovered():
            imgui.set_tooltip("routes edited since the preset loaded")
    imgui.same_line(0, 2)
    if imgui.arrow_button("next", imgui.Dir.right):
        step(panel, router, 1)
    imgui.end_disabled()
    if imgui.begin_popup("list"):
        ui._micro("routing")
        for name in listing:
            fac = _factory(panel, name)
            imgui.push_style_color(imgui.Col_.text, ui.DIM if fac else
                                   imgui.ImVec4(0.92, 0.92, 0.92, 1))
            picked, _ = imgui.selectable(f"{name}##pick", name == cur)
            imgui.pop_style_color()
            if picked:
                load(panel, router, name)
        imgui.end_popup()
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("save", "as…", "reset"))
    imgui.begin_disabled(cur is None or factory or _home(panel) is None)
    if ui.chip("save"):
        save_as(panel, router, cur)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("Write the routes over the current preset"
                          + (" — a factory preset: save as… instead" if factory else ""))
    imgui.same_line()
    if ui.chip("as…"):
        ui_presets._begin_naming(panel, KEY, cur or "")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Save the routes as a new user preset (library/bindings/)")
    imgui.same_line()
    if ui.chip("reset"):
        load(panel, router, "default")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Back to the factory routes (the default preset); the bases stay")
    imgui.pop_id()


# ---- the rows ----

SOURCE_ORDER = ("hand", "lfo", "ext")   # the fed schemes, after the analyzer's lanes


def _sources(panel, router: Router) -> list[tuple[str, str]]:
    """(source, label) the combo offers: every analyzer lane as "i NAME",
    then each fed scheme (SOURCE_ORDER) that is around — its adapter has
    published labels, it is being fed this frame, or a row names it — one
    entry per lane, labelled as the adapter says ("lfo LFO 1") or by
    index. Nothing here knows what a scheme is; the ext lanes are the one
    case with a fixed count (N_EXT) since the bridge publishes no labels."""
    chain = panel.audio.chain
    out = [(f"lane:{i}", f"{i} {name}") for i, name in enumerate(chain.band_names)]
    labels = getattr(router, "labels", {})
    for scheme in SOURCE_ORDER:
        names = labels.get(scheme) or []
        vec = router.feeds.get(scheme)
        used = any(b.scheme == scheme for b in router.table.bindings)
        if not (names or vec is not None or used):
            continue
        n = len(names) or (len(vec) if vec is not None else 0) or (N_EXT if scheme == "ext" else 0)
        out += [(f"{scheme}:{i}", f"{scheme} {names[i] if i < len(names) else i}")
                for i in range(n)]
    return out


def _gates(router: Router) -> list[tuple[str, str]]:
    """(address, label) for every switch an adapter offers as a gate."""
    return [(f"{scheme}:{i}", lb)
            for scheme, lanes in getattr(router, "gates", {}).items()
            for i, lb in lanes]


def _gate_combo(b: Binding, gates: list[tuple[str, str]], width: float) -> None:
    """Which switch has to be held for this row to act, or none."""
    labels = ["no gate"] + [lb for _, lb in gates]
    addrs: list[str | None] = [None] + [a for a, _ in gates]
    if b.when not in addrs:            # a gate no adapter is offering now
        labels, addrs = labels + [b.when], addrs + [b.when]
    cur = addrs.index(b.when)
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
    i = b.index
    if b.scheme == "lane":
        a = panel.audio
        if not getattr(a, "on", False) or not 0 <= i < a.chain.n:
            return None
        return float(a.chain.lanes[i]) / CEIL
    vec = router.feeds.get(b.scheme)
    if vec is None or not 0 <= i < len(vec):
        return None
    u = float(vec[i])
    return None if math.isnan(u) else u     # NaN: a hand out of view


def _targets(panel) -> list[Param]:
    return [p for p in panel.reg if p.modulatable and not p.alias]


def _scales(panel, target: str | None = None) -> list[Param]:
    """What a row's scale may be: the macros first — they exist for this —
    then every other continuous param (master.gain on the rate routes), less
    the row's own target: a row scaled by what it pushes strobes (the push
    grows the scale grows the push, then clamps and lets go, every frame).
    Two macros scaling each other's rows are allowed — the performer's rope."""
    reg = panel.reg
    return [q for q in reg.group("macro") if q.id != target] + [
        q for q in reg if q.kind is Kind.CONTINUOUS and not q.alias
        and q.group != "macro" and q.id != target]


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
    cur = next((i for i, (s, _) in enumerate(sources) if s == b.source), -1)
    imgui.set_next_item_width(SRC_W)
    if cur < 0:
        labels, cur = labels + [b.source], len(labels)
    if imgui.begin_combo("##src", labels[cur], imgui.ComboFlags_.no_arrow_button):
        for i, lb in enumerate(labels):
            sel, _ = imgui.selectable(lb, i == cur)
            if sel and i < len(sources):
                b.source = sources[i][0]
        imgui.end_combo()
    imgui.same_line()
    sp = imgui.get_style().item_spacing.x
    op_w = ui.chip_w("push")
    picked = _param_combo(panel, "##target", b.target, -(op_w + ui.chip_w("×") + 2 * sp),
                          lambda: _targets(panel))
    if picked:
        cur = router.table.owner(picked)
        if cur is None or cur is b or not b.is_performer:
            b.target = picked
        else:                               # the referee, on a retarget
            ask(panel, cur, replace(b, target=picked),
                lambda picked=picked: _retarget(router, b, picked))
    if p is None:
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"{b.target}: no such param — the row is dormant")
    elif not p.modulatable and imgui.is_item_hovered():
        imgui.set_tooltip(f"{b.target} is not modulatable — the row is dormant")
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
    scale = _param_combo(panel, "##scale", b.scale,
                         -(BAR_W + gate_w + sp * (2 if gate_w else 1)),
                         lambda: _scales(panel, b.target), none="× 1")
    if scale is not False:
        b.scale = scale
    if imgui.is_item_hovered():
        imgui.set_tooltip("A param whose live value multiplies the depth — a macro, "
                          "to chain (own the macro with a hand or LFO), or master.gain "
                          "on the rate routes. Never the row's own target; two macros "
                          "scaling each other's routes is allowed, and is your rope.")
    if gates:
        imgui.same_line()
        _gate_combo(b, gates, gate_w)
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


# ---- the macros ----

def macros(panel) -> None:
    """The eight macro knobs in two lines of four, each the panel's compact
    slider with its number beside it — so Learn, "Route a lane here…" and
    the `base → effective` readout under a performer come for free."""
    ms = panel.reg.group("macro")
    if not ms:
        return
    ui._micro("macros")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Knobs that do nothing on their own: name one as a route's "
                          "scale, and own it with a hand or LFO, to chain")
    if imgui.begin_table("##macros", MACRO_COLS, imgui.TableFlags_.sizing_stretch_same):
        for k, p in enumerate(ms):
            imgui.table_next_column()
            panel._row(p.id, label=str(k + 1), label_w=MACRO_LABEL_W)
        imgui.end_table()


# ---- the page ----

def page(panel, dt: float) -> None:
    st = _state(panel)
    router = router_of(panel)
    ui._micro("routing")
    if router is None:
        imgui.separator()
        imgui.text_disabled("no router attached")
        return
    strip(panel, router)
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
    if st["error"]:
        imgui.text_colored(ui.WARN, st["error"])
    # what the referee refused from the last preset (one owner per target)
    # and what a migration dropped or moved, until the next edit
    for b, why in router.table.dropped:
        imgui.text_colored(ui.WARN, f"dropped {b.source} → {b.target}: {why}")
    for note in router.table.notes:
        imgui.text_disabled(note)
    # the macros and the rows scroll together if they must, so the strip
    # never shortens the list for good; the preset strip and the header stay put
    if imgui.begin_child("##routes", imgui.ImVec2(0, 0)):
        macros(panel)
        imgui.separator()
        dead = None
        for k, b in enumerate(rows):
            if _row(panel, router, b, k):
                dead = b
            imgui.separator()
        if dead is not None:
            router.table.remove(dead)
        if not rows:
            imgui.text_disabled("no routes — the lanes drive nothing")
    imgui.end_child()
    _save_edits(panel, router)


def _save_edits(panel, router: Router) -> None:
    """The page edits the live table in place; land it in bindings.json once
    it changes and nothing is mid-drag, so a delete stays deleted."""
    st = _state(panel)
    sig = _sig(router)
    if st.get("saved") is None:
        st["saved"] = sig                  # first sight: what's on disk already
    elif sig != st["saved"] and not imgui.is_any_item_active():
        router.table.write()
        st["saved"] = sig
